from types import SimpleNamespace

import pytest

from app.services import ai_copilot
from app.services.ai_copilot import (
    GUIDANCE,
    NO_EVIDENCE_ANSWER,
    STOPWORDS,
    AICopilot,
    _build_lead,
    _format_citation,
    os_label,
)

QUESTION = "ashwagandha patent requirements"


def _doc(content, **kw):
    base = {
        "content": content,
        "source": "IP-SAKTI KB",
        "doc_id": "doc-1",
        "title": "Knowledge Record",
        "section_heading": "Section 4.2",
        "authority": "CSIR-NIC",
        "source_url": "https://kb.example.org/record",
        "effective_date": "2021-04-01",
        "authority_level": 1,
    }
    base.update(kw)
    return base


def _cit(**kw):
    base = {
        "exact_passage": "statutory passage describing the requirements",
        "source_url": "https://indiacode.nic.in/act",
        "act_title": "Patents Act, 1970",
        "section_reference": "S.13",
        "authority": "Legislative Department",
        "effective_date": "1970",
        "authority_rank": 1,
    }
    base.update(kw)
    return SimpleNamespace(**base)


def _set_docs(monkeypatch, docs):
    docs = list(docs)
    monkeypatch.setattr(
        AICopilot, "_faiss_index",
        SimpleNamespace(search=lambda q, top_k=8: [dict(d) for d in docs]))


def _set_statutory(monkeypatch, citations):
    citations = list(citations)
    monkeypatch.setattr(
        ai_copilot.HybridRetrievalEngine, "search_passages",
        lambda *a, **k: list(citations))


def _set_images(monkeypatch, images=None):
    seen = []

    def _images(query):
        seen.append(query)
        return list(images or [])

    monkeypatch.setattr(ai_copilot, "find_relevant_images", _images)
    return seen


@pytest.fixture(autouse=True)
def _copilot_defaults(monkeypatch):
    _set_docs(monkeypatch, [])
    _set_statutory(monkeypatch, [])
    _set_images(monkeypatch, [])
    yield


# ---------------------------------------------------------------------------
# index lifecycle
# ---------------------------------------------------------------------------

def test_get_index_builds_once_and_resets(monkeypatch):
    calls = {"init": 0, "load": 0}

    class _FakeIndex:
        def __init__(self):
            calls["init"] += 1

        def load_or_build(self):
            calls["load"] += 1

    monkeypatch.setattr(ai_copilot, "FAISSIndex", _FakeIndex)
    monkeypatch.setattr(AICopilot, "_faiss_index", None)

    first = AICopilot.get_index()
    assert isinstance(first, _FakeIndex)
    assert AICopilot.get_index() is first
    assert calls == {"init": 1, "load": 1}

    AICopilot.reset_index()
    assert AICopilot._faiss_index is None

    AICopilot.get_index()
    assert calls == {"init": 2, "load": 2}
    AICopilot.reset_index()


def test_get_index_reuses_prefetched_instance(monkeypatch):
    injected = SimpleNamespace(search=lambda q, top_k=8: [])
    monkeypatch.setattr(AICopilot, "_faiss_index", injected)
    assert AICopilot.get_index() is injected


# ---------------------------------------------------------------------------
# query()
# ---------------------------------------------------------------------------

def test_query_grounds_and_builds_full_payload(monkeypatch):
    _set_docs(monkeypatch, [_doc(
        "ashwagandha patent requirements are documented in the compiled "
        "knowledge base record")])
    _set_statutory(monkeypatch, [_cit()])
    _set_images(monkeypatch, ["img/a.png"])

    out = AICopilot.query(QUESTION, passport_context={"passport_id": "p1"})

    assert out["question"] == QUESTION
    assert NO_EVIDENCE_ANSWER not in out["answer"]
    assert out["answer"].startswith(
        "Based on the retrieved patent and traditional-knowledge sources")
    assert GUIDANCE in out["answer"]
    assert "Verified citation:" in out["answer"]
    assert 0.7 <= out["confidence"] <= 0.95
    assert [s["category"] for s in out["sources"]] == ["knowledge", "statutory"]
    assert out["images"] == ["img/a.png"]
    assert [c["type"] for c in out["charts"]][:2] == ["bar", "doughnut"]


def test_query_refuses_when_tokens_do_not_overlap(monkeypatch):
    image_queries = _set_images(monkeypatch, ["img/a.png"])
    _set_docs(monkeypatch, [_doc("unrelated marine biology corpus about coral")])

    out = AICopilot.query("ashwagandha patent requirements")

    assert out["answer"] == NO_EVIDENCE_ANSWER
    assert out["confidence"] == 0.08
    assert out["sources"] == []
    assert out["images"] == []
    assert out["charts"][0]["type"] == "doughnut"
    assert out["charts"][0]["values"] == [0, 100]
    assert image_queries == []


def test_query_without_any_retrieval_is_refused():
    out = AICopilot.query("ashwagandha patent requirements")
    assert out["answer"] == NO_EVIDENCE_ANSWER
    assert out["confidence"] == 0.08
    assert out["sources"] == []


def test_query_maps_statutory_citations(monkeypatch):
    _set_docs(monkeypatch, [_doc(
        "ashwagandha patent requirements recorded in the statutory corpus")])
    _set_statutory(monkeypatch, [_cit(
        exact_passage="the statutory requirements are enumerated here",
        source_url="https://ipindia.gov.in/act",
        section_reference="S.2",
        authority="IP India",
        effective_date="2005",
        authority_rank=2)])

    out = AICopilot.query(QUESTION)
    statutory = [s for s in out["sources"] if s["category"] == "statutory"][0]

    assert statutory["content"] == "the statutory requirements are enumerated here"
    assert statutory["source"] == "https://ipindia.gov.in/act"
    assert statutory["act_title"] == "Patents Act, 1970"
    assert statutory["section"] == "S.2"
    assert statutory["authority"] == "IP India"
    assert statutory["effective_date"] == "2005"
    assert statutory["authority_rank"] == 2


def test_query_statutory_source_falls_back_to_act_title(monkeypatch):
    _set_docs(monkeypatch, [_doc(
        "ashwagandha patent requirements recorded in the statutory corpus")])
    _set_statutory(monkeypatch, [_cit(source_url=None, act_title="Ayurveda Act")])

    out = AICopilot.query(QUESTION)
    statutory = [s for s in out["sources"] if s["category"] == "statutory"][0]

    assert statutory["source"] == "Ayurveda Act"
    assert statutory["source_url"] == ""


def test_query_statutory_content_is_truncated_to_six_hundred_chars(monkeypatch):
    _set_docs(monkeypatch, [_doc(
        "ashwagandha patent requirements recorded in the statutory corpus")])
    _set_statutory(monkeypatch, [_cit(exact_passage="s" * 900)])

    out = AICopilot.query(QUESTION)
    statutory = [s for s in out["sources"] if s["category"] == "statutory"][0]
    assert len(statutory["content"]) == 600


def test_query_caps_confidence_at_point_nine_five(monkeypatch):
    _set_docs(monkeypatch, [_doc(
        f"{QUESTION} record {i} with full token overlap", doc_id=f"d{i}")
        for i in range(8)])

    out = AICopilot.query(QUESTION)
    assert out["confidence"] == 0.95


def test_query_truncates_used_sources_to_five(monkeypatch):
    _set_docs(monkeypatch, [_doc(
        f"{QUESTION} record {i} with full token overlap", doc_id=f"d{i}")
        for i in range(8)])

    out = AICopilot.query(QUESTION)
    assert len(out["sources"]) == 5


def test_query_single_token_question_uses_threshold_of_one(monkeypatch):
    _set_docs(monkeypatch, [_doc("neem is recorded in this passage")])

    out = AICopilot.query("neem")

    assert out["confidence"] > 0.08
    assert NO_EVIDENCE_ANSWER not in out["answer"]
    assert out["sources"]


def test_query_statutory_only_evidence_can_ground(monkeypatch):
    _set_statutory(monkeypatch, [_cit(
        exact_passage="patent requirements for formulations are stated here")])

    out = AICopilot.query(QUESTION)
    assert NO_EVIDENCE_ANSWER not in out["answer"]
    assert [s["category"] for s in out["sources"]] == ["statutory"]


def test_query_builds_charts_and_images_only_when_grounded(monkeypatch):
    image_queries = _set_images(monkeypatch, ["img/a.png"])
    _set_docs(monkeypatch, [_doc(
        "ashwagandha patent requirements recorded in the knowledge base")])

    out = AICopilot.query(QUESTION)
    assert len(out["charts"]) >= 2
    assert image_queries == [QUESTION]

    _set_docs(monkeypatch, [_doc("no overlap at all")])
    out = AICopilot.query(QUESTION)
    assert len(out["charts"]) == 1
    assert out["images"] == []


# ---------------------------------------------------------------------------
# _build_source
# ---------------------------------------------------------------------------

def test_build_source_maps_document_fields():
    out = AICopilot._build_source(_doc("body text"), kind="knowledge")
    assert out == {
        "content": "body text",
        "source": "IP-SAKTI KB",
        "category": "knowledge",
        "doc_id": "doc-1",
        "title": "Knowledge Record",
        "section": "Section 4.2",
        "authority": "CSIR-NIC",
        "source_url": "https://kb.example.org/record",
        "effective_date": "2021-04-01",
        "authority_rank": 1,
    }


def test_build_source_truncates_content_and_fills_defaults():
    out = AICopilot._build_source(
        {"content": "c" * 900, "section_heading": "H"}, kind="statutory")
    assert out["content"] == "c" * 600
    assert out["source"] == "unknown"
    assert out["category"] == "statutory"
    assert out["doc_id"] == ""
    assert out["title"] == ""
    assert out["section"] == "H"
    assert out["authority"] == ""
    assert out["source_url"] == ""
    assert out["effective_date"] == ""
    assert out["authority_rank"] == 3


# ---------------------------------------------------------------------------
# _build_charts
# ---------------------------------------------------------------------------

def test_build_charts_reports_category_mix_and_authorities():
    sources = [
        AICopilot._build_source(_doc("a", authority="CSIR-NIC"), kind="knowledge"),
        AICopilot._build_source(_doc("b", authority="CSIR-NIC"), kind="knowledge"),
        {"category": "statutory", "authority": "Legislative Department",
         "content": "c"},
    ]
    charts = AICopilot._build_charts(QUESTION, sources, 0.66)

    assert [c["type"] for c in charts] == ["bar", "doughnut", "bar"]
    assert charts[0]["labels"] == ["knowledge", "statutory"]
    assert charts[0]["values"] == [2, 1]
    assert "verified statutory passage" in charts[0]["insights"][1]
    assert charts[1]["values"] == [66, 34]
    assert charts[2]["labels"][0] in ("CSIR-NIC", "Legislative Department")
    assert charts[2]["values"] == [2, 1]


def test_build_charts_without_statutory_source_says_so():
    sources = [{"category": "knowledge", "authority": "CSIR-NIC", "content": "c"}]
    charts = AICopilot._build_charts(QUESTION, sources, 0.5)
    assert "No statutory passage" in charts[0]["insights"][1]
    assert "knowledge" in charts[0]["insights"][0]


def test_build_charts_without_sources_returns_only_grounding_doughnut():
    charts = AICopilot._build_charts(QUESTION, [], 0.0)
    assert len(charts) == 1
    assert charts[0]["type"] == "doughnut"
    assert charts[0]["labels"] == ["Grounded in sources", "Inference gap"]
    assert charts[0]["values"] == [0, 100]


def test_build_charts_full_grounding_has_no_inference_gap():
    charts = AICopilot._build_charts(QUESTION, [], 1.0)
    assert charts[0]["values"] == [100, 0]


def test_build_charts_single_authority_has_no_authority_chart():
    sources = [{"category": "knowledge", "authority": "CSIR-NIC", "content": "c"}]
    charts = AICopilot._build_charts(QUESTION, sources, 0.4)
    assert [c["type"] for c in charts] == ["bar", "doughnut"]


def test_build_charts_titles_are_deterministic_per_question():
    sources = [{"category": "knowledge", "authority": "CSIR-NIC", "content": "c"}]
    first = AICopilot._build_charts(QUESTION, sources, 0.5)
    second = AICopilot._build_charts(QUESTION, sources, 0.5)
    assert [c["title"] for c in first] == [c["title"] for c in second]

    other = AICopilot._build_charts("neem label claim evidence tkdl", sources, 0.5)
    assert [c["title"] for c in other] != [c["title"] for c in first]


def test_build_charts_category_counts_are_capped_at_five_labels():
    sources = [
        {"category": f"cat{i}", "authority": "A", "content": "c"}
        for i in range(7)
    ]
    charts = AICopilot._build_charts(QUESTION, sources, 0.3)
    assert len(charts[0]["labels"]) == 5


# ---------------------------------------------------------------------------
# _generate_answer
# ---------------------------------------------------------------------------

def _grounded_source(question, **kw):
    content = f"{question} official record text"
    return AICopilot._build_source(_doc(content, **kw), kind="knowledge")


@pytest.mark.parametrize("question,fragment", [
    ("is this patentable", "Section 3(p)"),
    ("neem oil extract", "Azadirachta indica"),
    ("label claim review", "Label and claim compliance"),
    ("what evidence is missing", "documentation gaps"),
    ("tkdl prior art search", "Traditional Knowledge Digital Library"),
    ("traditional knowledge record", "Traditional Knowledge Digital Library"),
    ("ashwagandha dosage schedule", "From the knowledge sources retrieved"),
])
def test_generate_answer_lead_branches(question, fragment):
    out = AICopilot._generate_answer(question, [_grounded_source(question)])
    assert fragment in out
    assert "Verified citation:" in out
    assert GUIDANCE in out
    assert NO_EVIDENCE_ANSWER not in out


def test_generate_answer_without_sources_returns_no_evidence():
    assert AICopilot._generate_answer(QUESTION, []) == NO_EVIDENCE_ANSWER


def test_generate_answer_without_meaningful_tokens_returns_no_evidence():
    source = AICopilot._build_source(_doc("what is this record"), kind="knowledge")
    assert AICopilot._generate_answer("what is", [source]) == NO_EVIDENCE_ANSWER


def test_generate_answer_below_coverage_threshold_returns_no_evidence():
    source = AICopilot._build_source(
        _doc("patent"), kind="knowledge")
    out = AICopilot._generate_answer("ashwagandha patent requirements", [source])
    assert out == NO_EVIDENCE_ANSWER


def test_generate_answer_quotes_long_snippet_with_ellipsis():
    question = "neem"
    source = {
        "content": f"{question} " + "x" * 700,
        "category": "knowledge",
        "source": "IP-SAKTI KB",
    }
    out = AICopilot._generate_answer(question, [source])
    assert "..." in out
    assert GUIDANCE in out


def test_generate_answer_uses_default_source_label_when_missing():
    question = "ashwagandha dosage"
    source = {
        "content": f"{question} official record",
        "category": "knowledge",
        "source": "",
    }
    out = AICopilot._generate_answer(question, [source])
    assert "From the knowledge sources retrieved for this question" in out
    assert "(retrieved source)" in out
    assert NO_EVIDENCE_ANSWER not in out


# ---------------------------------------------------------------------------
# citation / label helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source,expected", [
    ({}, "Verified citation: Cited source"),
    ({"act_title": "Patents Act, 1970"}, "Verified citation: Patents Act, 1970"),
    ({"title": "Fallback Title"}, "Verified citation: Fallback Title"),
    ({"section": "S.3(p)"}, "Verified citation: S.3(p)"),
    ({"authority": "FSSAI"}, "Verified citation: FSSAI"),
    ({"effective_date": "2020-01-01"},
     "Verified citation: (effective 2020-01-01)"),
    ({"act_title": "A", "section": "S.1", "authority": "Gov"},
     "Verified citation: A · S.1 · Gov"),
    ({"act_title": "A", "source_url": "https://x.example/a"},
     "Verified citation: A — https://x.example/a"),
])
def test_format_citation(source, expected):
    assert _format_citation(source) == expected


@pytest.mark.parametrize("path,expected", [
    ("path/to/file.txt", "file.txt"),
    ("file.txt", "file.txt"),
    ("", ""),
    ("https://kb.example.org/record.json", "record.json"),
])
def test_os_label(path, expected):
    assert os_label(path) == expected


@pytest.mark.parametrize("question,fragment", [
    ("can this be patented", "Section 3(p)"),
    ("azadirachta prior art", "Azadirachta indica"),
    ("compliant label wording", "Label and claim compliance"),
    ("missing evidence dossier", "documentation gaps"),
    ("tkdl defensive filing", "Traditional Knowledge Digital Library"),
    ("unrelated topic", ""),
])
def test_build_lead(question, fragment):
    assert fragment in _build_lead(question)


def test_stopwords_constant_drops_function_words():
    assert "the" in STOPWORDS
    assert "what" in STOPWORDS
    assert "ashwagandha" not in STOPWORDS


# ---------------------------------------------------------------------------
# defects
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="query tokens are punctuation-stripped but evidence tokens are raw "
           "whitespace splits, so comma-separated evidence fails the grounding "
           "gate (ai_copilot.py:77)",
    strict=False)
def test_query_grounds_evidence_containing_every_query_term(monkeypatch):
    _set_docs(monkeypatch, [_doc(
        "ashwagandha, patent, requirements recorded in the official record")])

    out = AICopilot.query(QUESTION)

    assert NO_EVIDENCE_ANSWER not in out["answer"]
    assert out["sources"]
