import pytest

from app.services.passport_engine import PassportEngine

pytestmark = pytest.mark.security


@pytest.fixture(autouse=True)
def _isolate_passport_store():
    PassportEngine._passports_store.clear()
    yield
    PassportEngine._passports_store.clear()


def test_retrieval_metrics_returns_report_document(api_client, monkeypatch):
    from app.api.v1 import evals_router

    captured = {}

    def fake_run_evaluation(limit=None):
        captured["limit"] = limit
        return {
            "generated_at": "2026-01-01T00:00:00",
            "framework": "test-framework",
            "aggregate": {"total_queries": 1, "avg_mrr": 0.5},
            "per_query": [],
        }

    monkeypatch.setattr(evals_router, "run_evaluation", fake_run_evaluation)
    response = api_client.get("/api/v1/evals/retrieval-metrics")
    assert response.status_code == 200
    body = response.json()
    assert "generated_at" in body
    assert "aggregate" in body
    assert isinstance(body["per_query"], list)
    assert captured["limit"] is None


def test_retrieval_metrics_forwards_limit(api_client, monkeypatch):
    from app.api.v1 import evals_router

    captured = {}

    def fake_run_evaluation(limit=None):
        captured["limit"] = limit
        return {"aggregate": {"total_queries": limit or 0}, "per_query": []}

    monkeypatch.setattr(evals_router, "run_evaluation", fake_run_evaluation)
    response = api_client.get("/api/v1/evals/retrieval-metrics?limit=3")
    assert response.status_code == 200
    assert captured["limit"] == 3
    assert response.json()["aggregate"]["total_queries"] == 3


def test_retrieval_metrics_rejects_non_integer_limit(api_client):
    response = api_client.get("/api/v1/evals/retrieval-metrics?limit=abc")
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="evals_router.py:13 declares limit: Optional[int] with no ge=1 constraint; a negative limit reaches run_evaluation(limit=-1), which silently drops only the last benchmark query (app/evals/retrieval_metrics.py:114-115) instead of returning 422",
    strict=False,
)
def test_retrieval_metrics_rejects_negative_limit(api_client, monkeypatch):
    from app.api.v1 import evals_router

    monkeypatch.setattr(
        evals_router, "run_evaluation", lambda limit=None: {"aggregate": {}, "per_query": []}
    )
    response = api_client.get("/api/v1/evals/retrieval-metrics?limit=-1")
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="evals_router.py:13 accepts limit=0; the `if limit:` check at app/evals/retrieval_metrics.py:114 treats 0 as 'unset' and evaluates the entire benchmark set instead of rejecting the input",
    strict=False,
)
def test_retrieval_metrics_rejects_zero_limit(api_client, monkeypatch):
    from app.api.v1 import evals_router

    monkeypatch.setattr(
        evals_router, "run_evaluation", lambda limit=None: {"aggregate": {}, "per_query": []}
    )
    response = api_client.get("/api/v1/evals/retrieval-metrics?limit=0")
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="GET /evals/retrieval-metrics has a write side effect: every unauthenticated call persists exports/retrieval_eval_report.json (app/evals/retrieval_metrics.py:165-168); a GET must be safe and idempotent",
    strict=False,
)
def test_retrieval_metrics_get_does_not_persist_report_file(api_client, monkeypatch, tmp_path):
    from app.evals import retrieval_metrics

    report_path = tmp_path / "retrieval_eval_report.json"
    monkeypatch.setattr(retrieval_metrics, "REPORT_PATH", str(report_path))
    monkeypatch.setattr(
        retrieval_metrics,
        "evaluate_one",
        lambda query, qrels, top_k=10: {
            "recall@5": 1.0,
            "recall@10": 1.0,
            "precision@5": 1.0,
            "precision@10": 1.0,
            "mrr": 1.0,
            "citation_accuracy": 1.0,
            "source_hit": True,
            "expected_source_hit": True,
        },
    )
    response = api_client.get("/api/v1/evals/retrieval-metrics?limit=1")
    assert response.status_code == 200
    assert not report_path.exists()


def test_run_benchmark_returns_release_gate_metrics(api_client, monkeypatch):
    from app.api.v1 import evals_router

    monkeypatch.setattr(
        evals_router.BenchmarkRunner,
        "run_benchmark",
        classmethod(
            lambda cls: {
                "total_benchmark_cases": 5,
                "overall_classification_accuracy": 80.0,
                "unsupported_claim_rate_ucr": 0.02,
                "ucr_gate_passed": True,
                "language_parity_gate": {"passed": True, "tolerance_threshold": 0.05},
                "ablation_summary": [],
            }
        ),
    )
    response = api_client.post("/api/v1/evals/run-benchmark")
    assert response.status_code == 200
    body = response.json()
    assert body["total_benchmark_cases"] == 5
    assert body["ucr_gate_passed"] is True
    assert body["language_parity_gate"]["passed"] is True
    assert isinstance(body["ablation_summary"], list)


def test_run_benchmark_does_not_swallow_runner_exceptions(api_client, monkeypatch):
    from app.api.v1 import evals_router

    def boom(cls):
        raise ValueError("gold cases unreadable")

    monkeypatch.setattr(evals_router.BenchmarkRunner, "run_benchmark", classmethod(boom))
    with pytest.raises(ValueError):
        api_client.post("/api/v1/evals/run-benchmark")


@pytest.mark.xfail(
    reason="evals_router.py:8-10 exposes POST /evals/run-benchmark with no authentication; unauthenticated callers can trigger the full benchmark run (unbounded compute, no rate limit)",
    strict=False,
)
def test_run_benchmark_requires_authentication(api_client, monkeypatch):
    from app.api.v1 import evals_router

    monkeypatch.setattr(
        evals_router.BenchmarkRunner,
        "run_benchmark",
        classmethod(lambda cls: {"status": "ok"}),
    )
    response = api_client.post("/api/v1/evals/run-benchmark")
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="evals_router.py:8-10 has no authentication and BenchmarkRunner.run_benchmark persists benchmark passports into the live application database through PassportEngine.create_from_intake (app/evals/benchmark_runner.py:36-40, app/services/passport_engine.py:154-156)",
    strict=False,
)
def test_run_benchmark_does_not_write_to_application_database(api_client):
    from app.core.database import SessionLocal
    from app.models.db_models import InnovationPassportDB

    def count_passports():
        db = SessionLocal()
        try:
            return db.query(InnovationPassportDB).count()
        finally:
            db.close()

    before = count_passports()
    response = api_client.post("/api/v1/evals/run-benchmark")
    assert response.status_code == 200
    assert count_passports() == before


@pytest.mark.xfail(
    reason="evals_router.py:12-15 exposes benchmark metrics with no authentication dependency",
    strict=False,
)
def test_retrieval_metrics_requires_authentication(api_client, monkeypatch):
    from app.api.v1 import evals_router

    monkeypatch.setattr(
        evals_router, "run_evaluation", lambda limit=None: {"aggregate": {}, "per_query": []}
    )
    response = api_client.get("/api/v1/evals/retrieval-metrics")
    assert response.status_code in (401, 403)
