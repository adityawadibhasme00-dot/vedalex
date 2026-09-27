import pytest

pytestmark = pytest.mark.integration


def test_botanical_canonicalize_resolves_known_ingredient(api_client):
    response = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "Ashwagandha"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["raw_input"] == "Ashwagandha"
    assert body["detected_language"] == "en"
    assert body["canonical_id"] == "ING-ASHWAGANDHA"
    assert body["botanical_name"] == "Withania somnifera (L.) Dunal"
    assert body["family"] == "Solanaceae"
    assert body["api_monograph_id"]
    assert body["confidence"] >= 0.9


def test_botanical_canonicalize_returns_full_metadata(api_client):
    body = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "Tulsi"}
    ).json()
    assert body["canonical_id"] == "ING-TULSI"
    assert body["plant_parts"]
    assert body["therapeutic_uses"]
    assert set(body["regulatory_status"]) == {
        "fssai_aahara",
        "us_fda_ndi",
        "canada_nhpid",
    }
    assert all(
        isinstance(value, str) and value
        for value in body["regulatory_status"].values()
    )


def test_botanical_canonicalize_resolves_hindi_name(api_client):
    body = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "अश्वगंधा"}
    ).json()
    assert body["detected_language"] == "hi"
    assert body["canonical_id"] == "ING-ASHWAGANDHA"
    assert body["confidence"] >= 0.9


def test_botanical_canonicalize_resolves_variant_synonym(api_client):
    body = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "Haldi"}
    ).json()
    assert body["canonical_id"] == "ING-HARIDRA"
    assert body["botanical_name"] == "Curcuma longa L."


def test_botanical_canonicalize_unknown_name_returns_zero_confidence(api_client):
    response = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "zzzz-not-a-plant"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["canonical_id"] is None
    assert body["botanical_name"] is None
    assert body["api_monograph_id"] is None
    assert body["confidence"] == 0.0


def test_botanical_canonicalize_missing_raw_name_returns_422(api_client):
    response = api_client.post("/api/v1/botanical/canonicalize", json={})
    assert response.status_code == 422


def test_botanical_canonicalize_rejects_non_string_raw_name(api_client):
    response = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": 42}
    )
    assert response.status_code == 422


def test_characterization_botanical_canonicalize_accepts_empty_raw_name(api_client):
    response = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": ""}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["canonical_id"] is None
    assert body["confidence"] == 0.0


def test_botanical_canonicalize_does_not_require_authentication(api_client):
    response = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "Ashwagandha"}
    )
    assert response.status_code == 200


@pytest.mark.xfail(
    reason="CanonicalizeRequest.source_language is accepted but never read or validated (botanical_router.py:11)",
    strict=False,
)
def test_botanical_canonicalize_validates_source_language(api_client):
    response = api_client.post(
        "/api/v1/botanical/canonicalize",
        json={"raw_name": "Ashwagandha", "source_language": "klingon"},
    )
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="CanonicalizeRequest.raw_name has no max_length (botanical_router.py:10); unbounded payloads are accepted",
    strict=False,
)
def test_botanical_canonicalize_rejects_oversized_raw_name(api_client):
    response = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "x" * 100_000}
    )
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="botanical aliases are matched with re.search and no word boundary (multilingual_nlp.py:85), so 'Tulsidas' canonicalizes as Tulsi",
    strict=False,
)
def test_botanical_canonicalize_matches_whole_words_only(api_client):
    response = api_client.post(
        "/api/v1/botanical/canonicalize", json={"raw_name": "Tulsidas"}
    )
    assert response.status_code == 200
    assert response.json()["canonical_id"] is None
