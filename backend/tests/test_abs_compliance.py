from app.services.abs_compliance_service import ABSComplianceEngine


def test_company_large_turnover():
    r = ABSComplianceEngine.check(
        ingredients=["Ashwagandha", "Brahmi"],
        user_type="company",
        turnover_inr=300_00_00_000,
    )
    assert r.status == "compliance_required"
    assert r.benefit_sharing.applicable is True
    assert r.benefit_sharing.rate_pct == 0.6
    assert r.benefit_sharing.amount_inr == 18_000_000.0
    assert "Form 9" in r.required_approvals[0]
    assert any("Benefit-sharing" in o.obligation for o in r.obligations)


def test_small_company_no_bs():
    r = ABSComplianceEngine.check(
        user_type="msme",
        turnover_inr=2_00_00_000,
    )
    assert r.benefit_sharing.applicable is False
    assert r.benefit_sharing.amount_inr == 0.0


def test_mid_slab_02pct():
    r = ABSComplianceEngine.check(user_type="startup", turnover_inr=20_00_00_000)
    assert r.benefit_sharing.rate_pct == 0.2
    assert r.benefit_sharing.amount_inr == 4_00_000.0


def test_ayush_practitioner_exempt_codified_tk():
    r = ABSComplianceEngine.check(
        ingredients=["Ashwagandha"],
        user_type="registered_ayush_practitioner",
        codified_tk=True,
    )
    assert r.status == "exempt"
    assert "Rule 14(2)" in r.exemption_reason
    assert r.required_approvals == []


def test_researcher_non_commercial_exempt():
    r = ABSComplianceEngine.check(
        user_type="researcher",
        commercial_use=False,
    )
    assert r.status == "exempt"


def test_missing_turnover_info_required():
    r = ABSComplianceEngine.check(user_type="company", commercial_use=True)
    assert r.status == "info_required"
    assert any(o.status == "info_required" for o in r.obligations)


def test_wild_collected_adds_sbb():
    r = ABSComplianceEngine.check(
        user_type="company",
        turnover_inr=10_00_00_000,
        wild_collected=True,
    )
    assert any("Biodiversity Board" in o.obligation for o in r.obligations)