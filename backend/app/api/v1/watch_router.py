"""G8 - Filing Intelligence API: patent watch, deadlines, fee estimates.

  POST /watch/profiles        create a watch profile (A2)
  GET  /watch/profiles        list your active profiles
  DELETE /watch/profiles/{id} stop watching
  POST /watch/run             admin: run one screening cycle
  GET  /watch/digest          weekly digest (Hindi + English, alerts per profile)
  GET  /deadlines/rules       supported deadline kinds + statutory basis (A3)
  POST /deadlines             track one deadline
  POST /deadlines/schedule    derive the full schedule (e.g. all patent renewals)
  GET  /deadlines             list / upcoming window
  POST /deadlines/{id}/done   mark completed
  GET  /fees/routes           fee routes + official source links (C2)
  POST /fees/estimate         estimate fees with concession applied
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_optional_user
from app.auth.rbac import require_role
from app.core.database import get_db
from app.models.db_models import User
from app.services import deadline_service, fee_estimator, watch_service

router = APIRouter(tags=["Filing Intelligence"])

require_practitioner = require_role("practitioner", "startup", "facilitator")
require_admin = require_role("admin")


def _uid(current_user: User) -> str:
    return str(current_user.id)


# ---------------------------------------------------------------------------
# A2 - Patent watch
# ---------------------------------------------------------------------------

class WatchProfileRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    ingredients: list[str] = Field(..., min_length=1, max_length=40)
    indication: str = Field("", max_length=200)
    classical_ref: str = Field("", max_length=300)
    passport_id: str | None = None


@router.post("/watch/profiles")
def create_watch_profile(
    req: WatchProfileRequest,
    current_user: User = Depends(require_practitioner),
    db: Session = Depends(get_db),
):
    profile = watch_service.create_profile(
        db,
        user_id=_uid(current_user),
        title=req.title,
        ingredients=req.ingredients,
        indication=req.indication,
        classical_ref=req.classical_ref,
        passport_id=req.passport_id,
    )
    return {
        "profile_id": profile.id,
        "title": profile.title,
        "ingredients": profile.ingredients,
        "status": profile.status,
    }


@router.get("/watch/profiles")
def list_watch_profiles(
    current_user: User = Depends(require_practitioner),
    db: Session = Depends(get_db),
):
    profiles = watch_service.list_profiles(db, _uid(current_user))
    return {
        "count": len(profiles),
        "profiles": [
            {
                "profile_id": p.id,
                "title": p.title,
                "ingredients": p.ingredients,
                "indication": p.indication,
                "last_checked_at": p.last_checked_at,
            }
            for p in profiles
        ],
    }


@router.delete("/watch/profiles/{profile_id}")
def delete_watch_profile(
    profile_id: str,
    current_user: User = Depends(require_practitioner),
    db: Session = Depends(get_db),
):
    if not watch_service.delete_profile(db, _uid(current_user), profile_id):
        raise HTTPException(404, "watch profile not found")
    return {"deleted": profile_id}


class WatchRunRequest(BaseModel):
    patents: list[dict[str, Any]] | None = Field(
        None, description="Newly published patent records for this cycle"
    )
    user_id: str | None = None


@router.post("/watch/run")
def run_watch_cycle(
    req: WatchRunRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return watch_service.run_watch_cycle(db, patents=req.patents, user_id=req.user_id)


@router.get("/watch/digest")
def watch_digest(
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    user_id = _uid(current_user) if current_user else "anonymous"
    return watch_service.build_digest(db, user_id)


# ---------------------------------------------------------------------------
# A3 - Deadlines
# ---------------------------------------------------------------------------

class DeadlineRequest(BaseModel):
    kind: str = Field(..., max_length=32)
    due_date: str = Field(..., description="YYYY-MM-DD")
    reference: str = Field("", max_length=120)
    title: str = Field("", max_length=200)
    notes: str = Field("", max_length=600)


class DeadlineScheduleRequest(BaseModel):
    kind: str = Field(..., max_length=32)
    anchor_date: str = Field(..., description="Filing / registration date, YYYY-MM-DD")
    reference: str = Field("", max_length=120)
    notes: str = Field("", max_length=600)


@router.get("/deadlines/rules")
def deadline_rules():
    return {"rules": deadline_service.rules_catalogue()}


@router.post("/deadlines")
def create_deadline(
    req: DeadlineRequest,
    current_user: User = Depends(require_practitioner),
    db: Session = Depends(get_db),
):
    try:
        row = deadline_service.create_deadline(
            db,
            _uid(current_user),
            req.kind,
            req.due_date,
            reference=req.reference,
            title=req.title,
            notes=req.notes,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"id": row.id, "kind": row.kind, "due_date": row.due_date, "title": row.title}


@router.post("/deadlines/schedule")
def create_deadline_schedule(
    req: DeadlineScheduleRequest,
    current_user: User = Depends(require_practitioner),
    db: Session = Depends(get_db),
):
    try:
        rows = deadline_service.create_schedule(
            db,
            _uid(current_user),
            req.kind,
            req.anchor_date,
            reference=req.reference,
            notes=req.notes,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "created": len(rows),
        "deadlines": [
            {"id": r.id, "kind": r.kind, "due_date": r.due_date, "title": r.title}
            for r in rows
        ],
    }


@router.get("/deadlines")
def list_deadlines(
    within_days: int | None = Query(None, ge=1, le=3650),
    status: str = Query("", max_length=16),
    current_user: User = Depends(require_practitioner),
    db: Session = Depends(get_db),
):
    rows = deadline_service.list_deadlines(
        db, _uid(current_user), status=status, within_days=within_days
    )
    return {
        "count": len(rows),
        "deadlines": [
            {
                "id": r.id,
                "kind": r.kind,
                "title": r.title,
                "reference": r.reference,
                "due_date": r.due_date,
                "status": r.status,
                "reminder_days": r.reminder_days,
            }
            for r in rows
        ],
    }


@router.post("/deadlines/{deadline_id}/done")
def complete_deadline(
    deadline_id: str,
    current_user: User = Depends(require_practitioner),
    db: Session = Depends(get_db),
):
    if not deadline_service.mark_done(db, _uid(current_user), deadline_id):
        raise HTTPException(404, "deadline not found")
    return {"id": deadline_id, "status": "done"}


# ---------------------------------------------------------------------------
# C2 - Fee estimator
# ---------------------------------------------------------------------------

class FeeEstimateRequest(BaseModel):
    route: str = Field(..., description="patent | trademark | gi | abs")
    entity_class: str = Field("individual", description="individual | startup | small_entity | large_entity")
    classes: int = Field(1, ge=1, le=45)
    include_examination: bool = True


@router.get("/fees/routes")
def fee_routes():
    return {"routes": fee_estimator.list_routes()}


@router.post("/fees/estimate")
def fee_estimate(
    req: FeeEstimateRequest,
    current_user: User | None = Depends(get_optional_user),
):
    try:
        return fee_estimator.estimate(
            req.route,
            entity_class=req.entity_class,
            classes=req.classes,
            include_examination=req.include_examination,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
