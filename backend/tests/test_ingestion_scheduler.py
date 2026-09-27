"""Tests for ingestion scheduler hardening (per-source retry + health state)."""

import time
from typing import Any

from app.services import ingestion_scheduler as sched


def test_backoff_grows_exponentially_and_caps():
    base = sched._backoff_base()
    costs = [sched._attempt_cost(i) for i in (1, 2, 3, 5)]
    assert costs[0] == base
    assert costs[1] == base * 2
    assert costs[2] == base * 4
    assert costs[-1] == min(base * (2 ** 4), 2 * 3600)
    # cap must hold
    huge = sched._attempt_cost(20)
    assert huge == 2 * 3600


def test_source_on_cooldown_logic():
    assert sched._source_on_cooldown(0, 0) is False
    assert sched._source_on_cooldown(2, time.time() + 1000) is True
    assert sched._source_on_cooldown(2, time.time() - 1) is False


def test_scheduler_status_has_hardening_fields(monkeypatch):
    monkeypatch.setenv("IPSAKTI_INGESTION_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("IPSAKTI_INGESTION_BACKOFF_BASE", "120")
    status = sched.get_scheduler_status()
    assert status["max_attempts_per_source"] == 5
    assert status["backoff_base_sec"] == 120
    assert "source_health" in status
    assert "state_file" in status
    assert isinstance(status["cadence"]["daily"], int)


def test_health_state_roundtrip(monkeypatch):
    store: dict[str, Any] = {"scheduler": {"sources": {}}}
    monkeypatch.setattr(sched, "_load_state", lambda: store)
    monkeypatch.setattr(
        sched, "_save_state",
        lambda state: store.update({"scheduler": {"sources": state["scheduler"]["sources"]}}),
    )
    health = sched._read_health_state()
    health.setdefault("nba", {"failures": 0, "cooldown_until": 0})
    health["nba"]["failures"] = 1
    health["nba"]["cooldown_until"] = time.time() + 5000
    sched._write_health_state(health)
    reloaded = sched._read_health_state()
    assert reloaded["nba"]["failures"] == 1

    # and cooldown sees the persisted failure
    assert sched._source_on_cooldown(reloaded["nba"]["failures"], reloaded["nba"]["cooldown_until"]) is True


def test_max_attempts_parsing(monkeypatch):
    assert sched._max_attempts() >= 1
    monkeypatch.setenv("IPSAKTI_INGESTION_MAX_ATTEMPTS", "not-a-number")
    assert sched._max_attempts() == 3
    monkeypatch.setenv("IPSAKTI_INGESTION_MAX_ATTEMPTS", "0")
    assert sched._max_attempts() == 1