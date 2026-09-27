from app.core.confidence import ConfidenceBand
from app.models.regulatory import RuleConditionState
from app.services.passport_engine import PassportEngine
from app.services.rule_engine import DeterministicRuleEngine


def test_deterministic_eval_wellness_claims():
    passport = PassportEngine.create_from_intake(
        raw_text="Ashwagandha + Brahmi formulation, claim: supports healthy sleep, target markets: India, USA, Canada",
        user_lang="en"
    )

    findings = DeterministicRuleEngine.evaluate_passport(passport)
    assert len(findings) == 3

    in_finding = next(f for f in findings if f.jurisdiction == "India")
    assert in_finding.status == RuleConditionState.SATISFIED
    assert in_finding.confidence == ConfidenceBand.HIGH
    assert "Ayurveda Aahara" in in_finding.pathway_category
    assert len(in_finding.supporting_citations) >= 1

    us_finding = next(f for f in findings if f.jurisdiction == "United States")
    assert us_finding.status == RuleConditionState.SATISFIED
    assert "Dietary Supplement" in us_finding.pathway_category
    assert "21 CFR 101.93" in us_finding.supporting_citations[0].section_reference

    ca_finding = next(f for f in findings if f.jurisdiction == "Canada")
    assert ca_finding.status == RuleConditionState.SATISFIED
    assert "Natural Health Product" in ca_finding.pathway_category


def test_facts_include_user_and_product_fields():
    from app.models.passport import IngredientEntry, InnovationPassport
    passport = InnovationPassport(
        business_role="Ayurveda MSME Manufacturer",
        manufacturing_location="India",
        biological_resource_origin="Domestic Cultivated (India)",
        target_markets=["India", "United States"],
        product_form="Tablet",
        ingredients=[IngredientEntry(raw_name="Ashwagandha")],
    )
    facts = DeterministicRuleEngine._build_facts(passport, [], False, True)
    assert facts["business_role"] == "ayurveda msme manufacturer"
    assert facts["manufacturing_location"] == "india"
    assert facts["biological_resource_origin"] == "domestic cultivated (india)"
    assert "india" in facts["target_markets"]
    assert facts["product_form"] == "tablet"


def test_findings_carry_spec_governance_fields():
    passport = PassportEngine.create_from_intake(
        raw_text="Ayurvedic multibotanical for diabetes relief, cure claimed, ingredients: Ashwagandha, Haritaki, target markets: India",
        user_lang="en"
    )
    findings = DeterministicRuleEngine.evaluate_passport(passport)
    in_finding = next(f for f in findings if f.jurisdiction == "India")

    assert hasattr(in_finding, "risk_level")
    assert hasattr(in_finding, "requires_human_review")
    assert isinstance(in_finding.requires_human_review, bool)
    assert isinstance(in_finding.applied_rules, list)

    for rule in in_finding.applied_rules:
        assert rule["rule_id"]
        assert rule["rule_version"]
        assert rule["effective_from"]
        assert rule["status"] in {"active", "draft", "superseded"}
        assert rule["risk_level"] in {"critical", "high", "medium", "low"}
        assert isinstance(rule["requires_human_review"], bool)
        assert rule["evidence"].get("source_id")
        assert rule["evidence"].get("locator")
        assert rule["evidence"].get("authority")


def test_classical_process_fires_classical_rule():
    passport = PassportEngine.create_from_intake(
        raw_text="Kwatha decoction of Ashwagandha per classical Sushruta Samhita text, First Schedule ASU, target markets: India only, no disease claim",
        user_lang="en"
    )
    findings = DeterministicRuleEngine.evaluate_passport(passport)
    in_finding = next(f for f in findings if f.jurisdiction == "India")
    rule_ids = [r["rule_id"] for r in in_finding.applied_rules]
    assert "RULE_ASU_CLASSICAL" in rule_ids


def test_ip_suite_rules_fire_for_distinctive_single_origin_botanical():
    from app.models.passport import IngredientEntry, InnovationPassport
    passport = InnovationPassport(
        case_title="Ashwagandha Originals",
        business_role="Ayurveda MSME Manufacturer",
        manufacturing_location="India",
        biological_resource_origin="Domestic Cultivated (India)",
        target_markets=["India"],
        product_form="Capsule",
        ingredients=[IngredientEntry(raw_name="Ashwagandha")],
        proposed_claims=["classical Ayurveda traditional rasayana use"],
        process_description="Classical Kwatha decoction followed by spray drying",
    )
    findings = DeterministicRuleEngine.evaluate_passport(passport)
    in_finding = next(f for f in findings if f.jurisdiction == "India")
    rule_ids = [r["rule_id"] for r in in_finding.applied_rules]
    assert "RULE_TM_GENERIC_NAME_BAR" not in rule_ids, "coined name should not be generic"
    assert "RULE_GI_INDIAN_ORIGIN_ELIGIBILITY" in rule_ids
    assert "RULE_TK_TKDL_PRIOR_ART_POINTER" in rule_ids
    assert "RULE_COPYRIGHT_LABEL_LITERATURE" in rule_ids
    assert "RULE_TK_CLASSICAL_TEXT_IDENTITY" in rule_ids


def test_generic_name_triggers_trademark_rule():
    from app.models.passport import IngredientEntry, InnovationPassport
    passport = InnovationPassport(
        case_title="Ayurvedic Herbal Tablet",
        business_role="Ayurveda Startup / MSME",
        manufacturing_location="India",
        biological_resource_origin="Domestic Cultivated (India)",
        target_markets=["India"],
        product_form="Tablet",
        ingredients=[IngredientEntry(raw_name="Ashwagandha")],
    )
    findings = DeterministicRuleEngine.evaluate_passport(passport)
    in_finding = next(f for f in findings if f.jurisdiction == "India")
    rule_ids = [r["rule_id"] for r in in_finding.applied_rules]
    assert "RULE_TM_GENERIC_NAME_BAR" in rule_ids
    tm_rule = next(r for r in in_finding.applied_rules if r["rule_id"] == "RULE_TM_GENERIC_NAME_BAR")
    assert tm_rule["risk_level"] == "high"
    assert tm_rule["requires_human_review"] is True
    assert tm_rule["evidence"]["source_id"]
