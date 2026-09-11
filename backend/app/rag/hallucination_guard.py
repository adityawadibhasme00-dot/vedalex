"""
Zero-Hallucination Prevention Module for VEDALEX.

Enterprise legal/patent RAG systems require strict guardrails:
  1. Answer ONLY from retrieved documents
  2. Never generate patent numbers, dates, or legal citations
  3. Return "Insufficient Evidence" when confidence is low
  4. Cite every factual statement with source attribution
  5. Validate retrieved metadata before using in answers
  6. Separate patent claims into individual chunks for precision

This module implements all guardrails as a pre-response validation layer.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HallucinationRisk(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HallucinationCheck:
    risk_level: HallucinationRisk
    grounded: bool
    coverage_ratio: float
    citation_count: int
    violations: List[str]
    recommendations: List[str]


# Patterns that indicate fabricated patent numbers
PATENT_NUMBER_PATTERN = re.compile(
    r"(?:IN|US|WO|EP|JP|CN|KR|CA|AU|BR|RU|MX|ZA)-?\d{4,}[-/]?\d{0,6}",
    re.IGNORECASE,
)

# Patterns for fabricated dates
DATE_PATTERN = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)

# Stopwords carried over from copilot
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "with", "is", "are",
    "was", "be", "been", "by", "at", "from", "as", "it", "its", "this", "that", "what",
    "which", "does", "do", "how", "my", "i", "we", "you", "would", "please", "help",
    "about", "can", "not", "no", "yes", "me", "us", "them", "their", "they", "there",
    "then", "than", "if", "when", "will", "all", "need",
}

FRAMING_WORDS = {
    "can", "could", "would", "should", "this", "these", "those", "that",
    "what", "which", "does", "how", "any", "some", "with", "from", "into",
    "about", "then", "next", "when", "where", "there", "here", "my", "me",
    "your", "all", "the", "a", "an",
}


def _extract_meaningful_tokens(text: str) -> set:
    """Extract content-bearing tokens from text."""
    tokens = (t for tok in re.split(r"[^a-z0-9%.]+", text.lower()) for t in tok.split())
    return set(
        t for t in tokens
        if t not in STOPWORDS and t not in FRAMING_WORDS and len(t) > 1
    )


def _count_citations(text: str) -> int:
    """Count explicit citations in answer text."""
    citation_patterns = [
        r"(?:Verified|Source|Citation|Reference|Authority):\s",
        r"\[Source\s*\d+\]",
        r"\(Source:\s",
        r"Source:\s+\S+",
    ]
    count = 0
    for pattern in citation_patterns:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count


def _detect_fabricated_patent_numbers(text: str, source_patent_numbers: List[str]) -> List[str]:
    """Check if the answer contains patent numbers not found in sources."""
    violations = []
    found_numbers = PATENT_NUMBER_PATTERN.findall(text)
    source_numbers = set(s.lower() for s in source_patent_numbers)

    for num in found_numbers:
        if num.lower() not in source_numbers:
            violations.append(f"Fabricated patent number detected: {num}")
    return violations


def _detect_fabricated_dates(text: str, source_dates: List[str]) -> List[str]:
    """Check if the answer contains dates not found in sources."""
    violations = []
    found_dates = DATE_PATTERN.findall(text)
    source_date_set = set(d.lower() for d in source_dates if d)

    for date in found_dates:
        if date.lower() not in source_date_set:
            violations.append(f"Potentially fabricated date: {date}")
    return violations


def _detect_unsupported_claims(text: str, sources: List[Dict[str, Any]]) -> List[str]:
    """Check for absolute claims without source support."""
    violations = []
    absolute_patterns = [
        (r"\b(?:definitely|certainly|always|never|guaranteed|proven)\b", "Absolute claim without qualification"),
        (r"\b(?:all experts agree|universally accepted)\b", "Appeal to authority without citation"),
        (r"\b(?:study (?:shows|proves|confirms))\b", "Study claim without specific citation"),
    ]

    for pattern, desc in absolute_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            violations.append(f"{desc}: {matches[0]}")

    return violations


# Patterns for multi-omics database identifiers (UniProt, PMID, PubChem CID).
_UNIPROT_PATTERN = re.compile(r"\b[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2}\b")
_PMID_PATTERN = re.compile(r"\bPMID[:#]?\s*(\d{1,18})\b", re.IGNORECASE)
_PUBCHEM_PATTERN = re.compile(r"\bPubChem\s+(?:CID)?\s*#{0,1}\s*(\d{1,12})\b", re.IGNORECASE)


def _collect_omics_identifiers(sources: List[Dict[str, Any]]) -> Dict[str, set]:
    """Collect verified omics identifiers from retrieved source payloads."""
    verified = {
        "uniprot": set(),
        "pmid": set(),
        "pubchem": set(),
    }
    for s in sources:
        if s.get("uniprot_accession"):
            verified["uniprot"].add(str(s["uniprot_accession"]).upper())
        if s.get("pmid"):
            verified["pmid"].add(str(s["pmid"]))
        if s.get("pubchem_cid"):
            verified["pubchem"].add(str(s["pubchem_cid"]))
        content = str(s.get("content", ""))
        for m in _PMID_PATTERN.findall(content):
            verified["pmid"].add(m)
        for m in _PUBCHEM_PATTERN.findall(content):
            verified["pubchem"].add(m)
    return verified


def _detect_fabricated_omics_identifiers(
    text: str,
    sources: List[Dict[str, Any]],
) -> List[str]:
    """Flag UniProt accessions / PMIDs / PubChem CIDs that are not in sources.

    This enforces the zero-hallucination rule for multi-omics evidence: any
    database identifier named in the answer must trace back to a retrieved,
    indexed record — never fabricated.
    """
    violations = []
    verified = _collect_omics_identifiers(sources)

    for cand in _UNIPROT_PATTERN.findall(text):
        up = cand.upper()
        if len(up) == 6 and up not in verified["uniprot"]:
            violations.append(f"Unverified UniProt accession in answer: {cand}")

    for m in _PMID_PATTERN.findall(text):
        if m not in verified["pmid"]:
            violations.append(f"Fabricated PMID in answer: {m}")

    for m in _PUBCHEM_PATTERN.findall(text):
        if m not in verified["pubchem"]:
            violations.append(f"Unverified PubChem CID in answer: {m}")

    return violations


def validate_answer(
    answer: str,
    sources: List[Dict[str, Any]],
    query: str,
    confidence: float,
    source_patent_numbers: Optional[List[str]] = None,
    source_dates: Optional[List[str]] = None,
) -> HallucinationCheck:
    """
    Comprehensive hallucination validation on a generated answer.

    Returns a HallucinationCheck with risk assessment and violations.
    """
    violations = []
    recommendations = []

    # 1. Coverage check — how much of the query is grounded in sources
    meaningful = _extract_meaningful_tokens(query)
    combined_source = " ".join(s.get("content", "") for s in sources).lower()
    source_tokens = set(combined_source.split())
    coverage = len(meaningful.intersection(source_tokens)) / max(1, len(meaningful))

    # 2. Citation check
    citation_count = _count_citations(answer)
    if citation_count == 0 and confidence > 0.3:
        violations.append("No explicit citations found in answer")
        recommendations.append("Add source citations for every factual claim")

    # 3. Patent number fabrication check
    if source_patent_numbers is None:
        source_patent_numbers = []
        for s in sources:
            if s.get("patent_number"):
                source_patent_numbers.append(s["patent_number"])
    patent_violations = _detect_fabricated_patent_numbers(answer, source_patent_numbers)
    violations.extend(patent_violations)

    # 4. Date fabrication check
    if source_dates is None:
        source_dates = [s.get("effective_date", "") for s in sources if s.get("effective_date")]
    date_violations = _detect_fabricated_dates(answer, source_dates)
    violations.extend(date_violations)

    # 5. Unsupported absolute claims
    claim_violations = _detect_unsupported_claims(answer, sources)
    violations.extend(claim_violations)

    # 6. Source quality check
    if not sources:
        violations.append("No sources provided for answer generation")
        recommendations.append("Ensure retrieval returns at least one relevant source")

    # 6b. Multi-omics identifier fabrication check (UniProt / PMID / PubChem)
    omics_violations = _detect_fabricated_omics_identifiers(answer, sources)
    violations.extend(omics_violations)

    # 7. Answer length vs source length ratio (too long = likely hallucinated)
    avg_source_len = sum(len(s.get("content", "")) for s in sources) / max(1, len(sources))
    if len(answer) > avg_source_len * 5 and avg_source_len > 0:
        violations.append("Answer significantly longer than source material")
        recommendations.append("Keep answers grounded in retrieved content length")

    # Risk assessment
    risk_score = 0
    risk_score += len(violations) * 15
    risk_score += max(0, (1 - coverage) * 30)
    risk_score += max(0, (1 - confidence) * 20)
    if patent_violations:
        risk_score += 25
    if omics_violations:
        risk_score += 20
    if citation_count == 0:
        risk_score += 10

    if risk_score >= 60:
        risk = HallucinationRisk.CRITICAL
        grounded = False
    elif risk_score >= 40:
        risk = HallucinationRisk.HIGH
        grounded = False
    elif risk_score >= 25:
        risk = HallucinationRisk.MEDIUM
        grounded = coverage >= 0.4 and confidence >= 0.2
    elif risk_score >= 10:
        risk = HallucinationRisk.LOW
        grounded = coverage >= 0.35
    else:
        risk = HallucinationRisk.NONE
        grounded = True

    if not grounded and confidence > 0.3:
        recommendations.append("Reduce confidence score — answer is not fully grounded")
    if coverage < 0.3:
        recommendations.append("Retrieval coverage is low — consider rephrasing the query")
    if len(sources) < 2:
        recommendations.append("Retrieve additional sources for multi-source corroboration")

    return HallucinationCheck(
        risk_level=risk,
        grounded=grounded,
        coverage_ratio=round(coverage, 3),
        citation_count=citation_count,
        violations=violations,
        recommendations=recommendations,
    )


def should_refuse_answer(
    coverage: float,
    confidence: float,
    num_sources: int,
    min_coverage: float = 0.4,
    min_confidence: float = 0.2,
    min_sources: int = 2,
) -> Tuple[bool, str]:
    """
    Decision gate: should the system refuse to answer?

    Returns (should_refuse, refusal_reason).
    """
    if num_sources < min_sources:
        return True, "NO_SOURCES: No relevant documents found in the knowledge base."

    if coverage < min_coverage:
        return True, (
            f"INSUFFICIENT_COVERAGE: Only {coverage:.0%} of query tokens matched "
            f"retrieved sources (minimum: {min_coverage:.0%}). "
            "The system will not generate answers from insufficient context."
        )

    if confidence < min_confidence:
        return True, (
            f"LOW_CONFIDENCE: Confidence score {confidence:.2f} below threshold "
            f"{min_confidence:.2f}. Add more authoritative sources and re-query."
        )

    return False, ""


def build_grounding_check(
    query: str,
    sources: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Pre-generation grounding check — validates retrieval quality
    before the LLM generates an answer.
    """
    meaningful = _extract_meaningful_tokens(query)
    combined = " ".join(s.get("content", "") for s in sources).lower()
    covered = meaningful.intersection(set(combined.split()))
    coverage = len(covered) / max(1, len(meaningful))

    uncovered = meaningful - set(combined.split())

    return {
        "grounded": coverage >= 0.4,
        "coverage_ratio": round(coverage, 3),
        "meaningful_tokens": len(meaningful),
        "covered_tokens": len(covered),
        "uncovered_tokens": list(uncovered)[:10],
        "source_count": len(sources),
        "recommendation": (
            "Proceed with answer generation" if coverage >= 0.4
            else "Retrieve additional documents or rephrase query"
        ),
    }
