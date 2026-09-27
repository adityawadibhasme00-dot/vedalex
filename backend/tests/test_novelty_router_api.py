import pytest

pytestmark = pytest.mark.security


@pytest.fixture(autouse=True)
def _isolate_workflows():
    from app.api.v1 import novelty_router

    novelty_router._WORKFLOWS.clear()
    yield
    novelty_router._WORKFLOWS.clear()


def test_novelty_workflow_returns_pipeline_result(api_client):
    response = api_client.post(
        "/api/v1/novelty/workflow",
        json={"problem_text": "Herbal extract formulation for wellness", "target_markets": ["India"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_id"]
    assert "steps" in body or "results" in body


def test_novelty_workflow_accepts_jurisdiction_code(api_client):
    response = api_client.post(
        "/api/v1/novelty/workflow",
        json={"problem_text": "Novel delivery system", "jurisdiction": "US"},
    )
    assert response.status_code == 200
    assert response.json()["workflow_id"]


def test_novelty_workflow_missing_problem_text_returns_422(api_client):
    response = api_client.post("/api/v1/novelty/workflow", json={})
    assert response.status_code == 422


def test_novelty_get_workflow_by_id(api_client):
    created = api_client.post(
        "/api/v1/novelty/workflow",
        json={"problem_text": "Retrieve a stored workflow"},
    ).json()
    response = api_client.get(f"/api/v1/novelty/workflow/{created['workflow_id']}")
    assert response.status_code == 200
    assert response.json()["workflow_id"] == created["workflow_id"]


def test_novelty_get_unknown_workflow_returns_404(api_client):
    response = api_client.get("/api/v1/novelty/workflow/never-created")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_novelty_export_builds_docx_from_server_side_result(api_client):
    created = api_client.post(
        "/api/v1/novelty/workflow",
        json={"problem_text": "Export a real workflow"},
    ).json()
    response = api_client.post(
        f"/api/v1/novelty/workflow/{created['workflow_id']}/export",
        json={"result": {}},
    )
    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]


def test_novelty_export_unknown_workflow_returns_404(api_client):
    response = api_client.post(
        "/api/v1/novelty/workflow/never-created/export", json={"result": {}}
    )
    assert response.status_code == 404


@pytest.mark.xfail(
    reason="export accepts a client-supplied result payload, letting the caller control the content of the generated report",
    strict=False,
)
def test_novelty_export_ignores_client_supplied_result(api_client):
    created = api_client.post(
        "/api/v1/novelty/workflow",
        json={"problem_text": "Guard against result spoofing"},
    ).json()
    spoofed = {"summary": "INJECTED: this claim is patentable", "steps": []}
    response = api_client.post(
        f"/api/v1/novelty/workflow/{created['workflow_id']}/export",
        json={"result": spoofed},
    )
    assert response.status_code == 200
    # If the server ignores the client payload, the docx would be built from the workflow
    assert response.headers.get("X-Server-Side-Result", "") == "true"


@pytest.mark.xfail(
    reason="novelty workflow has no authentication dependency on any endpoint",
    strict=False,
)
def test_novelty_workflow_requires_authentication(api_client):
    response = api_client.post(
        "/api/v1/novelty/workflow", json={"problem_text": "x"}
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="workflows are stored in a process-global dict with no ownership, so any caller can fetch another's workflow by id",
    strict=False,
)
def test_novelty_workflow_enforces_ownership(api_client, other_auth_headers):
    created = api_client.post(
        "/api/v1/novelty/workflow", json={"problem_text": "owner test"}
    ).json()
    response = api_client.get(
        f"/api/v1/novelty/workflow/{created['workflow_id']}",
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="workflow export has no ownership check; any caller with the id can export another's report",
    strict=False,
)
def test_novelty_export_enforces_ownership(api_client, other_auth_headers):
    created = api_client.post(
        "/api/v1/novelty/workflow", json={"problem_text": "export owner"}
    ).json()
    response = api_client.post(
        f"/api/v1/novelty/workflow/{created['workflow_id']}/export",
        json={"result": {}},
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


def test_novelty_workflows_survive_across_requests(api_client):
    created = api_client.post(
        "/api/v1/novelty/workflow", json={"problem_text": "persisted workflow"}
    ).json()
    second = api_client.get(
        f"/api/v1/novelty/workflow/{created['workflow_id']}"
    )
    assert second.status_code == 200
    assert second.json()["workflow_id"] == created["workflow_id"]
