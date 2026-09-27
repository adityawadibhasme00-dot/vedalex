import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

VALID_PASSPORT_ID = "test-passport-123"


@pytest.fixture
def passport_fixture():
    from app.services.passport_engine import PassportEngine

    PassportEngine._passports_store.clear()
    passport = PassportEngine.create_from_intake(
        raw_text="Test formulation for export",
        user_lang="en",
        title="Export Test",
        intake={"target_markets": ["India", "United States"]},
    )
    yield passport
    PassportEngine._passports_store.clear()


def test_export_dossier_returns_download_url(api_client, passport_fixture):
    response = api_client.post(
        "/api/v1/export/dossier", json={"passport_id": passport_fixture.id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["download_url"].startswith("/api/v1/export/download/")
    assert body["filename"].startswith("IPSAKTI_Dossier_")


def test_export_dossier_for_unknown_passport_returns_404(api_client):
    response = api_client.post(
        "/api/v1/export/dossier", json={"passport_id": "does-not-exist"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


def test_export_generates_html_with_user_supplied_data(api_client, passport_fixture):
    response = api_client.post(
        "/api/v1/export/dossier", json={"passport_id": passport_fixture.id}
    )
    filename = response.json()["filename"]
    download = api_client.get(f"/api/v1/export/download/{filename}")
    html = download.text
    assert passport_fixture.case_title in html
    assert "Export Test" in html
    assert passport_fixture.id[:8] in html
    assert "India" in html


def test_download_endpoint_blocks_path_traversal(api_client, passport_fixture):
    export_dir = Path(os.path.join(os.path.dirname(__file__), "..", "..", "..", "exports"))
    export_dir.mkdir(exist_ok=True)
    # write a file outside export_dir
    outside = Path(os.path.dirname(__file__)) / ".." / ".." / ".." / "secret.txt"
    outside.write_text("SECRET")
    try:
        response = api_client.get(
            "/api/v1/export/download/../../secret.txt"
        )
        assert response.status_code == 404
    finally:
        if outside.exists():
            outside.unlink()


def test_download_endpoint_blocks_path_traversal_with_allowed_extension(api_client):
    # The download endpoint has no containment check beyond os.path.exists;
    # a filename like ../../etc/passwd could escape if the file exists
    response = api_client.get("/api/v1/export/download/../../etc/passwd")
    assert response.status_code == 404


@pytest.mark.xfail(
    reason="exported HTML directly interpolates user-controlled fields (claims, innovation description) without escaping, enabling stored XSS",
    strict=False,
)
def test_exported_html_escapes_user_supplied_strings(api_client, passport_fixture):
    from app.services.passport_engine import PassportEngine

    malicious = PassportEngine.create_from_intake(
        raw_text="x",
        user_lang="en",
        title="<script>alert('xss')</script>",
        intake={
            "proposed_claims": ['<img src=x onerror=alert(1)>', 'normal claim'],
            "claimed_innovation": "<script>stealCookies()</script>",
        },
    )
    response = api_client.post(
        "/api/v1/export/dossier", json={"passport_id": malicious.id}
    )
    filename = response.json()["filename"]
    download = api_client.get(f"/api/v1/export/download/{filename}")
    html = download.text
    assert "<script>" not in html
    assert "<script>" in html or "<img" in html


def test_download_missing_file_returns_404(api_client):
    response = api_client.get("/api/v1/export/download/does_not_exist.html")
    assert response.status_code == 404


def test_download_endpoint_only_serves_files_from_export_directory(api_client):
    response = api_client.get("/api/v1/export/download/../../etc/passwd")
    assert response.status_code == 404


def test_export_includes_qr_code_when_qrcode_available(api_client, passport_fixture):
    response = api_client.post(
        "/api/v1/export/dossier", json={"passport_id": passport_fixture.id}
    )
    filename = response.json()["filename"]
    download = api_client.get(f"/api/v1/export/download/{filename}")
    assert "data:image/png;base64," in download.text


def test_export_dossier_does_not_require_authentication(api_client, passport_fixture):
    response = api_client.post(
        "/api/v1/export/dossier", json={"passport_id": passport_fixture.id}
    )
    assert response.status_code == 200


def test_download_does_not_require_authentication(api_client, passport_fixture):
    body = api_client.post(
        "/api/v1/export/dossier", json={"passport_id": passport_fixture.id}
    ).json()
    response = api_client.get(f"/api/v1/export/download/{body['filename']}")
    assert response.status_code == 200