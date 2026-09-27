import pytest

pytestmark = pytest.mark.integration


def test_fto_check_returns_similar_patents(api_client, test_passport):
    response = api_client.post(
        "/api/v1/fto/check", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    patents = body["similar_patents"]
    assert len(patents) >= 1
    for patent in patents:
        assert patent["patent_id"]
        assert patent["title"]
        assert patent["jurisdiction"]
        assert patent["description"]
        assert 0 <= patent["overlap_percentage"] <= 100
        assert patent["risk_level"] in ("LOW", "MODERATE", "HIGH")
    assert body["overall_risk"] in ("LOW", "MODERATE", "HIGH")
    assert body["recommendation"]


@pytest.mark.xfail(
    reason="target_markets (fto_router.py:11) is accepted but never read; patents from unrequested jurisdictions are always returned",
    strict=False,
)
def test_fto_check_respects_requested_target_markets(api_client, test_passport):
    response = api_client.post(
        "/api/v1/fto/check",
        json={"passport_id": test_passport.id, "target_markets": ["India"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert {p["jurisdiction"] for p in body["similar_patents"]} <= {"India"}


def test_fto_check_unknown_passport_returns_404(api_client):
    response = api_client.post(
        "/api/v1/fto/check", json={"passport_id": "passport-that-does-not-exist"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


def test_fto_check_missing_passport_id_returns_422(api_client):
    response = api_client.post("/api/v1/fto/check", json={})
    assert response.status_code == 422


def test_fto_check_rejects_non_string_passport_id(api_client):
    response = api_client.post("/api/v1/fto/check", json={"passport_id": 123})
    assert response.status_code == 422


def test_fto_check_does_not_require_authentication(api_client, test_passport):
    response = api_client.post(
        "/api/v1/fto/check", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 200


@pytest.mark.xfail(
    reason="POST /fto/check (fto_router.py:27) takes no current-user dependency and never compares the passport owner; any caller holding an id can read the analysis",
    strict=False,
)
def test_fto_check_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.post(
        "/api/v1/fto/check",
        json={"passport_id": test_passport.id},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="POST /fto/check (fto_router.py:27) has no authentication requirement at all; anonymous callers can run FTO analysis for any passport id",
    strict=False,
)
def test_fto_check_requires_authentication(api_client, test_passport):
    response = api_client.post(
        "/api/v1/fto/check", json={"passport_id": test_passport.id}
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="similar_patents, overall_risk and recommendation are hardcoded (fto_router.py:38-70) and target_markets (fto_router.py:11) is never read, so requested markets change nothing",
    strict=False,
)
def test_fto_check_result_depends_on_target_markets(api_client, test_passport):
    india = api_client.post(
        "/api/v1/fto/check",
        json={"passport_id": test_passport.id, "target_markets": ["India"]},
    ).json()
    us = api_client.post(
        "/api/v1/fto/check",
        json={
            "passport_id": test_passport.id,
            "target_markets": ["United States"],
        },
    ).json()
    india_key = (
        india["overall_risk"],
        [p["patent_id"] for p in india["similar_patents"]],
    )
    us_key = (
        us["overall_risk"],
        [p["patent_id"] for p in us["similar_patents"]],
    )
    assert india_key != us_key


@pytest.mark.xfail(
    reason="statutory = HybridRetrievalEngine.search_passages(...) is computed and then discarded (fto_router.py:36); the FTO response carries no sources or citations",
    strict=False,
)
def test_fto_check_includes_grounding_sources(api_client, test_passport):
    response = api_client.post(
        "/api/v1/fto/check", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("sources") or body.get("statutory_basis")
