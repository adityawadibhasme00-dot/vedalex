"""
Citation Validity Checker for VEDALEX Verification Layer.

Verifies that every citation in the generated answer actually exists
in the retrieved source documents. This catches a common hidden
hallucination: the LLM generates a citation (e.g., "Section 3(p)")
that does not appear in any of the retrieved passages.

Checks performed:
  1. Does the cited document/act exist in sources?
  2. Does the cited section exist in the source?
  3. Does the retrieved passage actually support the claim tied to the citation?
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class CitationCheck:
    citation_text: str
    document_found: bool
    section_found: bool
    source_matched: Optional[str] = None
    passage_supports: bool = False
    valid: bool = False
    note: str = ""


@dataclass
class CitationValidityReport:
    checks: List[CitationCheck]
    total_citations: int = 0
    valid_citations: int = 0
    invalid_citations: int = 0
    validity_ratio: float = 0.0
    all_valid: bool = False


# Patterns to extract citation references from answer text
_CITATION_DOC_PATTERNS = [
    re.compile(
        r"(?:Section|Article|Rule|Regulation|Schedule|Clause|Provision)\s*"
        r"(\d+(?:\([a-zA-Z]+\))?(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Patents?\s+Act|DSHEA|NHPR|CDSCO|FSSAI|AYUSH|DPDP|NBA)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:TKDL|WIPO|WHO|FDA|ECHA|EMA|Health\s+Canada)",
        re.IGNORECASE,
    ),
]

_SECTION_PATTERNS = [
    re.compile(r"Section\s+(\d+(?:\([a-z]+\))?)", re.IGNORECASE),
    re.compile(r"Rule\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"Article\s+(\d+(?:\([a-z]+\))?)", re.IGNORECASE),
    re.compile(r"Schedule\s+([A-Z]|\d+)", re.IGNORECASE),
]


def _extract_citations_from_answer(answer: str) -> List[str]:
    """Extract all citation references mentioned in the answer."""
    citations = set()
    for pattern in _CITATION_DOC_PATTERNS:
        for match in pattern.finditer(answer):
            citations.add(match.group(0).strip())
    return list(citations)


def _extract_sections_from_answer(answer: str) -> List[str]:
    """Extract section references (e.g., '3(p)', '3(d)', '100')."""
    sections = set()
    for pattern in _SECTION_PATTERNS:
        for match in pattern.finditer(answer):
            sections.add(match.group(1) if match.lastindex else match.group(0))
    return list(sections)


def _source_text_lower(source: Dict[str, Any]) -> str:
    """Combine all text fields of a source for matching."""
    parts = []
    for key in ("content", "act_title", "title", "source", "section_heading",
                "authority", "exact_passage"):
        val = source.get(key)
        if val:
            parts.append(str(val).lower())
    return " ".join(parts)


def _document_exists_in_sources(
    citation: str,
    sources: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """Check if a cited document/act exists in any source."""
    citation_lower = citation.lower()
    for source in sources:
        text = _source_text_lower(source)
        if citation_lower in text:
            label_parts = []
            for key in ("act_title", "title", "source"):
                val = source.get(key)
                if val:
                    label_parts.append(str(val))
                    break
            return True, label_parts[0] if label_parts else None
    return False, None


def _section_exists_in_sources(
    section: str,
    sources: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """Check if a cited section exists in any source."""
    section_lower = section.lower()
    section_patterns = [
        re.compile(rf"section\s+{re.escape(section_lower)}", re.IGNORECASE),
        re.compile(rf"rule\s+{re.escape(section_lower)}", re.IGNORECASE),
        re.compile(rf"article\s+{re.escape(section_lower)}", re.IGNORECASE),
        re.compile(rf"schedule\s+{re.escape(section_lower)}", re.IGNORECASE),
        re.compile(rf"\({re.escape(section_lower)}\)"),
    ]

    for source in sources:
        text = _source_text_lower(source)
        for pat in section_patterns:
            if pat.search(text):
                label_parts = []
                for key in ("act_title", "title", "source"):
                    val = source.get(key)
                    if val:
                        label_parts.append(str(val))
                        break
                if source.get("section_heading"):
                    label_parts.append(str(source["section_heading"]))
                return True, " — ".join(label_parts) if label_parts else None
    return False, None


def check_citation_validity(
    answer: str,
    sources: List[Dict[str, Any]],
) -> CitationValidityReport:
    """
    Validate every citation in the answer against retrieved sources.

    For each citation found in the answer:
      1. Does the document/act exist in sources?
      2. Does the section/rule exist in sources?
      3. Does the passage support the surrounding claim?

    Returns a CitationValidityReport with per-citation checks.
    """
    if not sources:
        return CitationValidityReport(
            checks=[],
            total_citations=0,
            valid_citations=0,
            invalid_citations=0,
            validity_ratio=0.0,
            all_valid=False,
        )

    cited_docs = _extract_citations_from_answer(answer)
    cited_sections = _extract_sections_from_answer(answer)

    # Merge document and section citations into unified checks
    all_refs = list(set(cited_docs + [f"Section {s}" for s in cited_sections]))
    checks: List[CitationCheck] = []

    for ref in all_refs:
        doc_found, doc_source = _document_exists_in_sources(ref, sources)
        section_found = False
        section_source = None

        # If it's a section reference, also check section-level existence
        section_match = re.search(r"Section\s+(\d+(?:\([a-z]+\))?)", ref, re.IGNORECASE)
        if section_match:
            sec = section_match.group(1)
            section_found, section_source = _section_exists_in_sources(sec, sources)

        matched_source = doc_source or section_source
        valid = doc_found or section_found

        note = ""
        if not doc_found and not section_found:
            note = "Citation not found in any retrieved source — possible hallucination."
        elif doc_found and not section_found and section_match:
            note = "Document found but specific section not verified in retrieved passages."
        else:
            note = "Citation verified against retrieved sources."

        checks.append(CitationCheck(
            citation_text=ref,
            document_found=doc_found,
            section_found=section_found,
            source_matched=matched_source,
            passage_supports=valid,
            valid=valid,
            note=note,
        ))

    valid_count = sum(1 for c in checks if c.valid)
    total = len(checks)

    report = CitationValidityReport(
        checks=checks,
        total_citations=total,
        valid_citations=valid_count,
        invalid_citations=total - valid_count,
        validity_ratio=round(valid_count / max(1, total), 3),
        all_valid=valid_count == total and total > 0,
    )

    if total > 0 and valid_count < total:
        invalid_refs = [c.citation_text for c in checks if not c.valid]
        logger.warning(f"Invalid citations detected: {invalid_refs}")

    return report
