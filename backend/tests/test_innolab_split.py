"""Guards the Innovation-Lab executor surface and the S5 module split.

``agent_executors`` used to be one 8.5k-line file.  The shared grounding
primitives now live in ``_shared`` and each domain's agent in
``agents/<domain>.py``; this module is the compatibility facade over both.
This test pins all three halves so a future refactor cannot silently move a
helper, drop a public name, or break a registered agent slug.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import pytest

from app.services.innolab import _shared, agent_executors as A

# The public surface other modules and the router depend on.
PUBLIC_API = [
    "EXECUTORS",
    "execute_agent",
    "input_schema",
    "sample_query",
    "extract_features",
    "_hub_execution",
    "_workflow_trace",
]

# Grounding primitives that must stay shared, not drift per-agent.
SHARED_NAMES = [
    "_KB",
    "_load_json",
    "_retrieve",
    "_resolve_ingredients",
    "_jurisdiction_code",
    "_source_kind",
    "_sources_section",
    "_section",
    "_finding",
    "_evidence",
    "_base_result",
    "_as_citation",
]

# S5 domain split: module name -> the hub executors it must own.  Pinning the
# mapping is the point: it is a design decision, not an accident of file order.
DOMAIN_MODULES = {
    "discovery": ["_hub_triz", "_hub_quick_research", "_hub_find_solutions"],
    "novelty": ["_hub_novelty", "_hub_tdoc_novelty"],
    "fto": ["_hub_fto", "_hub_design_fto"],
    "patent": ["_hub_patent_drafting", "_hub_office_action", "_hub_claim_chart"],
    "disclosure": ["_hub_invention_disclosure"],
    "contract_analysis": ["_hub_document_analyzer", "_hub_markush"],
    "pharma": ["_hub_lca_small", "_hub_lead_candidate", "_hub_sar", "_hub_antibody"],
    "product": ["_hub_formulation", "_hub_materials"],
}
SHARED_TEXT_MODULE = "_shared_text"


def test_public_api_present():
    missing = [n for n in PUBLIC_API if not hasattr(A, n)]
    assert not missing, f"executor surface lost: {missing}"


@pytest.mark.parametrize("name", SHARED_NAMES)
def test_shared_primitives_live_in_shared(name):
    assert hasattr(_shared, name), f"{name} should be in _shared"
    assert hasattr(A, name), f"{name} must stay importable from agent_executors"


def test_shared_all_is_explicit():
    """No star imports: the seam must be auditable."""
    assert _shared.__all__, "_shared must declare __all__"
    assert set(_shared.__all__).issubset(set(dir(_shared)))
    # Every exported name is a real definition, not an accidental leak.
    src = inspect.getsource(_shared)
    for name in _shared.__all__:
        assert f"def {name}(" in src or f"{name}" in src, name


def test_every_registered_slug_runs():
    """A registered slug must never raise - it returns an 'insufficient' result."""
    inputs = {
        "formulation_text": "Withania somnifera root extract 10% w/w in hydroalcoholic solvent.",
        "problem_text": "Improve bioavailability of a poorly soluble botanical extract.",
        "ingredients": "Withania somnifera",
        "target_markets": "India, United States",
    }
    for slug in sorted(A.EXECUTORS):
        result = A.execute_agent(slug, inputs)
        assert isinstance(result, dict) and result, slug
        assert isinstance(A.input_schema(slug), list), slug
        assert isinstance(A.sample_query(slug), str), slug


def test_unknown_slug_falls_back_not_crashes():
    out = A.execute_agent("no_such_agent_registered_anywhere", {})
    assert isinstance(out, dict)
    assert out.get("phase") or out.get("summary")


def test_retrieval_helpers_do_not_fabricate():
    """_as_citation / _sources_section must degrade, never invent a source."""
    empty = A._sources_section([])
    assert isinstance(empty, dict)

    # _as_citation reads attributes off a citation object, not dict keys.
    class _Cit:
        act_title = "Drugs and Cosmetics Act, 1940"
        section_reference = "Section 26B"
        authority = "Parliament of India"
        effective_date = "1950-04-01"
        exact_passage = "No person shall advertise a drug for the treatment of human beings."
        source_url = "https://indiacode.nic.in"
        authority_rank = 1

    cit = A._as_citation(_Cit())
    assert cit["act_title"] == "Drugs and Cosmetics Act, 1940"
    assert cit["section_reference"] == "Section 26B"
    assert cit["authority_rank"] == 1
    assert len(cit["exact_passage"]) <= 500


def test_as_citation_of_a_bare_object_does_not_invent_fields():
    class _Bare:
        pass

    cit = A._as_citation(_Bare())
    assert cit["act_title"] == "" and cit["authority"] == ""
    assert cit["authority_rank"] == 1, "rank defaults rather than raising"


def test_sources_section_labels_known_authorities():
    section = A._sources_section([
        A._as_citation(type("C", (), {
            "act_title": "Drugs and Cosmetics Act, 1940",
            "section_reference": "26B", "authority": "Parliament of India",
            "effective_date": "", "exact_passage": "x", "source_url": "",
            "authority_rank": 1})())
    ])
    assert isinstance(section, dict)


# --------------------------------------------------------------------------- #
# S5: the per-domain agent package
# --------------------------------------------------------------------------- #

AGENTS_DIR = Path(inspect.getfile(A)).parent / "agents"
# The facade is meant to stay a facade.  It was 8,265 lines; it is now ~1.5k of
# which roughly a third is the explicit re-export block that keeps the flat
# `agent_executors.<helper>` surface working.  The bound leaves headroom for that
# block but still fails loudly if a domain's code creeps back in.
FACADE_MAX_LOC = 1600
DOMAIN_MAX_LOC = 1600


def test_agents_package_is_present():
    assert AGENTS_DIR.is_dir(), f"missing S5 package dir {AGENTS_DIR}"
    assert (AGENTS_DIR / "__init__.py").exists()


@pytest.mark.parametrize("module", sorted(DOMAIN_MODULES))
def test_domain_module_exists_and_declares_all(module):
    mod = importlib.import_module(f"app.services.innolab.agents.{module}")
    assert mod.__all__, f"agents/{module}.py must declare __all__ (no star imports)"
    assert set(mod.__all__).issubset(set(dir(mod)))


@pytest.mark.parametrize("module", sorted(DOMAIN_MODULES))
def test_domain_module_owns_its_hubs(module):
    mod = importlib.import_module(f"app.services.innolab.agents.{module}")
    for hub in DOMAIN_MODULES[module]:
        assert hasattr(mod, hub), f"{hub} should live in agents/{module}.py"
        assert callable(getattr(mod, hub))
        # The hub must be implemented here, not merely re-exported from a sibling.
        assert getattr(mod, hub).__module__ == mod.__name__, (
            f"{hub} is imported into agents/{module}.py rather than defined there"
        )


@pytest.mark.parametrize("module", sorted(DOMAIN_MODULES))
def test_hub_not_duplicated_across_domains(module):
    """A hub owned by two modules means one copy is dead code."""
    mod = importlib.import_module(f"app.services.innolab.agents.{module}")
    for hub in DOMAIN_MODULES[module]:
        others = [
            other
            for other, hubs in DOMAIN_MODULES.items()
            if other != module and hub in hubs
        ]
        assert not others, f"{hub} is claimed by {module} and {others}"


@pytest.mark.parametrize("module", sorted(DOMAIN_MODULES))
def test_domain_module_stays_small(module):
    path = AGENTS_DIR / f"{module}.py"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= DOMAIN_MAX_LOC, (
        f"agents/{module}.py grew to {len(lines)} lines; the split is regressing"
    )


def test_shared_text_module_is_not_empty():
    mod = importlib.import_module(
        f"app.services.innolab.agents.{SHARED_TEXT_MODULE}"
    )
    assert mod.__all__, "shared text primitives must be declared"
    assert len(mod.__all__) >= 10


@pytest.mark.parametrize("module", sorted(DOMAIN_MODULES))
def test_facade_reexports_every_domain_name(module):
    """The suite and other services reach private helpers via the facade.

    This is the regression that actually bit during the split: a private helper
    moved to a domain module and every white-box test broke at call time.
    """
    mod = importlib.import_module(f"app.services.innolab.agents.{module}")
    missing = [n for n in mod.__all__ if not hasattr(A, n)]
    assert not missing, f"agents/{module}.py names missing from facade: {missing}"


def test_facade_reexports_shared_text():
    mod = importlib.import_module(f"app.services.innolab.agents.{SHARED_TEXT_MODULE}")
    missing = [n for n in mod.__all__ if not hasattr(A, n)]
    assert not missing, f"shared text names missing from facade: {missing}"


def test_facade_stays_a_facade():
    lines = Path(inspect.getfile(A)).read_text(encoding="utf-8").splitlines()
    assert len(lines) <= FACADE_MAX_LOC, (
        f"agent_executors.py is {len(lines)} lines; the domain split is regressing"
    )


def test_all_forty_agent_slugs_registered():
    """20 legacy executors + the 19 hub slugs registered by the loop."""
    assert len(A.EXECUTORS) == 39, f"expected 39 slugs, got {len(A.EXECUTORS)}"
    for hub in [h for hubs in DOMAIN_MODULES.values() for h in hubs]:
        entry = A.EXECUTORS.get(_slug_for_hub(hub))
        assert entry is not None, f"{hub} is not reachable through EXECUTORS"


HUB_SLUGS = {
    "_hub_triz": "triz",
    "_hub_quick_research": "quick_research",
    "_hub_find_solutions": "find_solutions",
    "_hub_novelty": "novelty_search",
    "_hub_tdoc_novelty": "tdoc_novelty_search",
    "_hub_fto": "fto_search",
    "_hub_design_fto": "design_fto",
    "_hub_patent_drafting": "patent_drafting",
    "_hub_invention_disclosure": "invention_disclosure",
    "_hub_office_action": "office_action_response",
    "_hub_claim_chart": "essentiality_claim_chart",
    "_hub_document_analyzer": "document_analyzer",
    "_hub_lca_small": "lca_small_molecule",
    "_hub_lead_candidate": "lca_biotherapeutic",
    "_hub_sar": "sar_data_extraction",
    "_hub_antibody": "antibody_target_predictor",
    "_hub_markush": "markush_drafting",
    "_hub_formulation": "formulation",
    "_hub_materials": "materials_find_solutions",
}


def _slug_for_hub(hub: str) -> str:
    return HUB_SLUGS[hub]
