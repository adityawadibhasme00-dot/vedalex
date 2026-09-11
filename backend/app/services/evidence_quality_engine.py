import json
import os
from typing import Dict, List, Any

from app.models.intelligence import (
    EvidenceQualityIntelligenceResponse,
    IngredientIntelligence,
    EvidenceLadderCell,
    QualityParameter,
)
from app.services.passport_engine import PassportEngine

_KNOWLEDGE = os.path.join(os.path.dirname(__file__), "..", "knowledge")


class EvidenceQualityEngine:
    """
    Evidence & Quality Intelligence (USP #2).
    Builds a per-ingredient research-evidence ladder (traditional → preclinical →
    clinical → product-specific → safety) and a pharmacopoeia quality-readiness
    profile (botanical identity, monograph, heavy metals, microbial, markers).
    All values come from curated knowledge datasets — no invented findings.
    """

    _ladders: Dict[str, Dict[str, Any]] = {}
    _quality: Dict[str, Dict[str, Any]] = {}

    DISCLAIMER = (
        "Evidence-support levels reflect the curated knowledge base at the time of assessment and are "
        "not approvals. Quality readiness describes document/test availability, not regulatory acceptance."
    )

    @classmethod
    def load_data(cls):
        if not cls._ladders:
            path = os.path.join(_KNOWLEDGE, "evidence_ladders.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._ladders = {item["canonical_id"]: item for item in json.load(f)}
        if not cls._quality:
            path = os.path.join(_KNOWLEDGE, "quality_pharmacopoeia.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._quality = {item["canonical_id"]: item for item in json.load(f)}

    @classmethod
    def _ingredient_intelligence(cls, canonical_id: str) -> IngredientIntelligence:
        ladder_entry = cls._ladders.get(canonical_id)
        quality_entry = cls._quality.get(canonical_id)

        ladder_cells: List[EvidenceLadderCell] = []
        evidence_gaps: List[str] = []
        if ladder_entry:
            for cell in ladder_entry.get("ladder", []):
                ladder_cells.append(EvidenceLadderCell(
                    level=cell["level"],
                    level_label=cell["level_label"],
                    support_status=cell["support_status"],
                    support_pct=cell.get("support_pct", 0),
                    sources=cell.get("sources", []),
                    note=cell.get("note", ""),
                    gap_reason=cell.get("gap_reason"),
                ))
                if cell["support_status"] == "insufficient":
                    evidence_gaps.append(f"{cell['level_label']}: {cell.get('gap_reason', 'No data')}")

        evidence_support_pct = 0
        if ladder_cells:
            evidence_support_pct = int(sum(c.support_pct for c in ladder_cells) / len(ladder_cells))

        quality_params: List[QualityParameter] = []
        quality_gaps: List[str] = []
        if quality_entry:
            for p in quality_entry.get("parameters", []):
                available = bool(p.get("available"))
                quality_params.append(QualityParameter(
                    param_name=p["param_name"],
                    spec=p.get("spec", ""),
                    test_method=p.get("test_method", ""),
                    available=available,
                    status="available" if available else "missing",
                ))
                if not available:
                    quality_gaps.append(p["param_name"])

        quality_readiness_pct = 0
        if quality_params:
            quality_readiness_pct = int(sum(1 for q in quality_params if q.available) * 100 / len(quality_params))

        botanical = quality_entry.get("botanical_name") or ladder_entry.get("botanical_name") or canonical_id
        monograph = quality_entry.get("api_monograph_id") or ladder_entry.get("api_monograph_id") or "—"

        return IngredientIntelligence(
            canonical_id=canonical_id,
            botanical_name=botanical,
            api_monograph_id=monograph,
            evidence_ladder=ladder_cells,
            evidence_support_pct=evidence_support_pct,
            evidence_gaps=evidence_gaps,
            quality_parameters=quality_params,
            quality_readiness_pct=quality_readiness_pct,
            quality_gaps=quality_gaps,
        )

    @classmethod
    def evaluate(cls, passport_id: str) -> EvidenceQualityIntelligenceResponse:
        cls.load_data()
        passport = PassportEngine.get_passport(passport_id)
        if passport is None:
            return cls._fallback_response(passport_id)

        canonical_ids: List[str] = []
        for ing in passport.ingredients:
            cid = ing.canonical_id
            if cid and cid not in canonical_ids:
                canonical_ids.append(cid)

        if not canonical_ids:
            return cls._fallback_response(passport_id)

        ingredients = [cls._ingredient_intelligence(cid) for cid in canonical_ids]

        overall_evidence = int(sum(i.evidence_support_pct for i in ingredients) / len(ingredients)) if ingredients else 0
        overall_quality = int(sum(i.quality_readiness_pct for i in ingredients) / len(ingredients)) if ingredients else 0

        actions: List[str] = []
        for ing in ingredients:
            if ing.evidence_gaps:
                actions.append(f"{ing.botanical_name}: commission the missing evidence — {ing.evidence_gaps[0].split(':')[0]}.")
            if ing.quality_gaps:
                actions.append(f"{ing.botanical_name}: arrange NABL tests for {', '.join(ing.quality_gaps[:2])}.")
        if not actions:
            actions.append("All curated evidence and quality dimensions are satisfied. Proceed to dossier assembly.")

        return EvidenceQualityIntelligenceResponse(
            passport_id=passport_id,
            ingredients=ingredients,
            overall_evidence_support_pct=overall_evidence,
            overall_quality_readiness_pct=overall_quality,
            recommended_actions=actions,
            disclaimer=cls.DISCLAIMER,
        )

    @classmethod
    def _fallback_response(cls, passport_id: str) -> EvidenceQualityIntelligenceResponse:
        return EvidenceQualityIntelligenceResponse(
            passport_id=passport_id,
            ingredients=[],
            overall_evidence_support_pct=0,
            overall_quality_readiness_pct=0,
            recommended_actions=["No resolved passport found for this ID. Create an Innovation Passport first, then re-run the intelligence assessment."],
            disclaimer=cls.DISCLAIMER,
        )