import pytest

pytestmark = pytest.mark.security


def test_chat_query_returns_answer_and_sources(api_client):
    response = api_client.post(
        "/api/v1/chat/query",
        json={"question": "What are the patent requirements for Ashwagandha in India?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert "sources" in body
    assert "confidence" in body
    assert "audit" in body


def test_chat_query_accepts_passport_id_context(api_client):
    response = api_client.post(
        "/api/v1/chat/query",
        json={"question": "test", "passport_id": "some-id"},
    )
    assert response.status_code == 200


def test_chat_query_accepts_context_dict(api_client):
    response = api_client.post(
        "/api/v1/chat/query",
        json={"question": "test", "context": {"key": "value"}},
    )
    assert response.status_code == 200


def test_chat_query_consent_record_opt_in(api_client):
    response = api_client.post(
        "/api/v1/chat/query",
        json={"question": "test", "consent_record": True},
    )
    assert response.status_code == 200
    audit = response.json()["audit"]
    assert "persisted" in audit


def test_chat_query_without_consent_does_not_persist_full_text(api_client):
    response = api_client.post(
        "/api/v1/chat/query", json={"question": "test", "consent_record": False}
    )
    assert response.status_code == 200
    audit = response.json()["audit"]
    assert audit.get("persisted") is not True


def test_chat_query_audit_contains_query_hash_and_citation_ids(api_client):
    response = api_client.post("/api/v1/chat/query", json={"question": "test"})
    audit = response.json()["audit"]
    assert "query_hash" in audit
    assert "citation_ids" in audit
    assert "audit_id" in audit


def test_chat_query_accepts_empty_question(api_client):
    # ChatRequest.question has no min_length validation; empty string is accepted
    response = api_client.post("/api/v1/chat/query", json={"question": ""})
    assert response.status_code == 200


def test_chat_audit_trail_returns_entries(api_client):
    response = api_client.get("/api/v1/chat/audit-trail")
    assert response.status_code == 200
    assert "entries" in response.json()


def test_chat_audit_trail_respects_limit(api_client):
    response = api_client.get("/api/v1/chat/audit-trail?limit=5")
    assert response.status_code == 200
    assert len(response.json()["entries"]) <= 5


def test_chat_suggested_questions_returns_list(api_client):
    response = api_client.get("/api/v1/chat/suggested-questions")
    assert response.status_code == 200
    assert "questions" in response.json()
    assert len(response.json()["questions"]) > 0


@pytest.mark.xfail(
    reason="audit trail does not include user_id even when authenticated and consent_record=true",
    strict=False,
)
def test_chat_query_audit_includes_user_id_when_authenticated(api_client, auth_headers):
    response = api_client.post(
        "/api/v1/chat/query",
        json={"question": "test", "consent_record": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    audit = response.json()["audit"]
    assert audit.get("user_id") is not None


@pytest.mark.xfail(
    reason="audit trail uses id(audit_entry) which is a Python object id, not a stable identifier",
    strict=False,
)
def test_chat_audit_uses_stable_identifier_not_id(api_client):
    response = api_client.post("/api/v1/chat/query", json={"question": "test"})
    audit = response.json()["audit"]
    assert not isinstance(audit.get("audit_id"), int)


@pytest.mark.xfail(
    reason="chat/query accepts optional auth; no ownership check on passport_id context",
    strict=False,
)
def test_chat_query_enforces_passport_ownership(api_client, test_passport, other_auth_headers):
    response = api_client.post(
        "/api/v1/chat/query",
        json={"question": "test", "passport_id": test_passport.id},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


def test_chat_query_does_not_require_authentication(api_client):
    response = api_client.post("/api/v1/chat/query", json={"question": "test"})
    assert response.status_code == 200


def test_chat_audit_trail_does_not_require_authentication(api_client):
    response = api_client.get("/api/v1/chat/audit-trail")
    assert response.status_code == 200