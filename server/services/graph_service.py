"""
Graph service — manages persistent local Knowledge Graph for email entities.
Nodes: Sender, Email, Organization, Topic, ActionItem
Edges: SENT, BELONGS_TO, DISCUSSES, REQUIRES
"""

import json
import os
import re

GRAPH_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "graph_data.json")

_graph_data = {
    "nodes": {},  # id -> {id, label, type, metadata}
    "edges": []   # [{source, target, relation}]
}


def load_graph():
    """Load persistent knowledge graph from JSON file."""
    global _graph_data
    if os.path.exists(GRAPH_FILE):
        try:
            with open(GRAPH_FILE, "r", encoding="utf-8") as f:
                _graph_data = json.load(f)
                if "nodes" not in _graph_data:
                    _graph_data["nodes"] = {}
                if "edges" not in _graph_data:
                    _graph_data["edges"] = []
        except Exception as e:
            print(f"[GraphStore] Error loading graph file: {e}")
            _graph_data = {"nodes": {}, "edges": []}
    else:
        _graph_data = {"nodes": {}, "edges": []}


def save_graph():
    """Save persistent knowledge graph to JSON file."""
    os.makedirs(os.path.dirname(GRAPH_FILE), exist_ok=True)
    try:
        with open(GRAPH_FILE, "w", encoding="utf-8") as f:
            json.dump(_graph_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[GraphStore] Error saving graph file: {e}")


def _clean_id(text: str) -> str:
    """Clean string to form a stable node ID."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', text.strip().lower())


def add_node(node_id: str, label: str, node_type: str, metadata: dict = None) -> str:
    """Add or update a node in the graph."""
    if not node_id or not label:
        return ""
    
    if node_id not in _graph_data["nodes"]:
        _graph_data["nodes"][node_id] = {
            "id": node_id,
            "label": label,
            "type": node_type,
            "metadata": metadata or {}
        }
    else:
        # Merge metadata
        if metadata:
            _graph_data["nodes"][node_id]["metadata"].update(metadata)
    return node_id


def add_edge(source_id: str, target_id: str, relation: str):
    """Add an edge if both nodes exist and edge doesn't already exist."""
    if not source_id or not target_id or source_id not in _graph_data["nodes"] or target_id not in _graph_data["nodes"]:
        return
    
    # Check duplicate
    for edge in _graph_data["edges"]:
        if edge["source"] == source_id and edge["target"] == target_id and edge["relation"] == relation:
            return
            
    _graph_data["edges"].append({
        "source": source_id,
        "target": target_id,
        "relation": relation
    })


def extract_org_from_email_address(email_addr: str) -> str:
    """Extract domain/company name from an email address (e.g., openai.com -> OpenAI)."""
    match = re.search(r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', email_addr)
    if match:
        domain = match.group(1).lower()
        # Exclude common generic providers
        if domain not in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]:
            company = domain.split('.')[0]
            return company.capitalize()
    return ""


def add_email_to_graph(
    message_id: str,
    subject: str,
    sender_raw: str,
    date: str,
    summary: str,
    uid: str,
    extracted_entities: dict = None
):
    """
    Incorporate an email and its extracted entities into the knowledge graph.
    """
    load_graph()

    # 1. Email Node
    email_node_id = f"email_{message_id}"
    add_node(
        node_id=email_node_id,
        label=subject[:40] if subject else "(No Subject)",
        node_type="email",
        metadata={
            "message_id": message_id,
            "subject": subject,
            "date": date,
            "summary": summary,
            "uid": uid
        }
    )

    # 2. Sender Node
    sender_name = sender_raw
    sender_id = f"sender_{_clean_id(sender_raw)}"
    add_node(
        node_id=sender_id,
        label=sender_name,
        node_type="sender",
        metadata={"raw": sender_raw, "uid": uid}
    )
    
    # Edge: Sender -> SENT -> Email
    add_edge(sender_id, email_node_id, "SENT")

    # 3. Organization Node (from domain or extraction)
    org_name = extract_org_from_email_address(sender_raw)
    if org_name:
        org_id = f"org_{_clean_id(org_name)}"
        add_node(org_id, org_name, "organization", metadata={"uid": uid})
        add_edge(sender_id, org_id, "BELONGS_TO")

    # 4. Process Extracted Entities (topics, organizations, action items)
    if extracted_entities:
        # Organizations
        for org in extracted_entities.get("organizations", []):
            if org and len(org.strip()) > 1:
                o_id = f"org_{_clean_id(org)}"
                add_node(o_id, org.strip(), "organization", metadata={"uid": uid})
                add_edge(email_node_id, o_id, "MENTIONS")

        # Topics / Concepts
        for topic in extracted_entities.get("topics", []):
            if topic and len(topic.strip()) > 1:
                t_id = f"topic_{_clean_id(topic)}"
                add_node(t_id, topic.strip(), "topic", metadata={"uid": uid})
                add_edge(email_node_id, t_id, "DISCUSSES")

        # Action Items
        for action in extracted_entities.get("action_items", []):
            if action and len(action.strip()) > 2:
                a_id = f"action_{_clean_id(action[:30])}"
                add_node(a_id, action.strip(), "action_item", metadata={"uid": uid})
                add_edge(email_node_id, a_id, "REQUIRES")

    save_graph()


def get_user_graph(uid: str = "") -> dict:
    """Return nodes and edges filtered for a specific user UID."""
    load_graph()
    
    if not uid:
        # Return all
        nodes_list = list(_graph_data["nodes"].values())
        return {"nodes": nodes_list, "edges": _graph_data["edges"]}

    # Filter nodes by UID
    valid_node_ids = set()
    filtered_nodes = []
    
    for n_id, node in _graph_data["nodes"].items():
        node_uid = node.get("metadata", {}).get("uid")
        if not node_uid or node_uid == uid:
            valid_node_ids.add(n_id)
            filtered_nodes.append(node)

    # Filter edges between valid nodes
    filtered_edges = [
        e for e in _graph_data["edges"]
        if e["source"] in valid_node_ids and e["target"] in valid_node_ids
    ]

    return {"nodes": filtered_nodes, "edges": filtered_edges}
