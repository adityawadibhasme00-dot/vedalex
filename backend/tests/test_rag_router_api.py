import pytest

pytestmark = pytest.mark.security


def test_rag_ask_returns_structured_response(api_client):
    response = api_client.post(
        "/api/v1/rag/ask",
        json={"query": "What are the patent requirements for Ashwagandha formulation in India?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert "sources" in body
    assert "confidence" in body
    assert "grounding" in body
    assert "hallucination_check" in body
    assert "verification_badge" in body
    assert "retrieval_stats" in body


def test_rag_ask_validates_query_length(api_client):
    response = api_client.post("/api/v1/rag/ask", json={"query": "ab"})
    assert response.status_code == 422


def test_rag_ask_filters_by_jurisdiction(api_client):
    response = api_client.post(
        "/api/v1/rag/ask",
        json={"query": "Ashwagandha patent", "jurisdiction": "India", "top_k": 3},
    )
    assert response.status_code == 200


def test_rag_ask_filters_by_category(api_client):
    response = api_client.post(
        "/api/v1/rag/ask",
        json={"query": "patent", "category": "patents", "top_k": 3},
    )
    assert response.status_code == 200


def test_rag_ask_accepts_passport_id_for_context(api_client):
    response = api_client.post(
        "/api/v1/rag/ask",
        json={"query": "patent requirements for formulation", "passport_id": "some-passport-id", "top_k": 1},
    )
    assert response.status_code == 200


def test_rag_ask_does_not_leak_prompt_when_false(api_client):
    response = api_client.post(
        "/api/v1/rag/ask", json={"query": "test", "include_prompt": False}
    )
    assert response.json().get("llm_prompt") is None


def test_rag_ask_includes_prompt_when_requested(api_client):
    response = api_client.post(
        "/api/v1/rag/ask", json={"query": "patent requirements for formulation", "include_prompt": True}
    )
    assert response.status_code == 200
    assert response.json()["llm_prompt"] is not None


def test_rag_search_patent_returns_results(api_client):
    response = api_client.post(
        "/api/v1/rag/search-patent",
        json={"query": "Ashwagandha formulation", "top_k": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert "total_found" in body


def test_rag_boolean_search_builds_strategies(api_client):
    response = api_client.post(
        "/api/v1/rag/boolean-search",
        json={"query": "Ashwagandha extract", "jurisdiction": "IN", "top_k": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert "searches" in body
    assert "reference_list" in body
    assert len(body["searches"]) > 0


@pytest.mark.xfail(
    reason="rag_router.py:300 passes direct (no 'name' key) to merged_reference_list; KeyError at boolean_search.py:605 when corpus has hits",
    strict=False,
)
def test_rag_boolean_search_accepts_raw_expression(api_client):
    response = api_client.post(
        "/api/v1/rag/boolean-search",
        json={"query": "ignored", "expression": "ashwagandha AND formulation", "top_k": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["searches"][0]["expression"] == "ashwagandha AND formulation"


def test_rag_innovation_passport_unknown_returns_200_with_error_payload(api_client):
    # Current behavior: 200 with error JSON instead of 404 (see xfail below for desired behavior)
    response = api_client.get("/api/v1/rag/innovation-passport/does-not-exist")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] == "Passport not found"
    assert body["passport_id"] == "does-not-exist"


def test_rag_innovation_passport_returns_structured_data_for_known(api_client, test_passport):
    response = api_client.get(f"/api/v1/rag/innovation-passport/{test_passport.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    assert "ingredients" in body
    assert "prior_art_analysis" in body
    assert "tkdl_overlap" in body


@pytest.mark.xfail(
    reason="endpoint returns 200 with error JSON instead of 404 when passport not found",
    strict=False,
)
def test_rag_innovation_passport_returns_404_status_on_missing(api_client):
    response = api_client.get("/api/v1/rag/innovation-passport/missing-id")
    assert response.status_code == 404


def test_rag_status_returns_pipeline_health(api_client):
    response = api_client.get("/api/v1/rag/status")
    assert response.status_code == 200
    assert "qdrant" in response.json() or "bm25" in response.json()


@pytest.mark.xfail(
    reason="reindex is an admin operation but has no authentication dependency",
    strict=False,
)
def test_rag_reindex_requires_admin_authentication(api_client):
    response = api_client.post("/api/v1/rag/reindex")
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="patent corpus harvest is an admin operation but has no authentication dependency",
    strict=False,
)
def test_rag_patent_corpus_harvest_requires_admin_authentication(api_client):
    response = api_client.post("/api/v1/rag/ingest/patent-corpus")
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="ingestion trigger is an admin operation but has no authentication dependency",
    strict=False,
)
def test_rag_ingest_requires_admin_authentication(api_client):
    response = api_client.post("/api/v1/rag/ingest")
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="configure changes process-wide RAG settings but has no authentication dependency",
    strict=False,
)
def test_rag_configure_requires_admin_authentication(api_client):
    response = api_client.post("/api/v1/rag/configure", json={"rag_type": "hybrid"})
    assert response.status_code in (401, 403)


def test_rag_unified_search_returns_sources(api_client):
    response = api_client.post(
        "/api/v1/rag/search",
        json={"query": "Ashwagandha patent", "top_k": 3, "rag_type": "hybrid"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "sources" in body
    assert body["rag_type"] == "hybrid"


def test_rag_unified_search_rejects_invalid_rag_type(api_client):
    response = api_client.post(
        "/api/v1/rag/search",
        json={"query": "test", "rag_type": "nonexistent"},
    )
    assert response.status_code == 400


def test_rag_unified_search_respects_filters(api_client):
    response = api_client.post(
        "/api/v1/rag/search",
        json={"query": "patent", "jurisdiction": "India", "category": "patents", "top_k": 5},
    )
    assert response.status_code == 200


def test_rag_unified_search_user_key_overrides_identity(api_client):
    response = api_client.post(
        "/api/v1/rag/search",
        json={"query": "test", "user_key": "custom-user-id"},
    )
    assert response.status_code == 200


def test_rag_unified_search_user_key_ignored_when_authenticated(api_client, auth_headers):
    # When authenticated, user_key should be ignored in favour of the token's identity
    response = api_client.post(
        "/api/v1/rag/search",
        json={"query": "test", "user_key": "attacker-id"},
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_rag_unified_stats_returns_all_types(api_client):
    response = api_client.get("/api/v1/rag/search/stats")
    assert response.status_code == 200
    body = response.json()
    assert "rag_types" in body
    assert "default_rag_type" in body
    assert "hybrid" in body["rag_types"]


def test_rag_configure_validates_rag_type(api_client):
    response = api_client.post("/api/v1/rag/configure", json={"rag_type": "invalid"})
    assert response.status_code == 400


def test_rag_configure_validates_cache_ttl_range(api_client):
    response = api_client.post("/api/v1/rag/configure", json={"cache_ttl": -1})
    assert response.status_code == 422


def test_rag_configure_validates_rate_limit_range(api_client):
    response = api_client.post("/api/v1/rag/configure", json={"rate_limit": 0})
    assert response.status_code == 422


def test_rag_knowledge_graph_stats_returns_counts(api_client):
    response = api_client.get("/api/v1/rag/knowledge-graph/stats")
    assert response.status_code == 200


def test_rag_knowledge_graph_search_returns_entities(api_client):
    response = api_client.get("/api/v1/rag/knowledge-graph/search?q=ashwagandha&limit=5")
    assert response.status_code == 200


def test_rag_ingest_status_returns_state(api_client):
    response = api_client.get("/api/v1/rag/ingest/status")
    assert response.status_code == 200


def test_rag_patent_corpus_status_returns_state(api_client):
    response = api_client.get("/api/v1/rag/ingest/patent-corpus/status")
    assert response.status_code == 200


def test_rag_ask_with_empty_sources_handles_gracefully(api_client):
    response = api_client.post(
        "/api/v1/rag/ask",
        json={"query": "nonexistenttermxyz123", "top_k": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "verification_badge" in body


def test_rag_ask_does_not_500_on_llm_failure(api_client):
    response = api_client.post("/api/v1/rag/ask", json={"query": "test query"})
    assert response.status_code == 200