"""
Human Escalation Service (STEP 8 of the IP-SAKTI Sahayak workflow).

Har answer ke saath ek escalation recommendation banti hai:
jab classification high-risk ho, yaa confidence kam ho, yaa rule engine
human review mandatory bataaye — tab user ko expert (IP attorney /
regulatory expert / NBA / TKDL) ke paas jaane ki salah di jaati hai.

Output bilingual hai (English + Hindi) taaki bhasha switch hone par bhi
guidance samajh aaye. Contact info sirf official websites par le jaati hai.
"""

from dataclasses import asdict, dataclass
from typing import Any, TypedDict

# ---------------------------------------------------------------------------
# Bilingual labels
# ---------------------------------------------------------------------------

TYPE_LABELS: dict[str, dict[str, str]] = {
    "ip_attorney":        {"en": "Registered Patent Agent / IP Attorney", "hi": "पंजीकृत पेटेंट एजेंट / आईपी अटॉर्नी"},
    "regulatory_expert":  {"en": "Regulatory Expert", "hi": "विनियामक विशेषज्ञ"},
    "nba":                {"en": "NBA / State Biodiversity Board", "hi": "एनबीए / राज्य जैव विविधता बोर्ड"},
    "tkdl":               {"en": "TKDL Search / IP India", "hi": "टीकेडीएल खोज / आईपी इंडिया"},
}

URGENCY_LABELS: dict[str, dict[str, str]] = {
    "low":    {"en": "Low", "hi": "कम"},
    "medium": {"en": "Medium", "hi": "मध्यम"},
    "high":   {"en": "High", "hi": "उच्च"},
}

class _ContactInfo(TypedDict):
    organization: str
    website: str


CONTACT_INFO: dict[str, _ContactInfo] = {
    "ip_attorney": {
        "organization": "Office of the Controller General of Patents (IP India)",
        "website": "https://ipindia.gov.in",
    },
    "regulatory_expert": {
        "organization": "CDSCO (Central Drugs Standard Control Organisation)",
        "website": "https://cdsco.gov.in",
    },
    "nba": {
        "organization": "National Biodiversity Authority (NBA)",
        "website": "https://nbaindia.nic.in",
    },
    "tkdl": {
        "organization": "Traditional Knowledge Digital Library (TKDL)",
        "website": "https://tkdl.res.in",
    },
}


# ---------------------------------------------------------------------------
# Escalation decision
# ---------------------------------------------------------------------------

@dataclass
class EscalationRecommendation:
    """Human escalation recommendation (bilingual)."""
    recommended: bool
    type: str = "ip_attorney"
    urgency: str = "low"
    reason_en: str = ""
    reason_hi: str = ""
    organization: str = ""
    website: str = ""
    confidence_below_threshold: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["type_label"] = TYPE_LABELS.get(self.type, {}).get("en", self.type)
        d["type_label_hi"] = TYPE_LABELS.get(self.type, {}).get("hi", self.type)
        d["urgency_label"] = URGENCY_LABELS.get(self.urgency, {}).get("en", self.urgency)
        d["urgency_label_hi"] = URGENCY_LABELS.get(self.urgency, {}).get("hi", self.urgency)
        return d


def should_escalate(
    classification: dict[str, Any] | None = None,
    confidence: float = 0.0,
    requires_human_review: bool = False,
    risk_level: str = "Moderate",
    has_bio_resources: bool = False,
    is_patent_question: bool = True,
) -> EscalationRecommendation:
    """Human escalation triggers (mirrors the STEP-8 spec):

    1. New Drug / Phytopharmaceutical classification + moderate confidence
       → regulatory_expert (CDSCO), high urgency.
    2. Rule engine flags ``requires_human_review`` (e.g. Section 3(p) exposure)
       → ip_attorney, medium urgency.
    3. Low confidence (< 0.5) in automated analysis → ip_attorney.
    4. Commercial use of biological resources (proprietary/new/ABS cases)
       → NBA clearance (medium).
    5. Classical medicine / proprietary with TKDL risk → TKDL search (low).
    """
    category = (classification or {}).get("category") if classification else None
    str((classification or {}).get("pathway_confidence") or "").upper()

    # 1. New drug / phytopharmaceutical → regulatory expert.
    if category in ("new_drug", "phytopharmaceutical") and confidence < 0.7:
        return EscalationRecommendation(
            recommended=True,
            type="regulatory_expert",
            urgency="high",
            reason_en=(
                "Your product maps to the New Drug / Phytopharmaceutical pathway, which needs "
                "expert regulatory guidance (CDSCO approval, clinical data strategy)."
            ),
            reason_hi=(
                "आपका उत्पाद नई दवा / फाइटोफार्मास्युटिकल श्रेणी में आता है, जिसके लिए विशेषज्ञ "
                "विनियामक मार्गदर्शन आवश्यक है (सीडीएससीओ अनुमोदन, क्लिनिकल डेटा रणनीति)।"
            ),
            **CONTACT_INFO["regulatory_expert"],
        )

    # 2. Rule engine human-review flag.
    if requires_human_review:
        return EscalationRecommendation(
            recommended=True,
            type="ip_attorney",
            urgency="medium",
            reason_en=(
                "The rule engine flagged this question for professional review — a legal "
                "opinion is needed (for example Section 3(p) / traditional-knowledge exposure)."
            ),
            reason_hi=(
                "रूल इंजन ने इस प्रश्न को व्यावसायिक समीक्षा के लिए चिह्नित किया है — "
                "कानूनी राय आवश्यक है (जैसे धारा 3(पी) / पारंपरिक ज्ञान से जुड़ा जोखिम)।"
            ),
            **CONTACT_INFO["ip_attorney"],
        )

    # 3. Low confidence / abstention (excluding pure-refusal cases).
    if confidence < 0.5 and confidence > 0.02:
        return EscalationRecommendation(
            recommended=True,
            type="ip_attorney",
            urgency="medium",
            reason_en=(
                "Automated analysis confidence is low — expert review is recommended before "
                "making any filing or compliance decision."
            ),
            reason_hi=(
                "स्वचालित विश्लेषण का विश्वास स्तर कम है — किसी भी फाइलिंग या अनुपालन निर्णय "
                "से पहले विशेषज्ञ समीक्षा की सलाह दी जाती है।"
            ),
            confidence_below_threshold=True,
            **CONTACT_INFO["ip_attorney"],
        )

    # 4. Biological-resource commercial use → NBA clearance.
    if has_bio_resources and category in ("proprietary_ayurveda", "new_drug", "phytopharmaceutical"):
        return EscalationRecommendation(
            recommended=True,
            type="nba",
            urgency="medium",
            reason_en=(
                "Commercial utilisation of biological resources likely needs NBA approval / "
                "RIAF and prior informed consent (Biological Diversity Act, 2002)."
            ),
            reason_hi=(
                "जैविक संसाधनों के व्यावसायिक उपयोग के लिए संभवतः एनबीए अनुमोदन / आरआईएएफ और "
                "पूर्व सूचित सहमति आवश्यक है (जैविक विविधता अधिनियम, 2002)।"
            ),
            **CONTACT_INFO["nba"],
        )

    # 5. Classical / TKDL prior-art risk → TKDL search.
    if is_patent_question and category in ("classical_medicine", "ayurvedic_drug", "proprietary_ayurveda"):
        return EscalationRecommendation(
            recommended=True,
            type="tkdl",
            urgency="low",
            reason_en=(
                "Classical / traditional-knowledge basis — confirm TKDL coverage and prior-art "
                "status before taking a patent position."
            ),
            reason_hi=(
                "शास्त्रीय / पारंपरिक ज्ञान आधार — पेटेंट रुख लेने से पहले टीकेडीएल कवरेज और "
                "पूर्व-कला स्थिति की पुष्टि करें।"
            ),
            **CONTACT_INFO["tkdl"],
        )

    return EscalationRecommendation(
        recommended=False,
        type="ip_attorney",
        urgency="low",
        reason_en="No escalation required — the answer is grounded and within confidence bounds.",
        reason_hi="कोई एस्केलेशन आवश्यक नहीं — उत्तर आधारित है और विश्वास सीमा के भीतर है।",
        **CONTACT_INFO["ip_attorney"],
    )


# ---------------------------------------------------------------------------
# Bilingual labels for classification
# ---------------------------------------------------------------------------

CATEGORY_LABELS: dict[str, dict[str, str]] = {
    "classical_medicine": {"en": "Classical Medicine", "hi": "शास्त्रीय औषधि"},
    "ayurvedic_drug": {"en": "Classical / Ayurvedic Drug", "hi": "शास्त्रीय / आयुर्वेदिक औषधि"},
    "proprietary_ayurveda": {"en": "Patent & Proprietary Ayurveda", "hi": "पेटेंट एवं प्रोप्राइटरी आयुर्वेद"},
    "new_drug": {"en": "New Drug", "hi": "नई दवा"},
    "phytopharmaceutical": {"en": "Phytopharmaceutical", "hi": "फाइटोफार्मास्युटिकल"},
    "ayurveda_aahara": {"en": "Ayurveda Aahar (Food)", "hi": "आयुर्वेद आहार (खाद्य)"},
    "nutraceutical": {"en": "Nutraceutical / Supplement", "hi": "न्यूट्रास्यूटिकल / सप्लीमेंट"},
    "cosmetic": {"en": "Cosmetic", "hi": "प्रसाधन"},
    "unresolved": {"en": "To be confirmed", "hi": "पुष्टि होनी बाकी"},
}


def classification_bilingual(classification: dict[str, Any] | None) -> dict[str, Any] | None:
    """Attach bilingual category labels onto a ProductClassifier response."""
    if not classification:
        return None
    out = dict(classification)
    cat = out.get("pathway_category") or out.get("category") or "unresolved"
    out["category_label"] = CATEGORY_LABELS.get(cat, {}).get("en", cat)
    out["category_label_hi"] = CATEGORY_LABELS.get(cat, {}).get("hi", cat)
    return out