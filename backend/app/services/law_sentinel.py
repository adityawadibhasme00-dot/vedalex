"""A1 — Law-Change Sentinel (basic).

Watches the P0/P1 statutory sources already declared in
``app.ingestion.sources.CORPUS`` (India Code, IP India, NBA, WIPO by
default), fetches each source's canonical URL, and compares a SHA-256
content hash against the stored state:

  - first fetch  -> ``first_seen`` (baseline recorded)
  - same hash    -> ``unchanged``
  - new hash     -> ``changed``: row flagged ``stale`` + ``needs_reembed``
  - fetch fails  -> ``error`` (previous hash preserved)

Every run appends a ``law_sentinel.run`` event to the hash-chained audit
log. The re-embed hook is completed with ``mark_reembedded`` once the index
refresh (admin reindex or scheduled ingestion) has picked up the change.

Network access is injectable (``fetcher``) so the whole flow is testable
offline; the default fetcher reuses the guarded ``ingestion.fetchers`` layer.
"""

from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.ingestion import sources as corpus_sources
from app.ingestion.fetchers import fetch_html
from app.models.db_models import LawSourceState
from app.services.audit_chain import record_event

logger = logging.getLogger(__name__)

DEFAULT_SENTINEL_IDS: tuple[str, ...] = ("india_code", "ip_india", "nba", "wipo")

Fetcher = Callable[[str], tuple[str, str] | None]


def watched_ids() -> tuple[str, ...]:
    """Sentinel watch-list: env override (csv) or the default P0/P1 laws."""
    raw = os.environ.get("IPSAKTI_SENTINEL_SOURCES", "").strip()
    ids = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not ids:
        ids = DEFAULT_SENTINEL_IDS
    return tuple(sid for sid in ids if sid in corpus_sources.CORPUS_BY_ID)


def content_hash(text: str) -> str:
    """Stable SHA-256 over whitespace-normalised source text."""
    normalized = " ".join((text or "").split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _update(row: LawSourceState, **fields: Any) -> None:
    """Assign ORM columns without tripping the untyped-Column checker."""
    for key, value in fields.items():
        setattr(row, key, value)


def _default_fetcher(url: str) -> tuple[str, str] | None:
    return fetch_html(url)


def check_source(
    db: Session,
    source: dict[str, Any],
    fetched: tuple[str, str] | None,
    error: str = "",
) -> dict[str, Any]:
    """Compare one fetch result against stored state; persists the outcome."""
    source_id = str(source["id"])
    url = str(source["canonical_urls"][0])
    now = _now()
    row = db.get(LawSourceState, source_id)

    if fetched is None:
        if row is None:
            row = LawSourceState(
                source_id=source_id,
                url=url,
                last_status="error",
                last_error=error[:300],
                last_checked_at=now,
            )
            db.add(row)
        else:
            _update(
                row,
                last_status="error",
                last_error=error[:300],
                last_checked_at=now,
            )
        db.commit()
        return {
            "source_id": source_id,
            "event": "error",
            "url": url,
            "error": error[:300],
        }

    _, text = fetched
    new_hash = content_hash(text)

    if row is None:
        row = LawSourceState(
            source_id=source_id,
            url=url,
            content_hash=new_hash,
            last_checked_at=now,
            last_status="ok",
            last_error="",
        )
        db.add(row)
        db.commit()
        return {"source_id": source_id, "event": "first_seen", "url": url}

    event = "unchanged"
    if row.content_hash and str(row.content_hash) != new_hash:
        event = "changed"
        _update(
            row,
            content_hash=new_hash,
            stale=True,
            needs_reembed=True,
            changed_at=now,
            change_count=int(row.change_count or 0) + 1,
        )
        logger.warning(
            "Law change detected for %s (%s) — flagged stale for re-embed",
            source_id,
            url,
        )
    _update(row, last_status="ok", last_error="", last_checked_at=now)
    db.commit()
    return {"source_id": source_id, "event": event, "url": url}


def run_sentinel(
    db: Session,
    fetcher: Fetcher | None = None,
    source_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Run one full sentinel cycle over the watch-list; audits the result."""
    fetch = fetcher or _default_fetcher
    ids = tuple(source_ids) if source_ids else watched_ids()
    summary: dict[str, Any] = {
        "ran_at": _now(),
        "watched": list(ids),
        "first_seen": [],
        "unchanged": [],
        "changed": [],
        "errors": [],
    }
    for source_id in ids:
        source = corpus_sources.CORPUS_BY_ID.get(source_id)
        if source is None:
            summary["errors"].append({"source_id": source_id, "error": "unknown source"})
            continue
        url = str(source["canonical_urls"][0])
        try:
            fetched = fetch(url)
            error = "" if fetched else "fetch returned no content"
        except Exception as exc:  # noqa: BLE001 — one bad source never aborts the run
            fetched = None
            error = str(exc)[:300]
        outcome = check_source(db, source, fetched, error=error)
        bucket = outcome["event"]
        if bucket in ("first_seen", "unchanged", "changed"):
            summary[bucket].append(source_id)
        else:
            summary["errors"].append(
                {"source_id": source_id, "error": outcome.get("error", "error")}
            )
    try:
        record_event(
            db,
            "law_sentinel.run",
            {
                "watched": summary["watched"],
                "changed": summary["changed"],
                "errors": [e["source_id"] for e in summary["errors"]],
            },
        )
    except Exception:  # noqa: BLE001 — sentinel must keep its own result
        logger.warning("law_sentinel audit record failed", exc_info=True)
    return summary


def mark_reembedded(db: Session, source_id: str) -> bool:
    """Re-embed hook completion: clear stale/needs_reembed flags."""
    row = db.get(LawSourceState, source_id)
    if row is None:
        return False
    _update(row, stale=False, needs_reembed=False)
    db.commit()
    return True


def sentinel_status(db: Session) -> list[dict[str, Any]]:
    """State of every watched source (never-checked sources included)."""
    rows = {
        str(row.source_id): row
        for row in db.query(LawSourceState).all()
    }
    out: list[dict[str, Any]] = []
    for source_id in watched_ids():
        row = rows.get(source_id)
        out.append(
            {
                "source_id": source_id,
                "url": str(row.url) if row else "",
                "status": str(row.last_status) if row else "never",
                "stale": bool(row.stale) if row else False,
                "needs_reembed": bool(row.needs_reembed) if row else False,
                "change_count": int(row.change_count or 0) if row else 0,
                "last_checked_at": str(row.last_checked_at) if row else None,
                "changed_at": str(row.changed_at) if row else None,
                "last_error": str(row.last_error or "") if row else "",
            }
        )
    return out
