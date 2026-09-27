"""Innovation-Lab Run Engine.

A deterministic, mock-first engine that walks a passport-style run through
the registered Innovation-Lab agents.  Agent steps are:

  * gated by their feature flags (see ``app.agents.registry``)
  * recorded on ``innolab_run_steps`` with input/output payloads
  * allowed to attach evidence + source citations
  * followed by an audit event + usage footprint

No external provider is contacted unless BOTH the provider is in live mode
and the ``innolab.live_providers`` feature flag is enabled.  The default is
full mock mode so the module works offline in CI/testing.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.agents.registry import AgentSpec, get_registry
from app.models.innolab_models import (
    InnolabRunDB,
    InnolabRunStepDB,
)

# Feature-flag prefixes (kept aligned with app.agents.registry slugs).
FEATURE_FLAG_PREFIX = "innolab.agent."


def _new_id() -> str:
    return str(uuid.uuid4())


class RunAlreadyCompletedError(RuntimeError):
    pass


class AgentNotEnabledError(RuntimeError):
    pass


class InnovationLabRunEngine:
    """Orchestrates multi-agent runs for a project under a versioned state machine."""

    def __init__(
        self,
        db: Session,
        *,
        run_id: str,
        spec_slugs: list[str] | None = None,
        feature_flags: dict[str, bool] | None = None,
    ) -> None:
        self.db = db
        self.run_id = run_id
        self._registry = get_registry()

        run = db.query(InnolabRunDB).filter(InnolabRunDB.id == run_id).one_or_none()
        if run is None:
            raise LookupError(f"Run '{run_id}' not found.")
        if run.status in ("completed", "failed", "cancelled"):
            raise RunAlreadyCompletedError(f"Run '{run_id}' already terminal: {run.status}")
        self.run = run

        self.spec_slugs = spec_slugs or self._default_spec_slugs()
        self.feature_flags = feature_flags or {}

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _default_spec_slugs(self) -> list[str]:
        return [s.slug for s in self._active_specs()]

    def _active_specs(self) -> list[AgentSpec]:
        return sorted(
            (s for s in self._registry.all() if s.enabled_by_default and self._flag_ok(s.slug)),
            key=lambda s: s.phase_order,
        )

    def _flag_ok(self, slug: str) -> bool:
        flag = f"{FEATURE_FLAG_PREFIX}{slug}"
        if flag in self.feature_flags:
            return bool(self.feature_flags[flag])
        return True  # default-on when no explicit override, aligned with registry

    def _active_specs_for_run(self) -> list[AgentSpec]:
        """Respects per-run spec_slugs but keeps registry phase ordering."""
        by_slug = {s.slug: s for s in self._registry.all() if s.enabled_by_default and self._flag_ok(s.slug)}
        if self.spec_slugs:
            chosen = [by_slug[s] for s in self.spec_slugs if s in by_slug]
        else:
            chosen = sorted(by_slug.values(), key=lambda s: s.phase_order)
        return chosen

    # ------------------------------------------------------------------ #
    # per-agent execution (knowledge-grounded, offline-safe)
    # ------------------------------------------------------------------ #
    def _execute_agent(self, seq: int, spec: AgentSpec, base: dict[str, Any]) -> InnolabRunStepDB:
        from app.services.innolab.agent_executors import execute_agent

        start = time.monotonic()
        payload = dict(base)
        try:
            result = execute_agent(spec.slug, payload)
            status = "completed" if result.get("ok", True) else "failed"
        except Exception as exc:  # noqa: BLE001
            result = {
                "agent_slug": spec.slug,
                "phase": spec.phase,
                "ok": False,
                "summary": "Agent execution failed.",
                "note": f"Agent execution failed: {exc}",
                "findings": [],
                "evidence": [],
                "citations": [],
                "claims": [],
                "suggestions": [],
            }
            status = "failed"
        int((time.monotonic() - start) * 1000)

        step = InnolabRunStepDB(
            id=_new_id(),
            run_id=self.run_id,
            seq=seq,
            agent_slug=spec.slug,
            status=status,
            input_payload=payload,
            output_payload=result,
            error=None if status == "completed" else result.get("note"),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        return step
