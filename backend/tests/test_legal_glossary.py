"""Tests for the legal/Ayurveda bilingual glossary service."""

from typing import Any

from app.services.legal_glossary_service import LegalGlossary


def test_glossary_loads_and_counts():
    LegalGlossary._data = {}
    desc: dict[str, Any] = LegalGlossary.describe()
    assert desc["available"] is True
    assert desc["term_count"] >= 20
    assert "hi" in desc["languages"]


def test_exact_lookup():
    entry = LegalGlossary.lookup("prior_art")
    assert entry is not None
    assert entry["en"] == "prior art"
    assert len(entry["hi"]) > 0


def test_lookup_by_english_term():
    entry = LegalGlossary.lookup("prior art")
    assert entry is not None
    assert entry["hi"]


def test_detect_glossary_terms_in_query():
    hits = LegalGlossary.detect_glossary_terms(
        "Is my traditional knowledge a prior art for a patent claim?"
    )
    labels = [h[0] for h in hits]
    assert "prior art" in labels
    assert "patent" in labels


def test_to_hindi_appends_glossary_block():
    out = LegalGlossary.to_hindi("Explain novelty and the disclosure of origin rule.")
    assert "()" not in out
    assert "नवीनता" in out
    assert "novelty" in out


def test_glossary_never_doubles_entries():
    hits1 = LegalGlossary.detect_glossary_terms("novelty novelty novelty")
    # Duplicate matches collapse to one entry per term.
    assert len([h for h in hits1 if h[0] == "novelty"]) == 1