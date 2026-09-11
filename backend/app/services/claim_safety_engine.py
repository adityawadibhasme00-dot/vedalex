import json
import os
import re
from typing import List, Dict, Optional, Any

from app.models.intelligence import (
    ClaimSafetyAnalysisResponse,
    ClaimSafetyResult,
    ClaimSafetySignal,
    MisleadingAdRisk,
)
from app.services.ingredient_resolver import IngredientResolverService

_KNOWLEDGE = os.path.join(os.path.dirname(__file__), "..", "knowledge")


class ClaimSafetyEngine:
    """
    Claim & Safety Intelligence (USP #1).
    Tests proposed claims against curated regulatory-claim rules and Ayurveda
    pharmacovigilance signals (Ayush Suraksha / Drugs & Magic Remedies Act).
    Never invents legal conclusions: unmatched wording is flagged 'not_evaluated'.
    """

    _claim_rules: List[Dict[str, Any]] = []
    _safety_signals: List[Dict[str, Any]] = []

    DISCLAIMER = (
        "Suggested alternative wording is regulatory guidance only and does not constitute "
        "legal confirmation of compliance. Final claim language must be validated by "
        "regulators and competent counsel for each target market."
    )

    @classmethod
    def load_data(cls):
        if not cls._claim_rules:
            path = os.path.join(_KNOWLEDGE, "claim_alternatives.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._claim_rules = json.load(f)
        if not cls._safety_signals:
            path = os.path.join(_KNOWLEDGE, "safety_signals.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._safety_signals = json.load(f)

    @staticmethod
    def _market_regulations(target_markets: List[str]) -> str:
        anchors = []
        if any(m.lower().startswith("india") for m in target_markets):
            anchors.append("India: Drugs & Magic Remedies Act 1954 / CDSCO-ASU / FSSAI Ayurveda Aahara Reg. 4")
        if any("us" in m.lower() or "united states" in m.lower() or "america" in m.lower() for m in target_markets):
            anchors.append("US: FD&C Act §201(g) / DSHEA 1994 / 21 CFR 101.93")
        if any("canada" in m.lower() for m in target_markets):
            anchors.append("Canada: NHPR SOR/2003-196")
        return anchors[0] if len(anchors) == 1 else " | ".join(anchors)

    @classmethod
    def _match_rule(cls, claim_lower: str) -> Optional[Dict[str, Any]]:
        for rule in cls._claim_rules:
            try:
                if re.search(rule["pattern"], claim_lower):
                    return rule
            except re.error:
                continue
        return None

    @classmethod
    def _resolve_ingredients(cls, ingredient_hints: List[str]) -> List[str]:
        canonical_ids: List[str] = []
        for hint in ingredient_hints:
            resolved = IngredientResolverService.resolve(hint)
            if resolved:
                canonical_ids.append(resolved.canonical_id)
        return canonical_ids

    @classmethod
    def _safety_signals_for(cls, canonical_ids: List[str]) -> List[ClaimSafetySignal]:
        out: List[ClaimSafetySignal] = []
        for entry in cls._safety_signals:
            if entry["canonical_id"] not in canonical_ids:
                continue
            for sig in entry.get("signals", []):
                out.append(ClaimSafetySignal(
                    ingredient=entry["ingredient"],
                    botanical_name=entry.get("botanical_name", ""),
                    signal=sig["signal"],
                    severity=sig.get("severity", "LOW"),
                    evidence_source=sig.get("evidence_source", ""),
                    precaution=sig.get("precaution", ""),
                ))
        return out

    @classmethod
    def analyze(
        cls,
        claims: List[str],
        ingredients: List[str],
        target_markets: List[str],
        product_type: str = "ayurvedic_drug",
        passport_id: Optional[str] = None,
    ) -> ClaimSafetyAnalysisResponse:
        cls.load_data()
        resolved = cls._resolve_ingredients(ingredients)
        safety = cls._safety_signals_for(resolved)
        regulation = cls._market_regulations(target_markets)

        results: List[ClaimSafetyResult] = []
        flagged_misleading: List[str] = []
        disease_flags: List[str] = []

        for claim in claims:
            claim_lower = claim.lower()
            rule = cls._match_rule(claim_lower)
            if not rule:
                results.append(ClaimSafetyResult(
                    claim_text=claim,
                    claim_category="other",
                    evidence_alignment="not_evaluated",
                    risk_level="SAFE",
                    risk_color="green",
                    regulation=regulation,
                    suggested_alternative=None,
                    note="No conflicting wording detected in the claim rules engine. Verify the statement against actual evidence and target-market submission requirements."
                ))
                continue

            category = rule["claim_category"]
            risk = rule["risk_level"]
            alternative = rule.get("suggested_alternative")

            if risk == "CRITICAL":
                risk, color = "HIGH_RISK", "red"
            else:
                color = {"HIGH_RISK": "red", "WARNING": "yellow", "SAFE": "green"}.get(risk, "yellow")

            evidence_alignment = {
                "SAFE": "supported",
                "WARNING": "partial",
                "HIGH_RISK": "unsupported",
            }.get(risk, "not_evaluated")

            if category == "safety":
                flagged_misleading.append(claim)
            if risk in ("HIGH_RISK", "CRITICAL") and category == "curative":
                disease_flags.append(claim)

            results.append(ClaimSafetyResult(
                claim_text=claim,
                claim_category=category,
                evidence_alignment=evidence_alignment,
                risk_level=risk,
                risk_color=color,
                regulation=regulation,
                suggested_alternative=alternative,
                note=rule.get("note", ""),
            ))

        misleading = MisleadingAdRisk(
            flagged_phrases=flagged_misleading,
            act_citation="Ayush Suraksha 2023 (misleading advertisements) & Drugs and Magic Remedies (Objectionable Advertisements) Act, 1954 §3",
            action="Revise or remove flagged wording. Retain documentary evidence for every structure/function statement before marketing.",
        )

        counts = {"red": sum(1 for r in results if r.risk_color == "red"),
                  "yellow": sum(1 for r in results if r.risk_color == "yellow"),
                  "green": sum(1 for r in results if r.risk_color == "green")}
        if disease_flags:
            overall, overall_color = "HIGH_RISK", "red"
        elif counts["red"] > 0:
            overall, overall_color = "HIGH_RISK", "red"
        elif counts["yellow"] > 2:
            overall, overall_color = "WARNING", "yellow"
        else:
            overall, overall_color = "SAFE", "green"

        alerts = [
            f"{len(safety)} pharmacovigilance signal(s) surfaced for formulated ingredients — review precaution wording on the label.",
            "Market anchor batch: {0}".format(regulation),
            "Structure/function and traditional-use claims require a compliant disclaimer (e.g., 21 CFR 101.93 / FSSAI).",
        ]

        summary = (
            f"Analysis complete: {counts['red']} high-risk, {counts['yellow']} warnings, {counts['green']} "
            f"permissible claims. {len(safety)} safety signal(s) attached to {len(resolved)} resolved ingredient(s)."
        )

        return ClaimSafetyAnalysisResponse(
            passport_id=passport_id,
            overall_verdict=overall,
            overall_color=overall_color,
            claims=results,
            safety_signals=safety,
            misleading_ad_risk=misleading,
            regulatory_alerts=alerts,
            summary=summary,
            disclaimer=cls.DISCLAIMER,
        )