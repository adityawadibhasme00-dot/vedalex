import pytest

pytestmark = pytest.mark.integration


def test_formulation_parse_resolves_known_ingredients(api_client):
    response = api_client.post(
        "/api/v1/formulation/parse", json={"text": "Ashwagandha, Brahmi"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["detected_language"] == "en"
    assert body["raw_text"] == "Ashwagandha, Brahmi"
    assert body["unresolved"] == []
    ids = {i["canonical_id"] for i in body["ingredients"]}
    assert ids == {"ING-ASHWAGANDHA", "ING-BRAHMI"}
    for ingredient in body["ingredients"]:
        assert ingredient["status"] == "resolved"
        assert ingredient["botanical_name"]
        assert ingredient["api_monograph_id"]
        assert ingredient["confidence"] >= 0.9


def test_formulation_parse_strips_quantities_and_preparation_words(api_client):
    body = api_client.post(
        "/api/v1/formulation/parse",
        json={"text": "Ashwagandha powder 500mg and Brahmi extract 250 mg"},
    ).json()
    raw_names = [i["raw_name"] for i in body["ingredients"]]
    assert raw_names
    assert not any("mg" in name.lower() for name in raw_names)
    assert not any("powder" in name.lower() for name in raw_names)
    assert not any("extract" in name.lower() for name in raw_names)
    ids = {i["canonical_id"] for i in body["ingredients"]}
    assert ids == {"ING-ASHWAGANDHA", "ING-BRAHMI"}


def test_formulation_parse_reports_unresolved_tokens(api_client):
    body = api_client.post(
        "/api/v1/formulation/parse",
        json={"text": "Ashwagandha and zorblatt berry"},
    ).json()
    assert "zorblatt berry" in body["unresolved"]
    unresolved = [
        i for i in body["ingredients"] if i["raw_name"] == "zorblatt berry"
    ]
    assert len(unresolved) == 1
    assert unresolved[0]["status"] == "unresolved"
    assert unresolved[0]["canonical_id"] is None


def test_formulation_parse_deduplicates_repeated_mentions(api_client):
    body = api_client.post(
        "/api/v1/formulation/parse",
        json={"text": "Ashwagandha and Ashwagandha and ashwagandha"},
    ).json()
    assert len(body["ingredients"]) == 1
    assert body["ingredients"][0]["canonical_id"] == "ING-ASHWAGANDHA"


def test_formulation_parse_detects_hindi_text(api_client):
    body = api_client.post(
        "/api/v1/formulation/parse", json={"text": "अश्वगंधा"}
    ).json()
    assert body["detected_language"] == "hi"
    assert body["ingredients"]
    assert body["ingredients"][0]["canonical_id"] == "ING-ASHWAGANDHA"
    assert body["ingredients"][0]["detected_language"] == "hi"


def test_formulation_parse_missing_text_returns_422(api_client):
    response = api_client.post("/api/v1/formulation/parse", json={})
    assert response.status_code == 422


def test_formulation_parse_rejects_non_string_text(api_client):
    response = api_client.post("/api/v1/formulation/parse", json={"text": 7})
    assert response.status_code == 422


def test_characterization_formulation_parse_accepts_empty_text(api_client):
    response = api_client.post("/api/v1/formulation/parse", json={"text": ""})
    assert response.status_code == 200
    body = response.json()
    assert body["ingredients"] == []
    assert body["unresolved"] == []
    assert body["detected_language"] == "en"


def test_formulation_parse_does_not_require_authentication(api_client):
    response = api_client.post(
        "/api/v1/formulation/parse", json={"text": "Ashwagandha"}
    )
    assert response.status_code == 200


@pytest.mark.xfail(
    reason="matched_ids is keyed on the raw token text instead of the canonical id (formulation_router.py:90,103), so two synonyms of one plant produce duplicate canonical entries",
    strict=False,
)
def test_formulation_parse_deduplicates_by_canonical_id(api_client):
    body = api_client.post(
        "/api/v1/formulation/parse",
        json={"text": "Ashwagandha and Indian Ginseng"},
    ).json()
    ids = [i["canonical_id"] for i in body["ingredients"]]
    assert len(ids) == len(set(ids))


@pytest.mark.xfail(
    reason='ParsedIngredient.status declares a "quantity_only" state (formulation_router.py:24) that is never emitted; bare quantity tokens are silently dropped',
    strict=False,
)
def test_formulation_parse_reports_quantity_only_fragments(api_client):
    body = api_client.post(
        "/api/v1/formulation/parse", json={"text": "Ashwagandha, 500 mg"}
    ).json()
    statuses = {i["status"] for i in body["ingredients"]}
    assert "quantity_only" in statuses


@pytest.mark.xfail(
    reason="FormulationParseRequest.language is accepted but never read or validated (formulation_router.py:12)",
    strict=False,
)
def test_formulation_parse_validates_language(api_client):
    response = api_client.post(
        "/api/v1/formulation/parse",
        json={"text": "Ashwagandha", "language": "klingon"},
    )
    assert response.status_code == 422
