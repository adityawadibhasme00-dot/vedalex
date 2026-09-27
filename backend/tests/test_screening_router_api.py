import pytest

from app.services.passport_engine import PassportEngine

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolate_passport_store():
    PassportEngine._passports_store.clear()
    yield
    PassportEngine._passports_store.clear()


def test_screening_returns_fingerprint_and_statutory_analysis(api_client, test_passport):
    response = api_client.post(
        "/api/v1/screening/ip-tk", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    fingerprint = body["formulation_fingerprint"]
    assert fingerprint["fingerprint_hash"]
    assert isinstance(fingerprint["canonical_ingredient_ids"], list)
    assert isinstance(fingerprint["ratios"], dict)
    assert "Section 3(p)" in body["section_3p_analysis"]["statutory_basis"]
    assert isinstance(body["section_3p_analysis"]["statutory_citations"], list)
    assert isinstance(body["retrieved_prior_art_records"], list)
    assert body["coverage_limitations"]
    assert body["recommended_patentability_strategy"]


def test_screening_fingerprint_is_deterministic(api_client, test_passport):
    payload = {"passport_id": test_passport.id}
    first = api_client.post("/api/v1/screening/ip-tk", json=payload).json()
    second = api_client.post("/api/v1/screening/ip-tk", json=payload).json()
    assert (
        first["formulation_fingerprint"]["fingerprint_hash"]
        == second["formulation_fingerprint"]["fingerprint_hash"]
    )


def test_screening_unknown_passport_returns_404(api_client):
    response = api_client.post("/api/v1/screening/ip-tk", json={"passport_id": "nope"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


def test_screening_missing_passport_id_returns_422(api_client):
    response = api_client.post("/api/v1/screening/ip-tk", json={})
    assert response.status_code == 422


def test_screening_null_passport_id_returns_422(api_client):
    response = api_client.post("/api/v1/screening/ip-tk", json={"passport_id": None})
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="screening_router.py:41-45 returns a canned Section 3(p) verdict for every passport ('HIGH_SECTION_3P_EXPOSURE' plus a primary_reason asserting the components are 'established in classical Ayurvedic texts (Charaka Samhita)'), even for a synthetic polymer formulation with zero botanicals",
    strict=False,
)
def test_screening_analysis_is_derived_from_the_passport(api_client):
    passport = PassportEngine.create_from_intake(
        raw_text="Synthetic polymer anti-corrosion coating for industrial pipes",
        title="Polymer Coating",
        intake={"proposed_claims": ["Prevents corrosion on steel surfaces"]},
    )
    body = api_client.post(
        "/api/v1/screening/ip-tk", json={"passport_id": passport.id}
    ).json()
    analysis = body["section_3p_analysis"]
    assert analysis["statutory_risk_level"] != "HIGH_SECTION_3P_EXPOSURE"
    assert "Charaka" not in analysis["primary_reason"]


@pytest.mark.xfail(
    reason="screening_router.py:15-17 has no authentication dependency; IP/TK screening and prior-art records are served to anonymous callers",
    strict=False,
)
def test_screening_requires_authentication(api_client, test_passport):
    response = api_client.post(
        "/api/v1/screening/ip-tk", json={"passport_id": test_passport.id}
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="screening_router.py:15-19 performs no ownership check; any caller can screen another user's passport by id",
    strict=False,
)
def test_screening_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.post(
        "/api/v1/screening/ip-tk",
        json={"passport_id": test_passport.id},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


def test_characterization_screening_analysis_is_identical_for_unrelated_passports(
    api_client, test_passport
):
    other = PassportEngine.create_from_intake(
        raw_text="Synthetic polymer anti-corrosion coating for industrial pipes",
        title="Polymer Coating",
        intake={"proposed_claims": ["Prevents corrosion on steel surfaces"]},
    )
    first = api_client.post(
        "/api/v1/screening/ip-tk", json={"passport_id": test_passport.id}
    ).json()
    second = api_client.post(
        "/api/v1/screening/ip-tk", json={"passport_id": other.id}
    ).json()
    assert first["section_3p_analysis"] == second["section_3p_analysis"]
    assert first["retrieved_prior_art_records"] == second["retrieved_prior_art_records"]
