import pytest

from app.services.passport_engine import PassportEngine

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolate_passport_store():
    PassportEngine._passports_store.clear()
    yield
    PassportEngine._passports_store.clear()


def test_what_if_returns_simulation_document(api_client, test_passport):
    mutated = ["Supports restful sleep"]
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={"passport_id": test_passport.id, "mutated_claims": mutated},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["original_claims"] == test_passport.proposed_claims
    assert body["mutated_claims"] == mutated
    assert isinstance(body["affected_nodes_count"], int)
    assert isinstance(body["diffs"], list)
    for diff in body["diffs"]:
        assert diff["jurisdiction"]
        assert diff["prior_classification"]
        assert diff["new_classification"]
        assert diff["impact_severity"]
        assert diff["risk_alert"]
        assert isinstance(diff["removed_requirements"], list)
        assert isinstance(diff["new_requirements"], list)


def test_what_if_disease_claim_triggers_critical_diff(api_client, test_passport):
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={
            "passport_id": test_passport.id,
            "mutated_claims": ["Treats chronic insomnia and reverses anxiety disorders"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["affected_nodes_count"] >= 2
    us = next(d for d in body["diffs"] if d["jurisdiction"] == "United States")
    assert "Unapproved New Drug" in us["new_classification"]
    assert us["impact_severity"] == "CRITICAL_BURDEN_INCREASE"
    assert any("Investigational New Drug" in r for r in us["new_requirements"])
    india = next(d for d in body["diffs"] if d["jurisdiction"] == "India")
    assert any("AYUSH" in r for r in india["new_requirements"])


def test_what_if_is_deterministic(api_client, test_passport):
    payload = {
        "passport_id": test_passport.id,
        "mutated_claims": ["Treats chronic insomnia"],
    }
    first = api_client.post("/api/v1/what-if/simulate", json=payload).json()
    second = api_client.post("/api/v1/what-if/simulate", json=payload).json()
    assert first == second


def test_what_if_does_not_mutate_stored_passport(api_client, test_passport):
    before_passport = PassportEngine.get_passport(test_passport.id)
    assert before_passport is not None
    before = list(before_passport.proposed_claims)
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={
            "passport_id": test_passport.id,
            "mutated_claims": ["Cures every disease instantly"],
        },
    )
    assert response.status_code == 200
    after_passport = PassportEngine.get_passport(test_passport.id)
    assert after_passport is not None
    after = list(after_passport.proposed_claims)
    assert after == before


def test_what_if_unknown_passport_returns_404(api_client):
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={"passport_id": "nope", "mutated_claims": ["x"]},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


def test_what_if_missing_mutated_claims_returns_422(api_client, test_passport):
    response = api_client.post(
        "/api/v1/what-if/simulate", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 422


def test_what_if_missing_passport_id_returns_422(api_client):
    response = api_client.post(
        "/api/v1/what-if/simulate", json={"mutated_claims": ["x"]}
    )
    assert response.status_code == 422


def test_what_if_rejects_non_list_mutated_claims(api_client, test_passport):
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={"passport_id": test_passport.id, "mutated_claims": "Supports sleep"},
    )
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="what_if_router.py:12 declares mutated_claims: List[str] with no max_length; arbitrarily large claim lists are accepted and each is evaluated twice by the deterministic rule engine",
    strict=False,
)
def test_what_if_rejects_oversized_mutated_claims(api_client, test_passport):
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={
            "passport_id": test_passport.id,
            "mutated_claims": [f"synthetic claim {index}" for index in range(1000)],
        },
    )
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="what_if_router.py:14-21 has no authentication dependency; simulations that echo the passport's original claims are served to anonymous callers",
    strict=False,
)
def test_what_if_requires_authentication(api_client, test_passport):
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={"passport_id": test_passport.id, "mutated_claims": ["x"]},
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="what_if_router.py:16-18 performs no ownership check; any caller can simulate against another user's passport and read back its original claims via original_claims",
    strict=False,
)
def test_what_if_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={"passport_id": test_passport.id, "mutated_claims": ["x"]},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)
