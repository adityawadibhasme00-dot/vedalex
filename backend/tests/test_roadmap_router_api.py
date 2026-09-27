import pytest

from app.services.passport_engine import PassportEngine

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolate_passport_store():
    PassportEngine._passports_store.clear()
    yield
    PassportEngine._passports_store.clear()


def test_roadmap_returns_six_phases(api_client, test_passport):
    response = api_client.get(f"/api/v1/roadmap/{test_passport.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    assert body["total_phases"] == len(body["phases"]) == 6
    assert 1 <= body["current_phase"] <= body["total_phases"]
    assert body["estimated_completion"]
    assert body["next_action"]


def test_roadmap_phases_carry_status_and_requirements(api_client, test_passport):
    body = api_client.get(f"/api/v1/roadmap/{test_passport.id}").json()
    for index, phase in enumerate(body["phases"], start=1):
        assert phase["phase"] == index
        assert phase["title"]
        assert phase["description"]
        assert phase["duration"]
        assert phase["status"] in ("completed", "in_progress", "pending", "not_started")
        assert isinstance(phase["requirements"], list)
        assert phase["requirements"]


def test_roadmap_unknown_passport_returns_404(api_client):
    response = api_client.get("/api/v1/roadmap/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


def test_roadmap_reads_passport_from_database_when_cache_is_cold(api_client, test_passport):
    PassportEngine._passports_store.clear()
    response = api_client.get(f"/api/v1/roadmap/{test_passport.id}")
    assert response.status_code == 200
    assert response.json()["passport_id"] == test_passport.id


@pytest.mark.xfail(
    reason="roadmap_router.py:64-73 hardcodes current_phase=4, fixed per-phase statuses, estimated_completion and next_action; a brand-new passport with unresolved clarifications is reported as already mid-way through Evidence Collection",
    strict=False,
)
def test_roadmap_reflects_actual_passport_state(api_client, test_passport):
    body = api_client.get(f"/api/v1/roadmap/{test_passport.id}").json()
    assert body["current_phase"] == 1
    assert all(phase["status"] != "completed" for phase in body["phases"])


@pytest.mark.xfail(
    reason="roadmap_router.py:7-11 has no authentication dependency; the regulatory roadmap is served to anonymous callers",
    strict=False,
)
def test_roadmap_requires_authentication(api_client, test_passport):
    response = api_client.get(f"/api/v1/roadmap/{test_passport.id}")
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="roadmap_router.py:7-11 performs no ownership check; any caller can read another user's passport roadmap by id",
    strict=False,
)
def test_roadmap_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.get(
        f"/api/v1/roadmap/{test_passport.id}", headers=other_auth_headers
    )
    assert response.status_code in (401, 403)


def test_characterization_roadmap_is_identical_for_unrelated_passports(api_client, test_passport):
    other = PassportEngine.create_from_intake(
        raw_text="Synthetic polymer anti-corrosion coating for industrial pipes",
        title="Polymer Coating",
        intake={"proposed_claims": ["Prevents corrosion on steel surfaces"]},
    )
    first = api_client.get(f"/api/v1/roadmap/{test_passport.id}").json()
    second = api_client.get(f"/api/v1/roadmap/{other.id}").json()
    assert first["phases"] == second["phases"]
    assert first["current_phase"] == second["current_phase"]
    assert first["estimated_completion"] == second["estimated_completion"]
    assert first["next_action"] == second["next_action"]
