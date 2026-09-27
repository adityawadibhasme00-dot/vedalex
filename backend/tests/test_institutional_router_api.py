import pytest

pytestmark = pytest.mark.security


def test_institutional_dashboard_returns_cohort_document(api_client):
    response = api_client.get("/api/v1/institutional/cohort-analytics")
    assert response.status_code == 200
    body = response.json()
    assert body["organization_name"]
    assert isinstance(body["total_active_cases"], int)
    assert isinstance(body["pending_expert_reviews"], int)
    assert 0 <= body["avg_coverage_meter"] <= 100
    assert isinstance(body["cases"], list)
    assert isinstance(body["top_cohort_gaps"], list)


def test_institutional_dashboard_case_rows_are_complete(api_client):
    body = api_client.get("/api/v1/institutional/cohort-analytics").json()
    assert body["cases"]
    for case in body["cases"]:
        assert case["case_id"]
        assert case["startup_name"]
        assert case["product_name"]
        assert isinstance(case["target_markets"], list)
        assert case["target_markets"]
        assert case["current_status"]
        assert 0 <= case["coverage_meter"] <= 100
        assert case["assigned_reviewer"]
        assert case["last_updated"]


def test_institutional_dashboard_gap_rows_are_complete(api_client):
    body = api_client.get("/api/v1/institutional/cohort-analytics").json()
    assert body["top_cohort_gaps"]
    for gap in body["top_cohort_gaps"]:
        assert gap["gap_title"]
        assert gap["affected_startups_count"] > 0
        assert 0 <= gap["percentage"] <= 100
        assert gap["recommended_workshop_action"]


def test_institutional_dashboard_average_coverage_matches_returned_cases(api_client):
    body = api_client.get("/api/v1/institutional/cohort-analytics").json()
    meters = [case["coverage_meter"] for case in body["cases"]]
    assert body["avg_coverage_meter"] == round(sum(meters) / len(meters))


def test_characterization_institutional_dashboard_returns_fixed_cohort(api_client):
    body = api_client.get("/api/v1/institutional/cohort-analytics").json()
    assert [case["case_id"] for case in body["cases"]] == [
        "CASE-AYUR-001",
        "CASE-AYUR-002",
        "CASE-AYUR-003",
    ]
    assert [gap["affected_startups_count"] for gap in body["top_cohort_gaps"]] == [18, 14, 11]


@pytest.mark.xfail(
    reason="institutional_service.py:67 reports total_active_cases=25 while the payload only ever contains the 3 hardcoded rows built at institutional_service.py:12-43; the headline metric is not derived from the returned cohort or from any database query",
    strict=False,
)
def test_institutional_dashboard_totals_match_returned_cases(api_client):
    body = api_client.get("/api/v1/institutional/cohort-analytics").json()
    assert body["total_active_cases"] == len(body["cases"])


@pytest.mark.xfail(
    reason="institutional_router.py:7-9 has no authentication dependency; incubator cohort metrics, startup names and reviewer assignments are served to anonymous callers",
    strict=False,
)
def test_institutional_dashboard_requires_authentication(api_client):
    response = api_client.get("/api/v1/institutional/cohort-analytics")
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="institutional_router.py:7-9 has no role check; an authenticated researcher receives the full multi-tenant cohort dashboard instead of 403",
    strict=False,
)
def test_institutional_dashboard_restricted_to_admin(api_client, auth_headers):
    response = api_client.get(
        "/api/v1/institutional/cohort-analytics", headers=auth_headers
    )
    assert response.status_code == 403
