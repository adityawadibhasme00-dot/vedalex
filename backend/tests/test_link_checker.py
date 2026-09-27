"""A5 — dead-link checker: offline by default, injectable fetcher, CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.ingestion import sources as corpus_sources
from app.services import link_checker

pytestmark = pytest.mark.unit

BACKEND_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _offline_by_default(monkeypatch):
    monkeypatch.delenv("IPSAKTI_LINK_CHECK_LIVE", raising=False)


def test_offline_mode_skips_network_by_default():
    outcome = link_checker.check_url("https://example.gov.in/page")
    assert outcome["status"] == "skipped"
    assert "disabled" in outcome["detail"]


def test_live_flag_enables_checks(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LINK_CHECK_LIVE", "1")
    assert link_checker.live_enabled() is True
    outcome = link_checker.check_url(
        "https://example.gov.in/page", fetcher=lambda url: True
    )
    assert outcome["status"] == "ok"


def test_dead_link_detected_with_injected_fetcher():
    outcome = link_checker.check_url("https://old.gov.in/gone", fetcher=lambda u: False)
    assert outcome["status"] == "dead"


def test_fetcher_exception_classified_dead():
    def boom(url):
        raise RuntimeError("DNS failure")

    outcome = link_checker.check_url("https://x.gov.in", fetcher=boom)
    assert outcome["status"] == "dead"
    assert "DNS failure" in outcome["detail"]


def test_corpus_report_covers_every_url():
    expected_urls = sum(
        len(s.get("canonical_urls") or []) + len(s.get("pointer_urls") or [])
        for s in corpus_sources.list_sources()
    )
    report = link_checker.check_corpus_links(fetcher=lambda url: True)
    assert report["urls_checked"] == expected_urls
    assert report["ok"] == expected_urls
    assert report["dead"] == 0
    assert report["live"] is True


def test_corpus_report_subset_and_unknown_source():
    report = link_checker.check_corpus_links(
        fetcher=lambda url: False, source_ids=["nba", "ghost"]
    )
    statuses = {r["source_id"]: r["status"] for r in report["results"]}
    assert statuses["nba"] == "dead"
    assert statuses["ghost"] == "dead"
    assert any(r["url"] == "" and r["source_id"] == "ghost" for r in report["results"])


def test_offline_report_counts_skipped():
    report = link_checker.check_corpus_links()
    assert report["live"] is False
    assert report["skipped"] == report["urls_checked"]
    assert report["ok"] == 0 and report["dead"] == 0


def test_cli_runs_offline_with_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(BACKEND_ROOT / "scripts" / "check_links.py")],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(BACKEND_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert "checked" in proc.stdout
    assert "skipped" in proc.stdout
