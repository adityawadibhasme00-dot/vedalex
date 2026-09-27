"""
Metadata assembly for ingested corpus documents.

Every chunk entering the vector store carries full provenance so citations in
the copilot answers resolve to the exact authority, jurisdiction and official
URL — mirroring the metadata contract in ``app.rag.qdrant_store``.
"""

import hashlib
import re
import time
from typing import Any


def _extract_year(title: str = "", text: str = "") -> int:
    for haystack in (title, (text or "")[:2000]):
        m = re.search(r"\b(19|20)\d{2}\b", haystack)
        if m:
            return int(m.group(0))
    return 0


def build_metadata(
    source: dict[str, Any],
    url: str,
    title: str,
    text: str,
    chunk_index: int = 0,
) -> dict[str, Any]:
    """Build the Qdrant payload fields for one ingested chunk."""
    jurisdiction = source.get("jurisdiction", "")
    authority = source.get("authority", "")
    document_type = source.get("document_type", "")

    doc_id = _doc_id(source.get("id", ""), url, chunk_index)
    return {
        "title": title[:300] or source.get("name", ""),
        "source": source.get("name", authority),
        "source_id": source.get("id", ""),
        "category": source.get("category", "regulatory"),
        "doc_id": doc_id,
        "authority": authority,
        "jurisdiction": jurisdiction,
        "authority_level": int(source.get("authority_level", 3)),
        "priority": source.get("priority", "P3"),
        "document_type": document_type,
        "taxonomy": source.get("category", document_type),
        "section_heading": "",
        "patent_number": "",
        "publication_year": _extract_year(title, text),
        "source_url": url,
        "effective_date": "",
        "chunk_index": chunk_index,
        "retrieval_method": "ingestion",
        "access_mode": source.get("access_mode", "public"),
        "retrieval_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "version": "1",
    }


def _doc_id(source_id: str, url: str, chunk_index: int) -> str:
    raw = f"{source_id}:{url}:{chunk_index}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"INGEST-{digest}"


def content_digest(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()