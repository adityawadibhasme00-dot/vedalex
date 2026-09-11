# IP-SAKTI Sahayak

**Ayurveda IP & Regulatory Decision Engine** — A multilingual, RAG-based (source-cited) AI assistant guiding Ayurveda researchers, startups, students, MSMEs, and patent professionals from *Idea → Innovation Passport → Patent Analysis → Compliance → Commercialization*.

Production-grade — runs locally in VS Code, deployed via Docker.

---

## ✨ Core Features

| Feature | Status |
|---|---|
| Next.js 15 Frontend (App Router, TypeScript, Tailwind) | ✅ Working |
| FastAPI Backend with Swagger docs | ✅ Working |
| JWT Authentication (Signup / Login / Profile) | ✅ Working |
| PostgreSQL + SQLite fallback (SQLAlchemy) | ✅ Working |
| FAISS RAG pipeline (BGE embeddings) | ✅ Working |
| Multilingual formulation input (10 languages) | ✅ Working |
| Botanical canonicalization (हळद → Curcuma longa) | ✅ Working |
| Innovation Passport (4-section w/ QR) | ✅ Working |
| Patent Readiness (Novelty / Inventive Step / Overall) | ✅ Working |
| Evidence Matrix (color-coded, upload) | ✅ Working |
| AI Copilot (RAG-grounded with sources + confidence) | ✅ Working |
| Claim Firewall (label analysis) | ✅ Working |
| FTO Check (Google/WIPO patent metadata simulation) | ✅ Working |
| Regulatory Roadmap (6-phase timeline) | ✅ Working |
| Dossier Export (HTML report w/ QR, Patent Score, Evidence) | ✅ Working |
| Document upload (PDF / DOCX / TXT / images) | ✅ Working |
| Docker Compose (frontend + backend + postgres) | ✅ Working |

---

## 📁 Project Structure

```
IP-SAKTI/
├── frontend/                    # Next.js 15 App Router
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
│   │   ├── rag/                 # FAISS index & retriever
│   │   ├── models/              # Pydantic + SQLAlchemy models
│   │   ├── services/            # Business logic engines
│   │   ├── knowledge/           # Ayurveda datasets (JSON)
│   │   └── main.py              # FastAPI entrypoint
│   ├── data/                    # RAG source documents
│   ├── scripts/                 # build_faiss.py
│   ├── exports/                 # Generated dossiers
│   ├── uploads/                 # Uploaded documents
│   └── requirements.txt
│
├── docker-compose.yml           # frontend + backend + postgres
├── .env.example
└── README.md
```

---

## 🚀 Quick Start (VS Code)

### Prerequisites
- Node.js 18+
- Python 3.11+
- (Optional) PostgreSQL 15 — *falls back to SQLite automatically*

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows (PowerShell)
pip install -r requirements.txt
python scripts/build_faiss.py   # Build RAG index
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000` · Swagger at `http://localhost:8000/api/v1/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:3000`

---

## 🐳 Docker

```bash
docker compose up --build
```

Services:
- `postgres` — PostgreSQL 15 (`ipsakti` / `ipsakti_secret`)
- `backend` — FastAPI on `:8000`
- `frontend` — Next.js on `:3000`

To rebuild the RAG index inside the container:
```bash
docker compose exec backend python scripts/build_faiss.py
```

---

## 🔐 Environment Variables

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

## 📡 API Reference

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

## 🧬 RAG Pipeline

1. **Load** documents from `backend/data/{pharmacopoeia,ayurveda,regulations,patents,pubmed,who}`
2. **Chunk** — 800 tokens with 150-token overlap, metadata stored
3. **Embed** — `BAAI/bge-base-en-v1.5` via Sentence Transformers
4. **Index** — FAISS flat index saved to `app/rag/faiss_index/`
5. **Retrieve** — top-5 relevant chunks per query
6. **Generate** — LLM answers grounded only in retrieved context (never hallucinates)

Re-build the index after adding data:
```bash
cd backend
python scripts/build_faiss.py
```

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
- Or set `DATABASE_URL=sqlite:///./ipsakti.db`

**FAISS / embeddings install fails**
- Ensure Python 3.11 × 64-bit. On Windows try `pip install faiss-cpu sentence-transformers`
- The app degrades to keyword retrieval if FAISS isn't installed

**Frontend can't reach backend**
- Check `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`
- Restart backend with `uvicorn app.main:app --reload`

**Port already in use**
- Backend: `uvicorn app.main:app --port 8001`
- Frontend: `npm run dev -- -p 3001`

---

## 🎯 Demo Flow

1. Open `http://localhost:3000` → **Create Account** (or use demo credentials)
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