import json
import os
from typing import Any

from app.models.intelligence import (
    ABSBenefitSharing,
    ABSComplianceResponse,
    ABSObligation,
)

_KNOWLEDGE = os.path.join(os.path.dirname(__file__), "..", "knowledge")

# Turnover slabs (INR) for ABS benefit-sharing (blueprint: NBA ABS Regulations 2025).
# Each tuple: (upper_bound_inclusive, rate_decimal, slab_label)
TURNOVER_SLABS: list[tuple] = [
    (5_00_00_000, 0.0, "up to ₹5 crore"),
    (50_00_00_000, 0.002, "₹5–50 crore"),
    (250_00_00_000, 0.004, "₹50–250 crore"),
    (float("inf"), 0.006, "above ₹250 crore"),
]

CITATIONS = {
    "rule_14_2": "Biological Diversity Rules 2024, Rule 14(2) — registered AYUSH practitioners practising codified traditional knowledge are exempt from ABS obligations.",
    "section_6": "Biological Diversity Act, 2002 (as amended 2023), Section 6 — prior approval required before commercialization of biological resources and associated knowledge (Form 9 / NBA clearance).",
    "abs_regulations": "NBA ABS Regulations 2025 (turnover-based benefit-sharing rates); Biological Diversity Rules 2024.",
    "wild_collected": "Biological Diversity Rules 2024, Rule 18 / SBB guidelines — wild-collected resources require intimation to the State Biodiversity Board (SBB) and NBA where applicable.",
    "supply_chain": "Biological Diversity Act, 2002 (as amended 2023); NBA exempted-commodities notifications — cultivated / notified 'normally traded commodities' may be exempt from benefit-sharing.",
}

USER_TYPE_LABELS: dict[str, str] = {
    "registered_ayush_practitioner": "Registered AYUSH practitioner",
    "researcher": "Researcher / academic",
    "academic": "Researcher / academic",
    "msme": "MSME / small business",
    "startup": "Startup",
    "company": "Company / corporate",
    "ngo": "Non-profit organisation",
    "individual": "Individual",
}


class ABSComplianceEngine:
    """
    ABS / NBA Compliance Helper (blueprint: check_abs_compliance).
    Deterministically returns whether Access & Benefit Sharing obligations apply for a
    formulation, given user type, turnover, and resource characteristics. Sources every
    rule to the underlying statute / regulation.
    """

    _bioresource: dict[str, dict[str, Any]] = {}
    _synonyms: dict[str, dict[str, Any]] = {}

    DISCLAIMER = (
        "ABS assessment is decision support computed from declared inputs and curated rules "
        "(BDA 2002 as amended 2023, Biological Diversity Rules 2024, NBA ABS Regulations 2025). "
        "The NBA / State Biodiversity Board remains the final authority on any filing."
    )

    @classmethod
    def load_data(cls):
        if not cls._bioresource:
            path = os.path.join(_KNOWLEDGE, "bioresource.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    cls._bioresource = {item["canonical_id"]: item for item in json.load(f)}
        if not cls._synonyms:
            path = os.path.join(_KNOWLEDGE, "botanical_synonyms.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    cls._synonyms = json.load(f)

    @classmethod
    def ingredients_in_codified_tk(cls, ingredients: list[str] | None) -> bool | None:
        """Best-effort check that every ingredient resolves to a classical/codified
        biological resource in the curated knowledge base. None when inputs are empty
        or ambiguous."""
        if not ingredients:
            return None
        cls.load_data()
        reconciled: list[bool] = []
        for raw in ingredients:
            raw = (raw or "").strip().lower()
            if not raw:
                continue
            matched = False
            for canonical_id, entry in cls._bioresource.items():
                haystack = canonical_id.lower()
                haystack += " " + entry.get("botanical_name", "").lower()
                for lang_names in entry.get("ayurvedic_names", {}).values():
                    haystack += " " + " ".join(str(n).lower() for n in lang_names)
                if raw in haystack:
                    matched = True
                    break
            if not matched:
                for canonical_id, _syn in cls._synonyms.items():
                    if canonical_id.lower() in raw or raw in canonical_id.lower():
                        matched = True
                        break
            reconciled.append(matched)
        if not reconciled:
            return None
        if all(reconciled):
            return True
        return False

    @staticmethod
    def _benefit_sharing_for_turnover(turnover: float | None) -> ABSBenefitSharing:
        if turnover is None:
            return ABSBenefitSharing(
                applicable=True,
                citation=CITATIONS["abs_regulations"],
            )
        for upper, rate, slab in TURNOVER_SLABS:
            if turnover <= upper:
                if rate == 0.0:
                    return ABSBenefitSharing(
                        applicable=False,
                        slab=slab,
                        rate_pct=0.0,
                        amount_inr=0.0,
                        basis="No benefit-sharing required (below benefit-sharing threshold)",
                        citation=CITATIONS["abs_regulations"],
                    )
                return ABSBenefitSharing(
                    applicable=True,
                    slab=slab,
                    rate_pct=round(rate * 100, 1),
                    amount_inr=round(turnover * rate, 2),
                    basis=f"{rate*100:.1f}% of total turnover",
                    citation=CITATIONS["abs_regulations"],
                )
        return ABSBenefitSharing(
            applicable=True,
            slab=TURNOVER_SLABS[-1][2],
            rate_pct=round(TURNOVER_SLABS[-1][1] * 100, 1),
            amount_inr=round(turnover * TURNOVER_SLABS[-1][1], 2),
            basis=f"{TURNOVER_SLABS[-1][1]*100:.1f}% of total turnover",
            citation=CITATIONS["abs_regulations"],
        )

    @classmethod
    def check(
        cls,
        ingredients: list[str] | None = None,
        user_type: str = "company",
        turnover_inr: float | None = None,
        codified_tk: bool | None = None,
        wild_collected: bool | None = None,
        commercial_use: bool = True,
    ) -> ABSComplianceResponse:
        cls.load_data()
        user_type = (user_type or "company").strip().lower()
        obligations: list[ABSObligation] = []
        decision_path: list[str] = []
        exemption_reason = ""
        status = "compliance_required"
        benefit_sharing: ABSBenefitSharing = ABSBenefitSharing()

        # ── Input normalization ────────────────────────────────────────────────
        decision_path.append(f"User type: {USER_TYPE_LABELS.get(user_type, user_type)}.")
        if codified_tk is None:
            codified_tk = cls.ingredients_in_codified_tk(ingredients)
        if codified_tk is not None:
            decision_path.append(
                "Codified traditional knowledge: "
                + ("all ingredients resolve to classical/codified biological resources." if codified_tk else "not all ingredients resolve to codified resources.")
            )

        # ── Rule: AYUSH practitioner + codified TK → exempt (Rule 14(2)) ───────
        if user_type == "registered_ayush_practitioner" and codified_tk is True:
            status = "exempt"
            exemption_reason = (
                "Registered AYUSH practitioner practising codified traditional-knowledge formulations "
                "in the course of their practice — exempt from ABS obligations under Biological Diversity Rules 2024, Rule 14(2)."
            )
            obligations.append(ABSObligation(
                obligation="Document the classical source text (e.g., First Schedule / API) in the practice dossier",
                status="applicable",
                citation=CITATIONS["rule_14_2"],
                note="Exemption depends on the practice using documented, codified traditional knowledge.",
            ))
            decision_path.append("Rule 14(2): registered AYUSH practitioner + codified TK → ABS-exempt.")
        elif user_type in ("researcher", "academic") and not commercial_use:
            status = "exempt"
            exemption_reason = (
                "Non-commercial research on biological resources is exempt from prior approval and "
                "benefit-sharing; NBA intimation applies before commercialization."
            )
            decision_path.append("Rule: non-commercial research use → ABS-exempt, with NBA intimation before commercialization.")
        else:
            # ── Turnover-based benefit sharing ──────────────────────────────────
            if turnover_inr is None:
                status = "info_required"
                benefit_sharing = cls._benefit_sharing_for_turnover(None)
                obligations.append(ABSObligation(
                    obligation="Declare total annual turnover (₹) to determine the applicable benefit-sharing rate",
                    status="info_required",
                    citation=CITATIONS["abs_regulations"],
                    note="Benefit-sharing is a percentage of total turnover once the threshold applies.",
                ))
                decision_path.append("Turnover not declared — benefit-sharing rate cannot be finalised (info required).")
            else:
                benefit_sharing = cls._benefit_sharing_for_turnover(turnover_inr)
                if benefit_sharing.applicable:
                    obligations.append(ABSObligation(
                        obligation=f"Benefit-sharing @ {benefit_sharing.rate_pct}% of turnover (₹{benefit_sharing.amount_inr:,.2f})",
                        status="required",
                        citation=CITATIONS["abs_regulations"],
                        note=f"Slab: {benefit_sharing.slab} · basis: {benefit_sharing.basis}",
                    ))
                else:
                    obligations.append(ABSObligation(
                        obligation="Benefit-sharing not required (below threshold)",
                        status="not_applicable",
                        citation=CITATIONS["abs_regulations"],
                        note=f"Turnover slab: {benefit_sharing.slab}",
                    ))
                decision_path.append(f"Turnover {turnover_inr:,.2f} → slab {benefit_sharing.slab} @ {benefit_sharing.rate_pct}%.")

            # ── Prior approval for commercialization ─────────────────────────────
            if commercial_use and status != "info_required":
                obligations.append(ABSObligation(
                    obligation="Form 9 prior approval for commercialization of biological resources",
                    status="required",
                    citation=CITATIONS["section_6"],
                    note="Required under Section 6, BDA 2002 (as amended 2023) before commercialization.",
                ))
                decision_path.append("Section 6: Form 9 prior approval required before commercialization.")
            elif commercial_use and status == "info_required":
                obligations.append(ABSObligation(
                    obligation="Form 9 prior approval for commercialization of biological resources",
                    status="info_required",
                    citation=CITATIONS["section_6"],
                    note="Comes due once full ABS assessment inputs (turnover) are finalised.",
                ))

        # ── Wild-collected resource → SBB/NBA intimation ──────────────────────
        if wild_collected is True and status != "exempt":
            obligations.append(ABSObligation(
                obligation="Intimate State Biodiversity Board (SBB) / NBA on use of wild-collected resource",
                status="required",
                citation=CITATIONS["wild_collected"],
                note="Wild-collected access requires SBB/NBA compliance and benefit-sharing documentation.",
            ))
            decision_path.append("Wild-collected resource declared → SBB/NBA intimation obligation added.")

        # ── Lawful sourcing note (always present) ──────────────────────────────
        obligations.append(ABSObligation(
            obligation="Source biological resources through lawful, notified supply chains; retain origin declarations",
            status="applicable",
            citation=CITATIONS["supply_chain"],
            note="Cultivated / normally-traded commodities may be exempt — verify the current NBA exempted list.",
        ))
        decision_path.append("Baseline: lawful sourcing and documented origin required regardless of exemptions.")

        required_approvals: list[str] = []
        if status != "exempt":
            required_approvals.append("Form 9 prior approval (Section 6, BDA 2002 as amended 2023)")
            if wild_collected is True:
                required_approvals.append("SBB/NBA intimation for wild-collected resource")

        return ABSComplianceResponse(
            status=status,
            user_type=user_type,
            turnover_inr=turnover_inr,
            codified_tk=codified_tk,
            wild_collected=wild_collected,
            commercial_use=commercial_use,
            exemption_reason=exemption_reason,
            benefit_sharing=benefit_sharing,
            obligations=obligations,
            required_approvals=required_approvals,
            citations=sorted({o.citation for o in obligations}),
            decision_path=decision_path,
            disclaimer=cls.DISCLAIMER,
        )