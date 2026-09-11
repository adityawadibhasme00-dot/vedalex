from typing import Dict, Any, List
from app.models.passport import InnovationPassport
from app.models.regulatory import RegulatoryFinding

class ProvenanceEngine:
    """
    Builds the Traceable Decision Workspace ('Why?' View) (Section 6.8).
    Creates an inspectable graph mapping User Fact -> Evaluated Condition -> Statutory Gazette Section -> Finding.
    """

    @classmethod
    def generate_provenance_graph(
        cls,
        passport: InnovationPassport,
        finding: RegulatoryFinding
    ) -> Dict[str, Any]:
        nodes = []
        edges = []

        # 1. Fact Nodes
        for idx, ing in enumerate(passport.ingredients):
            node_id = f"fact-ing-{idx}"
            nodes.append({
                "id": node_id,
                "type": "USER_FACT",
                "label": f"Ingredient: {ing.raw_name} ({ing.botanical_name or 'Botanical'})",
                "status": ing.origin_status,
                "details": f"Part: {ing.plant_part}, Ratio: {ing.quantity_percentage}%"
            })
            edges.append({
                "source": node_id,
                "target": "rule-eval-node",
                "relation": "evaluated_by"
            })

        claim_node_id = "fact-claim-0"
        nodes.append({
            "id": claim_node_id,
            "type": "USER_CLAIM",
            "label": f"Proposed Claim: '{passport.proposed_claims[0] if passport.proposed_claims else 'General'}'",
            "status": "user_confirmed"
        })
        edges.append({
            "source": claim_node_id,
            "target": "rule-eval-node",
            "relation": "triggers"
        })

        # 2. Rule Evaluation Node
        nodes.append({
            "id": "rule-eval-node",
            "type": "DETERMINISTIC_RULE",
            "label": f"Evaluated Rule: {finding.pathway_category}",
            "jurisdiction": finding.jurisdiction,
            "condition_state": finding.status
        })

        # 3. Citation Nodes
        for c_idx, cite in enumerate(finding.supporting_citations):
            cite_node_id = f"citation-{c_idx}"
            nodes.append({
                "id": cite_node_id,
                "type": "STATUTORY_CITATION",
                "label": f"{cite.act_title} ({cite.section_reference})",
                "authority": cite.authority,
                "effective_date": cite.effective_date,
                "passage_excerpt": cite.exact_passage[:150] + "..."
            })
            edges.append({
                "source": "rule-eval-node",
                "target": cite_node_id,
                "relation": "grounded_in_law"
            })
            edges.append({
                "source": cite_node_id,
                "target": "finding-node",
                "relation": "substantiates"
            })

        # 4. Final Finding Node
        nodes.append({
            "id": "finding-node",
            "type": "DECISION_FINDING",
            "label": f"Classification: {finding.pathway_category}",
            "confidence": finding.confidence,
            "jurisdiction": finding.jurisdiction
        })

        return {
            "passport_id": passport.id,
            "jurisdiction": finding.jurisdiction,
            "nodes": nodes,
            "edges": edges,
            "verifiable_paper_trail": True
        }
