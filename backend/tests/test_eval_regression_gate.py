"""A5 — nightly eval regression gate over the 50-question labelled set.

The full harness costs ~4.6 minutes (retrieval warmup + 50 chain runs), so
the gate is opt-in for nightly CI/cron via ``IPSAKTI_EVAL_GATE=1``; it runs
the same thresholds as ``python tests/eval_harness.py --strict``.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.performance

_EVAL_GATE = os.environ.get("IPSAKTI_EVAL_GATE", "0").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


@pytest.mark.skipif(
    not _EVAL_GATE,
    reason="nightly gate: set IPSAKTI_EVAL_GATE=1 to run the 50-question eval",
)
def test_eval_regression_gate_meets_all_thresholds():
    from tests.eval_harness import run_eval

    report = run_eval()
    assert report["below_threshold"] == {}, (
        f"eval below threshold: {report['below_threshold']}"
    )
    metrics = report["metrics"]
    assert metrics["questions"] == 50
    assert metrics["passed"] == 50
    assert metrics["routing_accuracy"] == 1.0
    assert metrics["jurisdiction_accuracy"] == 1.0
    assert metrics["abstention_accuracy"] == 1.0
