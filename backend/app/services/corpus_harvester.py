"""
Curated authoritative-corpus harvester (IP India / NBA patent-legal documents).

Ingests the high-signal official documents that the copilot actually answers
with — full text of the Patents Act 1970 (EN + HI), Patents Rules 2003,
examination guidelines, pharmaceutical-examination guidelines, CRI guidelines,
the 2023 amendment act, and an NBA procedure document.

Runs INSIDE the backend process so it writes through the already-open Qdrant
client (the local Qdrant storage folder is single-owner locked).

Change detection: a content-hash ledger at backend/data/curated_corpus_state.json
means repeated runs only re-embed documents that changed.
"""

import json
import logging
import os
import time
from typing import Any

from app.ingestion import fetchers, normalizer
from app.ingestion import metadata as md
from app.ingestion.chunker import to_documents

logger = logging.getLogger(__name__)

LEDGER = os.path.join(os.path.dirname(__file__), "..", "..", "data", "curated_corpus_state.json")

IP_INDIA_BASE = "https://ipindia.gov.in/storage/uploads/docs-operator"

# Curated official patent-legal corpus. URL order = authoritative.
CORPUS_MANIFEST: list[dict[str, Any]] = [
    {
        "title": "The Patents Act, 1970 — consolidated full text",
        "url": f"{IP_INDIA_BASE}/df4efbcf-6fdf-4b2b-b6d6-56853aa39083.pdf",
        "document_type": "regulations",
        "category": "regulatory",
        "authority": "Office of the Controller General of Patents, Designs & Trade Marks (CGPDTM)",
    },
{
        "title": "The Patents Rules, 2003",
        "url": f"{IP_INDIA_BASE}/5c2404f2-42f4-4aee-b0c9-dc06d687bbf5.pdf",
        "document_type": "regulations",
        "category": "regulatory",
        "authority": "Office of the Controller General of Patents, Designs & Trade Marks (CGPDTM)",
    },
    {
        "title": "Jan Vishwas (Amendment of Provisions) Act, 2023",
        "url": f"{IP_INDIA_BASE}/8f3e28fb-b6af-4e43-bbe9-10fa373274fb.pdf",
        "document_type": "regulations",
        "category": "regulatory",
        "authority": "Legislative Department, Ministry of Law and Justice",
    },
    {
        "title": "Guidelines for Search and Examination of Patent Applications",
        "url": f"{IP_INDIA_BASE}/e23412b4-6beb-4a55-a7ae-276aaed28eaf.pdf",
        "document_type": "guidelines",
        "category": "patent",
        "authority": "Office of the Controller General of Patents, Designs & Trade Marks (CGPDTM)",
    },
    {
        "title": "Guidelines for Examination of Patent Applications in the Field of Pharmaceuticals",
        "url": f"{IP_INDIA_BASE}/cbdc240a-0de2-42e5-ac0f-ef020640101d.pdf",
        "document_type": "guidelines",
        "category": "patent",
        "authority": "Office of the Controller General of Patents, Designs & Trade Marks (CGPDTM)",
    },
    {
        "title": "Guidelines for Examination of Computer Related Inventions (CRIs)",
        "url": f"{IP_INDIA_BASE}/125154d2-4490-41aa-9a8c-0ee97219692f.pdf",
        "document_type": "guidelines",
        "category": "patent",
        "authority": "Office of the Controller General of Patents, Designs & Trade Marks (CGPDTM)",
    },
    {
        "title": "Guidelines for Examination of Patent Applications (2025)",
        "url": f"{IP_INDIA_BASE}/335e2746-58c1-4b56-a1e5-cdd172a92a3c.pdf",
        "document_type": "guidelines",
        "category": "patent",
        "authority": "Office of the Controller General of Patents, Designs & Trade Marks (CGPDTM)",
    },
{
        "title": "Access and Benefit Sharing Guidelines, 2014 (India)",
        "url": "https://nbaindia.org/uploaded/pdf/Access_and_Benefit_Sharing_Guidelines_2014.pdf",
        "document_type": "biodiversity_protocol",
        "category": "regulatory",
        "authority": "National Biodiversity Authority of India (NBA)",
        "jurisdiction": "India",
    },
]


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


def _source_meta(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "ipindia_docs",
        "name": f"Intellectual Property India (CGPDTM) — {entry['title']}",
        "jurisdiction": entry.get("jurisdiction", "India"),
        "authority": entry["authority"],
        "authority_level": 1,
        "priority": "P0",
        "document_type": entry["document_type"],
        "category": entry["category"],
        "access_mode": "public",
    }


def harvest_documents(
    target: list[str] | None = None,
    limit_per_doc: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Fetch + embed + upsert curated corpus documents.

    Args:
        target: optional subset of URLs (exact match) — None = all.
        limit_per_doc: cap chunks embedded per document.
        force: ignore the change-detection ledger and re-embed everything.
    """
    from app.rag.qdrant_store import QdrantVectorStore
    store = QdrantVectorStore()

    ledger = _load_ledger()
    results: list[dict[str, Any]] = []
    total_chunks = 0

    for entry in CORPUS_MANIFEST:
        url = entry["url"]
        if target and url not in target:
            continue
        try:
            text = fetchers.fetch_pdf(url)
            if not text or len(normalizer.normalize_text(text)) < 300:
                results.append({"title": entry["title"], "status": "skipped", "reason": "no extractable text"})
                continue
            text = normalizer.normalize_text(text)
            digest = md.content_digest(text)

            doc_ledger = ledger["docs"].get(url)
            if not force and doc_ledger and doc_ledger.get("hash") == digest:
                results.append({"title": entry["title"], "status": "unchanged", "chunks": doc_ledger.get("chunks", 0)})
                continue

            base = md.build_metadata(_source_meta(entry), url, entry["title"], text, 0)
            docs = to_documents(text, entry["title"], url, base, max_tokens=650)
            if limit_per_doc is not None:
                docs = docs[:limit_per_doc]
            if not docs:
                results.append({"title": entry["title"], "status": "skipped", "reason": "no chunks"})
                continue

            upserted = store.upsert_documents(docs, batch_size=32)
            ledger["docs"][url] = {
                "hash": digest,
                "chunks": len(docs),
                "upserted": upserted,
                "last_run": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            total_chunks += len(docs)
            results.append({"title": entry["title"], "status": "ingested",
                            "chunks": len(docs), "upserted": upserted})
            logger.info("Harvested %s: %d chunks -> %d upserted", entry["title"], len(docs), upserted)
        except Exception as exc:
            logger.exception("Harvest failed for %s", entry["title"])
            results.append({"title": entry["title"], "status": "error", "error": str(exc)[:160]})

    _save_ledger(ledger)
    return {
        "ok": True,
        "total_documents": len(results),
        "total_chunks": total_chunks,
        "results": results,
        "ledger": LEDGER,
    }


def harvester_status() -> dict[str, Any]:
    ledger = _load_ledger()
    return {
        "manifest_size": len(CORPUS_MANIFEST),
        "ledger": LEDGER,
        "docs": ledger.get("docs", {}),
        "manifest": [
            {"title": e["title"], "url": e["url"], "document_type": e["document_type"]}
            for e in CORPUS_MANIFEST
        ],
    }

