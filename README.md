﻿# IP-SAKTI Sahayak

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

---

## ☁️ Deployment

The free-tier deployment guide (Vercel frontend, Render or Cloud Run backend,
environment variables, and the "lite" mode notes) lives in
[`DEPLOYMENT.md`](DEPLOYMENT.md) so that keeping this README short does not
mean losing the deployment instructions.

## 🔐 Environment Variables

### Backend (`backend/.env`)

Start by copying the template: `cp backend/.env.example backend/.env`.

⚠️ **Only some variables are actually read from `.env`.** The app has two configuration paths, and they behave differently:

**Read from `.env`** (loaded by the pydantic `Settings` model):
`PROJECT_NAME`, `VERSION`, `ENVIRONMENT`, `PORT`, `HOST`, `CORS_ORIGINS`, `GRIEVANCE_OFFICER_NAME`, `GRIEVANCE_OFFICER_EMAIL`, `DATA_LOCALIZATION_REGION`, `DPDP_RETENTION_DAYS`, `BACKEND_API_KEY_SECRET`, `FEATURE_FLAGS`.

**NOT read from `.env`** — these are read straight from the process environment with `os.getenv`, so putting them in `.env` has **no effect**. Export them in your shell or inject them via Docker:

```
DATABASE_URL, QDRANT_URL, QDRANT_API_KEY, REDIS_URL,
NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
GEMINI_API_KEY, OPENAI_API_KEY,
and every IPSAKTI_* flag (IPSAKTI_USE_BGE_M3, IPSAKTI_LLM_PROVIDER, ...)
```

Minimal `.env`:
```
BACKEND_API_KEY_SECRET=<paste a long random string here>
CORS_ORIGINS=["http://localhost:3000"]
```

`BACKEND_API_KEY_SECRET` signs JWTs and gates the `/admin/*` endpoints. **If you leave it empty the app generates a random one per process**, which means every backend restart silently logs all users out and `/admin/*` can no longer be called. Always set it for a demo or deployment.

`DATABASE_URL` is the one people most often expect to work from `.env` — it does not. Set it in the shell instead:
```bash
# Windows PowerShell
$env:DATABASE_URL = "postgresql://ipsakti:ipsakti_secret@localhost:5432/ipsakti"
# macOS / Linux
export DATABASE_URL=postgresql://ipsakti:ipsakti_secret@localhost:5432/ipsakti
```
Omit it entirely and the app uses SQLite (`backend/ipsakti.db`).

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

---

## 📡 API Reference

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/signup` | Create account |
| `POST /api/v1/auth/login` | Login, returns JWT |
| `GET /api/v1/auth/profile` | Current user profile |
| `POST /api/v1/passport/create` | Create Innovation Passport |
| `PUT /api/v1/passport/{id}/update` | Update passport |
| `POST /api/v1/formulation/parse` | Parse multilingual formulation |
| `POST /api/v1/botanical/canonicalize` | Map to API botanical name |
| `POST /api/v1/chat/query` | AI Copilot (RAG answer + sources) |
| `GET /api/v1/chat/suggested-questions` | Suggested copilot questions |
| `POST /api/v1/fto/check` | Freedom-to-Operate analysis |
| `POST /api/v1/label/analyze` | Claim Firewall / label analysis |
| `GET /api/v1/analysis/readiness/{id}` | Patent readiness scores |
| `GET /api/v1/roadmap/{id}` | Regulatory roadmap |
| `POST /api/v1/export/dossier` | Generate dossier — `format`: `pdf` (dossier), `docx` (editable), `checklist` (filing tick-list), `html` |
| `POST /api/v1/upload/disclosure-check` | Upload & scan documents |
| `POST /api/v1/assessment/evaluate` | Regulatory assessment |
| `POST /api/v1/what-if/simulate` | Claim mutation simulation |
| `GET /api/v1/evidence/{id}` | Evidence gaps summary |
| `POST /api/v1/rag/reindex` | Build/refresh the vector index — **run once after cloning** |
| `POST /api/v1/rag/search` | Unified RAG search (`rag_type`) |
| `GET /api/v1/rag/search/stats` | Per-architecture RAG health + metrics |

Full interactive docs: `http://localhost:8000/api/v1/docs`

---

## 🧬 RAG Pipeline

Hybrid retrieval — four cascading strategies (`backend/app/rag/retrieval_pipeline.py`):

1. **Qdrant** — dense semantic search over the curated corpus
2. **BM25** — lexical / keyword search (`rank_bm25`)
3. **Metadata filter** — source, jurisdiction, authority, patent number
4. **BGE reranker** — cross-encoder re-scoring of the merged candidates

```
Query → Query Expansion → Embed → Qdrant (top 20)
      → BM25 (top 20) → Multi-Query (parallel)
      → Merge + Deduplicate → Metadata Filter
      → Adaptive Rerank → Hallucination Check
      → Confidence Score → Verified Context
```

- **Corpus** — `backend/data/{pharmacopoeia,ayurveda,regulations,patents,pubmed,who,...}` (tracked in git)
- **Chunking** — 800 words / 150-word overlap, with a section-aware 700/120 variant for structured documents (`app/rag/kb.py`)
- **Embeddings** — `BAAI/bge-m3` (1024-dim, multilingual); falls back to OpenAI, then to a local hashing embedding (192-dim)
- **Generation** — answers are grounded only in retrieved context; every reply carries its sources and a confidence score

The vector store is **gitignored and therefore empty on a fresh clone**. Rebuild it once the server is running:

```bash
curl -X POST http://localhost:8000/api/v1/rag/reindex
```

Re-run this after changing anything under `backend/data/`.

> `python scripts/build_faiss.py` builds a *separate, legacy* FAISS index used only by a few auxiliary services. It is **not** the store the copilot queries — running it will not populate retrieval.

---

## 🌐 Multilingual Pipeline

```
User input (हळद, नीम, तुळस)
        ↓
Language Detection (Devanagari → hi/mr, Tamil → ta, ...)
        ↓
Botanical Canonicalization → Curcuma longa, Azadirachta indica...
        ↓
RAG Retrieval against Ayurvedic Pharmacopoeia & classical texts
        ↓
LLM Answer + Cited Sources
```

Supported: English, हिन्दी (hi), मराठी (mr), தமிழ் (ta), తెలుగు (te), ಕನ್ನಡ (kn), বাংলা (bn), ગુજરાતી (gu), മലയാളം (ml), संस्कृतम् (sa).

---

## 🛠 Troubleshooting

**Backend won't start (database error)**
- PostgreSQL unavailable → app auto-falls back to SQLite (`ipsakti.db`)
- To force SQLite, set `DATABASE_URL=sqlite:///./ipsakti.db` **in the shell** — setting it in `.env` has no effect (see Environment Variables)

**Copilot answers with no sources / "no sources matched"**
- The vector store is gitignored, so it is empty on a fresh clone. Run `curl -X POST http://localhost:8000/api/v1/rag/reindex` once the server is up.
- Setting `DATABASE_URL` or the LLM keys in `.env` also silently does nothing — they must be real environment variables.

**Everyone gets logged out after a backend restart**
- `BACKEND_API_KEY_SECRET` is unset, so a random secret is generated per process. Set it in `backend/.env` (this one *is* read from `.env`).

**Slow first start / model download**
- The first run downloads `BAAI/bge-m3` and `BAAI/bge-reranker-v2-m3` (~4-5 GB combined). To skip, set `IPSAKTI_USE_BGE_M3=0` and `IPSAKTI_USE_RERANKER=0` in the **shell**.

**Embeddings / FAISS install fails**
- Ensure Python 3.11 × 64-bit. On Windows try `pip install faiss-cpu sentence-transformers`
- Without `faiss-cpu` only the legacy auxiliary index is unavailable; the main Qdrant + BM25 pipeline still works

**Frontend can't reach backend**
- Check `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` (optional locally — `next.config.js` proxies `/api/v1` to `:8000`)
- Restart backend with `uvicorn app.main:app --reload`

**Port already in use**
- Backend: `uvicorn app.main:app --port 8001`
- Frontend: `npm run dev -- -p 3001`

---

## 🎯 Demo Flow

1. Open `http://localhost:3000` → **Create Account** (no demo user is seeded — sign up first)
2. Dashboard shows Overview cards (Passport, Patent Readiness, Evidence, Next Action)
3. Fill the **Innovation Passport** 4-step form (basic info → multilingual formulation → process → claims)
4. View **Patent Analysis** scores, **Evidence Matrix**, and chat with **AI Copilot**
5. Run **Claim Firewall** on your label copy, then **export the dossier**

---

## ⚖️ Compliance

- **DPDP Act 2023** — consent logging (`DPDPConsentLogger`)
- **AI citation grounding** — every answer shows retrieved sources + confidence
- **Grievance officer** — grievance@ipsakti.in
- **Data residency** — ap-south-1 (Mumbai, India)

For informational purposes only — not legal advice. Consult qualified patent agents and regulatory specialists for final decisions.

---

## 🧠 Unified RAG Architectures

The knowledge layer exposes several RAG architectures behind one unified
interface (`backend/app/services/rag/`), all wrapping the same hybrid pipeline:

| Architecture | What it adds over the core hybrid pipeline |
|---|---|
| `combined` | Union of every architecture below — **the default, and what "Auto" always resolves to** |
| `hybrid` | Qdrant dense + BM25 + statutory -> RRF -> BGE cross-encoder rerank |
| `production` | Result caching + per-user rate limit + query/cost logging (Redis opt-in, in-memory fallback) |
| `graph` | Local knowledge graph entity traversal fused with hybrid results (optional Neo4j) |
| `agentic` | Parallel Patent / Regulatory / ABS / TKDL specialist agents + intent routing |

**Endpoints** (all backward-compatible; `/rag/ask` is untouched):

- `POST /rag/search` — unified search, select via `rag_type: combined|hybrid|production|graph|agentic`
- `GET /rag/search/stats` — per-architecture health + metrics
- `POST /rag/configure` — set default `rag_type`, `cache_ttl`, `rate_limit` at runtime

**Environment** (optional, see `backend/.env.example`):

- `IPSAKTI_RAG_DEFAULT` — default architecture when `rag_type` is omitted (defaults to `combined`)
- `IPSAKTI_RAG_CACHE_TTL`, `IPSAKTI_RAG_RATE_LIMIT` — production caching/limits
- `REDIS_URL` — enables Redis cache + rate limiting (in-memory fallbacks otherwise)
- `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` — optional Neo4j graph traversal

> As noted under Environment Variables, these `IPSAKTI_*` / `REDIS_URL` / `NEO4J_*` values are read from the **process environment**, not from `backend/.env`.

**Frontend:** the AI Copilot labels replies "Unified RAG" and shows live latency, source-count and confidence metrics. There is currently **no per-request architecture selector in the UI** — the backend resolves every query to `combined`. To exercise a specific architecture, call `POST /api/v1/rag/search` directly with `rag_type`.