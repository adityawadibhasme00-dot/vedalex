"""Tests for CITES schedule knowledge and bio-resource enforcement."""

import json
import os

from app.services.bio_resource_engine import BioResourceEngine
from app.services.passport_engine import PassportEngine

KNOWLEDGE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "app", "knowledge"
)


def _cites_plants():
    with open(os.path.join(KNOWLEDGE_DIR, "cites.json"), encoding="utf-8") as f:
        return json.load(f)["plants"]


def test_cites_dataset_has_meta_and_unique_latin_names():
    data = json.load(open(os.path.join(KNOWLEDGE_DIR, "cites.json"), encoding="utf-8"))
    plants = data["plants"]
    latin = [p["latin_name"] for p in plants]
    assert len(latin) == len(set(latin)), "CITES latin_name must be unique"
    assert "appendices_valid_from" in data.get("_meta", {})
    for p in plants:
        assert p["appendix"] in ("I", "II")
        assert p["permit_requirement"]
        assert p["impact"]


def test_cites_schedule_known_key_species():
    by_name = {p["latin_name"]: p for p in _cites_plants()}
    assert by_name["Saussurea costus"]["appendix"] == "I"
    assert by_name["Rauvolfia serpentina"]["appendix"] == "II"
    assert by_name["Nardostachys grandiflora"]["appendix"] == "II"
    assert by_name["Picrorhiza kurrooa"]["appendix"] == "II"
    assert by_name["Taxus wallichiana"]["appendix"] == "II"
    assert by_name["Aquilaria malaccensis"]["appendix"] == "II"


def test_lookup_cites_by_latin_name():
    hit = BioResourceEngine.lookup_cites("Rauvolfia serpentina (L.) Benth. ex Kurz")
    assert hit and hit["latin_name"] == "Rauvolfia serpentina"
    assert hit["appendix"] == "II"


def test_lookup_cites_by_vernacular_name():
    hit = BioResourceEngine.lookup_cites("Sarpagandha")
    assert hit is not None
    assert hit["latin_name"] == "Rauvolfia serpentina"
    alt = BioResourceEngine.lookup_cites("Indian Snakeroot")
    assert alt is not None
    assert alt["latin_name"] == "Rauvolfia serpentina"


def test_lookup_cites_returns_none_for_unlisted():
    assert BioResourceEngine.lookup_cites("Withania somnifera") is None


def _sarpagandha_passport():
    return PassportEngine.create_from_intake(
        raw_text="Sarpagandha root used for hypertension and anxiety support",
        user_lang="en",
    )


def test_bio_resource_graph_attaches_cites_and_enforces():
    passport = _sarpagandha_passport()
    graph = BioResourceEngine.build(passport.id)
    assert len(graph.plants) == 1
    plant = graph.plants[0]
    assert plant.cites is not None
    assert plant.cites.appendix == "II"
    assert plant.cites.permit_requirement
    assert any("CITES Appendix II" in r for r in graph.recommendations)
    assert any("CITES:" in r for r in graph.recommendations)
    assert any("CITES Annex" in r for r in graph.recommendations)


def test_bio_resource_no_cites_when_unlisted():
    passport = PassportEngine.create_from_intake(
        raw_text="Ashwagandha root for stress support", user_lang="en"
    )
    graph = BioResourceEngine.build(passport.id)
    assert graph.plants and graph.plants[0].cites is None
    assert not any("CITES" in r for r in graph.recommendations)