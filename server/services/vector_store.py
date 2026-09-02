"""
Vector store service — FAISS + all-MiniLM-L6-v2 (sentence-transformers).

Embeddings: local, 384-dim, no API key required.
Index:       FAISS IndexFlatIP (Inner Product / cosine similarity on normalised vectors).
Metadata:    stored in a sidecar JSON file alongside the FAISS index.
Persistence: saved to disk on every write; loaded on startup.
"""

import json
import os
import uuid
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR      = Path(os.getenv("VECTOR_STORE_DIR", "./data"))
INDEX_PATH    = DATA_DIR / "email_index.faiss"
METADATA_PATH = DATA_DIR / "email_metadata.json"
DIMENSION     = 384   # all-MiniLM-L6-v2 output dimension

# ── Module-level singletons (loaded once at startup) ─────────────────────────
_model:    SentenceTransformer | None = None
_index:    faiss.Index | None         = None
_metadata: list[dict]                  = []   # parallel list: _metadata[i] → vector at index i


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("[VectorStore] Loading all-MiniLM-L6-v2 model…")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[VectorStore] Model loaded.")
    return _model


def _get_index() -> faiss.Index:
    global _index
    if _index is None:
        _index = faiss.IndexFlatIP(DIMENSION)
    return _index


def load_store() -> None:
    """Load FAISS index and metadata from disk (called at server startup)."""
    global _index, _metadata
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if INDEX_PATH.exists() and METADATA_PATH.exists():
        print(f"[VectorStore] Loading existing index from {INDEX_PATH}")
        _index    = faiss.read_index(str(INDEX_PATH))
        _metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        print(f"[VectorStore] Loaded {len(_metadata)} stored documents.")
    else:
        print("[VectorStore] No existing index found, starting fresh.")
        _index    = faiss.IndexFlatIP(DIMENSION)
        _metadata = []

    # Ensure model is pre-loaded so first request is fast
    _get_model()


def _save_store() -> None:
    """Persist FAISS index and metadata to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(_get_index(), str(INDEX_PATH))
    METADATA_PATH.write_text(
        json.dumps(_metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _embed(text: str) -> np.ndarray:
    """Encode a string to a normalised 384-dim float32 vector."""
    model  = _get_model()
    vector = model.encode([text], normalize_embeddings=True, show_progress_bar=False)
    return vector.astype(np.float32)   # shape: (1, 384)


def add_document(metadata: dict) -> str:
    """
    Embed the summary text in metadata["summary"] and add it to the FAISS index.
    Returns the generated doc_id.

    metadata must include: summary, message_id, subject, from, date
    """
    global _metadata

    doc_id   = str(uuid.uuid4())
    summary  = metadata.get("summary", "")
    email_id = metadata.get("from", "")
    
    # Prepend email/sender ID to summary before embedding/storing (without sending to LLM)
    combined_summary = f"Sender/Email ID: {email_id}\n\n{summary}"
    metadata["summary"] = combined_summary
    
    vector   = _embed(combined_summary)          # (1, 384)

    index = _get_index()
    index.add(vector)                   # adds at position len(_metadata)
    _metadata.append({**metadata, "doc_id": doc_id})
    _save_store()
    return doc_id


def search(query_text: str, k: int = 5) -> list[dict]:
    """
    Embed query_text and perform hybrid search combining local FAISS vector
    similarity and normalized term occurrence (TF-IDF).
    Filters results using a strict confidence threshold of 0.48.
    """
    index = _get_index()
    if index.ntotal == 0:
        return []

    # 1. Fetch dense vector results from FAISS
    # We query more elements than requested to allow candidate pool processing
    candidate_k = min(k * 4, index.ntotal)
    query_v = _embed(query_text)
    scores, indices = index.search(query_v, candidate_k)

    # 2. Extract unique query tokens for sparse lexical search
    stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "is", "of"}
    query_tokens = [
        t.strip().lower() 
        for t in query_text.replace(",", " ").replace(".", " ").split() 
        if len(t.strip()) > 1 and t.strip().lower() not in stopwords
    ]

    candidates = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1 or idx >= len(_metadata):
            continue
        
        meta = _metadata[idx].copy()
        vector_score = float(score)  # range: [0, 1] for normalized embeddings

        # Calculate lexical match (term occurrence / TF proxy)
        text_content = f"{meta.get('subject', '')} {meta.get('summary', '')}".lower()
        tf_score = 0.0
        if query_tokens:
            for token in query_tokens:
                count = text_content.count(token)
                if count > 0:
                    tf_score += count * 1.5  # Weight keyword hits
        
        candidates.append({
            "meta": meta,
            "vector_score": vector_score,
            "tf_score": tf_score
        })

    if not candidates:
        return []

    # 3. Min-Max normalize tf_score to [0, 1] range to balance both scales
    tf_scores = [c["tf_score"] for c in candidates]
    min_tf = min(tf_scores)
    max_tf = max(tf_scores)
    tf_range = max_tf - min_tf

    for c in candidates:
        normalized_tf = (c["tf_score"] - min_tf) / tf_range if tf_range > 0 else (1.0 if min_tf > 0 else 0.0)
        
        # Fused Hybrid Score (60% Dense + 40% Sparse)
        hybrid_score = 0.6 * c["vector_score"] + 0.4 * normalized_tf
        c["hybrid_score"] = hybrid_score

    # 4. Filter by strict confidence threshold (0.48) and sort
    threshold = 0.48
    filtered_results = []
    for c in candidates:
        if c["hybrid_score"] >= threshold:
            meta = c["meta"]
            meta["score"] = c["hybrid_score"]  # override score output key
            filtered_results.append(meta)

    filtered_results.sort(key=lambda x: x["score"], reverse=True)
    return filtered_results[:k]


def get_all_summaries() -> list[dict]:
    """Return all stored email metadata (without vectors)."""
    return list(_metadata)


def is_already_stored(message_id: str) -> bool:
    """Check if an email with this Gmail message_id is already in the store."""
    return any(m.get("message_id") == message_id for m in _metadata)


def delete_document(target_id: str) -> bool:
    """
    Remove an email summary by target_id (matches message_id OR doc_id)
    from metadata and rebuild the FAISS index by reconstructing vectors
    directly from the old index (avoiding re-embedding).
    Returns True if an item was removed, False otherwise.
    """
    global _index, _metadata

    # 1. Identify which documents to keep
    keep_indices = []
    new_metadata = []
    for i, m in enumerate(_metadata):
        if m.get("message_id") != target_id and m.get("doc_id") != target_id:
            keep_indices.append(i)
            new_metadata.append(m)

    if len(new_metadata) == len(_metadata):
        return False

    # 2. Rebuild FAISS index using reconstructed vectors from the current index
    new_index = faiss.IndexFlatIP(DIMENSION)
    for old_pos in keep_indices:
        vector = _index.reconstruct(old_pos)
        new_index.add(vector.reshape(1, -1))

    _metadata = new_metadata
    _index = new_index
    _save_store()
    return True
