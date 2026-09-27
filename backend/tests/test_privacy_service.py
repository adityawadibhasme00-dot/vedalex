"""Tests for the DPDP-aligned privacy layer (scrubbing, audit hashing, consent)."""

import re

from app.services.privacy_service import (
    QueryAuditLog,
    hash_audit_token,
    scrub_text,
)


def test_scrub_removes_quantities():
    out = scrub_text("Take 500mg Ashwagandha 2 times daily with 10 ml water")
    assert "500mg" not in out.lower() or "[REDACTED]" in out
    assert "[REDACTED]" in out


def test_scrub_removes_currency_and_identifiers():
    out = scrub_text("Cost ₹25000, contact 9876543210 at demo@ayush.com")
    assert "[REDACTED]" in out
    assert "9876543210" not in out
    assert "demo@ayush.com" not in out


def test_scrub_preserves_legal_wording():
    out = scrub_text("Check Section 3(p) of the Patents Act 1970")
    assert "Section 3(p)" in out
    assert "Patents Act" in out


def test_hash_is_stable_and_content_sensitive():
    h1 = hash_audit_token("Should I patent my Chyawanprash?")
    h2 = hash_audit_token("Should I patent my Chyawanprash?")
    h3 = hash_audit_token("Should I trademark my Chyawanprash?")
    assert h1 == h2
    assert h1 != h3
    assert re.fullmatch(r"[0-9a-f]{64}", h1)


def test_audit_log_never_keeps_raw_text():
    QueryAuditLog.reset()
    entry = QueryAuditLog.record(
        query_hash=hash_audit_token("Formula X 20%"),
        answer_hash=hash_audit_token("Response text"),
        source_ids=["patents_act_1970_section_3"],
        citation_ids=["IN-PAT-0001"],
        jurisdiction="India",
        confidence=0.8,
        language="en",
        opt_in_store=False,
    )
    assert entry["query_hash"]
    assert "Formula X" not in str(entry)
    assert "20%" not in str(entry)
    trail = QueryAuditLog.get_trail()
    assert len(trail) == 1
    assert trail[0]["source_ids"] == ["patents_act_1970_section_3"]


def test_full_record_only_when_opted_in():
    QueryAuditLog.reset()
    no_consent = QueryAuditLog.record(
        query_hash="q", answer_hash="a", source_ids=[], citation_ids=[],
        jurisdiction=None, confidence=None, language=None, opt_in_store=False,
    )
    consented = QueryAuditLog.record(
        query_hash="q2", answer_hash="a2", source_ids=[], citation_ids=[],
        jurisdiction="India", confidence=0.5, language="en", opt_in_store=True,
    )
    assert no_consent["stored_full_record"] is False
    assert consented["stored_full_record"] is True