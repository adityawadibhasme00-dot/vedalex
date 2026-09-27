from typing import Any

import pytest

from app.services.innolab import agent_executors as ae


def test_design_source_category_branches():
    assert ae._design_source_category("Indian Patent Office design register") == "design_register"
    assert ae._design_source_category("Hague industrial design database") == "design_register"
    assert ae._design_source_category("Indian Patent Office") == "patent"
    assert ae._design_source_category("US FDA") == "regulatory"
    assert ae._design_source_category("PubMed study of packaging") == "technical"


def test_design_article_detection():
    assert ae._design_article("amber glass bottle with cap") == "Bottle"
    assert ae._design_article("the dropper bottle assembly") == "Dropper Bottle"
    assert ae._design_article("nasal spray bottle") == "Nasal Spray Bottle"
    assert ae._design_article("a novel widget").startswith("Article to be confirmed")


def test_design_visual_features_rich_text():
    text = "tall cylindrical amber bottle with cap, grip ridges, leaf motif, label typography and spray pump"
    feats = ae._design_visual_features(text)
    cats = {f["category"] for f in feats}
    assert {"Silhouette", "Configuration", "Surface", "Ornamentation", "Colour", "Label", "Functional"} <= cats
    assert len(feats) <= 12
    assert feats[0]["feature"] == "Overall cylindrical tall silhouette."
    assert feats[0]["functional_relevance"] == "Ornamental"
    assert all(f["confirmation"] == "Pending" for f in feats)


def test_design_visual_features_empty_text_defaults():
    feats = ae._design_visual_features("")
    assert len(feats) == 7
    assert all("not described" in f["feature"] for f in feats)


def test_short_name_and_first_sentence():
    assert ae._short_name("Withania somnifera (L.) Dunal") == "Withania somnifera"
    assert ae._short_name("Brahmi") == "Brahmi"
    assert ae._first_sentence("Extract the root. Then dry it.") == "Extract the root"
    assert ae._first_sentence("") == "An Ayurvedic botanical composition"


def test_process_steps_branches():
    assert ae._process_steps("") == []
    assert ae._process_steps("1. Extract the root; 2. Dry at 40 C; 3. Blend with excipients") == [
        "Extract the root",
        "Dry at 40 C",
        "Blend with excipients",
    ]
    steps = ae._process_steps("Mix the herbs, add water, then heat and dry")
    assert len(steps) == 2


def test_value_markers_branches():
    assert ae._value_markers("standardised to 5% withanolides") == ["5% withanolides"]
    assert ae._value_markers("5% of the batch") == ["5%"]
    assert ae._value_markers("no numbers at all") == []
    assert ae._value_markers("5% withanolides and 5% withanolides") == ["5% withanolides"]


def test_gcd_ratio():
    assert ae._gcd_ratio(40.0, 60.0) == 20
    assert ae._gcd_ratio(7.0, 3.0) == 1
    assert ae._gcd_ratio(0.5, 0.25) == 25


def test_detected_ratio_branches():
    assert ae._detected_ratio("blend 2:1 with water", ["Ashwagandha", "Brahmi"]) == "about 2:1"
    assert ae._detected_ratio("500 mg Ashwagandha with 250 mg Brahmi", ["Ashwagandha", "Brahmi"]) == "about 2:1"
    assert ae._detected_ratio("no amounts stated", ["Ashwagandha"]) is None


def test_use_phrase_branches():
    default = "nutritional or wellness application in a subject in need thereof"
    assert ae._use_phrase("") == default
    assert ae._use_phrase("restful sleep") == "supporting restful sleep"
    assert ae._use_phrase("for sleep quality") == "for sleep quality"
    assert ae._use_phrase("supporting stress") == "supporting stress"
    assert ae._use_phrase("supports cognition") == "supporting cognition"


def test_solvent_word_variants():
    assert ae._solvent_word("70% Ethanol") == "ethanol"
    assert ae._solvent_word("") == ""
    none_value: Any = None
    assert ae._solvent_word(none_value) == ""


def test_skeleton_claims_full_inv():
    inv = {
        "ingredients": ["Ashwagandha", "Brahmi"],
        "steps": ["Extract the root", "Dry at 40 C"],
        "use": "restful sleep",
        "dosage_form": "tablet",
        "solvent": "Hydroalcoholic",
    }
    tree = ae._skeleton_claims(inv)
    assert len(tree) == 7
    assert tree[0]["layer"] == "product"
    assert tree[0]["text"] == "A composition comprising Ashwagandha, Brahmi."
    assert tree[0]["status"].startswith("Preliminary skeleton")
    assert "(a) extract the root" in tree[1]["text"]
    assert tree[1]["layer"] == "method"
    assert "jurisdiction" in tree[2]["status"]
    assert tree[3]["depends_on"] == 1
    assert "tablet" in tree[4]["text"]
    assert tree[6]["layer"] == "method"
    assert tree[6]["depends_on"] == 2
    assert "hydroalcoholic solvent" in tree[6]["text"]


def test_skeleton_claims_minimal_inv():
    inv = {"ingredients": ["X"], "steps": [], "use": "", "dosage_form": "capsule", "solvent": ""}
    tree = ae._skeleton_claims(inv)
    assert len(tree) == 5
    assert "TO BE CONFIRMED" in tree[1]["text"]
    assert "extraction / separation" in tree[1]["text"]
    assert tree[2]["text"].endswith("in a subject in need thereof.")
    assert all("depends_on" in c for c in tree)


def test_ingredient_benefit_split_branches():
    inv = {"problem": "cognitive support formula", "use": "general wellness", "ingredients": ["Ashwagandha"]}
    resolved: list[dict[str, Any]] = [
        {"resolved": True, "botanical_name": "Withania somnifera", "raw_name": "ashwagandha"},
        {"resolved": False, "botanical_name": None, "raw_name": "mystery root"},
    ]
    out = ae._ingredient_benefit_split(inv, resolved, {})
    assert out["ingredients"] == ["Withania somnifera"]
    assert out["unresolved_candidates"] == ["mystery root"]
    assert "cognitive support" in out["benefit_terms"]
    assert "general wellness" in out["benefit_terms"]
    assert out["confirmed"] == ["Ashwagandha"]

    out2 = ae._ingredient_benefit_split({"problem": "x", "use": "y", "ingredients": []}, [], {})
    assert out2["benefit_terms"] == ["none detected"]
    assert out2["ingredients"] == []
    assert out2["unresolved_candidates"] == ["none"]


BLOCKING_CASES = [
    ({"problem": "cognitive support blend"}, "block-benefit"),
    ({"problem": "use effective amounts of extract"}, "block-undefined-amount"),
    ({"problem": "acts synergistically during processing"}, "block-synergy"),
    ({"problem": "maintained under controlled conditions"}, "block-process"),
    ({"problem": "supporting stress relief claim"}, "block-stress"),
    ({"problem": "extractHowever transcription"}, "block-corrupt"),
    ({"problem": "the solvent is used for extraction", "solvent": ""}, "block-solvent"),
]


@pytest.mark.parametrize("inv,code", BLOCKING_CASES)
def test_draft_block_reasons_detects_blockers(inv, code):
    reasons = ae._draft_block_reasons(inv, {})
    assert code in {r["code"] for r in reasons}
    assert all(r["detail"] for r in reasons)


def test_draft_block_reasons_clean_text_passes():
    assert ae._draft_block_reasons({"problem": "Ashwagandha extract dried at 40 C for 3 h"}, {}) == []


def test_draft_block_reasons_deduplicates_repeated_codes():
    reasons = ae._draft_block_reasons({"problem": "cognitive support and cognitive support"}, {})
    assert [r["code"] for r in reasons].count("block-benefit") == 1


def test_draft_blocker_check_shape():
    out = ae._draft_blocker_check({"title": "Vague process", "detail": "Name the parameters"})
    assert out == {
        "track": "semantic",
        "check": "Blocker: Vague process",
        "result": "fail",
        "detail": "Name the parameters",
    }


def test_extract_claims_branches():
    assert ae._extract_claims("Objection to claims 1-5 and 7 is maintained") == "Claims 1-5"
    assert ae._extract_claims("claim 3 lacks support") == "Claims 3"
    assert ae._extract_claims("no numbers here") == "[CLAIMS TO BE EXTRACTED FROM FULL ACTION]"
    none_value: Any = None
    assert ae._extract_claims(none_value) == "[CLAIMS TO BE EXTRACTED FROM FULL ACTION]"


@pytest.mark.parametrize(
    "segment,ground",
    [
        ("claims are not new over the prior art", "Novelty (prior-art anticipation)"),
        ("claim lacks inventive step", "Inventive step / obviousness"),
        ("claims lack clarity and conciseness", "Clarity / conciseness"),
        ("claim is not supported by the description", "Support / written description"),
        ("cannot be performed by a skilled person", "Enablement / sufficiency"),
        ("claims lack unity of invention", "Unity of invention"),
        ("subject matter is excluded under section 3", "Excluded subject matter"),
        ("formality regarding drawings", "Formal / procedural"),
        ("random unrelated text", "Unclassified — specific statutory/examination ground required"),
    ],
)
def test_classify_ground_branches(segment, ground):
    assert ae._classify_ground(segment) == ground


def test_segment_objections_splits_and_labels():
    oa = (
        "The examiner noted an issue. Objection under novelty: claims 1-3 are not new. "
        "Objection under Article 84: clarity is lacking."
    )
    objs = ae._segment_objections(oa)
    assert [o["id"] for o in objs] == ["O-001", "O-002", "O-003"]
    assert objs[0]["ground"] == "Unclassified — specific statutory/examination ground required"
    assert objs[1]["ground"] == "Novelty (prior-art anticipation)"
    assert objs[1]["claims"] == "Claims 1-3"
    assert objs[2]["ground"] == "Clarity / conciseness"
    assert all(o["excerpt"] and o["words"] for o in objs)


def test_segment_objections_empty_returns_placeholder():
    objs = ae._segment_objections("")
    assert len(objs) == 1
    assert objs[0]["id"] == "O-000"
    assert objs[0]["ground"] == "Unclassified — [OFFICE ACTION TEXT REQUIRED]"


def test_split_claims_txt_branches():
    text = (
        "1. A composition comprising ashwagandha extract.\n"
        "2. The composition of claim 1, wherein the extract is hydroalcoholic."
    )
    assert ae._split_claims_txt(text) == [
        ("1", "A composition comprising ashwagandha extract."),
        ("2", "The composition of claim 1, wherein the extract is hydroalcoholic."),
    ]
    assert ae._split_claims_txt("pasted single claim body") == [("1", "pasted single claim body")]
    assert ae._split_claims_txt("   ") == []
    assert ae._split_claims_txt("") == []


def test_claim_blocks_single_line_multi_claims():
    text = "1. A composition comprising ashwagandha. 2. The composition of claim 1, wherein standardized."
    blocks = ae._claim_blocks(text)
    assert [n for n, _ in blocks] == ["1", "2"]
    assert blocks[0][1] == "A composition comprising ashwagandha."


def test_claim_elements_split():
    body = "Mix with water; Dry the powder; Test the yield."
    assert ae._claim_elements(body) == ["Mix with water", "Dry the powder", "Test the yield"]
    assert ae._claim_elements("Mix; Dry") == []


def test_standard_hint_variants():
    assert ae._standard_hint("") == []
    assert ae._standard_hint("ETSI EN 300 328") == ["etsi"]
    assert ae._standard_hint("IEEE 802.11 specification") == ["ieee"]


def test_is_standard_source_branches():
    assert ae._is_standard_source({"act_title": "ETSI EN 300 328", "authority": ""}) is True
    assert ae._is_standard_source({"act_title": "ISO guidance from FDA", "authority": ""}) is False
    assert ae._is_standard_source({"act_title": "plain article", "authority": ""}) is False


@pytest.mark.parametrize(
    "inputs,standard,expected",
    [
        ({"chart_intent": "litigation before court"}, "", "Patent-to-chart — litigation preparation"),
        ({"chart_intent": "pool licensing FRAND royalties"}, "", "Patent-to-standard — licensing / pool / FRAND"),
        ({"product_versions": ["v1"], "chart_intent": ""}, "", "Patent-to-product — implementation mapping"),
        ({"chart_intent": "validity challenge over prior art"}, "", "Patent-to-prior-art — validity support"),
        ({"chart_intent": ""}, "IS 1234", "Standard-essentiality mapping (type not declared — confirm)"),
        ({"chart_intent": ""}, "", "Not declared — chart type is a required input"),
    ],
)
def test_chart_type_branches(inputs, standard, expected):
    out = ae._chart_type(inputs, standard)
    assert out[0] == expected
    assert out[1]


@pytest.mark.parametrize(
    "clause,expected",
    [
        ("", "Unclear — clause text required for classification"),
        ("this clause is deprecated", "Deprecated / obsolete"),
        ("the device shall not exceed 10 mg", "Normative — prohibition (shall not / must not)"),
        ("if the device is powered then shall transmit", "Normative — conditional (if/when/where … shall)"),
        ("the system shall log events", "Normative — mandatory (shall / must)"),
        ("the cover should be closed", "Recommended (should)"),
        ("the feature may be omitted", "Optional / permitted (may)"),
        ("see informative annex for details", "Informative (non-normative)"),
        ("this profile is specific to device", "Profile-specific (applies to a declared profile only)"),
        ("implementation-dependent behavior applies", "Implementation-dependent"),
        ("for example a sensor module", "Example / illustrative"),
        ("the widget is blue", "Unclear — clause text to review"),
    ],
)
def test_clause_obligation_branches(clause, expected):
    assert ae._clause_obligation(clause) == expected


@pytest.mark.parametrize(
    "feature,clause,obligation,expected",
    [
        ("ashwagandha", "", "Normative — mandatory (shall / must)", "Unclear"),
        ("", "the system shall log", "Normative — mandatory (shall / must)", "Not classifiable"),
        ("[NOT PROVIDED]", "the system shall log", "Normative — mandatory (shall / must)", "Not classifiable"),
        (
            "ashwagandha extract hydroalcoholic",
            "the ashwagandha extract is hydroalcoholic",
            "Normative — mandatory (shall / must)",
            "Direct match",
        ),
        (
            "ashwagandha extract hydroalcoholic",
            "the ashwagandha extract is hydroalcoholic",
            "Normative — conditional (if/when/where … shall)",
            "Direct match (conditional clause)",
        ),
        (
            "ashwagandha extract hydroalcoholic",
            "the ashwagandha extract is hydroalcoholic",
            "Normative — prohibition (shall not / must not)",
            "Direct match (prohibited feature)",
        ),
        (
            "ashwagandha extract hydroalcoholic standardised withanolides",
            "the ashwagandha extract is hydroalcoholic",
            "Normative — mandatory (shall / must)",
            "Partial match",
        ),
        (
            "ashwagandha extract hydroalcoholic withanolides",
            "ashwagandha shall apply",
            "Optional / permitted (may)",
            "Optional (mentioned only as permitted)",
        ),
        (
            "ashwagandha extract hydroalcoholic withanolides",
            "ashwagandha shall apply",
            "Recommended (should)",
            "Recommended only",
        ),
        (
            "ashwagandha extract hydroalcoholic withanolides",
            "ashwagandha shall apply",
            "Informative (non-normative)",
            "Informative / example level",
        ),
        (
            "ashwagandha extract hydroalcoholic withanolides",
            "ashwagandha shall apply",
            "Normative — mandatory (shall / must)",
            "Weak overlap",
        ),
        (
            "quercetin dihydrate",
            "ashwagandha extract shall apply",
            "Normative — mandatory (shall / must)",
            "Not found in the retrieved clause text",
        ),
    ],
)
def test_feature_match_label_branches(feature, clause, obligation, expected):
    label, basis = ae._feature_match_label(feature, clause, obligation)
    assert label == expected
    assert basis


@pytest.mark.parametrize(
    "match,obligation,expected",
    [
        ("Not found in the retrieved clause text", "x", "Not mapped"),
        ("Unclear", "x", "Uncertain — clause text / quantified limitation required"),
        ("Not classifiable", "x", "Uncertain — clause text / quantified limitation required"),
        ("Optional (mentioned only as permitted)", "x", "Not shown to be essential (non-mandatory clause)"),
        (
            "Direct match",
            "Normative — conditional (if/when/where … shall)",
            "Conditional — potentially essential when the conditional trigger applies",
        ),
        ("Direct match", "Normative — mandatory (shall / must)", "Potentially essential — technical essentiality to be confirmed"),
        ("Partial match", "x", "Not shown to be essential — incomplete feature mapping"),
        ("Weak overlap", "x", "Not shown to be essential — incomplete feature mapping"),
    ],
)
def test_essentiality_verdict_branches(match, obligation, expected):
    assert ae._essentiality_verdict(match, obligation) == expected


@pytest.mark.parametrize(
    "cit,expected",
    [
        ({"act_title": "ISO 12345 wireless", "authority": "ISO"}, "Tier 1 — official standard text (clause-level evidence)"),
        ({"act_title": "US10000000 patent", "authority": "USPTO"}, "Tier 2 — patent / essentiality-declaration record"),
        ({"act_title": "Implementation technical manual", "authority": ""}, "Tier 3 — technical / implementation documentation"),
        (
            {"act_title": "FSSAI labelling regulation", "authority": "US FDA"},
            "Tier 4 — regulatory / patent-office context (does NOT prove a clause)",
        ),
        ({"act_title": "misc blog post", "authority": "local"}, "Tier 5 — secondary"),
    ],
)
def test_evidence_tier_branches(cit, expected):
    assert ae._evidence_tier(cit) == expected


def test_da_lines_and_filters():
    assert ae._da_lines("a\nb") == ["a", "b"]
    assert ae._da_is_artifact("# OCR Output (Demo)") is True
    assert ae._da_is_artifact("OCR output follows") is True
    assert ae._da_is_artifact("ordinary sentence") is False
    assert ae._da_is_admin("") is True
    assert ae._da_is_admin("Page 3") is True
    assert ae._da_is_admin("12/01/2024") is True
    assert ae._da_is_admin("Confidential") is True
    assert ae._da_is_admin("The batch shall be released") is False


def test_da_meta_extracts_labels():
    meta = ae._da_meta(["Document Title: Stability report", "Prepared by: QA team", "Document Code: DOC-42"])
    assert meta["document_title"] == "Stability report"
    assert meta["prepared_by"] == "QA team"
    assert meta["document_code"] == "DOC-42"


@pytest.mark.parametrize(
    "lines,doc,confidence",
    [
        (["Document Title: Batch Record"], "ignored", "High (explicit metadata label)"),
        (["# Batch Processing Record"], "ignored", "Medium (heading line)"),
        (["STABILITY SUMMARY REPORT FOR BATCH"], "ignored", "Medium (all-caps title line)"),
        ([], "12 mg/mL result", "Low (first substantive line)"),
        (["# OCR Output (Demo)"], "# OCR Output (Demo)", "None"),
    ],
)
def test_da_title_branches(lines, doc, confidence):
    out = ae._da_title(lines, doc)
    assert out["confidence"] == confidence
    assert out["title"]
    assert out["from"]


def test_da_structure_levels_and_parents():
    rows = ae._da_structure(["# Introduction", "## Methods", "2. Results"])
    assert [(r["id"], r["level"], r["parent"]) for r in rows] == [
        ("S-001", "1", "—"),
        ("S-002", "2", "S-001"),
        ("S-003", "1", "—"),
    ]
    assert [r["heading"] for r in rows] == ["Introduction", "Methods", "Results"]


def test_da_obligations():
    lines = [
        "Page 2",
        "The operator shall wear gloves.",
        "Staff must not smoke in the lab.",
        "Records should be reviewed monthly.",
        "The system should not auto-reject.",
        "Notes: see annex.",
    ]
    rows = ae._da_obligations(lines)
    assert [r["type"] for r in rows] == ["Mandatory", "Prohibition", "Recommendation"]
    assert rows[0]["evidence"] == "document text · page 2"
    assert rows[0]["confidence"] == "High"
    assert rows[2]["confidence"] == "Medium"
    assert not any("auto-reject" in r["obligation"] for r in rows)


def test_da_measures_branches():
    empty = ae._da_measures("")
    assert empty["rows"] == []
    assert empty["warned"] is True
    assert empty["status"].startswith("No numeric content")

    out = ae._da_measures("Assay result 12 mg/mL was recorded")
    assert out["rows"][0]["id"] == "M-001"
    assert out["rows"][0]["value"] == "12"
    assert out["rows"][0]["source_layer"]
    assert "numeric measure" in out["status"]
    assert "LIMITATION" in out["status"]

    nodigit = ae._da_measures("alpha beta gamma delta epsilon")
    assert nodigit["rows"] == []
    assert "No digits" in nodigit["status"]

    tab = ae._da_measures("Parameter | Limit\nAssay | 10")
    assert tab["rows"] == []
    assert "Tabular rows are present" in tab["status"]


def test_da_tables_parses_pipe_rows():
    rows = ae._da_tables(["Intro line", "Parameter | Limit", "Assay | 10"])
    assert len(rows) == 1
    assert rows[0]["columns"] == "2"
    assert rows[0]["rows_tall"] == "2"
    assert rows[0]["header"] == "Parameter, Limit"
    assert ae._da_tables(["no tables here"]) == []


def test_da_figures_detects_captions():
    rows = ae._da_figures(["Fig. 1. Extraction apparatus", "plain text line"])
    assert len(rows) == 1
    assert "Extraction" in rows[0]["caption"]
    assert rows[0]["kind"].startswith("Caption-detect")
    assert ae._da_figures(["Fig. 1. " + "y" * 240]) == []


def test_da_entity_context_and_categorise():
    assert ae._da_entity_context(["Ashwagandha root is dried"], "ashwagandha").startswith("Ashwagandha root")
    assert ae._da_entity_context(["no match here"], "quercetin") == "—"
    assert ae._da_entity_categorise("batch")[0] == "Generic process/QC concept"
    assert ae._da_entity_categorise("batch")[1] is False
    assert ae._da_entity_categorise("Ministry of AYUSH")[0] == "Organisation / Authority"
    assert ae._da_entity_categorise("Ministry of AYUSH")[1] is True
    assert ae._da_entity_categorise("Drugs and Cosmetics Act")[0] == "Regulatory framework / standard reference"
    assert ae._da_entity_categorise("GMP compliance")[0] == "Standard / certification scheme"
    assert ae._da_entity_categorise("12 mg/mL")[0] == "Measurement / unit term"
    assert ae._da_entity_categorise("monoclonal antibody")[0] == "Biomedical / technical entity"
    assert ae._da_entity_categorise("REF2024")[0] == "Code / identifier"
    assert ae._da_entity_categorise("banana")[0] == "Generic term"


def test_da_entities_excludes_generics():
    out = ae._da_entities(["Ashwagandha extract meets the batch limits.", "Batch record attached."])
    entities = [r["entity"] for r in out["rows"]]
    assert "Ashwagandha" in entities
    assert "Batch" in out["excluded_generics"]
    assert all(r["valid_biomedical"] in ("Yes", "No") for r in out["rows"])
    assert all(r["context"] for r in out["rows"])


def test_da_definitions_detects_definition_phrases():
    rows = ae._da_definitions(["The rate means the initial velocity of the reaction measured at twenty five degrees."])
    assert len(rows) == 1
    assert rows[0]["term"].startswith("The rate means")
    assert rows[0]["definition"]
    assert ae._da_definitions(["short"]) == []


def test_da_crossrefs_resolution():
    structure = [{"id": "S-001", "heading": "Methods"}]
    rows = ae._da_crossrefs(["See Section methods for details.", "Refer to Appendix xyz."], structure)
    assert len(rows) == 2
    assert rows[0]["status"] == "Resolved — target heading present"
    assert rows[1]["status"] == "Broken / unresolved in this text layer"
    assert ae._da_crossrefs([], structure) == []


@pytest.mark.parametrize(
    "doc,lines,band",
    [
        ("", [], "Unusable"),
        ("# OCR Output (Demo)\nThe remaining text continues here for a while longer.", ["# OCR Output (Demo)"], "Medium"),
        ("word " * 100, [], "High"),
        ("Short but valid text layer content exceeding forty characters.", [], "Medium"),
    ],
)
def test_da_quality_band_branches(doc, lines, band):
    out_band, issues = ae._da_quality_band(doc, lines)
    assert out_band == band
    assert issues


def test_lca_tokens_variants():
    assert ae._lca_tokens("") == []
    assert ae._lca_tokens("the and of") == []
    assert ae._lca_tokens("Adalimumab") == ["Adalimumab"]
    long_space = " ".join(f"Tok{i}" for i in range(100))
    assert len(ae._lca_tokens(long_space)) == 40


@pytest.mark.parametrize(
    "token,valid,kind_sub",
    [
        ("Biologic", False, "Excluded generic label"),
        ("SEQ ID NO: 1", True, "SEQ ID reference"),
        ("P12345", True, "accession"),
        ("clone 7", True, "Clone"),
        ("adalimumab", True, "INN-style"),
        ("trastuzumab HC", True, "lead word"),
        ("AB1234", True, "Clinical development code"),
        ("EGFR", False, "Target / mechanism"),
        ("guidance for industry", False, "Guidance"),
        ("banana", False, "No defined identity"),
    ],
)
def test_lca_validate_branches(token, valid, kind_sub):
    ok, kind, why = ae._lca_validate(token, "space")
    assert ok is valid
    assert kind_sub in kind
    assert why


def test_lca_modality_and_target():
    assert ae._lca_modality("rituximab", "monoclonal antibody IgG1") == "mAb / therapeutic antibody"
    assert ae._lca_modality("peptide X", "cyclic peptide sequence") == "Peptide / cyclopeptide"
    assert ae._lca_modality("x", "") == "[MODALITY NOT PROVIDED]"
    assert ae._lca_target("directed against EGFR in vitro") == "EGFR"
    assert ae._lca_target("no target stated") == "[TARGET REQUIRED]"


def test_lca_patent_rows_dedup_and_marking():
    cit = [
        {"act_title": "US10000000 composition for EGFR", "authority": "USPTO"},
        {"act_title": "US10000000 composition for EGFR", "authority": "USPTO"},
        {"act_title": "WHO guideline for assays", "authority": "WHO"},
        {"act_title": "Journal study of extracts", "authority": "Elsevier"},
    ]
    rows = ae._lca_patent_rows(cit, ["C1"], "space")
    assert len(rows) == 3
    assert rows[0]["patent"] == "US10000000"
    assert rows[0]["valid_candidates_linked"] == "1"
    assert rows[0]["molecule_per_patent"] == "to be mapped from claim examples"
    assert rows[1]["kind"] == "GUIDANCE / REGULATORY CONTEXT"
    assert rows[2]["kind"] == "OTHER LITERATURE / CORPUS"

    solo = ae._lca_patent_rows([{"act_title": "US10000000 x", "authority": "USPTO"}], [], "space")
    assert solo[0]["molecule_per_patent"] == "0 (no valid candidate requiring mapping)"
    assert ae._lca_patent_rows([], [], "space") == []


def test_lca_rank_scorecard_rows():
    cands = [{"valid": True, "name": "Adalimumab"}, {"valid": False, "name": "Junk"}]
    rows = ae._lca_rank_scorecard(cands)
    assert len(rows) == 9
    assert {r["candidate"] for r in rows} == {"Adalimumab"}
    assert all(r["score"] == "Not assessed — evidence unavailable" for r in rows)
    assert ae._lca_rank_scorecard([{"valid": False, "name": "Junk"}]) == []


def test_lsm_first_word():
    assert ae._lsm_first_word("Compound-1A") == "compound"
    assert ae._lsm_first_word("ASPIRIN") == "aspirin"


def test_lsm_activity_near_branches():
    out = ae._lsm_activity_near("Compound 1 was tested: IC50 = 45 nM", "Compound 1")
    assert out["indicator"] == "IC50"
    assert out["value"] == "45"
    assert out["unit"] == "nM"
    assert out["qualifier"] == "="
    assert ae._lsm_activity_near("", "Compound 1")["indicator"] == "[ASSAY DATA REQUIRED]"
    assert ae._lsm_activity_near("IC50 = 45 nM", "ab")["indicator"] == "[ASSAY DATA REQUIRED]"


def test_lsm_candidates_parses_identities():
    space = "CAS 5000-00-0; Compound 1; C22H30O5; ashwagandha with R1 scaffold"
    out = ae._lsm_candidates(space)
    names = [c["name"] for c in out["candidates"]]
    assert "5000-00-0" in names
    assert "Compound 1" in names
    assert "C22H30O5" in names
    assert "Ashwagandha" in out["botanicals"]
    assert "scaffold" in out["markush_signals"]
    assert all(c["valid"] for c in out["candidates"])
    empty = ae._lsm_candidates("")
    assert empty["candidates"] == []
    assert empty["botanicals"] == []


def test_lsm_patent_rows_and_scorecard():
    cit = [
        {"act_title": "US10000000 chemistry", "authority": "USPTO"},
        {"act_title": "US10000000 chemistry", "authority": "USPTO"},
        {"act_title": "landscape analysis of markers", "authority": "Local"},
    ]
    rows = ae._lsm_patent_rows(cit, ["Aspirin"])
    assert len(rows) == 2
    assert rows[0]["kind"] == "Patent document (chemical)"
    assert rows[0]["candidates"] == "Aspirin"
    assert rows[1]["kind"] == "GUIDANCE / REGULATORY / LANDSCAPE CONTEXT"
    score = ae._lsm_rank_scorecard([{"valid": True, "name": "Aspirin"}, {"valid": False, "name": "x"}])
    assert len(score) == 10
    assert {r["candidate"] for r in score} == {"Aspirin"}
    assert ae._lsm_rank_scorecard([{"valid": False, "name": "x"}]) == []


def test_sar_artifact_and_unit_normalisation():
    assert ae._sar_is_artifact("Project metadata demo") is True
    assert ae._sar_is_artifact("Compound 1 - IC50 = 45 nM") is False
    assert ae._sar_unit_norm("uM") == "\u00b5M"
    assert ae._sar_unit_norm("ug/mL") == "\u00b5g/mL"
    assert ae._sar_unit_norm("nM") == "nM"


def test_abp_is_aa_seq_branches():
    assert ae._abp_is_aa_seq("MKLVVVGAGVVGASS") is True
    assert ae._abp_is_aa_seq("MKLVVVGAGVVGAS") is False
    assert ae._abp_is_aa_seq("XXXXXXXXXXXXXXXX") is False
    assert ae._abp_is_aa_seq("MKLVVVGAGVVGAS!!") is False


def test_abp_family_only():
    assert ae._abp_family_only("interleukin family of cytokines") is True
    assert ae._abp_family_only("interleukin and IL-6 were studied") is False
    assert ae._abp_family_only("") is False


@pytest.mark.parametrize(
    "space,has_seq,level",
    [
        ("", False, 5),
        ("co-crystal structure resolved", False, 1),
        ("neutralizing activity observed", False, 2),
        ("SPR binding assay", False, 1),
        ("SPR binding assay", True, 2),
        ("MKLVVVGAGVVGASS", True, 3),
        ("patent claim pending", False, 4),
        ("IL-6 was studied", False, 4),
    ],
)
def test_abp_evidence_level_branches(space, has_seq, level):
    assert ae._abp_evidence_level(space, has_seq) == level


@pytest.mark.parametrize(
    "space,level,has_seq,has_affinity,expected",
    [
        ("", 5, False, False, 0.0),
        ("IL-6 patent example", 4, False, True, 0.35),
    ],
)
def test_abp_confidence_components(space, level, has_seq, has_affinity, expected):
    result: Any = ae._abp_confidence_components(space, level, has_seq, has_affinity)
    rows, total = result
    assert len(rows) == 7
    assert total == expected
    assert all(r["weight"] in ("30%", "25%", "15%", "10%", "5%") for r in rows)


def test_abp_sequences_detects_and_validates():
    assert ae._abp_sequences("") == []
    rows = ae._abp_sequences("CDRH3 label MKLVVVGAGVVGASS tail")
    assert len(rows) == 1
    assert rows[0]["length"] == "15"
    assert rows[0]["valid_symbols"] == "Pass"
    assert rows[0]["cdr_detected"] == "Yes"
    assert rows[0]["status"] == "Valid"


def test_abp_candidates_branches():
    out = ae._abp_candidates("IL-6")
    assert len(out["il_candidates"]) == 1
    assert out["il_candidates"][0]["target"] == "IL-6"
    assert out["family_only"] is False
    fam = ae._abp_candidates("interleukin family of cytokines")
    assert fam["il_candidates"] == []
    assert fam["family_only"] is True


def test_abp_affinity_branches():
    assert ae._abp_affinity("") == []
    rows = ae._abp_affinity("Kd 3.2 nM was measured")
    assert len(rows) == 1
    assert rows[0]["cross_check"].startswith("Unclear")


def test_mk_clean_separates_artifacts():
    out = ae._mk_clean("Project Title: demo work\nR1 = methyl")
    assert out["artifacts"] == ["Project Title: demo work"]
    assert out["clean"] == "R1 = methyl"


def test_mk_formula_status_branches():
    assert ae._mk_formula_status("C22H30O5")["flag"] == "VALID"
    assert ae._mk_formula_status("verbal scaffold description only")["flag"] == "INVALID/INCOMPLETE"
    assert ae._mk_formula_status("SMILES CC(=O)OC1=CC=CC=C1")["flag"] == "VALID"
    assert "verbal scaffold description" in ae._mk_formula_status("verbal scaffold description only")["note"]


def test_mk_rgroups_bounded_and_broad():
    rows = ae._mk_rgroups("R1 = methyl, ethyl; R2 = standard conditions")
    assert [r["position"] for r in rows] == ["R1", "R2"]
    assert rows[0]["status"] == "Eligible (verify position)"
    assert rows[0]["closed_or_open"] == "Closed/bounded"
    assert rows[0]["structure_definition"] == "Explicit"
    assert rows[0]["support"] == "Not evidenced"
    assert rows[1]["status"] == "Narrow / Blocked"
    assert rows[1]["closed_or_open"].startswith("Too broad")
    assert rows[1]["structure_definition"] == "Under-defined"


def test_mk_rgroups_with_example_evidence():
    rows = ae._mk_rgroups("R1 = methyl; Example 1 shows activity with IC50")
    assert rows[0]["support"] == "Examples/activity in source"


def test_mk_combinations_disclosure():
    clean = "R1 = methyl; Example 1 shows activity"
    rgs = ae._mk_rgroups(clean)
    combos = ae._mk_combinations(clean, rgs)
    assert combos[0]["disclosed"] == "Yes"
    assert combos[0]["claimable"] == "Strong (explicit)"
    assert combos[0]["prepared"] == "Unverified"
    assert combos[0]["tested"] == "No — not evidenced"
    empty = ae._mk_combinations("nothing", [])
    assert empty[0]["combination"] == "[NONE DECLARED]"
    assert empty[0]["claimable"] == "Blocked — no R-groups defined"


def test_form_concentration_branches():
    hits = ae._form_concentration("use 5-10% w/w and 3% extra")
    assert hits[0]["low"] == "5"
    assert hits[0]["high"] == "10"
    assert any(h["raw"] == "3%" for h in hits)
    assert ae._form_concentration("no numbers") == []


def test_form_ingredient_names_branches():
    resolved = [{"resolved": True, "botanical_name": "Withania somnifera", "raw_name": "ashwagandha"}]
    assert ae._form_ingredient_names(resolved) == ["Withania somnifera"]
    unresolved = [{"resolved": False, "botanical_name": None, "raw_name": "mystery root"}]
    assert ae._form_ingredient_names(unresolved) == ["mystery root"]
    assert ae._form_ingredient_names([]) == []


def test_form_strategy_and_cna():
    assert ae._form_one_strategy_id(0) == "FC-001"
    assert ae._form_one_strategy_id(11) == "FC-012"
    assert ae._form_cna_pct([], 0) == "[USER CONFIRMATION REQUIRED]"
    assert ae._form_cna_pct([{"raw": "5-10%"}], 3) == "5-10%"
    assert ae._form_cna_pct([{"raw": ""}], 0) == "[RANGE REQUIRED]"


def test_solvent_short_and_detect_solvent():
    assert ae._solvent_short("Water (decoction)") == "aqueous decoction"
    assert ae._solvent_short("Not sure") == "optimal solvent"
    assert ae._solvent_short("Acme solvent") == "Acme solvent"
    assert ae._solvent_short("") == "optimal solvent"
    assert ae._detect_solvent("ethanolic extraction at 40 C") == "Hydroalcoholic"
    assert ae._detect_solvent("ghrita base preparation") == "Ghee / ghrita"
    assert ae._detect_solvent("honey added") == "Honey"
    assert ae._detect_solvent("milk based") == "Milk"
    assert ae._detect_solvent("asava fermentation") == "Alcohol (asava/aristha)"
    assert ae._detect_solvent("water decoction process") == "Water (decoction)"
    assert ae._detect_solvent("nothing stated") == "Hydroalcoholic"


def test_mat_material_names_and_properties():
    names = ae._mat_material_names("magnesium stearate and talc")
    assert "magnesium stearate" in names
    assert "talc" in names
    assert ae._mat_material_names("starch and starch") == ["starch"]
    assert ae._mat_material_names("") == []
    props = ae._mat_property_obs("low flow and caking observed")
    assert props[0] == "flow"
    assert "caking" in props
    assert ae._mat_property_obs("no issues stated") == []


def test_mat_grade_branches():
    assert ae._mat_grade("Grade 2 material", "x") == "Grade 2"
    assert ae._mat_grade("USP compliant material", "x") == "USP spec — [level required]"
    assert ae._mat_grade("no designation", "x") == "[GRADE REQUIRED]"


@pytest.mark.parametrize(
    "slug,inputs",
    [
        (
            "office_action_response",
            {
                "office_action_text": (
                    "Objection under novelty: claims 1-3 are not new. Objection under unity of invention. "
                    "Subject matter excluded under section 3."
                ),
                "proposed_claims": (
                    "1. A composition comprising ashwagandha extract. "
                    "2. The composition of claim 1, wherein hydroalcoholic."
                ),
                "application_number": "IN2024/0099",
                "response_deadline": "2026-03-01",
            },
        ),
        (
            "essentiality_claim_chart",
            {
                "chart_intent": "litigation preparation for court",
                "claim_wording": "1. A composition comprising ashwagandha extract.",
                "standard_name": "IS 777",
            },
        ),
        (
            "essentiality_claim_chart",
            {
                "product_versions": ["v1.0"],
                "product_desc": "tablet",
                "claim_wording": "1. A composition comprising ashwagandha extract.",
                "standard_name": "IS 888",
            },
        ),
        (
            "essentiality_claim_chart",
            {
                "chart_intent": "validity challenge over prior art",
                "claim_wording": "1. A composition comprising ashwagandha extract.",
                "standard_name": "IS 999",
            },
        ),
        (
            "document_analyzer",
            {
                "document_text": (
                    "# GMP Handbook\n\nThe operator shall wear gloves.\nStaff must not smoke.\n\n"
                    "Parameter | Limit\nAssay | 10\n\nFig. 1. Extraction setup\n"
                )
            },
        ),
        (
            "markush_drafting",
            {
                "core_structure": "SMILES CC(=O)OC1=CC=CC=C1 scaffold; R1 = methyl, ethyl",
                "variant_features": "Example 1 and Example 2 tested with IC50 activity",
            },
        ),
        ("sar_data_extraction", {"compound_desc": "Project metadata demo; Compound 1 - IC50 = 45 nM"}),
        ("lca_biotherapeutic", {"problem_text": "monoclonal antibody candidate, SEQ ID NO: 1, against EGFR"}),
        ("antibody_target_predictor", {"antibody_desc": "CDRH3 MKLVVVGAGVVGASS sequence; SPR Kd 3.2 nM for IL-6"}),
        (
            "formulation",
            {"problem_text": "use 5-10% w/w ashwagandha with 3% brahmi at pH 4.5", "ingredients": "Ashwagandha, Brahmi"},
        ),
        (
            "materials_find_solutions",
            {
                "material_challenge": "dissolution failure and hardness variation",
                "current_material": "USP grade starch",
                "performance_target": "dissolution rate",
            },
        ),
        (
            "patent_drafting",
            {
                "problem_text": "cognitive support formulation",
                "ingredients": "Ashwagandha",
                "proposed_claims": "effective amounts of extract synergistically combined",
                "process_desc": "maintained under controlled conditions",
            },
        ),
        ("design_fto", {"problem_text": "tall cylindrical amber bottle with cap, grip ridges and label typography"}),
        ("lca_small_molecule", {"compound_desc": "Compound 2; IC50 = 12 nM; CAS 50-78-2; R1 = methyl scaffold"}),
        ("triz", {"problem_text": "yield drops while temperature rises", "improve_aspect": "extraction yield"}),
        ("quick_research", {"problem_text": "Ayurveda Aahara beverage", "target_markets": ["India", "United States"]}),
        ("find_solutions", {"problem_text": "moisture uptake shortens shelf life", "process_desc": "drying at 40 C"}),
        ("invention_disclosure", {
            "disclosure_text": "Inventor notes: hydroalcoholic extract standardised to withanolides.",
            "proposed_claims": "supports restful sleep",
        }),
        ("fto_search", {"problem_text": "ashwagandha nasal spray", "target_markets": ["India"],
                        "proposed_claims": "supports sleep"}),
        ("tdoc_novelty_search", {"document_text": "Technical disclosure of hydroalcoholic extraction at 40 C.",
                                 "relevant_date": "2024-06-01"}),
    ],
)
def test_hub_input_variants_v2(slug, inputs):
    result = ae.execute_agent(slug, dict(inputs))
    assert result["ok"] is True
    assert result["summary"].strip()
    assert isinstance(result["sections"], list) and result["sections"]
    assert isinstance(result["findings"], list)
