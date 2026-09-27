"""A1 — Law-Change Sentinel: fetch → content-hash diff → stale flag →
re-embed marker, with audit-chain integration and admin endpoints.
"""

from __future__ import annotations

import pytest

from app.models.db_models import AuditLogEntry, LawSourceState
from app.services import law_sentinel
from app.services.audit_chain import verify_chain

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "off")
    monkeypatch.delenv("IPSAKTI_SENTINEL_SOURCES", raising=False)


def _fetch(text: str):
    def fake(url: str) -> tuple[str, str] | None:
        return ("Fetched Title", text)

    return fake


# ---------------------------------------------------------------------------
# Core detection loop
# ---------------------------------------------------------------------------


def test_first_fetch_records_baseline_without_stale(db_session):
    summary = law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("statute text v1"), source_ids=["india_code"]
    )
    assert summary["first_seen"] == ["india_code"]
    row = db_session.get(LawSourceState, "india_code")
    assert row is not None
    assert row.stale is False
    assert row.needs_reembed is False
    assert row.content_hash == law_sentinel.content_hash("statute text v1")
    assert row.last_status == "ok"


def test_same_content_is_unchanged(db_session):
    law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("same text"), source_ids=["ip_india"]
    )
    summary = law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("same text"), source_ids=["ip_india"]
    )
    assert summary["unchanged"] == ["ip_india"]
    assert summary["changed"] == []
    row = db_session.get(LawSourceState, "ip_india")
    assert row.stale is False
    assert int(row.change_count) == 0


def test_changed_content_sets_stale_and_reembed_flags(db_session):
    law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("old wording"), source_ids=["nba"]
    )
    summary = law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("NEW amended wording"), source_ids=["nba"]
    )
    assert summary["changed"] == ["nba"]
    row = db_session.get(LawSourceState, "nba")
    assert row.stale is True
    assert row.needs_reembed is True
    assert row.changed_at is not None
    assert int(row.change_count) == 1
    assert row.content_hash == law_sentinel.content_hash("NEW amended wording")


def test_fetch_error_preserves_previous_hash(db_session):
    law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("known good text"), source_ids=["wipo"]
    )
    summary = law_sentinel.run_sentinel(
        db_session, fetcher=lambda url: None, source_ids=["wipo"]
    )
    assert summary["errors"] == [
        {"source_id": "wipo", "error": "fetch returned no content"}
    ]
    row = db_session.get(LawSourceState, "wipo")
    assert row.content_hash == law_sentinel.content_hash("known good text")
    assert row.last_status == "error"
    assert row.stale is False


def test_fetcher_exception_is_contained(db_session):
    def boom(url: str) -> tuple[str, str] | None:
        raise RuntimeError("connection reset")

    summary = law_sentinel.run_sentinel(
        db_session, fetcher=boom, source_ids=["india_code"]
    )
    assert summary["errors"][0]["source_id"] == "india_code"
    assert "connection reset" in summary["errors"][0]["error"]


def test_unknown_source_id_reported_as_error(db_session):
    summary = law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("x"), source_ids=["no_such_source"]
    )
    assert summary["errors"][0]["error"] == "unknown source"


# ---------------------------------------------------------------------------
# Watch-list + re-embed hook + status
# ---------------------------------------------------------------------------


def test_default_watch_list_matches_blueprint_sources():
    watched = law_sentinel.watched_ids()
    assert watched == ("india_code", "ip_india", "nba", "wipo")


def test_env_override_filters_unknown_ids(db_session, monkeypatch):
    monkeypatch.setenv("IPSAKTI_SENTINEL_SOURCES", "india_code, bogus, nba")
    assert law_sentinel.watched_ids() == ("india_code", "nba")


def test_mark_reembedded_clears_flags(db_session):
    law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("v1"), source_ids=["india_code"]
    )
    law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("v2 changed"), source_ids=["india_code"]
    )
    assert law_sentinel.mark_reembedded(db_session, "india_code") is True
    row = db_session.get(LawSourceState, "india_code")
    assert row.stale is False
    assert row.needs_reembed is False
    assert int(row.change_count) == 1
    assert law_sentinel.mark_reembedded(db_session, "never_seen") is False


def test_sentinel_status_includes_never_checked_sources(db_session):
    status = law_sentinel.sentinel_status(db_session)
    ids = [s["source_id"] for s in status]
    assert ids == ["india_code", "ip_india", "nba", "wipo"]
    assert all(s["status"] == "never" for s in status)
    law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("text"), source_ids=["india_code"]
    )
    status = law_sentinel.sentinel_status(db_session)
    india = next(s for s in status if s["source_id"] == "india_code")
    assert india["status"] == "ok"
    assert india["stale"] is False


# ---------------------------------------------------------------------------
# Audit chain integration + endpoints
# ---------------------------------------------------------------------------


def test_sentinel_runs_are_audit_logged(db_session):
    law_sentinel.run_sentinel(
        db_session, fetcher=_fetch("v1"), source_ids=["india_code"]
    )
    rows = (
        db_session.query(AuditLogEntry)
        .filter(AuditLogEntry.event_type == "law_sentinel.run")
        .all()
    )
    assert rows
    assert '"changed":["india_code"]' in rows[0].payload or "india_code" in rows[0].payload
    assert verify_chain(db_session)["valid"] is True


def test_status_endpoint_is_public(api_client, db_session):
    resp = api_client.get("/api/v1/admin/law-sentinel")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["sources"]) == 4
    assert {s["source_id"] for s in body["sources"]} == {
        "india_code",
        "ip_india",
        "nba",
        "wipo",
    }


def test_run_endpoint_requires_valid_api_key(api_client):
    resp = api_client.post(
        "/api/v1/admin/law-sentinel/run",
        json={"api_key": "wrong-key", "source_ids": ["india_code"]},
    )
    assert resp.status_code == 403


def test_run_endpoint_executes_with_patched_fetcher(
    api_client, db_session, monkeypatch
):
    monkeypatch.setattr(law_sentinel, "fetch_html", lambda url: ("T", "live text"))
    resp = api_client.post(
        "/api/v1/admin/law-sentinel/run",
        json={
            "api_key": "pytest-only-admin-key-not-for-production",
            "source_ids": ["india_code"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["first_seen"] == ["india_code"] or body["unchanged"] == ["india_code"]
    status = api_client.get("/api/v1/admin/law-sentinel").json()
    india = next(s for s in status["sources"] if s["source_id"] == "india_code")
    assert india["status"] == "ok"
