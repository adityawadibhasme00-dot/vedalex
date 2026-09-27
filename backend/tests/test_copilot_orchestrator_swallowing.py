from unittest.mock import patch

import pytest

from app.rag.retrieval_pipeline import HybridRetriever
from app.services.copilot_orchestrator import AICopilotOrchestrator as Orchestrator

pytestmark = pytest.mark.integration

QUESTION = "What are the patent requirements for Ashwagandha formulation in India?"


def _boom(*_args, **_kwargs):
    raise RuntimeError("retrieval backend down")


@pytest.fixture(scope="module")
def failed_retrieval_result():
    with patch.object(Orchestrator, "_get_fallback_sources", classmethod(lambda cls, q: [])), \
            patch.object(HybridRetriever, "retrieve", _boom):
        yield Orchestrator.run(QUESTION)


def test_returns_dict_when_retrieval_fails(failed_retrieval_result):
    result = failed_retrieval_result
    assert isinstance(result, dict)
    assert "answer" in result
    assert "confidence" in result


def test_refuses_to_answer_when_retrieval_fails(failed_retrieval_result):
    result = failed_retrieval_result
    assert "No verified information found" in result["answer"]
    assert result["confidence"] < 0.2


def test_no_sources_cited_when_retrieval_failed(failed_retrieval_result):
    result = failed_retrieval_result
    assert result["sources"] == []
    assert not (result.get("verification") or {}).get("citations")


@pytest.mark.xfail(
    reason="orchestrator swallows the HybridRetriever exception (bare except at "
           "copilot_orchestrator.py:1023) and returns a normal answer dict with "
           "no error/retrieval_error signal for the caller",
    strict=False,
)
def test_surfaces_retrieval_failure_to_caller(failed_retrieval_result):
    result = failed_retrieval_result
    assert result.get("error") or result.get("retrieval_error")


@pytest.mark.xfail(
    reason="decision trace records the static retrieval pipeline description "
           "but never records that retrieval raised/failed",
    strict=False,
)
def test_decision_trace_records_retrieval_failure(failed_retrieval_result):
    trace = str(failed_retrieval_result.get("decision_trace", {}))
    assert "error" in trace.lower() or "fail" in trace.lower()
