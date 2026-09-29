# IP-SAKTI Sahayak

**Ayurveda IP & Regulatory Decision Engine** — A multilingual, RAG-based (source-cited) AI assistant guiding Ayurveda researchers, startups, students, MSMEs, and patent professionals from *Idea → Innovation Passport → Patent Analysis → Compliance → Commercialization*.

Production-grade — runs locally in VS Code, deployed via Docker.

---

## ✨ Core Features

| Feature | Status |
|---|---|
| Next.js 14 Frontend (App Router, TypeScript, Tailwind) | ✅ Working |
| FastAPI Backend with Swagger docs | ✅ Working |
| JWT Authentication (Signup / Login / Profile) | ✅ Working |
| PostgreSQL + SQLite fallback (SQLAlchemy) | ✅ Working |
| Hybrid RAG pipeline (Qdrant dense + BM25 lexical, BGE-M3 embeddings) | ✅ Working |
| Multilingual formulation input (10 languages) | ✅ Working |
| Botanical canonicalization (हळद → Curcuma longa) | ✅ Working |
| Innovation Passport (4-section) | ✅ Working |
| Patent Readiness (Novelty / Inventive Step / Overall) | ✅ Working |
| Evidence Matrix (color-coded, upload) | ✅ Working |
| AI Copilot (RAG-grounded with sources + confidence) | ✅ Working |
| Claim Firewall (label analysis) | ✅ Working |
| FTO Check (Google/WIPO patent metadata simulation) | ✅ Working |
| Regulatory Roadmap (6-phase timeline) | ✅ Working |
| Dossier Export (PDF / DOCX / HTML / filing checklist) | ✅ Working |
| Document upload (PDF / DOCX / TXT / images) | ✅ Working |
| Docker Compose (8 services: frontend, backend, workers, postgres, qdrant, redis, model server) | ✅ Working |

---

## 📁 Project Structure

```
IP-SAKTI/
├── frontend/                    # Next.js 14 App Router
│   ├── src/
│   │   ├── app/                 # Pages (dashboard, login)
│   │   ├── components/          # UI components
│   │   ├── lib/                 # API clients, auth, i18n
│   │   └── types/               # TypeScript types
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/v1/              # All API route handlers
│   │   ├── auth/                # JWT + password hashing
│   │   ├── rag/                 # Qdrant store, embeddings, hybrid retriever
│   │   ├── models/              # Pydantic + SQLAlchemy models
│   │   ├── services/            # Business logic engines
│   │   ├── knowledge/           # Ayurveda datasets (JSON)
│   │   └── main.py              # FastAPI entrypoint
│   ├── data/                    # RAG source documents
│   ├── scripts/                 # build_faiss.py (legacy FAISS index)
│   ├── exports/                 # Generated dossiers
│   ├── uploads/                 # Uploaded documents
│   └── requirements.txt
│
├── docker-compose.yml           # 8 services (see Docker section)
├── backend/.env.example
└── README.md
```

---

## 🚀 Quick Start (VS Code)

### Prerequisites
- Node.js 18+
- Python 3.11+
- (Optional) PostgreSQL 15 — *falls back to SQLite automatically*
- ~5 GB free disk + a one-time model download (see step 1d)

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows (PowerShell)
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
cp .env.example .env           # then edit .env (see Environment Variables)
uvicorn app.main:app --reload
```

**1a.** The API runs at `http://localhost:8000` · Swagger at `http://localhost:8000/api/v1/docs`

**1b.** The database schema is created automatically on first start — no migration step. Without PostgreSQL it silently uses `backend/ipsakti.db` (SQLite).

**1c.** The vector store ships **empty** because it is gitignored. Until you reindex, the copilot has no dense-retrieval results. Build it once after the server is up:

```bash
curl -X POST http://localhost:8000/api/v1/rag/reindex
```

This loads the curated corpus from `backend/data/` and upserts it into Qdrant (embedded locally by default). `POST /api/v1/admin/reindex` requires `BACKEND_API_KEY_SECRET` as the `api_key` header and is otherwise equivalent.

> Do **not** run `python scripts/build_faiss.py` for this — it builds a legacy FAISS index that the main RAG pipeline never reads.

**1d.** On first start the embedding layer downloads `BAAI/bge-m3` (~2 GB) and the reranker `BAAI/bge-reranker-v2-m3` (~2 GB). To skip the download, set `IPSAKTI_USE_BGE_M3=0` and `IPSAKTI_USE_RERANKER=0` **as environment variables in your shell** (these are `os.getenv` settings, so `.env` will not work — see Environment Variables); the app then falls back to a local hashing embedding (192-dim) and BM25 lexical search — fully functional, lower semantic quality.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:3000`

> `frontend/.env.local` is optional for local dev — `next.config.js` already proxies `/api/v1` to `http://localhost:8000`.

---

## 🐳 Docker

```bash
docker compose up --build
```

Services (8):

| Service | Role |
|---|---|
| `frontend` | Next.js on `:3000` |
| `backend` | FastAPI on `:8000` |
| `postgres` | PostgreSQL 15 (`ipsakti` / `ipsakti_secret`) |
| `qdrant` | Vector store on `:6333` |
| `redis` | Cache / rate-limit / job lock |
| `modelserver` | Embedding + reranker model host on `:8081` |
| `jobworker` | Background job runner (`python -m app.core.jobs`) |
| `ingestionworker` | Scheduled corpus harvester |

Docker Compose injects real environment variables, so `.env` is **not** consulted there. The first build waits on `modelserver` becoming healthy (`start_period: 180s`) because of the model download.

To build the RAG index inside the running container, call the same endpoint the local flow uses:
```bash
curl -X POST http://localhost:8000/api/v1/rag/reindex
```

---



> As noted under Environment Variables, these `IPSAKTI_*` / `REDIS_URL` / `NEO4J_*` values are read from the **process environment**, not from `backend/.env`.

**Frontend:** the AI Copilot labels replies "Unified RAG" and shows live latency, source-count and confidence metrics. There is currently **no per-request architecture selector in the UI** — the backend resolves every query to `combined`. To exercise a specific architecture, call `POST /api/v1/rag/search` directly with `rag_type`.
