# IP-SAKTI Sahayak

**Ayurveda IP & Regulatory Decision Engine** â€” A multilingual, RAG-based (source-cited) AI assistant guiding Ayurveda researchers, startups, students, MSMEs, and patent professionals from *Idea â†’ Innovation Passport â†’ Patent Analysis â†’ Compliance â†’ Commercialization*.

Production-grade â€” runs locally in VS Code, deployed via Docker.

---

## âœ¨ Core Features

| Feature | Status |
|---|---|
| Next.js 14 Frontend (App Router, TypeScript, Tailwind) | âœ… Working |
| FastAPI Backend with Swagger docs | âœ… Working |
| JWT Authentication (Signup / Login / Profile) | âœ… Working |
| PostgreSQL + SQLite fallback (SQLAlchemy) | âœ… Working |
| FAISS RAG pipeline (BGE embeddings) | âœ… Working |
| Multilingual formulation input (10 languages) | âœ… Working |
| Botanical canonicalization (à¤¹à¤³à¤¦ â†’ Curcuma longa) | âœ… Working |
| Innovation Passport (4-section w/ QR) | âœ… Working |
| Patent Readiness (Novelty / Inventive Step / Overall) | âœ… Working |
| Evidence Matrix (color-coded, upload) | âœ… Working |
| AI Copilot (RAG-grounded with sources + confidence) | âœ… Working |
| Claim Firewall (label analysis) | âœ… Working |
| FTO Check (Google/WIPO patent metadata simulation) | âœ… Working |
| Regulatory Roadmap (6-phase timeline) | âœ… Working |
| Dossier Export (HTML report w/ QR, Patent Score, Evidence) | âœ… Working |
| Document upload (PDF / DOCX / TXT / images) | âœ… Working |
| Docker Compose (frontend + backend + postgres) | âœ… Working |

---

## ðŸ“ Project Structure

```
IP-SAKTI/
â”œâ”€â”€ frontend/                    # Next.js 14 App Router
â”‚   â”œâ”€â”€ src/
â”‚   â”‚   â”œâ”€â”€ app/                 # Pages (dashboard, login)
â”‚   â”‚   â”œâ”€â”€ components/          # UI components
â”‚   â”‚   â”œâ”€â”€ lib/                 # API clients, auth, i18n
â”‚   â”‚   â””â”€â”€ types/               # TypeScript types
â”‚   â””â”€â”€ package.json
â”‚
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ api/v1/              # All API route handlers
â”‚   â”‚   â”œâ”€â”€ auth/                # JWT + password hashing
â”‚   â”‚   â”œâ”€â”€ rag/                 # FAISS index & retriever
â”‚   â”‚   â”œâ”€â”€ models/              # Pydantic + SQLAlchemy models
â”‚   â”‚   â”œâ”€â”€ services/            # Business logic engines
â”‚   â”‚   â”œâ”€â”€ knowledge/           # Ayurveda datasets (JSON)
â”‚   â”‚   â””â”€â”€ main.py              # FastAPI entrypoint
â”‚   â”œâ”€â”€ data/                    # RAG source documents
â”‚   â”œâ”€â”€ scripts/                 # build_faiss.py
â”‚   â”œâ”€â”€ exports/                 # Generated dossiers
â”‚   â”œâ”€â”€ uploads/                 # Uploaded documents
â”‚   â””â”€â”€ requirements.txt
â”‚
â”œâ”€â”€ docker-compose.yml           # frontend + backend + postgres
â”œâ”€â”€ .env.example
â””â”€â”€ README.md
```

---

## ðŸš€ Quick Start (VS Code)

### Prerequisites
- Node.js 18+
- Python 3.11+
- (Optional) PostgreSQL 15 â€” *falls back to SQLite automatically*

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows (PowerShell)
pip install -r requirements.txt
python scripts/build_faiss.py   # Build RAG index
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000` Â· Swagger at `http://localhost:8000/api/v1/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:3000`

---

## ðŸ³ Docker

```bash
docker compose up --build
```

Services:
- `postgres` â€” PostgreSQL 15 (`ipsakti` / `ipsakti_secret`)
- `backend` â€” FastAPI on `:8000`
- `frontend` â€” Next.js on `:3000`

To rebuild the RAG index inside the container:
```bash
docker compose exec backend python scripts/build_faiss.py
```

---

## ðŸ” Environment Variables

### Backend (`backend/.env`)
```
DATABASE_URL=postgresql://ipsakti:ipsakti_secret@localhost:5432/ipsakti
SECRET_KEY=your_jwt_secret_here
BACKEND_API_KEY_SECRET=your_api_secret_here
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

---

## ðŸ“¡ API Reference

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/signup` | Create account |
| `POST /api/v1/auth/login` | Login, returns JWT |
| `GET /api/v1/auth/profile` | Current user profile |
| `POST /api/v1/passport/create` | Create Innovation Passport |
| `POST /api/v1/passport/{id}/update` | Update passport |
| `POST /api/v1/formulation/parse` | Parse multilingual formulation |
| `POST /api/v1/botanical/canonicalize` | Map to API botanical name |
| `POST /api/v1/chat/query` | AI Copilot (RAG answer + sources) |
| `GET /api/v1/chat/suggested-questions` | Suggested copilot questions |
| `POST /api/v1/fto/check` | Freedom-to-Operate analysis |
| `POST /api/v1/label/analyze` | Claim Firewall / label analysis |
| `GET /api/v1/analysis/readiness/{id}` | Patent readiness scores |
| `GET /api/v1/roadmap/{id}` | Regulatory roadmap |
| `POST /api/v1/export/dossier` | Generate exportable dossier |
| `POST /api/v1/upload/disclosure-check` | Upload & scan documents |
| `POST /api/v1/assessment/evaluate` | Regulatory assessment |
| `POST /api/v1/what-if/simulate` | Claim mutation simulation |
| `GET /api/v1/evidence/{id}` | Evidence gaps summary |

Full interactive docs: `http://localhost:8000/api/v1/docs`

---

## ðŸ§¬ RAG Pipeline

1. **Load** documents from `backend/data/{pharmacopoeia,ayurveda,regulations,patents,pubmed,who}`
2. **Chunk** â€” 800 tokens with 150-token overlap, metadata stored
3. **Embed** â€” `BAAI/bge-base-en-v1.5` via Sentence Transformers
4. **Index** â€” FAISS flat index saved to `app/rag/faiss_index/`
5. **Retrieve** â€” top-5 relevant chunks per query
6. **Generate** â€” LLM answers grounded only in retrieved context (never hallucinates)

Re-build the index after adding data:
```bash
cd backend
python scripts/build_faiss.py
```

---

## ðŸŒ Multilingual Pipeline

```
User input (à¤¹à¤³à¤¦, à¤¨à¥€à¤®, à¤¤à¥à¤³à¤¸)
        â†“
Language Detection (Devanagari â†’ hi/mr, Tamil â†’ ta, ...)
        â†“
Botanical Canonicalization â†’ Curcuma longa, Azadirachta indica...
        â†“
RAG Retrieval against Ayurvedic Pharmacopoeia & classical texts
        â†“
LLM Answer + Cited Sources
```

Supported: English, à¤¹à¤¿à¤¨à¥à¤¦à¥€ (hi), à¤®à¤°à¤¾à¤ à¥€ (mr), à®¤à®®à®¿à®´à¯ (ta), à°¤à±†à°²à±à°—à± (te), à²•à²¨à³à²¨à²¡ (kn), à¦¬à¦¾à¦‚à¦²à¦¾ (bn), àª—à«àªœàª°àª¾àª¤à«€ (gu), à´®à´²à´¯à´¾à´³à´‚ (ml), à¤¸à¤‚à¤¸à¥à¤•à¥ƒà¤¤à¤®à¥ (sa).

---

## ðŸ›  Troubleshooting

**Backend won't start (database error)**
- PostgreSQL unavailable â†’ app auto-falls back to SQLite (`ipsakti.db`)
- Or set `DATABASE_URL=sqlite:///./ipsakti.db`

**FAISS / embeddings install fails**
- Ensure Python 3.11 Ã— 64-bit. On Windows try `pip install faiss-cpu sentence-transformers`
- The app degrades to keyword retrieval if FAISS isn't installed

**Frontend can't reach backend**
- Check `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`
- Restart backend with `uvicorn app.main:app --reload`

**Port already in use**
- Backend: `uvicorn app.main:app --port 8001`
- Frontend: `npm run dev -- -p 3001`

---

## ðŸŽ¯ Demo Flow

1. Open `http://localhost:3000` â†’ **Create Account** (or use demo credentials)
2. Dashboard shows Overview cards (Passport, Patent Readiness, Evidence, Next Action)
3. Fill the **Innovation Passport** 4-step form (basic info â†’ multilingual formulation â†’ process â†’ claims)
4. View **Patent Analysis** scores, **Evidence Matrix**, and chat with **AI Copilot**
5. Run **Claim Firewall** on your label copy, then **export the dossier**

---

## âš–ï¸ Compliance

- **DPDP Act 2023** â€” consent logging (`DPDPConsentLogger`)
- **AI citation grounding** â€” every answer shows retrieved sources + confidence
- **Grievance officer** â€” grievance@ipsakti.in
- **Data residency** â€” ap-south-1 (Mumbai, India)

For informational purposes only â€” not legal advice. Consult qualified patent agents and regulatory specialists for final decisions.

---

## ðŸ§  Unified RAG Architectures (Hybrid / Production / Graph / Agentic)

The knowledge layer exposes four selectable RAG architectures behind one
unified interface (`backend/app/services/rag/`), all wrapping the existing
production hybrid pipeline (no legacy code rewritten):

| Architecture | What it adds over the core hybrid pipeline |
|---|---|
| `hybrid` | Qdrant dense + BM25 + statutory -> RRF -> BGE cross-encoder rerank (default) |
| `production` | Result caching + per-user rate limit + query/cost logging (Redis opt-in, in-memory fallback) |
| `graph` | Local knowledge graph entity traversal fused with hybrid results (optional Neo4j) |
| `agentic` | Parallel Patent / Regulatory / ABS / TKDL specialist agents + intent routing |

**Endpoints** (all backward-compatible; `/rag/ask` is untouched):

- `POST /rag/search` — unified search, select via `rag_type: hybrid|production|graph|agentic`
- `GET /rag/search/stats` — per-architecture health + metrics
- `POST /rag/configure` — set default `rag_type`, `cache_ttl`, `rate_limit` at runtime

**Environment** (optional, see `backend/.env.example`):

- `IPSAKTI_RAG_DEFAULT` — default architecture when `rag_type` is omitted
- `IPSAKTI_RAG_CACHE_TTL`, `IPSAKTI_RAG_RATE_LIMIT` — production caching/limits
- `REDIS_URL` — enables Redis cache + rate limiting (in-memory fallbacks otherwise)
- `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` — optional Neo4j graph traversal

**Frontend:** the AI Copilot has an *Engine* selector row above its input
(AI Copilot / RAG Hybrid / RAG Production / RAG Graph / RAG Agentic) that
persists the choice per browser and shows live latency/count/confidence
metrics on each RAG reply.