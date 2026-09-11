from typing import List, Dict, Any
from app.models.passport import InnovationPassport

class RedTeamModule:
    """
    'Challenge My Innovation' Red-Team Module (Section 6.7).
    Surfaces 2-3 patent examiner-style objections across Section 3(p) TK aggregation,
    novelty, inventive step, and regulatory claim exposure before filing.
    """

    @classmethod
    def challenge_innovation(cls, passport: InnovationPassport) -> Dict[str, Any]:
        objections = []

        # 1. Section 3(p) Traditional Knowledge Objection
        has_classical_pair = any(ing.canonical_id == "ING-ASHWAGANDHA" for ing in passport.ingredients) and \
                             any(ing.canonical_id == "ING-BRAHMI" for ing in passport.ingredients)
        
        if has_classical_pair:
            objections.append({
                "objection_id": "OBJ-IPO-SEC3P-01",
                "authority_simulated": "Indian Patent Office (IPO) — Senior Patent Examiner",
                "legal_basis": "Section 3(p) of the Patents Act, 1970 & TK Examination Guidelines",
                "objection_title": "Anticipation by Traditional Knowledge & Obvious Combination",
                "summary": "The combination of Ashwagandha (Withania somnifera) and Brahmi (Bacopa monnieri) for cognitive calm and sleep induction is well documented in Charaka Samhita (Chikitsa Sthana) and Ayurvedic Pharmacopoeia of India. In the absence of comparative synergy data showing statistically significant efficacy beyond individual additive effects, the claims are barred under Section 3(p).",
                "investigable_action": "Conduct in-vitro combination-index (Chou-Talalay method) or animal behavioral assays comparing 1:1 mixture against individual single-herb doses to prove true synergism."
            })

        # 2. Labeling & Cross-Border Regulatory Objection
        objections.append({
            "objection_id": "OBJ-USFDA-WARNING-02",
            "authority_simulated": "US FDA Division of Dietary Supplement Programs",
            "legal_basis": "21 U.S.C. 343(r)(6) & FD&C Act Section 403(r)",
            "objection_title": "Implicit Disease Claim Exposure in Marketing Collateral",
            "summary": "While the primary claim is worded as 'supports healthy sleep', promotional references to stress-induced anxiety or insomnia on website meta-tags or accompanying packaging would classify the product as an unapproved new drug under 21 U.S.C. 321(g).",
            "investigable_action": "Review all secondary marketing channels and product packaging to ensure zero disease keywords appear alongside dietary supplement disclosures."
        })

        # 3. Biological Diversity Act / ABS Compliance Objection
        objections.append({
            "objection_id": "OBJ-NBA-BDA-03",
            "authority_simulated": "National Biodiversity Authority (NBA, India)",
            "legal_basis": "Section 6 of the Biological Diversity Act, 2002",
            "objection_title": "Mandatory NBA Approval for IP Filing on Indian Biological Resources",
            "summary": "Patent applications utilizing biological resources obtained from India require prior approval from the National Biodiversity Authority under Form III before patent grant. Commercial utilization without Benefit Sharing Agreements incurs penal liabilities.",
            "investigable_action": "Secure Form III approval from NBA India prior to patent sealing and maintain botanical sourcing vendor traceability records."
        })

        return {
            "passport_id": passport.id,
            "disclaimer": "Simulated examiner objections for investigable pre-filing triage only; not a formal legal verdict or rejection notice.",
            "total_objections": len(objections),
            "objections": objections
        }
