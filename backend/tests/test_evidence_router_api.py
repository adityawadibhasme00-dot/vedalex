import pytest

from app.models.evidence import EvidenceLifecycle

pytestmark = pytest.mark.security

EVALUATED_STATUSES = {
    EvidenceLifecycle.UPLOADED,
    EvidenceLifecycle.NEEDS_REVIEW,
    EvidenceLifecycle.ACCEPTED,
}


@pytest.fixture(autouse=True)
def _isolate_evidence_store():
    from app.api.v1 import evidence_router

    evidence_router._evidence_store.clear()
    yield
    evidence_router._evidence_store.clear()


def test_evidence_gap_summary_is_seeded_for_any_passport_id(api_client):
    response = api_client.get("/api/v1/evidence/passport-abc")
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == "passport-abc"
    assert body["total_checks"] == 4
    assert len(body["items"]) == 4


def test_evidence_coverage_math_is_consistent(api_client):
    body = api_client.get("/api/v1/evidence/passport-math").json()
    evaluated = sum(
        1
        for item in body["items"]
        if EvidenceLifecycle(item["status"]) in EVALUATED_STATUSES
    )
    assert body["evaluated_checks"] == evaluated
    assert body["blocked_by_missing_sources"] == body["total_checks"] - evaluated
    assert body["coverage_meter_percentage"] == int(
        (evaluated / body["total_checks"]) * 100
    )


def test_seeded_evidence_carries_citations_and_next_actions(api_client):
    items = api_client.get("/api/v1/evidence/passport-detail").json()["items"]
    for item in items:
        assert item["why_it_applies"]
        assert item["next_action"]
        assert item["jurisdiction"]


def test_evidence_response_is_stable_for_repeat_requests(api_client):
    first = api_client.get("/api/v1/evidence/passport-stable").json()
    second = api_client.get("/api/v1/evidence/passport-stable").json()
    assert first == second


def test_evidence_is_served_for_a_nonexistent_passport_id(api_client):
    response = api_client.get("/api/v1/evidence/never-created-passport")
    assert response.status_code == 200
    assert response.json()["total_checks"] == 4


def test_lifecycle_update_changes_status_and_coverage(api_client):
    api_client.get("/api/v1/evidence/passport-lifecycle")
    response = api_client.put(
        "/api/v1/evidence/item/EV-01/lifecycle",
        json={
            "status": EvidenceLifecycle.ACCEPTED.value,
            "supplied_filename": "nabl-report.pdf",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == EvidenceLifecycle.ACCEPTED.value
    assert body["supplied_filename"] == "nabl-report.pdf"
    summary = api_client.get("/api/v1/evidence/passport-lifecycle").json()
    assert summary["coverage_meter_percentage"] == 100


def test_lifecycle_update_for_unknown_item_returns_404(api_client):
    response = api_client.put(
        "/api/v1/evidence/item/EV-999/lifecycle",
        json={"status": EvidenceLifecycle.ACCEPTED.value},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Evidence item not found"


def test_lifecycle_update_rejects_an_invalid_status(api_client):
    api_client.get("/api/v1/evidence/passport-invalid")
    response = api_client.put(
        "/api/v1/evidence/item/EV-01/lifecycle", json={"status": "TOTALLY_INVALID"}
    )
    assert response.status_code == 422


def test_lifecycle_update_can_mutate_another_passports_item(api_client):
    from app.api.v1 import evidence_router

    api_client.get("/api/v1/evidence/victim-passport")
    before = evidence_router._evidence_store["victim-passport"][0].status
    api_client.put(
        "/api/v1/evidence/item/EV-01/lifecycle",
        json={"status": EvidenceLifecycle.ACCEPTED.value},
        headers={"Authorization": "Bearer unrelated-token"},
    )
    after = evidence_router._evidence_store["victim-passport"][0].status
    assert before != after


@pytest.mark.xfail(
    reason="GET /evidence/{passport_id} has no authentication dependency",
    strict=False,
)
def test_evidence_gaps_require_authentication(api_client):
    response = api_client.get("/api/v1/evidence/passport-anon")
    assert response.status_code == 401


@pytest.mark.xfail(
    reason="the evidence store is keyed only by an arbitrary passport_id, so any caller can read another passport's evidence",
    strict=False,
)
def test_evidence_gaps_enforce_ownership(api_client, other_auth_headers):
    response = api_client.get(
        "/api/v1/evidence/owner-passport", headers=other_auth_headers
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="PUT /evidence/item/{item_id}/lifecycle has no ownership check and mutates a process-global store",
    strict=False,
)
def test_lifecycle_update_enforces_ownership(api_client, other_auth_headers):
    api_client.get("/api/v1/evidence/owner-passport")
    response = api_client.put(
        "/api/v1/evidence/item/EV-01/lifecycle",
        json={"status": EvidenceLifecycle.ACCEPTED.value},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)
