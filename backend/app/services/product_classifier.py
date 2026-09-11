import json
import os
import re
from typing import Dict, List, Any, Optional

from app.models.intelligence import (
    ProductClassifierResponse,
    PathwayScore,
)
from app.services.passport_engine import PassportEngine

_KNOWLEDGE = os.path.join(os.path.dirname(__file__), "..", "knowledge")

CURATIVE_HINTS = [
    r"treat(?:s|ing|ed|ment|ments)?",
    r"cure(?:s|d)?",
    r"heal(?:s|ing|ed)?",
    r"prevent(?:s|ed|ing)?",
    r"remed(?:y|ies)",
    r"combat(?:s)?",
    r"fight(?:s|ing)?",
    r"relieve(?:s|d|ing)?",
]
STRUCTURE_HINTS = [
    r"support(?:s|ing|ed)?",
    r"promote(?:s|ing|d)?",
    r"maintain(?:s|ing|ed)?",
    r"help(?:s|ing)?",
    r"calm(?:s|ing)?",
    r"relax(?:es|ed|ing|ation)?",
    r"nourish(?:es|ing|ed)?",
    r"wellness",
    r"wellbeing",
    r"healthy",
]
THERAPEUTIC_HINTS = [
    r"condition",
    r"disease|disorders?",
    r"symptom",
    r"insomnia",
    r"anxiety",
    r"pain",
]
DIETARY_HINTS = [
    r"dietary",
    r"daily",
    r"nutrition",
    r"food",
    r"immunity",
    r"energy",
    r"wellness",
    r"supplement",
    r"strength",
]

PATHWAY_META: Dict[str, Dict[str, Any]] = {
    "ayurvedic_drug": {
        "authority": "State Licensing Authority / CDSCO ASU-CC via e-AUSHADHI",
        "sources": ["Drugs and Cosmetics Act, 1940 & Rules 1945 (ASU)", "e-AUSHADHI portal", "Drugs & Magic Remedies (Objectionable Advertisements) Act, 1954"],
    },
    "proprietary_ayurveda": {
        "authority": "State Licensing Authority / CDSCO ASU-CC via e-AUSHADHI",
        "sources": ["Drugs and Cosmetics Act, 1940 (Schedule Z proprietary Ayurveda medicines)", "e-AUSHADHI portal"],
    },
    "ayurveda_aahara": {
        "authority": "FSSAI (State Food Safety Commissioner)",
        "sources": ["FSS (Ayurveda Aahara) Regulations, 2022", "FSS (Health Supplements, Nutraceuticals, FSDC, SAC) Regulations, 2022", "FSSAI labelling & claims notification"],
    },
    "cosmetic": {
        "authority": "CDSCO — Cosmetics",
        "sources": ["Cosmetics Rules, 2020", "BIS standards for herbal cosmetics"],
    },
    "nutraceutical": {
        "authority": "FSSAI (Central/State)",
        "sources": ["FSS (Health Supplements, Nutraceuticals, FSDC, SAC) Regulations, 2022", "FSSAI product approval / NLT route"],
    },
    "unresolved": {"authority": "To be confirmed with the concerned authority", "sources": []},
}


class ProductClassifier:
    """
    Ayurveda Aahara / Product Classifier (USP: Product Classification Intelligence).
    Uses declared product facts (form, dosage, purpose, claims, preparation) against
    curated pathway rules to propose the likely regulatory class and why, without
    claiming the classification is final.
    """

    _rules: List[Dict[str, Any]] = []

    DISCLAIMER = (
        "Pathway classification is decision support computed from declared product inputs and curated rules. "
        "The final registration class is determined by the concerned licensing or food-safety authority."
    )

    @classmethod
    def load_data(cls):
        if not cls._rules:
            path = os.path.join(_KNOWLEDGE, "pathway_rules.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._rules = json.load(f)

    @staticmethod
    def _has_any(field: str, keywords: List[str]) -> bool:
        pattern = r"(?:\b(?:" + "|".join(keywords) + r")\b)"
        return re.search(pattern, field, flags=re.IGNORECASE) is not None

    @classmethod
    def classify(
        cls,
        product_form: str = "",
        dosage_form: str = "",
        intended_use: str = "",
        claims: Optional[List[str]] = None,
        ingredients: Optional[List[str]] = None,
        process_description: str = "",
        passport_id: Optional[str] = None,
        label_disclaimer: Optional[str] = None,
    ) -> ProductClassifierResponse:
        cls.load_data()
        claims = claims or []
        ingredients = ingredients or []
        form = f"{product_form} {dosage_form}".lower().strip()
        use = f"{intended_use} {' '.join(claims)}".lower()
        prep = (process_description or "").lower()

        claim_lower = " ".join(claims).lower()
        claim_curative = cls._has_any(claim_lower, CURATIVE_HINTS)
        claim_structure = cls._has_any(claim_lower, STRUCTURE_HINTS)

        intent_dietary = cls._has_any(use, DIETARY_HINTS)
        intent_therapeutic = claim_curative or cls._has_any(use, THERAPEUTIC_HINTS)
        prep_aqueous = cls._has_any(prep, ["aqueous", "kwatha", "decoction", "water", "kadha", "juice"])
        prep_solvent = cls._has_any(prep, ["hydroalcoholic", "alcohol", "ethanol", "solvent", "supercritical", "co2"])

        topical_forms = ["taila", "ointment", "cream", "gel", "lotion", "balm", "lepa", "oil", "liniment"]
        classical_forms = ["vati", "kwatha", "kashayam", "asava", "arishta", "churna", "taila", "ghrita", "avaleha", "choorna"]
        encapsulated_forms = ["capsule", "tablet", "softgel", "pills", "vati"]
        food_forms = ["churna", "powder", "mix", "granule", "bites", "confectionery", "mixture", "sweet", "ladoo"]

        predicates: Dict[str, bool] = {
            "claim_curative": claim_curative,
            "claim_structure_or_wellness": claim_structure and not claim_curative,
            "not_therapeutic": not intent_therapeutic,
            "intent_dietary": intent_dietary,
            "therapeutic_purpose": intent_therapeutic,
            "prep_aqueous": prep_aqueous,
            "prep_solvent": prep_solvent,
            "form_food": cls._has_any(form, food_forms),
            "form_classical_medicine": cls._has_any(form, classical_forms),
            "form_encapsulated": cls._has_any(form, encapsulated_forms),
            "topical": cls._has_any(form, topical_forms),
            "no_disclaimer": not (label_disclaimer and "not" in label_disclaimer.lower()),
        }

        scores: Dict[str, int] = {}
        reasons: Dict[str, List[str]] = {}
        for rule in cls._rules:
            conditions = rule.get("conditions", {})
            if all(predicates.get(key, False) == val for key, val in conditions.items()):
                scores[rule["pathway_key"]] = scores.get(rule["pathway_key"], 0) + rule["weight"]
                reasons.setdefault(rule["pathway_key"], []).append(rule["reason"])

        if not scores:
            scores["unresolved"] = 0
            reasons["unresolved"] = ["No strong rule matched the declared inputs — pathway must be confirmed with the authority."]

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        winner_key, winner_score = ranked[0]
        runner_score = ranked[1][1] if len(ranked) > 1 else 0

        if winner_score - runner_score >= 8 and winner_score >= 24:
            confidence = "HIGH"
        elif winner_score >= 14:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        meta = PATHWAY_META[winner_key]
        alternative_pathways = [
            PathwayScore(pathway=k, score=v, match_reasons=reasons.get(k, []))
            for k, v in ranked[:3]
        ]

        next_actions = {
            "ayurvedic_drug": [
                "Register on e-AUSHADHI and obtain ASU product + manufacturing licences before marketing.",
                "Confirm no Drugs & Magic Remedies Act §3 disease wording on the label.",
                "Complete Schedule T GMP and batch quality (heavy metals, microbial) testing.",
            ],
            "proprietary_ayurveda": [
                "Apply for a proprietary Ayurveda medicine product licence via e-AUSHADHI.",
                "Prepare formulation, method of manufacture and evidence dossier.",
            ],
            "ayurveda_aahara": [
                "Submit the formulation and label to FSSAI for pathway confirmation.",
                "Adopt FSS (Ayurveda Aahara) schedule-compliant labeling and claims.",
            ],
            "cosmetic": [
                "Register the product under Cosmetics Rules, 2020 (CDSCO cosmetics module).",
                "Verify applicable BIS standards for the herbal cosmetic.",
            ],
            "nutraceutical": [
                "Secure FSSAI product approval / NLT case approval under FSS (Health Supplements) Regulations 2022.",
            ],
            "unresolved": [
                "Declare intended use, dosage form and claims to the concerned licensing/food authority for a binding classification.",
            ],
        }

        return ProductClassifierResponse(
            passport_id=passport_id,
            product_form=product_form,
            dosage_form=dosage_form,
            intended_use=intended_use,
            claims=claims,
            ingredients=ingredients,
            likely_pathway=meta["authority"],
            pathway_category=winner_key,
            pathway_confidence=confidence,
            reasons=reasons.get(winner_key, []),
            alternative_pathways=alternative_pathways,
            applicable_authority=meta["authority"],
            applicable_sources=meta["sources"],
            next_actions=next_actions.get(winner_key, []),
            disclaimer=cls.DISCLAIMER,
        )

    @classmethod
    def classify_passport(cls, passport_id: str) -> ProductClassifierResponse:
        passport = PassportEngine.get_passport(passport_id)
        if passport is None:
            return cls.classify(passport_id=passport_id)
        return cls.classify(
            product_form=passport.product_form,
            dosage_form=passport.dosage_form,
            intended_use=passport.intended_use,
            claims=passport.proposed_claims,
            ingredients=[ing.raw_name for ing in passport.ingredients],
            process_description=passport.process_description,
            passport_id=passport_id,
        )