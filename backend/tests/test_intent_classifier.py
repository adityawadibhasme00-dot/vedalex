"""
Unit tests for the domain-intent classifier that gates retrieval before search.

Verifies:
  - the nine domain intents are scored / routed correctly
  - relevant Qdrant collections are returned per intent
  - the Patent Rule Engine gate flag is set only for the patent intent
  - patent topics are stripped from non-patent answers
  - sources from off-domain collections are filtered from the evidence set
"""

import pytest

from app.services.intent_classifier import (
    classify_domain_intent,
    filter_sources_by_domain,
    strip_banned_patent_topics,
)


@pytest.mark.parametrize(
    "question,expected_id,expected_domains,runs_patent_engine",
    [
        ("Is my turmeric formulation patentable under section 3(p)?",
         "patent", ["patents", "traditional_knowledge"], True),
        ("What is the prior art position for my ashwagandha extract?",
         "patent", ["patents", "traditional_knowledge"], True),
        ("Does my formulation need a TKDL clearance before filing?",
         "patent", ["patents", "traditional_knowledge"], True),
        ("What are the FSSAI labelling requirements for Ayurveda Aahar?",
         "fssai", ["regulations"], False),
        ("Do I need an FSSAI licence for my nutraceutical drink?",
         "fssai", ["regulations"], False),
        ("How do I get NBA approval for commercial utilisation of giloy?",
         "abs", ["biodiversity", "regulations"], False),
        ("What is the access and benefit sharing process with the SBB?",
         "abs", ["biodiversity", "regulations"], False),
        ("Do I need to register a trademark for my brand name in class 5?",
         "trademark", ["regulations"], False),
        ("How do I get a GI tag for my Kashmiri saffron?",
         "gi", ["regulations"], False),
        ("Can I export my ayurvedic product to the USA?",
         "export", ["regulations", "safety"], False),
        ("What are the safety limits for heavy metals in my herbal tea?",
         "safety", ["safety", "regulations"], False),
        ("What GMP requirements apply to my manufacturing batch?",
         "quality", ["quality_standards", "regulations"], False),
        ("Is a DSHEA licence needed for my supplement?",
         "regulatory", ["regulations"], False),
    ],
)
def test_domain_intent_classification(question, expected_id, expected_domains,
                                      runs_patent_engine):
    result = classify_domain_intent(question)
    assert result["id"] == expected_id, f"{question!r} -> {result}"
    assert result["collections"] == expected_domains
    assert result["run_patent_engine"] is runs_patent_engine


def test_domain_intent_always_returns_complete_shape():
    for q in ["hello", "", "kaise ho bhai", "random unrelated text"]:
        result = classify_domain_intent(q)
        assert set(result) >= {
            "id", "label", "collections", "run_patent_engine", "ban_patent_topics"
        }
        assert result["collections"]


def test_fssai_domain_bans_patent_topics():
    result = classify_domain_intent("FSSAI labelling rules for Ayurveda Aahar")
    assert result["ban_patent_topics"] is True


def test_patent_domain_does_not_ban_patent_topics():
    result = classify_domain_intent("Is my extract patentable under section 3(p)?")
    assert result["ban_patent_topics"] is False


def test_regulatory_intent_used_as_default():
    result = classify_domain_intent("")
    assert result["id"] == "regulatory"
    assert result["run_patent_engine"] is False


# ---------------------------------------------------------------------------
# Patent-topic stripping
# ---------------------------------------------------------------------------

def test_strip_removes_section_3p_and_prior_art_sentences():
    text = (
        "The FSSAI Licence requires a valid registration from the state food authority. "
        "Review Section 3(p) exposure with a patent agent before filing. "
        "Your product must carry the mandatory nutrition panel."
    )
    cleaned = strip_banned_patent_topics(text)
    assert "Section 3(p)" not in cleaned
    assert "patent agent" not in cleaned
    assert "FSSAI Licence" in cleaned
    assert "nutrition panel" in cleaned


def test_strip_removes_wipo_readiness_and_patent_token_sentences():
    text = (
        "Heavy metal limits are prescribed under Schedule T. "
        "Your patent readiness score is 42/100, so WIPO/PCT filing is premature. "
        "Submit a micro report for the microbiology criteria."
    )
    cleaned = strip_banned_patent_topics(text)
    assert "readiness score" not in cleaned
    assert "WIPO" not in cleaned
    assert "patent" not in cleaned
    assert "micro report" in cleaned
    assert "Heavy metal limits" in cleaned
    assert "microbiology" in cleaned


def test_strip_keeps_regulatory_only_content_untouched():
    text = "Schedule T sets the GMP limit for heavy metals in Ayurvedic medicines."
    assert strip_banned_patent_topics(text) == text


def test_strip_handles_empty():
    assert strip_banned_patent_topics("") == ""


# ---------------------------------------------------------------------------
# Source filtering by domain
# ---------------------------------------------------------------------------

def _src(name, collection, juris="India", rank=1, score=0.5):
    return {
        "source": name, "collection": collection, "jurisdiction": juris,
        "authority_rank": rank, "score": score, "content": f"{name} body text",
    }


def test_filter_sources_drops_off_domain_collections():
    sources = [
        _src("FSSAI Act", "regulations"),
        _src("Patent X", "patents"),
        _src("NBA SBB", "biodiversity"),
    ]
    kept = filter_sources_by_domain(sources, ["regulations"])
    assert [s["source"] for s in kept] == ["FSSAI Act"]


def test_filter_sources_keeps_unlabelled_statutory_passages():
    sources = [
        _src("FSSAI Act", "regulations"),
        _src("Patent X", "patents"),
        {"source": "Schedule T passage", "category": "statutory",
         "content": "stat text"},
    ]
    kept = filter_sources_by_domain(sources, ["regulations"])
    names = [s["source"] for s in kept]
    assert "FSSAI Act" in names
    assert "Patent X" not in names
    assert "Schedule T passage" in names


def test_filter_sources_no_op_without_domains_or_tags():
    sources = [_src("A", "regulations"), _src("B", "patents")]
    assert filter_sources_by_domain(sources, None) == sources
    untagged = [{"source": "x", "content": "y"}]
    assert filter_sources_by_domain(untagged, ["regulations"]) == untagged


def test_filter_sources_keeps_all_when_all_in_domain():
    sources = [_src("A", "regulations"), _src("B", "safety")]
    kept = filter_sources_by_domain(sources, ["regulations", "safety"])
    assert len(kept) == 2