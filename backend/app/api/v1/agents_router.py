"""Agentic chat endpoint — Master Prompt v7.0.0.

Exposes the full 12-component agentic RAG chain
(``app.agents.chain.AgenticChain``) as a single POST route without touching
the existing ``/rag/ask`` or ``/chat/*`` flows:

    POST /api/v1/agents/agentic-chat
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.chain import AgenticChain
from app.auth.jwt_auth import get_optional_user
from app.core.database import get_db
from app.models.db_models import User
from app.services.privacy_service import hash_audit_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

_chain: AgenticChain | None = None


def get_chain() -> AgenticChain:
    """Process-wide chain instance (components are stateless)."""
    global _chain
    if _chain is None:
        _chain = AgenticChain()
    return _chain


class AgenticChatRequest(BaseModel):
    """Request body for the agentic chat endpoint."""

    query: str = Field(
        min_length=3,
        max_length=2000,
        description="User question for the Ayurveda IPR assistant.",
    )
    jurisdiction: str = Field(
        default="india",
        pattern="^(india|international|both|India|International|Both)$",
        description="Jurisdiction toggle — never mixes India/International.",
    )
    top_k: int = Field(default=5, ge=1, le=10)


@router.post("/agentic-chat")
def agentic_chat(
    req: AgenticChatRequest,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Run the complete agentic pipeline for one query.

    Enhanced with:
    - Parallel claim verification
    - Contradiction severity scoring
    - Source attribution verification
    - Response caching
    """
    try:
        out = get_chain().execute(
            req.query.strip(),
            jurisdiction=req.jurisdiction.lower(),
            top_k=req.top_k,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — boundary: never leak internals
        raise HTTPException(
            status_code=500, detail="Agentic pipeline execution failed"
        ) from exc
    try:
        from app.services.audit_chain import record_event

        defense = out.get("input_defense") or {}
        record_event(
            db,
            "agentic.query",
            {
                "query_hash": hash_audit_token(str(defense.get("query") or req.query)),
                "status": out.get("status"),
                "confidence": out.get("confidence"),
                "jurisdiction": out.get("jurisdiction"),
                "pii_redacted": defense.get("pii_redacted") or {},
                "injections_neutralized": defense.get("injections_neutralized") or [],
            },
            actor_id=str(current_user.id) if current_user else None,
        )
    except Exception:  # noqa: BLE001 — audit must never break the answer path
        logger.warning("audit chain record failed", exc_info=True)
    return out


@router.get("/components")
def agentic_components(
    current_user: User | None = Depends(get_optional_user),
) -> dict[str, Any]:
    """List the linked components of the agentic graph."""
    del current_user  # optional auth — same contract as /chat/query
    return {
        "components": AgenticChain.component_names(),
        "count": len(AgenticChain.component_names()),
    }
