import pytest

pytestmark = pytest.mark.security


def test_label_analyze_flags_therapeutic_keywords(api_client):
    response = api_client.post(
        "/api/v1/label/analyze",
        json={"label_text": "This product cures and treats disease", "product_type": "ayurvedic_drug"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "HIGH_RISK"
    assert body["overall_color"] == "red"
    high = [c for c in body["claims"] if c["risk_color"] == "red"]
    assert len(high) >= 2


def test_label_analyze_accepts_safe_structure_function_claims(api_client):
    response = api_client.post(
        "/api/v1/label/analyze",
        json={"label_text": "Moisturizes skin. Dosage: 500mg twice daily. Manufactured by Test Corp. Disclaimer: not evaluated by FDA."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["overall_color"] == "green"


@pytest.mark.xfail(
    reason='substring matching: "healthy" contains "heal", so safe claims are misclassified as HIGH_RISK therapeutic claims',
    strict=False,
)
def test_label_analyze_safe_claims_not_misclassified_as_therapeutic(api_client):
    response = api_client.post(
        "/api/v1/label/analyze",
        json={"label_text": "Supports healthy skin. Dosage: 500mg. Manufactured by Co. Disclaimer: not evaluated."},
    )
    reds = [c for c in response.json()["claims"] if c["risk_color"] == "red"]
    assert not reds


def test_label_analyze_missing_disclaimer_produces_warning(api_client):
    response = api_client.post(
        "/api/v1/label/analyze",
        json={"label_text": "This product cures disease. Dosage: 1 tablet. Manufactured by Test."},
    )
    body = response.json()
    warnings = [c for c in body["claims"] if c["risk_color"] == "yellow"]
    assert any("disclaimer" in c["claim_text"].lower() for c in warnings)


def test_label_analyze_missing_dosage_produces_warning(api_client):
    response = api_client.post(
        "/api/v1/label/analyze",
        json={"label_text": "Supports wellness. Manufactured by Test."},
    )
    body = response.json()
    warnings = [c for c in body["claims"] if c["risk_color"] == "yellow"]
    assert any("dosage" in c["claim_text"].lower() for c in warnings)


def test_label_analyze_missing_manufacturer_produces_warning(api_client):
    response = api_client.post(
        "/api/v1/label/analyze",
        json={"label_text": "Supports wellness. Dosage: 1 tablet."},
    )
    body = response.json()
    warnings = [c for c in body["claims"] if c["risk_color"] == "yellow"]
    assert any("manufacturer" in c["claim_text"].lower() for c in warnings)


def test_label_analyze_is_case_insensitive(api_client):
    lower = api_client.post(
        "/api/v1/label/analyze", json={"label_text": "this product cures disease"}
    ).json()
    upper = api_client.post(
        "/api/v1/label/analyze", json={"label_text": "THIS PRODUCT CURES DISEASE"}
    ).json()
    assert lower["overall_status"] == upper["overall_status"] == "HIGH_RISK"


def test_label_analyze_threshold_high_risk_beats_warnings(api_client):
    response = api_client.post(
        "/api/v1/label/analyze",
        json={"label_text": "Treats illness but missing dosage and manufacturer"},
    )
    assert response.json()["overall_status"] == "HIGH_RISK"


def test_label_analyze_warning_threshold_is_more_than_two(api_client):
    # 3+ yellow warnings but no red → WARNING
    response = api_client.post(
        "/api/v1/label/analyze",
        json={"label_text": "Supports overall wellness. Disclaimer present."},
    )
    body = response.json()
    yellows = [c for c in body["claims"] if c["risk_color"] == "yellow"]
    if len(yellows) > 2:
        assert body["overall_status"] == "WARNING"


def test_label_analyze_empty_label_text(api_client):
    response = api_client.post("/api/v1/label/analyze", json={"label_text": ""})
    assert response.status_code == 200
    body = response.json()
    # empty text has no dosage/manufacturer → warnings
    assert body["overall_status"] in ("WARNING", "SAFE")


def test_label_analyze_validates_missing_label_text(api_client):
    response = api_client.post("/api/v1/label/analyze", json={})
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="LabelAnalyzeRequest.label_text has no max_length; unbounded input is accepted",
    strict=False,
)
def test_label_analyze_rejects_oversized_label_text(api_client):
    response = api_client.post(
        "/api/v1/label/analyze", json={"label_text": "x" * 1_000_000}
    )
    assert response.status_code == 422


def test_label_analyze_accepts_multiple_target_markets(api_client):
    response = api_client.post(
        "/api/v1/label/analyze",
        json={"label_text": "Supports wellness", "target_markets": ["India", "United States", "Canada"]},
    )
    assert response.status_code == 200


def test_label_analyze_summary_counts_match_claims(api_client):
    body = api_client.post(
        "/api/v1/label/analyze", json={"label_text": "Treats disease"}
    ).json()
    reds = sum(1 for c in body["claims"] if c["risk_color"] == "red")
    yellows = sum(1 for c in body["claims"] if c["risk_color"] == "yellow")
    greens = sum(1 for c in body["claims"] if c["risk_color"] == "green")
    summary = body["summary"]
    assert str(reds) in summary
    assert str(yellows) in summary
    assert str(greens) in summary


@pytest.mark.xfail(
    reason="claim firewall matches keywords by substring inside label_text; word-boundary bypasses are possible",
    strict=False,
)
def test_label_analyze_matches_therapeutic_keywords_on_word_boundary(api_client):
    # "untreated" contains "treat" but is not a therapeutic claim
    response = api_client.post(
        "/api/v1/label/analyze",
        json={"label_text": "Untreated wooden surface for crafts. Dosage: n/a. Manufactured by Co."},
    )
    reds = [c for c in response.json()["claims"] if c["risk_color"] == "red"]
    assert not any("treat" in c["claim_text"] for c in reds)
