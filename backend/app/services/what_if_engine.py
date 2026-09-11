import copy
from typing import Dict, Any, List
from app.models.passport import InnovationPassport
from app.models.diff import WhatIfDiffItem, WhatIfSimulationResponse
from app.services.rule_engine import DeterministicRuleEngine
from app.services.retrieval_engine import HybridRetrievalEngine

class WhatIfSimulatorEngine:
    """
    Reactive What-If Simulator Engine (Section 6.6).
    Clones passport, mutates target variables, and generates semantic diffs showing altered risks,
    removed requirements, and newly required clinical evidence without full case recomputation.
    """

    @classmethod
    def simulate_claim_mutation(
        cls,
        original_passport: InnovationPassport,
        mutated_claims: List[str]
    ) -> WhatIfSimulationResponse:
        # Clone passport
        cloned_passport = copy.deepcopy(original_passport)
        cloned_passport.proposed_claims = mutated_claims

        # Original Findings vs Mutated Findings
        orig_findings = DeterministicRuleEngine.evaluate_passport(original_passport)
        mutated_findings = DeterministicRuleEngine.evaluate_passport(cloned_passport)

        diffs: List[WhatIfDiffItem] = []
        affected_count = 0

        orig_map = {f.jurisdiction: f for f in orig_findings}
        for mut_f in mutated_findings:
            orig_f = orig_map.get(mut_f.jurisdiction)
            if not orig_f:
                continue

            # Check if classification or requirements changed
            if (orig_f.pathway_category != mut_f.pathway_category) or (orig_f.status != mut_f.status):
                affected_count += 1
                
                # Determine impact severity
                severity = "MODERATE_BURDEN_INCREASE"
                risk_alert = "Classification shifted due to promotional claim alteration."
                removed_reqs = []
                new_reqs = []

                if mut_f.jurisdiction == "United States":
                    if "Unapproved New Drug" in mut_f.pathway_category:
                        severity = "CRITICAL_BURDEN_INCREASE"
                        risk_alert = "Disease claim triggers FDA 21 U.S.C. 321(g) Drug Classification. Prohibits marketing as Dietary Supplement without approved NDA."
                        removed_reqs = ["DSHEA 30-Day Structure/Function Notification"]
                        new_reqs = ["Investigational New Drug (IND) Application", "Phase I-III Clinical Trial Evidence"]

                elif mut_f.jurisdiction == "India":
                    if "ASU Patent / Proprietary" in mut_f.pathway_category:
                        severity = "HIGH_BURDEN_INCREASE"
                        risk_alert = "Disqualified from FSSAI Ayurveda Aahara food category; must obtain State AYUSH Drug Manufacturing License under Rule 158-B."
                        removed_reqs = ["FSSAI Ayurveda Aahara Central Food License"]
                        new_reqs = ["State AYUSH Drug Manufacturing License", "Rule 158-B Safety & Efficacy Dossier", "Schedule T GMP Audit"]

                diffs.append(WhatIfDiffItem(
                    jurisdiction=mut_f.jurisdiction,
                    prior_classification=orig_f.pathway_category,
                    new_classification=mut_f.pathway_category,
                    impact_severity=severity,
                    risk_alert=risk_alert,
                    removed_requirements=removed_reqs,
                    new_requirements=new_reqs,
                    new_citations=mut_f.supporting_citations
                ))

        return WhatIfSimulationResponse(
            original_claims=original_passport.proposed_claims,
            mutated_claims=mutated_claims,
            affected_nodes_count=affected_count,
            diffs=diffs
        )
