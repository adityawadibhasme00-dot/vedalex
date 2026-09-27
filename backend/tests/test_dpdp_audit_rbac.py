"""Security pack G3 — DPDP consent notice, hash-chained audit log (B4),
retention purge, and RBAC roles/permission logging (B5).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.auth.jwt_auth import create_access_token
from app.auth.rbac import ROLES, log_permission, normalize_role, require_role
from app.core.config import settings
from app.models.db_models import AuditLogEntry, ChatHistory, User
from app.rag import pipeline as pipe_mod
from app.services.audit_chain import (
    GENESIS_HASH,
    record_event,
    verify_chain,
)
from app.services.dpdp_service import notice_payload, purge_expired

pytestmark = pytest.mark.security


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "off")
    monkeypatch.delenv("IPSAKTI_BHASHINI_API_KEY", raising=False)
    monkeypatch.delenv("IPSAKTI_BHASHINI_USER_ID", raising=False)


class FakeRetriever:
    calls: list[dict] = []
    result: dict = {
        "sources": [
            {
                "title": "The Patents Act 1970",
                "content": "Section 3(p) bars known formulations.",
                "jurisdiction": "India",
            }
        ],
        "confidence": 0.9,
        "should_refuse": False,
    }

    @classmethod
    def retrieve(cls, query: str, **kwargs):
        cls.calls.append({"query": query, **kwargs})
        return dict(cls.result)


@pytest.fixture
def fake_retriever(monkeypatch):
    FakeRetriever.calls = []
    monkeypatch.setattr(pipe_mod, "HybridRetriever", FakeRetriever)
    return FakeRetriever


def _admin_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


# ---------------------------------------------------------------------------
# B4 — hash-chained audit log
# ---------------------------------------------------------------------------


def test_chain_links_entries_and_verifies(db_session):
    first = record_event(db_session, "chat.query", {"query_hash": "a" * 64})
    second = record_event(db_session, "agentic.query", {"query_hash": "b" * 64})
    assert first.prev_hash == GENESIS_HASH
    assert second.prev_hash == first.entry_hash
    assert first.entry_hash != second.entry_hash
    result = verify_chain(db_session)
    assert result == {"valid": True, "checked": 2, "first_broken_id": None}


def test_chain_detects_tampered_payload_via_raw_sql(db_session):
    entry = record_event(db_session, "chat.query", {"query_hash": "c" * 64})
    db_session.execute(
        text("UPDATE audit_log SET payload = :p WHERE id = :i"),
        {"p": '{"query_hash":"evil"}', "i": entry.id},
    )
    db_session.commit()
    result = verify_chain(db_session)
    assert result["valid"] is False
    assert result["first_broken_id"] == entry.id


def test_chain_orm_mutation_rejected_append_only(db_session):
    entry = record_event(db_session, "chat.query", {"query_hash": "d" * 64})
    entry.payload = '{"query_hash":"tampered"}'  # type: ignore[assignment]  # Column attr, no SA mypy plugin
    with pytest.raises(ValueError, match="append-only"):
        db_session.commit()
    db_session.rollback()
    with pytest.raises(ValueError, match="append-only"):
        db_session.delete(entry)
        db_session.commit()


def test_chain_stores_no_raw_query_text(db_session):
    record_event(
        db_session,
        "chat.query",
        {"query_hash": "e" * 64, "consent": False},
    )
    row = db_session.query(AuditLogEntry).one()
    assert row.payload == '{"consent":false,"query_hash":"' + "e" * 64 + '"}'
    assert len(row.actor_hash) == 64


def test_chat_query_writes_audit_entry_without_pii(api_client, db_session):
    resp = api_client.post(
        "/api/v1/chat/query",
        json={"question": "My Aadhaar is 1234 5678 9012, is turmeric patentable?"},
    )
    assert resp.status_code == 200
    entries = (
        db_session.query(AuditLogEntry)
        .filter(AuditLogEntry.event_type == "chat.query")
        .all()
    )
    assert entries, "chat.query event must be recorded in the audit chain"
    for entry in entries:
        assert "1234 5678 9012" not in entry.payload
        assert "123456789012" not in entry.payload
    assert verify_chain(db_session)["valid"] is True


def test_agentic_chat_writes_audit_entry(api_client, db_session, fake_retriever):
    resp = api_client.post(
        "/api/v1/agents/agentic-chat",
        json={"query": "What is Section 3(p)?", "jurisdiction": "india"},
    )
    assert resp.status_code == 200
    entries = (
        db_session.query(AuditLogEntry)
        .filter(AuditLogEntry.event_type == "agentic.query")
        .all()
    )
    assert entries
    assert verify_chain(db_session)["valid"] is True


# ---------------------------------------------------------------------------
# B3 — DPDP consent notice + retention
# ---------------------------------------------------------------------------


def test_dpdp_notice_endpoint_returns_required_fields(api_client):
    resp = api_client.get("/api/v1/dpdp/notice")
    assert resp.status_code == 200
    body = resp.json()
    assert "DPDP" in body["consent_notice"]
    assert body["retention_days"] == 90
    assert "Mumbai" in body["data_residency"] or "India" in body["data_residency"]
    assert body["grievance_officer"]["email"] == settings.GRIEVANCE_OFFICER_EMAIL
    assert "erasure" in body["rights"]
    assert body["persist_full_text_only_with_consent"] is True


def test_notice_payload_unit():
    payload = notice_payload()
    assert payload["retention_days"] == settings.DPDP_RETENTION_DAYS
    assert payload["grievance_officer"]["response_sla_days"] == 30


def test_purge_expired_removes_old_chat_rows(db_session, test_user):
    old = ChatHistory(
        user_id=test_user.id,
        message="old question",
        response="old answer",
        query_hash="f" * 64,
        created_at=datetime.now(UTC) - timedelta(days=120),
    )
    fresh = ChatHistory(
        user_id=test_user.id,
        message="recent question",
        response="recent answer",
        query_hash="9" * 64,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([old, fresh])
    db_session.commit()
    removed = purge_expired(db_session)
    assert removed == 1
    remaining = db_session.query(ChatHistory).all()
    assert [c.message for c in remaining] == ["recent question"]


def test_purge_honours_retention_until_override(db_session, test_user):
    soon = ChatHistory(
        user_id=test_user.id,
        message="explicit deadline",
        response="x",
        created_at=datetime.now(UTC),
        retention_until=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(soon)
    db_session.commit()
    assert purge_expired(db_session) == 1


# ---------------------------------------------------------------------------
# B5 — RBAC
# ---------------------------------------------------------------------------


def test_normalize_role_maps_legacy_and_unknown():
    assert normalize_role("researcher") == "practitioner"
    assert normalize_role("ADMIN") == "admin"
    assert normalize_role(None) == "practitioner"
    assert normalize_role("hacker") == "practitioner"
    assert set(ROLES) == {"practitioner", "startup", "facilitator", "admin"}


def test_require_role_dependency_allows_admin_and_role_holder():
    dependency = require_role("facilitator")
    admin = User(name="A", email="a@x.in", hashed_password="h", role="admin")
    fac = User(name="B", email="b@x.in", hashed_password="h", role="facilitator")
    prac = User(name="C", email="c@x.in", hashed_password="h", role="researcher")
    assert dependency(current_user=admin) is admin
    assert dependency(current_user=fac) is fac
    with pytest.raises(HTTPException) as exc:
        dependency(current_user=prac)
    assert exc.value.status_code == 403


def test_log_permission_emits_structured_line(caplog):
    with caplog.at_level("INFO", logger="ipsakti.permissions"):
        log_permission(None, "paid_source.patentscope", False, "no_subscription")
    assert "resource=paid_source.patentscope" in caplog.text
    assert "granted=False" in caplog.text
    assert "no_subscription" in caplog.text


def test_audit_verify_endpoint_rejects_anonymous(api_client):
    resp = api_client.get("/api/v1/dpdp/audit-chain/verify")
    assert resp.status_code in (401, 403)


def test_audit_verify_endpoint_rejects_practitioner(api_client, auth_headers):
    resp = api_client.get(
        "/api/v1/dpdp/audit-chain/verify", headers=auth_headers
    )
    assert resp.status_code == 403


def test_audit_verify_endpoint_allows_admin(api_client, admin_user, db_session):
    record_event(db_session, "chat.query", {"query_hash": "1" * 64})
    resp = api_client.get(
        "/api/v1/dpdp/audit-chain/verify", headers=_admin_headers(admin_user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["checked"] >= 1
    assert body["head"]


def test_purge_endpoint_requires_admin(api_client, admin_user, db_session):
    resp = api_client.post("/api/v1/dpdp/purge-retention")
    assert resp.status_code in (401, 403)
    resp = api_client.post(
        "/api/v1/dpdp/purge-retention", headers=_admin_headers(admin_user)
    )
    assert resp.status_code == 200
    assert resp.json()["retention_days"] == 90
    assert verify_chain(db_session)["valid"] is True
