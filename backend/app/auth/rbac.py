"""B5 — role-based access control (RBAC) for IP-SAKTI.

Roles: ``practitioner | startup | facilitator | admin``. The legacy default
``researcher`` normalises to ``practitioner`` so existing accounts keep
working. ``require_role`` is a FastAPI dependency factory (admin always
bypasses) and every paid-source or privileged access should be recorded with
``log_permission`` for the audit trail.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import Depends, HTTPException

from app.auth.jwt_auth import get_current_user
from app.models.db_models import User

logger = logging.getLogger("ipsakti.permissions")

ROLES: tuple[str, ...] = ("practitioner", "startup", "facilitator", "admin")

_LEGACY_ROLE_MAP: dict[str, str] = {
    "researcher": "practitioner",
    "user": "practitioner",
    "member": "practitioner",
}


def normalize_role(role: str | None) -> str:
    """Map any stored role string onto the canonical role set."""
    value = (role or "").strip().lower()
    value = _LEGACY_ROLE_MAP.get(value, value)
    return value if value in ROLES else "practitioner"


def require_role(*allowed: str) -> Callable[..., User]:
    """Dependency factory: authenticated user whose role is allowed (or admin)."""
    allowed_set = {normalize_role(role) for role in allowed} | {"admin"}

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        role = normalize_role(str(current_user.role))
        if role not in allowed_set:
            raise HTTPException(
                status_code=403,
                detail=f"role '{role}' is not permitted for this action",
            )
        return current_user

    return dependency


def log_permission(
    user: User | None, resource: str, granted: bool, reason: str = ""
) -> None:
    """Structured permission log — paid/privileged source access is logged."""
    logger.info(
        "permission_check resource=%s user=%s role=%s granted=%s reason=%s",
        resource,
        user.id if user else "anonymous",
        normalize_role(str(user.role)) if user else "anonymous",
        granted,
        reason,
    )
