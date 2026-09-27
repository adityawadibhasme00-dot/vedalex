"""A5 — dead-link checker for official corpus URLs.

Walks every ``CORPUS`` entry in ``app.ingestion.sources`` (canonical and
pointer URLs) and classifies each link as ``ok`` / ``dead`` / ``skipped``.
Offline by default (``IPSAKTI_LINK_CHECK_LIVE=0``): no network is touched
unless explicitly enabled, and the live fetch reuses the whitelist-guarded
``ingestion.fetchers`` layer. The fetcher is injectable for tests and for
the ``scripts/check_links.py`` CLI.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

from app.ingestion import sources as corpus_sources
from app.ingestion.fetchers import fetch_html

logger = logging.getLogger(__name__)

Fetcher = Callable[[str], Any]


def live_enabled() -> bool:
    """True only when IPSAKTI_LINK_CHECK_LIVE opts in to real network calls."""
    return os.environ.get("IPSAKTI_LINK_CHECK_LIVE", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _default_fetch(url: str) -> bool:
    return fetch_html(url) is not None


def check_url(url: str, fetcher: Fetcher | None = None) -> dict[str, Any]:
    """Classify one URL; never raises — network failures are 'dead'."""
    if fetcher is None:
        if not live_enabled():
            return {"url": url, "status": "skipped", "detail": "live check disabled"}
        fetcher = _default_fetch
    try:
        ok = bool(fetcher(url))
    except Exception as exc:  # noqa: BLE001 — a dead link must not break the run
        return {"url": url, "status": "dead", "detail": str(exc)[:200]}
    if ok:
        return {"url": url, "status": "ok", "detail": ""}
    return {"url": url, "status": "dead", "detail": "fetch returned no content"}


def check_corpus_links(
    fetcher: Fetcher | None = None,
    source_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Check canonical + pointer URLs of every (or selected) corpus source."""
    ids = source_ids or [s["id"] for s in corpus_sources.list_sources()]
    results: list[dict[str, Any]] = []
    for source_id in ids:
        source = corpus_sources.CORPUS_BY_ID.get(source_id)
        if source is None:
            results.append(
                {
                    "source_id": source_id,
                    "url": "",
                    "status": "dead",
                    "detail": "unknown source",
                }
            )
            continue
        urls = list(source.get("canonical_urls") or []) + list(
            source.get("pointer_urls") or []
        )
        for url in urls:
            outcome = check_url(str(url), fetcher=fetcher)
            outcome["source_id"] = source_id
            results.append(outcome)
    counts = {"ok": 0, "dead": 0, "skipped": 0}
    for item in results:
        counts[str(item["status"])] = counts.get(str(item["status"]), 0) + 1
    return {
        "live": fetcher is not None or live_enabled(),
        "sources_checked": len(ids),
        "urls_checked": len(results),
        "ok": counts.get("ok", 0),
        "dead": counts.get("dead", 0),
        "skipped": counts.get("skipped", 0),
        "results": results,
    }
