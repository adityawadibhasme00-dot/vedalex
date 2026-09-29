"""Provision cross-reference graph tests.

The graph exists to stop an exception or a definition from being invisible when
only the parent provision was retrieved. These tests pin the three properties
that make it safe to use in an answer:

  1. Edges are grounded — no dangling endpoints, no invented provisions.
  2. Only current law reaches the answer — superseded and out-of-window
     provisions are flagged and withheld.
  3. A graph pointer is never counted as independent evidence, and it can never
     drag a foreign legal regime into a domestic answer.
"""

import json
import os
from datetime import date

import pytest

from app.services import provision_graph as pg


@pytest.fixture(autouse=True)
def _fresh_graph():
    pg.reset_cache()
    yield
    pg.reset_cache()


# --------------------------------------------------------------------------
# Data integrity
# --------------------------------------------------------------------------

def test_every_edge_endpoint_resolves_to_a_real_provision():
    graph = pg.get_graph()
    for provision_id, records in graph["out_edges"].items():
        assert provision_id in graph["provisions"], provision_id
        for record in records:
            assert record["to"] in graph["provisions"], record["to"]


def test_no_self_edges():
    for provision_id in pg.get_graph()["out_edges"]:
        for record in pg.out_edges(provision_id):
            assert record["to"] != provision_id


def test_every_provision_declares_a_citation_locator():
    for provision_id, prov in pg.get_graph()["provisions"].items():
        assert prov.get("citation_locator"), provision_id
        assert prov.get("jurisdiction"), provision_id


def test_graph_loads_without_error():
    assert pg.available()
    assert pg.get_graph()["load_error"] is None


# --------------------------------------------------------------------------
# Traversal
# --------------------------------------------------------------------------

def test_dshea_reaches_drug_definition_and_nda():
    """The core scenario: DSHEA retrieved alone must surface the drug carve-out."""
    result = pg.expand([("ACT-US-FDA-1994-DSHEA", "")])
    linked = {e["provision_id"]: e["edge_type"] for e in result["linked"]}
    assert linked["ACT-US-FDCA-321G1B"] == "definition"
    assert linked["ACT-US-FDCA-355-NDA"] == "cross_reference"


def test_section_3p_reaches_botanical_derived_and_disclosure_provisions():
    result = pg.expand([("ACT-IN-PATENT-1970-SEC3P", "")])
    linked = {e["provision_id"] for e in result["linked"]}
    assert "ACT-IN-BD-2002-S6" in linked
    assert "ACT-IN-PATENT-1970-S10-4D-II" in linked


def test_traversal_is_bounded_by_max_depth():
    """Transitive expansion must terminate, not walk the whole graph."""
    result = pg.expand([("ACT-IN-GI-1999-S3", "")], max_depth=1)
    depths = {e["depth"] for e in result["linked"]}
    assert depths <= {1}


def test_traversal_reaches_a_fixed_point_on_an_acyclic_graph():
    """Deeper expansion adds nothing once the reachable set is exhausted."""
    one = frozenset(
        e["provision_id"] for e in pg.expand([("ACT-US-FDA-1994-DSHEA", "")], max_depth=1)["linked"]
    )
    three = frozenset(
        e["provision_id"] for e in pg.expand([("ACT-US-FDA-1994-DSHEA", "")], max_depth=3)["linked"]
    )
    assert one == three


def test_cycle_terminates_instead_of_recursing_forever(monkeypatch, tmp_path):
    """A -> B -> A must not loop; each provision is visited at most once."""
    def prov(pid):
        return {
            "provision_id": pid, "label": pid, "summary": pid,
            "jurisdiction": "India", "authority": "Test", "authority_level": 1,
            "citation_locator": pid, "status": "active",
            "effective_from": "2000-01-01", "effective_to": None,
            "verification_status": "unverified", "source_url": "",
        }

    def edge(a, b):
        return {
            "from": a, "type": "cross_reference", "to": b,
            "basis": "test fixture", "citation_locator": b,
            "verification_status": "unverified",
        }

    data = {
        "provisions": [prov("A"), prov("B"), prov("C")],
        "edges": [edge("A", "B"), edge("B", "C"), edge("C", "A")],
    }
    target = tmp_path / "provision_graph.json"
    target.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(pg, "GRAPH_FILE", str(target))
    pg.reset_cache()

    result = pg.expand([("A", "")], max_depth=50)
    visited = [e["provision_id"] for e in result["linked"]]
    assert set(visited) == {"B", "C"}
    assert len(visited) == len(set(visited)), "a provision was expanded twice"


def test_edge_type_filter_excludes_unwanted_relations():
    result = pg.expand(
        [("ACT-US-FDA-1994-DSHEA", "")], edge_types=("definition",)
    )
    assert {e["edge_type"] for e in result["linked"]} == {"definition"}


def test_leaf_provision_expands_to_nothing():
    result = pg.expand([("ACT-US-FDCA-321G1B", "")])
    assert result["linked"] == []


def test_unknown_provision_degrades_without_raising():
    result = pg.expand([("ACT-DOES-NOT-EXIST", "")])
    assert result["matched"] == []
    assert result["linked"] == []


# --------------------------------------------------------------------------
# Temporal correctness
# --------------------------------------------------------------------------

def test_provision_current_on_its_own_effective_date():
    # 21 U.S.C. 321(g)(1)(B) took effect with the 1938 FD&C Act.
    assert pg.is_current("ACT-US-FDCA-321G1B", as_of=date(1938, 6, 25))


def test_provision_not_current_before_it_took_effect():
    assert not pg.is_current("ACT-US-FDCA-321G1B", as_of=date(1930, 1, 1))
    assert not pg.is_current("ACT-IN-PATENT-1970-SEC3P", as_of=date(2004, 1, 1))


def test_closed_window_is_not_current_even_with_active_status(monkeypatch, tmp_path):
    """A window that closed is not current even if status was never updated."""
    data = json.loads(open(pg.GRAPH_FILE, encoding="utf-8").read())
    for prov in data["provisions"]:
        if prov["provision_id"] == "ACT-US-FDCA-321G1B":
            prov["effective_to"] = "1994-01-01"
    target = tmp_path / "provision_graph.json"
    target.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(pg, "GRAPH_FILE", str(target))
    pg.reset_cache()

    assert pg.is_current("ACT-US-FDCA-321G1B", as_of=date(1990, 1, 1))
    assert not pg.is_current("ACT-US-FDCA-321G1B", as_of=date(2000, 1, 1))


def test_superseded_provision_is_never_current(monkeypatch, tmp_path):
    data = json.loads(open(pg.GRAPH_FILE, encoding="utf-8").read())
    for prov in data["provisions"]:
        if prov["provision_id"] == "ACT-US-FDCA-321G1B":
            prov["status"] = "superseded"
    target = tmp_path / "provision_graph.json"
    target.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(pg, "GRAPH_FILE", str(target))
    pg.reset_cache()

    assert not pg.is_current("ACT-US-FDCA-321G1B")


def test_stale_provisions_are_reported_not_cited():
    """A pre-effective-date lookup must surface the staleness, not hide it."""
    result = pg.expand([("ACT-US-FDCA-321G1B", "")], as_of=date(1930, 1, 1))
    assert any(
        s["provision_id"] == "ACT-US-FDCA-321G1B" for s in result["stale"]
    )
    assert any("not current law" in t for t in result["traversal"])


# --------------------------------------------------------------------------
# Joining retrieved chunks to the graph
# --------------------------------------------------------------------------

def test_expand_for_sources_accepts_a_single_provision_id():
    result = pg.expand_for_sources(
        [{"provision_id": "ACT-US-FDA-1994-DSHEA", "citation_locator": "Pub. L. 103-417"}]
    )
    assert len(result["matched"]) == 1
    assert result["matched"][0]["citation_locator"] == "Pub. L. 103-417"


def test_expand_for_sources_accepts_a_list_of_provision_ids():
    """One Act record can back several provisions."""
    result = pg.expand_for_sources(
        [{"provision_id": ["ACT-IN-PATENT-1970-SEC3P", "ACT-IN-BD-2002-S6"]}]
    )
    assert {m["provision_id"] for m in result["matched"]} == {
        "ACT-IN-PATENT-1970-SEC3P", "ACT-IN-BD-2002-S6",
    }


def test_expand_for_sources_skips_chunks_without_provision_identity():
    result = pg.expand_for_sources(
        [{"content": "some legacy chunk"}, {"provision_id": ""}, {}]
    )
    assert result["matched"] == []


def test_expand_for_sources_ignores_malformed_entries():
    result = pg.expand_for_sources([None, "string", 42, {"provision_id": [None, 7]}])
    assert result["matched"] == []


# --------------------------------------------------------------------------
# Corpus-record join (ingestion side)
# --------------------------------------------------------------------------

def test_exact_provision_id_wins_over_parent_record():
    assert pg.provisions_for_record("ACT-IN-PATENT-1970-SEC3P") == [
        "ACT-IN-PATENT-1970-SEC3P"
    ]


def test_parent_record_maps_to_every_provision_it_backs():
    """The FD&C Act record covers both 321(g)(1)(B) and 355."""
    assert pg.provisions_for_record("ACT-US-FDA-FDCA-DRUG") == [
        "ACT-US-FDCA-321G1B", "ACT-US-FDCA-355-NDA",
    ]


def test_unknown_record_maps_to_nothing_rather_than_guessing():
    assert pg.provisions_for_record("ACT-NOT-IN-GRAPH") == []
    assert pg.provisions_for_record("") == []


# --------------------------------------------------------------------------
# Source adapter
# --------------------------------------------------------------------------

def test_provision_to_source_is_marked_graph_derived():
    src = pg.provision_to_source("ACT-US-FDCA-321G1B")
    assert src is not None
    assert src["graph_derived"] is True
    assert src["provision_id"] == "ACT-US-FDCA-321G1B"
    assert src["citation_locator"]
    assert src["jurisdiction"] == "United States"


def test_provision_to_source_preserves_the_relationship_that_reached_it():
    entry = pg.expand([("ACT-US-FDA-1994-DSHEA", "")])["linked"][0]
    src = pg.provision_to_source(entry["provision_id"], entry)
    assert src["graph_edge_type"] == entry["edge_type"]
    assert src["graph_via"] == "ACT-US-FDA-1994-DSHEA"


def test_provision_to_source_returns_none_for_unknown_provision():
    assert pg.provision_to_source("ACT-NOPE") is None


# --------------------------------------------------------------------------
# Graceful degradation
# --------------------------------------------------------------------------

def test_missing_graph_file_degrades_to_empty(monkeypatch):
    monkeypatch.setattr(
        pg, "GRAPH_FILE", os.path.join("does", "not", "exist.json")
    )
    pg.reset_cache()
    assert not pg.available()
    assert pg.expand([("ACT-US-FDA-1994-DSHEA", "")])["linked"] == []


def test_corrupt_graph_file_degrades_to_empty(monkeypatch, tmp_path):
    bad = tmp_path / "provision_graph.json"
    bad.write_text("{ this is not json", encoding="utf-8")
    monkeypatch.setattr(pg, "GRAPH_FILE", str(bad))
    pg.reset_cache()
    assert not pg.available()
    assert pg.get_graph()["load_error"]


def test_edge_pointing_at_missing_provision_is_dropped(monkeypatch, tmp_path):
    """A dangling edge must not crash expansion or invent a provision."""
    data = json.loads(
        open(pg.GRAPH_FILE, encoding="utf-8").read()
    )
    data["edges"].append({
        "from": "ACT-US-FDA-1994-DSHEA",
        "type": "exception",
        "to": "ACT-GHOST-0000",
        "basis": "test fixture",
        "citation_locator": "nowhere",
        "verification_status": "unverified",
    })
    target = tmp_path / "provision_graph.json"
    target.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(pg, "GRAPH_FILE", str(target))
    pg.reset_cache()

    result = pg.expand([("ACT-US-FDA-1994-DSHEA", "")])
    assert all(e["provision_id"] != "ACT-GHOST-0000" for e in result["linked"])
    assert any(
        e["provision_id"] == "ACT-US-FDCA-321G1B" for e in result["linked"]
    ), "valid edges must survive alongside the dangling one"


# --------------------------------------------------------------------------
# Ingestion preserves provision identity
# --------------------------------------------------------------------------

def test_list_seed_is_indexed_per_record_not_as_one_blob():
    from app.ingestion.pipeline import _seed_units

    data = [
        {"id": "ACT-ONE", "title": "One"},
        {"id": "ACT-TWO", "title": "Two"},
    ]
    units = _seed_units(data)
    assert [k for k, _, _ in units] == ["ACT-ONE", "ACT-TWO"]
    assert "ACT-TWO" not in units[0][1]


def test_dict_seed_keeps_whole_file_behaviour():
    from app.ingestion.pipeline import _seed_units

    units = _seed_units({"a": "1", "b": "2"})
    assert len(units) == 1


def test_seed_record_keeps_its_own_jurisdiction():
    """Regression: every seed used to be tagged jurisdiction=India.

    That mislabelled the US and Canadian Acts as Indian law, so a US source
    survived an India filter as domestic evidence and was dropped from an
    International filter.
    """
    from app.ingestion.pipeline import _record_metadata

    dshea = _record_metadata(
        {"id": "ACT-US-FDA-1994-DSHEA", "jurisdiction": "United States"}, {}
    )
    assert dshea["jurisdiction"] == "United States"

    nhpr = _record_metadata(
        {"id": "ACT-CA-HC-2004-NHPR", "jurisdiction": "Canada"}, {}
    )
    assert nhpr["jurisdiction"] == "Canada"


def test_seed_record_joins_to_the_graph():
    from app.ingestion.pipeline import _record_metadata

    meta = _record_metadata(
        {"id": "ACT-IN-PATENT-1970-SEC3P", "jurisdiction": "India"}, {}
    )
    assert meta["provision_id"] == ["ACT-IN-PATENT-1970-SEC3P"]
    assert meta["effective_from"]
    assert meta["citation_locator"]
    assert meta["verification_status"]


def test_seed_record_inherits_provision_id_from_parent_record():
    from app.ingestion.pipeline import _record_metadata

    meta = _record_metadata(
        {"id": "ACT-US-FDA-FDCA-DRUG", "jurisdiction": "United States"}, {}
    )
    assert meta["provision_id"] == [
        "ACT-US-FDCA-321G1B", "ACT-US-FDCA-355-NDA",
    ]


def test_seed_record_without_provision_identity_is_left_alone():
    from app.ingestion.pipeline import _record_metadata

    meta = _record_metadata({"id": "SOME-OTHER-RECORD"}, {})
    assert "provision_id" not in meta


def test_ingestion_survives_a_broken_graph(monkeypatch):
    """The graph is additive; a failure in it must not stop ingestion."""
    from app.ingestion import pipeline

    def boom(_record_id):
        raise RuntimeError("graph exploded")

    monkeypatch.setattr(pg, "provisions_for_record", boom)
    meta = pipeline._record_metadata({"id": "ACT-IN-PATENT-1970-SEC3P"}, {})
    assert "provision_id" not in meta


# --------------------------------------------------------------------------
# Orchestration: the properties that keep this safe in a live answer
# --------------------------------------------------------------------------

def _dshea_source(**kw):
    base = {
        "content": "DSHEA dietary supplement definition and new dietary "
                   "ingredient rules for botanical claims.",
        "source": "FDA",
        "title": "DSHEA 1994",
        "authority": "FDA",
        "authority_level": 1,
        "category": "statutory",
        "jurisdiction": "United States",
        "source_url": "https://www.fda.gov/dshea",
        "provision_id": ["ACT-US-FDA-1994-DSHEA"],
    }
    base.update(kw)
    return base


def _run(query, sources, mode):
    from app.services.multi_layer_orchestrator import MultiLayerOrchestrator as M

    return M.run(query, retrieved_sources=sources, context={"jurisdiction": mode})


QUERY = "novel botanical ingredient dietary supplement DSHEA rules"


def test_cross_reach_the_answer_with_their_relation():
    result = _run(QUERY, [_dshea_source()], "International")
    xrefs = {x["provision_id"]: x["relation"] for x in result["cross_references"]}
    assert xrefs["ACT-US-FDCA-321G1B"] == "definition"
    assert xrefs["ACT-US-FDCA-355-NDA"] == "cross_reference"
    for x in result["cross_references"]:
        assert x["reached_from"] == "ACT-US-FDA-1994-DSHEA"
        assert x["citation_locator"]


def test_cross_references_are_never_mixed_into_the_cited_sources():
    """They are graph pointers, not retrieved documents, so they must not be
    presented in the citation list the judge reads."""
    result = _run(QUERY, [_dshea_source()], "International")
    cited = {
        pid
        for s in result["sources"]
        for pid in (s.get("provision_id") if isinstance(s.get("provision_id"), list)
                    else [s.get("provision_id")])
    }
    assert "ACT-US-FDCA-321G1B" not in cited
    assert "ACT-US-FDCA-355-NDA" not in cited
    assert "ACT-US-FDA-1994-DSHEA" in cited


def test_cross_references_do_not_inflate_confidence():
    """A graph lookup must never manufacture High Confidence."""
    with_id = _run(QUERY, [_dshea_source()], "International")
    without_id = _run(QUERY, [_dshea_source(provision_id=None)], "International")
    assert with_id["confidence"] == without_id["confidence"]


def test_cross_references_cannot_cross_the_jurisdiction_boundary():
    """A US cross-reference must never surface in an India-framework answer."""
    result = _run(QUERY, [_dshea_source()], "India")
    assert result["cross_references"] == []


def test_graph_traversal_is_recorded_in_the_decision_trace():
    result = _run(QUERY, [_dshea_source()], "International")
    layers = result["decision_trace"]["pipeline"]["layer_flow"]
    entry = next(
        (s for s in layers if "Cross-Reference" in s["layer"]), None
    )
    assert entry is not None
    assert entry["status"] == "PASS"
    assert "not counted as independent votes" in entry["detail"]


def test_provision_graph_file_is_never_indexed_as_retrievable_text():
    """The graph holds internal IDs and edge records, not statutory wording.

    If it were indexed, a judge could be shown a raw edge record as though it
    were legal text.
    """
    from app.ingestion.pipeline import NON_RETRIEVABLE_SEED_FILES

    assert "provision_graph" in NON_RETRIEVABLE_SEED_FILES
    assert "corpus_manifest" in NON_RETRIEVABLE_SEED_FILES


def test_query_with_no_provisions_is_unaffected():
    """Corpus chunks without provision identity must change nothing."""
    result = _run(QUERY, [_dshea_source(provision_id=None)], "International")
    assert result["cross_references"] == []
    assert result["superseded_provisions"] == []
