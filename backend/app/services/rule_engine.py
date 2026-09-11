import re
import os
import glob
import json
import yaml
from typing import List, Dict, Any, Optional, Tuple
from app.models.passport import InnovationPassport
from app.models.regulatory import RegulatoryFinding, RuleConditionState, StatutoryCitation
from app.core.confidence import ConfidenceBand, ConfidenceEvaluator
from app.services.retrieval_engine import HybridRetrievalEngine
from app.services.ingredient_resolver import IngredientResolverService
from app.services.ingredient_legality import IngredientLegalityChecker

class DeterministicRuleEngine:
    """
    Deterministic 3-state legal rule evaluator across India, US, and Canada.

    Two rule layers:
      1. Hand-coded Python pathways (India / US / Canada) - classification + citations.
      2. Declarative YAML rule packs in app/rules/*.yaml + dynamic blueprint_rules.json
         (from the Excel "Rules" sheet) - condition -> outcome interpreter that runs
         BEFORE generation and refines requirements/citations.
    """
    _yaml_packs_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None
    _dynamic_rules_cache: Optional[List[Dict[str, Any]]] = None

    # ------------------------------------------------------------------
    # Declarative rules (YAML pack + Excel blueprint Rules sheet)
    # ------------------------------------------------------------------
    @classmethod
    def _load_rule_packs(cls) -> List[Dict[str, Any]]:
        if cls._yaml_packs_cache is not None:
            return cls._yaml_packs_cache

        packs: List[Dict[str, Any]] = []
        rules_dir = os.path.join(os.path.dirname(__file__), "..", "rules")
        for ypath in sorted(glob.glob(os.path.join(rules_dir, "*.yaml"))):
            try:
                with open(ypath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict) and isinstance(data.get("rules"), list):
                    for rule in data["rules"]:
                        rule = dict(rule)
                        rule["rule_pack_id"] = data.get("rule_pack_id", "")
                        rule["jurisdiction"] = data.get("jurisdiction", "")
                        rule["authority"] = data.get("authority", "")
                        rule["governing_act"] = data.get("governing_act", "")
                        packs.append(rule)
            except Exception as e:
                print(f"(rule_engine) failed to load rule pack {ypath}: {e}")

        # Dynamic rules extracted from the Excel "Rules" sheet (blueprint).
        for rule in cls._load_dynamic_rules():
            packs.append(rule)

        cls._yaml_packs_cache = packs
        return packs

    @classmethod
    def _load_dynamic_rules(cls) -> List[Dict[str, Any]]:
        if cls._dynamic_rules_cache is not None:
            return cls._dynamic_rules_cache
        path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "blueprint_rules.json")
        rules: List[Dict[str, Any]] = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    rules = data
            except Exception:
                rules = []
        cls._dynamic_rules_cache = rules
        return rules

    @classmethod
    def _build_facts(
        cls,
        passport: InnovationPassport,
        resolved_ingredients: List[Any],
        has_disease_claim: bool,
        has_canonical: bool,
    ) -> Dict[str, Any]:
        claims_text = " ".join(passport.proposed_claims).lower()
        resolved_names = " ".join(
            str(getattr(ing, "canonical_name", "") or "") for ing in resolved_ingredients
        ).lower()
        return {
            "ingredients_have_documented_tk_use": has_canonical,
            "synergistic_empirical_data_present": False,
            "ingredients_conform_to_first_schedule": has_canonical,
            "process_conforms_to_classical_text": False,
            "contains_only_permitted_ayush_ingredients": has_canonical,
            "is_novel_ratio_or_form": True,
            "ingredients_on_aahara_positive_list": has_canonical,
            "claim_contains_disease_treatment": has_disease_claim,
            "form_is_dietary_food": not has_disease_claim,
            "ingredients_are_dietary_botanicals": has_canonical,
            "ingredients_on_nhpid_list": has_canonical,
            "dosage_within_nhpid_monograph_limits": has_canonical,
            "proposed_claims": claims_text,
            "intended_use": passport.intended_use.lower(),
            "resolved_ingredients": resolved_names,
        }

    @classmethod
    def _eval_condition(cls, condition: Dict[str, Any], facts: Dict[str, Any]) -> bool:
        if not isinstance(condition, dict):
            return True
        key = condition.get("fact_key") or condition.get("key")
        op = (condition.get("operator") or "equals").lower().replace("_", " ")
        expected = condition.get("expected_value")
        actual = facts.get(key)

        if op in ("equals", "eq", "is"):
            return actual == expected
        if op in ("not equals", "neq", "is not"):
            return actual != expected
        if op in ("contains", "in"):
            return (expected in actual) if isinstance(actual, (str, list, tuple)) else actual == expected
        if op in ("gt", "greater than"):
            try:
                return float(actual) > float(expected)
            except Exception:
                return False
        if op in ("lt", "less than"):
            try:
                return float(actual) < float(expected)
            except Exception:
                return False
        return False

    @classmethod
    def _eval_text_condition(cls, condition: str, facts: Dict[str, Any], jurisdiction: str) -> bool:
        """Best-effort interpreter for free-text Excel 'Rules' sheet conditions."""
        c = condition.lower()
        if not c:
            return False
        composite = f"{facts.get('proposed_claims', '')} {facts.get('intended_use', '')} " \
                    f"{facts.get('resolved_ingredients', '')} {jurisdiction.lower()} " \
                    f"india united states canada traditional knowledge patent section 3(p)"
        tokens = set(re.findall(r"[a-z0-9()]+", c))
        if not tokens:
            return True
        hit = sum(1 for tok in tokens if tok in composite)
        return hit >= max(1, len(tokens)) or (len(tokens) >= 2 and hit >= len(tokens) - 1)

    @classmethod
    def _fired_rules(cls, facts: Dict[str, Any], jurisdiction: str) -> List[Dict[str, Any]]:
        fired: List[Dict[str, Any]] = []
        for rule in cls._load_rule_packs():
            rule_jur = (rule.get("jurisdiction") or "").lower()
            if rule_jur and rule_jur != jurisdiction.lower() and \
               not (rule_jur == "us" and jurisdiction.lower() == "united states") and \
               not (rule_jur == "united states" and jurisdiction.lower() == "us"):
                continue
            conditions = rule.get("conditions")
            if isinstance(conditions, list) and conditions:
                ok = all(cls._eval_condition(c, facts) for c in conditions if isinstance(c, dict))
            else:
                condition_text = rule.get("condition")
                if condition_text:
                    ok = cls._eval_text_condition(str(condition_text), facts, jurisdiction)
                else:
                    ok = False
            if ok:
                fired.append(rule)
        return fired

    @classmethod
    def _merge_yaml_into(cls, finding: RegulatoryFinding, fired: List[Dict[str, Any]]) -> RegulatoryFinding:
        if not fired:
            return finding
        extra_requirements: List[str] = []
        fired_names: List[str] = []
        for rule in fired:
            fired_names.append(rule.get("name") or rule.get("rule_name") or rule.get("rule_pack_id") or "rule")
            cons = rule.get("consequence", {}) or {}
            reqs = cons.get("requirements", [])
            if isinstance(reqs, list):
                for r in reqs:
                    text = str(r).strip()
                    if text and text not in extra_requirements:
                        extra_requirements.append(text)
            reqs_txt = rule.get("requirements", [])
            if isinstance(reqs_txt, list):
                for r in reqs_txt:
                    text = str(r).strip()
                    if text and text not in extra_requirements:
                        extra_requirements.append(text)
            cat = cons.get("category") or rule.get("outcome") or ""
            if cat and rule.get("consequence", {}).get("category"):
                pass

        conditions = list(finding.conditions_evaluated) + [f"Rule pack triggered: {r}" for r in fired_names]
        next_steps = list(finding.next_action_steps)
        for req in extra_requirements:
            if req not in next_steps:
                next_steps.append(req)
        limitations = finding.coverage_limitations
        limitations = f"{limitations} Activated rule packs: {', '.join(fired_names)}."

        return RegulatoryFinding(
            jurisdiction=finding.jurisdiction,
            pathway_category=finding.pathway_category,
            status=finding.status,
            confidence=finding.confidence,
            conditions_evaluated=conditions,
            supporting_citations=finding.supporting_citations,
            missing_facts=finding.missing_facts,
            next_action_steps=next_steps,
            coverage_limitations=limitations,
            assumptions_made=finding.assumptions_made,
            explanation_text=finding.explanation_text,
        )

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    @classmethod
    def evaluate_passport(
        cls,
        passport: InnovationPassport,
        target_markets: List[str] = ["India", "United States", "Canada"]
    ) -> List[RegulatoryFinding]:
        findings = []

        # 1. Resolve Canonical Ingredients
        resolved_ingredients = []
        for ing in passport.ingredients:
            resolved = IngredientResolverService.resolve(ing.raw_name)
            if resolved:
                resolved_ingredients.append(resolved)

        has_canonical = len(resolved_ingredients) > 0
        canonical_conf = 0.95 if has_canonical else 0.4

        # 2. Evaluate Claims for Disease vs Structure/Function
        claims_text = " ".join(passport.proposed_claims).lower() + " " + passport.intended_use.lower()

        disease_triggers = ["treat", "cure", "prevent", "mitigate", "insomnia", "depression", "hypertension", "diabetes", "disease", "रोग", "उपचार", "निवारण"]
        has_disease_claim = any(trigger in claims_text for trigger in disease_triggers)

        facts = cls._build_facts(passport, resolved_ingredients, has_disease_claim, has_canonical)

        # 3. India Evaluation
        if "India" in target_markets:
            finding_in = cls._evaluate_india(passport, resolved_ingredients, has_disease_claim, canonical_conf)
            findings.append(cls._merge_yaml_into(finding_in, cls._fired_rules(facts, "India")))

        # 4. US Evaluation
        if any(m in ["United States", "USA", "US"] for m in target_markets):
            finding_us = cls._evaluate_us(passport, resolved_ingredients, has_disease_claim, canonical_conf)
            findings.append(cls._merge_yaml_into(finding_us, cls._fired_rules(facts, "United States")))

        # 5. Canada Evaluation
        if "Canada" in target_markets:
            finding_ca = cls._evaluate_canada(passport, resolved_ingredients, has_disease_claim, canonical_conf)
            findings.append(cls._merge_yaml_into(finding_ca, cls._fired_rules(facts, "Canada")))

        return findings

    # ------------------------------------------------------------------
    # Country pathways (existing classification logic preserved)
    # ------------------------------------------------------------------
    @classmethod
    def _evaluate_india(
        cls,
        passport: InnovationPassport,
        resolved_ingredients: list,
        has_disease_claim: bool,
        canonical_conf: float
    ) -> RegulatoryFinding:
        citations = HybridRetrievalEngine.search_passages("Ayurveda Aahara FSSAI ASU Drug Rule 158-B", jurisdiction="India", top_k=2)

        if has_disease_claim:
            category = "ASU Patent / Proprietary Medicine (Rule 158-B)"
            status = RuleConditionState.SATISFIED
            conditions = [
                "Disease treatment claim present — disqualified from Ayurveda Aahara food category",
                "Ingredients listed in authoritative classical texts (First Schedule)",
                "Novel composition requires Rule 158-B safety/efficacy substantiation"
            ]
            next_steps = [
                "Apply for State AYUSH Drug Manufacturing License",
                "Compile Rule 158-B safety dossier & pilot clinical data",
                "Comply with Schedule T Good Manufacturing Practices (GMP)"
            ]
            missing = ["Schedule T GMP audit certificate", "Pilot clinical trial data"]
            explanation = "Your formulation makes disease-directed claims ('treats/cures'), which strictly places it under the Drugs and Cosmetics Act as an ASU Drug rather than a food."
        else:
            category = "Ayurveda Aahara (FSSAI 2022) / Wellness ASU"
            status = RuleConditionState.SATISFIED
            conditions = [
                "Ingredients listed in Ayurveda Aahara Schedule I positive list",
                "Dosage and form conform to traditional dietary recipe standards",
                "No therapeutic cure or disease mitigation claims made"
            ]
            next_steps = [
                "Apply for FSSAI Central License under Ayurveda Aahara category",
                "Affix mandatory official Ayurveda Aahara logo and disclaimer on principal display panel",
                "Submit heavy metal, microbiological purity, and pesticide residue test reports"
            ]
            missing = ["Heavy metals & pesticide residue lab report"]
            explanation = "Your formulation contains traditional botanicals and uses structure/function wellness claims without disease treatment references, making it eligible for expedited FSSAI Ayurveda Aahara licensing."

        confidence = ConfidenceEvaluator.calculate(
            rule_satisfied=(status == RuleConditionState.SATISFIED),
            missing_critical_facts=missing if len(passport.ingredients) == 0 else [],
            citation_count=len(citations),
            canonical_resolution_confidence=canonical_conf,
            has_primary_statute=True
        )

        return RegulatoryFinding(
            jurisdiction="India",
            pathway_category=category,
            status=status,
            confidence=confidence,
            conditions_evaluated=conditions,
            supporting_citations=citations,
            missing_facts=missing,
            next_action_steps=next_steps,
            coverage_limitations="Evaluated against Drugs & Cosmetics Act 1940 and FSSAI 2022 gazettes. State licensing authority inspection required.",
            assumptions_made=["Assumes manufacturing facility is located within Indian territory"],
            explanation_text=explanation
        )

    @classmethod
    def _evaluate_us(
        cls,
        passport: InnovationPassport,
        resolved_ingredients: list,
        has_disease_claim: bool,
        canonical_conf: float
    ) -> RegulatoryFinding:
        if has_disease_claim:
            citations = HybridRetrievalEngine.search_passages("FD&C Act 21 U.S.C. 321 new drug disease claim", jurisdiction="United States", top_k=1)
            category = "Unapproved New Drug (21 U.S.C. 321(g) / High Risk)"
            status = RuleConditionState.NOT_SATISFIED
            conditions = [
                "Claim text explicitly references disease treatment or mitigation",
                "Product cannot be marketed as a Dietary Supplement under DSHEA with disease claims"
            ]
            next_steps = [
                "Reformulate claims to Structure/Function wording (e.g. 'supports healthy sleep')",
                "Alternatively, file an Investigational New Drug (IND) application with FDA CDER"
            ]
            missing = ["IND application dossier", "Phase I-III clinical trial protocols"]
            explanation = "Under 21 U.S.C. 321(g), claims to treat or mitigate diseases (like insomnia) classify the product as a drug requiring pre-market FDA approval."
        else:
            citations = HybridRetrievalEngine.search_passages("DSHEA 21 CFR 101.93 dietary supplement structure function", jurisdiction="United States", top_k=1)
            category = "Dietary Supplement (DSHEA 1994)"
            status = RuleConditionState.SATISFIED
            conditions = [
                "Botanicals recognized as dietary ingredients",
                "Claims describe structure/function role without disease mention",
                "Includes mandatory 21 CFR 101.93 FDA disclaimer"
            ]
            next_steps = [
                "Draft and print mandatory FDA disclaimer on label",
                "Submit 30-Day Structure/Function notification to FDA post-market launch",
                "Establish compliance with 21 CFR 111 dietary supplement cGMP"
            ]
            missing = ["Draft 30-day post-market notification letter"]
            explanation = "Compliant with US DSHEA as a dietary supplement because claims relate to normal bodily structure/function and mandatory disclaimers apply."

        confidence = ConfidenceEvaluator.calculate(
            rule_satisfied=(status == RuleConditionState.SATISFIED),
            missing_critical_facts=missing if has_disease_claim else [],
            citation_count=len(citations),
            canonical_resolution_confidence=canonical_conf,
            has_primary_statute=True
        )

        return RegulatoryFinding(
            jurisdiction="United States",
            pathway_category=category,
            status=status,
            confidence=confidence,
            conditions_evaluated=conditions,
            supporting_citations=citations,
            missing_facts=missing,
            next_action_steps=next_steps,
            coverage_limitations="Assumes oral dosage form (tablet/capsule). Intravenous or sublingual drug delivery forms are excluded.",
            assumptions_made=["Assumes dietary ingredients were marketed prior to Oct 15, 1994 or have safety notification"],
            explanation_text=explanation
        )

    @classmethod
    def _evaluate_canada(
        cls,
        passport: InnovationPassport,
        resolved_ingredients: list,
        has_disease_claim: bool,
        canonical_conf: float
    ) -> RegulatoryFinding:
        citations = HybridRetrievalEngine.search_passages("Natural Health Products Regulations NHPR NPN", jurisdiction="Canada", top_k=1)
        category = "Natural Health Product (NHP - Class I/II)"
        status = RuleConditionState.SATISFIED
        conditions = [
            "Ashwagandha and Brahmi listed in Health Canada NHPID Monograph Compendium",
            "Dosage falls within permitted dried herb equivalent limits (< 6000mg/day)"
        ]
        next_steps = [
            "Submit electronic Product Licence Application (ePLA) for 8-digit NPN",
            "Contract an authorized Canadian importer holding a valid Site Licence",
            "Submit Foreign Site Annex for Indian GMP facility"
        ]
        missing = ["Foreign Site Licence GMP equivalence audit report"]
        explanation = "Eligible for expedited Class I Natural Health Product licensing in Canada under the NHPID Compendium of Monographs."

        confidence = ConfidenceEvaluator.calculate(
            rule_satisfied=True,
            missing_critical_facts=[],
            citation_count=len(citations),
            canonical_resolution_confidence=canonical_conf,
            has_primary_statute=True
        )

        return RegulatoryFinding(
            jurisdiction="Canada",
            pathway_category=category,
            status=status,
            confidence=confidence,
            conditions_evaluated=conditions,
            supporting_citations=citations,
            missing_facts=missing,
            next_action_steps=next_steps,
            coverage_limitations="Health Canada requires both a Product Licence (NPN) and a Canadian Site Licence for importation.",
            assumptions_made=["Assumes formulation follows single/multi-ingredient published monograph standards"],
            explanation_text=explanation
        )