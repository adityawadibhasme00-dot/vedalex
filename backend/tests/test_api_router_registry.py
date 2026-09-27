import pytest

from app.api.v1.router import api_router
from app.main import app

HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})

EXPECTED_ROUTER_COUNT = 31
EXPECTED_PATH_COUNT = 110
EXPECTED_OPERATION_COUNT = 114

EXPECTED_PREFIXES = frozenset(
    {
        "admin",
        "agents",
        "analysis",
        "assessment",
        "auth",
        "botanical",
        "chat",
        "copilot",
        "deadlines",
        "dossier",
        "dpdp",
        "evals",
        "evidence",
        "expert-handoff",
        "export",
        "fees",
        "formulation",
        "fto",
        "health",
        "innolab",
        "institutional",
        "intelligence",
        "label",
        "novelty",
        "passport",
        "prefill",
        "rag",
        "red-team",
        "regulatory-diff",
        "roadmap",
        "screening",
        "upload",
        "watch",
        "what-if",
        "whitespace",
    }
)

EXPECTED_SECURED_OPERATIONS = frozenset(
    {
        ("GET", "/api/v1/agents/components"),
        ("POST", "/api/v1/agents/agentic-chat"),
        ("GET", "/api/v1/auth/profile"),
        ("POST", "/api/v1/chat/query"),
        ("GET", "/api/v1/deadlines"),
        ("POST", "/api/v1/deadlines"),
        ("POST", "/api/v1/deadlines/schedule"),
        ("POST", "/api/v1/deadlines/{deadline_id}/done"),
        ("POST", "/api/v1/dossier/build"),
        ("GET", "/api/v1/dpdp/audit-chain/verify"),
        ("POST", "/api/v1/dpdp/purge-retention"),
        ("POST", "/api/v1/fees/estimate"),
        ("POST", "/api/v1/prefill/{form}"),
        ("POST", "/api/v1/rag/ask"),
        ("POST", "/api/v1/rag/boolean-search"),
        ("GET", "/api/v1/rag/innovation-passport/{passport_id}"),
        ("POST", "/api/v1/rag/search"),
        ("POST", "/api/v1/rag/search-patent"),
        ("GET", "/api/v1/watch/digest"),
        ("GET", "/api/v1/watch/profiles"),
        ("POST", "/api/v1/watch/profiles"),
        ("DELETE", "/api/v1/watch/profiles/{profile_id}"),
        ("POST", "/api/v1/watch/run"),
    }
)


def _segment(path: str, index: int) -> str:
    parts = path.split("/")
    return parts[index] if len(parts) > index else "<root>"


@pytest.fixture(scope="module")
def openapi_paths() -> dict:
    return app.openapi()["paths"]


@pytest.fixture(scope="module")
def operations(openapi_paths) -> list[tuple[str, str]]:
    return sorted(
        (method.upper(), path)
        for path, methods in openapi_paths.items()
        for method in methods
        if method.upper() in HTTP_METHODS
    )


@pytest.fixture(scope="module")
def secured_operations(openapi_paths) -> list[tuple[str, str]]:
    return sorted(
        (method.upper(), path)
        for path, methods in openapi_paths.items()
        for method, operation in methods.items()
        if method.upper() in HTTP_METHODS and operation.get("security")
    )


def test_api_router_includes_expected_number_of_routers():
    assert len(api_router.routes) == EXPECTED_ROUTER_COUNT


def test_openapi_exposes_expected_path_count(openapi_paths):
    assert len(openapi_paths) == EXPECTED_PATH_COUNT


def test_openapi_exposes_expected_operation_count(operations):
    assert len(operations) == EXPECTED_OPERATION_COUNT


def test_no_duplicate_method_path_pairs(operations):
    assert len(operations) == len(set(operations))


def test_expected_router_prefixes_are_mounted(openapi_paths):
    mounted = {
        _segment(path, 3) for path in openapi_paths if path.startswith("/api/v1/")
    }
    assert mounted == EXPECTED_PREFIXES


def test_every_api_path_is_versioned_or_root(openapi_paths):
    unversioned = [path for path in openapi_paths if not path.startswith(("/api/v1", "/"))]
    assert unversioned == []


def test_openapi_declares_bearer_security_scheme():
    schemes = app.openapi().get("components", {}).get("securitySchemes", {})
    assert any(name.lower().startswith("httpbearer") for name in schemes), schemes


def test_profile_route_requires_bearer_auth(openapi_paths):
    security = openapi_paths["/api/v1/auth/profile"]["get"]["security"]
    assert security and list(security[0]) == ["HTTPBearer"]


def test_public_auth_routes_declare_no_security(openapi_paths):
    assert openapi_paths["/api/v1/auth/signup"]["post"].get("security") is None
    assert openapi_paths["/api/v1/auth/login"]["post"].get("security") is None


def test_authenticated_operation_surface_matches_snapshot(secured_operations):
    assert set(secured_operations) == EXPECTED_SECURED_OPERATIONS


def test_most_operations_declare_no_authentication(operations, secured_operations):
    unsecured = len(operations) - len(secured_operations)
    assert unsecured == 91
