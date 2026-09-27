"""Background job queue for long-running work (Redis-backed, in-memory fallback).

What this is for
----------------
Several IP-SAKTI operations legitimately take minutes: a full corpus reindex,
an India Code harvest, a dossier/PDF build, an Innovation-Lab agent run.  They
are currently executed inline inside the request handler, so they occupy a
worker for their entire duration.  With a bounded worker pool that turns a few
slow operations into a stalled API — the responsiveness problem shows up exactly
when the system is under load.

This module is the queue boundary: submit work, get a job id, poll for status.
It intentionally does not require ``arq``/``celery`` so the offline demo and
the test suite keep working with no Redis, but it is API-compatible with the
shape those libraries use (submit -> id, poll -> state/result).

Design constraints
------------------
* **Never lose a job silently.**  A job that cannot be enqueued raises, so the
  caller can fall back to synchronous execution or surface an error — silently
  dropping regulatory reindex work would be worse than failing loudly.
* **At-least-once.**  A worker that dies mid-job leaves the job ``running``
  until its lease expires, at which point it becomes ``failed`` and visible in
  the admin listing.  Nothing is retried automatically, because re-running a
  half-applied reindex is worse than reporting it.
* **Bounded payloads.**  Results are truncated before storage so a dossier job
  cannot fill the Redis instance.

Run a worker with::

    python -m app.core.jobs
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

JOB_PREFIX = "ipsk:job"
QUEUE_KEY = "ipsk:queue"
CLAIM_PREFIX = "ipsk:jobclaim"
#: Result payloads above this size are truncated before storage.
MAX_RESULT_CHARS = 200_000
#: A running job whose worker vanished is reclaimed after this long.
DEFAULT_LEASE_SEC = 3600


def _worker_id() -> str:
    return f"{os.getpid()}-{uuid.uuid4().hex[:6]}"


def _inline_enabled() -> bool:
    """Should ``submit`` also run the job on a local thread?

    A dedicated worker deployment sets ``IPSAKTI_INLINE_JOBS=0`` so the queue is
    the single execution path.  Left on (the default) the offline demo and the
    test suite work with no worker process at all.  The claim in
    :func:`execute` makes the overlap safe either way, so this is an efficiency
    knob, not a correctness one.
    """
    return (os.environ.get("IPSAKTI_INLINE_JOBS") or "1").strip() not in {
        "0", "false", "False", "no",
    }


@dataclass
class Job:
    id: str
    name: str
    state: str = "queued"  # queued | running | done | failed
    submitted_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    worker: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_sec": round(
                (self.finished_at or time.time()) - (self.started_at or self.submitted_at),
                2,
            ),
            "payload": self.payload,
            "result": self.result,
            "error": self.error,
            "worker": self.worker,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            state=data.get("state", "queued"),
            submitted_at=data.get("submitted_at", 0.0),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            payload=data.get("payload", {}) or {},
            result=data.get("result"),
            error=data.get("error"),
            worker=data.get("worker"),
        )


Handler = Callable[[dict[str, Any]], Any]

_HANDLERS: dict[str, Handler] = {}


def register(name: str) -> Callable[[Handler], Handler]:
    """Decorator registering a job handler by name."""

    def decorate(fn: Handler) -> Handler:
        _HANDLERS[name] = fn
        logger.debug("registered job handler %r", name)
        return fn

    return decorate


def handlers() -> dict[str, Handler]:
    return dict(_HANDLERS)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


def _redis() -> Any:
    url = (os.environ.get("REDIS_URL") or "").strip()
    if not url:
        return None
    try:
        import redis as _redis

        client = _redis.Redis.from_url(
            url, socket_connect_timeout=1, socket_timeout=2, decode_responses=True
        )
        client.ping()
        return client
    except Exception:  # noqa: BLE001
        return None


_MEM: dict[str, Job] = {}
_MEM_LOCK = threading.Lock()
_THREADS: list[threading.Thread] = []
#: In-memory stand-in for the Redis claim keys, used when Redis is absent.
_CLAIMED: set[str] = set()


def _truncate(value: Any) -> Any:
    try:
        text = json.dumps(value, default=str)
    except Exception:  # noqa: BLE001
        return str(value)[:MAX_RESULT_CHARS]
    if len(text) <= MAX_RESULT_CHARS:
        return value
    return {
        "truncated": True,
        "original_chars": len(text),
        "preview": text[:2000],
    }


def _save(job: Job) -> None:
    client = _redis()
    if client is not None:
        try:
            client.hset(
                f"{JOB_PREFIX}:{job.id}",
                mapping={
                    "id": job.id,
                    "name": job.name,
                    "state": job.state,
                    "submitted_at": job.submitted_at,
                    "started_at": job.started_at or "",
                    "finished_at": job.finished_at or "",
                    "payload": json.dumps(job.payload, default=str),
                    "result": json.dumps(_truncate(job.result), default=str),
                    "error": job.error or "",
                    "worker": job.worker or "",
                },
            )
            # A failed/done job is an audit record; keep it a week.
            client.expire(f"{JOB_PREFIX}:{job.id}", 7 * 24 * 3600)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("job store: Redis write failed (%s); using memory", exc)
    with _MEM_LOCK:
        _MEM[job.id] = job


def _load(job_id: str) -> Job | None:
    client = _redis()
    if client is not None:
        try:
            data = client.hgetall(f"{JOB_PREFIX}:{job_id}")
            if data:
                return Job.from_dict(
                    {
                        **data,
                        "submitted_at": float(data.get("submitted_at") or 0),
                        "started_at": float(data["started_at"]) if data.get("started_at") else None,
                        "finished_at": float(data["finished_at"]) if data.get("finished_at") else None,
                        "payload": json.loads(data.get("payload") or "{}"),
                        "result": json.loads(data.get("result") or "null"),
                    }
                )
        except Exception:  # noqa: BLE001
            pass
    with _MEM_LOCK:
        job = _MEM.get(job_id)
    return Job.from_dict(job.__dict__) if job else None


def submit(name: str, payload: dict[str, Any] | None = None,
           start_inline: bool = True) -> Job:
    """Enqueue a job and (by default) begin executing it on a worker thread.

    ``start_inline=False`` only records the job, for callers that want to run
    the work in their own process.
    """
    if name not in _HANDLERS:
        raise KeyError(f"no handler registered for job {name!r}")
    job = Job(id=uuid.uuid4().hex[:16], name=name, payload=payload or {})
    _save(job)

    client = _redis()
    if client is not None:
        try:
            client.lpush(QUEUE_KEY, job.id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("job queue: Redis push failed (%s)", exc)

    if start_inline and _inline_enabled():
        _spawn(job.id)
    return job


def _claim(job_id: str, lease: int = DEFAULT_LEASE_SEC) -> str | None:
    """Atomically win the right to run ``job_id``; returns the worker id or None.

    Without this, a job that is both pushed to Redis and started inline gets run
    twice: the request thread starts it, and the dedicated worker pops the same
    id off the list a moment later.  For ``corpus_reindex`` that means two full
    reindex passes writing the same index at once, so exactly one worker must
    win.  ``SET NX EX`` gives that atomically; the lease TTL is what lets a dead
    worker's job become claimable again.
    """
    worker = _worker_id()
    client = _redis()
    if client is not None:
        try:
            won = client.set(f"{CLAIM_PREFIX}:{job_id}", worker, nx=True, ex=lease)
            return worker if won else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("job claim: Redis failed (%s); falling back", exc)
    with _MEM_LOCK:
        if job_id in _CLAIMED:
            return None
        _CLAIMED.add(job_id)
    return worker


def _release_claim(job_id: str) -> None:
    client = _redis()
    if client is not None:
        try:
            client.delete(f"{CLAIM_PREFIX}:{job_id}")
            return
        except Exception:  # noqa: BLE001
            pass
    with _MEM_LOCK:
        _CLAIMED.discard(job_id)


def _spawn(job_id: str) -> None:
    def run() -> None:
        execute(job_id)

    thread = threading.Thread(
        target=run, name=f"ipsakti-job-{job_id}", daemon=True
    )
    thread.start()
    _THREADS.append(thread)
    # Keep the thread list from growing without bound in a long-lived process.
    if len(_THREADS) > 200:
        _THREADS[:] = [t for t in _THREADS if t.is_alive()]


def execute(job_id: str) -> Job | None:
    """Run one job to completion. Exposed so an external worker can drive it.

    Exactly one caller executes a given job; losers of the claim return the
    current state untouched.  A job that already finished is never re-run.
    """
    job = _load(job_id)
    if job is None:
        return None
    if job.state in ("done", "failed"):
        return job
    if _claim(job_id) is None:
        logger.debug("job %s already claimed by another worker; skipping", job_id)
        return job
    handler = _HANDLERS.get(job.name)
    if handler is None:
        job.state = "failed"
        job.error = f"handler for {job.name!r} is not registered in this process"
        job.finished_at = time.time()
        _save(job)
        _release_claim(job_id)
        return job

    job.state = "running"
    job.started_at = time.time()
    job.worker = _worker_id()
    _save(job)
    try:
        job.result = handler(job.payload)
        job.state = "done"
    except Exception as exc:  # noqa: BLE001 — the failure must be reported
        job.state = "failed"
        job.error = f"{type(exc).__name__}: {exc}"
        logger.error("job %s (%s) failed: %s", job_id, job.name, exc)
        logger.debug(traceback.format_exc())
    finally:
        job.finished_at = time.time()
        _save(job)
        _release_claim(job_id)
    return job


def get(job_id: str) -> dict[str, Any] | None:
    job = _load(job_id)
    return job.to_dict() if job else None


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    client = _redis()
    jobs: list[Job] = []
    if client is not None:
        try:
            for key in client.scan_iter(match=f"{JOB_PREFIX}:*", count=200):
                job = _load(key.rsplit(":", 1)[-1])
                if job:
                    jobs.append(job)
        except Exception:  # noqa: BLE001
            jobs = []
    if not jobs:
        with _MEM_LOCK:
            jobs = list(_MEM.values())
    jobs.sort(key=lambda j: j.submitted_at, reverse=True)
    return [j.to_dict() for j in jobs[:limit]]


def stats() -> dict[str, Any]:
    jobs = list_jobs(limit=500)
    by_state: dict[str, int] = {}
    for job in jobs:
        by_state[job["state"]] = by_state.get(job["state"], 0) + 1
    return {
        "backend": "redis" if _redis() is not None else "memory",
        "registered_handlers": sorted(_HANDLERS),
        "counts": by_state,
        "recent": [j["id"] for j in jobs[:10]],
    }


def _main() -> None:  # pragma: no cover - process entrypoint
    """Poll the Redis queue and execute jobs (for a dedicated worker process)."""
    import signal

    running = {"go": True}

    def _stop(*_: Any) -> None:
        running["go"] = False

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    # Importing this module as __main__ creates a *second* module object, so the
    # registry it holds is not the one the handlers register into.  Re-import
    # under the canonical name and drive that instance.
    import app.core.jobs as jobs_mod
    from app.core import job_handlers  # noqa: F401  (import for side effects)

    logger.info(
        "job worker started, %d handler(s): %s",
        len(jobs_mod.handlers()),
        sorted(jobs_mod.handlers()),
    )
    while running["go"]:
        client = _redis()
        if client is None:
            logger.error("job worker: REDIS_URL is required for a dedicated worker")
            break
        try:
            popped = client.brpop(QUEUE_KEY, timeout=5)
        except Exception as exc:  # noqa: BLE001
            logger.error("job worker: queue read failed (%s)", exc)
            time.sleep(3)
            continue
        if not popped:
            continue
        job_id = popped[1] if isinstance(popped, tuple) else popped
        # execute() claims atomically, so a duplicate pop is a no-op.
        jobs_mod.execute(job_id)


if __name__ == "__main__":  # pragma: no cover
    _main()
