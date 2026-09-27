import json
import os
import re
from typing import Any

from app.models.intelligence import (
    BioResourceGraphResponse,
    BioResourcePlant,
    CITESSchedule,
    GeoOrigin,
)
from app.services.passport_engine import PassportEngine

_KNOWLEDGE = os.path.join(os.path.dirname(__file__), "..", "knowledge")

NON_REGIONAL = {"sanskrit", "hindi", "marathi", "bengali", "gujarati", "english"}


def _norm_latin(name: str) -> str:
    """Normalise a botanical (or vernacular) name for CITES matching:
    lowercase, strip author citations, comparator words and trailing ssp./var."""
    name = name.lower()
    name = re.sub(r"\([^)]*\)", "", name)
    name = re.split(r"\b(ssp\.?|subsp\.?|var\.?|x)\b", name)[0].strip()
    name = re.sub(r"[^a-z\s-]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _latin_tokens(name: str) -> set:
    return set(_norm_latin(name).split())


class BioResourceEngine:
    """
    Bio-Resource Intelligence Graph (USP: Medicinal Plant Intelligence).
    Per-plant graph: identity + Ayurvedic names + plant part + geography/provenance +
    conservation/trade + TK + ABS + IP + evidence bridge. All sourced from curated
    knowledge datasets (NMPB/e-Charak, NBA, TKDL, API monograph framing).
    """

    _bioresource: dict[str, dict[str, Any]] = {}
    _synonyms: dict[str, dict[str, Any]] = {}
    _ladders: dict[str, dict[str, Any]] = {}
    _cites: list[dict[str, Any]] = []

    DISCLAIMER = (
        "Bio-resource intelligence reflects curated datasets (NMPB trade guidance, NBA ABS framework, TKDL, "
        "API monographs) at assessment time and is decision support, not a legal ABS or export opinion."
    )

    @classmethod
    def load_data(cls):
        if not cls._bioresource:
            path = os.path.join(_KNOWLEDGE, "bioresource.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    cls._bioresource = {item["canonical_id"]: item for item in json.load(f)}
        if not cls._synonyms:
            path = os.path.join(_KNOWLEDGE, "botanical_synonyms.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    cls._synonyms = json.load(f)
        if not cls._ladders:
            path = os.path.join(_KNOWLEDGE, "evidence_ladders.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    cls._ladders = {item["canonical_id"]: item for item in json.load(f)}
        if not cls._cites:
            path = os.path.join(_KNOWLEDGE, "cites.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    cls._cites = json.load(f).get("plants", [])

    @classmethod
    def lookup_cites(cls, botanical_name: str) -> dict[str, Any] | None:
        """Resolve a botanical (or vernacular) name against the curated CITES
        schedule dataset using normalised Latin-token matching."""
        cls.load_data()
        if not botanical_name:
            return None
        name = _norm_latin(botanical_name)
        if not name:
            return None
        tokens = _latin_tokens(name)
        for entry in cls._cites:
            subjects = [entry.get("latin_name", "")] + entry.get("synonyms", [])
            for subject in subjects:
                s_tokens = _latin_tokens(subject)
                if not s_tokens:
                    continue
                # genus + species epithet must both be present & exact
                if (s_tokens.issubset(tokens) or tokens.issubset(s_tokens)) and s_tokens & tokens:
                    # require at least a genus epithet (>=2 token) or full binomial
                    union = s_tokens & tokens
                    if len(union) >= 2 or len(union) == len(s_tokens):
                        return entry
        # vernacular fallback (ayurvedic/common names)
        norm = _norm_latin(botanical_name)
        for entry in cls._cites:
            for alias in entry.get("ayurvedic_names", []):
                cand = _norm_latin(alias)
                if cand and (cand == norm or len(cand) >= 4 and cand in norm):
                    return entry
        return None

    @classmethod
    def _attach_cites(cls, plant: BioResourcePlant) -> BioResourcePlant:
        entry = cls.lookup_cites(plant.botanical_name)
        if entry is None:
            return plant
        plant.cites = CITESSchedule(
            latin_name=entry.get("latin_name", plant.botanical_name),
            synonyms=entry.get("synonyms", []),
            ayurvedic_names=entry.get("ayurvedic_names", []),
            appendix=entry.get("appendix", ""),
            annotation=entry.get("annotation"),
            plant_parts=entry.get("plant_parts", []),
            impact=entry.get("impact", ""),
            permit_requirement=entry.get("permit_requirement", ""),
            india_controls=entry.get("india_controls", ""),
            cultivation_note=entry.get("cultivation_note", ""),
        )
        return plant

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

        ayurvedic: dict[str, list[str]] = {}
        regional: dict[str, list[str]] = {}
        english: list[str] = []
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

        canonical_ids: list[str] = []
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

        plants = [cls._attach_cites(cls._plant(cid)) for cid in canonical_ids]

        recommendations: list[str] = []
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

        # ---- CITES enforcement -----------------------------------------------
        cites_hits = [p for p in plants if p.cites is not None]
        if cites_hits:
            app_i = [p for p in cites_hits if p.cites and p.cites.appendix == "I"]
            app_ii = [p for p in cites_hits if p.cites and p.cites.appendix == "II"]
            names = ", ".join(p.botanical_name for p in cites_hits)
            if app_i:
                recommendations.insert(
                    0,
                    "CITES Appendix I: " + names + " — international trade in wild-collected specimens escapes "
                    "standard commercial channels; export/import requires exceptional CITES permits from both "
                    "the exporting and importing Parties. Treat wild origin as a practical trade ban and source "
                    "only documented cultivated stock."
                )
            elif app_ii:
                recommendations.insert(
                    0,
                    "CITES Appendix II: " + names + " — export of the listed parts/derivatives requires a CITES "
                    "export permit and legal-procurement certification. Verify the annotated scope (e.g. #2 finished-"
                    "product exemption) before international commercial transfer."
                )
            else:
                recommendations.insert(
                    0,
                    "CITES-listed species: " + names + " — confirm the applicable Appendix and permit regime before "
                    "export/import."
                )
            for p in cites_hits:
                c = p.cites
                if c:
                    requirements = [r for r in (c.permit_requirement, c.india_controls, c.cultivation_note) if r]
                    recommendation = "CITES: " + p.botanical_name + " (" + (c.appendix or "listed") + ")"
                    if requirements:
                        recommendation += " — " + " | ".join(set(requirements))
                    recommendations.append(recommendation)
            recommendations.append(
                "Confirm whether any ingredient's official export route is covered by the CITES Annex "
                "(Saussurea costus I; Jatamansi, Kutki, Sarpagandha, Himalayan yew, Bankakri, Agarwood II, ...) "
                "before drafting supply agreements."
            )

        return BioResourceGraphResponse(
            passport_id=passport_id,
            plants=plants,
            recommendations=recommendations,
            disclaimer=cls.DISCLAIMER,
        )