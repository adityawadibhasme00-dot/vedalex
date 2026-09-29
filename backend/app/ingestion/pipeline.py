"""
End-to-end ingestion pipeline for IP-SAKTI's RAG knowledge base.

Flow per source: fetch -> extract -> normalize -> metadata -> chunk -> embed
-> upsert to Qdrant, with:
  - content-hash change detection (only changed documents are re-embedded)
  - licensing guardrail enforcement (restricted sources = pointers/citations only)
  - local corpus + knowledge-seed ingestion
  - BM25 index refresh after new vectors land

Usage:
    python -m app.ingestion --sources p0 --mode update
"""

import glob
import json
import logging
import os
import time
from typing import Any

from app.ingestion import fetchers, normalizer
from app.ingestion import metadata as md
from app.ingestion import sources as src
from app.ingestion.chunker import to_documents

logger = logging.getLogger(__name__)

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "ingestion_state.json")

CATEGORY_BY_SEED_FILE = {
    "botanical_synonyms": "botanical",
    "api_monographs": "pharmacopoeia",
    "acts_and_gazettes": "statutory",
    "evidence_ladders": "regulatory",
    "safety_signals": "safety",
    "export_market_requirements": "regulatory",
    "perm_tk_prior_art": "tkdl",
    "white_space": "regulatory",
    "claim_alternatives": "regulatory",
}

# Seed files that are internal structures rather than citable legal content.
# Loaded directly by the code that needs them; never indexed for retrieval.
NON_RETRIEVABLE_SEED_FILES = frozenset({
    "provision_graph",
    "corpus_manifest",
})


def _load_state() -> dict[str, Any]:
    try:
        with open(STATE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"sources": {}, "last_global_run": None}


def _save_state(state: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def _upsert(documents: list[dict[str, Any]]) -> int:
    if not documents:
        return 0
    from app.rag.qdrant_store import QdrantVectorStore
    store = QdrantVectorStore()
    return store.upsert_documents(documents, batch_size=32)


def _refresh_bm25() -> None:
    """Rebuild the in-memory BM25 index from Qdrant after ingestion."""
    try:
        from app.rag.qdrant_store import QdrantVectorStore
        from app.rag.retrieval_pipeline import HybridRetriever
        store = QdrantVectorStore()
        docs = store.get_all_documents(limit=8000)
        if docs:
            HybridRetriever.build_bm25_index(docs)
            logger.info("BM25 index refreshed (%d documents)", len(docs))
    except Exception as exc:
        logger.debug("BM25 refresh skipped: %s", exc)


def ingest_one_url(
    source: dict[str, Any],
    url: str,
    state: dict[str, Any],
    mode: str,
    limit_per_source: int | None,
) -> list[dict[str, Any]]:
    """Fetch one URL for a source, chunk it, and upsert (change-aware)."""
    title, text = None, None
    if url.endswith(".pdf"):
        text = fetchers.fetch_pdf(url)
        title = source.get("name", url.split("/")[-1])
    else:
        fetched = fetchers.fetch_html(url)
        if fetched:
            title, text = fetched
    if not text or len(normalizer.normalize_text(text)) < 120:
        return []

    text = normalizer.normalize_text(text)
    digest = md.content_digest(text)

    per_source = state["sources"].setdefault(source["id"], {})
    url_state = per_source.get("urls", {}).get(url, {})
    if mode != "full" and url_state.get("hash") == digest:
        logger.info("  unchanged: %s (%s)", source["id"], url)
        return []

    base = md.build_metadata(source, url, title or source["name"], text, 0)
    docs = to_documents(text, title or source["name"], url, base)
    if limit_per_source is not None:
        docs = docs[:limit_per_source]
    upserted = _upsert(docs)
    per_source.setdefault("urls", {})[url] = {
        "hash": digest,
        "chunks": len(docs),
        "upserted": upserted,
        "last_run": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    logger.info("  ingested %d chunks from %s", len(docs), url)
    return docs


def _allowed_urls(source: dict[str, Any], query: str | None) -> list[str]:
    """URLs to harvest for a source, honouring its access mode."""
    urls = list(source.get("canonical_urls") or [])
    mode = source.get("access_mode", "public")

    if mode == "restricted":
        # TKDL licence: never scrape search results. Authorized pointers only.
        urls = list(source.get("pointer_urls") or []) or urls[:1]
        logger.info("Restricted source %s: pointers only (%d URLs)", source["id"], len(urls))
        return urls

    if query:
        found = fetchers.search_source(urls, query, top=3)
        return found or urls
    return urls


def ingest_source(source: dict[str, Any], mode: str = "update", query: str | None = None,
                  limit_per_source: int | None = None) -> dict[str, Any]:
    state = _load_state()
    urls = _allowed_urls(source, query)
    harvested: list[dict[str, Any]] = []
    for url in urls:
        docs = ingest_one_url(source, url, state, mode, limit_per_source)
        harvested.extend(docs)
    state["sources"].setdefault(source["id"], {})["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _save_state(state)
    return {
        "source_id": source["id"],
        "name": source["name"],
        "priority": source["priority"],
        "access_mode": source["access_mode"],
        "urls": url,
        "chunks": len(harvested),
    }


def _json_value_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


# Seed records whose id is the stable key that provision_graph.json keys on.
_PROVISION_ID_FIELDS = ("id", "canonical_id", "provision_id")


def _seed_units(data: Any) -> list[tuple[str, str, dict[str, Any]]]:
    """Split a seed file into individually indexable units.

    Returns ``(unit_key, text, record)`` per unit.

    A list-shaped seed is indexed **per record**. Collapsing the whole list into
    one ``entry:`` blob destroys record identity, which breaks two things:

    1. Citation granularity — chunks span several Acts at once, so a chunk
       cannot be attributed to the provision it actually came from.
    2. Provision identity — nothing in the payload says which provision a chunk
       is, so the cross-reference graph in ``provision_graph.py`` can never be
       joined to a retrieved chunk.

    Dict-shaped seeds (botanical_synonyms, treaties_metadata) keep their
    existing whole-file behaviour, since their keys *are* the record identity.
    """
    if isinstance(data, list):
        units: list[tuple[str, str, dict[str, Any]]] = []
        for i, record in enumerate(data):
            if isinstance(record, dict):
                key = ""
                for field in _PROVISION_ID_FIELDS:
                    value = record.get(field)
                    if isinstance(value, str) and value.strip():
                        key = value.strip()
                        break
                key = key or f"entry_{i}"
                text = "\n".join(
                    f"{k}: {_json_value_text(v)}" for k, v in record.items()
                )
                units.append((key, text, record))
            else:
                units.append((f"entry_{i}", _json_value_text(record), {}))
        return units
    text = "\n".join(
        f"{k}: {_json_value_text(v)}" for k, v in (data or {}).items()
    )
    return [("__file__", text, {})]


def _record_metadata(
    record: dict[str, Any], fallback: dict[str, Any]
) -> dict[str, Any]:
    """Per-record payload overrides.

    The seed source is hardcoded to ``jurisdiction: India`` because that is
    what most of the corpus is. A US or Canadian Act indexed under that tag is
    then treated as Indian law by ``filter_sources_by_jurisdiction``: it
    survives an India filter as domestic evidence, and is dropped from an
    International filter. That silently defeats the "never mix legal
    frameworks" rule, so a record's own jurisdiction must win.
    """
    out: dict[str, Any] = {}
    for field in ("jurisdiction", "authority", "act_title", "source_url"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            out[field] = value.strip()
    rank = record.get("authority_rank")
    if isinstance(rank, (int, float)):
        out["authority_level"] = int(rank)

    # Join to the cross-reference graph where this record *is* a provision.
    key = ""
    for field in _PROVISION_ID_FIELDS:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            key = value.strip()
            break
    if key:
        try:
            from app.services import provision_graph as _pg
            provision_ids = _pg.provisions_for_record(key)
            if provision_ids:
                # Always a list: one Act record can back several provisions
                # (e.g. the FD&C Act record covers both 21 U.S.C. 321(g)(1)(B)
                # and 21 U.S.C. 355), and Qdrant indexes a KEYWORD array
                # natively.
                out["provision_id"] = provision_ids
                first = _pg.get_provision(provision_ids[0]) or {}
                out["effective_from"] = first.get("effective_from", "") or ""
                out["effective_to"] = first.get("effective_to", "") or ""
                out["citation_locator"] = first.get("citation_locator", "") or ""
                out["verification_status"] = first.get("verification_status", "") or ""
        except Exception:  # graph must never break ingestion
            pass
    return out


def ingest_local_corpus(mode: str = "update") -> dict[str, Any]:
    """Index curated files under backend/data/** (txt/md/json/pdf/docx)."""
    base = os.path.join(os.path.dirname(STATE_FILE))
    state = _load_state()
    per_source = state["sources"].setdefault("local_corpus", {})
    per_source.setdefault("files", {})
    harvested: list[dict[str, Any]] = []
    patterns = [
        os.path.join(base, "**", "*.txt"),
        os.path.join(base, "**", "*.md"),
        os.path.join(base, "**", "*.json"),
        os.path.join(base, "**", "*.csv"),
        os.path.join(base, "**", "*.pdf"),
        os.path.join(base, "**", "*.docx"),
        os.path.join(base, "**", "*.png"),
        os.path.join(base, "**", "*.jpg"),
        os.path.join(base, "**", "*.jpeg"),
    ]
    seen_files = set()
    for pattern in patterns:
        for path in glob.glob(pattern, recursive=True):
            seen_files.add(os.path.normpath(path))

    for path in sorted(seen_files):
        parsed = fetchers.read_local_file(path)
        if not parsed:
            continue
        title, text = parsed
        text = normalizer.normalize_text(text)
        digest = md.content_digest(text)
        if mode != "full" and per_source["files"].get(path, {}).get("hash") == digest:
            continue
        source = {
            "id": "local_corpus", "name": f"Local corpus — {title}",
            "jurisdiction": "Mixed", "authority": "Curated internal corpus",
            "authority_level": 3, "priority": "P0", "document_type": "regulations",
            "category": "regulatory", "access_mode": "authorized",
        }
        base_md = md.build_metadata(source, path, title, text, 0)
        docs = to_documents(text, title, path, base_md)
        upserted = _upsert(docs)
        per_source["files"][path] = {"hash": digest, "chunks": len(docs), "upserted": upserted}
        harvested.extend(docs)
        logger.info("  ingested %d chunks from %s", len(docs), path)
    _save_state(state)
    return {"source_id": "local_corpus", "name": "Local corpus", "chunks": len(harvested)}


def ingest_knowledge_seeds(mode: str = "update") -> dict[str, Any]:
    """Index canonical seed JSON (app/knowledge/*.json) as retrievable docs."""
    state = _load_state()
    per_source = state["sources"].setdefault("knowledge_seeds", {})
    per_source.setdefault("files", {})
    harvested: list[dict[str, Any]] = []
    seed_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    if not os.path.isdir(seed_dir):
        return {"source_id": "knowledge_seeds", "name": "Knowledge seeds", "chunks": 0}
    for path in sorted(glob.glob(os.path.join(seed_dir, "*.json"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if name in NON_RETRIEVABLE_SEED_FILES:
            # The graph is a lookup structure, not legal text. Indexing it would
            # put internal provision IDs and edge records into the retrievable
            # corpus, where they could be quoted back to a judge as though they
            # were statutory wording. The provisions' actual text is indexed
            # from the Act records in acts_and_gazettes.json.
            logger.debug("Skipping non-retrievable seed %s", name)
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            logger.warning("Seed read failed %s: %s", path, exc)
            continue
        units = _seed_units(data)
        # File-level digest: the whole file is the unit of change detection, as
        # before, so an unchanged file is still skipped.
        digest = md.content_digest("\n\n".join(text for _, text, _ in units))
        if mode != "full" and per_source["files"].get(name, {}).get("hash") == digest:
            continue
        base_source = {
            "id": "knowledge_seeds", "name": f"IP-SAKTI canonical seeds — {name}",
            "jurisdiction": "India", "authority": "IP-SAKTI canonical knowledge seeds",
            "authority_level": 1, "priority": "P0",
            "document_type": "regulations",
            "category": CATEGORY_BY_SEED_FILE.get(name, "regulatory"),
            "access_mode": "authorized",
        }
        file_docs: list[dict[str, Any]] = []
        for unit_key, unit_text, record in units:
            text = normalizer.normalize_text(unit_text)
            overrides = _record_metadata(record, base_source)
            source = dict(base_source)
            source.update(overrides)
            base_md = md.build_metadata(source, path, unit_key, text, 0)
            # build_metadata synthesises doc_id from source_id+url+index, which
            # is identical for every record in the file. Set it explicitly so
            # each record is addressable, and let the provision fields ride
            # through to_documents' metadata merge.
            base_md["doc_id"] = f"{name}:{unit_key}"
            for key, value in overrides.items():
                if key in ("provision_id", "effective_from", "effective_to",
                           "citation_locator", "verification_status"):
                    base_md[key] = value
            file_docs.extend(
                to_documents(text, unit_key, path, base_md, max_tokens=500)
            )
        upserted = _upsert(file_docs)
        per_source["files"][name] = {"hash": digest, "chunks": len(file_docs), "upserted": upserted}
        harvested.extend(file_docs)
        logger.info("  ingested %d chunks from seed %s", len(file_docs), name)
    _save_state(state)
    return {"source_id": "knowledge_seeds", "name": "Knowledge seeds", "chunks": len(harvested)}


def run_ingestion(
    source_ids: list[str] | None = None,
    mode: str = "update",
    include_local: bool = True,
    include_seeds: bool = True,
    query: str | None = None,
    limit_per_source: int | None = None,
) -> dict[str, Any]:
    """
    Orchestrate a full or incremental ingest pass.

    Args:
        source_ids: None -> all corpus sources. Accepts ids/P0-P3/all/daily/weekly/monthly.
        mode: update (hash-aware) | full (force re-embed, chunks unchanged) | refresh.
        include_local / include_seeds: include the curated local corpus / seed JSONs.
    """
    selected = src.resolve_source_ids(source_ids) if source_ids else list(src.CORPUS)
    if not selected:
        return {"ok": False, "error": "No sources matched", "sources": []}

    started = time.time()
    results: list[dict[str, Any]] = []
    total_chunks = 0

    for source in selected:
        try:
            res = ingest_source(source, mode=mode, query=query, limit_per_source=limit_per_source)
            results.append(res)
            total_chunks += res.get("chunks", 0)
        except Exception as exc:
            logger.exception("Ingestion failed for %s", source["id"])
            results.append({"source_id": source["id"], "error": str(exc)[:200]})

    if include_local:
        results.append(ingest_local_corpus(mode=mode))
    if include_seeds:
        results.append(ingest_knowledge_seeds(mode=mode))

    state = _load_state()
    state["last_global_run"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _save_state(state)

    _refresh_bm25()

    summary = {
        "ok": True,
        "mode": mode,
        "sources_processed": len(results),
        "total_chunks": total_chunks,
        "elapsed_seconds": round(time.time() - started, 2),
        "results": results,
        "state_file": STATE_FILE,
    }
    logger.info("Ingestion complete: %s", summary)
    return summary


def get_ingestion_status() -> dict[str, Any]:
    state = _load_state()
    return {
        "state_file": STATE_FILE,
        "last_global_run": state.get("last_global_run"),
        "sources": state.get("sources", {}),
        "corpus": [s["id"] for s in src.list_sources()],
    }