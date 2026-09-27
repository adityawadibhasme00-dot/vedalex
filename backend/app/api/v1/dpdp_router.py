"""B3 + B4 + B5 — DPDP compliance endpoints.

    GET  /api/v1/dpdp/notice            - consent notice, rights, grievance
    GET  /api/v1/dpdp/audit-chain/verify - admin: verify the hash chain
    POST /api/v1/dpdp/purge-retention   - admin: run the 90-day retention purge
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.core.database import get_db
from app.models.db_models import User
from app.services import dpdp_service
from app.services.audit_chain import chain_head, record_event, verify_chain

router = APIRouter(prefix="/dpdp", tags=["DPDP Compliance"])

require_admin = require_role("admin")


@router.get("/notice")
def consent_notice() -> dict[str, Any]:
    """DPDP consent notice, data rights, grievance officer, retention."""
    return dpdp_service.notice_payload()


@router.get("/audit-chain/verify")
def audit_chain_verify(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Recompute the tamper-evident audit chain (admin only)."""
    result = verify_chain(db)
    result["head"] = chain_head(db)
    result["requested_by_role"] = "admin"
    return result


@router.post("/purge-retention")
def purge_retention(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Apply the DPDP retention policy (admin only) and audit the run."""
    removed = dpdp_service.purge_expired(db)
    record_event(
        db,
        "dpdp.purge_retention",
        {"removed_records": removed, "retention_days": dpdp_service.settings.DPDP_RETENTION_DAYS},
        actor_id=str(current_user.id),
    )
    return {
        "removed_records": removed,
        "retention_days": dpdp_service.settings.DPDP_RETENTION_DAYS,
    }
