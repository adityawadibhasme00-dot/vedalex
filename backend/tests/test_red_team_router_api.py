import pytest

from app.services.passport_engine import PassportEngine

pytestmark = pytest.mark.integration

REQUIRED_OBJECTION_FIELDS = (
    "objection_id",
    "authority_simulated",
    "legal_basis",
    "objection_title",
    "summary",
    "investigable_action",
)


@pytest.fixture(autouse=True)
def _isolate_passport_store():
    PassportEngine._passports_store.clear()
    yield
    PassportEngine._passports_store.clear()


def _challenge(api_client, passport_id, headers=None):
    return api_client.post(
        "/api/v1/red-team/challenge",
        json={"passport_id": passport_id},
        headers=headers,
    )


def test_red_team_challenge_returns_structured_objections(
    api_client, test_passport
):
    response = _challenge(api_client, test_passport.id)
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    assert body["disclaimer"]
    objections = body["objections"]
    assert body["total_objections"] == len(objections)
    assert len(objections) >= 2
    for objection in objections:
        for field in REQUIRED_OBJECTION_FIELDS:
            assert objection[field]


def test_red_team_challenge_flags_classical_pair(api_client, test_passport):
    body = _challenge(api_client, test_passport.id).json()
    ids = [o["objection_id"] for o in body["objections"]]
    assert "OBJ-IPO-SEC3P-01" in ids
    assert "OBJ-USFDA-WARNING-02" in ids
    assert "OBJ-NBA-BDA-03" in ids
    assert body["total_objections"] == 3


def test_red_team_challenge_skips_section3p_for_unpaired_passport(
    api_client, db_session
):
    passport = PassportEngine.create_from_intake(
        raw_text="Neem and turmeric topical gel for external application",
        user_lang="en",
        title="Neem Gel",
        intake={"proposed_claims": ["supports skin"]},
    )
    body = _challenge(api_client, passport.id).json()
    ids = [o["objection_id"] for o in body["objections"]]
    assert "OBJ-IPO-SEC3P-01" not in ids
    assert len(body["objections"]) == 2
    assert body["total_objections"] == 2


def test_red_team_challenge_unknown_passport_returns_404(api_client):
    response = _challenge(api_client, "passport-that-does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


def test_red_team_challenge_missing_passport_id_returns_422(api_client):
    response = api_client.post("/api/v1/red-team/challenge", json={})
    assert response.status_code == 422


def test_red_team_challenge_rejects_non_string_passport_id(api_client):
    response = api_client.post(
        "/api/v1/red-team/challenge", json={"passport_id": 42}
    )
    assert response.status_code == 422


def test_red_team_challenge_does_not_require_authentication(
    api_client, test_passport
):
    response = _challenge(api_client, test_passport.id)
    assert response.status_code == 200


@pytest.mark.xfail(
    reason="POST /red-team/challenge (red_team_router.py:12) never resolves or compares the passport owner against the caller",
    strict=False,
)
def test_red_team_challenge_enforces_ownership(
    api_client, test_passport, other_auth_headers
):
    response = _challenge(api_client, test_passport.id, other_auth_headers)
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="POST /red-team/challenge (red_team_router.py:12) has no authentication requirement; objections for any passport id are readable anonymously",
    strict=False,
)
def test_red_team_challenge_requires_authentication(api_client, test_passport):
    response = _challenge(api_client, test_passport.id)
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="Section 3(p) objection is gated on the hardcoded pair ING-ASHWAGANDHA + ING-BRAHMI (red_team_module.py:16-17); other TK combinations never receive a 3(p) challenge",
    strict=False,
)
def test_red_team_challenge_flags_other_tk_combinations(api_client, db_session):
    passport = PassportEngine.create_from_intake(
        raw_text="Turmeric and neem extract capsule for immunity",
        user_lang="en",
        title="Turmeric Neem Capsule",
        intake={"proposed_claims": ["supports immunity"]},
    )
    body = _challenge(api_client, passport.id).json()
    ids = [o["objection_id"] for o in body["objections"]]
    assert "OBJ-IPO-SEC3P-01" in ids


@pytest.mark.xfail(
    reason="objection text is canned and independent of the passport's claims and ingredients (red_team_module.py:30-47); only the Section 3(p) objection is conditional",
    strict=False,
)
def test_red_team_challenge_objections_derive_from_passport(
    api_client, db_session
):
    first = PassportEngine.create_from_intake(
        raw_text="Neem and turmeric topical gel for external application",
        user_lang="en",
        title="Neem Gel",
        intake={"proposed_claims": ["supports skin barrier"]},
    )
    second = PassportEngine.create_from_intake(
        raw_text="Sarpagandha and Shatavari root powder capsule for vitality",
        user_lang="en",
        title="Root Powder Capsule",
        intake={"proposed_claims": ["supports energy"]},
    )
    first_body = _challenge(api_client, first.id).json()
    second_body = _challenge(api_client, second.id).json()
    first_summaries = [o["summary"] for o in first_body["objections"]]
    second_summaries = [o["summary"] for o in second_body["objections"]]
    assert first_summaries != second_summaries
