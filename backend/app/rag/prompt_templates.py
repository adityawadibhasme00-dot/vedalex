"""
Production-ready LLM prompt templates for VEDALEX RAG pipeline.

Enforces:
  1. Answer ONLY from retrieved context
  2. Mandatory citation of every factual statement
  3. Rejection of unsupported claims
  4. Confidence reporting
  5. Zero speculation — "I don't know" when evidence is insufficient
  6. Patent-specific formatting (claims, prior art, Section 3(p) analysis)
"""

from typing import List, Dict, Any, Optional


# ============================================================================
# System Prompt — Master instruction for the LLM
# ============================================================================

SYSTEM_PROMPT = """You are VEDALEX | IP-SAKTI SAHAYAK, an AI-powered Ayurveda Innovation Intelligence and Regulatory Decision Engine. You are a Senior AI Architect specializing in Retrieval-Augmented Generation (RAG), Patent Intelligence, Legal AI, and Ayurveda Regulatory Systems.

## YOUR CORE RULES (NEVER VIOLATE)

1. **ANSWER ONLY FROM RETRIEVED CONTEXT**: Every factual statement you make MUST come from the provided source documents. If the sources do not contain enough information, say "Insufficient evidence in the knowledge base."

2. **CITE EVERYTHING**: Every factual claim MUST include a citation in the format: [Source: <source_name>, Section: <section>]. Never make uncited factual claims.

3. **NEVER FABRICATE**: Do NOT invent patent numbers, dates, statistics, legal citations, or scientific claims. If you don't know, say so.

4. **NEVER SPECULATE**: Do not guess, infer beyond what the sources state, or provide hypothetical answers presented as facts.

5. **REPORT CONFIDENCE**: Always acknowledge the strength of evidence. Use phrases like "Based on the retrieved sources..." or "The evidence suggests..."

6. **REJECT UNSUPPORTED CLAIMS**: If a user asks about something not covered by the sources, respond with: "This query requires additional documentation. The current knowledge base does not contain sufficient evidence to answer this question reliably."

## MULTI-OMICS EVIDENCE RULES

When citing genomic, proteomic, metabolomic or pharmacogenomic evidence:
- Cite database identifiers ONLY if they appear verbatim in the retrieved sources (e.g., UniProt accession, NCBI Gene ID, PubChem CID, PMID).
- Never invent an accession, CID, gene symbol or PMID.
- Label the evidence type explicitly: "proteomics evidence", "metabolomic marker", "pharmacogenomic interaction".
- For pharmacogenomic interactions, distinguish documented findings from flagged risk ("documented interaction" vs "interaction risk flagged in screening").

## DOMAIN EXPERTISE

You specialize in:
- **Patent Readiness Assessment**: Evaluating Ayurvedic formulations for patentability under Indian Patents Act 1970, Section 3(p)
- **TKDL Overlap Detection**: Identifying Traditional Knowledge Digital Library prior art conflicts
- **Regulatory Navigation**: AYUSH, CDSCO, FSSAI, US DSHEA, Canada NHPR compliance
- **Scientific Evidence Review**: PubMed, pharmacopoeia, and clinical study retrieval
- **Freedom-to-Operate Analysis**: Patent landscape and infringement risk assessment
- **Claim Firewall**: Ensuring marketing claims comply with regulatory frameworks

## RESPONSE FORMAT

For every answer:
1. Start with a direct answer grounded in sources
2. Provide supporting evidence with citations
3. Note any limitations or gaps in the evidence
4. Suggest next steps when applicable
5. Include a confidence qualifier

## SECTION 3(p) SPECIFIC RULES

When discussing Indian patent law:
- Section 3(p) prohibits patents on "mere new form of known substance" unless enhanced efficacy is demonstrated
- Traditional Knowledge (TK) documented in TKDL constitutes prior art
- Synergistic effect data is required to overcome Section 3(p) objections
- Always cite the specific statutory provision and any relevant case law from sources

## PATENT CLAIM ANALYSIS RULES

When analyzing patent claims:
- Break down each claim element
- Map each element to source evidence
- Identify prior art conflicts
- Assess novelty and inventive step
- Note any TKDL overlaps
- Provide a claim-by-claim assessment with citations
"""


# ============================================================================
# RAG Context Injection Template
# ============================================================================

RAG_CONTEXT_TEMPLATE = """## RETRIEVED SOURCE DOCUMENTS

The following documents were retrieved from the VEDALEX knowledge base using semantic search, keyword matching, and metadata filtering. These are YOUR ONLY allowed sources for answering the question.

{sources_section}

---

## USER QUESTION

{query}

---

## INSTRUCTIONS

1. Answer the question using ONLY the retrieved sources above.
2. Cite each factual claim with [Source: <name>, Section: <section>].
3. If the sources do not contain enough information, state: "Insufficient evidence in the knowledge base for this query."
4. Do NOT use any knowledge outside these sources.
5. If multiple sources conflict, note the conflict and cite both.
6. Format your response clearly with headers and bullet points where appropriate.
"""


# ============================================================================
# Source Formatting
# ============================================================================

def format_sources_for_prompt(sources: List[Dict[str, Any]]) -> str:
    """Format retrieved sources into a structured context block for the LLM."""
    if not sources:
        return "No relevant sources found."

    parts = []
    for i, source in enumerate(sources, 1):
        content = source.get("content", "").strip()
        if not content:
            continue

        header_parts = [f"SOURCE {i}"]
        if source.get("title"):
            header_parts.append(f"Title: {source['title']}")
        if source.get("authority"):
            header_parts.append(f"Authority: {source['authority']}")
        if source.get("section_heading"):
            header_parts.append(f"Section: {source['section_heading']}")
        if source.get("patent_number"):
            header_parts.append(f"Patent: {source['patent_number']}")
        if source.get("jurisdiction"):
            header_parts.append(f"Jurisdiction: {source['jurisdiction']}")
        if source.get("effective_date"):
            header_parts.append(f"Effective: {source['effective_date']}")
        if source.get("source_url"):
            header_parts.append(f"URL: {source['source_url']}")
        if source.get("authority_level"):
            header_parts.append(f"Authority Level: {source['authority_level']}")
        if source.get("rerank_score"):
            header_parts.append(f"Relevance Score: {source['rerank_score']:.3f}")

        header = " | ".join(header_parts)
        parts.append(f"### {header}\n\n{content}")

    return "\n\n---\n\n".join(parts)


# ============================================================================
# Query-Specific Prompt Variants
# ============================================================================

PATENTABILITY_PROMPT = """Analyze the patentability of the described Ayurvedic formulation.

Focus on:
1. Novelty assessment (is this truly new or a known combination?)
2. Section 3(p) compliance (does it demonstrate enhanced efficacy?)
3. Prior art overlap with existing patents and TKDL records
4. Inventive step analysis
5. Sufficiency of disclosure

For each point, cite the relevant source. If prior art exists, identify the specific conflicts.
"""

PRIOR_ART_PROMPT = """Search for and analyze prior art related to this Ayurvedic innovation.

Focus on:
1. Existing patent families with similar claims
2. TKDL records documenting traditional knowledge
3. Published scientific literature
4. Any public disclosures that may affect novelty

For each prior art reference found, cite the source and explain how it relates to the query.
"""

REGULATORY_COMPLIANCE_PROMPT = """Analyze the regulatory requirements for this Ayurvedic product/innovation.

Cover:
1. Indian regulations (AYUSH, CDSCO, FSSAI)
2. International regulations (US DSHEA, Canada NHPR, EU Novel Food)
3. Labeling and claim requirements
4. Evidence requirements for regulatory approval
5. Compliance timeline and next steps

Cite each regulatory requirement with its source.
"""


# ============================================================================
# Prompt Builder
# ============================================================================

def build_rag_prompt(
    query: str,
    sources: List[Dict[str, Any]],
    intent: Optional[str] = None,
    passport_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Build the complete prompt for the LLM with retrieved context.

    Returns dict with 'system' and 'user' keys.
    """
    sources_text = format_sources_for_prompt(sources)

    # Select intent-specific instructions
    intent_instructions = ""
    if intent == "patentability":
        intent_instructions = PATENTABILITY_PROMPT
    elif intent == "prior_art":
        intent_instructions = PRIOR_ART_PROMPT
    elif intent in ("compliance", "regulatory_roadmap"):
        intent_instructions = REGULATORY_COMPLIANCE_PROMPT

    # Add passport context if available
    passport_section = ""
    if passport_context:
        passport_section = f"\n\n## INNOVATION PASSPORT CONTEXT\n\nThe user has an Innovation Passport with the following details:\n"
        for key, value in passport_context.items():
            if value and key not in ("id", "created_at", "updated_at"):
                passport_section += f"- **{key.replace('_', ' ').title()}**: {value}\n"

    user_prompt = RAG_CONTEXT_TEMPLATE.format(
        sources_section=sources_text,
        query=query,
    )

    if intent_instructions:
        user_prompt += f"\n\n## ADDITIONAL INSTRUCTIONS FOR THIS QUERY TYPE\n\n{intent_instructions}"

    if passport_section:
        user_prompt += passport_section

    return {
        "system": SYSTEM_PROMPT,
        "user": user_prompt,
    }


# ============================================================================
# Post-Processing Validation Prompt
# ============================================================================

VALIDATION_PROMPT = """Review the following answer for compliance with RAG ground rules.

ANSWER:
{answer}

SOURCES USED:
{sources}

CHECK:
1. Does every factual claim have a citation?
2. Are there any patent numbers, dates, or statistics not found in the sources?
3. Does the answer contain absolute claims without evidence?
4. Is the confidence level appropriate given the source quality?
5. Does the answer address the user's question directly?

Return a JSON object with:
- "compliant": true/false
- "issues": list of specific issues found
- "suggested_fixes": list of suggested corrections
"""


# ============================================================================
# Verification & Regeneration Prompt
# ============================================================================

REGENERATION_PROMPT = """Your previous answer contained claims that were not sufficiently supported by the retrieved evidence.

## UNSUPPORTED OR CONTRADICTED CLAIMS

The following claims from your previous answer could NOT be verified against the retrieved sources:
{unsupported_claims}

## SUPPORTED CLAIMS

The following claims WERE supported by the retrieved evidence and should be kept:
{supported_claims}

## RETRIEVED EVIDENCE (YOUR ONLY ALLOWED SOURCES)

{sources_section}

## USER QUESTION

{query}

## INSTRUCTIONS

1. Rewrite the answer using ONLY the retrieved evidence above.
2. REMOVE every unsupported or contradicted claim — do not rephrase them to make them fit.
3. Do not add any information not present in the sources.
4. Cite each kept claim with [Source: <source_name>, Section: <section>].
5. If no claims remain verifiable, respond exactly: "Insufficient verified information. The available sources do not provide enough evidence to answer this reliably."
6. Keep the answer concise and strictly grounded.
"""


def build_regeneration_prompt(
    query: str,
    sources: List[Dict[str, Any]],
    unsupported_claims: List[str],
    supported_claims: List[str],
) -> Dict[str, str]:
    """
    Build a prompt for regenerating an answer after verification failure.

    The LLM is given ONLY the supported claims and the retrieved evidence,
    and must produce a new answer that excludes all unsupported content.
    """
    sources_text = format_sources_for_prompt(sources)

    unsupported_section = "\n".join(f"- {c}" for c in unsupported_claims) if unsupported_claims else "None"
    supported_section = "\n".join(f"- {c}" for c in supported_claims) if supported_claims else "None"

    user_prompt = REGENERATION_PROMPT.format(
        unsupported_claims=unsupported_section,
        supported_claims=supported_section,
        sources_section=sources_text,
        query=query,
    )

    return {
        "system": SYSTEM_PROMPT,
        "user": user_prompt,
    }
