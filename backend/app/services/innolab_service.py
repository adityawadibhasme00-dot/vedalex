"""Innovation-Lab run service.

Phase-1 scope:
  * deterministic, mock-first orchestration of the 19-agent workflow
  * gated by the ''AgentRegistry'' feature flags (see app.agents.registry)
  * evidence + source-citation capture per step
  * audit events on every state transition
  * no tokens consumed, no external provider contacted while in mock mode

Every function here is pure/orchestration over the innolab tables so the
service layer stays unit-testable without spinning up live providers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.agents.registry import AGENT_COUNT
from app.models.innolab_models import (
    InnolabAuditEventDB,
    InnolabEvidenceDB,
    InnolabProjectDB,
    InnolabRunDB,
    InnolabSourceCitationDB,
)


def _new_id() -> str:
    return str(uuid.uuid4())


# --------------------------------------------------------------------------- #
# Public pulse helpers
# --------------------------------------------------------------------------- #
def pulse(db) -> dict[str, Any]:
    """Lightweight health signal used by the Innovation-Lab status endpoint."""
    return {
        "engine": "innolab.run_engine.v1",
        "registry_agents": AGENT_COUNT,
        "mock_first": True,
        "queued_runs": 0,
        "active_runs": 0,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def create_project(db, *, name, slug, description=None, owner_id, sensitivity="standard") -> InnolabProjectDB:
    project = InnolabProjectDB(
        id=_new_id(),
        name=name,
        slug=slug,
        description=description,
        owner_id=owner_id,
        sensitivity=sensitivity,
        status="draft",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db, *, owner_id=None) -> list[InnolabProjectDB]:
    q = db.query(InnolabProjectDB)
    if owner_id:
        q = q.filter(InnolabProjectDB.owner_id == owner_id)
    return q.order_by(InnolabProjectDB.created_at.desc()).all()


def get_project(db, project_id: str) -> InnolabProjectDB | None:
    return db.query(InnolabProjectDB).filter(InnolabProjectDB.id == project_id).one_or_none()


def create_run(db, *, project_id, initiator_id, run_type="passport_workflow", feature_flags=None) -> InnolabRunDB:
    run = InnolabRunDB(
        id=_new_id(),
        project_id=project_id,
        initiator_id=initiator_id,
        run_type=run_type,
        status="pending",
        feature_flags_json=feature_flags or {},
    )
    db.add(run)
    db.add(
        InnolabAuditEventDB(
            id=_new_id(),
            actor_id=initiator_id,
            project_id=project_id,
            action="innolab.run.created",
            resource=f"run:{run.id}",
        )
    )
    db.commit()
    db.refresh(run)
    return run


def _save_citation(db, *, run_id, agent_slug, kind, label, url=None, snippet=None, ref=None, provider=None, confidence=None) -> InnolabSourceCitationDB:
    citation = InnolabSourceCitationDB(
        id=_new_id(),
        run_id=run_id,
        agent_slug=agent_slug,
        kind=kind,
        label=label,
        url=url,
        snippet=snippet,
        ref=ref,
        provider=provider,
        confidence=confidence,
    )
    db.add(citation)
    return citation


def _save_evidence(db, *, run_id, agent_slug, kind, finding, severity="info", status="unverified") -> InnolabEvidenceDB:
    evidence = InnolabEvidenceDB(
        id=_new_id(),
        run_id=run_id,
        agent_slug=agent_slug,
        kind=kind,
        finding=finding,
        severity=severity,
        status=status,
    )
    db.add(evidence)
    return evidence
