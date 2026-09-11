import json
import os
from typing import Dict, List, Any, Set

from app.models.intelligence import (
    ExportReadinessResponse,
    MarketReadinessItem,
    ExportGap,
)
from app.services.passport_engine import PassportEngine
from app.services.claim_safety_engine import ClaimSafetyEngine
from app.services.evidence_quality_engine import EvidenceQualityEngine
from app.services.product_classifier import ProductClassifier
from app.services.ingredient_resolver import IngredientResolverService

_KNOWLEDGE = os.path.join(os.path.dirname(__file__), "..", "knowledge")


class ExportReadinessEngine:
    """
    Market / Export Readiness Engine.
    Per-market (India, US, EU, Canada) requirement gap comparison built from the
    passport + claim analysis + evidence/quality intelligence + product class.
    Deterministic and explainable — every gap carries an action and a source.
    """

    _requirements: List[Dict[str, Any]] = []

    DISCLAIMER = (
        "Export readiness is a deterministic planning score, not an approval. Requirements and authorities must be "
        "re-validated against the latest official texts before filing."
    )

    @classmethod
    def load_data(cls):
        if not cls._requirements:
            path = os.path.join(_KNOWLEDGE, "export_market_requirements.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._requirements = json.load(f)

    @classmethod
    def _resolved_status(cls, rule_key: str, ctx: Dict[str, Any]) -> str:
        key_map: Dict[str, str] = {
            "requirement_satisfied": "satisfied",
            "requirement_partial": "partial",
            "requirement_missing": "missing",
            "claims_safe": ctx.get("claims_safe", "missing"),
            "claims_structure_only": ctx.get("claims_structure_only", "missing"),
            "quality_high": ctx.get("quality_high", "missing"),
            "quality_partial": ctx.get("quality_partial", "missing"),
            "evidence_product_specific": ctx.get("evidence_product_specific", "missing"),
            "ndi_old": ctx.get("ndi_old", "missing"),
            "monograph": ctx.get("monograph", "missing"),
            "pathway_any": ctx.get("pathway_any", "missing"),
            "pathway_drug": ctx.get("pathway_drug", "missing"),
            "pathway_food": ctx.get("pathway_food", "missing"),
        }
        if rule_key in ("requirement_satisfied", "requirement_partial", "requirement_missing"):
            return rule_key.split("_")[1]
        status = key_map.get(rule_key, "missing")
        return status if status in ("satisfied", "partial", "missing") else "missing"

    @classmethod
    def evaluate(cls, passport_id: str) -> ExportReadinessResponse:
        cls.load_data()
        passport = PassportEngine.get_passport(passport_id)
        if passport is None:
            return ExportReadinessResponse(
                passport_id=passport_id,
                markets=[],
                recommended_first_market="",
                summary="No resolved passport found. Create an Innovation Passport first.",
                disclaimer=cls.DISCLAIMER,
            )

        ingredients_raw = [ing.raw_name for ing in passport.ingredients]
        claim_analysis = ClaimSafetyEngine.analyze(
            claims=passport.proposed_claims,
            ingredients=ingredients_raw,
            target_markets=passport.target_markets,
            passport_id=passport_id,
        )
        eq = EvidenceQualityEngine.evaluate(passport_id)
        pc = ProductClassifier.classify_passport(passport_id)

        quality_pct = eq.overall_quality_readiness_pct
        product_specific_documented = any(
            cell.level == "product_specific" and cell.support_status == "documented"
            for ing in eq.ingredients
            for cell in ing.evidence_ladder
        )

        all_ndi_old: Set[str] = set()
        all_monographed: Set[str] = set()
        for ing in passport.ingredients:
            if not ing.canonical_id:
                continue
            resolved = IngredientResolverService.resolve(ing.raw_name)
            if resolved:
                if resolved.us_fda_ndi_status == "old_dietary_ingredient":
                    all_ndi_old.add(ing.canonical_id)
                if resolved.canada_nhpid_status == "monographed":
                    all_monographed.add(ing.canonical_id)
        resolved_set = {ing.canonical_id for ing in passport.ingredients if ing.canonical_id}

        ctx: Dict[str, Any] = {
            "claims_safe": "satisfied" if claim_analysis.overall_color == "green" else ("partial" if claim_analysis.overall_color == "yellow" else "missing"),
            "claims_structure_only": "satisfied" if all(c.risk_color == "green" for c in claim_analysis.claims) else ("partial" if claim_analysis.overall_color == "yellow" else "missing"),
            "quality_high": "satisfied" if quality_pct >= 60 else ("partial" if quality_pct >= 40 else "missing"),
            "quality_partial": "satisfied" if quality_pct >= 40 else "missing",
            "evidence_product_specific": "satisfied" if product_specific_documented else "missing",
            "ndi_old": "satisfied" if resolved_set and all_ndi_old == resolved_set else "missing",
            "monograph": "satisfied" if resolved_set and all_monographed == resolved_set else "missing",
            "pathway_any": "satisfied" if pc.pathway_category != "unresolved" else "missing",
            "pathway_drug": "satisfied" if pc.pathway_category in ("ayurvedic_drug", "proprietary_ayurveda") else "missing",
            "pathway_food": "satisfied" if pc.pathway_category in ("ayurveda_aahara", "nutraceutical") else "missing",
        }

        markets_out: List[MarketReadinessItem] = []
        for market_def in cls._requirements:
            gaps: List[ExportGap] = []
            satisfied: int = 0
            for req in market_def.get("requirements", []):
                status = cls._resolved_status(req["rule_key"], ctx)
                if status == "satisfied":
                    satisfied += 1
                gaps.append(ExportGap(
                    area=req["area"],
                    requirement=req["requirement"],
                    status=status,
                    action="Complete the requirement and keep documentary evidence." if status == "missing" else ("Strengthen supporting documentation." if status == "partial" else "Retain documentation as ready."),
                    source=req["source"],
                ))

            total = len(gaps)
            pct = int(round(100 * satisfied / total)) if total else 0
            if pct >= 75:
                overall = "ready"
            elif pct >= 40:
                overall = "partial"
            else:
                overall = "not_ready"

            prerequisites = [g.area for g in gaps if g.status == "satisfied"]
            markets_out.append(MarketReadinessItem(
                market=market_def["market"],
                flag=market_def.get("flag", ""),
                overall_status=overall,
                readiness_pct=pct,
                prerequisites_satisfied=prerequisites,
                gaps=gaps,
            ))

        ranked = sorted(markets_out, key=lambda m: m.readiness_pct, reverse=True)
        recommended = ranked[0].market if ranked else ""
        if ranked and ranked[0].readiness_pct < 40:
            recommended = f"{ranked[0].market} (needs the most work — lowest barrier first)"

        summary = (
            f"Comparing {len(markets_out)} markets for the '{passport.case_title}' passport: highest current "
            f"readiness is {ranked[0].readiness_pct}% ({ranked[0].market}). Focus gaps: licenses/GMP, batch quality "
            f"tests and claim substantiation."
        )

        next_actions: List[str] = []
        top_gap_areas = []
        for m in markets_out:
            missing = [g.area for g in m.gaps if g.status == "missing"]
            if missing:
                top_gap_areas.append(f"{m.market}: {', '.join(missing[:3])}")
            if m.readiness_pct < 40:
                next_actions.append(f"{m.market}: address missing license/GMP and batch-quality requirements before export planning.")
        if not next_actions:
            next_actions.append("Primary market readiness above threshold — begin dossier assembly for the recommended market.")
        if top_gap_areas:
            next_actions.append("Common gaps: " + "; ".join(top_gap_areas[:3]))

        return ExportReadinessResponse(
            passport_id=passport_id,
            origin_market=passport.target_markets[0] if passport.target_markets else "India",
            markets=markets_out,
            recommended_first_market=recommended,
            summary=summary,
            next_actions=next_actions,
            disclaimer=cls.DISCLAIMER,
        )