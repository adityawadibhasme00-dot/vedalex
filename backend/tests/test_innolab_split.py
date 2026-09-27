"""Guards the Innovation-Lab executor surface and the S5 module split.

``agent_executors`` used to be one 8.5k-line file.  The shared grounding
primitives now live in ``_shared``; this test pins both halves so a future
refactor cannot silently move a helper, drop a public name, or break a
registered agent slug.
"""

from __future__ import annotations

import inspect

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
