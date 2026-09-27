"""Tests for the Agent Hub tool router toolbox (retrieval and file IO mocked)."""

from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest

from app.services.agent_hub import toolbox as tb

pytestmark = pytest.mark.unit


def test_vec_search_maps_passages_and_forwards_options():
    citation = SimpleNamespace(
        act_title="The Patents Act, 1970",
        section_reference="Section 3",
        authority="Legislative Department",
        effective_date="1970-04-20",
        exact_passage="p" * 600,
        source_url="https://example.test/patents-act/section/3",
        authority_rank=1,
    )
    with patch.object(
        tb.HybridRetrievalEngine, "search_passages", return_value=[citation]
    ) as mock_search:
        hits = tb.vec_search("traditional knowledge", jurisdiction="IN", top_k=2, min_score=1.5)

    mock_search.assert_called_once_with(
        "traditional knowledge", jurisdiction="IN", top_k=2, min_score=1.5
    )
    assert hits == [
        {
            "act_title": "The Patents Act, 1970",
            "section_reference": "Section 3",
            "authority": "Legislative Department",
            "effective_date": "1970-04-20",
            "exact_passage": "p" * 500,
            "source_url": "https://example.test/patents-act/section/3",
            "authority_rank": 1,
        }
    ]


def test_vec_search_defaults_missing_passage_attributes():
    with patch.object(tb.HybridRetrievalEngine, "search_passages", return_value=[SimpleNamespace()]):
        hits = tb.vec_search("query")

    assert hits == [
        {
            "act_title": "",
            "section_reference": "",
            "authority": "",
            "effective_date": "",
            "exact_passage": "",
            "source_url": "",
            "authority_rank": 1,
        }
    ]


def test_vec_search_blank_query_short_circuits():
    with patch.object(tb.HybridRetrievalEngine, "search_passages") as mock_search:
        assert tb.vec_search("") == []
        assert tb.vec_search("   ") == []

    mock_search.assert_not_called()


def test_characterization_vec_search_returns_empty_list_when_retriever_fails():
    with patch.object(
        tb.HybridRetrievalEngine, "search_passages", side_effect=RuntimeError("index down")
    ):
        assert tb.vec_search("traditional knowledge") == []


def test_bm25_rank_orders_by_overlap_and_limits_results():
    documents = [
        "Ashwagandha root powder is used in supplements",
        "entirely unrelated wording about coatings",
        "ashwagandha extract capsule for wellness",
    ]
    ranked = tb.bm25_rank("ashwagandha extract", documents, top_k=2)

    assert len(ranked) == 2
    assert ranked[0]["index"] == 2
    assert ranked[0]["rank"] == 1
    assert ranked[0]["score"] > ranked[1]["score"]
    assert ranked[1]["index"] == 0
    assert ranked[0]["snippet"] == documents[2][:500]


def test_bm25_rank_truncates_long_snippets():
    long_doc = "alpha " + "y" * 600
    ranked = tb.bm25_rank("alpha", [long_doc])

    assert len(ranked[0]["snippet"]) == 500


def test_bm25_rank_empty_inputs_return_no_results():
    assert tb.bm25_rank("", ["alpha doc"]) == []
    assert tb.bm25_rank("alpha", []) == []
    assert tb.bm25_rank("alpha", ["no overlap at all"]) == []


def test_knowledge_ingredient_resolves_known_botanical():
    bioresource = [
        {"canonical_id": "ING-SOMETHING-ELSE", "conservation_status": "irrelevant"},
        {"canonical_id": "ING-ASHWAGANDHA", "conservation_status": "Least Concern"},
    ]
    with patch.object(tb, "_load_json", return_value=bioresource):
        result = tb.knowledge_ingredient("Ashwagandha")

    assert result["resolved"] is True
    assert result["raw_name"] == "Ashwagandha"
    assert result["canonical_id"] == "ING-ASHWAGANDHA"
    assert result["api_monograph_id"] == "API-VOL1-008"
    assert result["botanical_name"] == "Withania somnifera (L.) Dunal"
    assert result["family"] == "Solanaceae"
    assert result["classical_therapeutic_uses"]
    assert result["fssai_aahara_status"] == "permitted"
    assert result["us_fda_ndi_status"] == "old_dietary_ingredient"
    assert result["canada_nhpid_status"] == "monographed"
    assert result["conservation_status"] == "Least Concern"
    assert result["resolution_confidence"] == 0.98


def test_knowledge_ingredient_without_bioresource_entry_has_empty_conservation():
    with patch.object(tb, "_load_json", return_value=[]):
        result = tb.knowledge_ingredient("Ashwagandha")

    assert result["resolved"] is True
    assert result["conservation_status"] == ""


def test_knowledge_ingredient_reports_unresolved_name():
    result = tb.knowledge_ingredient("unobtainium salt")

    assert result == {"raw_name": "unobtainium salt", "resolved": False}


def test_knowledge_ingredient_survives_resolver_failure():
    with patch.object(
        tb.IngredientResolverService, "resolve", side_effect=RuntimeError("corpus missing")
    ):
        result = tb.knowledge_ingredient("Ashwagandha")

    assert result == {"raw_name": "Ashwagandha", "resolved": False}


def test_semantic_match_ranks_and_drops_zero_overlap():
    candidates = ["ashwagandha root powder", "zinc oxide"]
    matches = tb.semantic_match("ashwagandha root", candidates)

    assert len(matches) == 1
    assert matches[0]["text"] == "ashwagandha root powder"
    assert matches[0]["similarity"] == 0.667


def test_semantic_match_truncates_long_candidates():
    long_candidate = "ashwagandha " + "z" * 400
    matches = tb.semantic_match("ashwagandha", [long_candidate])

    assert len(matches[0]["text"]) == 300


def test_semantic_match_empty_inputs_return_no_results():
    assert tb.semantic_match("ashwagandha", []) == []
    assert tb.semantic_match("ashwagandha", ["zinc oxide"]) == []


def test_extract_features_returns_feature_segments():
    features = tb.extract_features("Ashwagandha root, Brahmi whole plant, Curcumin extract")

    assert features == [
        "Ashwagandha root",
        "Brahmi whole plant",
        "Curcumin extract",
    ]


def test_extract_features_splits_around_claim_connectors():
    features = tb.extract_features("A extract comprising B extract and C oil")

    assert "A extract" in features
    assert "B extract and C oil" in features


def test_extract_features_caps_output_at_twelve_items():
    description = ", ".join(f"seg{index:02d} feature" for index in range(20))
    features = tb.extract_features(description)

    assert len(features) == 12


def test_extract_features_blank_inputs_return_no_features():
    assert tb.extract_features(cast(str, None)) == []
    assert tb.extract_features("") == []
    assert tb.extract_features("ab") == []


def test_rule_signal_flags_every_signal_in_one_claim():
    text = (
        "A composition comprising ashwagandha that cures disease, "
        "supports immunity, prepared using water as solvent"
    )
    signals = tb.rule_signal(text)

    assert signals == {
        "curative": True,
        "therapeutic_purpose": True,
        "solvent": True,
        "function_claim": True,
        "structure_claim": True,
    }


def test_rule_signal_is_all_false_for_neutral_text():
    signals = tb.rule_signal("Sugar free chewing gum")

    assert set(signals) == {
        "curative",
        "therapeutic_purpose",
        "solvent",
        "function_claim",
        "structure_claim",
    }
    assert not any(signals.values())


def test_rule_signal_handles_missing_claim_text():
    assert not any(tb.rule_signal(cast(str, None)).values())


def test_knowledge_graph_links_resolve_botanical_and_canonical_id():
    by_name = tb.knowledge_graph_links("Withania")
    assert by_name == [
        {
            "node": "Withania somnifera (L.) Dunal",
            "predicate": "family",
            "value": "Solanaceae",
        },
        {
            "node": "Withania somnifera (L.) Dunal",
            "predicate": "api_monograph",
            "value": "API-VOL1-008",
        },
        {
            "node": "Withania somnifera (L.) Dunal",
            "predicate": "classical_use",
            "value": "Kshaya, Daurbalya",
        },
    ]

    by_canonical_id = tb.knowledge_graph_links("ing-ashwagandha")
    assert [link["predicate"] for link in by_canonical_id] == [
        "family",
        "api_monograph",
        "classical_use",
    ]


def test_knowledge_graph_links_are_capped_at_six():
    assert len(tb.knowledge_graph_links("a")) == 6


def test_knowledge_graph_links_skip_monographs_without_classical_uses():
    monographs = [
        {
            "botanical_name": "Rauvolfia serpentina (L.) Benth. ex Kurz",
            "family": "Apocynaceae",
            "api_monograph_id": "API-VOL2-023",
        }
    ]
    with patch.object(tb, "_load_json", return_value=monographs):
        links = tb.knowledge_graph_links("Rauvolfia")

    assert [link["predicate"] for link in links] == ["family", "api_monograph"]
    assert links[0]["value"] == "Apocynaceae"


def test_load_json_returns_none_for_missing_knowledge_file():
    assert tb._load_json("no-such-knowledge-file.json") is None


def test_trend_analyze_ignores_stopwords():
    trends = tb.trend_analyze(["This formulation with water when tested"])
    terms = [trend["term"] for trend in trends]

    assert terms == ["formulation", "water", "tested"]
    assert "with" not in terms
    assert "when" not in terms


def test_trend_analyze_counts_terms_and_ignores_stopwords():
    trends = tb.trend_analyze(
        [
            "Ashwagandha extract helps. Ashwagandha is used.",
            "Brahmi and ashwagandha combined",
        ],
        top_k=2,
    )

    assert trends == [
        {"term": "ashwagandha", "occurrences": 3},
        {"term": "extract", "occurrences": 1},
    ]


def test_trend_analyze_empty_and_missing_texts_return_no_trends():
    assert tb.trend_analyze([]) == []
    assert tb.trend_analyze(["", cast(str, None)]) == []


def test_document_entities_reports_entities_without_sections():
    out = tb.document_entities("Ashwagandha extract helps with stress relief")

    assert out["sections"] == []
    assert out["entities"] == ["Ashwagandha"]
    assert out["measures"] == []


def test_normalize_document_collapses_whitespace():
    assert tb.normalize_document("  a\n\nb\t  c  ") == "a b c"
    assert tb.normalize_document("already clean") == "already clean"


def test_tool_catalog_entries_expose_name_kind_and_desc():
    assert len(tb.TOOL_CATALOG) == 10
    for entry in tb.TOOL_CATALOG:
        assert set(entry) == {"name", "kind", "desc"}
        assert entry["name"]
        assert entry["kind"]
        assert entry["desc"]


@pytest.mark.parametrize(
    "agent_slug,expected_first",
    [
        ("triz", "vec_search"),
        ("patent_drafting", "extract_features"),
        ("invention_disclosure", "document_entities"),
        ("formulation", "knowledge_ingredient"),
        ("unknown_agent_slug", "vec_search"),
    ],
)
def test_route_tools_returns_expected_tools(agent_slug, expected_first):
    tools = tb.route_tools(agent_slug)

    assert tools
    assert tools[0] == expected_first
    assert set(tools) <= {entry["name"] for entry in tb.TOOL_CATALOG}


@pytest.mark.xfail(
    reason="re.split keeps the capture group, so the connector word itself is reported as an extracted feature (toolbox.py:134)",
    strict=False,
)
def test_extract_features_never_reports_connector_words_as_features():
    features = tb.extract_features("A extract comprising B extract")

    assert "comprising" not in features


@pytest.mark.xfail(
    reason="the fallback path ignores the 120-character segment cap, so oversized segments are emitted (toolbox.py:144)",
    strict=False,
)
def test_extract_features_keeps_segments_within_length_cap():
    features = tb.extract_features("x" * 200)

    assert features
    assert all(3 <= len(segment) <= 120 for segment in features)


@pytest.mark.xfail(
    reason="negative top_k is never validated and is applied as a slice, silently dropping the top-ranked document (toolbox.py:74)",
    strict=False,
)
def test_bm25_rank_rejects_negative_top_k():
    documents = ["alpha one document", "alpha two document"]
    tb.bm25_rank("alpha", documents, top_k=-1)

    raise AssertionError("negative top_k must be rejected")


@pytest.mark.xfail(
    reason="an empty entity matches every monograph because '' in value is always True, so the graph tool returns links for an unrelated query (toolbox.py:166)",
    strict=False,
)
def test_knowledge_graph_links_rejects_empty_entity():
    assert tb.knowledge_graph_links("") == []


@pytest.mark.xfail(
    reason="curative patterns are matched as whole words only, so common inflections such as 'treats' are not flagged (toolbox.py:152)",
    strict=False,
)
def test_rule_signal_flags_inflected_curative_wording():
    assert tb.rule_signal("The formulation treats pain")["curative"] is True


@pytest.mark.xfail(
    reason="the measurement regex only captures the unit group, so '5%' becomes '' and '20 mg' becomes 'mg' (toolbox.py:194)",
    strict=False,
)
def test_document_entities_keeps_measured_values():
    out = tb.document_entities("Dose is 5% and 20 mg daily")

    assert out["measures"] == ["5%", "20 mg"]


@pytest.mark.xfail(
    reason="heading detection returns the raw '#' marker and the following body text as sections (toolbox.py:191)",
    strict=False,
)
def test_document_entities_returns_heading_labels_as_sections():
    out = tb.document_entities("# Method\nAshwagandha extract at 5% and 20 mg dose")

    sections = out["sections"]
    assert sections
    assert all(not section.startswith("#") for section in sections)
    assert all("\n" not in section for section in sections)


@pytest.mark.xfail(
    reason="normalize_document has no None guard unlike its sibling tools, so a missing OCR string raises TypeError (toolbox.py:200)",
    strict=False,
)
def test_normalize_document_handles_missing_text():
    assert tb.normalize_document(cast(str, None)) == ""
