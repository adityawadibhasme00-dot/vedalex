"""
Scheduled ingestion for IP-SAKTI.

Runs the corpus pipeline on a cadence in the background so the knowledge base
stays current without manual intervention:
  - regulations/notices  -> every 24h   (IP India, India Code, NBA, AYUSH notices)
  - patents              -> every 7d    (IP India, WIPO, TKDL pointers)
  - pharmacopoeia/standards -> every 30d (API monographs)
Change detection (content hashing) ensures only changed documents re-embed.

Hardening / reliability guarantees:
  - Per-source retry with exponential backoff: a failing source is retried
    (IPSAKTI_INGESTION_MAX_ATTEMPTS, default 3) with a growing delay
    (IPSAKTI_INGESTION_BACKOFF_BASE, default 300s) before being put on
    cooldown, so one flaky endpoint cannot block the whole cadence.
  - Per-source health state (last_success / last_error / attempts) persisted
    to the pipeline state file and surfaced via get_scheduler_status().
  - Failed sources are skipped during cooldown instead of timing out the loop.

Disable with IPSAKTI_INGESTION_SCHEDULER=0; poll interval via
IPSAKTI_INGESTION_POLL_SEC (default 3600s).
"""

import logging
import os
import threading
import time
from typing import Any

from app.ingestion.pipeline import STATE_FILE, _load_state, _save_state
from app.core.lock import inspect as _lock_inspect
from app.core.lock import single_writer

logger = logging.getLogger(__name__)

_CADENCE_SECONDS = {
    "daily": 24 * 3600,
    "weekly": 7 * 24 * 3600,
    "monthly": 30 * 24 * 3600,
}

_thread: threading.Thread | None = None
_stop_event = threading.Event()
_lock = threading.Lock()
_last_summary: dict[str, Any] = {}


def _max_attempts() -> int:
    try:
        return max(1, int(os.environ.get("IPSAKTI_INGESTION_MAX_ATTEMPTS", "3")))
    except ValueError:
        return 3


def _backoff_base() -> int:
    try:
        return max(30, int(os.environ.get("IPSAKTI_INGESTION_BACKOFF_BASE", "300")))
    except ValueError:
        return 300


def _scheduler_enabled() -> bool:
    return os.environ.get("IPSAKTI_INGESTION_SCHEDULER", "1").strip().lower() not in (
        "0", "false", "off", "no",
    )


def _poll_interval() -> int:
    try:
        return max(60, int(os.environ.get("IPSAKTI_INGESTION_POLL_SEC", "3600")))
    except ValueError:
        return 3600


def _ingest_lock_ttl() -> int:
    """Lease length for the single-writer guard.

    Must exceed the worst-case cycle (many slow official sources, each with its
    own retry/backoff) so a healthy holder is never declared dead mid-run.  If
    the process dies the lease still expires and the schedule self-heals.
    """
    try:
        return max(
            120, int(os.environ.get("IPSAKTI_INGESTION_LOCK_TTL", "1800"))
        )
    except ValueError:
        return 1800


def _read_health_state() -> dict[str, Any]:
    return _load_state().get("scheduler", {}).get("sources", {})


def _write_health_state(health: dict[str, Any]) -> None:
    try:
        state = _load_state()
        state.setdefault("scheduler", {})["sources"] = health
        _save_state(state)
    except Exception as exc:
        logger.debug("Failed to persist scheduler health state: %s", exc)


def _source_health(health: dict[str, Any], source_id: str) -> dict[str, Any]:
    return health.setdefault(source_id, {
        "attempts": 0,
        "failures": 0,
        "last_success": None,
        "last_error": "",
        "cooldown_until": 0,
    })


def _source_on_cooldown(failures: int, cooldown_until: float) -> bool:
    if failures <= 0:
        return False
    return time.time() < cooldown_until


def _attempt_cost(attempt: int) -> int:
    """Exponential backoff: base * 2^(attempt-1), capped at ~2h."""
    return min(_backoff_base() * (2 ** max(0, attempt - 1)), 2 * 3600)


def _due_sources() -> list:
    """Return corpus ids whose cadence window has elapsed AND are not on
    retry-cooldown from consecutive failed attempts."""
    from app.ingestion import sources as src

    state = _load_state()
    health = _read_health_state()
    now = time.time()
    due: list = []
    for source in src.list_sources():
        sid = source["id"]
        cadence = _CADENCE_SECONDS.get(source.get("schedule", "weekly"))
        if cadence is None:
            # "on_demand" (and unknown) schedules are only ever run manually —
            # never auto-scheduled, so skip them entirely.
            continue
        last = state.get("sources", {}).get(sid, {}).get("last_run")
        h = _source_health(health, sid)
        if _source_on_cooldown(h["failures"], h.get("cooldown_until", 0)):
            logger.info(
                "Source %s on retry cooldown (%d consecutive failures; next after %.0fs) — skipped",
                sid, h["failures"], h.get("cooldown_until", 0) - now,
            )
            continue
        if not last:
            due.append(sid)
            continue
        try:
            last_ts = time.mktime(time.strptime(last, "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            due.append(sid)
            continue
        if now - last_ts >= cadence:
            due.append(sid)
    return due


def _ingest_source_guarded(sid: str) -> dict[str, Any]:
    """Run one ingestion attempt for a source. On failure record the failure and
    schedule an exponential-backoff cooldown (persisted) so the scheduler keeps
    cycling without blocking on one flaky endpoint."""
    from app.ingestion.pipeline import run_ingestion

    health = _read_health_state()
    h = _source_health(health, sid)
    now = time.time()

    try:
        summary = run_ingestion(
            source_ids=[sid],
            mode="update",
            include_local=False,
            include_seeds=False,
        )
        if summary.get("ok"):
            h["attempts"] = 0
            h["failures"] = 0
            h["last_success"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            h["last_error"] = ""
            h["cooldown_until"] = 0
            result = {
                "source_id": sid,
                "ok": True,
                "failures": 0,
                "chunks": summary.get("total_chunks", 0),
                "results": summary.get("results", []),
            }
            _write_health_state(health)
            logger.info("Ingested %s OK", sid)
            return result
        h["failures"] += 1
        h["attempts"] = h["failures"]
        h["cooldown_until"] = now + _attempt_cost(h["failures"])
        results = summary.get("results", [])
        source_found: dict[str, Any] = next((r for r in results if r.get("source_id") == sid), {})
        h["last_error"] = (
            source_found.get("error")
            or str(summary.get("error", "unsuccessful run"))
        )[:200]
    except Exception as exc:
        h["failures"] += 1
        h["attempts"] = h["failures"]
        h["cooldown_until"] = now + _attempt_cost(h["failures"])
        h["last_error"] = str(exc)[:200]

    _write_health_state(health)
    logger.warning(
        "Source %s failed (total %d consecutive failures; cooldown %.0fs)",
        sid, h["failures"], h["cooldown_until"] - now,
    )
    return {
        "source_id": sid,
        "ok": False,
        "failures": h["failures"],
        "last_error": h["last_error"],
    }


def _watch_enabled() -> bool:
    import os

    if os.environ.get("IPSAKTI_WATCH_SCHEDULER", "1").strip() in {"0", "false", "off"}:
        return False
    return _scheduler_enabled()


def _run_watch_cycle_guarded() -> dict[str, Any] | None:
    """Screen active watch profiles after a successful ingestion cycle (A2).

    Failures are logged, never raised: a watch hiccup must not stop ingestion.
    """
    if not _watch_enabled():
        return None
    try:
        from app.core.database import SessionLocal
        from app.services.watch_service import run_watch_cycle

        db = SessionLocal()
        try:
            return run_watch_cycle(db)
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001 - background cycle must stay non-fatal
        logger.warning("Scheduled patent-watch cycle failed: %s", exc)
        return None


def _scheduler_loop() -> None:
    global _last_summary
    while not _stop_event.is_set():
        try:
            due = []
            with _lock:
                due = _due_sources()
            if due:
                # Single-writer guard: only one replica may scrape the official
                # sources in a given cycle.  Without this, N replicas means N
                # concurrent crawls of IP India / India Code / WIPO, which gets
                # the deployment rate-limited and silently stops the Law
                # Sentinel from noticing amended clauses.
                with single_writer("ingestion", ttl=_ingest_lock_ttl()) as held:
                    if not held:
                        _last_summary = {
                            "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "due": due,
                            "ok_sources": [],
                            "failed_sources": [],
                            "results": [],
                            "skipped": "another replica holds the ingestion lock",
                        }
                        _stop_event.wait(_poll_interval())
                        continue
                    with _lock:
                        results = [_ingest_source_guarded(sid) for sid in due]
                        ok_now = [r["source_id"] for r in results if r.get("ok")]
                        _last_summary = {
                            "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "due": due,
                            "ok_sources": ok_now,
                            "failed_sources": [r["source_id"] for r in results if not r.get("ok")],
                            "results": results,
                        }
                        logger.info("Scheduled ingestion ran for %s: %s", due, _last_summary)
                    if any(sid.startswith("patent") for sid in ok_now):
                        watch = _run_watch_cycle_guarded()
                        if watch:
                            logger.info("Scheduled patent-watch cycle: %s", watch)
        except Exception as exc:
            logger.exception("Scheduled ingestion cycle failed: %s", exc)
        _stop_event.wait(_poll_interval())


def start_ingestion_scheduler() -> threading.Thread | None:
    global _thread
    if not _scheduler_enabled():
        logger.info("Ingestion scheduler disabled (IPSAKTI_INGESTION_SCHEDULER=0)")
        return None
    if _thread is not None and _thread.is_alive():
        return _thread
    _stop_event.clear()
    _thread = threading.Thread(
        target=_scheduler_loop,
        name="ipsakti-ingestion-scheduler",
        daemon=True,
    )
    _thread.start()
    logger.info("Ingestion scheduler started (poll=%ss)", _poll_interval())
    return _thread


def stop_ingestion_scheduler() -> None:
    global _thread
    _stop_event.set()
    if _thread is not None:
        _thread.join(timeout=5)
        _thread = None
    logger.info("Ingestion scheduler stopped")


def get_scheduler_status() -> dict[str, Any]:
    return {
        "enabled": _scheduler_enabled(),
        "poll_interval_sec": _poll_interval(),
        "cadence": _CADENCE_SECONDS,
        "max_attempts_per_source": _max_attempts(),
        "backoff_base_sec": _backoff_base(),
        "thread_alive": bool(_thread is not None and _thread.is_alive()),
        "single_writer_lock": _lock_inspect("ingestion"),
        "lock_ttl_sec": _ingest_lock_ttl(),
        "last_summary": _last_summary,
        "source_health": _read_health_state(),
        "state_file": STATE_FILE,
    }


def run_forever() -> None:  # pragma: no cover - process entrypoint
    """Run the ingestion loop in the foreground until SIGINT/SIGTERM.

    This is the dedicated-worker entrypoint (``python -m
    app.services.ingestion_scheduler``).  It exists so the schedule is a
    deployment decision rather than a side effect of the web process: the API
    replicas can be scaled to zero and restarted freely while ingestion keeps
    its cadence.  The single-writer lock still applies, so running several of
    these is safe — the extras simply skip each cycle.
    """
    import signal

    logger.info(
        "Ingestion worker starting (poll=%ss, cadence=%s, lock_ttl=%ss)",
        _poll_interval(), _CADENCE_SECONDS, _ingest_lock_ttl(),
    )

    def _stop(*_: Any) -> None:
        logger.info("Ingestion worker: shutdown requested")
        _stop_event.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    _stop_event.clear()
    _scheduler_loop()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_forever()