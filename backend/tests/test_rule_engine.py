from app.services.passport_engine import PassportEngine
from app.services.rule_engine import DeterministicRuleEngine
from app.models.regulatory import RuleConditionState
from app.core.confidence import ConfidenceBand

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
