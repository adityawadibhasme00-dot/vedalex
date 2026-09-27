"""Component 6 — ABS Compliance Agent, Master Prompt v7.0.0.

Builds a step-by-step NBA/ABS compliance path (Step 1 → Step 2 → Step 3 with
authority, form, documents and timeline) on top of the EXISTING
``ABSComplianceEngine`` (Biological Diversity Act 2002 as amended 2023 +
Biological Diversity Rules 2024) — it does not re-implement the rule engine.

Output: ``{status, steps, benefit_sharing, required_approvals, citations,
disclaimer, escalation}`` where every step carries its own citation.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentBase, AgentContext
from app.services.abs_compliance_service import ABSComplianceEngine

# Documented authorities/forms per approval line (BD Rules 2024 vocabulary).
_AUTHORITY_FORMS = {
    "NBA": {
        "authority": "National Biodiversity Authority (NBA)",
        "form": "Form I (prior approval application, BD Rules 2024)",
    },
    "SBB": {
        "authority": "State Biodiversity Board (SBB)",
        "form": "Form for intimation/approval under the BD Rules 2024",
    },
    "BMC": {
        "authority": "Biodiversity Management Committee (BMC)",
        "form": "Local register entry / BMC prior intimation",
    },
}

_DEFAULT_TLAs = "As per NBA/SBB notified timelines (typically 30–90 days from filing)"


class ABSComplianceAgent(AgentBase):
    """Component 6: rule-based ABS checklist grounded in the existing engine."""

    name = "abs_agent"
    prompt_file = "abs_prompt.txt"

    def compliance_path(
        self,
        ingredients: list[str] | None = None,
        user_type: str = "company",
        turnover_inr: float | None = None,
        wild_collected: bool | None = None,
        commercial_use: bool = True,
        context: AgentContext | None = None,
    ) -> dict[str, Any]:
        """Produce the numbered ABS compliance path for a use-case."""
        ings = [i for i in (ingredients or []) if i]
        if not ings and context is not None:
            ings = list(context.ingredients)

        resp = ABSComplianceEngine.check(
            ingredients=ings or None,
            user_type=user_type,
            turnover_inr=turnover_inr,
            wild_collected=wild_collected,
            commercial_use=commercial_use,
        )
        dump = resp.model_dump()

        steps = self._build_steps(dump)
        result = {
            "status": dump.get("status"),
            "steps": steps,
            "benefit_sharing": dump.get("benefit_sharing"),
            "required_approvals": dump.get("required_approvals") or [],
            "citations": dump.get("citations") or [],
            "decision_path": dump.get("decision_path") or [],
            "exemption_reason": dump.get("exemption_reason") or "",
            "disclaimer": dump.get("disclaimer")
            or (
                "This is general information, not legal advice. "
                "Consult a human IP facilitator or the NBA for official guidance."
            ),
            "escalation": (
                "Escalate to a human IP facilitator for formal filing support."
            ),
        }
        return self.llm_json(
            "ABS path built deterministically:\n"
            f"status={result['status']}\nsteps={len(steps)}",
            fallback=result,
        )

    # -- step builder --------------------------------------------------------

    @staticmethod
    def _resolve_approval_token(approval: str) -> str:
        upper = approval.upper()
        for token in _AUTHORITY_FORMS:
            if token in upper:
                return token
        return "NBA" if "BIODIVERSITY" in upper or "NBA" in upper else ""

    def _build_steps(self, dump: dict[str, Any]) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        status = str(dump.get("status") or "")
        decision_path = dump.get("decision_path") or []
        citations = dump.get("citations") or []
        obligations = dump.get("obligations") or []
        approvals = dump.get("required_approvals") or []
        benefit = dump.get("benefit_sharing") or {}

        # Step 1 — applicability determination (always present).
        steps.append(
            {
                "step": 1,
                "title": "Determine whether ABS approval applies",
                "authority": "Applicant self-assessment (NBA/SBB/BMC framework)",
                "form": "—",
                "documents": [
                    "Ingredient list with sourcing details (cultivated vs wild)",
                    "User type proof (company / AYUSH practitioner / researcher)",
                ],
                "timeline": "Immediate (pre-application step)",
                "detail": " ".join(str(p) for p in decision_path[:3]),
                "citation": citations[0] if citations else "",
            }
        )

        if status == "exempt":
            steps.append(
                {
                    "step": 2,
                    "title": "Record the exemption basis",
                    "authority": "National Biodiversity Authority (records)",
                    "form": "—",
                    "documents": ["Evidence of codified-TK sourcing / user type"],
                    "timeline": "Maintain records for inspection",
                    "detail": str(dump.get("exemption_reason") or "Exempt."),
                    "citation": citations[-1] if citations else "",
                }
            )
            return steps

        # Step 2 — prior approval application, per required approval line.
        approval = approvals[0] if approvals else "NBA prior approval"
        token = self._resolve_approval_token(str(approval)) or "NBA"
        meta = _AUTHORITY_FORMS.get(token, _AUTHORITY_FORMS["NBA"])
        steps.append(
            {
                "step": 2,
                "title": f"Obtain prior approval: {approval}",
                "authority": meta["authority"],
                "form": meta["form"],
                "documents": [
                    "Form application with proposed use and resource details",
                    "Proof of possession/authorization for the biological resource",
                ],
                "timeline": _DEFAULT_TLAs,
                "detail": " ".join(str(p) for p in decision_path[3:6]),
                "citation": citations[1] if len(citations) > 1 else (
                    citations[0] if citations else ""
                ),
            }
        )

        # Step 3 — benefit sharing + ongoing obligations.
        bs_bits = []
        if benefit.get("applicable"):
            slab = benefit.get("slab") or ""
            rate = benefit.get("rate_pct")
            basis = benefit.get("basis") or ""
            bs_bits.append(f"Benefit sharing applicable: {slab} @ {rate}%")
            if basis:
                bs_bits.append(str(basis))
        for ob in obligations[:4]:
            text = str(ob.get("obligation") or ob.get("note") or "")
            if text:
                bs_bits.append(f"{text} [{ob.get('citation', '')}]")
        steps.append(
            {
                "step": 3,
                "title": "Discharge benefit-sharing & ongoing compliance",
                "authority": meta["authority"],
                "form": "Benefit-sharing agreement / returns as directed by NBA",
                "documents": [
                    "Benefit-sharing agreement",
                    "Periodic compliance returns",
                ],
                "timeline": "Per agreement; annual returns where directed",
                "detail": " ".join(bs_bits) or (
                    "No benefit-sharing obligation detected for this use-case."
                ),
                "citation": benefit.get("citation") or (
                    citations[-1] if citations else ""
                ),
            }
        )
        if len(approvals) > 1:
            for i, extra in enumerate(approvals[1:], start=4):
                extra_token = self._resolve_approval_token(str(extra)) or "BMC"
                extra_meta = _AUTHORITY_FORMS.get(extra_token, _AUTHORITY_FORMS["BMC"])
                steps.append(
                    {
                        "step": i,
                        "title": f"Additional approval: {extra}",
                        "authority": extra_meta["authority"],
                        "form": extra_meta["form"],
                        "documents": ["Supporting declarations per form"],
                        "timeline": _DEFAULT_TLAs,
                        "detail": "Required in addition to the primary approval.",
                        "citation": citations[-1] if citations else "",
                    }
                )
        return steps
