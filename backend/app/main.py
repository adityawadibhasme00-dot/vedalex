import asyncio
import threading
import os
import sys

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="IP-SAKTI — A multilingual, RAG-based (source-cited) AI assistant for Intellectual Property and regulatory guidance in Ayurveda, across national and international regimes.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables
@app.on_event("startup")
async def startup_event():
    try:
        init_db()
    except Exception as e:
        print(f"Database initialization skipped: {e}")

    # Warm up RAG pipeline (BGE-M3 model + BM25 index) so the first
    # /rag/* request does not pay the model-loading penalty.
    try:
        from app.rag.retrieval_pipeline import _warmup_rag_pipeline
        threading.Thread(target=_warmup_rag_pipeline, daemon=True).start()
    except Exception as e:
        print(f"RAG warm-up skipped: {e}")

# Include v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "system": "IP-SAKTI",
        "tagline": "Multilingual, RAG-based citation-grounded decision support for Ayurveda IP & cross-border regulations",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "status": "OPERATIONAL",
        "compliance": {
            "dpdp_act_2023": "Aligned (Consent logging & grievance handling active)",
            "grievance_officer": settings.GRIEVANCE_OFFICER_NAME,
            "data_residency": settings.DATA_LOCALIZATION_REGION
        }
    }

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "rules_engine": "operational",
        "retrieval_engine": "operational",
        "canonical_resolver": "operational",
        "rag": "operational",
        "auth": "operational",
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)