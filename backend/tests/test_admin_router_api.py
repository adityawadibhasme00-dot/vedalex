import pytest

pytestmark = pytest.mark.security


def test_admin_status_requires_no_authentication(api_client):
    response = api_client.get("/api/v1/admin/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "kb_root" in body


def test_admin_reindex_requires_api_key(api_client):
    response = api_client.post("/api/v1/admin/reindex", json={"api_key": "wrong"})
    assert response.status_code == 403


def test_admin_reindex_accepts_correct_key(api_client):
    from app.core.config import settings

    key = settings.BACKEND_API_KEY_SECRET
    response = api_client.post("/api/v1/admin/reindex", json={"api_key": key})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "indexed_chunks" in body


def test_admin_reindex_rejects_missing_key(api_client):
    response = api_client.post("/api/v1/admin/reindex", json={})
    assert response.status_code == 422


def test_admin_harvest_indiacode_requires_api_key(api_client):
    response = api_client.post("/api/v1/admin/harvest/indiacode", json={"api_key": "wrong"})
    assert response.status_code == 403


def test_admin_harvest_indiacode_accepts_correct_key(api_client):
    from app.core.config import settings

    key = settings.BACKEND_API_KEY_SECRET
    response = api_client.post(
        "/api/v1/admin/harvest/indiacode",
        json={"api_key": key, "act_ids": ["__test_only__"]},
    )
    assert response.status_code == 200
    assert response.json()["total_chunks"] == 0


def test_admin_status_reports_faiss_index_state(api_client):
    body = api_client.get("/api/v1/admin/status").json()
    assert "index_present" in body
    assert "index_size" in body


def test_admin_status_includes_corpus_manifest(api_client):
    body = api_client.get("/api/v1/admin/status").json()
    assert "corpus_version" in body
    assert "manifest_present" in body


def test_admin_status_includes_indiacode_metrics(api_client):
    body = api_client.get("/api/v1/admin/status").json()
    assert "india_code_acts" in body
    assert "india_code_api_live" in body


@pytest.mark.xfail(
    reason="reindex is an admin operation but only protected by API key; no rate limiting or audit",
    strict=False,
)
def test_admin_reindex_has_audit_and_rate_limit(api_client):
    from app.core.config import settings

    key = settings.BACKEND_API_KEY_SECRET
    codes = [
        api_client.post("/api/v1/admin/reindex", json={"api_key": key}).status_code
        for _ in range(10)
    ]
    # Rate limiting would throttle repeated calls with 429
    assert any(c == 429 for c in codes)


@pytest.mark.xfail(
    reason="status endpoint is unauthenticated, leaking KB structure and manifest",
    strict=False,
)
def test_admin_status_requires_authentication(api_client):
    response = api_client.get("/api/v1/admin/status")
    assert response.status_code in (401, 403)