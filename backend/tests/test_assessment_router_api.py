import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolate_passport_store():
    from app.services.passport_engine import PassportEngine

    PassportEngine._passports_store.clear()
    yield
    PassportEngine._passports_store.clear()


def test_assessment_evaluate_returns_findings(api_client, test_passport):
    response = api_client.post(
        "/api/v1/assessment/evaluate",
        json={"passport_id": test_passport.id, "target_markets": ["India"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assessment_id"]
    assert body["passport_id"] == test_passport.id
    assert isinstance(body["findings"], list)
    assert len(body["findings"]) > 0


def test_assessment_evaluate_unknown_passport_returns_404(api_client):
    response = api_client.post(
        "/api/v1/assessment/evaluate", json={"passport_id": "does-not-exist"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


def test_assessment_evaluate_audits_citations(api_client, test_passport):
    body = api_client.post(
        "/api/v1/assessment/evaluate",
        json={"passport_id": test_passport.id, "target_markets": ["India"]},
    ).json()
    assert "unsupported_claim_rate" in body
    ucr = body["unsupported_claim_rate"]
    assert 0.0 <= ucr <= 1.0


def test_assessment_evaluate_sets_timestamp(api_client, test_passport):
    body = api_client.post(
        "/api/v1/assessment/evaluate",
        json={"passport_id": test_passport.id, "target_markets": ["India"]},
    ).json()
    assert "T" in body["timestamp"]
    assert body["timestamp"].endswith("Z")


def test_assessment_evaluate_respects_language_parameter(api_client, test_passport):
    body = api_client.post(
        "/api/v1/assessment/evaluate",
        json={"passport_id": test_passport.id, "target_markets": ["India"], "language": "hi"},
    ).json()
    assert body["language"] == "hi"


def test_assessment_evaluate_filters_by_target_markets(api_client, test_passport):
    india = api_client.post(
        "/api/v1/assessment/evaluate",
        json={"passport_id": test_passport.id, "target_markets": ["India"]},
    ).json()
    us = api_client.post(
        "/api/v1/assessment/evaluate",
        json={"passport_id": test_passport.id, "target_markets": ["United States"]},
    ).json()
    india_jurisdictions = {f["jurisdiction"] for f in india["findings"]}
    us_jurisdictions = {f["jurisdiction"] for f in us["findings"]}
    assert "India" in india_jurisdictions
    assert "United States" in us_jurisdictions or not us["findings"]


def test_assessment_evaluate_missing_passport_id_returns_422(api_client):
    response = api_client.post("/api/v1/assessment/evaluate", json={"target_markets": []})
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="coverage_meter_score is hardcoded to 82 regardless of actual evidence coverage",
    strict=False,
)
def test_assessment_coverage_score_is_not_hardcoded(api_client, test_passport):
    body = api_client.post(
        "/api/v1/assessment/evaluate",
        json={"passport_id": test_passport.id, "target_markets": ["India"]},
    ).json()
    assert body["coverage_meter_score"] != 82


def test_assessment_evaluate_requires_no_authentication(api_client, test_passport):
    response = api_client.post(
        "/api/v1/assessment/evaluate",
        json={"passport_id": test_passport.id, "target_markets": ["India"]},
    )
    assert response.status_code == 200


@pytest.mark.xfail(
    reason="assessment evaluate has no ownership check; any caller can evaluate another user's passport",
    strict=False,
)
def test_assessment_evaluate_enforces_ownership(
    api_client, test_passport, other_auth_headers
):
    response = api_client.post(
        "/api/v1/assessment/evaluate",
        json={"passport_id": test_passport.id, "target_markets": ["India"]},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


def test_provenance_for_known_passport(api_client, test_passport):
    response = api_client.get(
        f"/api/v1/assessment/{test_passport.id}/provenance"
    )
    assert response.status_code == 200
    body = response.json()
    assert "nodes" in body or "edges" in body


def test_provenance_unknown_passport_returns_404(api_client):
    response = api_client.get("/api/v1/assessment/does-not-exist/provenance")
    assert response.status_code == 404


def test_provenance_respects_jurisdiction_parameter(api_client, test_passport):
    response = api_client.get(
        f"/api/v1/assessment/{test_passport.id}/provenance?jurisdiction=India"
    )
    assert response.status_code == 200


@pytest.mark.xfail(
    reason="provenance endpoint has no ownership check",
    strict=False,
)
def test_provenance_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.get(
        f"/api/v1/assessment/{test_passport.id}/provenance",
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


def test_provenance_returns_404_when_no_finding_for_jurisdiction(
    api_client, test_passport
):
    response = api_client.get(
        f"/api/v1/assessment/{test_passport.id}/provenance?jurisdiction=Atlantis"
    )
    assert response.status_code == 404
