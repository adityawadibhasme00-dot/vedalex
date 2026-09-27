import pytest

from app.services.passport_engine import PassportEngine

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolate_passport_store():
    PassportEngine._passports_store.clear()
    yield
    PassportEngine._passports_store.clear()


# --------------------------------------------------------------------------
# Regulatory roadmap
# --------------------------------------------------------------------------

def test_roadmap_returns_phases(api_client, test_passport):
    response = api_client.get(f"/api/v1/roadmap/{test_passport.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    assert body["total_phases"] == len(body["phases"]) == 6
    assert body["current_phase"] >= 1
    assert body["estimated_completion"]
    assert body["next_action"]
    for phase in body["phases"]:
        assert phase["phase"]
        assert phase["title"]
        assert phase["status"] in ("completed", "in_progress", "pending", "not_started")


def test_roadmap_unknown_passport_returns_404(api_client):
    response = api_client.get("/api/v1/roadmap/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


@pytest.mark.xfail(
    reason="roadmap is fully hardcoded (current_phase=4, fixed statuses); ignores actual passport state",
    strict=False,
)
def test_roadmap_reflects_passport_state(api_client, test_passport):
    body = api_client.get(f"/api/v1/roadmap/{test_passport.id}").json()
    assert body["current_phase"] != 4 or any(
        p["status"] not in ("completed", "pending", "in_progress", "not_started")
        for p in body["phases"]
    )


@pytest.mark.xfail(
    reason="roadmap endpoint has no ownership check",
    strict=False,
)
def test_roadmap_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.get(
        f"/api/v1/roadmap/{test_passport.id}", headers=other_auth_headers
    )
    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------
# Patent readiness
# --------------------------------------------------------------------------

def test_patent_readiness_returns_result(api_client, test_passport):
    response = api_client.get(f"/api/v1/analysis/readiness/{test_passport.id}")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert body


def test_patent_readiness_unknown_passport_returns_404(api_client):
    response = api_client.get("/api/v1/analysis/readiness/does-not-exist")
    assert response.status_code == 404


@pytest.mark.xfail(
    reason="patent readiness endpoint has no ownership check",
    strict=False,
)
def test_patent_readiness_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.get(
        f"/api/v1/analysis/readiness/{test_passport.id}", headers=other_auth_headers
    )
    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------
# Freedom to operate
# --------------------------------------------------------------------------

def test_fto_check_returns_similar_patents(api_client, test_passport):
    response = api_client.post(
        "/api/v1/fto/check", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    assert isinstance(body["similar_patents"], list)
    assert len(body["similar_patents"]) > 0
    for patent in body["similar_patents"]:
        assert patent["patent_id"]
        assert 0 <= patent["overlap_percentage"] <= 100
        assert patent["risk_level"] in ("LOW", "MODERATE", "HIGH")
    assert body["overall_risk"] in ("LOW", "MODERATE", "HIGH")
    assert body["recommendation"]


def test_fto_unknown_passport_returns_404(api_client):
    response = api_client.post("/api/v1/fto/check", json={"passport_id": "nope"})
    assert response.status_code == 404


@pytest.mark.xfail(
    reason="similar_patents are hardcoded fixtures, identical for every passport",
    strict=False,
)
def test_fto_similar_patents_derive_from_passport(api_client, test_passport):
    first = api_client.post("/api/v1/fto/check", json={"passport_id": test_passport.id}).json()
    PassportEngine._passports_store.clear()
    other = PassportEngine.create_from_intake(
        raw_text="A completely different synthetic polymer coating formulation",
        user_lang="en",
        title="Polymer Coating",
        intake={"proposed_claims": ["Prevents corrosion"]},
    )
    second = api_client.post("/api/v1/fto/check", json={"passport_id": other.id}).json()
    assert [p["patent_id"] for p in first["similar_patents"]] != [
        p["patent_id"] for p in second["similar_patents"]
    ]


@pytest.mark.xfail(
    reason="fto check has no ownership check",
    strict=False,
)
def test_fto_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.post(
        "/api/v1/fto/check",
        json={"passport_id": test_passport.id},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------
# IP & TK screening
# --------------------------------------------------------------------------

def test_screening_ip_tk_returns_analysis(api_client, test_passport):
    response = api_client.post(
        "/api/v1/screening/ip-tk", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    assert body["formulation_fingerprint"]
    assert body["section_3p_analysis"]["statutory_basis"]
    assert "coverage_limitations" in body
    assert body["recommended_patentability_strategy"]


def test_screening_unknown_passport_returns_404(api_client):
    response = api_client.post("/api/v1/screening/ip-tk", json={"passport_id": "nope"})
    assert response.status_code == 404


def test_screening_missing_passport_id_returns_422(api_client):
    response = api_client.post("/api/v1/screening/ip-tk", json={})
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="screening has no ownership check",
    strict=False,
)
def test_screening_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.post(
        "/api/v1/screening/ip-tk",
        json={"passport_id": test_passport.id},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------
# Red-team challenge
# --------------------------------------------------------------------------

def test_red_team_challenge_returns_challenges(api_client, test_passport):
    response = api_client.post(
        "/api/v1/red-team/challenge", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert body


def test_red_team_unknown_passport_returns_404(api_client):
    response = api_client.post("/api/v1/red-team/challenge", json={"passport_id": "nope"})
    assert response.status_code == 404


def test_red_team_missing_passport_id_returns_422(api_client):
    response = api_client.post("/api/v1/red-team/challenge", json={})
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="red-team challenge has no ownership check",
    strict=False,
)
def test_red_team_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.post(
        "/api/v1/red-team/challenge",
        json={"passport_id": test_passport.id},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------
# What-if simulator
# --------------------------------------------------------------------------

def test_what_if_simulate_returns_response(api_client, test_passport):
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={"passport_id": test_passport.id, "mutated_claims": ["Supports sleep"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert body


def test_what_if_unknown_passport_returns_404(api_client):
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={"passport_id": "nope", "mutated_claims": ["x"]},
    )
    assert response.status_code == 404


def test_what_if_missing_mutated_claims_returns_422(api_client, test_passport):
    response = api_client.post(
        "/api/v1/what-if/simulate", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="what-if simulation has no ownership check",
    strict=False,
)
def test_what_if_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.post(
        "/api/v1/what-if/simulate",
        json={"passport_id": test_passport.id, "mutated_claims": ["x"]},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------
# White space navigator
# --------------------------------------------------------------------------

def test_whitespace_get_returns_analysis(api_client, test_passport):
    response = api_client.get(f"/api/v1/whitespace/{test_passport.id}")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_whitespace_unknown_passport_returns_4xx(api_client):
    response = api_client.get("/api/v1/whitespace/does-not-exist")
    assert response.status_code in (404, 500)
    if response.status_code == 500:
        pytest.xfail("whitespace returns 500 instead of 404 for unknown passport")


def test_whitespace_post_analyze_returns_analysis(api_client, test_passport):
    response = api_client.post(
        "/api/v1/whitespace/analyze", json={"passport_id": test_passport.id}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.xfail(
    reason="whitespace analysis has no ownership check",
    strict=False,
)
def test_whitespace_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.get(
        f"/api/v1/whitespace/{test_passport.id}", headers=other_auth_headers
    )
    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------
# Regulatory diff & alerts
# --------------------------------------------------------------------------

def test_regulatory_diff_updates_returns_list(api_client):
    response = api_client.get("/api/v1/regulatory-diff/updates")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_regulatory_diff_updates_filters_by_case(api_client):
    response = api_client.get("/api/v1/regulatory-diff/updates?case_id=unknown-case")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.xfail(
    reason="regulatory diff feed has no authentication; case ids are enumerable",
    strict=False,
)
def test_regulatory_diff_requires_authentication(api_client):
    response = api_client.get("/api/v1/regulatory-diff/updates?case_id=CASE-1")
    assert response.status_code in (401, 403)
