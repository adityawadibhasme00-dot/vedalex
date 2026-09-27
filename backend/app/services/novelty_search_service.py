"""Live novelty / prior-art search service.

Merges every *real* evidence surface the platform can reach into one
prior-art report for a formulation:

1. Permitted TK prior-art corpus (classical Ayurvedic texts) — indicative of
   Section 3(p) exposure.
2. Local patent/RAG corpus via the hybrid retriever.
3. Optional live PATENTSCOPE gateway (operator-configured; silent when absent).
4. Optional InPASS application status (operator-configured; silent when absent).
5. Browser-ready PATENTSCOPE / TKDL / InPASS search links so an operator can
   complete the authorised search manually.

Nothing is fabricated: when a live surface is unavailable the report marks it
as ``not_searched`` rather than inventing hits.
"""

import json
import logging
import os
from typing import Any, cast

from app.models.passport import InnovationPassport
from app.services import patentscope_client

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge")
_TK_PATH = os.path.join(_KNOWLEDGE_DIR, "permitted_tk_prior_art.json")

def _norm(s):
    return (s or "").strip().lower()


def _load_tk_prior_art() -> list[dict[str, Any]]:
    if not os.path.exists(_TK_PATH):
        return []
    try:
        with open(_TK_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("TK prior-art load failed: %s", exc)
        return []


def _passport_canonical_ids(passport: InnovationPassport) -> list[str]:
    ids = []
    for ing in passport.ingredients:
        cid = getattr(ing, "canonical_id", None)
        if cid and cid not in ids:
            ids.append(cid)
    return ids


def _match_tk_records(
    passport: InnovationPassport, records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    canon = set(_passport_canonical_ids(passport))
    {_norm(i.raw_name) for i in passport.ingredients} | {
        _norm(i.botanical_name) for i in passport.ingredients
    }
    hits: list[dict[str, Any]] = []
    for rec in records:
        rec_ing = set(rec.get("canonical_ingredients") or [])
        shared = rec_ing & canon
        if not shared:
            continue
        coverage = round(len(shared) / len(rec_ing) * 100.0, 1) if rec_ing else 0.0
        hits.append({
            "tk_reference_id": rec.get("tk_reference_id"),
            "source_text": rec.get("source_text"),
            "shared_ingredients": sorted(shared),
            "coverage_pct": coverage,
            "traditional_indication": rec.get("traditional_indication"),
            "traditional_processing": rec.get("traditional_processing"),
            "relevance_under_sec3p": rec.get("relevance_under_sec3p"),
            "source": "permitted-tk-corpus",
        })
    hits.sort(key=lambda h: h["coverage_pct"], reverse=True)
    return hits


def _local_corpus_hits(passport: InnovationPassport, top_k: int = 6) -> list[dict[str, Any]]:
    """Query the local hybrid retriever restricted to patent documents."""
    try:
        from app.rag.retrieval_pipeline import HybridRetriever
        query = " ".join(
            filter(
                None,
                [
                    passport.claimed_innovation,
                    passport.process_description,
                    " ".join(i.raw_name for i in passport.ingredients),
                ],
            )
        ).strip()
        if not query:
            return []
        result = HybridRetriever.retrieve(
            query=query, top_k=top_k, category="patent"
        )
        hits = []
        for src in result.get("sources", []):
            hits.append({
                "patent_id": src.get("patent_number") or src.get("document_id", ""),
                "title": src.get("title", ""),
                "similarity": round(float(src.get("score", 0.0)) * 100.0, 1),
                "jurisdiction": src.get("jurisdiction", ""),
                "publication_date": src.get("publication_year") or src.get("date", ""),
                "source": "local-patent-corpus",
            })
        return hits
    except Exception as exc:
        logger.debug("local prior-art retrieval failed: %s", exc)
        return []


def _ingredient_names(passport: InnovationPassport) -> list[str]:
    names = []
    for ing in passport.ingredients:
        for n in (ing.raw_name, ing.botanical_name):
            if n and n not in names:
                names.append(n)
    return names


def run_novelty_search(
    passport: InnovationPassport,
    include_local_corpus: bool = True,
    live: bool = True,
) -> dict[str, Any]:
    """Produce a prior-art / novelty report for a formulation.

    Args:
        live: when False, skip all network surfaces (used by tests/demo).
    """
    ingredients = _ingredient_names(passport)
    tk_hits = _match_tk_records(passport, _load_tk_prior_art())

    local_hits = _local_corpus_hits(passport) if include_local_corpus else []

    live_hits: list[dict[str, Any]] = []
    surface_status: dict[str, str] = {
        "permitted_tk_corpus": "searched",
        "local_patent_corpus": "searched" if include_local_corpus else "not_searched",
    }

    if live and patentscope_client.gateway_live():
        got = patentscope_client.search_live(
            patentscope_client.build_search_link(ingredients, passport.target_markets)
        )
        if got:
            live_hits = got
            surface_status["patentscope_live"] = "searched"
        else:
            surface_status["patentscope_live"] = "unavailable"
    else:
        surface_status["patentscope_live"] = "not_configured"

    # InPASS application status (guarded)
    inpass_status: dict[str, Any] | None = None
    surface_status["inpass_status"] = "not_configured"
    if live:
        try:
            from app.services.inpass_client import get_application_status
            app_no = getattr(passport, "application_number", None)
            if app_no:
                inpass_status = get_application_status(app_no)
                surface_status["inpass_status"] = (
                    "searched" if inpass_status else "unavailable"
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("InPASS lookup failed: %s", exc)
            surface_status["inpass_status"] = "unavailable"

    all_hits = tk_hits + local_hits + live_hits
    # Overlap signal: strongest hit drives the exposure tier.
    strongest = max(
        [h.get("coverage_pct", 0.0) for h in tk_hits]
        + [h.get("similarity", 0.0) for h in local_hits + live_hits]
        + [0.0]
    )
    if strongest >= 75.0:
        exposure, band = "HIGH_PRIOR_ART_EXPOSURE", "risk"
    elif strongest >= 45.0:
        exposure, band = "MODERATE_PRIOR_ART_EXPOSURE", "warn"
    elif all_hits:
        exposure, band = "LOW_PRIOR_ART_EXPOSURE", "good"
    else:
        exposure, band = "NO_MATCHES_FOUND", "warn"

    search_links = {
        "patentscope": patentscope_client.build_search_link(
            ingredients, passport.target_markets
        ),
        "inpass": patentscope_client.build_inpass_link(
            getattr(passport, "application_number", None)
        ),
        "tkdl": patentscope_client.build_tkdl_link(
            ingredients[0] if ingredients else cast(Any, passport).product_name
        ),
    }

    return {
        "passport_id": passport.id,
        "query": {
            "ingredients": ingredients,
            "target_markets": passport.target_markets,
            "canonical_ingredient_ids": _passport_canonical_ids(passport),
        },
        "exposure_tier": exposure,
        "exposure_band": band,
        "strongest_overlap_pct": round(strongest, 1),
        "hit_count": len(all_hits),
        "hits": {
            "permitted_tk": tk_hits,
            "local_corpus": local_hits,
            "live": live_hits,
        },
        "inpass_application_status": inpass_status,
        "surface_status": surface_status,
        "search_links": search_links,
        "coverage_limitations": (
            "Permitted TK corpus and local patent index are indicative only. "
            "PATENTSCOPE offers no public search API; an authorised search must be "
            "completed via the provided link. This is not a Freedom-to-Operate opinion."
        ),
        "patentscope_availability": patentscope_client.patentscope_status(),
    }