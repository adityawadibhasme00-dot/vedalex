import pytest

pytestmark = pytest.mark.integration


def test_diff_updates_returns_records_with_full_schema(api_client):
    response = api_client.get("/api/v1/regulatory-diff/updates")
    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)
    assert records
    for record in records:
        assert record["id"]
        assert record["source_authority"]
        assert record["act_title"]
        assert record["prior_version_date"]
        assert record["new_version_date"]
        assert record["summary_of_change"]
        assert isinstance(record["affected_provisions"], list)
        assert record["affected_provisions"]
        assert isinstance(record["affected_case_ids"], list)
        assert record["severity"] in ("LOW", "MEDIUM", "HIGH")


def test_diff_updates_filter_returns_only_matching_case(api_client):
    everything = api_client.get("/api/v1/regulatory-diff/updates").json()
    filtered = api_client.get(
        "/api/v1/regulatory-diff/updates?case_id=case-brahmi-042"
    ).json()
    assert [r["id"] for r in filtered] == ["DIFF-FSSAI-2024-01"]
    assert len(filtered) < len(everything)
    assert all(
        "case-brahmi-042" in r["affected_case_ids"] for r in filtered
    )


def test_diff_updates_filter_returns_all_records_affecting_case(api_client):
    filtered = api_client.get(
        "/api/v1/regulatory-diff/updates?case_id=case-sleep-001"
    ).json()
    assert len(filtered) == 2
    assert all(
        "case-sleep-001" in r["affected_case_ids"] for r in filtered
    )


def test_diff_updates_unknown_case_returns_no_records(api_client):
    filtered = api_client.get(
        "/api/v1/regulatory-diff/updates?case_id=CASE-DOES-NOT-EXIST"
    ).json()
    assert filtered == []


def test_diff_updates_does_not_require_authentication(api_client):
    response = api_client.get("/api/v1/regulatory-diff/updates")
    assert response.status_code == 200


@pytest.mark.xfail(
    reason="GET /regulatory-diff/updates (diff_router.py:8) has no auth or ownership check; affected_case_ids of every user's case are readable anonymously",
    strict=False,
)
def test_diff_updates_requires_authentication(api_client):
    response = api_client.get(
        "/api/v1/regulatory-diff/updates?case_id=case-sleep-001"
    )
    assert response.status_code in (401, 403)


@pytest.mark.xfail(
    reason="empty case_id falls through `if case_id:` (diff_router.py:10) and is treated as 'no filter', returning every record unfiltered",
    strict=False,
)
def test_diff_updates_empty_case_id_is_rejected(api_client):
    response = api_client.get("/api/v1/regulatory-diff/updates?case_id=")
    assert response.status_code == 422
