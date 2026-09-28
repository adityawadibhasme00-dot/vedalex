"""Jurisdiction Router tests.

Verifies the golden rule: India and International legal frameworks are never
mixed, and AYUSH / traditional-knowledge questions resolve to the India
framework instead of requesting clarification.
"""

from app.services.jurisdiction_router import (
    FRAMEWORKS,
    _keyword_hint,
    filter_sources_by_jurisdiction,
    resolve_jurisdiction,
)


def test_explicit_toggle_wins():
    res = resolve_jurisdiction(
        "Can I patent a turmeric supplement?",
        context={"jurisdiction": "International"},
    )
    assert res["mode"] == "International"
    assert res["clarification_needed"] is False
    assert res["resolved_via"] == "jurisdiction toggle (explicit)"


def test_keyword_resolves_indic():
    res = resolve_jurisdiction(
        "Can I patent an Ayurvedic formulation based on Charaka Samhita "
        "for treating diabetes?"
    )
    assert res["mode"] == "India"
    assert res["clarification_needed"] is False
    assert res["resolved_via"] == "keyword cue"


def test_international_cue_beats_domain_keyword():
    res = resolve_jurisdiction(
        "Can I export this Ayurvedic herbal formulation to the United States?"
    )
    assert res["mode"] == "International"
    assert res["clarification_needed"] is False


def test_no_signal_clarifies():
    res = resolve_jurisdiction("What are the fees?")
    assert res["clarification_needed"] is True
    assert res["mode"] is None


def test_classical_text_cue():
    res = resolve_jurisdiction(
        "Do I need TKDL clearance for an Ashwagandha classical formulation?"
    )
    assert res["mode"] == "India"


def test_cleartext_frameworks_never_mixed():
    # India mode keeps India + neutral + International (WIPO/PCT context),
    # but never US/Canada-specific law.
    assert FRAMEWORKS["India"]["allowed_jurisdictions"] == {"", "India", "International"}
    assert FRAMEWORKS["International"]["allowed_jurisdictions"] == {
        "", "International", "United States", "Canada",
    }


def test_filter_sources_by_jurisdiction_gates_cross_regime():
    india = {"jurisdiction": "India", "title": "Patent Act"}
    us = {"jurisdiction": "United States", "title": "FDA DSHEA"}
    ca = {"jurisdiction": "Canada", "title": "NHPR"}
    neutral = {"title": "Ayurvedic Pharmacopoeia"}
    kept = filter_sources_by_jurisdiction([india, us, ca, neutral], "India")
    titles = {s["title"] for s in kept}
    assert "Patent Act" in titles
    assert "Ayurvedic Pharmacopoeia" in titles
    assert "FDA DSHEA" not in titles
    assert "NHPR" not in titles

    kept_intl = filter_sources_by_jurisdiction(
        [india, us, {**india, "title": "PCT", "jurisdiction": "International"}, neutral],
        "International",
    )
    intl_titles = {s["title"] for s in kept_intl}
    assert "Patent Act" not in intl_titles
    assert "PCT" in intl_titles


# ---------------------------------------------------------------------------
# Cue matching must respect token boundaries
# ---------------------------------------------------------------------------

def test_short_cue_does_not_match_inside_ordinary_words():
    """Regression: the cue ``us`` matched inside ``users``, routing an
    adversarial SQL string to the International framework. Retrieval then
    returned evidence for a regime the user never asked about and the copilot
    answered it with high confidence — a fabricated answer."""
    assert _keyword_hint("SELECT * FROM users; DROP TABLE users;--") is None
    assert _keyword_hint("because the focus is unclear") is None
    assert _keyword_hint("discuss the status") is None


def test_standalone_short_cue_still_resolves():
    # "us" as a real token must keep working, and so must longer cues.
    assert _keyword_hint("Can I export this to the US?") == "International"
    assert _keyword_hint("FDA requirements for supplements") == "International"
    assert _keyword_hint("export to the United States") == "International"


def test_phrase_cue_matches_with_boundaries():
    assert _keyword_hint("What does section 3(p) say?") == "India"
    assert _keyword_hint("Is TKDL clearance needed?") == "India"
    assert _keyword_hint("section3p") is None
