import pytest

pytestmark = pytest.mark.integration

READINESS_COMPONENT_CODES = {
    "novelty",
    "prior_art",
    "section3p",
    "disclosure",
    "evidence",
    "ownership",
    "fto",
    "documentation",
}


def test_patent_readiness_returns_structured_result(api_client, test_passport):
    response = api_client.get(
        f"/api/v1/analysis/readiness/{test_passport.id}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passport_id"] == test_passport.id
    assert 0 <= body["overall_readiness"] <= 100
    assert body["overall_pct"] == body["overall_readiness"]
    assert body["patent_ready"] == (body["overall_readiness"] >= 70)
    assert isinstance(body["strengths"], list)
    assert isinstance(body["weaknesses"], list)
    assert body["strengths"] or body["weaknesses"]
    assert body["next_actions"]
    assert isinstance(body["recommendations"], list)
    assert isinstance(body["missing_evidence"], list)


def test_patent_readiness_components_are_complete(api_client, test_passport):
    body = api_client.get(
        f"/api/v1/analysis/readiness/{test_passport.id}"
    ).json()
    components = body["components"]
    assert len(components) == 8
    assert {c["code"] for c in components} == READINESS_COMPONENT_CODES
    for component in components:
        assert 0 <= component["earned"] <= component["max"]
        assert component["max"] > 0
        assert 0 <= component["pct"] <= 100
        assert component["status"] in ("good", "warn", "risk")


def test_patent_readiness_component_scores_sum_to_overall(
    api_client, test_passport
):
    body = api_client.get(
        f"/api/v1/analysis/readiness/{test_passport.id}"
    ).json()
    total = round(sum(c["earned"] for c in body["components"]), 1)
    assert total == body["overall_readiness"]


def test_patent_readiness_reports_risk_and_prior_art(api_client, test_passport):
    body = api_client.get(
        f"/api/v1/analysis/readiness/{test_passport.id}"
    ).json()
    assert body["section3p_risk"] in ("Low", "Medium", "High")
    assert body["disclosure_risk"] in ("Low", "Medium", "High")
    assert 0 <= body["prior_art_overlap"] <= 100
    assert 0 <= body["fto_overlap"] <= 100
    assert isinstance(body["similar_patents"], list)
    for patent in body["similar_patents"]:
        assert patent["patent_id"]
        assert patent["title"]
        assert 0 <= patent["similarity"] <= 100


def test_patent_readiness_unknown_passport_returns_404(api_client):
    response = api_client.get("/api/v1/analysis/readiness/no-such-passport")
    assert response.status_code == 404
    assert response.json()["detail"] == "Passport not found"


def test_patent_readiness_does_not_require_authentication(
    api_client, test_passport
):
    response = api_client.get(
        f"/api/v1/analysis/readiness/{test_passport.id}"
    )
    assert response.status_code == 200


@pytest.mark.xfail(
    reason="GET /analysis/readiness/{passport_id} (patent_router.py:12) never resolves the current user or checks the passport owner",
    strict=False,
)
def test_patent_readiness_enforces_ownership(
    api_client, test_passport, other_auth_headers
):
    response = api_client.get(
        f"/api/v1/analysis/readiness/{test_passport.id}",
        headers=other_auth_headers,
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="GET /analysis/readiness/{passport_id} (patent_router.py:12) has no authentication requirement; the readiness report of any passport id is readable anonymously",
    strict=False,
)
def test_patent_readiness_requires_authentication(api_client, test_passport):
    response = api_client.get(
        f"/api/v1/analysis/readiness/{test_passport.id}"
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="readiness output (patent_router.py:18) contains no citations or source links backing the prior-art and section 3(p) findings",
    strict=False,
)
def test_patent_readiness_includes_citations(api_client, test_passport):
    body = api_client.get(
        f"/api/v1/analysis/readiness/{test_passport.id}"
    ).json()
    assert body.get("citations") or body.get("sources")
