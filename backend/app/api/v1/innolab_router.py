"""Innovation-Lab v1 router (wiring draft).

Composes the 8 Innovation-Lab sub-router families behind one ``innolab_router``
that the API v1 root includes.  Import-safe by construction:

  * only ``app.agents.registry`` is imported eagerly (whose entire surface is
    already verified importable and used by ``run_engine``/``providers``)
  * all model + engine references are resolved lazily inside each handler so
    module import never depends on ORM column spelling

Default is full mock mode: no external provider is contacted unless the
feature-flag prefix plus the global \"innolab.live_providers\" flag are both
enabled.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.registry import get_registry
from app.core.database import get_db
from app.models import innolab_models  # noqa: F401 — registers tables with Base.metadata
from app.services import innolab_service
from app.services.innolab.providers import ProviderHub
from app.services.innolab.run_engine import (
    AgentNotEnabledError,
    RunAlreadyCompletedError,
)


# ------------------------------------------------------------------ #
# contracts (thin, registry-derived — no ORM column guessing)
# ------------------------------------------------------------------ #
class AgentDescriptor(BaseModel):
    slug: str
    label: str = Field(default="")
    phase: str = Field(default="")
    category_label: str = Field(default="")
    description: str = Field(default="")
    enabled_by_default: bool = Field(default=True)
    requires_evidence: bool = Field(default=False)
    live_default: str = Field(default="mock")


class RegistrySummary(BaseModel):
    count: int
    phases: list[str]
    agents: list[AgentDescriptor]


def _registry_summary() -> RegistrySummary:
    reg = get_registry()
    phases: list[str] = []
    agents: list[AgentDescriptor] = []
    for s in reg.all():
        phase = getattr(s, "phase", "") or getattr(s, "category", "")
        if phase and phase not in phases:
            phases.append(phase)
        agents.append(
            AgentDescriptor(
                slug=getattr(s, "slug", "?"),
                label=getattr(s, "label", getattr(s, "name", "")),
                phase=phase,
                category_label=getattr(s, "category_label", phase.replace("_", " ").title()),
                description=getattr(s, "description", ""),
                enabled_by_default=bool(getattr(s, "enabled", getattr(s, "enabled_by_default", True))),
                requires_evidence=bool(getattr(s, "requires_evidence", False)),
            )
        )
    return RegistrySummary(count=len(agents), phases=phases, agents=agents)


class Capability(BaseModel):
    name: str
    kind: str = Field(default="agent")
    phase: str = Field(default="")
    flags: list[str] = Field(default_factory=list)


class CapabilitiesResponse(BaseModel):
    summary: RegistrySummary
    capabilities: list[Capability]


# ------------------------------------------------------------------ #
# router assemblies
# ------------------------------------------------------------------ #
router = APIRouter(prefix="/innolab", tags=["Innovation-Lab (v1)"])


@router.get("/capabilities", response_model=CapabilitiesResponse)
def innovation_lab_capabilities() -> CapabilitiesResponse:
    summary = _registry_summary()
    caps = [
        Capability(
            name=a.slug,
            kind="agent",
            phase=a.phase,
            flags=[f"innolab.agent.{a.slug}"],
        )
        for a in summary.agents
    ]
    return CapabilitiesResponse(summary=summary, capabilities=caps)


@router.get("/agents", response_model=RegistrySummary)
def list_agents() -> RegistrySummary:
    return _registry_summary()


# ------------------------------------------------------------------ #
# Per-agent detail + direct execution
# ------------------------------------------------------------------ #
from app.services.innolab.agent_executors import (  # noqa: E402
    execute_agent,
    extract_features,
    input_schema,
    sample_query,
)


class AgentInputField(BaseModel):
    key: str
    label: str
    kind: str = Field(default="text")
    required: bool = Field(default=False)
    default: Any = None


class AgentDetail(BaseModel):
    slug: str
    label: str
    phase: str = Field(default="")
    description: str = Field(default="")
    enabled_by_default: bool = Field(default=True)
    requires_evidence: bool = Field(default=False)
    inputs_schema: list[AgentInputField] = Field(default_factory=list)
    sample_query: str = Field(default="")


@router.get("/agents/{slug}", response_model=AgentDetail)
def get_agent_detail(slug: str) -> AgentDetail:
    spec = get_registry().get(slug)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found in registry")
    phase = getattr(spec, "phase", "") or getattr(spec, "category", "")
    return AgentDetail(
        slug=spec.slug,
        label=spec.label,
        phase=phase,
        description=spec.description,
        enabled_by_default=spec.enabled_by_default,
        requires_evidence=spec.requires_evidence,
        inputs_schema=[AgentInputField(**f) for f in input_schema(slug)],
        sample_query=sample_query(slug),
    )


# ------------------------------------------------------------------ #
# Guided workflow (step-by-step questions for one agent)
# ------------------------------------------------------------------ #
from app.services.innolab import agent_workflows  # noqa: E402


class WorkflowStepOut(BaseModel):
    label: str
    description: str = Field(default="")


class AgentQuestionOut(BaseModel):
    key: str
    label: str
    question: str
    kind: str = Field(default="text")
    required: bool = Field(default=False)
    options: list[str] = Field(default_factory=list)
    placeholder: str = Field(default="")
    help: str = Field(default="")


class AgentWorkflowDetail(BaseModel):
    slug: str
    label: str
    phase: str = Field(default="")
    description: str = Field(default="")
    steps: list[WorkflowStepOut] = Field(default_factory=list)
    questions: list[AgentQuestionOut] = Field(default_factory=list)
    auto_run: bool = Field(default=False)


@router.get("/agents/{slug}/workflow", response_model=AgentWorkflowDetail)
def get_agent_workflow(slug: str) -> AgentWorkflowDetail:
    spec = get_registry().get(slug)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found in registry")
    workflow = agent_workflows.workflow_for(slug)
    phase = getattr(spec, "phase", "") or getattr(spec, "category", "")
    return AgentWorkflowDetail(
        slug=spec.slug,
        label=spec.label,
        phase=phase,
        description=spec.description,
        steps=[WorkflowStepOut(**s) for s in workflow.get("steps", [])],
        questions=[AgentQuestionOut(**q) for q in workflow.get("questions", [])],
        auto_run=bool(workflow.get("auto_run", False)),
    )


class ExtractFeaturesRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)


class ExtractedFeature(BaseModel):
    text: str
    kind: str = Field(default="keyword")


class ExtractFeaturesResponse(BaseModel):
    slug: str
    summary: str = Field(default="")
    features: list[ExtractedFeature] = Field(default_factory=list)
    markets: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    resolved: list[str] = Field(default_factory=list)


@router.post("/agents/{slug}/extract-features", response_model=ExtractFeaturesResponse)
def extract_agent_features(slug: str, payload: ExtractFeaturesRequest) -> ExtractFeaturesResponse:
    """Eureka-style 'Confirm the agent's understanding'.

    Returns the technical features the agent extracted from the answers plus a
    one-line summary of its understanding, for the user to review/edit before
    the run (mirrors Eureka Novelty Search Step 2 / FTO feature extraction /
    TRIZ 'review and confirm understanding').
    """
    spec = get_registry().get(slug)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found in registry")
    data = extract_features(slug, payload.inputs)
    return ExtractFeaturesResponse(slug=slug, **data)


# ------------------------------------------------------------------ #
# Per-agent document upload (the agent reads the uploaded document)
# ------------------------------------------------------------------ #
_ALLOWED_DOC_EXTS = {".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".png", ".jpg", ".jpeg"}
_MAX_DOC_BYTES = 20 * 1024 * 1024  # 20MB
_MAX_DOC_CHARS = 120_000


class UploadDocumentResponse(BaseModel):
    slug: str
    filename: str
    ext: str = Field(default="")
    char_count: int = Field(default=0)
    extracted_text: str = Field(default="")
    threats: list[str] = Field(default_factory=list)


@router.post("/agents/{slug}/upload-document", response_model=UploadDocumentResponse)
async def upload_document_for_agent(slug: str, file: UploadFile = File(...)) -> UploadDocumentResponse:
    """Upload a document for an agent to read.

    Extracts text from PDF / DOCX / TXT / MD / CSV / JSON / image (OCR),
    grounds the extracted text on the local corpus the next time the agent
    is run, and returns the cleaned text so the frontend can prefill the
    guided workflow inputs.
    """
    spec = get_registry().get(slug)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found in registry")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_DOC_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext or 'unknown'}' not supported. Allowed: {', '.join(sorted(_ALLOWED_DOC_EXTS))}",
        )
    content = await file.read()
    if len(content) > _MAX_DOC_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds the 20MB limit")

    from app.core.sandboxing import DocumentSanitizer
    from app.ingestion.fetchers import read_local_file

    try:
        fd, path = tempfile.mkstemp(prefix="innolab_doc_", suffix=ext)
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
        parsed = read_local_file(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    if not parsed:
        raise HTTPException(status_code=400, detail="Could not extract any text from the uploaded document.")
    _, raw_text = parsed
    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=400, detail="The uploaded document contained no extractable text (scanned PDF? run OCR first).")

    cleaned, threats = DocumentSanitizer.sanitize(raw_text, file.filename or "agent_document")
    return UploadDocumentResponse(
        slug=slug,
        filename=file.filename or "document",
        ext=ext.lstrip("."),
        char_count=len(cleaned),
        extracted_text=cleaned[:_MAX_DOC_CHARS],
        threats=threats,
    )


# ------------------------------------------------------------------ #
# Orchestration Engine (multi-agent coordination)
# ------------------------------------------------------------------ #
from app.services.innolab import orchestrator  # noqa: E402


class OrchestratorPlanRequest(BaseModel):
    brief: str = Field(min_length=3, max_length=2000)


class IntentOut(BaseModel):
    intent: str
    label: str = Field(default="")


class PlannedAgent(BaseModel):
    slug: str
    label: str = Field(default="")
    phase: str = Field(default="")
    description: str = Field(default="")
    reason: str = Field(default="")
    tools: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    questions: int = Field(default=0)


class OrchestratorPlanResponse(BaseModel):
    brief: str
    intents: list[IntentOut] = Field(default_factory=list)
    entities: dict[str, Any] = Field(default_factory=dict)
    agents: list[PlannedAgent] = Field(default_factory=list)
    total_steps: int = Field(default=0)


@router.post("/orchestrator/plan", response_model=OrchestratorPlanResponse)
def orchestrator_plan(payload: OrchestratorPlanRequest) -> OrchestratorPlanResponse:
    plan = orchestrator.plan_brief(payload.brief)
    return OrchestratorPlanResponse(**plan)


class OrchestratorRunRequest(BaseModel):
    brief: str = Field(min_length=3, max_length=2000)
    agents: list[str] | None = Field(default=None)
    project_id: str | None = Field(default=None)
    answers: dict[str, Any] = Field(default_factory=dict)


class OrchestratorRunResponse(BaseModel):
    run_id: str
    project_id: str
    status: str
    chain: list[PlannedAgent] = Field(default_factory=list)
    base_inputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)


@router.post("/orchestrator/run", response_model=OrchestratorRunResponse)
def orchestrator_run(payload: OrchestratorRunRequest, db: Session = Depends(get_db)) -> OrchestratorRunResponse:
    try:
        parsed = orchestrator.parse_brief(payload.brief)
        if payload.answers:
            parsed["answers"] = payload.answers
        result = orchestrator.run_plan(
            db,
            parsed,
            agent_slugs=payload.agents,
            project_id=payload.project_id,
        )
    except (RunAlreadyCompletedError, AgentNotEnabledError, LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chain = []
    for a in result.get("chain", []):
        planned = PlannedAgent(**{k: a.get(k, "") for k in ["slug", "label", "phase", "description", "reason", "tools", "workflow_steps", "questions"]})
        chain.append(planned)

    return OrchestratorRunResponse(
        run_id=result["run_id"],
        project_id=result["project_id"],
        status=result["status"],
        chain=chain,
        base_inputs=result["base_inputs"],
        steps=result["steps"],
        verification=result["verification"],
    )


class AgentRunRequest(BaseModel):
    project_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    agent_slug: str
    run_id: str | None = None
    status: str = Field(default="ok")
    result: dict[str, Any]


@router.post("/agents/{slug}/run", response_model=AgentRunResponse)
def run_agent(slug: str, payload: AgentRunRequest, db: Session = Depends(get_db)) -> AgentRunResponse:
    spec = get_registry().get(slug)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found in registry")

    result = execute_agent(slug, payload.inputs or {})
    status = "ok" if result.get("ok", True) else "error"

    run_id = None
    if payload.project_id:
        project = innolab_service.get_project(db, payload.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        run = innolab_service.create_run(
            db,
            project_id=payload.project_id,
            initiator_id="system",
            run_type="agent_direct",
            feature_flags={f"innolab.agent.{slug}": True},
        )
        try:
            from app.services.innolab.run_engine import InnovationLabRunEngine

            engine = InnovationLabRunEngine(
                db,
                run_id=cast(str, run.id),
                spec_slugs=[slug],
                feature_flags={f"innolab.agent.{slug}": True},
            )
            step = engine._execute_agent(1, spec, base=payload.inputs or {})
            db.add(step)
            db.commit()
        except (RunAlreadyCompletedError, AgentNotEnabledError, LookupError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        run_id = cast(str, run.id)

    return AgentRunResponse(agent_slug=slug, run_id=run_id, status=status, result=result)


class AgentExportRequest(BaseModel):
    result: dict[str, Any] = Field(default_factory=dict)


@router.post("/agents/{slug}/export", response_class=FileResponse)
def export_agent_result(slug: str, payload: AgentExportRequest) -> FileResponse:
    """Export a finished agent run as a Word (.docx) report."""
    spec = get_registry().get(slug)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found in registry")

    from app.services.innolab.innolab_docx import build_agent_docx, export_path

    try:
        buf = build_agent_docx(
            spec.slug,
            spec.label,
            getattr(spec, "phase", "") or getattr(spec, "category", ""),
            payload.result,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Could not build the Word report: {exc}") from exc

    filename = export_path(spec.slug)
    with open(filename, "wb") as f:
        f.write(buf.getvalue())
    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{spec.slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
    )


@router.get("/healthy")
def healthy() -> dict[str, Any]:
    return {"ok": "true", "module": "innolab", "mode": "mock", "agents": get_registry().slugs()}


@router.get("/pulse")
def pulse(db: Session = Depends(get_db)) -> dict[str, Any]:
    return innolab_service.pulse(db)


@router.get("/providers")
def list_providers() -> list[dict[str, Any]]:
    hub = ProviderHub(live_mode_flag=False)
    return [
        {
            "slug": p.slug,
            "label": p.label,
            "available": p.available,
            "live_mode_enabled": p.live_mode_enabled,
            "configured": p.configured,
            "capabilities": [c.name for c in p.capabilities],
            "notes": p.notes,
        }
        for p in hub.list_providers()
    ]


# ------------------------------------------------------------------ #
# Projects
# ------------------------------------------------------------------ #
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    sensitivity: str = "standard"


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    sensitivity: str
    created_at: str | None = None

    @classmethod
    def from_db(cls, p) -> ProjectOut:
        return cls(
            id=p.id,
            name=p.name,
            description=p.description,
            status=p.status,
            sensitivity=p.sensitivity,
            created_at=p.created_at.isoformat() if p.created_at else None,
        )


projects_router = APIRouter(prefix="/projects", tags=["Innovation-Lab: Projects"])


@projects_router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectOut:
    slug = f"{payload.name.strip().lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}"
    try:
        project = innolab_service.create_project(
            db,
            name=payload.name,
            slug=slug,
            description=payload.description,
            owner_id="system",
            sensitivity=payload.sensitivity,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create project: {exc}") from exc
    return ProjectOut.from_db(project)


@projects_router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectOut]:
    return [ProjectOut.from_db(p) for p in innolab_service.list_projects(db)]


@projects_router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectOut:
    project = innolab_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut.from_db(project)


# ------------------------------------------------------------------ #
# Runs
# ------------------------------------------------------------------ #
class RunCreate(BaseModel):
    project_id: str
    run_type: str = "passport_workflow"
    agent_slugs: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)


class RunStepOut(BaseModel):
    seq: int
    agent_slug: str
    status: str
    input_payload: dict[str, Any] | None = None
    output_payload: dict[str, Any] | None = None
    error: str | None = None


class RunOut(BaseModel):
    id: str
    project_id: str
    status: str
    run_type: str
    current_step: str | None = None
    steps: list[RunStepOut] = Field(default_factory=list)

    @classmethod
    def from_db(cls, r, steps: list[Any] | None = None) -> RunOut:
        return cls(
            id=r.id,
            project_id=r.project_id,
            status=r.status,
            run_type=r.run_type,
            current_step=(
                cast("str | None", r.current_step)
                if isinstance(r, innolab_models.InnolabRunDB)
                else None
            ),
            steps=[
                RunStepOut(
                    seq=s.seq,
                    agent_slug=s.agent_slug,
                    status=s.status,
                    input_payload=s.input_payload,
                    output_payload=s.output_payload,
                    error=s.error,
                )
                for s in (steps or [])
            ],
        )


runs_router = APIRouter(prefix="/runs", tags=["Innovation-Lab: Runs"])


@runs_router.post("", response_model=RunOut, status_code=201)
def create_run(payload: RunCreate, db: Session = Depends(get_db)) -> RunOut:
    project = innolab_service.get_project(db, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    run = innolab_service.create_run(
        db,
        project_id=payload.project_id,
        initiator_id="system",
        run_type=payload.run_type,
        feature_flags={f"innolab.agent.{s}": True for s in payload.agent_slugs},
    )

    engine = None
    try:
        from app.services.innolab.run_engine import InnovationLabRunEngine

        engine = InnovationLabRunEngine(
            db,
            run_id=cast(str, run.id),
            spec_slugs=payload.agent_slugs or None,
            feature_flags={f"innolab.agent.{s}": True for s in payload.agent_slugs},
        )
    except (RunAlreadyCompletedError, AgentNotEnabledError, LookupError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    steps = _run_steps(db, engine)
    return RunOut.from_db(run, steps=steps)


def _run_steps(db: Session, engine) -> list[Any]:
    steps: list[Any] = []
    for seq, spec in enumerate(engine._active_specs_for_run(), start=1):
        step = engine._execute_agent(seq, spec, base={})
        db.add(step)
        steps.append(step)
    db.commit()
    return steps


@runs_router.get("")
def list_runs(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [
        {"id": run.id, "project_id": run.project_id, "status": run.status, "run_type": run.run_type}
        for run in db.query(innolab_models.InnolabRunDB).order_by(
            innolab_models.InnolabRunDB.created_at.desc()
        ).all()
    ]


@runs_router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)) -> RunOut:
    run = db.query(innolab_models.InnolabRunDB).filter(
        innolab_models.InnolabRunDB.id == run_id
    ).one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunOut.from_db(run, steps=run.steps)


# ------------------------------------------------------------------ #
# assembly
# ------------------------------------------------------------------ #
router.include_router(projects_router)
router.include_router(runs_router)
