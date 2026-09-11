import json
import os
from typing import Dict, List, Any

from app.models.intelligence import (
    BioResourceGraphResponse,
    BioResourcePlant,
    GeoOrigin,
)
from app.services.passport_engine import PassportEngine

_KNOWLEDGE = os.path.join(os.path.dirname(__file__), "..", "knowledge")

NON_REGIONAL = {"sanskrit", "hindi", "marathi", "bengali", "gujarati", "english"}


class BioResourceEngine:
    """
    Bio-Resource Intelligence Graph (USP: Medicinal Plant Intelligence).
    Per-plant graph: identity + Ayurvedic names + plant part + geography/provenance +
    conservation/trade + TK + ABS + IP + evidence bridge. All sourced from curated
    knowledge datasets (NMPB/e-Charak, NBA, TKDL, API monograph framing).
    """

    _bioresource: Dict[str, Dict[str, Any]] = {}
    _synonyms: Dict[str, Dict[str, Any]] = {}
    _ladders: Dict[str, Dict[str, Any]] = {}

    DISCLAIMER = (
        "Bio-resource intelligence reflects curated datasets (NMPB trade guidance, NBA ABS framework, TKDL, "
        "API monographs) at assessment time and is decision support, not a legal ABS or export opinion."
    )

    @classmethod
    def load_data(cls):
        if not cls._bioresource:
            path = os.path.join(_KNOWLEDGE, "bioresource.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._bioresource = {item["canonical_id"]: item for item in json.load(f)}
        if not cls._synonyms:
            path = os.path.join(_KNOWLEDGE, "botanical_synonyms.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._synonyms = json.load(f)
        if not cls._ladders:
            path = os.path.join(_KNOWLEDGE, "evidence_ladders.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._ladders = {item["canonical_id"]: item for item in json.load(f)}

    @classmethod
    def _evidence_support_pct(cls, canonical_id: str) -> int:
        entry = cls._ladders.get(canonical_id)
        if not entry:
            return 0
        cells = entry.get("ladder", [])
        return int(sum(c.get("support_pct", 0) for c in cells) / len(cells)) if cells else 0

    @classmethod
    def _plant(cls, canonical_id: str) -> BioResourcePlant:
        bio = cls._bioresource.get(canonical_id, {})
        syn = cls._synonyms.get(canonical_id, {})

        ayurvedic: Dict[str, List[str]] = {}
        regional: Dict[str, List[str]] = {}
        english: List[str] = []
        for lang, names in syn.items():
            if lang == "canonical_id" or lang == "botanical_name":
                continue
            if lang == "english":
                english = names
            elif lang in NON_REGIONAL:
                ayurvedic[lang] = names
            else:
                regional[lang] = names

        geography = [GeoOrigin(**g) for g in bio.get("geography", [])]

        return BioResourcePlant(
            canonical_id=canonical_id,
            botanical_name=bio.get("botanical_name") or syn.get("botanical_name") or canonical_id,
            family=bio.get("family", ""),
            api_monograph_id=bio.get("api_monograph_id", ""),
            plant_parts=bio.get("plant_parts", []),
            ayurvedic_names=ayurvedic,
            regional_synonyms=regional,
            english_names=english,
            geography=geography,
            conservation_status=bio.get("conservation_status", ""),
            trade_demand_class=bio.get("trade_demand_class", ""),
            price_trend_note=bio.get("price_trend_note", ""),
            provenance_options=bio.get("provenance_options", []),
            abs_considerations=bio.get("abs_considerations", []),
            tk_considerations=bio.get("tk_considerations", []),
            ip_considerations=bio.get("ip_considerations", []),
            evidence_support_pct=cls._evidence_support_pct(canonical_id),
        )

    @classmethod
    def build(cls, passport_id: str) -> BioResourceGraphResponse:
        cls.load_data()
        passport = PassportEngine.get_passport(passport_id)
        if passport is None:
            return BioResourceGraphResponse(
                passport_id=passport_id,
                plants=[],
                recommendations=["No resolved passport found. Create an Innovation Passport first."],
                disclaimer=cls.DISCLAIMER,
            )

        canonical_ids: List[str] = []
        for ing in passport.ingredients:
            if ing.canonical_id and ing.canonical_id not in canonical_ids:
                canonical_ids.append(ing.canonical_id)

        if not canonical_ids:
            return BioResourceGraphResponse(
                passport_id=passport_id,
                plants=[],
                recommendations=["No resolved botanical ingredients found in the passport."],
                disclaimer=cls.DISCLAIMER,
            )

        plants = [cls._plant(cid) for cid in canonical_ids]

        recommendations: List[str] = []
        pending_provenance = [p.botanical_name for p in plants if any(g.status != "verified" for g in p.geography)]
        if pending_provenance:
            recommendations.append(
                "Complete provenance verification for: " + ", ".join(pending_provenance) +
                " (supplier declarations, GPS/plot records, and NBA-exempt commodity checks)."
            )
        recommendations.append(
            "File/maintain ABS records under the Biological Diversity Act (as amended 2023) for any wild-collected "
            "or non-exempt resource before commercial use."
        )
        recommendations.append(
            "Expect TKDL/classical prior art for standard uses; restrict patent filings to demonstrated combinations, "
            "ratios, or process markers with supporting evidence."
        )

        return BioResourceGraphResponse(
            passport_id=passport_id,
            plants=plants,
            recommendations=recommendations,
            disclaimer=cls.DISCLAIMER,
        )