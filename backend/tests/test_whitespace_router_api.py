from datetime import datetime, timedelta

import pytest

from app.services.passport_engine import PassportEngine

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolate_passport_store():
    PassportEngine._passports_store.clear()
    yield
    PassportEngine._passports_store.clear()


def test_whitespace_get_returns_opportunity_analysis(api_client, test_passport):
    response = api_client.get(f"/api/v1/whitespace/{test_passport.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    assert body["case_title"]
    assert 0 <= body["overall_score"] <= 100
    assert body["status"] in (
        "Crowded",
        "Moderate",
        "Good Opportunity",
        "High Innovation Opportunity",
    )
    assert 0 <= body["tk_risk"] <= 100
    assert isinstance(body["dimensions"], list)
    assert len(body["dimensions"]) == 7
    assert len(body["heatmap"]["cells"]) == 25
    assert isinstance(body["cards"], list)
    assert len(body["cards"]) <= 3
    assert isinstance(body["recommendations"], list)
    assert body["filters"]["product_forms"]
    assert body["mutated"] is False


def test_whitespace_post_analyze_returns_analysis(api_client, test_passport):
    response = api_client.post(
        "/api/v1/whitespace/analyze", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    assert isinstance(body["overall_score"], int)
    assert body["mutated"] is False


def test_whitespace_post_analyze_with_mutation_returns_before_and_after(
    api_client, test_passport
):
    response = api_client.post(
        "/api/v1/whitespace/analyze",
        json={
            "passport_id": test_passport.id,
            "mutate": {"product_form": "Nano Liposomal Gel"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mutated"] is True
    assert "before" in body and "after" in body
    assert body["before"]["passport_id"] == test_passport.id
    assert body["after"]["passport_id"] == test_passport.id
    assert "overall_score" in body["before"]
    assert "overall_score" in body["after"]


def test_whitespace_unknown_passport_returns_404(api_client):
    response = api_client.get("/api/v1/whitespace/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


def test_whitespace_post_unknown_passport_returns_404(api_client):
    response = api_client.post(
        "/api/v1/whitespace/analyze", json={"passport_id": "does-not-exist"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


def test_whitespace_missing_passport_id_returns_422(api_client):
    response = api_client.post("/api/v1/whitespace/analyze", json={})
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="whitespace_router.py:17-25 has no authentication dependency; the full opportunity analysis of a passport is served to anonymous callers",
    strict=False,
)
def test_whitespace_requires_authentication(api_client, test_passport):
    response = api_client.get(f"/api/v1/whitespace/{test_passport.id}")
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="whitespace_router.py:17-21 performs no ownership check; any caller can read another user's opportunity analysis by passport id",
    strict=False,
)
def test_whitespace_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.get(
        f"/api/v1/whitespace/{test_passport.id}", headers=other_auth_headers
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="whitespace_router.py:25 and :36 interpolate the raw exception message into the 500 detail, leaking internal failure details (paths, driver strings, connection data) to the caller",
    strict=False,
)
def test_whitespace_internal_error_does_not_leak_exception_details(
    api_client, test_passport, monkeypatch
):
    from app.api.v1 import whitespace_router

    def boom(passport_id, db=None, mutate=None):
        raise RuntimeError("sqlite+pysqlite:///C:/Users/secret/app.db connection refused")

    monkeypatch.setattr(whitespace_router.WhitespaceNavigator, "analyze", boom)
    response = api_client.get(f"/api/v1/whitespace/{test_passport.id}")
    assert response.status_code == 500
    assert "secret" not in response.json()["detail"]


def test_whitespace_generated_at_is_utc_marked(api_client, test_passport):
    body = api_client.get(f"/api/v1/whitespace/{test_passport.id}").json()
    parsed = datetime.fromisoformat(body["generated_at"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)
