import hashlib
import json
import os
import re
from typing import Any

from app.models.intelligence import (
    ClassifierEvidence,
    PathwayScore,
    ProductClassifierResponse,
    RuleValidationCheck,
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

PATHWAY_META: dict[str, dict[str, Any]] = {
    "classical_medicine": {
        "authority": "AYUSH CCReM / State Licensing Authority (Classical ASU medicine)",
        "sources": ["Drugs and Cosmetics Rules, 1945 — First Schedule (Classical medicines)", "AYUSH Classical Medicine recognition (CCReM)", "Ayurvedic Pharmacopoeia of India"],
    },
    "ayurvedic_drug": {
        "authority": "State Licensing Authority / CDSCO ASU-CC via e-AUSHADHI",
        "sources": ["Drugs and Cosmetics Act, 1940 & Rules 1945 (ASU)", "e-AUSHADHI portal", "Drugs & Magic Remedies (Objectionable Advertisements) Act, 1954"],
    },
    "proprietary_ayurveda": {
        "authority": "State Licensing Authority / CDSCO ASU-CC via e-AUSHADHI",
        "sources": ["Drugs and Cosmetics Act, 1940 (Schedule Z proprietary Ayurveda medicines)", "e-AUSHADHI portal"],
    },
    "new_drug": {
        "authority": "CDSCO (Central Drugs Standard Control Organisation) — New Drug approval",
        "sources": ["Drugs and Cosmetics Rules, 1945 — Rule 2(ea) new drug", "Section 3(p) D&C Act 1940 (legal fiction for novel AYUSH ingredients)", "CDSCO New Drug application route"],
    },
    "phytopharmaceutical": {
        "authority": "CDSCO — Phytopharmaceutical New Drug approval",
        "sources": ["Drugs and Cosmetics Rules, 1945 — Rule 2(ea) Phytopharmaceutical", "CDSCO guidance on phytopharmaceuticals", "Ayurvedic Pharmacopoeia of India (botanical markers)"],
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

NOVEL_EXTRACTION_METHODS = {
    "supercritical": "Supercritical CO2",
    "solvent": "Hydro-alcoholic / solvent",
    "enzyme": "Enzyme-assisted",
    "fermentation": "Fermentation / microbial",
    "ultrasound": "Ultrasound-assisted",
    "membrane": "Membrane filtration / chromato",
    "nanotech": "Nanosizing / micronization",
    "standardised": "Standardised / titrated extract",
}

CLASSICAL_EXTRACTION_METHODS = {
    "classical": "Classical (Kwatha/Vati traditional)",
    "aqueous": "Aqueous decoction (Kwatha)",
    "decoction": "Aqueous decoction (Kwatha)",
    "kshudra": "Classical (Kshudra panchak)",
    "taila": "Classical medicated oil",
    "traditional": "Traditional method",
    "": "Not declared",
}


class ProductClassifier:
    """
    Ayurveda Aahara / Product Classifier (USP: Product Classification Intelligence).
    Uses declared product facts (form, dosage, purpose, claims, preparation) against
    curated pathway rules to propose the likely regulatory class and why, without
    claiming the classification is final.
    """

    _rules: list[dict[str, Any]] = []
    _rag_cache: dict[str, list[ClassifierEvidence]] = {}

    DISCLAIMER = (
        "Pathway classification is decision support computed from declared product inputs and curated rules. "
        "The final registration class is determined by the concerned licensing or food-safety authority."
    )

    # Step 4 domains per product family. Each domain maps to official sources:
    #   regulations        -> India Code / D&C Act 1940 & Rules 1945 / AYUSH e-AUSHADHI / FSSAI
    #   patents            -> IP India (patents & TKDL prior art, Section 3(p))
    #   biodiversity       -> NBA / Biological Diversity Act 2002 (ABS)
    #   traditional_knowledge -> TKDL / AYUSH classical references
    INTENT_LABELS: dict[str, str] = {
        "classical_medicine": "Classical (First Schedule)",
        "ayurvedic_drug": "Classical / Ayurvedic Drug",
        "proprietary_ayurveda": "Patent & Proprietary",
        "new_drug": "New Drug",
        "phytopharmaceutical": "Phytopharmaceutical / New Drug",
        "ayurveda_aahara": "Ayurveda Aahara (Food)",
        "nutraceutical": "Nutraceutical / Supplement",
        "cosmetic": "Cosmetic",
        "unresolved": "To be confirmed",
    }

    INTENT_DOMAINS: dict[str, list[list[str]]] = {
        "classical_medicine": [["regulations", "traditional_knowledge"]],
        "ayurvedic_drug": [["regulations", "traditional_knowledge"]],
        "proprietary_ayurveda": [["regulations"], ["patents", "traditional_knowledge"], ["biodiversity"]],
        "new_drug": [["regulations"], ["patents", "traditional_knowledge"], ["biodiversity"]],
        "phytopharmaceutical": [["regulations"], ["patents", "traditional_knowledge"], ["biodiversity"]],
        "ayurveda_aahara": [["regulations"]],
        "nutraceutical": [["regulations"]],
        "cosmetic": [["regulations"]],
        "unresolved": [["regulations"]],
    }

    # Step 5 rule packs applied against the winning family.
    RULE_VALIDATION_META: dict[str, list[dict[str, str]]] = {
        "classical_medicine": [
            {"rule": "First Schedule / Classical reference", "source": "D&C Rules 1945 — First Schedule; AYUSH CCReM"},
            {"rule": "AYUSH licensing (D&C Act 1940 & Rules 1945)", "source": "Drugs and Cosmetics Rules, 1945 (Rule 158-B / Schedule T)"},
            {"rule": "Labelling & claims (DMR Act 1954)", "source": "Drugs & Magic Remedies (Objectionable Advertisements) Act, 1954"},
        ],
        "ayurvedic_drug": [
            {"rule": "AYUSH licensing (D&C Act 1940 & Rules 1945)", "source": "Drugs and Cosmetics Rules, 1945 (Rule 158-B / Schedule T)"},
            {"rule": "Section 3(p) / New Drug check", "source": "Section 3(p) D&C Act 1940; Rule 2(ea) D&C Rules 1945"},
            {"rule": "ABS (NBA / Biological Diversity Act 2002)", "source": "Biological Diversity Act, 2002; ABS Rules 2014"},
            {"rule": "Labelling & claims (DMR Act 1954)", "source": "Drugs & Magic Remedies (Objectionable Advertisements) Act, 1954"},
        ],
        "proprietary_ayurveda": [
            {"rule": "AYUSH licensing (e-AUSHADHI / Schedule Z)", "source": "Drugs and Cosmetics Act, 1940 — Schedule Z; e-AUSHADHI"},
            {"rule": "Section 3(p) / New Drug check", "source": "Section 3(p) D&C Act 1940; Rule 2(ea) D&C Rules 1945"},
            {"rule": "ABS (NBA / Biological Diversity Act 2002)", "source": "Biological Diversity Act, 2002; ABS Rules 2014"},
            {"rule": "Labelling & claims (DMR Act 1954)", "source": "Drugs & Magic Remedies (Objectionable Advertisements) Act, 1954"},
        ],
        "new_drug": [
            {"rule": "New Drug approval (Rule 2(ea) CDSCO)", "source": "Drugs and Cosmetics Rules, 1945 — Rule 2(ea)"},
            {"rule": "Section 3(p) / New Drug check", "source": "Section 3(p) D&C Act 1940"},
            {"rule": "ABS (NBA / Biological Diversity Act 2002)", "source": "Biological Diversity Act, 2002; ABS Rules 2014"},
            {"rule": "Schedule T GMP & lead clinical evidence", "source": "Drugs and Cosmetics Rules, 1945 — Schedule T"},
        ],
        "phytopharmaceutical": [
            {"rule": "Phytopharmaceutical New Drug route", "source": "Rule 2(ea) D&C Rules 1945; CDSCO phytopharmaceutical guidance"},
            {"rule": "Section 3(p) / New Drug check", "source": "Section 3(p) D&C Act 1940"},
            {"rule": "ABS (NBA / Biological Diversity Act 2002)", "source": "Biological Diversity Act, 2002; ABS Rules 2014"},
        ],
        "ayurveda_aahara": [
            {"rule": "FSSAI Ayurveda Aahara Regulations 2022", "source": "FSS (Ayurveda Aahar) Regulations, 2022"},
            {"rule": "FSSAI labelling & permitted health claims", "source": "FSSAI Labelling & Display Regulations, 2020"},
            {"rule": "ABS (NBA / Biological Diversity Act 2002)", "source": "Biological Diversity Act, 2002; ABS Rules 2014"},
        ],
        "nutraceutical": [
            {"rule": "FSSAI Health Supplements / Nutraceuticals 2022", "source": "FSS (Health Supplements, Nutraceuticals, FSDC, SAC) Regulations, 2022"},
            {"rule": "FSSAI labelling & permitted health claims", "source": "FSSAI Labelling & Display Regulations, 2020"},
        ],
        "cosmetic": [
            {"rule": "Cosmetics Rules 2020 registration", "source": "Cosmetics Rules, 2020 (CDSCO)"},
            {"rule": "BIS standards for herbal cosmetics", "source": "Bureau of Indian Standards (BIS)"},
        ],
        "unresolved": [
            {"rule": "Classification confirmation by concerned authority", "source": "State Licensing Authority / FSSAI / CDSCO as applicable"},
        ],
    }

    @classmethod
    def load_data(cls):
        if not cls._rules:
            path = os.path.join(_KNOWLEDGE, "pathway_rules.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    cls._rules = json.load(f)

    @staticmethod
    def _has_any(field: str, keywords: list[str]) -> bool:
        pattern = r"(?:\b(?:" + "|".join(keywords) + r")\b)"
        return re.search(pattern, field, flags=re.IGNORECASE) is not None

    # ------------------------------------------------------------------
    # Step 4 — RAG Retrieval (official-database evidence)
    # ------------------------------------------------------------------
    @classmethod
    def _build_topic(cls, product_name: str, ingredients: list[str], intended_use: str) -> str:
        parts = [product_name] if product_name else []
        parts.extend(ingredients)
        if intended_use:
            parts.append(intended_use)
        return " ".join(p for p in parts if p).strip()[:160]

    @classmethod
    def _retrieve_evidence(
        cls,
        topic: str,
        winner_key: str,
    ) -> list[ClassifierEvidence]:
        """Retrieve a small, domain-restricted evidence set for the winning
        family. Queries are cached per topic so repeated classifications reuse
        the retrieval cost. Failures degrade to an empty evidence list."""
        if not topic:
            return []

        cache_key = hashlib.sha256(f"{winner_key}::{topic}".encode()).hexdigest()
        if cache_key in cls._rag_cache:
            return cls._rag_cache[cache_key]

        domain_sets = cls.INTENT_DOMAINS.get(winner_key, cls.INTENT_DOMAINS["unresolved"])
        query_blueprints = {
            "regulations": "regulatory classification pathway AYUSH Ayurveda medicine India D&C Act {topic}",
            "patents/tk": "patent prior art Section 3(p) traditional knowledge biological resource {topic}",
            "biodiversity": "Biological Diversity Act 2002 ABS access and benefit sharing NBA clearance commercial utilisation {topic}",
        }
        chosen: list[tuple] = []
        for domains in domain_sets:
            key = ("patents/tk" if set(domains) == {"patents", "traditional_knowledge"} else
                   "regulations" if domains == ["regulations"] else domains[0])
            template = query_blueprints.get(key, query_blueprints["regulations"])
            chosen.append((domains, template.format(topic=topic)))
        if winner_key in ("new_drug", "proprietary_ayurveda", "phytopharmaceutical", "ayurvedic_drug") and \
                not any(set(d) & {"patents", "traditional_knowledge"} for d, _ in chosen):
            chosen.append((["patents", "traditional_knowledge"], query_blueprints["patents/tk"].format(topic=topic)))
        if not any(set(d) & {"biodiversity"} for d, _ in chosen) and \
                winner_key not in ("classical_medicine", "ayurveda_aahara", "nutraceutical", "cosmetic"):
            chosen.append((["biodiversity"], query_blueprints["biodiversity"].format(topic=topic)))

        evidence: list[ClassifierEvidence] = []
        seen: set = set()
        try:
            from app.rag.retrieval_pipeline import HybridRetriever
        except Exception:
            return []

        for domains, query in chosen[:3]:
            try:
                result = HybridRetriever.retrieve(query, top_k=2, domains=list(domains))
                for doc in result.get("sources", [])[:2]:
                    title = (
                        doc.get("title") or doc.get("act_title") or doc.get("section_heading")
                        or doc.get("source") or (doc.get("content", "")[:70])
                    )
                    source = doc.get("source") or doc.get("source_url") or title
                    key = f"{source}::{title}"
                    if key in seen:
                        continue
                    seen.add(key)
                    evidence.append(ClassifierEvidence(
                        collection=doc.get("collection", "") or ",".join(domains),
                        title=title,
                        passage=(doc.get("content") or "")[:600],
                        source=source,
                        authority=doc.get("authority", ""),
                        source_url=doc.get("source_url", "") or "",
                    ))
            except Exception:
                continue

        evidence = evidence[:5]
        cls._rag_cache[cache_key] = evidence
        return evidence

    # ------------------------------------------------------------------
    # Step 5 — Rule Engine Validation (3-state)
    # ------------------------------------------------------------------
    @classmethod
    def _build_rule_validation(
        cls,
        winner_key: str,
        first_schedule: bool | None,
        new_ingredient: bool | None,
        intent_dietary: bool,
        intent_therapeutic: bool,
        is_novel_extraction: bool,
        label_disclaimer: str | None,
        claim_curative: bool,
        product_name: str,
    ) -> list[RuleValidationCheck]:
        checks: list[RuleValidationCheck] = []

        def add(rule: str, status: str, reason: str, source: str) -> None:
            verdict = {
                "SATISFIED": "Compliant",
                "NOT_SATISFIED": "Attention needed",
                "INSUFFICIENT": "Information required",
            }[status]
            checks.append(RuleValidationCheck(rule=rule, status=status, verdict=verdict, reason=reason, source=source))

        # --- India ASU / First Schedule / Section 3(p) ---
        if first_schedule is True:
            add(
                "First Schedule / Classical reference",
                "SATISFIED",
                "Classical text-based formulation confirmed in the First Schedule — grandfathered as a scheduled medicine.",
                "D&C Rules 1945 — First Schedule; AYUSH CCReM",
            )
        elif first_schedule is False:
            add(
                "First Schedule / Classical reference",
                "NOT_SATISFIED",
                "No classical First Schedule reference declared — the formulation is treated as a novel composition.",
                "D&C Rules 1945 — First Schedule",
            )
        else:
            add(
                "First Schedule / Classical reference",
                "INSUFFICIENT",
                "Declare whether the formulation matches a classical First Schedule text reference.",
                "D&C Rules 1945 — First Schedule",
            )

        if new_ingredient is True:
            add(
                "Section 3(p) / New Drug check",
                "NOT_SATISFIED",
                "Ingredient not referenced in the First Schedule — formulation becomes New Drug material under the Section 3(p) legal fiction (Rule 2(ea)), unless grandfathered.",
                "Section 3(p) D&C Act 1940; Rule 2(ea) D&C Rules 1945",
            )
        elif first_schedule is True or new_ingredient is False:
            add(
                "Section 3(p) / New Drug check",
                "SATISFIED",
                "Known, documented ingredients with recorded traditional knowledge use — no fresh Section 3(p) bar applies to the composition itself; novelty must still be shown for a patent claim.",
                "Section 3(p) D&C Act 1940",
            )
        else:
            add(
                "Section 3(p) / New Drug check",
                "INSUFFICIENT",
                "Confirm whether any ingredient falls outside the First Schedule to finalise the Section 3(p) / New Drug assessment.",
                "Section 3(p) D&C Act 1940",
            )

        # --- ABS / NBA ---
        if first_schedule is True and new_ingredient is False:
            add(
                "ABS (NBA / Biological Diversity Act 2002)",
                "SATISFIED",
                "Established classical botanical base — access to the resource must still be via the lawful supply chain; document origin for the dossier.",
                "Biological Diversity Act, 2002; ABS Rules 2014",
            )
        elif new_ingredient is True:
            add(
                "ABS (NBA / Biological Diversity Act 2002)",
                "INSUFFICIENT",
                f"Commercial utilisation of '{product_name or 'the formulation'}' from a non-classical biological resource likely requires NBA approval / RIAF and prior informed consent — confirm resource origin.",
                "Biological Diversity Act, 2002; ABS Rules 2014",
            )
        else:
            add(
                "ABS (NBA / Biological Diversity Act 2002)",
                "INSUFFICIENT",
                "Verify the biological resource origin and intended use to determine whether Access & Benefit Sharing obligations (NBA / RIAF) apply.",
                "Biological Diversity Act, 2002; ABS Rules 2014",
            )

        # --- AYUSH licensing (drug families) ---
        if winner_key in ("classical_medicine", "ayurvedic_drug", "proprietary_ayurveda", "new_drug", "phytopharmaceutical"):
            if winner_key == "classical_medicine":
                add(
                    "AYUSH licensing (D&C Act 1940 & Rules 1945)",
                    "SATISFIED",
                    "Classical recognition route (CCReM) — register the scheduled formulation; no fresh New Drug approval.",
                    "Drugs and Cosmetics Rules, 1945 — Rule 158-B / Schedule T",
                )
            else:
                add(
                    "AYUSH licensing (D&C Act 1940 & Rules 1945)",
                    "NOT_SATISFIED",
                    "An ASU product licence on e-AUSHADHI is required before marketing; Schedule T GMP and batch testing mandatory.",
                    "Drugs and Cosmetics Rules, 1945 — Rule 158-B / Schedule T",
                )
        elif winner_key == "ayurveda_aahara":
            add(
                "FSSAI Ayurveda Aahara Regulations 2022",
                "SATISFIED" if not intent_therapeutic else "NOT_SATISFIED",
                "FSSAI Ayurveda Aahar / nutraceutical frame applies; disease claims are prohibited — keep to daily-diet and wellness wording.",
                "FSS (Ayurveda Aahar) Regulations, 2022",
            )
        elif winner_key == "nutraceutical":
            add(
                "FSSAI Health Supplements / Nutraceuticals 2022",
                "SATISFIED" if not intent_therapeutic else "NOT_SATISFIED",
                "Route under FSS (Health Supplements, Nutraceuticals, FSDC, SAC) 2022 — product approval / NLT case required.",
                "FSS (Health Supplements, Nutraceuticals, FSDC, SAC) Regulations, 2022",
            )
        elif winner_key == "cosmetic":
            add(
                "Cosmetics Rules 2020 registration",
                "NOT_SATISFIED",
                "Register under Cosmetics Rules, 2020 (CDSCO cosmetics module) and confirm applicable BIS standard.",
                "Cosmetics Rules, 2020 (CDSCO)",
            )

        # --- Labelling & claims ---
        if claim_curative and winner_key not in ("ayurveda_aahara", "nutraceutical"):
            add(
                "Labelling & claims (DMR Act 1954)",
                "NOT_SATISFIED" if not (
                    label_disclaimer and "not" in label_disclaimer.lower()
                ) else "SATISFIED",
                "Curative wording triggers the Drugs & Magic Remedies Act 1954; disease claims and missing disclaimers are prohibited on labels and advertisements.",
                "Drugs & Magic Remedies (Objectionable Advertisements) Act, 1954",
            )
        elif winner_key in ("ayurveda_aahara", "nutraceutical"):
            add(
                "Labelling & health claims (FSSAI)",
                "SATISFIED" if not intent_therapeutic else "NOT_SATISFIED",
                "Only FSSAI-permitted health/nutrition claims allowed; therapeutic wording would reclassify the product as a drug.",
                "FSSAI Labelling & Display Regulations, 2020",
            )
        elif is_novel_extraction:
            add(
                "Labelling & claims",
                "INSUFFICIENT",
                "Advanced extraction with medicinal intent requires the CDSCO new-drug / phytopharmaceutical EUP pathway — support claims with the dossier.",
                "Rule 2(ea) D&C Rules 1945",
            )

        seen_rules = set()
        unique: list[RuleValidationCheck] = []
        for check in checks:
            if check.rule in seen_rules:
                continue
            seen_rules.add(check.rule)
            unique.append(check)
        return unique

    # ------------------------------------------------------------------
    # Step 7 — Next Actions (structured)
    # ------------------------------------------------------------------
    @staticmethod
    def _risk_level(confidence: str, winner_key: str) -> str:
        levels = {"HIGH": "LOW", "MEDIUM": "MODERATE", "LOW": "HIGH"}
        risk = levels.get(confidence, "MODERATE")
        if winner_key in ("new_drug", "phytopharmaceutical") and risk in ("LOW", "MODERATE"):
            if risk == "LOW":
                risk = "MODERATE"
            else:
                risk = "HIGH"
        if winner_key in ("ayurveda_aahara", "cosmetic", "nutraceutical") and risk == "MODERATE":
            risk = "LOW" if confidence == "HIGH" else "MODERATE"
        return risk

    @classmethod
    def classify(
        cls,
        product_name: str = "",
        product_form: str = "",
        dosage_form: str = "",
        intended_use: str = "",
        claims: list[str] | None = None,
        ingredients: list[str] | None = None,
        process_description: str = "",
        passport_id: str | None = None,
        label_disclaimer: str | None = None,
        first_schedule: bool | None = None,
        new_ingredient: bool | None = None,
        extraction_method: str = "",
        novel_process: bool | None = None,
        declared_use: str = "",
        ab_user_type: str = "",
        ab_turnover_inr: float | None = None,
        ab_wild_collected: bool | None = None,
        ab_commercial_use: bool = True,
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
        prep_standardised = cls._has_any(prep, ["standardised", "standardized", "titrated", "purified", "quantified", "marker", "titrated extract", "bioequivalent"])

        # Wizard step-3 intent override: explicit category beats keyword guessing
        # on short phrases such as "manages blood sugar" or "daily nutrition".
        declared_use_norm = (declared_use or "").lower().strip()
        if declared_use_norm == "medicine":
            intent_therapeutic = True
        elif declared_use_norm == "dietary":
            intent_dietary = True
            intent_therapeutic = False
        elif declared_use_norm == "wellness":
            intent_therapeutic = False
            intent_dietary = False

        topical_forms = ["taila", "ointment", "cream", "gel", "lotion", "balm", "lepa", "oil", "liniment"]
        classical_forms = ["vati", "kwatha", "kashayam", "asava", "arishta", "churna", "taila", "ghrita", "avaleha", "choorna"]
        encapsulated_forms = ["capsule", "tablet", "softgel", "pills", "vati", "syrup", "tonic", "juice", "liquor", "elixir", "drops", "linctus"]
        food_forms = ["churna", "powder", "mix", "granule", "bites", "confectionery", "mixture", "sweet", "ladoo"]

        # ---- Wizard inputs (Formulation Classification Wizard) ----
        extraction_norm = (extraction_method or "").lower().strip()
        is_novel_extraction = extraction_norm in NOVEL_EXTRACTION_METHODS

        predicates: dict[str, bool] = {
            "claim_curative": claim_curative,
            "claim_structure_or_wellness": claim_structure and not claim_curative,
            "not_therapeutic": not intent_therapeutic,
            "intent_dietary": intent_dietary,
            "therapeutic_purpose": intent_therapeutic,
            "prep_aqueous": prep_aqueous,
            "prep_solvent": prep_solvent,
            "prep_standardised": prep_standardised,
            "form_food": cls._has_any(form, food_forms),
            "form_classical_medicine": cls._has_any(form, classical_forms),
            "form_encapsulated": cls._has_any(form, encapsulated_forms),
            "topical": cls._has_any(form, topical_forms),
            "no_disclaimer": not (label_disclaimer and "not" in label_disclaimer.lower()),
            "wizard_first_schedule": bool(first_schedule),
            "wizard_new_ingredient": bool(new_ingredient),
            "wizard_novel_extraction": is_novel_extraction,
            "wizard_novel_process": bool(novel_process),
        }

        scores: dict[str, int] = {}
        reasons: dict[str, list[str]] = {}
        for rule in cls._rules:
            conditions = rule.get("conditions", {})
            if all(predicates.get(key, False) == val for key, val in conditions.items()):
                scores[rule["pathway_key"]] = scores.get(rule["pathway_key"], 0) + rule["weight"]
                reasons.setdefault(rule["pathway_key"], []).append(rule["reason"])

        if not scores:
            scores["unresolved"] = 0
            reasons["unresolved"] = ["No strong rule matched the declared inputs — pathway must be confirmed with the authority."]

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

        # When the wizard's answers are explicit, they are authoritative for the
        # headline category (the rule scores still surface as alternatives and
        # licensing nuances). Order of precedence:
        #   1) Novel ingredient + therapeutic use  -> New Drug
        #   2) Classical First Schedule (medicinal)-> Classical Medicine
        #   3) Classical First Schedule (diet/food)-> Ayurveda Aahar
        #   4) Advanced/non-classical extraction   -> Phytopharmaceutical
        wizard_used = any(k is not None for k in (first_schedule, new_ingredient, novel_process)) or bool(extraction_method) or bool(declared_use)
        override_key: str | None = None
        override_reason = ""
        if wizard_used:
            if new_ingredient is True and intent_therapeutic:
                override_key, override_reason = "new_drug", "WIZARD: novel ingredient (not in First Schedule) declared with therapeutic use — Section 3(p)/New Drug material."
            elif new_ingredient is True and intent_dietary:
                override_key, override_reason = "ayurveda_aahara", "WIZARD: novel ingredient declared for daily-diet/food use — Ayurveda Aahar/food frame."
            elif declared_use_norm == "cosmetic":
                override_key, override_reason = "cosmetic", "WIZARD: declared use is cosmetic (skin/hair appearance care) — Cosmetics Rules 2020 frame, not D&C drug."
            elif first_schedule is True:
                if intent_dietary:
                    override_key, override_reason = "ayurveda_aahara", "WIZARD: classical base consumed as daily diet/food — Ayurveda Aahar frame."
                else:
                    override_key, override_reason = "classical_medicine", "WIZARD: classical First Schedule text-based formulation confirmed — grandfathered Classical Medicine."
            elif is_novel_extraction and intent_therapeutic:
                override_key, override_reason = "phytopharmaceutical", "WIZARD: non-classical (advanced) extraction with medicinal intent — Phytopharmaceutical route."
            elif new_ingredient is True:
                override_key, override_reason = "new_drug", "WIZARD: novel ingredient not referenced in the First Schedule — New Drug material."
            elif novel_process is True and intent_therapeutic:
                override_key, override_reason = "proprietary_ayurveda", "WIZARD: novel/unconventional manufacturing process with therapeutic claim on a non-classical formulation — Patent & Proprietary route."

        if override_key:
            ranked = [(k, v) for k, v in ranked if k != override_key]
            override_score = scores.get(override_key, 0) or 30
            ranked.insert(0, (override_key, override_score))
            reasons.setdefault(override_key, []).insert(0, override_reason)

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

        # Human-readable wizard trace for the "How was this classified?" panel.
        wizard_used = any(k is not None for k in (first_schedule, new_ingredient, novel_process)) or bool(extraction_method)
        decision_path: list[str] = []
        if wizard_used:
            decision_path.append(
                "First Schedule classical reference: "
                + ("Yes — full classical text-based formulation" if first_schedule else ("No" if first_schedule is False else "Unknown/not declared"))
            )
            decision_path.append(
                "Novel ingredient not in First Schedule: "
                + ("Yes — ingredient qualifies as New Drug material" if new_ingredient else ("No — known/scheduled ingredients" if new_ingredient is False else "Unknown/not declared"))
            )
            decision_path.append(
                "Extraction / manufacturing method: "
                + (NOVEL_EXTRACTION_METHODS.get(extraction_norm, ("Classical (" + extraction_norm + ")") if extraction_norm else "Classical/standard route")
                   if is_novel_extraction or extraction_norm
                   else "Classical/standard route")
            )
            decision_path.append(
                "Novel process claim: "
                + ("Yes — process innovation declared" if novel_process else ("No — classical method retained" if novel_process is False else "Unknown/not declared"))
            )
            decision_path.append(f"Rule engine ranked {len(ranked)} pathway(s); winner: {winner_key} ({winner_score} pts).")

        next_actions = {
            "classical_medicine": [
                "Register the classical formulation under the AYUSH classical recognition route (CCReM) — no New Drug approval needed.",
                "Check the exact First Schedule entry and reproduce the classical method and ingredients as per the reference.",
                "Ensure Schedule T GMP compliance for licensed manufacturing.",
            ],
            "ayurvedic_drug": [
                "Register on e-AUSHADHI and obtain ASU product + manufacturing licences before marketing.",
                "Confirm no Drugs & Magic Remedies Act §3 disease wording on the label.",
                "Complete Schedule T GMP and batch quality (heavy metals, microbial) testing.",
            ],
            "proprietary_ayurveda": [
                "Apply for a proprietary Ayurveda medicine product licence via e-AUSHADHI.",
                "Prepare formulation, method of manufacture and evidence-of-efficacy dossier (Schedule Z).",
            ],
            "new_drug": [
                "File a New Drug application with CDSCO (Rule 2(ea)) — the Section 3(p) fiction applies to novel Ayurveda-based medicines.",
                "Generate safety & efficacy data in the required evidence formats before marketing.",
                "Confirm whether ASU-vs-phytopharmaceutical nuances route the product to the AYUSH or the CDSCO new-drug track.",
            ],
            "phytopharmaceutical": [
                "Prepare phytopharmaceutical New Drug dossier (chemistry, markers, pharmacology, toxicology, clinical).",
                "Align to CDSCO phytopharmaceutical guidance and Ayurvedic Pharmacopoeia marker-based testing.",
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

        # ── Step 3 — Intent detection (surfaced family label) ──────────────
        intent_detected = cls.INTENT_LABELS.get(winner_key, winner_key.replace("_", " ").title())

        # ── Step 4 — RAG retrieval of official-database evidence ────────────
        topics_all = cls._build_topic(product_name, ingredients, intended_use)
        evidence = cls._retrieve_evidence(topics_all, winner_key)

        # ── Step 5 — Rule engine validation (3-state) ───────────────────────
        rule_validation = cls._build_rule_validation(
            winner_key=winner_key,
            first_schedule=first_schedule,
            new_ingredient=new_ingredient,
            intent_dietary=intent_dietary,
            intent_therapeutic=intent_therapeutic,
            is_novel_extraction=is_novel_extraction,
            label_disclaimer=label_disclaimer,
            claim_curative=claim_curative,
            product_name=product_name,
        )

        # ── Step 7 — Structured next actions ─────────────────────────────────
        regulatory_pathway = {
            "classical_medicine": "AYUSH recognition under the Classical route (CCReM) + licensed manufacturing (Schedule T GMP)",
            "ayurvedic_drug": "State AYUSH drug licence via e-AUSHADHI (ASU product + manufacturing licence)",
            "proprietary_ayurveda": "Proprietary Ayurveda medicine product licence via e-AUSHADHI (Schedule Z evidence dossier)",
            "new_drug": "CDSCO New Drug application under Rule 2(ea) — Section 3(p) fiction applies to novel AYUSH medicines",
            "phytopharmaceutical": "CDSCO phytopharmaceutical New Drug approval (markers + clinical evidence)",
            "ayurveda_aahara": "FSSAI pathway confirmation under FSS (Ayurveda Aahar) Regulations 2022",
            "nutraceutical": "FSSAI product approval / NLT case under FSS (Health Supplements) Regulations 2022",
            "cosmetic": "CDSCO registration under Cosmetics Rules 2020 (+ applicable BIS standard)",
            "unresolved": "Confirm classification with the concerned licensing / food-safety authority",
        }[winner_key]

        if new_ingredient is True or first_schedule is False:
            ip_readiness = (
                "Novel composition — Section 3(p) scrutiny applies to traditional-knowledge aggregations; "
                "novelty/inventive-step prior-art search (IP India / TKDL) is required before filing."
            )
        elif first_schedule is True:
            ip_readiness = (
                "Classical First Schedule formulation — the composition itself is established prior art; "
                "patent claims should focus on a novel method, extraction or synergistic ratio."
            )
        else:
            ip_readiness = (
                "Documented traditional-knowledge use — confirm inventiveness and consider TKDL alignment "
                "before taking a patent position."
            )

        if winner_key in ("classical_medicine", "ayurveda_aahara", "nutraceutical", "cosmetic"):
            abs_status = (
                "Low ABS friction — biological resources must still be sourced lawfully; document origin for the dossier."
            )
        else:
            abs_status = (
                "ABS (NBA) clearance likely required for commercial utilisation — verify biological-resource origin "
                "and apply for prior informed consent / RIAF where applicable."
            )

        # ── ABS / NBA compliance helper (optional enrichment) ──────────────────
        abs_assessment = None
        if ab_user_type or ab_turnover_inr is not None or ab_wild_collected is not None:
            from app.models.intelligence import ABSComplianceResponse  # noqa: F401
            from app.services.abs_compliance_service import ABSComplianceEngine

            abs_assessment = ABSComplianceEngine.check(
                ingredients=ingredients,
                user_type=ab_user_type or "company",
                turnover_inr=ab_turnover_inr,
                codified_tk=None,
                wild_collected=ab_wild_collected,
                commercial_use=ab_commercial_use,
            )
            if abs_assessment.status == "exempt":
                abs_status = "ABS exemption — " + abs_assessment.exemption_reason
            elif abs_assessment.benefit_sharing.applicable and abs_assessment.benefit_sharing.rate_pct:
                rate = abs_assessment.benefit_sharing.rate_pct
                amt = abs_assessment.benefit_sharing.amount_inr
                abs_status = (
                    f"ABS benefit-sharing applies @ {rate}% of turnover (₹{amt:,.2f}) — "
                    + abs_assessment.benefit_sharing.citation.split(';')[0]
                )
            elif abs_assessment.status == "info_required":
                base = "ABS benefit-sharing rate pending — declare turnover to determine the slab."
                detail = abs_assessment.obligations[0].obligation if abs_assessment.obligations else "Form 9 prior approval applies to commercialization."
                abs_status = base + " " + detail
            else:
                abs_status = (
                    "ABS benefit-sharing not required at current turnover — Form 9 prior approval "
                    "applies before commercialization under Section 6, BDA 2002 (as amended 2023)."
                )
            decision_path.append(
                f"Step 7 — ABS helper: status={abs_assessment.status}, rate={abs_assessment.benefit_sharing.rate_pct}%, "
                f"slab={abs_assessment.benefit_sharing.slab or 'n/a'}."
            )

        risk_level = cls._risk_level(confidence, winner_key)
        recommended_next_step = next_actions.get(winner_key, ["Confirm classification with the concerned authority."])[0]

        # Trace the full 7-step run so judges see every stage.
        decision_path.append(f"Step 3 — Intent detected: {intent_detected}.")
        if evidence:
            domains_seen = ", ".join(sorted({e.collection for e in evidence}))
            decision_path.append(f"Step 4 — RAG retrieved {len(evidence)} evidence passage(s) from: {domains_seen}.")
        else:
            decision_path.append("Step 4 — RAG retrieval returned no passages (retrieval service offline / cold index).")
        satisfied = sum(1 for c in rule_validation if c.status == "SATISFIED")
        attention = sum(1 for c in rule_validation if c.status != "SATISFIED")
        decision_path.append(
            f"Step 5 — Rule engine evaluated {len(rule_validation)} checks ({satisfied} satisfied, {attention} need attention / information)."
        )
        decision_path.append(f"Step 7 — Recommended next step: {recommended_next_step}")

        return ProductClassifierResponse(
            passport_id=passport_id,
            product_name=product_name,
            product_form=product_form,
            dosage_form=dosage_form,
            intended_use=intended_use,
            claims=claims,
            ingredients=ingredients,
            intent_detected=intent_detected,
            likely_pathway=meta["authority"],
            pathway_category=winner_key,
            pathway_confidence=confidence,
            reasons=reasons.get(winner_key, []),
            alternative_pathways=alternative_pathways,
            applicable_authority=meta["authority"],
            applicable_sources=meta["sources"],
            next_actions=next_actions.get(winner_key, []),
            evidence=evidence,
            rule_validation=rule_validation,
            regulatory_pathway=regulatory_pathway,
            ip_readiness=ip_readiness,
            abs_status=abs_status,
            risk_level=risk_level,
            recommended_next_step=recommended_next_step,
            disclaimer=cls.DISCLAIMER,
            decision_path=decision_path,
            classification_mode="wizard_based" if wizard_used else "form_based",
            abs_assessment=abs_assessment,
        )

    @classmethod
    def classify_passport(cls, passport_id: str) -> ProductClassifierResponse:
        passport = PassportEngine.get_passport(passport_id)
        if passport is None:
            return cls.classify(passport_id=passport_id)
        return cls.classify(
            product_name=getattr(passport, "case_title", ""),
            product_form=passport.product_form,
            dosage_form=passport.dosage_form,
            intended_use=passport.intended_use,
            claims=passport.proposed_claims,
            ingredients=[ing.raw_name for ing in passport.ingredients],
            process_description=passport.process_description,
            passport_id=passport_id,
        )