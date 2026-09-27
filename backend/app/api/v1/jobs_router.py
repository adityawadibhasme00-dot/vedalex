"""Background job submission and inspection.

Long operations (corpus reindex, statutory harvest, law sentinel, dossier export)
run here instead of holding a request worker.  Submit returns a job id
immediately; poll ``/jobs/{id}`` for state and result.

The synchronous path still exists on the original endpoints — these routes are
for callers that do not want to wait, or that hit operations which have no
inline equivalent.

Access control
--------------
Submitting is **admin-only**: these handlers re-fetch government sources, rewrite
the retrieval index and burn embedding budget, so an unauthenticated POST here
is a denial-of-service lever, not a convenience.  Reading job state requires an
authenticated user because payloads and errors can quote input text.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.jwt_auth import get_current_user
from app.auth.rbac import require_role
from app.core import job_handlers as _handlers  # noqa: F401  (registers handlers)
from app.core.jobs import get as get_job
from app.core.jobs import list_jobs
from app.core.jobs import stats as job_stats
from app.core.jobs import submit as submit_job
from app.models.db_models import User

router = APIRouter(prefix="/jobs", tags=["Background Jobs"])

require_admin = require_role("admin")


class JobSubmitRequest(BaseModel):
    name: str = Field(..., description="Registered job name")
    payload: dict[str, Any] = Field(default_factory=dict)
    start: bool = Field(
        default=True,
        description="Execute immediately on a worker thread. False records only.",
    )


class JobView(BaseModel):
    id: str
    name: str
    state: str
    submitted_at: float
    started_at: float | None = None
    finished_at: float | None = None
    elapsed_sec: float = 0.0
    payload: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    error: str | None = None
    worker: str | None = None


@router.get("/handlers")
def list_handlers(
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Job names this deployment can execute."""
    from app.core.jobs import handlers

    return {"handlers": sorted(handlers())}


@router.post("", response_model=JobView, status_code=202)
def submit(req: JobSubmitRequest, _admin: User = Depends(require_admin)) -> Any:
    """Queue a background job. Admin only."""
    try:
        job = submit_job(req.name, req.payload, start_inline=req.start)
    except KeyError as exc:
        raise HTTPException(400, str(exc)) from exc
    return job.to_dict()


@router.get("/stats")
def stats(_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return job_stats()


@router.get("", response_model=list[JobView])
def listing(
    limit: int = 50,
    _user: User = Depends(get_current_user),
) -> Any:
    return list_jobs(limit=max(1, min(limit, 200)))


@router.get("/{job_id}", response_model=JobView)
def read(job_id: str, _user: User = Depends(get_current_user)) -> Any:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, f"job {job_id!r} not found")
    return job
