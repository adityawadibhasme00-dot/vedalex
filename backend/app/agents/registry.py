"""IP-SAKTI Agent Hub — Agent Registry.

Registers the 19 discipline-specific AI agents that power the Agent Hub
pipeline (engineering, IP, life-sciences and materials categories). Each
agent is orchestrated by the IP-SAKTI Orchestration Engine, runs its own
planner/tools/reasoning/validation workflow, and is feature-flag gated so
router endpoints, provenance auditor and UI share one canonical definition.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings

AGENT_CATEGORIES = (
    "engineering",
    "ip",
    "life_sciences",
    "materials",
)

# Kept for backwards compatibility with earlier phase-driven tooling.
AGENT_PHASES = AGENT_CATEGORIES

_AGENT_CATEGORY_LABELS = {
    "engineering": "Engineering",
    "ip": "Intellectual Property",
    "life_sciences": "Life Sciences",
    "materials": "Materials & Formulation",
}

_INTERNAL = object()


@dataclass(frozen=True)
class AgentSpec:
    """Canonical definition of one Agent-Hub agent."""

    slug: str
    label: str
    category: str = "research"
    description: str = ""
    phase: str = ""
    icon: str = "bot"
    provider_kind: str = "local"
    enabled_by_default: bool = True
    requires_evidence: bool = False
    dependencies: tuple = ()
    kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def feature_flag(self) -> str:
        return f"agent.{self.slug}"

    def __post_init__(self) -> None:
        if not self.phase and self.category:
            object.__setattr__(self, "phase", self.category)

    @property
    def phase_order(self) -> int:
        try:
            return AGENT_CATEGORIES.index(self.phase or self.category)
        except ValueError:
            return len(AGENT_CATEGORIES)

    @property
    def category_label(self) -> str:
        return _AGENT_CATEGORY_LABELS.get(self.phase or self.category, (self.phase or self.category).replace("_", " ").title())


class AgentRegistry:
    """Typed, feature-flag-gated registry shared across agents/services/UI."""

    def __init__(self, specs: list[AgentSpec]):
        self._specs: dict[str, AgentSpec] = {s.slug: s for s in specs}
        self._cache: dict[str, Any | None] = {}
        self._lock = threading.Lock()

    def all(self) -> list[AgentSpec]:
        return list(self._specs.values())

    def get(self, slug: str) -> AgentSpec | None:
        return self._specs.get(slug)

    def slugs(self) -> list[str]:
        return list(self._specs.keys())

    def is_enabled(self, slug: str) -> bool:
        spec = self._specs.get(slug)
        if spec is None:
            return False
        flag = spec.feature_flag
        flags = settings.FEATURE_FLAGS or {}
        return bool(flags.get(flag, spec.enabled_by_default))

    def enabled_slugs(self) -> list[str]:
        return [s.slug for s in self._specs.values() if self.is_enabled(s.slug)]

    def phases(self) -> dict[str, list[AgentSpec]]:
        by_phase: dict[str, list[AgentSpec]] = {}
        for phase in AGENT_PHASES:
            by_phase[phase] = [s for s in self._specs.values() if s.phase == phase]
        return by_phase

    def require(self, slug: str) -> AgentSpec:
        spec = self._specs.get(slug)
        if spec is None or not self.is_enabled(slug):
            raise KeyError(f"Agent '{slug}' is not registered or is disabled.")
        return spec


# --------------------------------------------------------------------------
# The 19 Agent-Hub discipline agents.
# Each maps to a distinct workflow inside the IP-SAKTI Orchestration Engine.
# --------------------------------------------------------------------------
_AGENT_SPECS: list[AgentSpec] = [
    AgentSpec("triz", "TRIZ Innovation", "engineering", "Find solutions with TRIZ — contradiction analysis, innovation principles and implementation roadmap.", icon="lightbulb"),
    AgentSpec("quick_research", "Quick Research", "engineering", "Technology intelligence — concept extraction, trend detection, evidence clustering and research-gap mapping.", icon="globe"),
    AgentSpec("novelty_search", "Novelty Search", "ip", "Examiner-style (WIPO single-reference) novelty search — disclosure → atomic feature extraction (F1…Fn, essential vs optional) → confirm → multi-strategy prior-art search → seven-level feature×reference disclosure → single-reference novelty matrix → separated metrics (semantic similarity, feature coverage, anticipation risk, search confidence), never a single unexplained 'novelty score'.", icon="search"),
    AgentSpec("fto_search", "FTO Search", "ip", "Jurisdiction- and activity-specific FTO screening — product/process decomposition (confirmed/missing) → jurisdiction×activity matrix → multi-strategy search → candidate screening (patents vs regulatory background) → element-wise claim chart (Identified / Not identified / Uncertain + reviewer question) → risk classification with basis, capped at Medium until legal status is verified on official registers.", icon="shield"),
    AgentSpec("patent_drafting", "Patent Drafting", "ip", "Eureka-exact patent drafting — invention description → terms map → corrupted/vague-term detection (drafting gate: benefit-as-component, corrupt text, undefined 'effective amounts', unsupported synergy, vague process, unnamed solvent) → ingredient-vs-benefit split → embedded prior-art/TK review → confirm essential features → gated claim versions (A broad/B supported/C fallback) → specification → figures only where technically meaningful → blocking dual-track compliance → preliminary draft with [TO BE CONFIRMED] markers and inventor-confirmation checklist (never 'filing-ready' without attorney review).", icon="file-text"),
    AgentSpec("invention_disclosure", "Invention Disclosure", "ip", "Source-of-truth invention disclosure — raw lab notes and inventor capture (Who/What/Why/How), confirmed vs unconfirmed record with explicit missing-data markers, problem → means → mechanism → effect analysis, essential-feature matrix, traditional-knowledge and public-disclosure review, and a gated handoff that blocks patent drafting until the record is inventor-confirmed and evidence-backed.", icon="folder"),
    AgentSpec("essentiality_claim_chart", "Essentiality Claim Chart", "ip", "Chart-type-classified AICC claim chart — claim text + standard + version gates (never '0 of 0', never 'referenced standard') → atomic claim limitations, dependent claims inherit their parent's limitations → standard clause classification (mandatory/conditional/optional/recommended/informative/example/deprecated/profile-specific/implementation-dependent/unclear) → limitation×clause mapping with evidence-based feature-match labels (direct/partial/optional/not-found/unclear) → five-level essentiality positions (potentially essential/conditional/not shown/not mapped/uncertain) → ETSI-style essentiality test → Tier 1–5 source hierarchy (regulatory & patent-office sources are context, never clause evidence) → version/release & evidence-freeze management + template-only export gate. Never a legal opinion.", icon="map"),
    AgentSpec("formulation", "Formulation", "materials", "Regulatory-first formulation hypotheses — product classification gate, objective & constraints, ingredient identity-to-function mapping, evidence-classified candidates with a single main-strategy change per comparison, concentration audit (sourced vs derived vs proposed screening range), process definitions without vague labels, four-type stability + ICH Q1A study design, microbial preservation and compatibility evidence, manufacturability not asserted without protocol + CPPs + CQAs + batches, per-jurisdiction regulatory pathway only after classification, claims wording audit, transparent decision weights and controlled bench-testing plans for every candidate.", icon="flask"),
    AgentSpec("materials_find_solutions", "Find Solutions (Materials)", "materials", "Evidence-based material problem solving — problem intake & classification, root-cause tree (material/process/product/supply) with confirmation gating, current-material characterization, ICH Q8(R2) CMA-CPP-CQA mapping, real candidate alternatives (MS-001/002, never Alternative-1/2) with grade, loading, mechanism, trade-offs and validation plan, compatibility/cost/regulatory/IP review where every claim needs a basis, risk classification per category, and controlled multi-batch validation experiments (MAT-EX) with DOE options.", icon="layers"),
]

REGISTRY = AgentRegistry(specs=_AGENT_SPECS)
AGENT_COUNT = len(_AGENT_SPECS)
AGENT_SLUGS = tuple(s.slug for s in _AGENT_SPECS)


def get_registry() -> AgentRegistry:
    return REGISTRY
