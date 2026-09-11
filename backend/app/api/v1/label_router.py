from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict

router = APIRouter(prefix="/label", tags=["Claim Firewall"])

class LabelAnalyzeRequest(BaseModel):
    label_text: str
    product_type: Optional[str] = "ayurvedic_drug"
    target_markets: Optional[List[str]] = ["India"]

class ClaimResult(BaseModel):
    claim_text: str
    risk_level: str
    risk_color: str
    regulation: str
    note: str

class LabelAnalyzeResponse(BaseModel):
    overall_status: str
    overall_color: str
    claims: List[ClaimResult]
    summary: str

THERAPEUTIC_KEYWORDS = [
    "cure", "treat", "heal", "prevent", "diagnose",
    "remedy", "medicine", "drug", "therapy", "clinical"
]

SAFE_CLAIMS = [
    "supports healthy skin", "moisturizes", "skin hygiene",
    "soothing effect", "maintains healthy", "supports overall",
    "traditional use", "natural ingredient", "herbal supplement"
]

@router.post("/analyze", response_model=LabelAnalyzeResponse)
async def analyze_label(req: LabelAnalyzeRequest):
    claims = []
    label_lower = req.label_text.lower()
    words = label_lower.split()

    has_therapeutic = False
    has_safety_disclaimer = False
    has_dosage = False
    has_manufacturer = False

    for kw in THERAPEUTIC_KEYWORDS:
        if kw in label_lower:
            has_therapeutic = True
            claims.append(ClaimResult(
                claim_text=f"Contains therapeutic claim: '{kw}'",
                risk_level="HIGH_RISK",
                risk_color="red",
                regulation="FDA FD&C Act / CDSCO Drug Classification",
                note=f"Use of '{kw}' may classify product as unapproved drug. Requires NDA/IND in US or ASU drug license in India."
            ))

    for safe in SAFE_CLAIMS:
        if safe in label_lower:
            claims.append(ClaimResult(
                claim_text=f"Safe structure/function claim: '{safe}'",
                risk_level="SAFE",
                risk_color="green",
                regulation="DSHEA / FSSAI Ayurveda Aahara",
                note="This is a permissible structure/function claim with proper disclaimers."
            ))

    if "disclaimer" in label_lower or "not evaluated" in label_lower:
        has_safety_disclaimer = True
    else:
        if has_therapeutic:
            claims.append(ClaimResult(
                claim_text="Missing FDA/CDSCO disclaimer",
                risk_level="WARNING",
                risk_color="yellow",
                regulation="21 CFR 101.93 / DSHEA Section 6",
                note="Therapeutic claims require prominent disclaimer."
            ))

    if "mg" in label_lower or "dosage" in label_lower:
        has_dosage = True

    if "manufactured" in label_lower or "mfg" in label_lower:
        has_manufacturer = True

    if not has_dosage:
        claims.append(ClaimResult(
            claim_text="Missing dosage information",
            risk_level="WARNING",
            risk_color="yellow",
            regulation="Schedule T / 21 CFR 201",
            note="Product labels must include dosage instructions."
        ))

    if not has_manufacturer:
        claims.append(ClaimResult(
            claim_text="Missing manufacturer details",
            risk_level="WARNING",
            risk_color="yellow",
            regulation="Schedule T / FDCA",
            note="Labels must include manufacturer name and address."
        ))

    risk_counts = {"red": 0, "yellow": 0, "green": 0}
    for c in claims:
        risk_counts[c.risk_color] += 1

    if risk_counts["red"] > 0:
        overall_status = "HIGH_RISK"
        overall_color = "red"
    elif risk_counts["yellow"] > 2:
        overall_status = "WARNING"
        overall_color = "yellow"
    else:
        overall_status = "SAFE"
        overall_color = "green"

    summary = f"Analysis complete: {risk_counts['red']} high-risk, {risk_counts['yellow']} warnings, {risk_counts['green']} safe claims."

    return LabelAnalyzeResponse(
        overall_status=overall_status,
        overall_color=overall_color,
        claims=claims,
        summary=summary
    )
