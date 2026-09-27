import pytest

pytestmark = pytest.mark.security


def test_institutional_cohort_analytics_returns_dashboard(api_client):
    response = api_client.get("/api/v1/institutional/cohort-analytics")
    assert response.status_code == 200
    body = response.json()
    assert body["organization_name"]
    assert isinstance(body["cases"], list)


def test_institutional_dashboard_includes_metrics(api_client):
    body = api_client.get("/api/v1/institutional/cohort-analytics").json()
    assert isinstance(body["total_active_cases"], int)
    assert isinstance(body["pending_expert_reviews"], int)
    assert 0 <= body["avg_coverage_meter"] <= 100


@pytest.mark.xfail(
    reason="institutional dashboard exposes cohort and case metrics with no authentication",
    strict=False,
)
def test_institutional_dashboard_requires_authentication(api_client):
    response = api_client.get("/api/v1/institutional/cohort-analytics")
    assert response.status_code in (401, 403)


def test_evals_retrieval_metrics_returns_metrics(api_client, monkeypatch):
    from app.api.v1 import evals_router

    captured = {}

    def fake_run_evaluation(limit=None):
        captured["limit"] = limit
        return {
            "generated_at": "2026-01-01T00:00:00",
            "aggregate": {"total_queries": 1, "avg_recall@5": 0.75},
        }

    monkeypatch.setattr(evals_router, "run_evaluation", fake_run_evaluation)
    response = api_client.get("/api/v1/evals/retrieval-metrics")
    assert response.status_code == 200
    assert "aggregate" in response.json()
    assert captured["limit"] is None


def test_evals_retrieval_metrics_respects_limit(api_client, monkeypatch):
    from app.api.v1 import evals_router

    captured = {}

    def fake_run_evaluation(limit=None):
        captured["limit"] = limit
        return {"aggregate": {"total_queries": limit or 0}}

    monkeypatch.setattr(evals_router, "run_evaluation", fake_run_evaluation)
    response = api_client.get("/api/v1/evals/retrieval-metrics?limit=2")
    assert response.status_code == 200
    assert captured["limit"] == 2


def test_evals_run_benchmark_returns_results(api_client, monkeypatch):
    from app.api.v1 import evals_router

    monkeypatch.setattr(
        evals_router.BenchmarkRunner,
        "run_benchmark",
        classmethod(lambda cls: {"status": "ok", "results": []}),
    )
    response = api_client.post("/api/v1/evals/run-benchmark")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


@pytest.mark.xfail(
    reason="benchmark and metrics endpoints are operational tooling but have no authentication",
    strict=False,
)
def test_evals_endpoints_require_authentication(api_client, monkeypatch):
    from app.api.v1 import evals_router

    monkeypatch.setattr(
        evals_router,
        "run_evaluation",
        lambda limit=None: {"aggregate": {}},
    )
    response = api_client.get("/api/v1/evals/retrieval-metrics")
    assert response.status_code in (401, 403)
