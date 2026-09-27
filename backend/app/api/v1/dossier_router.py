"""G9 - Document Engine API: cited dossier (A4) and prefilled forms (A6).

  GET  /dossier/forms                 supported prefilled forms (A6)
  POST /dossier/build                 build a cited dossier for a passport
  GET  /dossier/{passport_id}         latest stored dossier
  GET  /dossier/{passport_id}/markdown
  GET  /dossier/{passport_id}/pdf
  POST /prefill/{form}                prefill form1 | form2 (A6)
  GET  /prefill/{document_id}/readback  verify every field against its source
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.core.database import get_db
from app.models.db_models import GeneratedDocumentDB, User
from app.services import dossier_service, prefill_service

router = APIRouter(tags=["Document Engine"])

require_user = require_role("practitioner", "startup", "facilitator")
require_admin = require_role("admin")


class BuildDossierRequest(BaseModel):
    passport_id: str = Field(..., min_length=4, max_length=64)
    include_watch_alerts: bool = True
    top_k: int = Field(4, ge=1, le=10)


def _watch_alerts_for(passport_id: str) -> list[dict[str, Any]]:
    """Fold the user's open patent-watch alerts into the dossier (A2 -> A4)."""
    try:
        from app.models.db_models import WatchHit, WatchProfile

        db = None
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            profiles = (
                db.query(WatchProfile)
                .filter(
                    WatchProfile.passport_id == passport_id,
                    WatchProfile.status == "active",
                )
                .all()
            )
            alerts: list[dict[str, Any]] = []
            for profile in profiles:
                for hit in (
                    db.query(WatchHit)
                    .filter(WatchHit.profile_id == profile.id)
                    .order_by(WatchHit.detected_at.desc())
                    .limit(10)
                    .all()
                ):
                    alerts.append(
                        {
                            "patent_no": str(hit.patent_no),
                            "title": str(hit.title),
                            "match": str(hit.match_kind),
                            "overlap": str(hit.overlap),
                            "urgency": str(hit.urgency),
                            "source_url": str(hit.source_url),
                        }
                    )
            return alerts
        finally:
            db.close()
    except Exception:  # noqa: BLE001 - dossier must build without the watch service
        return []


@router.get("/dossier/forms")
def list_forms():
    return {"forms": prefill_service.supported_forms()}


@router.post("/dossier/build")
def build_dossier(
    req: BuildDossierRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    alerts = _watch_alerts_for(req.passport_id) if req.include_watch_alerts else []
    try:
        dossier = dossier_service.build_dossier(
            req.passport_id, top_k=req.top_k, watch_alerts=alerts
        )
    except dossier_service.DossierError as exc:
        raise HTTPException(404, str(exc)) from exc
    record = dossier_service.save_dossier_record(
        db, req.passport_id, str(current_user.id), dossier
    )
    return {**dossier, "document_id": record.id}


@router.get("/dossier/{passport_id}")
def get_latest_dossier(
    passport_id: str,
    db: Session = Depends(get_db),
):
    record = (
        db.query(GeneratedDocumentDB)
        .filter(
            GeneratedDocumentDB.passport_id == passport_id,
            GeneratedDocumentDB.kind == "dossier",
        )
        .order_by(GeneratedDocumentDB.created_at.desc())
        .first()
    )
    if record is None:
        raise HTTPException(404, "no dossier generated for this passport yet")
    return {
        "document_id": record.id,
        "passport_id": passport_id,
        "status": record.status,
        "content_hash": record.content_hash,
        "citation_count": record.citation_count,
        "generated_at": record.summary.get("generated_at", ""),
        "summary": record.summary,
    }


@router.get("/dossier/{passport_id}/markdown")
def dossier_markdown(passport_id: str):
    try:
        dossier = dossier_service.build_dossier(passport_id)
    except dossier_service.DossierError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(
        content=dossier_service.render_markdown(dossier),
        media_type="text/markdown; charset=utf-8",
    )


@router.get("/dossier/{passport_id}/pdf")
def dossier_pdf(passport_id: str):
    try:
        dossier = dossier_service.build_dossier(passport_id)
        pdf = dossier_service.render_pdf(dossier)
    except dossier_service.DossierError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="IPSAKTI_Dossier_{passport_id[:8]}.pdf"'
        },
    )


class PrefillRequest(BaseModel):
    passport_id: str = Field(..., min_length=4, max_length=64)
    applicant: dict[str, Any] | None = None


@router.post("/prefill/{form}")
def prefill(
    form: str,
    req: PrefillRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    try:
        draft = prefill_service.prefill_form(
            req.passport_id, form=form, applicant=req.applicant
        )
    except prefill_service.PrefillError as exc:
        raise HTTPException(404, str(exc)) from exc
    record = prefill_service.save_prefill_record(
        db, req.passport_id, str(current_user.id), draft
    )
    return {**draft, "document_id": record.id, "readback": prefill_service.read_back(draft)}


@router.get("/prefill/{document_id}/readback")
def prefill_readback(document_id: str, db: Session = Depends(get_db)):
    record = (
        db.query(GeneratedDocumentDB)
        .filter(GeneratedDocumentDB.id == document_id, GeneratedDocumentDB.kind == "form")
        .first()
    )
    if record is None:
        raise HTTPException(404, "draft not found")
    try:
        draft = prefill_service.prefill_form(str(record.passport_id), form=str(record.form_code))
    except prefill_service.PrefillError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {
        "document_id": document_id,
        "form": record.form_code,
        "status": record.status,
        "content_hash": record.content_hash,
        "readback": prefill_service.read_back(draft),
    }
