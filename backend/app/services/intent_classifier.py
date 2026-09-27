"""
Domain-intent classifier for IP-SAKTI retrieval.

Runs BEFORE retrieval so the pipeline only searches the collections that match
the user's intent (patent / regulatory / fssai / abs / trademark / gi / export /
safety / quality). This enforces three production rules:

1. Only evidence from intent-relevant collections is retrieved and cited.
2. The Patent Rule Engine runs only when the intent is ``patent``.
3. Patent-centric topics (Section 3(p), readiness scores, WIPO/PCT filing
   guidance, patent-filing advice) are stripped from answers to FSSAI / AYUSH /
   labeling / manufacturing / food-compliance queries.

Matching is deterministic and keyword-driven (phrase + token hits are scored and
the highest-scoring intent wins) so behaviour is fully unit-testable and runtime
has no LLM or embedding dependency.
"""

import re
from typing import Any

# Qdrant domain collection names (must match app.rag.qdrant_store.QDRANT_COLLECTIONS).
PATENT_DOMAINS = ["patents", "traditional_knowledge"]
REGULATORY_DOMAINS = ["regulations"]
ABS_DOMAINS = ["biodiversity", "regulations"]
EXPORT_DOMAINS = ["regulations", "safety"]
SAFETY_DOMAINS = ["safety", "regulations"]
QUALITY_DOMAINS = ["quality_standards", "regulations"]

# Ban patent topics in these intents (FSSAI / AYUSH / labeling / manufacturing
# / food-compliance and their regime neighbours).
_BAN_PATENT_TOPICS = {
    "regulatory": True,
    "fssai": True,
    "abs": True,
    "trademark": True,
    "gi": True,
    "safety": True,
    "quality": True,
    "patent": False,
    "export": False,
}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_INTENT_DEFS: list[dict[str, Any]] = [
    {
        "id": "patent",
        "label": "Patent",
        "collections": PATENT_DOMAINS,
        "run_patent_engine": True,
        "phrases": [
            "prior art", "section 3(p)", "section 3 p", "inventive step",
            "claim drafting", "patent filing", "patent office", "file a patent",
            "patentable", "patentability", "patent exemption", "3(p)",
            "already patented", "patented", "patenting", "existing patent",
            "similar patent", "patent history", "patent search", "patent search",
        ],
        "tokens": [
            "patent", "patents", "pct", "novelty", "novel", "tkdl",
            "traditional knowledge", "wipo", "examiner", "specification", "claims",
        ],
    },
    {
        "id": "fssai",
        "label": "FSSAI Compliance",
        "collections": REGULATORY_DOMAINS,
        "run_patent_engine": False,
        "phrases": [
            "ayurveda aahar", "ayurveda aahara", "food compliance",
            "food business operator", "food licence", "food license",
            "positive list", "nutraceutical regulation", "food product",
            "state food authority", "cas 900", "fbo registration",
        ],
        "tokens": ["fssai", "aahar", "aahara", "nutraceutical", "food", "packaging", "flavour", "labelling", "labeling", "label"],
    },
    {
        "id": "abs",
        "label": "Access & Benefit Sharing",
        "collections": ABS_DOMAINS,
        "run_patent_engine": False,
        "phrases": [
            "access and benefit sharing", "benefit sharing", "prior informed consent",
            "biological diversity act", "biodiversity act", "abs rules",
            "abs clearance", "abs compliance", "commercial utilisation",
            "commercial utilization", "state biodiversity board", "sbb approval",
            "nba approval", "biological resource", "bio resource",
        ],
        "tokens": ["abs", "nba", "biodiversity", "bioresource", "bio-resource", "pic"],
    },
    {
        "id": "trademark",
        "label": "Trademark",
        "collections": REGULATORY_DOMAINS,
        "run_patent_engine": False,
        "phrases": [
            "trade mark", "trademark registration", "register a trademark",
            "trademark search", "tm application", "brand registration",
            "trademark class", "logo registration",
        ],
        "tokens": ["trademark", "tm", "logo", "brand", "wordmark", "device mark"],
    },
    {
        "id": "gi",
        "label": "Geographical Indication",
        "collections": REGULATORY_DOMAINS,
        "run_patent_engine": False,
        "phrases": [
            "geographical indication", "geographical indicator", "gi registration",
            "gi tag", "gi application", "gi registry",
        ],
        "tokens": ["geographical", "geotag", "geo-tag", "origin tagged"],
    },
    {
        "id": "export",
        "label": "Export / Market Entry",
        "collections": EXPORT_DOMAINS,
        "run_patent_engine": False,
        "phrases": [
            "export market", "target market", "market entry", "which country",
            "international market", "us market", "european union", "eu market",
            "canada market", "import into", "sell abroad", "export to",
        ],
        "tokens": ["export", "exports", "importer", "overseas", "abroad", "customs"],
    },
    {
        "id": "safety",
        "label": "Safety",
        "collections": SAFETY_DOMAINS,
        "run_patent_engine": False,
        "phrases": [
            "heavy metal", "pesticide residue", "microbial contamination",
            "safety data", "adverse event", "side effect", "drug interaction",
            "contraindication", "shelf life", "toxicology",
        ],
        "tokens": ["safety", "safe", "toxic", "toxicity", "pesticides", "microbial", "stability"],
    },
    {
        "id": "quality",
        "label": "Quality & Standards",
        "collections": QUALITY_DOMAINS,
        "run_patent_engine": False,
        "phrases": [
            "good manufacturing practice", "good agricultural practice", "api monograph",
            "quality control", "batch release", "pharmacopoeia standard",
            "good clinical practice", "quality assurance", "good manufacturing",
            "good agricultural",
        ],
        "tokens": ["gmp", "cgmp", "gacp", "batch", "monograph", "pharmacopoeia", "specification"],
    },
    {
        "id": "regulatory",
        "label": "Regulatory",
        "collections": REGULATORY_DOMAINS,
        "run_patent_engine": False,
        "phrases": [
            "drugs and cosmetics act", "d&c act", "schedule t", "cdsco approval",
            "ayush license", "ayush licence", "regulatory approval",
            "manufacturing licence", "state drug authority", "drug licence",
            "notification", "legal requirement",
        ],
        "tokens": [
            "regulat", "complian", "licence", "license", "cdsco", "ayush",
            "schedule", "act", "rules", "guideline", "legal", "comply",
        ],
    },
]

# Priority for tie-breaking (more specific intents first).
_PRIORITY: dict[str, int] = {d["id"]: i for i, d in enumerate(_INTENT_DEFS)}

INTENT_BY_ID: dict[str, dict[str, Any]] = {d["id"]: d for d in _INTENT_DEFS}

DEFAULT_INTENT_ID = "regulatory"

# Phrases that must never appear in answers to non-patent regulatory queries.
PATENT_TOPIC_PHRASES: list[str] = [
    "section 3(p)",
    "section 3 p",
    "3(p)",
    "patent readiness",
    "patent-readiness",
    "readiness score",
    "patentable",
    "patentability",
    "patent filing",
    "patent-filing",
    "file a patent",
    "patent agent",
    "patent office",
    "prior art",
    "prior-art",
    "inventive step",
    "inventive-step",
    "wipo",
    "pct",
    "similar patent",
    "patent-ready",
    "equivalent patent",
    "patent-search",
]

# Tokens that mark a sentence as patent-centric. ``\bpatent`` also fences
# compounds of the word without whitelisting each legal phrasing variant.
PATENT_TOPIC_TOKENS: list[str] = ["patent"]
_PATENT_TOKEN_RE = re.compile(
    r"(?<![a-z])(" + "|".join(re.escape(t) for t in PATENT_TOPIC_TOKENS) + r")(?![a-z])"
)


def _normalize(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").lower()).strip()


def classify_domain_intent(question: str) -> dict[str, Any]:
    """Classify a user question into one of the 9 domain intents.

    Returns a dict with ``id``, ``label``, ``collections`` (Qdrant domains to
    search), ``run_patent_engine`` and ``ban_patent_topics``.
    """
    q = _normalize(question)
    scores: dict[str, int] = {}
    if q:
        for intent in _INTENT_DEFS:
            score = 0
            for phrase in intent["phrases"]:
                if phrase in q:
                    score += 3
            tokens = intent["tokens"]
            for token in tokens:
                if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", q):
                    score += 1
            if score:
                scores[intent["id"]] = score

        if not scores:
            winner = DEFAULT_INTENT_ID
        else:
            winner = max(
                scores,
                key=lambda iid: (scores[iid], -_PRIORITY[iid]),
            )
    else:
        winner = DEFAULT_INTENT_ID

    result = INTENT_BY_ID[winner].copy()
    result["ban_patent_topics"] = _BAN_PATENT_TOPICS.get(winner, result.get("run_patent_engine") is False)
    result["intent_score"] = scores.get(winner, 0)
    return result


def filter_sources_by_domain(sources: list[dict[str, Any]],
                             domains: list[str] | None = None) -> list[dict[str, Any]]:
    """Return only evidence belonging to the intent-relevant collections.

    Sources that carry no ``collection`` marker (statutory corpus, legacy
    retrieval, live-web hits) are kept as secondary evidence so a regulatory
    answer never depends on a Qdrant table being warm. If none of the sources
    are collection-tagged we cannot gate and return them unchanged.
    """
    if not sources or not domains:
        return sources

    domain_set = set(domains)
    tagged = [s for s in sources if s.get("collection")]
    if not tagged:
        return sources

    kept = [s for s in sources if s.get("collection") in domain_set]
    unlabelled = [s for s in sources if not s.get("collection")]
    return kept + unlabelled


def strip_banned_patent_topics(content: str) -> str:
    """Remove sentences that raise patent-centric topics.

    Applied only to non-patent intent answers so Section 3(p), patent
    readiness scores, WIPO/PCT filing guidance and patent-filing advice never
    surface on FSSAI / AYUSH / labeling / manufacturing / food-compliance
    responses.
    """
    if not content:
        return content
    banned = [p.lower() for p in PATENT_TOPIC_PHRASES]

    def _banned(sentence: str) -> bool:
        low = sentence.lower()
        if any(p in low for p in banned):
            return True
        return bool(_PATENT_TOKEN_RE.search(low))

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(content) if s.strip()]
    kept = [s for s in sentences if not _banned(s)]
    return " ".join(kept).strip()


PATENT_BAN_INSTRUCTION = (
    "\n\n## TOPIC RESTRICTION\n"
    "This is a regulatory / food / safety / quality / ABS / trade-mark / GI query. "
    "DO NOT discuss patent law, Section 3(p), patent readiness scores or "
    "patentability, and DO NOT give WIPO / PCT / patent-filing guidance. "
    "Answer strictly from the retrieved documents for the applicable regime."
)