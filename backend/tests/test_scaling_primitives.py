"""Tests for the S1-S4 scaling primitives: shared cache, single-writer lock, job queue."""

from __future__ import annotations

import json
import os
import threading
import time

import numpy as np
import pytest

from app.core.cache import SharedCache, get_cache, invalidate_prefix
from app.core.lock import single_writer
from app.core.jobs import get as get_job
from app.core.jobs import list_jobs, register, stats, submit


# --------------------------------------------------------------------------- #
# S1  SharedCache
# --------------------------------------------------------------------------- #
def test_cache_roundtrip_and_ttl_zero_is_shared_backend():
    """ttl=0 must still write to Redis - that is how invalidation counters work."""
    cache = get_cache("test_generation_counter", default_ttl=0)
    cache.set("gen", 7)
    assert cache.get("gen") == 7
    assert "gen" in cache
    assert cache.invalidate_prefix("gen") >= 1
    assert cache.get("gen") is None


def test_cache_does_not_serve_expired_entries():
    cache = get_cache("test_ttl", default_ttl=0.05)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    time.sleep(0.15)
    assert cache.get("k") is None


def test_cache_memory_is_bounded():
    cache = SharedCache("test_bound", max_memory_entries=3)
    for i in range(10):
        cache.set(f"k{i}", i)
    assert len(cache._mem) <= 3


def test_cache_roundtrips_numpy_vectors_as_numbers():
    """A NumPy array must not degrade to its repr string on the Redis path."""
    import numpy as np

    cache = SharedCache("test_vector")
    vec = np.array([0.1, 0.2, 0.3], dtype="float32")
    encoded = SharedCache._encode(vec)
    assert json.loads(encoded) == pytest.approx([0.1, 0.2, 0.3])
    cache.set("v", vec)
    loaded = cache.get("v")
    assert isinstance(loaded, list), "both backends must return the same shape"
    assert loaded == pytest.approx([0.1, 0.2, 0.3], rel=1e-6)
    # A cosine over the round-tripped value must not blow up on a string.
    assert sum(float(x) * float(x) for x in loaded) > 0


def test_cache_preserves_nested_structures():
    cache = SharedCache("test_nested")
    payload = {"vectors": [np.array([1.0, 2.0])], "meta": {"n": 2, "ok": True}}
    cache.set("p", payload)
    out = cache.get("p")
    assert out["meta"] == {"n": 2, "ok": True}
    assert out["vectors"][0] == pytest.approx([1.0, 2.0])


def test_cache_backends_agree_on_shape():
    """Memory and Redis paths must be observationally identical."""
    import numpy as np

    cache = SharedCache("test_parity")
    cache.set("arr", np.array([1, 2, 3]))
    cache.set("obj", {"a": (1, 2)})
    cache.set("scalar", 5)
    assert cache.get("arr") == [1, 2, 3]
    assert cache.get("obj") == {"a": [1, 2]}
    assert cache.get("scalar") == 5
    assert json.loads(SharedCache._encode(cache.get("arr"))) == [1, 2, 3]


# --------------------------------------------------------------------------- #
# S2  single_writer
# --------------------------------------------------------------------------- #
def test_lock_is_exclusive_then_released():
    with single_writer("test_lock_a", ttl=30) as first:
        assert first is True
        with single_writer("test_lock_a", ttl=30) as second:
            assert second is False, "a second holder must be refused"
    with single_writer("test_lock_a", ttl=30) as third:
        assert third is True, "lock must be reusable after release"


def test_lock_excludes_across_threads():
    outcome: list[bool] = []

    def _attempt() -> None:
        with single_writer("test_lock_b", ttl=30) as got:
            outcome.append(bool(got))

    with single_writer("test_lock_b", ttl=30):
        t = threading.Thread(target=_attempt)
        t.start()
        t.join(5)
        assert outcome == [False], "lock must be exclusive across threads"
    with single_writer("test_lock_b", ttl=30) as again:
        assert again is True, "released lock must be grantable"


def test_lock_expires_so_a_dead_replica_cannot_wedge_ingestion():
    with single_writer("test_lock_c", ttl=1):
        pass
    time.sleep(1.4)
    with single_writer("test_lock_c", ttl=5) as after:
        assert after is True, "TTL must release a lock held by a dead replica"


# --------------------------------------------------------------------------- #
# S4  job queue
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True, scope="module")
def _handlers():
    from app.core import job_handlers  # noqa: F401

    yield


def test_registered_handlers_cover_the_heavy_operations():
    expected = {
        "corpus_reindex", "indiacode_harvest", "patent_corpus_harvest",
        "law_sentinel_run", "ingestion_cycle", "dossier_export",
    }
    from app.core.jobs import handlers

    assert expected <= set(handlers())


def test_job_runs_to_completion_off_the_request_path():
    @register("t_success")
    def _ok(payload):
        return {"doubled": payload["n"] * 2}

    job = submit("t_success", {"n": 21})
    for _ in range(100):
        state = get_job(job.id)
        if state["state"] in ("done", "failed"):
            break
        time.sleep(0.05)
    assert state["state"] == "done", state
    assert state["result"] == {"doubled": 42}
    assert state["elapsed_sec"] >= 0


def test_job_failure_is_captured_not_swallowed():
    @register("t_boom")
    def _boom(payload):
        raise ValueError("intentional")

    job = submit("t_boom")
    for _ in range(100):
        state = get_job(job.id)
        if state["state"] in ("done", "failed"):
            break
        time.sleep(0.05)
    assert state["state"] == "failed"
    assert "intentional" in state["error"]


def test_unknown_job_name_is_refused_loudly():
    with pytest.raises(KeyError):
        submit("definitely_not_registered")


def test_jobs_are_listable_and_counted():
    submit("t_success", {"n": 1})
    ids = [j["id"] for j in list_jobs(limit=10)]
    assert ids
    counts = stats()["counts"]
    assert sum(counts.values()) >= 1


# --------------------------------------------------------------------------- #
# S4  exactly-once claim
# --------------------------------------------------------------------------- #
def test_claim_is_exclusive():
    from app.core import jobs

    first = jobs._claim("claim_probe_job")
    assert first, "first claimer must win"
    assert jobs._claim("claim_probe_job") is None, "second claimer must lose"
    jobs._release_claim("claim_probe_job")
    assert jobs._claim("claim_probe_job"), "claim must be reusable after release"


def test_claim_is_exclusive_across_threads():
    from app.core import jobs

    winners: list[str | None] = []
    barrier = threading.Barrier(6)

    def _race() -> None:
        barrier.wait(5)
        winners.append(jobs._claim("claim_race_job"))

    threads = [threading.Thread(target=_race) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert len(winners) == 6
    assert sum(w is not None for w in winners) == 1, (
        f"exactly one worker may claim, got {winners}"
    )


def test_handler_runs_exactly_once_under_concurrent_execute():
    """The inline thread and a worker popping the same id must not double-run."""
    from app.core import jobs

    calls: list[int] = []

    @register("t_once")
    def _once(payload):
        calls.append(1)
        time.sleep(0.3)  # widen the window a duplicate would land in
        return {"ok": True}

    job = jobs.Job(id="once_probe", name="t_once", payload={})
    jobs._save(job)

    racers = [threading.Thread(target=jobs.execute, args=("once_probe",))
              for _ in range(4)]
    for t in racers:
        t.start()
    for t in racers:
        t.join(15)

    assert len(calls) == 1, f"handler ran {len(calls)} times, expected exactly 1"
    assert jobs.get("once_probe")["state"] == "done"


def test_finished_job_is_not_re_executed():
    from app.core import jobs

    calls: list[int] = []

    @register("t_twice")
    def _twice(payload):
        calls.append(1)
        return 1

    first = submit("t_twice")
    for _ in range(100):
        if get_job(first.id)["state"] in ("done", "failed"):
            break
        time.sleep(0.05)
    jobs.execute(first.id)
    jobs.execute(first.id)
    assert len(calls) == 1, "a completed job must be idempotent on re-execute"


def test_inline_execution_can_be_disabled_for_dedicated_workers():
    from app.core import jobs

    os.environ["IPSAKTI_INLINE_JOBS"] = "0"
    try:
        assert jobs._inline_enabled() is False
        job = jobs.submit("t_success", {"n": 5})
        time.sleep(0.4)
        assert get_job(job.id)["state"] == "queued", (
            "job must stay queued for the dedicated worker to pick up"
        )
        jobs.execute(job.id)
        assert get_job(job.id)["state"] == "done"
    finally:
        os.environ.pop("IPSAKTI_INLINE_JOBS", None)
    assert jobs._inline_enabled() is True


# --------------------------------------------------------------------------- #
# S4  job endpoints must not be an unauthenticated DoS lever
# --------------------------------------------------------------------------- #
def test_every_job_endpoint_declares_authentication():
    from app.main import app

    spec = app.openapi()
    paths = {p: ops for p, ops in spec["paths"].items() if "/jobs" in p}
    assert len(paths) == 4, f"unexpected job path count: {sorted(paths)}"
    for path, ops in paths.items():
        for method, op in ops.items():
            assert op.get("security"), f"{method.upper()} {path} is unauthenticated"


def test_job_endpoints_reject_anonymous_callers():
    """The real check: an anonymous POST must not be able to trigger a reindex."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    assert client.post("/api/v1/jobs", json={"name": "corpus_reindex"}).status_code in (
        401, 403,
    )
    for path in ("/api/v1/jobs", "/api/v1/jobs/stats", "/api/v1/jobs/handlers"):
        assert client.get(path).status_code in (401, 403), path
    assert client.get("/api/v1/jobs/does-not-exist").status_code in (401, 403)


def test_job_submit_is_not_in_the_unauthenticated_surface():
    """Regression guard: the registry snapshot must keep POST /jobs secured."""
    from tests.test_api_router_registry import EXPECTED_SECURED_OPERATIONS

    for entry in (("POST", "/api/v1/jobs"), ("GET", "/api/v1/jobs"),
                  ("GET", "/api/v1/jobs/stats"), ("GET", "/api/v1/jobs/handlers"),
                  ("GET", "/api/v1/jobs/{job_id}")):
        assert entry in EXPECTED_SECURED_OPERATIONS, entry
