"""India Code statute harvester — section-level Indian law into the vector store.

Pulls section texts for the tracked Central Acts from the keyless IndiaCode API
and upserts them through the same chunker + Qdrant pipeline the curated corpus
uses. A content-hash ledger at backend/data/indiacode_state.json means repeated
runs only re-embed sections whose text changed.

Unlike the PDF corpus this is *section-located* law: each section is its own
document with a precise locator (act_id + section number), so citations resolve
to the exact provision.
"""

import json
import logging
import os
import time
from typing import Any

from app.ingestion import chunker, normalizer
from app.services import indiacode_client as ic

logger = logging.getLogger(__name__)

LEDGER = os.path.join(os.path.dirname(__file__), "..", "..", "data", "indiacode_state.json")


def _load_ledger() -> dict[str, Any]:
    try:
        with open(LEDGER, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"docs": {}}


def _save_ledger(ledger: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=2)


def _build_base_metadata(document: dict[str, Any]) -> dict[str, Any]:
    """Map the extraction-schema document onto the Qdrant payload contract."""
    loc = document["locator"]
    return {
        "title": document["title"][:300],
        "source": "India Code (eCourtsIndia) — Legislative Department",
        "source_id": "india_code",
        "category": "regulatory",
        "doc_id": document["document_id"],
        "authority": document["authority"],
        "jurisdiction": document["jurisdiction"],
        "authority_level": 1,
        "priority": "P0",
        "document_type": "statute",
        "taxonomy": "statute",
        "section_heading": loc.get("section_heading", ""),
        "patent_number": "",
        "publication_year": 0,
        "source_url": document["source_url"],
        "effective_date": document.get("effective_from", ""),
        "chunk_index": 0,
        "retrieval_method": "india_code_api",
        "access_mode": "public",
        "retrieval_timestamp": document.get("retrieved_at", ""),
        "version": "1",
        "act_name": loc.get("act_name", ""),
        "act_id": loc.get("act_id", ""),
        "section_number": loc.get("section", ""),
        "checksum": document.get("checksum", ""),
    }


def harvest_indiacode(
    act_ids: list[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Fetch + embed + upsert India Code statute sections.

    Args:
        act_ids: subset of tracked act ids; None = all tracked acts.
        force: ignore the change-detection ledger and re-embed everything.
    """
    from app.rag.qdrant_store import QdrantVectorStore
    store = QdrantVectorStore()

    ledger = _load_ledger()
    acts = [a for a in ic.INDIA_CODE_ACTS if not act_ids or a["id"] in act_ids]

    results: list[dict[str, Any]] = []
    total_chunks = 0

    for act in acts:
        doc_ledger = ledger["docs"].get(act["id"], {})
        existing_checksum = doc_ledger.get("checksums", {})

        docs = ic.harvest_sections_for_act(act)
        if not docs:
            results.append({"act": act["id"], "status": "no_sections"})
            continue
        register_section_passages(docs)

        act_chunks = 0
        act_checksums: dict[str, str] = {}
        for document in docs:
            checksum = document["checksum"]
            act_checksums[document["document_id"]] = checksum
            if not force and existing_checksum.get(document["document_id"]) == checksum:
                continue

            text = normalizer.normalize_text(document["text"])
            if len(text) < 200:
                continue
            base = _build_base_metadata(document)
            chunks = chunker.to_documents(text, document["title"], document["source_url"], base, max_tokens=650)
            if not chunks:
                continue

            upserted = store.upsert_documents(chunks, batch_size=32)
            act_chunks += len(chunks)
            total_chunks += len(chunks)
            results.append({
                "act": act["id"],
                "section": document["locator"]["section"],
                "status": "ingested",
                "chunks": len(chunks),
                "upserted": upserted,
            })

        ledger["docs"][act["id"]] = {
            "checksums": act_checksums,
            "sections": len(docs),
            "chunks": act_chunks,
            "last_run": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        logger.info("India Code act %s: %d sections, %d chunks", act["id"], len(docs), act_chunks)

    _save_ledger(ledger)
    return {
        "ok": True,
        "acts": [a["id"] for a in acts],
        "total_chunks": total_chunks,
        "results": results,
        "ledger": LEDGER,
    }


def indiacode_status() -> dict[str, Any]:
    ledger = _load_ledger()
    return {
        "api": ic.india_code_status(),
        "ledger": LEDGER,
        "acts": ledger.get("docs", {}),
    }


def register_section_passages(documents: list[dict[str, Any]]) -> int:
    """Register harvested statute sections as citable statutory passages.

    Each section becomes a StatutoryCitation-grade passage (section_reference,
    exact text, authority, jurisdiction, source_url) so the zero-hallucination
    retrieval engine can Cite-or-Withhold from live statute text without
    re-embedding.
    """
    from app.services.retrieval_engine import HybridRetrievalEngine
    passages = []
    for document in documents:
        loc = document.get("locator", {})
        passages.append({
            "act_title": document.get("title", ""),
            "section_reference": f"Section {loc.get('section', '')}",
            "authority": document.get("authority", "Legislative Department, Government of India"),
            "jurisdiction": document.get("jurisdiction", "India"),
            "exact_passage": (document.get("text", "") or "")[:1200],
            "source_url": document.get("source_url", ""),
            "effective_date": document.get("effective_from", ""),
            "authority_rank": 1,
            "keywords": ["section", str(loc.get("section", "")), str(loc.get("act_id", "")),
                        document.get("document_id", "")],
        })
    if passages:
        HybridRetrievalEngine.add_passages(passages)
    return len(passages)