"""
Claim Extraction Module for VEDALEX Verification Layer.

Decomposes a generated answer into individual verifiable claims.
Each claim is an atomic factual assertion that can be independently
checked against retrieved evidence.

Extraction strategy:
  1. Split on sentence boundaries
  2. Filter out non-claim sentences (disclaimers, headers, formatting)
  3. Detect citation spans and separate them from claim text
  4. Classify claim type (factual, legal, numerical, causal, comparative)
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ClaimType(str, Enum):
    FACTUAL = "factual"
    LEGAL = "legal"
    NUMERICAL = "numerical"
    CAUSAL = "causal"
    COMPARATIVE = "comparative"
    DEFINITIONAL = "definitional"
    PROCEDURAL = "procedural"


@dataclass
class Claim:
    text: str
    claim_type: ClaimType
    citations: List[str] = field(default_factory=list)
    source_index: int = 0
    confidence_hint: float = 0.5


# Sentences that are NOT verifiable claims
_SKIP_PATTERNS = [
    re.compile(r"^\s*(?:disclaimer|note|warning|caution)\s*:?", re.IGNORECASE),
    re.compile(r"^\s*this (?:assessment|analysis|answer) is generated", re.IGNORECASE),
    re.compile(r"^\s*always consult\b", re.IGNORECASE),
    re.compile(r"^\s*based on the retrieved", re.IGNORECASE),
    re.compile(r"^\s*the retrieved (?:official )?sources", re.IGNORECASE),
    re.compile(r"^\s*---+\s*$"),
    re.compile(r"^\s*#+\s*"),
    re.compile(r"^\s*$"),
]

# Patterns that identify citation spans within a sentence
_CITATION_PATTERNS = [
    re.compile(r"\[Source:\s*([^\]]+)\]", re.IGNORECASE),
    re.compile(r"\(Source:\s*([^)]+)\)", re.IGNORECASE),
    re.compile(r"Verified citation:\s*(.+?)(?:\s*—\s*\S+)?$", re.IGNORECASE),
    re.compile(r"(?:Source|Citation|Reference|Authority):\s*(.+?)(?:\s*$|\s*\n)", re.IGNORECASE),
]

# Claim type detection patterns
_LEGAL_PATTERNS = re.compile(
    r"(?:section|article|act|statute|regulation|rule|provision|clause|schedule|amendment|rule)\s*(?:\d+|[0-9]+[(\w)]*)",
    re.IGNORECASE,
)
_NUMERICAL_PATTERNS = re.compile(
    r"\b\d+(?:\.\d+)?(?:\s*%|\s*percent|\s*years?\s*months?|\s*days?)\b",
    re.IGNORECASE,
)
_CAUSAL_PATTERNS = re.compile(
    r"\b(?:therefore|consequently|because|as a result|leads? to|causes?|results? in|enables?|prevents?)\b",
    re.IGNORECASE,
)
_COMPARATIVE_PATTERNS = re.compile(
    r"\b(?:more than|less than|higher than|lower than|greater than|compared to|versus|vs\.?|whereas|while)\b",
    re.IGNORECASE,
)
_DEFINITIONAL_PATTERNS = re.compile(
    r"\b(?:is defined as|means?|refers? to|is characterized by|is known as)\b",
    re.IGNORECASE,
)
_PROCEDURAL_PATTERNS = re.compile(
    r"\b(?:must|shall|should|required to|ought to|need to|apply for|submit|file|register)\b",
    re.IGNORECASE,
)


def _strip_citations(text: str) -> tuple:
    """Remove citation spans and return (clean_text, list_of_citations)."""
    citations = []
    clean = text
    for pattern in _CITATION_PATTERNS:
        for match in pattern.finditer(text):
            cit = match.group(1).strip() if match.lastindex else match.group(0).strip()
            if cit and len(cit) > 3:
                citations.append(cit)
        clean = pattern.sub("", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean, citations


def _classify_claim(text: str) -> ClaimType:
    """Determine the claim type from lexical signals."""
    if _LEGAL_PATTERNS.search(text):
        return ClaimType.LEGAL
    if _NUMERICAL_PATTERNS.search(text):
        return ClaimType.NUMERICAL
    if _CAUSAL_PATTERNS.search(text):
        return ClaimType.CAUSAL
    if _COMPARATIVE_PATTERNS.search(text):
        return ClaimType.COMPARATIVE
    if _DEFINITIONAL_PATTERNS.search(text):
        return ClaimType.DEFINITIONAL
    if _PROCEDURAL_PATTERNS.search(text):
        return ClaimType.PROCEDURAL
    return ClaimType.FACTUAL


def _split_sentences(text: str) -> List[str]:
    """Split text on sentence boundaries, handling legal text conventions."""
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z\"\']|(?:\d))", text)
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s) < 15:
            continue
        sentences.append(s)
    return sentences


def _is_skip_sentence(text: str) -> bool:
    """Return True if the sentence is formatting, not a verifiable claim."""
    for pat in _SKIP_PATTERNS:
        if pat.search(text):
            return True
    return False


def extract_claims(answer: str) -> List[Claim]:
    """
    Extract individual verifiable claims from a generated answer.

    Returns a list of Claim objects, each representing one atomic
    factual assertion that can be independently verified against
    retrieved evidence.
    """
    if not answer or not answer.strip():
        return []

    sentences = _split_sentences(answer)
    claims: List[Claim] = []

    for i, sentence in enumerate(sentences):
        if _is_skip_sentence(sentence):
            continue

        clean_text, citations = _strip_citations(sentence)
        if len(clean_text) < 20:
            continue

        claim_type = _classify_claim(clean_text)

        claims.append(Claim(
            text=clean_text,
            claim_type=claim_type,
            citations=citations,
            source_index=i,
        ))

    if not claims and sentences:
        # Fallback: treat the entire answer as one claim
        full_clean, full_cits = _strip_citations(answer)
        if len(full_clean) > 20:
            claims.append(Claim(
                text=full_clean,
                claim_type=ClaimType.FACTUAL,
                citations=full_cits,
                source_index=0,
            ))

    logger.debug(f"Extracted {len(claims)} claims from answer ({len(answer)} chars)")
    return claims
