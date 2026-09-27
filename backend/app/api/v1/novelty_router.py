"""Eureka-style Novelty Search workflow endpoints.

POST /novelty/workflow          -> runs the 7-step pipeline
GET  /novelty/workflow/{id}     -> returns a stored workflow
POST /novelty/workflow/{id}/export -> exports the report as Word (.docx)
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter()

_WORKFLOWS: dict[str, dict[str, Any]] = {}


class NoveltySearchRequest(BaseModel):
    problem_text: str = Field(..., description="Description of the technical solution to search for.")
    target_markets: list[str] = Field(default_factory=lambda: ["India"])
    jurisdiction: str = Field(default="IN", description="Patent jurisdiction code, e.g. IN, US, EP.")


class NoveltyExportRequest(BaseModel):
    result: dict[str, Any] = Field(default_factory=dict)


def _get_workflow(workflow_id: str) -> dict[str, Any]:
    wf = _WORKFLOWS.get(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Novelty workflow '{workflow_id}' not found")
    return wf


@router.post("/novelty/workflow")
def run_novelty_workflow(payload: NoveltySearchRequest) -> dict[str, Any]:
    from app.services.novelty_workflow import run_workflow

    try:
        wf = run_workflow(
            payload.problem_text,
            target_markets=payload.target_markets,
            jurisdiction=payload.jurisdiction,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _WORKFLOWS[wf["workflow_id"]] = wf
    return wf


@router.get("/novelty/workflow/{workflow_id}")
def get_novelty_workflow(workflow_id: str) -> dict[str, Any]:
    return _get_workflow(workflow_id)


@router.post("/novelty/workflow/{workflow_id}/export", response_class=FileResponse)
def export_novelty_report(workflow_id: str, payload: NoveltyExportRequest) -> FileResponse:
    wf = _get_workflow(workflow_id)

    from app.services.innolab.innolab_docx import build_agent_docx, export_path
    from app.services.novelty_workflow import build_export_result

    result = payload.result or build_export_result(wf)
    try:
        buf = build_agent_docx(
            "novelty_search", "Novelty Search Report", "Patentability Review", result
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Could not build the Word report: {exc}") from exc

    filename = export_path("novelty_search")
    with open(filename, "wb") as f:
        f.write(buf.getvalue())

    from datetime import datetime
    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"novelty_search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
    )