"""PATENTSCOPE prior-art search adapter (guarded).

WIPO ships NO public REST/JSON search API for PATENTSCOPE (verified 2026:
the only programmatic surface is a fee-based SOAP/Java batch product, and the
JSF web UI forbids automated queries). So this adapter:

1. Builds verified, browser-ready PATENTSCOPE advanced-search links for a
   formulation so an operator can run the real search in one click.
2. Optionally queries a configured enterprise gateway (e.g. an operator's
   authorized PATENTSCOPE connector) at ``IPSAKTI_PATENTSCOPE_GATEWAY_URL``.
   Unset or failing gateway → silent None, never a hard error.

Field syntax (from PATENTSCOPE help): EN_TI title, EN_AB abstract, EN_CLMS
claims, PA applicant, IC IPC, DP:[A TO B] date range, CQL booleans AND/OR/NOT.
"""

import logging
import os
import re
from typing import Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

ADVANCED_SEARCH_URL = "https://patentscope.wipo.int/search/en/advancedSearch.jsf"
GATEWAY_URL = os.environ.get("IPSAKTI_PATENTSCOPE_GATEWAY_URL", "")
TIMEOUT = float(os.environ.get("IPSAKTI_PATENTSCOPE_TIMEOUT", "15"))


def _cql_terms(terms: list[str]) -> str:
    cleaned = [re.sub(r"[^A-Za-z0-9 ]", " ", t).strip() for t in terms]
    cleaned = [t for t in cleaned if t]
    if not cleaned:
        return ""
    parts = " ".join(f'"{t}"' for t in cleaned[:4])
    return f"EN_AB:({parts}) OR EN_CLMS:({parts})"


def build_search_link(ingredients: list[str], target_markets: list[str] | None = None) -> str:
    """Authoritative PATENTSCOPE advanced-search URL for a formulation."""
    query = _cql_terms(ingredients)
    tab = "PCTBiblio"
    params = f"tab={tab}&query={quote(query)}"
    if target_markets:
        codes = ",".join(target_markets)
        params += f"&cntry={quote(codes)}"
    return f"{ADVANCED_SEARCH_URL}?{params}"


def build_inpass_link(application_number: str | None = None) -> str:
    """InPASS (IP India) public search link — status/records are human-search only."""
    base = "https://iprsearch.ipindia.gov.in/PublicSearch/"
    if application_number:
        return f"{base}?searchtype=applicationNumber&q={quote(application_number)}"
    return base


def build_tkdl_link(keyword: str) -> str:
    """Traditional Knowledge Digital Library public search link."""
    return f"https://tkdl.res.in/tkdl/langdefault/common/Search.asp?gl=EN&q={quote(keyword)}"


def gateway_live() -> bool:
    return bool(GATEWAY_URL)


def search_live(
    query: str,
    limit: int = 10,
    timeout: float = TIMEOUT,
) -> list[dict[str, Any]] | None:
    """Search through a configured enterprise gateway; None when unavailable.

    The gateway contract mirrors what authorized PATENTSCOPE connectors
    return: a list of {publication_number, publication_date, title,
    applicants, abstract, pdf_url}. Any provider that returns records in this
    shape can be pointed at via IPSAKTI_PATENTSCOPE_GATEWAY_URL.
    """
    if not gateway_live():
        return None
    try:
        import requests
        resp = requests.post(
            GATEWAY_URL,
            json={"query": query, "limit": limit, "kind": "prior_art"},
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.debug("PATENTSCOPE gateway failed: %s", exc)
        return None

    records = payload.get("records") or payload.get("results") or []
    if not isinstance(records, list):
        return None
    out = []
    for rec in records[:limit]:
        if not isinstance(rec, dict):
            continue
        out.append({
            "patent_id": rec.get("publication_number") or rec.get("patent_id", ""),
            "title": rec.get("title", ""),
            "similarity": float(rec.get("score") or rec.get("similarity") or 50.0),
            "jurisdiction": rec.get("jurisdiction", "International"),
            "publication_date": rec.get("publication_date", ""),
            "applicant": rec.get("applicants") or rec.get("applicant", ""),
            "source": "patentscope-live",
        })
    return out


def patentscope_status() -> dict[str, Any]:
    return {
        "public_api": False,
        "note": "WIPO has no public REST/JSON PATENTSCOPE search API (fee-based SOAP batch only). Browser links + optional configured gateway are used.",
        "gateway_configured": gateway_live(),
        "advanced_search_url": ADVANCED_SEARCH_URL,
    }