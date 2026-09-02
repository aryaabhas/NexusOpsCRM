# NexusOpsCRM (NexusMail AI) 🚀

**NexusOpsCRM** is a privacy-first, on-device AI operations platform that unifies your email inbox, Kanban task board, CRM client directory, and scheduling into a single seamless workspace. Designed to eliminate context switching, it processes all semantic search and AI operations locally on your machine, ensuring zero private data leakage.

![Architecture Diagram](nexusops_architecture_diagram_1787813817818.jpg)

## 🌟 The Problem it Solves
Teams managing clients through email often lose track of tasks, complaints, and follow-ups because their tools—Gmail, spreadsheets, task managers, and notes apps—are completely disconnected. Existing solutions (like Salesforce) are expensive and complex, while cloud AI tools compromise data privacy.

**NexusOpsCRM** bridges this gap. It connects your inbox directly to your operations workflow, executing semantic search and AI processing completely on-device.

## 🚀 Key Features
*   **Inbox & Operations Unified:** Read, draft, and reply to emails inside the same dashboard where you manage tasks and clients.
*   **On-Device Semantic Search:** Search emails by concept, not just keywords. Uses a local FAISS index and `all-MiniLM-L6-v2` embeddings for sub-2ms hybrid retrieval (Cosine + TF-IDF) on your CPU.
*   **AI Summaries & Drafts:** Leverage `gpt-4o-mini` for instant thread summaries, entity extraction, and persona-injected email drafts.
*   **Interactive Knowledge Graph:** A 60 FPS HTML5 Canvas force-directed graph (Hooke's Law + Coulomb Repulsion) mapping entities, topics, and senders.
*   **Kanban Task Board:** Drag-and-drop task management with automated progress tracking and subtask checklists.
*   **CRM & Grievance Tracker:** Non-destructive Excel/CSV lead importing via SheetJS. Flag and track client complaints until resolution.
*   **NLP Calendar Scheduling:** Automatically detects dates (e.g., "next Friday") from emails and pre-fills your calendar.
*   **Rich Scratchpad & PDF Export:** Auto-saving rich text editor with image paste support and one-click PDF compilation via jsPDF.

## 🛠️ Tech Stack

### Frontend
*   **Vanilla JS (ES6+)** - Zero-framework SPA for maximum performance.
*   **HTML5 Canvas** - Custom physics engine for the Knowledge Graph (No D3/Three.js used for the graph logic).
*   **Three.js** - Ambient background particle rendering.
*   **CSS3** - Modern Warm Cream & Teal design system.
*   **SheetJS & jsPDF** - Client-side file processing.

### Backend
*   **Python 3.10+ & FastAPI** - High-performance async API server.
*   **Meta FAISS & SentenceTransformers** - Local vector storage and embedding generation.
*   **OpenAI API** - Remote LLM integration for summarization.
*   **Google Firebase** - OAuth2 Authentication and JWT Session validation.
*   **httpx** - Async Gmail API integration.
*   **JSON Flat-Files** - Mutex-gated local persistence.

## ⚙️ Architecture Highlights
*   **Privacy-Preserving Search:** Embeddings are generated locally using a `SentenceTransformers` singleton. The FAISS `IndexFlatIP` handles dense-sparse hybrid rank fusion with a strict 0.48 confidence threshold without exposing data to third-party vector clouds.
*   **Thread-Safe Storage:** Uses Python `threading.Lock()` mutex primitives to ensure race-condition-free writes across multi-tenant JSON flat-file datastores.
*   **Zero-Overhead State Management:** The frontend relies on native DOM diffing, event delegation, and debouncing instead of a Virtual DOM, providing instant responsiveness.

## 🚀 Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   Google Cloud Console Project (with Gmail API enabled)
*   Firebase Project (for Authentication)

### 1. Backend Setup
```bash
cd server
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows
pip install -r requirements.txt
```
**Environment Variables (`server/.env`)**
Create a `.env` file in the `server` directory:
```ini
OPENAI_API_KEY=your_openai_key
VECTOR_STORE_DIR=./data
PORT=8000
```
*Note: Place your `serviceAccountKey.json` from Firebase in the `server` directory.*

**Run the server:**
```bash
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd client
npm install
```
**Firebase Configuration (`client/src/firebase-config.js`)**
Ensure you configure your Firebase web SDK credentials inside the `firebase-config.js` file.

**Run the client:**
```bash
npm run dev
```
Navigate to `http://localhost:5173`.

---
*Developed by a Full-Stack / AI Engineer focused on privacy, performance, and seamless user experiences.*
