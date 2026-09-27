"""Novelty-search workflow (Eureka-style pipeline) unit tests."""
import pytest

from app.rag.boolean_search import build_searches, invalidate_corpus_cache, search
from app.services.novelty_workflow import (
    _detect_ingredients,
    build_export_result,
    run_workflow,
)


@pytest.fixture(autouse=True)
def _fresh_corpus():
    invalidate_corpus_cache()
    yield


PROBLEM = (
    "A synergistic herbal formulation of Ashwagandha with Brahmi "
    "for cognitive wellness in capsule form for the Indian market"
)


def test_full_workflow_runs_and_grounds():
    wf = run_workflow(PROBLEM, target_markets=["India"], jurisdiction="IN")

    assert wf["status"] == "complete"
    steps = wf["steps"]
    assert set(steps) == {
        "1_summary", "2_features", "3_elements", "4_strategy",
        "5_reference_list", "6_comparison", "7_report",
    }

    feats = steps["2_features"]["features"]
    assert len(feats) >= 2
    kinds = {f["kind"] for f in feats}
    assert "ingredient" in kinds
    assert any(f["core"] for f in feats if f["kind"] == "ingredient")

    strategy = steps["4_strategy"]
    assert len(strategy["boolean"]) == 5
    assert {b["name"] for b in strategy["boolean"]} == {
        "Boolean Search 1", "Boolean Search 2", "Boolean Search 3",
        "Boolean Search 4", "Boolean Search 5",
    }

    refs = steps["5_reference_list"]
    assert refs["total"] >= 0
    if refs["tabs"]:
        tab_keys = [t["key"] for t in refs["tabs"]]
        assert set(tab_keys) <= {"patent", "paper", "internet", "official"}

    comp = steps["6_comparison"]
    for row in comp["rows"]:
        assert row["disclosure_level"] in {
            "Explicitly disclosed", "Broadly disclosed", "Partially disclosed",
            "Suggested only", "Not disclosed", "Unclear",
        }
        assert row["essentiality"] in {"essential", "optional"}
        assert 0 <= row["score"] <= 100
    assert comp["feature_coverage_m"] >= comp["feature_coverage_n"]
    assert comp["anticipation_risk"] in {"High", "Medium", "Low", "Unknown"}
    assert comp["feature_coverage"] == f"{comp['feature_coverage_n']}/{comp['feature_coverage_m']}"

    report = steps["7_report"]
    assert report["status"] == "complete"


def test_word_export_shape_builds():
    wf = run_workflow(PROBLEM, target_markets=["India"], jurisdiction="IN")
    result = build_export_result(wf)
    assert result["summary"]
    assert result["sections"]
    assert result["findings"]
    assert result["citations"]


def test_ingredient_detection_from_prose():
    hits = _detect_ingredients(PROBLEM)
    ids = {h["canonical_id"] for h in hits}
    assert ids >= {"ING-ASHWAGANDHA", "ING-BRAHMI"}
    assert not _detect_ingredients("a purely synthetic polymer blend for coatings")


@pytest.mark.parametrize("expr,expected_some", [
    ("ashwagandha", True),
    ("ashwagandha AND brahmi", True),
])
def test_boolean_engine_smoke(expr, expected_some):
    out = search(expr)
    hits = out["results"]
    if expected_some:
        assert out["matched"] > 0
    for h in hits:
        assert h.get("content")


def test_build_searches_shapes():
    plans = build_searches(PROBLEM, top_k=4, jurisdiction="IN")
    assert len(plans) == 5
    for p in plans:
        assert p["name"]
        assert p["expression"]
        assert isinstance(p["matched"], int)
        assert isinstance(p["results"], list)