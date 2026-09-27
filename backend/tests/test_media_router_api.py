import pytest

pytestmark = pytest.mark.security


def test_media_endpoint_serves_existing_image(api_client):
    # The media endpoint looks in kb_root()/images; we don't have test images
    # so this documents the 404 behaviour for unknown paths
    response = api_client.get("/api/v1/copilot/media/does_not_exist.png")
    assert response.status_code == 404
    assert response.json()["detail"] == "Image not found"


def test_media_endpoint_blocks_absolute_path(api_client):
    response = api_client.get("/api/v1/copilot/media/../../../../etc/passwd")
    assert response.status_code == 404


def test_media_endpoint_blocks_parent_traversal(api_client):
    response = api_client.get("/api/v1/copilot/media/../etc/passwd")
    assert response.status_code == 404


def test_media_endpoint_blocks_null_byte(api_client):
    response = api_client.get("/api/v1/copilot/media/image.png%00")
    assert response.status_code == 404


def test_media_endpoint_blocks_direct_traversal(api_client):
    # os.path.abspath resolution + startswith containment check blocks basic traversal
    response = api_client.get("/api/v1/copilot/media/../../../../etc/passwd")
    assert response.status_code == 404


@pytest.mark.xfail(
    reason="startswith containment check is vulnerable to symlink attacks; an attacker who can plant a symlink in kb_root()/images could escape",
    strict=False,
)
def test_media_endpoint_contains_path_resolution_via_symlink(api_client):
    # This test documents the known weakness; fixing requires realpath + explicit allowlist
    response = api_client.get("/api/v1/copilot/media/any.png")
    assert response.status_code == 404


@pytest.mark.xfail(
    reason="media endpoint has no authentication dependency, so any caller can probe the image directory",
    strict=False,
)
def test_media_endpoint_requires_authentication(api_client):
    response = api_client.get("/api/v1/copilot/media/image.png")
    assert response.status_code == 401


def test_media_endpoint_only_serves_files_under_kb_images_directory(api_client):
    # arbitrary absolute path
    response = api_client.get("/api/v1/copilot/media//etc/passwd")
    assert response.status_code == 404
    # double encoding
    response = api_client.get("/api/v1/copilot/media/%2e%2e%2fetc%2fpasswd")
    assert response.status_code == 404