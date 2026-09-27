import pytest

from app.services.expert_handoff_service import ExpertHandoffService
from app.services.passport_engine import PassportEngine

pytestmark = pytest.mark.security


@pytest.fixture(autouse=True)
def _isolate():
    ExpertHandoffService._tickets.clear()
    PassportEngine._passports_store.clear()
    yield
    ExpertHandoffService._tickets.clear()
    PassportEngine._passports_store.clear()


def _dispatch_payload(**overrides):
    payload = {
        "passport_id": "PASS-123",
        "user_name": "Test User",
        "user_email": "handoff@example.test",
        "explicit_dpdp_consent": True,
        "liability_boundary_acknowledged": True,
    }
    payload.update(overrides)
    return payload


def test_dispatch_with_consent_returns_ticket(api_client):
    response = api_client.post("/api/v1/expert-handoff/dispatch", json=_dispatch_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"].startswith("IP-EXPERT-")
    assert body["passport_id"] == "PASS-123"
    assert body["status"] == "QUEUED_FOR_EXPERT_DISPATCH"
    assert body["sla_response_hours"] == 48
    assert body["dossier_download_url"].endswith(f"{body['ticket_id']}.pdf")
    assert body["consent_audit_hash"]


def test_dispatch_rejects_missing_dpdp_consent(api_client):
    response = api_client.post(
        "/api/v1/expert-handoff/dispatch",
        json=_dispatch_payload(explicit_dpdp_consent=False),
    )
    assert response.status_code == 400
    assert "DPDP" in response.json()["detail"]


def test_dispatch_rejects_missing_liability_ack(api_client):
    response = api_client.post(
        "/api/v1/expert-handoff/dispatch",
        json=_dispatch_payload(liability_boundary_acknowledged=False),
    )
    assert response.status_code == 400
    assert "liability" in response.json()["detail"].lower()


def test_dispatch_validates_required_fields(api_client):
    response = api_client.post(
        "/api/v1/expert-handoff/dispatch", json={"passport_id": "PASS-123"}
    )
    assert response.status_code == 422


def test_dispatch_accepts_unknown_passport_id(api_client):
    # No passport existence validation on dispatch — ticket is issued for any id
    response = api_client.post(
        "/api/v1/expert-handoff/dispatch", json=_dispatch_payload(passport_id="never-exists")
    )
    assert response.status_code == 200
    assert response.json()["passport_id"] == "never-exists"


def test_dossier_unknown_ticket_returns_404(api_client):
    response = api_client.get("/api/v1/expert-handoff/dossier/IP-EXPERT-NOPE.pdf")
    assert response.status_code == 404
    assert response.json()["detail"] == "Handoff ticket not found"


def test_dossier_renders_html_for_dispatched_ticket(api_client, test_passport):
    dispatched = api_client.post(
        "/api/v1/expert-handoff/dispatch",
        json=_dispatch_payload(passport_id=test_passport.id),
    ).json()
    response = api_client.get(dispatched["dossier_download_url"])
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert dispatched["ticket_id"] in response.text
    assert "Proposed Claims" in response.text


def test_dossier_returns_404_when_passport_missing(api_client):
    dispatched = api_client.post(
        "/api/v1/expert-handoff/dispatch",
        json=_dispatch_payload(passport_id="vanished-passport"),
    ).json()
    response = api_client.get(dispatched["dossier_download_url"])
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


@pytest.mark.xfail(
    reason="dispatch collects PII (name, email, phone) under DPDP with no authentication",
    strict=False,
)
def test_dispatch_requires_authentication(api_client):
    response = api_client.post("/api/v1/expert-handoff/dispatch", json=_dispatch_payload())
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="dossier with personal data and claims is served with no authentication",
    strict=False,
)
def test_dossier_requires_authentication(api_client, test_passport):
    dispatched = api_client.post(
        "/api/v1/expert-handoff/dispatch",
        json=_dispatch_payload(passport_id=test_passport.id),
    ).json()
    response = api_client.get(dispatched["dossier_download_url"])
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="dispatch stores tickets in a global dict with no ownership; any caller can dispatch any passport",
    strict=False,
)
def test_dispatch_enforces_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.post(
        "/api/v1/expert-handoff/dispatch",
        json=_dispatch_payload(passport_id=test_passport.id),
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="dossier interpolates passport claims and ingredient names into HTML without escaping (stored XSS)",
    strict=False,
)
def test_dossier_escapes_html_in_passport_content(api_client):
    passport = PassportEngine.create_from_intake(
        raw_text="Herbal formulation with <script>alert(1)</script> in claim text",
        user_lang="en",
        title="XSS Probe",
        intake={"proposed_claims": ["Cures everything <script>alert(1)</script>"]},
    )
    dispatched = api_client.post(
        "/api/v1/expert-handoff/dispatch",
        json=_dispatch_payload(passport_id=passport.id),
    ).json()
    response = api_client.get(dispatched["dossier_download_url"])
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text
