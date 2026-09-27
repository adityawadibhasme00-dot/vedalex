"""
Semantic chunker for legal/regulatory corpus.

- Splits text on section headings first so provisions stay atomic.
- Recursively splits oversized heading blocks at sentence boundaries.
- Overlaps neighbourhood boundaries so no provision is cut mid-thought.
- Target 500-800 tokens per chunk (default 650) with ~100 token overlap.
"""

import re
from typing import Any

MAX_TOKENS = 650
OVERLAP_TOKENS = 100
MIN_CHUNK_TOKENS = 140

_HEADING_PATTERNS = re.compile(
    r"(?m)^\s*(?:"
    r"(?:SECTION|Section|section)\s+\d+[A-Za-z]?\.?\s*[:.\-–—]?\s*[A-Za-z]|"
    r"(?:CHAPTER|Chapter|PART|Part|Schedule|Annexure)\s+[IVXLC\d]+[.:]?\s*[A-Za-z]|"
    r"\d{1,3}\.\s+[A-Z][A-Za-z][A-Za-z0-9&/(),\-\s]{4,}"
    r")\s*$"
)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r"\w+", text))


def _split_heading_blocks(text: str) -> list[dict[str, str]]:
    """Split text into [(section_heading, block)] preserving heading lines."""
    lines = text.split("\n")
    blocks: list[dict[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    def flush():
        nonlocal current_lines
        if current_lines:
            blocks.append({"heading": current_heading, "text": "\n".join(current_lines).strip()})
        current_lines = []

    for line in lines:
        stripped = line.strip().rstrip(":")
        if stripped and _HEADING_PATTERNS.match(line):
            flush()
            current_heading = stripped
        else:
            current_lines.append(line)
    flush()
    if not blocks:
        blocks.append({"heading": "", "text": text})
    return blocks


def _split_sentences(block: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?।])\s+", block)
    return [s.strip() for s in sentences if s.strip()]


def _chunk_block(block: str, max_tokens: int, overlap: int) -> list[str]:
    if not block.strip():
        return []
    if estimate_tokens(block) <= max_tokens:
        return [block.strip()]
    sentences = _split_sentences(block)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence) or 1
        if current and current_tokens + sentence_tokens > max_tokens:
            chunks.append(" ".join(current).strip())
            carry = current[-overlap:]
            current = list(carry)
            current_tokens = sum(estimate_tokens(s) for s in current)
        current.append(sentence)
        current_tokens += sentence_tokens
    if current:
        chunks.append(" ".join(current).strip())
    return [c for c in chunks if estimate_tokens(c) >= MIN_CHUNK_TOKENS or len(chunks) == 1]


def chunk_document(
    text: str,
    max_tokens: int = MAX_TOKENS,
    overlap: int = OVERLAP_TOKENS,
) -> list[dict[str, Any]]:
    """Chunk a normalized document into ``[{"text": ..., "heading": ...}]``."""
    if not text or not text.strip():
        return []
    result: list[dict[str, Any]] = []
    for block in _split_heading_blocks(text):
        for chunk in _chunk_block(block["text"], max_tokens, overlap):
            result.append({"text": chunk, "heading": block["heading"]})
    return result


def to_documents(
    text: str,
    title: str,
    url: str,
    metadata_base: dict[str, Any],
    max_tokens: int = MAX_TOKENS,
    overlap: int = OVERLAP_TOKENS,
) -> list[dict[str, Any]]:
    """Turn fetched text into ingest-ready documents (content + payload)."""
    chunks = chunk_document(text, max_tokens=max_tokens, overlap=overlap)
    docs: list[dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        doc = dict(metadata_base)
        doc["content"] = chunk["text"]
        doc["section_heading"] = chunk["heading"] or doc.get("section_heading", "")
        doc["chunk_index"] = i
        from app.ingestion.metadata import build_metadata
        merged = build_metadata(
            {"id": doc["source_id"], "name": doc["source"],
             "jurisdiction": doc["jurisdiction"], "authority": doc["authority"],
             "authority_level": doc["authority_level"], "priority": doc.get("priority", "P3"),
             "document_type": doc.get("document_type", ""), "category": doc.get("category", ""),
             "access_mode": doc.get("access_mode", "public")},
            url, title, chunk["text"], i,
        )
        merged.update({k: v for k, v in doc.items() if k not in merged})
        docs.append(merged)
    return docs