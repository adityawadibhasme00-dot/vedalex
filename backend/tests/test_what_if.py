from app.services.passport_engine import PassportEngine
from app.services.what_if_engine import WhatIfSimulatorEngine

def test_what_if_simulation_disease_claim():
    passport = PassportEngine.create_from_intake(
        raw_text="Ashwagandha + Brahmi formulation, claim: supports healthy sleep, target markets: India, USA, Canada",
        user_lang="en"
    )

    response = WhatIfSimulatorEngine.simulate_claim_mutation(
        passport,
        mutated_claims=["Treats chronic insomnia and reverses anxiety disorders"]
    )

    assert response.affected_nodes_count >= 2
    us_diff = next(d for d in response.diffs if d.jurisdiction == "United States")
    assert "Unapproved New Drug" in us_diff.new_classification
    assert us_diff.impact_severity == "CRITICAL_BURDEN_INCREASE"
    assert any("Investigational New Drug" in r for r in us_diff.new_requirements)

    in_diff = next(d for d in response.diffs if d.jurisdiction == "India")
    assert "ASU Patent / Proprietary" in in_diff.new_classification
    assert any("State AYUSH Drug" in r for r in in_diff.new_requirements)
