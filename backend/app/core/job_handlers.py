"""Registered background job handlers.

Kept separate from :mod:`app.core.jobs` so the queue module has no dependency on
the service layer (and can be imported by a standalone worker without pulling in
the whole application).

Import this module for its side effect of registering handlers::

    from app.core import job_handlers  # noqa: F401
    from app.core.jobs import submit
    job = submit("corpus_reindex")
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.jobs import register

logger = logging.getLogger(__name__)


@register("corpus_reindex")
def corpus_reindex(payload: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the retrieval index. Minutes-long, so it must not hold a worker."""
    from app.rag.retrieval_pipeline import HybridRetriever

    return HybridRetriever.reindex_all()


@register("indiacode_harvest")
def indiacode_harvest(payload: dict[str, Any]) -> dict[str, Any]:
    """Fetch + embed + upsert India Code statute sections."""
    from app.services.indiacode_harvester import harvest_indiacode

    return harvest_indiacode(
        act_ids=payload.get("act_ids"),
        force=bool(payload.get("force")),
    )


@register("patent_corpus_harvest")
def patent_corpus_harvest(payload: dict[str, Any]) -> dict[str, Any]:
    """Fetch + embed + upsert curated patent / TK / regulation documents."""
    from app.services.corpus_harvester import harvest_documents

    return harvest_documents(
        target=payload.get("target"),
        limit_per_doc=payload.get("limit_per_doc"),
        force=bool(payload.get("force")),
    )


@register("law_sentinel_run")
def law_sentinel_run(payload: dict[str, Any]) -> dict[str, Any]:
    """Poll the statutory sources and flag anything whose content hash moved.

    Runs under the same single-writer lock as ingestion: the whole point of the
    sentinel is to notice amended clauses, and N replicas polling the same
    government pages is how the deployment gets blocked from noticing anything.
    """
    from app.core.database import SessionLocal
    from app.core.lock import single_writer
    from app.services.law_sentinel import run_sentinel

    with single_writer("law_sentinel", ttl=600) as held:
        if not held:
            return {"ok": False, "skipped": "another replica holds the lock"}
        db = SessionLocal()
        try:
            return run_sentinel(db, source_ids=payload.get("source_ids"))
        finally:
            db.close()


@register("ingestion_cycle")
def ingestion_cycle(payload: dict[str, Any]) -> dict[str, Any]:
    """Run one ingestion cycle now, under the single-writer lock."""
    from app.services import ingestion_scheduler as sched

    with sched.single_writer("ingestion", ttl=sched._ingest_lock_ttl()) as held:
        if not held:
            return {"ok": False, "skipped": "another replica holds the lock"}
        due = sched._due_sources()
        results = [sched._ingest_source_guarded(sid) for sid in due]
        return {
            "ok": True,
            "due": due,
            "ok_sources": [r["source_id"] for r in results if r.get("ok")],
            "failed_sources": [r["source_id"] for r in results if not r.get("ok")],
            "results": results,
        }


@register("dossier_export")
def dossier_export(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a dossier (and optionally render markdown/PDF) off the request path."""
    from app.services.dossier_service import build_dossier

    passport_id = str(payload["passport_id"])
    dossier = build_dossier(
        passport_id,
        top_k=int(payload.get("top_k") or 4),
        watch_alerts=payload.get("watch_alerts"),
    )
    fmt = str(payload.get("format") or "json")
    if fmt == "markdown":
        from app.services.dossier_service import render_markdown

        return {"format": "markdown", "passport_id": passport_id,
                "content": render_markdown(dossier)}
    if fmt == "pdf":
        from app.services.dossier_service import render_pdf

        pdf_bytes = render_pdf(dossier)
        return {
            "format": "pdf",
            "passport_id": passport_id,
            "bytes": len(pdf_bytes),
            # Persist next to the other exports so the caller can download it.
            "path": _write_pdf(passport_id, pdf_bytes),
        }
    return {"format": "json", "passport_id": passport_id, "dossier": dossier}


def _write_pdf(passport_id: str, pdf_bytes: bytes) -> str:
    import os

    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "exports",
    )
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{passport_id}_dossier.pdf")
    with open(path, "wb") as handle:
        handle.write(pdf_bytes)
    return path
