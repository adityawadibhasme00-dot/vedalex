"""B3 — DPDP Act compliance pack: consent notice, retention, grievance.

Grounded on existing config (``GRIEVANCE_OFFICER_*``,
``DATA_LOCALIZATION_REGION``) and the ``chat_history.retention_until``
column; adds the retention purge and the user-facing notice payload.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.audit_chain import purge_expired_chat

CONSENT_NOTICE = (
    "IP-SAKTI processes your query solely to answer your Ayurveda IPR "
    "question. Under the DPDP Act 2023 you have the right to access, "
    "correct and erase your personal data, to withdraw consent at any time, "
    "and to grievance redressal within 30 days. Queries are redacted of "
    "identifiers (Aadhaar, phone, email, GSTIN) before processing, audit "
    "logs store only one-way hashes, and full chat text is persisted only "
    "when you explicitly opt in. Records are retained for at most "
    f"{settings.DPDP_RETENTION_DAYS} days. Data is stored in India "
    f"({settings.DATA_LOCALIZATION_REGION})."
)

DATA_RIGHTS: tuple[str, ...] = (
    "access",
    "correction",
    "erasure",
    "withdraw_consent",
    "grievance_redressal",
)


def notice_payload() -> dict[str, Any]:
    """Public DPDP notice: consent text, rights, grievance, retention, region."""
    return {
        "consent_notice": CONSENT_NOTICE,
        "rights": list(DATA_RIGHTS),
        "retention_days": settings.DPDP_RETENTION_DAYS,
        "data_residency": settings.DATA_LOCALIZATION_REGION,
        "grievance_officer": {
            "name": settings.GRIEVANCE_OFFICER_NAME,
            "email": settings.GRIEVANCE_OFFICER_EMAIL,
            "response_sla_days": 30,
        },
        "persist_full_text_only_with_consent": True,
        "pii_redacted_before_llm": True,
    }


def purge_expired(db: Session, retention_days: int | None = None) -> int:
    """Delete chat records past the DPDP retention deadline; returns count."""
    days = retention_days if retention_days is not None else settings.DPDP_RETENTION_DAYS
    return purge_expired_chat(db, retention_days=days)


def retention_deadline(from_ts: datetime | None = None) -> datetime:
    """Timestamp until which a record created now may be kept."""
    base = from_ts or datetime.now(UTC)
    return base + timedelta(days=settings.DPDP_RETENTION_DAYS)
