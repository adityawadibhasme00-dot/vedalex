import pytest

from app.services.passport_engine import PassportEngine

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolate_passport_store():
    PassportEngine._passports_store.clear()
    yield
    PassportEngine._passports_store.clear()


# --------------------------------------------------------------------------
# Claim safety
# --------------------------------------------------------------------------

def test_claim_safety_flags_curative_claim(api_client):
    response = api_client.post(
        "/api/v1/intelligence/claim-safety/analyze",
        json={"claims": ["Cures diabetes"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["overall_verdict"] == "HIGH_RISK"
    assert body["overall_color"] == "red"
    assert body["claims"][0]["risk_level"] == "HIGH_RISK"


def test_claim_safety_accepts_safe_claim(api_client):
    response = api_client.post(
        "/api/v1/intelligence/claim-safety/analyze",
        json={"claims": ["Supports healthy sleep"]},
    )
    assert response.status_code == 200
    assert response.json()["overall_verdict"]


def test_claim_safety_defaults_when_no_claims_supplied(api_client):
    response = api_client.post(
        "/api/v1/intelligence/claim-safety/analyze", json={}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["claims"]
    assert body["overall_verdict"]


def test_claim_safety_pulls_claims_from_passport(api_client, test_passport):
    response = api_client.post(
        "/api/v1/intelligence/claim-safety/analyze",
        json={"passport_id": test_passport.id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    assert body["claims"]


def test_claim_safety_respects_target_markets(api_client):
    response = api_client.post(
        "/api/v1/intelligence/claim-safety/analyze",
        json={"claims": ["Supports immunity"], "target_markets": ["United States"]},
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------
# Evidence quality / bio resource / export readiness / knowledge graph
# --------------------------------------------------------------------------

def test_evidence_quality_returns_empty_for_unknown_passport(api_client):
    # No 404 for unknown ids — endpoints answer with empty results
    response = api_client.get("/api/v1/intelligence/evidence-quality/unknown-id")
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == "unknown-id"
    assert body["ingredients"] == []
    assert body["overall_evidence_support_pct"] == 0


def test_evidence_quality_returns_analysis_for_known_passport(api_client, test_passport):
    response = api_client.get(
        f"/api/v1/intelligence/evidence-quality/{test_passport.id}"
    )
    assert response.status_code == 200
    assert response.json()["passport_id"] == test_passport.id


def test_bio_resource_returns_empty_for_unknown_passport(api_client):
    response = api_client.get("/api/v1/intelligence/bio-resource/unknown-id")
    assert response.status_code == 200
    body = response.json()
    assert body["plants"] == []
    assert body["recommendations"]


def test_export_readiness_returns_empty_for_unknown_passport(api_client):
    response = api_client.get("/api/v1/intelligence/export-readiness/unknown-id")
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == "unknown-id"
    assert "No resolved" in body["summary"]


def test_knowledge_graph_get_returns_empty_for_unknown_passport(api_client):
    response = api_client.get("/api/v1/intelligence/knowledge-graph/unknown-id")
    assert response.status_code == 200
    body = response.json()
    assert body["nodes"] == []
    assert body["edges"] == []


def test_knowledge_graph_post_resolves_ingredients(api_client):
    response = api_client.post(
        "/api/v1/intelligence/knowledge-graph", json={"ingredients": ["Ashwagandha"]}
    )
    assert response.status_code == 200
    body = response.json()
    ingredients = body["selected_innovation"]["ingredients"]
    assert any(i["canonical_id"] == "ING-ASHWAGANDHA" for i in ingredients)


# --------------------------------------------------------------------------
# Product classifier / ABS / terminology
# --------------------------------------------------------------------------

def test_product_classify_returns_pathway(api_client):
    response = api_client.post(
        "/api/v1/intelligence/product-classify",
        json={"product_name": "Ashwagandha churna"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["product_name"] == "Ashwagandha churna"
    assert body["likely_pathway"]
    assert body["intent_detected"]


def test_abs_check_returns_compliance_status(api_client):
    response = api_client.post(
        "/api/v1/intelligence/abs/check",
        json={"ingredients": ["Ashwagandha"], "turnover_inr": 5_000_000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("compliance_required", "exempt", "benefit_sharing")
    assert body["user_type"] == "company"


def test_abs_check_handles_wild_collected_flag(api_client):
    response = api_client.post(
        "/api/v1/intelligence/abs/check",
        json={"ingredients": ["Ashwagandha"], "wild_collected": True, "turnover_inr": 1000},
    )
    assert response.status_code == 200


def test_terminology_map_matches_known_ingredient(api_client):
    response = api_client.post(
        "/api/v1/intelligence/terminology/map", json={"query": "ashwagandha"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is True
    assert body["canonical_id"] == "ING-ASHWAGANDHA"
    assert body["botanical_name"]


def test_terminology_map_returns_unmatched_for_unknown_query(api_client):
    response = api_client.post(
        "/api/v1/intelligence/terminology/map", json={"query": "zzqqxx not an herb"}
    )
    assert response.status_code == 200
    assert "matched" in response.json()


def test_terminology_map_missing_query_returns_422(api_client):
    response = api_client.post("/api/v1/intelligence/terminology/map", json={})
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="intelligence passport endpoints accept any passport_id with no auth or ownership check",
    strict=False,
)
@pytest.mark.parametrize(
    "path_template",
    [
        "/api/v1/intelligence/evidence-quality/{pid}",
        "/api/v1/intelligence/bio-resource/{pid}",
        "/api/v1/intelligence/export-readiness/{pid}",
        "/api/v1/intelligence/knowledge-graph/{pid}",
    ],
)
def test_intelligence_passport_endpoints_enforce_ownership(
    api_client, test_passport, other_auth_headers, path_template
):
    response = api_client.get(
        path_template.format(pid=test_passport.id), headers=other_auth_headers
    )
    assert response.status_code in (401, 403)
