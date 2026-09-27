from typing import Any

import pytest

from app.services.innolab import agent_executors as ae

LEGACY_SLUGS = [
    "idea_router",
    "formula_triage",
    "sensitivity_vault",
    "formulation_intel",
    "labeling_check",
    "prior_art_search",
    "prior_art_mapping",
    "novelty_engine",
    "claim_scope",
    "inventive_step",
    "regulatory_map",
    "approval_gate",
    "claim_catalyst",
    "evidence_quality",
    "commercial_playbook",
    "export_pathfinder",
    "proof_auditor",
    "risk_guard",
    "compliance_officer",
    "reviewer_coordinator",
]

HUB_SLUGS = [
    "triz",
    "quick_research",
    "find_solutions",
    "novelty_search",
    "fto_search",
    "design_fto",
    "patent_drafting",
    "invention_disclosure",
    "office_action_response",
    "essentiality_claim_chart",
    "tdoc_novelty_search",
    "document_analyzer",
    "lca_biotherapeutic",
    "lca_small_molecule",
    "sar_data_extraction",
    "antibody_target_predictor",
    "markush_drafting",
    "formulation",
    "materials_find_solutions",
]

ALL_SLUGS = LEGACY_SLUGS + HUB_SLUGS

RICH_INPUTS = {
    "problem_text": "Ashwagandha and Brahmi formulation for cognitive support and restful sleep",
    "formulation_text": "Ashwagandha root extract 20% w/w with Brahmi extract in a hydroalcoholic base",
    "ingredients": "Ashwagandha, Brahmi",
    "process_desc": "Hydroalcoholic extraction at 40 C for 3 h, filtration and drying to a dry powder",
    "proposed_claims": "supports restful sleep; aids digestion; cognitive support",
    "claim_wording": "A composition comprising Ashwagandha extract",
    "target_markets": ["India", "United States", "Canada"],
    "product_type": "nutraceutical tablet",
    "office_action_text": (
        "First Examination Report. Objection under novelty: claims 1-5 are not new per Article 54. "
        "The claim lacks inventive step and clarity; enablement objection under Article 83."
    ),
    "document_text": (
        "# OCR Output (Demo)\n"
        "Document Title: Stability report\n"
        "Assay result 12 mg/mL after 40 C for 3 h\n"
        "Page 1\n"
    ),
    "disclosure_text": "Inventor notes: hydroalcoholic extract of Ashwagandha at 40 C for 3 h with marker standardisation.",
    "material_challenge": "MCC caking and low flow observed in the blend",
    "current_material": "microcrystalline cellulose",
    "performance_target": "flow and dissolution",
    "antibody_desc": "Antibody binding IL-6 measured by SPR with Kd 3.2 nM and CDR H3 present",
    "compound_desc": "Compound 1; IC50 = 45 nM; C22H30O5; CAS 5000-00-0",
    "core_structure": "withanolide scaffold with R1 = alkyl and lactone ring",
    "variant_features": "R1 = methyl; n = 1",
    "standard_name": "IS 4000",
    "improve_aspect": "extraction yield",
    "tradeoff": "marker stability",
    "system_name": "extraction unit",
    "timeframe": "2020-2026",
    "application_number": "IN202411001",
    "response_deadline": "2026-01-01",
    "relevant_date": "2024-01-01",
    "prior_art_cutoff": "2023-12-01",
    "solvent_pref": "Hydroalcoholic",
    "consumables": "glassware",
    "regulatory_notes": "FSSAI category check pending",
    "file_id": "doc-1",
    "indication": "cognitive support",
    "target": "IL-6",
    "extracted_features": ["Ashwagandha extract", "hydroalcoholic solvent"],
}


def _assert_success_shape(result):
    assert result["ok"] is True
    assert isinstance(result["summary"], str) and result["summary"].strip()
    assert isinstance(result["note"], str) and result["note"].strip()
    assert isinstance(result["findings"], list)
    assert isinstance(result["sections"], list)
    assert isinstance(result["citations"], list)
    assert isinstance(result["suggestions"], list)


def test_all_registered_slugs_present_in_executor_table():
    for slug in ALL_SLUGS:
        assert slug in ae.EXECUTORS


def test_executor_table_has_no_extra_slugs():
    assert set(ae.EXECUTORS) == set(ALL_SLUGS)


@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_execute_agent_rich_inputs_success(slug):
    result = ae.execute_agent(slug, dict(RICH_INPUTS))
    _assert_success_shape(result)
    assert result["agent_slug"] == slug


@pytest.mark.parametrize(
    "slug",
    [s for s in ALL_SLUGS if s not in ("novelty_search", "tdoc_novelty_search")],
)
def test_execute_agent_empty_inputs_success(slug):
    result = ae.execute_agent(slug, {})
    _assert_success_shape(result)
    assert result["agent_slug"] == slug


@pytest.mark.parametrize("slug", HUB_SLUGS)
def test_hub_result_carries_execution_trace(slug):
    result = ae.execute_agent(slug, dict(RICH_INPUTS))
    assert isinstance(result["workflow"], list)
    assert result["workflow"]
    assert isinstance(result["tools_used"], list)
    assert isinstance(result["execution"], dict)
    assert isinstance(result["jurisdictions"], list)
    assert result["sections"][-1]["title"].startswith("Data sources")
    assert isinstance(result["evidence"], list)


@pytest.mark.parametrize("slug", HUB_SLUGS)
def test_hub_result_without_confirmed_features(slug):
    inputs = {k: v for k, v in RICH_INPUTS.items() if k != "extracted_features"}
    result = ae.execute_agent(slug, inputs)
    assert "User confirmed" not in result["execution"].get("validated", "")


@pytest.mark.parametrize("slug", [s for s in HUB_SLUGS if s != "patent_drafting"])
def test_hub_result_records_confirmed_extracted_features(slug):
    result = ae.execute_agent(slug, dict(RICH_INPUTS))
    assert "User confirmed 2 extracted feature(s)" in result["execution"]["validated"]


def test_patent_drafting_overrides_execution_trace():
    result = ae.execute_agent("patent_drafting", dict(RICH_INPUTS))
    assert "Patent drafting workflow resolved" in result["execution"]["planner"]
    assert "validation" in result["execution"]


@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_extract_features_all_slugs(slug):
    out = ae.extract_features(slug, dict(RICH_INPUTS))
    assert isinstance(out["summary"], str) and out["summary"].strip()
    assert isinstance(out["features"], list)
    assert len(out["features"]) <= 12
    for feature in out["features"]:
        assert feature["text"]
        assert feature["kind"] in ("ingredient", "keyword", "context")
    assert isinstance(out["markets"], list)
    assert isinstance(out["ingredients"], list)
    assert isinstance(out["resolved"], list)


def test_extract_features_resolves_known_ingredients():
    out = ae.extract_features("novelty_engine", {"ingredients": "Ashwagandha, Brahmi"})
    assert len(out["ingredients"]) == 2
    assert len(out["resolved"]) == 2
    assert out["resolved"][0].startswith("Withania")


def test_extract_features_empty_inputs_still_returns_understanding():
    out = ae.extract_features("idea_router", {})
    assert out["summary"].strip()
    assert out["markets"] == ["India", "United States", "Canada"]


def test_execute_agent_with_none_inputs_uses_empty_dict():
    payload: Any = None
    result = ae.execute_agent("idea_router", payload)
    _assert_success_shape(result)


def test_input_schema_known_slug():
    schema = ae.input_schema("idea_router")
    assert schema[0]["key"] == "problem_text"


def test_input_schema_unknown_slug_returns_default():
    schema = ae.input_schema("not_a_real_agent")
    keys = [f["key"] for f in schema]
    assert "problem_text" in keys
    assert "target_markets" in keys


def test_sample_query_known_and_unknown():
    assert "Ashwagandha" in ae.sample_query("idea_router")
    assert ae.sample_query("not_a_real_agent") == ""


def test_text_returns_first_non_blank_key():
    assert ae._text({"a": "  hello  ", "b": "world"}, "a", "b") == "hello"
    assert ae._text({"a": "   "}, "a") == ""
    assert ae._text({}, "a") == ""


def test_list_value_from_string_and_list():
    assert ae._list_value({"ingredients": "A, B; C"}, "ingredients") == ["A", "B", "C"]
    assert ae._list_value({"ingredients": [" A ", "", None]}, "ingredients") == ["A"]
    assert ae._list_value({}, "ingredients") == []


def test_basis_text_joins_lists_and_strips_strings():
    assert ae._basis_text({"k": ["a", " b "]}, "k") == "a,  b "
    assert ae._basis_text({"k": ["", "  "]}, "k") == ""
    assert ae._basis_text({"k": "  value "}, "k", "zz") == "value"
    assert ae._basis_text({}, "k") == ""


def test_markets_defaults_and_explicit():
    assert ae._markets({}) == ["India", "United States", "Canada"]
    assert ae._markets({"target_markets": "India"}) == ["India"]


def test_ingredient_names_from_string_list_and_formulation():
    assert ae._ingredient_names({"ingredients": "Ashwagandha, Brahmi"}) == ["Ashwagandha", "Brahmi"]
    assert ae._ingredient_names({"ingredients": ["Ashwagandha", "Brahmi"]}) == ["Ashwagandha", "Brahmi"]
    from_formula = ae._ingredient_names({"formulation_text": "Ashwagandha root extract, Brahmi extract"})
    assert from_formula


def test_resolve_ingredients_known_and_unknown():
    resolved = ae._resolve_ingredients(["Ashwagandha", "zzz-unknown-xyz"])
    assert resolved[0]["resolved"] is True
    assert resolved[0]["botanical_name"]
    assert resolved[1]["resolved"] is False
    assert resolved[1]["raw_name"] == "zzz-unknown-xyz"


def test_resolve_ingredients_deduplicates_case_insensitively():
    resolved = ae._resolve_ingredients(["Ashwagandha", "ashwagandha", "ashwagandha "])
    assert len(resolved) == 1


def test_jurisdiction_code_mapping():
    assert ae._jurisdiction_code("India") == "in"
    assert ae._jurisdiction_code("United States") == "us"
    assert ae._jurisdiction_code("Canada") == "ca"
    assert ae._jurisdiction_code("Brazil") is None


def test_source_kind_mapping():
    assert ae._source_kind("Indian Patent Office") == "Patent database"
    assert ae._source_kind("United States Patent") == "Patent database"
    assert ae._source_kind("WIPO") == "Patent database (WIPO)"
    assert ae._source_kind("US FDA") == "Regulatory corpus (US FDA)"
    assert ae._source_kind("PubMed Central") == "Scientific literature (PubMed)"
    assert ae._source_kind("some local kb") == "Evidence corpus"


def test_citation_kind_classification():
    assert ae._citation_kind({"act_title": "US10000000 patent", "authority": ""}) == "Patent prior-art"
    assert ae._citation_kind({"act_title": "Charaka Samhita", "authority": ""}) == "Traditional-knowledge material"
    assert ae._citation_kind({"act_title": "", "authority": "US FDA"}) == "Regulatory material"
    assert ae._citation_kind({"act_title": "A study", "authority": "PubMed"}) == "Non-patent / technical (literature)"
    assert ae._citation_kind({"act_title": "misc", "authority": "local"}) == "Non-patent / technical"


def test_keyword_phrases_filters_stopwords_and_limits():
    phrases = ae._keyword_phrases("the ashwagandha extract for sleep support and stress relief")
    assert phrases
    assert "the" not in phrases
    assert len(ae._keyword_phrases("one two three four five six seven eight nine", limit=3)) <= 3


def test_keyword_phrases_single_token_branch():
    phrases = ae._keyword_phrases("extraction")
    assert phrases == ["extraction"]
    assert ae._keyword_phrases("a the and or") == []


@pytest.mark.parametrize(
    "slug,needle",
    [
        ("triz", "root-cause"),
        ("find_solutions", "root-cause"),
        ("formulation", "solvent"),
        ("document_analyzer", "read the"),
        ("novelty_search", "prior art"),
        ("fto_search", "active claims"),
        ("design_fto", "registered designs"),
        ("patent_drafting", "draft claims"),
        ("invention_disclosure", "disclosure"),
        ("office_action_response", "rejection grounds"),
        ("essentiality_claim_chart", "clause-by-clause"),
        ("quick_research", "evidence-backed landscape"),
        ("materials_find_solutions", "material challenge"),
    ],
)
def test_understanding_line_branches(slug, needle):
    line = ae._understanding_line(
        slug,
        {"problem_text": "Ashwagandha extract stability problem", "document_kind": "trend report"},
        "Ashwagandha extract stability problem",
        ["India"],
        [{"raw_name": "Ashwagandha", "resolved": True, "botanical_name": "Withania somnifera"}],
        "claim 1 wording",
    )
    assert needle in line


def test_understanding_line_default_branch():
    line = ae._understanding_line("idea_router", {}, "problem", [], [], "")
    assert line.startswith("The agent understood the request")


def test_sources_section_groups_by_authority():
    section = ae._sources_section([
        {"authority": "US FDA", "act_title": "a"},
        {"authority": "US FDA", "act_title": "b"},
        {"authority": "PubMed", "act_title": "c"},
    ])
    assert section["title"].startswith("Data sources")
    assert len(section["rows"]) == 2
    assert section["rows"][0]["passages"] == "2"


def test_sources_section_empty_corpus_fallback():
    section = ae._sources_section([])
    assert len(section["rows"]) == 1
    assert section["rows"][0]["passages"] == "0"


def test_real_ref_safe_on_empty_and_populated():
    assert ae._real_ref([], 0) == "local corpus"
    ref = ae._real_ref([{"act_title": "Title", "authority": "KB", "section_reference": "s1"}], 0)
    assert "Title" in ref and "KB" in ref
    assert "Title" in ae._real_ref([{"act_title": "Title", "authority": "KB"}], 3)


def test_finding_and_evidence_shapes():
    finding = ae._finding("f1", "title", "detail")
    assert finding == {"id": "f1", "title": "title", "detail": "detail", "severity": "info"}
    assert ae._evidence("kind", "label", "src") == {"kind": "kind", "label": "label", "source": "src"}
    assert "citation_ref" in ae._evidence("kind", "label", "src", "ref")


def test_section_defaults():
    section = ae._section("Title", [{"a": 1}])
    assert section == {"title": "Title", "rows": [{"a": 1}]}
    full = ae._section("Title", [], ["col"], "caption")
    assert full["columns"] == ["col"]
    assert full["caption"] == "caption"


def test_base_result_shape():
    result = ae._base_result("slug", "research", "summary", "note")
    assert result["ok"] is True
    assert set(result) == {
        "agent_slug", "phase", "ok", "summary", "note",
        "findings", "evidence", "citations", "claims", "suggestions", "sections",
    }


def test_draft_claims_with_and_without_process():
    resolved = ae._resolve_ingredients(["Ashwagandha", "Brahmi"])
    with_process = ae._draft_claims({"process_desc": "extraction at 40 C"}, resolved)
    assert any("obtainable by a process" in c for c in with_process)
    without = ae._draft_claims({}, resolved)
    assert not any("obtainable by a process" in c for c in without)
    assert len(without) >= 3


def test_as_citation_truncates_passage():
    class C:
        act_title = "t"
        section_reference = "s"
        authority = "a"
        effective_date = "d"
        exact_passage = "x" * 600
        source_url = "u"
        authority_rank = 2

    citation = ae._as_citation(C())
    assert len(citation["exact_passage"]) == 500
    assert citation["authority_rank"] == 2


def test_claim_signals_variants():
    curative = ae._claim_signals({"proposed_claims": "cures diabetes"})
    assert curative["claim_curative"] is True
    solvent = ae._claim_signals({"process_desc": "hydroalcoholic extraction"})
    assert solvent["prep_solvent"] is True
    purpose = ae._claim_signals({"problem_text": "cognitive support"})
    assert purpose["therapeutic_purpose"] is True
    none = ae._claim_signals({})
    assert none == {"claim_curative": False, "prep_solvent": False, "therapeutic_purpose": False}


def test_fingerprint_returns_dict():
    resolved = ae._resolve_ingredients(["Ashwagandha"])
    assert isinstance(ae._fingerprint({}, resolved), dict)


def test_system_from_problem_branches():
    assert ae._system_from_problem("ab") == "the affected system"
    assert ae._system_from_problem("short extraction system") == "short extraction system"
    long_problem = "one two three four five six seven eight nine ten"
    assert ae._system_from_problem(long_problem) == "one two three four five six…"
    assert ae._system_from_problem("part one, part two") == "part one"


def test_detect_improve_tradeoff_branches():
    assert ae._detect_improve_tradeoff("stability degrades at high temperature") == (
        "extraction temperature", "stability / potency retention")
    assert ae._detect_improve_tradeoff("stability degrades during drying") == (
        "product performance", "stability / potency retention")
    assert ae._detect_improve_tradeoff("low yield at high temperature") == (
        "extraction yield", "marker stability")
    assert ae._detect_improve_tradeoff("yield is low") == ("extraction yield", "marker stability")
    assert ae._detect_improve_tradeoff("yield drops with energy cost") == (
        "extraction yield", "energy use and processing time")
    assert ae._detect_improve_tradeoff("scale up the batch throughput") == (
        "batch throughput", "energy use and product consistency")
    assert ae._detect_improve_tradeoff("moisture pickup in storage") == (
        "storage stability", "drying energy and time")
    assert ae._detect_improve_tradeoff("something unrelated") == (
        "key performance metric", "another quality metric")


def test_triz_fallback_name_mapping():
    assert ae._triz_fallback_name(13, "") == "Stability of object's composition"
    assert ae._triz_fallback_name(23, "") == "Loss of substance"
    assert ae._triz_fallback_name(22, "") == "Loss of energy"
    assert ae._triz_fallback_name(17, "") == "Temperature"
    assert ae._triz_fallback_name(39, "") == "Productivity"
    assert ae._triz_fallback_name(None, "") == "Unmapped parameter — review"


def test_triz_propose_empty_cell_pairs_and_reverse():
    assert ae._triz_propose_empty_cell(13, 13) == [35, 1, 2]
    assert ae._triz_propose_empty_cell(17, 13) == [1, 35, 32]
    assert ae._triz_propose_empty_cell(13, 17) == [1, 35, 32]
    assert ae._triz_propose_empty_cell(39, 22) == [35, 21, 20]
    assert ae._triz_propose_empty_cell(39, 25) == [20, 21, 35]
    assert ae._triz_propose_empty_cell(4, 5) == [35, 2, 1]


def test_triz_success_metrics_context_branches():
    base = ae._triz_success_metrics("generic context")
    assert len(base) == 2
    assert len(ae._triz_success_metrics("yield target")) == 3
    assert len(ae._triz_success_metrics("stability of markers")) == 3
    assert len(ae._triz_success_metrics("temperature exposure")) == 3
    assert len(ae._triz_success_metrics("energy use")) == 3
    assert len(ae._triz_success_metrics("potency retention")) == 3
    assert len(ae._triz_success_metrics("stability over time")) == 4


def test_triz_validation_plan_with_and_without_cards():
    empty_plan = ae._triz_validation_plan([])
    assert len(empty_plan) == 2
    assert "Parameter changes" in empty_plan[0]["experiment"]
    assert "Re-run the confirmed prototype" in empty_plan[1]["experiment"]
    plan = ae._triz_validation_plan([
        {"principle": "Segmentation", "validation_experiment": "run a doE"},
        {"principle": "Cushioning", "validation_experiment": "run a second test"},
        {"principle": "Dynamisation", "validation_experiment": "ignored"},
    ])
    assert len(plan) == 3
    assert plan[0]["experiment"].startswith("Segmentation")
    assert plan[2]["measures"] == "RSD of markers, yield, appearance"


def test_qr_jurisdiction_hint_mapping():
    assert ae._qr_jurisdiction_hint("FSSAI") == "India"
    assert ae._qr_jurisdiction_hint("US FDA") == "United States"
    assert ae._qr_jurisdiction_hint("Health Canada") == "Canada"
    assert ae._qr_jurisdiction_hint("WIPO") == "International"
    assert ae._qr_jurisdiction_hint("unknown body") == "Not jurisdiction-tagged"


def test_qr_provisional_classification_branches():
    cosmetic = ae._qr_provisional_classification("herbal face cream", [])
    assert cosmetic["category"].startswith("Cosmetic")
    drug = ae._qr_provisional_classification("ayurvedic medicine capsule", [])
    assert "medicine" in drug["category"].lower()
    supplement = ae._qr_provisional_classification("dietary supplement gummy", [])
    assert supplement["category"] == "Dietary supplement"
    food = ae._qr_provisional_classification("ayurveda aahara beverage", [])
    assert "Aahara" in food["category"]
    extract = ae._qr_provisional_classification("standardized botanical extract", [])
    assert "extract" in extract["category"].lower()
    fallback = ae._qr_provisional_classification("misc item", [])
    assert fallback["confidence"].startswith("Low")


def test_tokens_and_overlap_similarity():
    assert "ashwagandha" in ae._tokens("Ashwagandha extract")
    assert ae._overlap_similarity("", "text") == 0
    assert ae._overlap_similarity("ashwagandha extract", "ashwagandha extract") == 100
    assert ae._overlap_similarity("ashwagandha", "completely unrelated words") == 0
    partial = ae._overlap_similarity("ashwagandha extract stability", "ashwagandha stability data")
    assert 0 < partial < 100


def test_parameter_flag_returns_match():
    assert ae._parameter_flag(r"\d+\s*C", "held at 40 C") == "40 C"
    assert ae._parameter_flag(r"\d+\s*C", "no temperature") is None


def test_atomic_novelty_features_rich_inputs():
    resolved = ae._resolve_ingredients(["Ashwagandha", "Brahmi"])
    features = ae._atomic_novelty_features(
        {
            "problem_text": "cognitive support formulation",
            "process_desc": "extraction at 40 C for 3 h in hydroalcoholic solvent with marker standardisation in capsules",
        },
        resolved,
    )
    assert features
    kinds = {f["type"] for f in features}
    assert "Composition" in kinds
    assert "Parameter" in kinds
    joined = " ".join(f["feature"] for f in features)
    assert "40" in joined
    assert "capsules" in joined


def test_atomic_novelty_features_missing_values_flagged():
    features = ae._atomic_novelty_features({}, [])
    joined = " ".join(f["feature"] for f in features)
    assert "not provided" in joined
    assert all(f["measurability"] for f in features)


def test_feature_disclosure_levels():
    assert ae._feature_disclosure("feature", "")[0] == "Unclear"
    assert ae._feature_disclosure("value not provided", "anything here")[0] == "Not disclosed"
    explicit = ae._feature_disclosure(
        "hydroalcoholic ashwagandha extract",
        "an ashwagandha extract made by hydroalcoholic extraction of the roots",
    )
    assert explicit[0] == "Explicitly disclosed"
    none = ae._feature_disclosure("ashwagandha solvent ratio", "completely different topic text")
    assert none[0] == "Not disclosed"
    partial = ae._feature_disclosure(
        "ashwagandha solvent ratio temperature",
        "ashwagandha solvent details here",
    )
    assert partial[0] in ("Partially disclosed", "Broadly disclosed", "Suggested only")


def test_source_category_mapping():
    assert ae._source_category("USPTO") == "patent"
    assert ae._source_category("FSSAI") == "regulatory"
    assert ae._source_category("PubMed") == "technical"
    assert ae._source_category("random kb") == "technical"


def test_fto_product_elements_and_claim_rows():
    resolved = ae._resolve_ingredients(["Ashwagandha"])
    elements = ae._fto_product_elements(
        {
            "problem_text": "Ashwagandha nasal spray with markers",
            "process_desc": "extraction and filling",
        },
        resolved,
        "supports restful sleep",
    )
    assert len(elements) == 11
    ids = [e["feature_id"] for e in elements]
    assert "F1" in ids and "U1" in ids
    rows = ae._fto_claim_rows(elements)
    assert len(rows) == len(elements)
    assert {r["preliminary_mapping"] for r in rows} <= {"Identified", "Uncertain", "Not identified"}


def test_fto_activity_matrix_rows():
    rows = ae._fto_activity_matrix(["India", "Canada"])
    assert len(rows) == 12
    assert rows[0]["jurisdiction"] == "India"
    assert ae._fto_activity_matrix([]) == []


def test_execute_agent_failure_returns_failure_dict(monkeypatch):
    def _boom(inputs):
        raise RuntimeError("kaboom")

    ae.EXECUTORS["__coverage_boom__"] = _boom
    try:
        result = ae.execute_agent("__coverage_boom__", {})
    finally:
        ae.EXECUTORS.pop("__coverage_boom__", None)
    assert result["ok"] is False
    assert result["summary"] == "Agent execution failed."
    assert result["note"] == "Agent execution failed: kaboom"
    assert result["findings"][0]["severity"] == "error"
    assert result["citations"] == []


def test_characterization_unknown_slug_falls_back_to_unknown_agent_slug():
    result = ae.execute_agent("no_such_agent", {"problem_text": "Ashwagandha"})
    assert result["agent_slug"] == "unknown"
    assert result["summary"].startswith("Grounded answer with")
    assert isinstance(result["citations"], list)


def test_fallback_executor_uses_agent_slug_input():
    result = ae._exec_fallback({"agent_slug": "custom_agent", "problem_text": "Ashwagandha extract"})
    assert result["agent_slug"] == "custom_agent"
    assert "corpus references" in result["summary"]


def test_fallback_executor_empty_inputs():
    result = ae._exec_fallback({})
    assert result["agent_slug"] == "unknown"
    assert result["phase"] == "unknown"
    assert isinstance(result["citations"], list)


@pytest.mark.parametrize("slug", LEGACY_SLUGS)
@pytest.mark.parametrize(
    "inputs",
    [
        {},
        dict(RICH_INPUTS),
        {"proposed_claims": "supports restful sleep and aids digestion"},
        {"process_desc": "hydroalcoholic extraction at 40 C for 3 h"},
    ],
    ids=["empty", "rich", "claims_only", "process_only"],
)
def test_legacy_executor_input_variants(slug, inputs):
    result = ae.execute_agent(slug, dict(inputs))
    assert result["ok"] is True
    assert result["summary"].strip()
    assert isinstance(result["findings"], list)
    assert isinstance(result["sections"], list)


@pytest.mark.parametrize(
    "slug,inputs",
    [
        ("triz", {"problem_text": "Extraction yield drops when temperature rises above 60 C"}),
        ("triz", {"problem_text": "Stability degrades during scale up of the batch"}),
        ("triz", {"problem_text": "moisture uptake in the dried powder"}),
        ("novelty_search", {"problem_text": "Ashwagandha and Brahmi hydroalcoholic extract for cognitive support",
                            "process_desc": "extraction at 40 C for 3 h"}),
        ("fto_search", {"problem_text": "Ashwagandha nasal spray",
                        "proposed_claims": "supports restful sleep",
                        "target_markets": ["India"]}),
        ("design_fto", {"problem_text": "ornamental bottle shape for a wellness drink"}),
        ("document_analyzer", {"document_text": "# OCR Output (Demo)\nDocument Title: Batch record\n12 mg/mL at 40 C\nPage 2"}),
        ("office_action_response", {"office_action_text": "The claim lacks inventive step under Article 56 and clarity under Article 84.",
                                    "proposed_claims": "1. A composition comprising Ashwagandha extract. 2. The composition of claim 1, wherein the extract is hydroalcoholic.",
                                    "application_number": "IN2024/001"}),
        ("essentiality_claim_chart", {"claim_wording": "1. A composition comprising ashwagandha extract.",
                                      "standard_name": "IS 12345"}),
        ("invention_disclosure", {"disclosure_text": "Inventor notes: hydroalcoholic extraction at 40 C for 3 h with ashwagandha.",
                                  "proposed_claims": "cognitive support"}),
        ("patent_drafting", {"problem_text": "Ashwagandha extract standardised to withanolides",
                             "ingredients": "Ashwagandha",
                             "process_desc": "extraction at 40 C for 3 h"}),
        ("lca_biotherapeutic", {"problem_text": "monoclonal antibody candidate targeting IL-6"}),
        ("lca_small_molecule", {"compound_desc": "Compound 1; IC50 = 45 nM; C22H30O5; CAS 5000-00-0"}),
        ("sar_data_extraction", {"compound_desc": "Compound 1 - IC50 = 45 nM; Project metadata"}),
        ("antibody_target_predictor", {"antibody_desc": "Antibody binding IL-6 by SPR with Kd 3.2 nM"}),
        ("markush_drafting", {"core_structure": "withanolide scaffold; R1 = methyl; R2 = ethyl; n = 1",
                              "variant_features": "Example 1 and Example 2 tested"}),
        ("formulation", {"problem_text": "Ashwagandha extract 8% w/w in a hydroalcoholic base at pH 4.5 for 3 h",
                         "ingredients": "Ashwagandha",
                         "target_markets": ["India", "United States"]}),
        ("materials_find_solutions", {"material_challenge": "microcrystalline cellulose caking and low flow",
                                      "current_material": "microcrystalline cellulose",
                                      "performance_target": "flow rate"}),
        ("quick_research", {"problem_text": "Ayurveda Aahara functional beverage", "timeframe": "2020-2026"}),
        ("find_solutions", {"problem_text": "shelf life shortens because of moisture uptake"}),
        ("tdoc_novelty_search", {"document_text": "Technical disclosure: hydroalcoholic extraction at 40 C for 3 h of ashwagandha.",
                                 "relevant_date": "2024-01-01"}),
    ],
)
def test_hub_agent_targeted_inputs(slug, inputs):
    result = ae.execute_agent(slug, dict(inputs))
    assert result["ok"] is True
    assert result["summary"].strip()
    assert result["sections"][-1]["title"].startswith("Data sources")


@pytest.mark.xfail(
    reason="defect: agent_executors.py:2586 _hub_novelty formats summary with closest['required_strong'] "
           "when closest is None (no qualifying prior-art passage), raising TypeError",
    strict=False,
)
def test_novelty_search_reports_gap_instead_of_crashing_without_passages(monkeypatch):
    monkeypatch.setattr(
        ae.HybridRetrievalEngine,
        "search_passages",
        staticmethod(lambda query, jurisdiction=None, top_k=4: []),
    )
    result = ae.execute_agent("novelty_search", {"problem_text": "Ashwagandha extract for cognitive support"})
    assert result["ok"] is True
    assert "no qualifying" in result["summary"].lower() or "not established" in result["summary"].lower()


@pytest.mark.xfail(
    reason="defect: agent_executors.py:2991 _hub_tdoc_novelty summary f-string dereferences "
           "closest['required_strong'] even though the guard only protects the denominator, "
           "raising TypeError when no qualifying reference is retrieved",
    strict=False,
)
def test_tdoc_novelty_reports_gap_instead_of_crashing_without_passages(monkeypatch):
    monkeypatch.setattr(
        ae.HybridRetrievalEngine,
        "search_passages",
        staticmethod(lambda query, jurisdiction=None, top_k=4: []),
    )
    result = ae.execute_agent(
        "tdoc_novelty_search",
        {"document_text": "Technical disclosure: hydroalcoholic extraction at 40 C for 3 h of ashwagandha."},
    )
    assert result["ok"] is True
    assert "0/0" in result["summary"]


@pytest.mark.xfail(
    reason="defect: agent_executors.py:827 and :864 — execute_agent does not forward the requested slug to "
           "_exec_fallback, so unknown agents are reported as agent_slug='unknown'",
    strict=False,
)
def test_unknown_slug_result_echoes_requested_slug():
    result = ae.execute_agent("no_such_agent", {"problem_text": "Ashwagandha"})
    assert result["agent_slug"] == "no_such_agent"
