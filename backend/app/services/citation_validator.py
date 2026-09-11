from typing import List, Tuple
from app.models.regulatory import StatutoryCitation, RegulatoryFinding

class CitationValidator:
    """
    Audits generated findings and calculates the Unsupported Claim Rate (UCR).
    Enforces the Core Invariant: LLM explains results but must cite primary statutory passages.
    """
    @staticmethod
    def audit_findings(findings: List[RegulatoryFinding]) -> Tuple[List[RegulatoryFinding], float]:
        unsupported_count = 0
        total_statements = 0

        audited_findings = []
        for finding in findings:
            total_statements += 1
            if not finding.supporting_citations or len(finding.supporting_citations) == 0:
                unsupported_count += 1
                # Demote confidence if no citation is attached
                finding.confidence = "INSUFFICIENT_EVIDENCE"
                finding.explanation_text = "Abstaining: Finding lacks verifiable primary statutory citation in database."
            audited_findings.append(finding)

        ucr = (unsupported_count / total_statements) if total_statements > 0 else 0.0
        return audited_findings, round(ucr, 4)
