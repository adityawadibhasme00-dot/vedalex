from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.rag.faiss_retriever import FAISSIndex
from app.rag.kb import (
    blueprint_path,
    collect_knowledge_documents,
    ensure_kb_layout,
    list_reference_links,
    official_dir,
)
from app.services.ai_copilot import AICopilot

router = APIRouter(prefix="/admin", tags=["Knowledge Base Admin"])

class ReindexRequest(BaseModel):
    api_key: str

class ReindexResponse(BaseModel):
    status: str
    indexed_chunks: int
    embeddings: str
    kb_root: str
    reference_links: list[dict[str, str]]
    statutory_passages: int = 0
    blueprint_present: bool = False

class KnowledgeStatus(BaseModel):
    status: str
    kb_root: str
    folders: list[str]
    reference_links: list[dict[str, str]]
    index_size: int
    index_present: bool
    blueprint_present: bool = False
    official_dir: str = ""
    corpus_version: str | None = None
    manifest_present: bool = False
    treaties_available: int = 0
    india_code_acts: int = 0
    india_code_api_live: bool = False

class IndiaCodeHarvestRequest(BaseModel):
    api_key: str
    act_ids: list[str] | None = None
    force: bool = False

class IndiaCodeHarvestResponse(BaseModel):
    status: str
    acts: list[str]
    total_chunks: int
    results: list[dict[str, Any]]

class LawSentinelRunRequest(BaseModel):
    api_key: str
    source_ids: list[str] | None = None

class LawSentinelRunResponse(BaseModel):
    status: str
    ran_at: str
    watched: list[str]
    first_seen: list[str]
    unchanged: list[str]
    changed: list[str]
    errors: list[dict[str, str]]

@router.post("/reindex", response_model=ReindexResponse)
def reindex_knowledge_base(req: ReindexRequest):
    from app.core.config import settings

    if req.api_key != settings.BACKEND_API_KEY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")

    from app.services.retrieval_engine import HybridRetrievalEngine
    HybridRetrievalEngine.load_database()
    statutory_passages = len(HybridRetrievalEngine._passages_db)

    docs = collect_knowledge_documents()
    index = FAISSIndex()
    index.build(docs)
    AICopilot.reset_index()

    from app.services.corpus_manifest import build_manifest
    build_manifest()

    return ReindexResponse(
        status="ok",
        indexed_chunks=len(docs),
        embeddings="hashing-fallback" if index.model is None else "sentence-transformers",
        kb_root=ensure_kb_layout(),
        reference_links=list_reference_links(),
        statutory_passages=statutory_passages,
        blueprint_present=bool(blueprint_path()),
    )

@router.get("/status", response_model=KnowledgeStatus)
def knowledge_base_status():
    import json as _json
    import os

    from app.rag.kb import KB_SUBFOLDERS
    from app.services.corpus_manifest import get_corpus_status
    from app.services.indiacode_client import india_code_status as ic_status

    manifest = get_corpus_status()
    ic = ic_status()
    treaties_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge", "treaties_metadata.json")
    treaties_count = 0
    if os.path.exists(treaties_file):
        try:
            with open(treaties_file, encoding="utf-8") as fh:
                treaties_count = len(_json.load(fh).get("treaties", []))
        except Exception:
            treaties_count = 0

    root = ensure_kb_layout()
    index_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "rag", "faiss_index", "index.faiss")
    index_present = os.path.exists(index_path)
    size = 0
    if index_present:
        try:
            import pickle
            with open(os.path.join(os.path.dirname(index_path), "metadata.pkl"), "rb") as f:
                size = len(pickle.load(f))
        except Exception:
            size = 0

    return KnowledgeStatus(
        status="ok",
        kb_root=root,
        folders=KB_SUBFOLDERS,
        reference_links=list_reference_links(),
        index_size=size,
        index_present=index_present,
        blueprint_present=bool(blueprint_path()),
        official_dir=official_dir(),
        corpus_version=manifest.get("corpus_version"),
        manifest_present=bool(manifest.get("manifest_present")),
        treaties_available=treaties_count,
        india_code_acts=len(ic.get("tracked_acts", [])),
        india_code_api_live=bool(ic.get("api_responsive")),
    )

@router.post("/harvest/indiacode", response_model=IndiaCodeHarvestResponse)
def harvest_indiacode(req: IndiaCodeHarvestRequest):
    from app.core.config import settings

    if req.api_key != settings.BACKEND_API_KEY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")

    from app.services.indiacode_harvester import harvest_indiacode as run_harvest
    summary = run_harvest(act_ids=req.act_ids, force=req.force)
    return IndiaCodeHarvestResponse(
        status=summary.get("status", "ok"),
        acts=summary.get("acts", []),
        total_chunks=summary.get("total_chunks", 0),
        results=summary.get("results", []),
    )

@router.get("/law-sentinel")
def law_sentinel_status(db: Session = Depends(get_db)):
    """A1 Law-Change Sentinel: staleness state of every watched statute."""
    from app.services.law_sentinel import sentinel_status

    return {"sources": sentinel_status(db)}

@router.post("/law-sentinel/run", response_model=LawSentinelRunResponse)
def law_sentinel_run(req: LawSentinelRunRequest, db: Session = Depends(get_db)):
    """Run one sentinel cycle (fetch → hash diff → stale flag)."""
    from app.core.config import settings

    if req.api_key != settings.BACKEND_API_KEY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")

    from app.services.law_sentinel import run_sentinel

    summary = run_sentinel(db, source_ids=req.source_ids)
    return LawSentinelRunResponse(
        status="ok",
        ran_at=summary["ran_at"],
        watched=summary["watched"],
        first_seen=summary["first_seen"],
        unchanged=summary["unchanged"],
        changed=summary["changed"],
        errors=summary["errors"],
    )