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
    # Self-abstention contract: True whenever the response is a refusal rather
    # than a sourced answer. The UI must never render a refusal as if it were
    # grounded, so this flag is derived server-side on every response.
    abstained: bool = False
    abstention_reason: str | None = None

# Confidence at or below which a response is treated as an abstention rather
# than an answer. Matches the orchestrator's own low-confidence gate.
ABSTAIN_CONFIDENCE = 0.35

PIPELINE_FAILURE_ANSWER = (
    "The IP-SAKTI copilot could not complete this query because a retrieval "
    "service failed. No answer was generated and no sources are cited. "
    "Please retry, or narrow the question to a specific statute, ingredient or "
    "regulator."
)


def _abstention(
    question: str,
    reason: str,
    message: str,
    intent: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build an honest no-answer payload.

    The pipeline failed, so nothing about the corpus can be asserted — not even
    that evidence is missing. The message says the query could not be served and
    cites nothing, instead of guessing a cause.
    """
    return {
        "question": question,
        "answer": message,
        "sources": [],
        "confidence": 0.0,
        "images": [],
        "intent": intent,
        "abstained": True,
        "abstention_reason": reason,
        "analysis_card": {"verification_badge": "Unable to answer"},
        "response_sections": {
            "direct_answer": message,
            "clarification_needed": False,
            "official_sources_used": [],
            "confidence": 0,
            "next_recommended_action": "Retry the question, or ask an IP facilitator.",
            "why_it_matters": (
                "No source was retrieved or cited, so nothing in this reply is "
                "backed by the official record."
            ),
        },
        "audit": {},
    }


def _mark_abstained(result: dict[str, Any], reason: str) -> None:
    """Record a refusal and strip the evidence that never supported an answer.

    Clearing sources and confidence is what keeps the contract honest: a reply
    flagged as a refusal must not also advertise citations, or the client
    renders "no answer given" above a list of sources the user will read as
    backing for a claim that was not made.
    """
    result["abstained"] = True
    result["abstention_reason"] = reason
    result["sources"] = []
    result["confidence"] = 0.0
    sections = result.get("response_sections")
    if isinstance(sections, dict):
        sections["official_sources_used"] = []


def _derive_abstention(result: dict[str, Any], no_evidence_answer: str) -> None:
    """Flag refusals in place so the client can never mistake one for an answer."""
    # Read the incoming verdict before defaulting it, and always leave the
    # payload well-formed so both flags are present on every response.
    already_refusal = bool(result.get("abstained"))
    reason = result.get("abstention_reason")
    result["abstained"] = False
    result["abstention_reason"] = None
    if already_refusal:
        # Already a refusal (the orchestrator decided so) — still normalise it,
        # so the no-citations invariant holds for every refusal path.
        _mark_abstained(result, str(reason or "declined to answer"))
        return
    answer = str(result.get("answer") or "")
    marker = no_evidence_answer.split(".")[0]
    sections = result.get("response_sections")
    sections = sections if isinstance(sections, dict) else {}
    # Order matters: the reason is shown to the user, so the most specific
    # cause has to win. A clarification carries low confidence by design and
    # would otherwise be mislabelled as weak evidence.
    if sections.get("clarification_needed"):
        _mark_abstained(result, "jurisdiction clarification required")
    elif not answer or answer.startswith(no_evidence_answer) or marker in answer:
        _mark_abstained(result, "no supporting evidence in the indexed corpus")
    elif float(result.get("confidence") or 0.0) < ABSTAIN_CONFIDENCE:
        _mark_abstained(result, "retrieved evidence was too weak to support an answer")

@router.post("/query", response_model=ChatResponse)
async def chat_query(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
):
    from app.agents.input_defenses import defend_query
    from app.services.ai_copilot import NO_EVIDENCE_ANSWER

    # Security B1+B2: sanitised before the question reaches the orchestrator
    # or any LLM; the audit trail hashes the sanitised form as well.
    question = defend_query(req.question)["query"]
    # The orchestrator is synchronous and LLM/RAG-bound (25-45s worst case).
    # Run it on a worker thread so the event loop keeps serving other requests.
    #
    # Any internal failure is converted into an explicit no-answer response
    # instead of a 500: a broken retrieval service must never surface to the
    # user as a generic "backend error", and it must never be papered over with
    # a generated answer.
    try:
        result = await run_sync(
            MultiLayerOrchestrator.run, question, req.passport_id, req.context
        )
    except Exception:  # noqa: BLE001 — the answer path must not 500
        logger.exception(
            "copilot pipeline failed (question_hash=%s)", hash_audit_token(question)
        )
        result = _abstention(
            question, "retrieval pipeline failure", PIPELINE_FAILURE_ANSWER
        )

    # Normalise/validate against the response schema. A payload that does not
    # fit the contract is not trustworthy enough to show, so it degrades to a
    # no-answer response instead of raising a 500 from the serialiser.
    try:
        result = ChatResponse.model_validate(result).model_dump()
    except Exception:  # noqa: BLE001
        logger.exception(
            "copilot response failed schema validation (question_hash=%s)",
            hash_audit_token(question),
        )
        result = _abstention(
            question, "malformed orchestrator response", PIPELINE_FAILURE_ANSWER
        )

    _derive_abstention(result, NO_EVIDENCE_ANSWER)

    # ``audit`` is an optional field on the schema, so it serialises to None
    # unless the orchestrator set it. Normalise it before the bookkeeping below
    # writes into it.
    if not isinstance(result.get("audit"), dict):
        result["audit"] = {}

    # Privacy-preserving audit + persistence:
    #  - Full text persisted ONLY on explicit consent (consent_record=true).
    #  - The audit trail stores hashed query/answer + source/citation IDs,
    #    never raw formulation details, to keep logs privacy-preserving.
    if req.consent_record and current_user:
        try:
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
            result["audit"].update({
                "persisted": True,
                "stored_full_record": True,
                "query_scrubbed": scrub_text(question) != question,
            })
        except Exception:  # noqa: BLE001 — persistence must not lose the answer
            db.rollback()
            logger.exception("chat history persistence failed")

    citation_ids = []
    for src in result.get("sources", []) or []:
        for key in ("citation_id", "source_id", "id"):
            val = src.get(key)
            if val:
                citation_ids.append(str(val))
                break
    source_ids = [str(s.get("source_id", s.get("id", ""))) for s in result.get("sources", []) or []]
    # Audit bookkeeping is best-effort: it must never turn a served answer into
    # a failed request.
    try:
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
    except Exception:  # noqa: BLE001
        logger.warning("query audit log failed", exc_info=True)
        # Fall back to the hashes we can still compute. The audit-chain record
        # below reads both keys, so an incomplete stub would silently drop the
        # privacy-preserving event instead of degrading to a reduced one.
        audit_entry = {
            "query_hash": hash_audit_token(question),
            "answer_hash": hash_audit_token(result["answer"]),
        }
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
