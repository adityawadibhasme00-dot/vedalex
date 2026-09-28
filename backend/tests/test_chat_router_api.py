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


# ---------------------------------------------------------------------------
# Self-abstention + failure containment
# ---------------------------------------------------------------------------

def test_chat_query_flags_abstention_when_no_evidence_found(api_client):
    response = api_client.post(
        "/api/v1/chat/query",
        json={"question": "What are the patent requirements for Ashwagandha in India?"},
    )
    body = response.json()
    assert "abstained" in body
    # Retrieval confidence for this question varies between runs, so assert the
    # invariant rather than a specific verdict.
    if body["abstained"]:
        # A refusal must never advertise citations or a confidence score: the
        # client would render "no answer given" above sources the user reads as
        # backing for a claim that was not made.
        assert body["sources"] == []
        assert body["confidence"] == 0.0
        assert body["abstention_reason"]
    else:
        assert body["sources"]


def test_derive_abstention_enforces_no_citations_on_refusal():
    """Unit-level guard on the contract itself: a weak-evidence refusal must
    not keep advertising the sources it decided were insufficient."""
    from app.api.v1.chat_router import _derive_abstention

    result = {
        "answer": "Here is a weakly supported answer.",
        "sources": [{"title": "Some Act", "content": "text"}],
        "confidence": 0.2,
        "response_sections": {"official_sources_used": [{"source": "Some Act"}]},
    }
    _derive_abstention(result, "no official source")
    assert result["abstained"] is True
    assert result["abstention_reason"] == "retrieved evidence was too weak to support an answer"
    assert result["sources"] == []
    assert result["confidence"] == 0.0
    assert result["response_sections"]["official_sources_used"] == []


def test_derive_abstention_normalises_orchestrator_refusal():
    """The orchestrator can flag its own refusal; the no-citations invariant
    must hold for that path too."""
    from app.api.v1.chat_router import _derive_abstention

    result = {
        "answer": "I could not find an official source.",
        "sources": [{"title": "Leaked", "content": "text"}],
        "confidence": 0.4,
        "abstained": True,
        "abstention_reason": "no supporting evidence in the indexed corpus",
    }
    _derive_abstention(result, "no official source")
    assert result["abstained"] is True
    assert result["abstention_reason"] == "no supporting evidence in the indexed corpus"
    assert result["sources"] == []
    assert result["confidence"] == 0.0


def test_derive_abstention_keeps_sourced_answer_intact():
    from app.api.v1.chat_router import _derive_abstention

    result = {
        "answer": "DSHEA defines the requirements.",
        "sources": [{"title": "DSHEA", "content": "text"}],
        "confidence": 0.81,
        "response_sections": {"official_sources_used": [{"source": "DSHEA"}]},
    }
    _derive_abstention(result, "no official source")
    assert result["abstained"] is False
    assert result["abstention_reason"] is None
    assert result["sources"]
    assert result["confidence"] == 0.81


def test_chat_query_pipeline_failure_returns_abstention_not_500(api_client, monkeypatch):
    """A broken retrieval service must not surface as an opaque backend error,
    and must never be replaced by a generated answer."""
    def _boom(*args, **kwargs):
        raise RuntimeError("retrieval backend exploded")

    monkeypatch.setattr(
        "app.services.multi_layer_orchestrator.MultiLayerOrchestrator.run",
        staticmethod(_boom),
    )
    response = api_client.post("/api/v1/chat/query", json={"question": "neem prior art"})
    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is True
    assert body["abstention_reason"] == "retrieval pipeline failure"
    assert body["sources"] == []
    assert body["confidence"] == 0.0
    assert "could not complete this query" in body["answer"].lower()


def test_chat_query_malformed_orchestrator_payload_degrades_to_abstention(
    api_client, monkeypatch
):
    """A payload that violates the response contract must not 500 in the
    serialiser, and must not be trusted enough to display."""
    monkeypatch.setattr(
        "app.services.multi_layer_orchestrator.MultiLayerOrchestrator.run",
        staticmethod(lambda *a, **k: {"answer": 12345, "sources": "not-a-list"}),
    )
    response = api_client.post("/api/v1/chat/query", json={"question": "neem prior art"})
    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is True
    assert body["abstention_reason"] == "malformed orchestrator response"
    assert body["sources"] == []


def test_chat_query_audit_failure_does_not_fail_the_request(api_client, monkeypatch):
    """Audit bookkeeping is best-effort and must never lose a served answer."""
    def _boom(*args, **kwargs):
        raise RuntimeError("audit store down")

    monkeypatch.setattr(
        "app.services.privacy_service.QueryAuditLog.record", staticmethod(_boom)
    )
    response = api_client.post(
        "/api/v1/chat/query",
        json={"question": "What are the patent requirements for Ashwagandha in India?"},
    )
    assert response.status_code == 200
    assert response.json()["answer"]


def test_chat_query_audit_chain_event_survives_audit_log_failure(api_client, monkeypatch):
    """When the audit log fails, the reduced stub must still carry both hashes,
    otherwise the privacy-preserving audit-chain event is dropped silently."""
    import app.services.audit_chain as audit_chain

    recorded = {}

    def _record_event(db, action, payload, actor_id=None):
        recorded["action"] = action
        recorded["payload"] = payload

    def _boom(*args, **kwargs):
        raise RuntimeError("audit store down")

    monkeypatch.setattr(
        "app.services.privacy_service.QueryAuditLog.record", staticmethod(_boom)
    )
    monkeypatch.setattr(audit_chain, "record_event", _record_event)

    response = api_client.post(
        "/api/v1/chat/query",
        json={"question": "What are the patent requirements for Ashwagandha in India?"},
    )
    assert response.status_code == 200
    assert recorded.get("action") == "chat.query"
    assert recorded["payload"]["query_hash"]
    assert recorded["payload"]["answer_hash"]


def test_chat_query_reports_clarification_not_weak_evidence(api_client):
    """The abstention reason is user-facing, so a clarification must be labelled
    as one — it deliberately carries low confidence, which would otherwise
    misreport it as weak evidence."""
    response = api_client.post(
        "/api/v1/chat/query",
        json={"question": "What is the capital of France?"},
    )
    body = response.json()
    assert body["abstained"] is True
    if body["response_sections"].get("clarification_needed"):
        assert body["abstention_reason"] == "jurisdiction clarification required"


# ---------------------------------------------------------------------------
# The answer/refusal contract
# ---------------------------------------------------------------------------

# Covers both in-domain questions and input the corpus cannot address, in every
# language the copilot supports. Hindi and Hinglish are here deliberately: an
# earlier English-only out-of-scope pre-filter refused both as "off-topic" and
# would have blocked a first-class supported language.
CONTRACT_QUERIES = [
    "What is the capital of France?",
    "SELECT * FROM users; DROP TABLE users;--",
    "भारत में पेटेंट कैसे करें",
    "kya mujhe kaise kar sakti hoon aur ye dawa bhi",
    "How do I comply with DSHEA in the US market?",
]


@pytest.mark.parametrize("question", CONTRACT_QUERIES)
def test_chat_response_never_presents_an_unsupported_answer(api_client, question):
    """Either a sourced answer, or a refusal that cites nothing.

    This is the guarantee behind "answer only from the corpus, and abstain when
    evidence is missing or weak". Retrieval confidence for a given question
    varies run to run, so the verdict is not asserted — the invariant is.
    """
    response = api_client.post("/api/v1/chat/query", json={"question": question})
    assert response.status_code == 200
    body = response.json()
    if body["abstained"]:
        assert body["sources"] == [], "a refusal must not cite sources"
        assert body["confidence"] == 0.0, "a refusal must not report confidence"
        assert body["abstention_reason"], "a refusal must say why"
    else:
        assert body["sources"], "an answer must be backed by sources"
        assert body["answer"]
