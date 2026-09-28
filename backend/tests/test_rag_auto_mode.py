"""G6 — Unified RAG: combined-engine routing, fallback, and configure integration."""

from __future__ import annotations

import pytest

from app.services.rag.auto_selector import select_rag_type
from app.services.rag.config import reset_runtime, update

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Selector (pure rules — offline)
# ---------------------------------------------------------------------------

def test_any_query_routes_to_combined():
    selection = select_rag_type("Withania somnifera")
    assert selection["rag_type"] == "combined"
    assert selection["reason"] == "all RAG engines combined into one"


def test_question_routes_to_combined_default():
    selection = select_rag_type("What is the patentability of turmeric extraction?")
    assert selection["rag_type"] == "combined"


def test_multi_aspect_question_routes_to_combined():
    selection = select_rag_type(
        "Compare patent and trademark strategy and list the deadlines"
    )
    assert selection["rag_type"] == "combined"


def test_default_of_auto_never_recurses():
    selection = select_rag_type(
        "Explain the registration process in full detail", default="auto"
    )
    assert selection["rag_type"] == "combined"


def test_config_default_accepts_combined():
    reset_runtime()
    try:
        assert update({"default": "graph"}) == {"default": "graph"}
        assert update({"default": "combined"}) == {"default": "combined"}
        assert update({"default": "bogus"}) == {}
    finally:
        reset_runtime()


# ---------------------------------------------------------------------------
# Endpoint: auto mode
# ---------------------------------------------------------------------------

def test_search_auto_resolves_combined(api_client):
    response = api_client.post(
        "/api/v1/rag/search",
        json={"query": "Withania somnifera", "rag_type": "auto"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["meta"]["auto_resolved"] == "combined"
    assert data["rag_type"] == "combined"


def test_search_auto_multi_aspect_resolves_combined(api_client):
    response = api_client.post(
        "/api/v1/rag/search",
        json={
            "query": "Compare patent and trademark strategy and list the deadlines",
            "rag_type": "auto",
        },
    )
    assert response.status_code == 200
    assert response.json()["meta"]["auto_resolved"] == "combined"


# ---------------------------------------------------------------------------
# Endpoint: fallback
# ---------------------------------------------------------------------------

def test_search_falls_back_to_hybrid_when_architecture_fails(monkeypatch, api_client):
    from app.services import rag as rag_pkg

    real_get_rag = rag_pkg.get_rag

    class ExplodingRAG:
        rag_type = "production"

        def search(self, **kwargs):
            raise RuntimeError("engine down")

        def status(self):
            return {"rag_type": "production", "available": False}

    def patched_get_rag(rag_type):
        if rag_type == "production":
            return ExplodingRAG()
        return real_get_rag(rag_type)

    monkeypatch.setattr(rag_pkg, "get_rag", patched_get_rag)

    response = api_client.post(
        "/api/v1/rag/search",
        json={"query": "What is a patent?", "rag_type": "production"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["fallback_from"] == "production"
    assert "engine down" in data["meta"]["fallback_error"]
    assert data["rag_type"] == "hybrid"
    assert data["success"] is True


# ---------------------------------------------------------------------------
# Endpoint: configure accepts auto
# ---------------------------------------------------------------------------

def test_configure_accepts_auto_and_rejects_bogus(api_client):
    try:
        response = api_client.post("/api/v1/rag/configure", json={"rag_type": "auto"})
        assert response.status_code == 200
        assert response.json()["config"]["default"] == "auto"

        bad = api_client.post("/api/v1/rag/configure", json={"rag_type": "bogus"})
        assert bad.status_code == 400
    finally:
        api_client.post("/api/v1/rag/configure", json={"rag_type": "hybrid"})
        reset_runtime()
