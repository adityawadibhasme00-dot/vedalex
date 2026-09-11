from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.rag.faiss_retriever import FAISSIndex
from app.rag.kb import collect_knowledge_documents, ensure_kb_layout, list_reference_links, blueprint_path, official_dir
from app.services.ai_copilot import AICopilot

router = APIRouter(prefix="/admin", tags=["Knowledge Base Admin"])

class ReindexRequest(BaseModel):
    api_key: str

class ReindexResponse(BaseModel):
    status: str
    indexed_chunks: int
    embeddings: str
    kb_root: str
    reference_links: List[Dict[str, str]]
    statutory_passages: int = 0
    blueprint_present: bool = False

class KnowledgeStatus(BaseModel):
    status: str
    kb_root: str
    folders: List[str]
    reference_links: List[Dict[str, str]]
    index_size: int
    index_present: bool
    blueprint_present: bool = False
    official_dir: str = ""

@router.post("/reindex", response_model=ReindexResponse)
async def reindex_knowledge_base(req: ReindexRequest):
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
async def knowledge_base_status():
    from app.rag.kb import KB_SUBFOLDERS
    import os

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
    )