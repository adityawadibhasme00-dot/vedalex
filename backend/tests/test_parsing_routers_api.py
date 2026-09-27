import pytest

pytestmark = pytest.mark.integration


# --------------------------------------------------------------------------
# Formulation parsing
# --------------------------------------------------------------------------

def test_formulation_parse_resolves_known_ingredients(api_client):
    response = api_client.post(
        "/api/v1/formulation/parse", json={"text": "Ashwagandha and Brahmi"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ingredients"]
    resolved = [i for i in body["ingredients"] if i["status"] == "resolved"]
    assert resolved
    assert any(i["canonical_id"] for i in resolved)
    assert all(i["detected_language"] for i in body["ingredients"])


def test_formulation_parse_reports_unresolved_tokens(api_client):
    response = api_client.post(
        "/api/v1/formulation/parse", json={"text": "Zzqxprobable substance"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["unresolved"]
    assert any(i["status"] == "unresolved" for i in body["ingredients"])


def test_formulation_parse_strips_quantity_suffixes(api_client):
    response = api_client.post(
        "/api/v1/formulation/parse", json={"text": "Ashwagandha 500mg, Brahmi 10 g"}
    )
    assert response.status_code == 200
    raw_names = [i["raw_name"].lower() for i in response.json()["ingredients"]]
    assert not any("500mg" in name for name in raw_names)


def test_formulation_parse_deduplicates_tokens(api_client):
    response = api_client.post(
        "/api/v1/formulation/parse", json={"text": "Ashwagandha, Ashwagandha, ashwagandha"}
    )
    assert response.status_code == 200
    ashwagandha = [
        i for i in response.json()["ingredients"] if "ashwagandha" in i["raw_name"].lower()
    ]
    assert len(ashwagandha) == 1


def test_formulation_parse_empty_text_returns_empty(api_client):
    response = api_client.post("/api/v1/formulation/parse", json={"text": ""})
    assert response.status_code == 200
    body = response.json()
    assert body["ingredients"] == []
    assert body["unresolved"] == []
    assert body["raw_text"] == ""


def test_formulation_parse_missing_text_returns_422(api_client):
    response = api_client.post("/api/v1/formulation/parse", json={})
    assert response.status_code == 422


def test_formulation_parse_echoes_language_parameter(api_client):
    response = api_client.post(
        "/api/v1/formulation/parse", json={"text": "Ashwagandha", "language": "hi"}
    )
    assert response.status_code == 200
    assert response.json()["detected_language"]


# --------------------------------------------------------------------------
# Botanical canonicalization
# --------------------------------------------------------------------------

def test_botanical_canonicalize_resolves_known_ingredient(api_client):
    response = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "Ashwagandha"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["raw_input"] == "Ashwagandha"
    assert body["canonical_id"] == "ING-ASHWAGANDHA"
    assert "Withania" in body["botanical_name"]
    assert body["confidence"] > 0
    assert set(body["regulatory_status"]) == {
        "fssai_aahara",
        "us_fda_ndi",
        "canada_nhpid",
    }
    assert body["detected_language"]


def test_botanical_canonicalize_unknown_returns_low_confidence(api_client):
    response = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "qqzzxx nonexistens"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["canonical_id"] is None
    assert body["confidence"] == 0.0


def test_botanical_canonicalize_missing_raw_name_returns_422(api_client):
    response = api_client.post("/api/v1/botanical/canonicalize", json={})
    assert response.status_code == 422


def test_botanical_canonicalize_is_case_insensitive(api_client):
    lower = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "ashwagandha"}
    ).json()
    upper = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "ASHWAGANDHA"}
    ).json()
    assert lower["canonical_id"] == upper["canonical_id"] == "ING-ASHWAGANDHA"
