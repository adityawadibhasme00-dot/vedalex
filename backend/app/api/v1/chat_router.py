import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_optional_user
from app.core.async_bridge import run_sync
from app.core.database import get_db
from app.models.db_models import ChatHistory, User
from app.services.multi_layer_orchestrator import MultiLayerOrchestrator
from app.services.privacy_service import QueryAuditLog, hash_audit_token, scrub_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["AI Copilot"])

class ChatRequest(BaseModel):
    question: str
    passport_id: str | None = None
    context: dict[str, Any] | None = None
    # Explicit opt-in to persist the full question/answer text for the session.
    consent_record: bool = False

class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    confidence: float
    question: str
    charts: list[dict[str, Any]] = []
    images: list[str] = []
    intent: dict[str, str] | None = None
    analysis_card: dict[str, Any] | None = None
    evidence_used: list[dict[str, str]] | None = None
    next_actions: list[str] | None = None
    jurisdiction: dict[str, Any] | None = None
    decision_trace: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    detected_language: str | None = None
    response_sections: dict[str, Any] | None = None
    product_classification: dict[str, Any] | None = None
    product_classification_bilingual: dict[str, Any] | None = None
    escalation: dict[str, Any] | None = None
    audit: dict[str, Any] | None = None

@router.post("/query", response_model=ChatResponse)
async def chat_query(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
):
    from app.agents.input_defenses import defend_query

    # Security B1+B2: sanitised before the question reaches the orchestrator
    # or any LLM; the audit trail hashes the sanitised form as well.
    question = defend_query(req.question)["query"]
    # The orchestrator is synchronous and LLM/RAG-bound (25-45s worst case).
    # Run it on a worker thread so the event loop keeps serving other requests.
    result = await run_sync(
        MultiLayerOrchestrator.run, question, req.passport_id, req.context
    )

    # Privacy-preserving audit + persistence:
    #  - Full text persisted ONLY on explicit consent (consent_record=true).
    #  - The audit trail stores hashed query/answer + source/citation IDs,
    #    never raw formulation details, to keep logs privacy-preserving.
    result["audit"] = {}
    if req.consent_record and current_user:
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=scrub_text(question),
            response=scrub_text(result["answer"]),
            sources=result["sources"],
            confidence=result["confidence"],
            consent_record=True,
            query_hash=hash_audit_token(question),
        )
        db.add(chat_entry)
        db.commit()
        result["audit"] = {
            "persisted": True,
            "stored_full_record": True,
            "query_scrubbed": scrub_text(question) != question,
        }

    citation_ids = []
    for src in result.get("sources", []) or []:
        for key in ("citation_id", "source_id", "id"):
            val = src.get(key)
            if val:
                citation_ids.append(str(val))
                break
    source_ids = [str(s.get("source_id", s.get("id", ""))) for s in result.get("sources", []) or []]
    audit_entry = QueryAuditLog.record(
        query_hash=hash_audit_token(question),
        answer_hash=hash_audit_token(result["answer"]),
        source_ids=source_ids,
        citation_ids=citation_ids,
        jurisdiction=(result.get("jurisdiction") or {}).get("detected")
            if isinstance(result.get("jurisdiction"), dict) else None,
        confidence=result.get("confidence"),
        language=result.get("detected_language"),
        user_id=str(current_user.id) if current_user else None,
        opt_in_store=bool(req.consent_record),
    )
    try:
        from app.services.audit_chain import record_event

        record_event(
            db,
            "chat.query",
            {
                "query_hash": audit_entry["query_hash"],
                "answer_hash": audit_entry["answer_hash"],
                "confidence": result.get("confidence"),
                "consent": bool(req.consent_record),
                "source_count": len(source_ids),
            },
            actor_id=str(current_user.id) if current_user else None,
        )
    except Exception:  # noqa: BLE001 — audit must never break the answer path
        logger.warning("audit chain record failed", exc_info=True)
    result["audit"].update({
        "query_hash": audit_entry["query_hash"],
        "citation_ids": citation_ids,
        "audit_id": id(audit_entry),
    })
    if req.consent_record and "persisted" not in result["audit"]:
        result["audit"]["persisted"] = False

    return ChatResponse(**result)

@router.get("/audit-trail")
def get_audit_trail(limit: int = 50):
    """Privacy-preserving audit trail: query/answer hashes and source/citation
    IDs only. Raw query text is never returned."""
    return {"entries": QueryAuditLog.get_trail(limit)}

SUGGESTED_QUESTIONS = [
    "Can I patent this Ayurvedic formulation?",
    "Is Neem already patented?",
    "Is my product label compliant?",
    "What evidence is missing for regulatory approval?",
    "What are the requirements for FSSAI Ayurveda Aahara?",
    "How do I comply with DSHEA in the US market?",
    "What is Section 3(p) and how does it affect my patent?",
    "Do I need NBA clearance for my formulation?",
]

@router.get("/suggested-questions")
def get_suggested_questions():
    return {"questions": SUGGESTED_QUESTIONS}
