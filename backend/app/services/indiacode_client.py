"""India Code API client (eCourtsIndia) — statute-law-as-data ingestion.

Talks to the keyless, open-CORS IndiaCode API (indiacode.ecourtsindia.com) and
returns section texts in the IP-SAKTI extraction schema so statute law can be
indexed verbatim with precise locators (act id, section number, chapter).

Endpoint contract (verified live, OpenAPI 3.1 at /api/v1/openapi.json):

* GET /api/v1/acts?q=...&year=...        resolve a title to a stable act id
* GET /api/v1/acts/{act}                 one Act + its section list
* GET /api/v1/{act}/section/{number}     one section (JSON) — text + judgements
* GET /api/v1/{act}/section/{number}.md  same section as Markdown
* GET /api/v1/search?q=...&kind=...      citation / meaning search
* GET /api/v1/instruments?act=&section=  subordinate legislation resting on a section
* GET /api/v1/judgments?act=&section=    reported judgments on a provision

Section numbers are strings (e.g. "3(p)", "124A", "331(4)").

Every failure degrades silently (returns None) so ingestion never crashes on a
flaky endpoint.
"""

import hashlib
import logging
import os
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

BASE_URL = os.environ.get(
    "IPSAKTI_INDIA_CODE_API",
    "https://indiacode.ecourtsindia.com",
)
API_BASE = f"{BASE_URL}/api/v1"

# The corpus-relevant Central Acts this copilot actually answers with. IDs are
# the stable short forms used by IndiaCode. Section lists drive targeted ingest.
INDIA_CODE_ACTS: list[dict[str, Any]] = [
    {
        "id": "patents-act",
        "act_name": "patents_act_1970",
        "title": "The Patents Act, 1970",
        "short_title": "Patents Act",
        "priority_sections": ["3", "10", "25", "43", "53", "84"],
        "document_type": "statute",
        "jurisdiction": "India",
        "authority": "Legislative Department, Ministry of Law and Justice",
    },
    {
        "id": "biological-diversity-act-2002",
        "act_name": "biological_diversity_act_2002",
        "title": "The Biological Diversity Act, 2002",
        "short_title": "Biological Diversity Act",
        "priority_sections": ["6", "3"],
        "document_type": "statute",
        "jurisdiction": "India",
        "authority": "Legislative Department, Ministry of Law and Justice",
    },
    {
        "id": "trade-marks-act",
        "act_name": "trade_marks_act_1999",
        "title": "The Trade Marks Act, 1999",
        "short_title": "Trade Marks Act",
        "priority_sections": ["2", "9", "23"],
        "document_type": "statute",
        "jurisdiction": "India",
        "authority": "Legislative Department, Ministry of Law and Justice",
    },
    {
        "id": "copyright-act",
        "act_name": "copyright_act_1957",
        "title": "The Copyright Act, 1957",
        "short_title": "Copyright Act",
        "priority_sections": ["13", "44"],
        "document_type": "statute",
        "jurisdiction": "India",
        "authority": "Legislative Department, Ministry of Law and Justice",
    },
    {
        "id": "designs-act-2000",
        "act_name": "designs_act_2000",
        "title": "The Designs Act, 2000",
        "short_title": "Designs Act",
        "priority_sections": ["2", "5"],
        "document_type": "statute",
        "jurisdiction": "India",
        "authority": "Legislative Department, Ministry of Law and Justice",
    },
    {
        "id": "geographical-indications-goods-registration-protection-act-1999",
        "act_name": "geographical_indications_act_1999",
        "title": "The Geographical Indications of Goods (Registration and Protection) Act, 1999",
        "short_title": "Geographical Indications Act",
        "priority_sections": ["2", "8"],
        "document_type": "statute",
        "jurisdiction": "India",
        "authority": "Legislative Department, Ministry of Law and Justice",
    },
    {
        "id": "drugs-cosmetics-act-1940",
        "act_name": "drugs_and_cosmetics_act_1940",
        "title": "The Drugs and Cosmetics Act, 1940",
        "short_title": "Drugs and Cosmetics Act",
        "priority_sections": ["16", "17"],
        "document_type": "statute",
        "jurisdiction": "India",
        "authority": "Legislative Department, Ministry of Law and Justice",
    },
    {
        "id": "protection-plant-varieties-farmers-rights-act-2001",
        "act_name": "plant_varieties_farmers_rights_act_2001",
        "title": "The Protection of Plant Varieties and Farmers' Rights Act, 2001",
        "short_title": "PPV&FR Act",
        "priority_sections": ["2", "13"],
        "document_type": "statute",
        "jurisdiction": "India",
        "authority": "Legislative Department, Ministry of Law and Justice",
    },
]


def _http_get(url: str, timeout: float = 15.0) -> dict[str, Any] | None:
    try:
        import requests
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "IP-SAKTI Sahayak Ingestion"})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("India Code GET failed %s: %s", url, exc)
        return None


def resolve_act(
    title_query: str,
    year: int | None = None,
    act_id: str | None = None,
) -> dict[str, Any] | None:
    """Resolve an Act title to its stable IndiaCode id + metadata.

    ``act_id`` short-circuits to /api/v1/acts/{id}. Otherwise ``q=`` resolves
    the title the same way IndiaCode itself does.
    """
    if act_id:
        return _http_get(f"{API_BASE}/acts/{act_id}")
    url = f"{API_BASE}/acts?q={_quote(title_query)}"
    if year:
        url += f"&year={year}"
    payload = _http_get(url)
    if not payload:
        return None
    acts = payload.get("acts") or []
    return acts[0] if acts else None


def fetch_act(act_id: str) -> dict[str, Any] | None:
    """One Act record + its full section list."""
    return _http_get(f"{API_BASE}/acts/{_quote(act_id)}")


def fetch_section(act_id: str, section: str) -> dict[str, Any] | None:
    """One section as JSON (text, heading, instruments, judgments)."""
    return _http_get(f"{API_BASE}/{_quote(act_id)}/section/{_quote(section)}")


def search_statute(query: str, kind: str = "section", limit: int = 5) -> list[dict[str, Any]]:
    """Search the statute book by citation or by meaning."""
    payload = _http_get(
        f"{API_BASE}/search?q={_quote(query)}&kind={_quote(kind)}&limit={limit}"
    )
    if not payload:
        return []
    return list(payload.get("results") or payload.get("sections") or [])


def fetch_instruments(act_id: str, section: str | None = None) -> list[dict[str, Any]]:
    """Subordinate legislation resting on an Act (optionally a specific section)."""
    url = f"{API_BASE}/instruments?act={_quote(act_id)}"
    if section:
        url += f"&section={_quote(section)}"
    payload = _http_get(url)
    if not payload:
        return []
    return list(payload.get("instruments") or [])


def fetch_judgments(act_id: str, section: str | None = None) -> list[dict[str, Any]]:
    """Reported judgments attached to a provision."""
    url = f"{API_BASE}/judgments?act={_quote(act_id)}"
    if section:
        url += f"&section={_quote(section)}"
    payload = _http_get(url)
    if not payload:
        return []
    return list(payload.get("judgments") or [])


def statute_document(
    act: dict[str, Any],
    section_response: dict[str, Any],
    section: str,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Shape an API section response into the IP-SAKTI extraction schema.

    Mirrors the JSON contract in the master prompt:
    document_id / source / document_type / title / authority / jurisdiction /
    effective_from / version / language / text / locator / source_url /
    retrieved_at / checksum / topics / review_status.
    """
    act_meta = section_response.get("act") or act
    section_data = section_response.get("section") or {}
    text = section_data.get("text") or ""
    heading = section_data.get("heading") or ""
    number = str(section_data.get("number") or section)

    canonical = "".join(ch for ch in number if ch.isalnum()).lower()
    doc_id = f"{act_meta.get('id', act.get('id', 'act'))}_section_{canonical}"
    source_url = f"{BASE_URL}/{act_meta.get('id', '')}/section/{number}/"

    return {
        "document_id": doc_id,
        "source": "india_code",
        "document_type": "statute",
        "title": f"{act_meta.get('short_title', act.get('title', ''))} — Section {number}",
        "authority": act.get("authority", "Legislative Department, Government of India"),
        "jurisdiction": act.get("jurisdiction", "India"),
        "effective_from": "",
        "effective_to": None,
        "version": "current",
        "language": "en",
        "text": text,
        "locator": {
            "act_name": act.get("act_name") or act_meta.get("id", ""),
            "act_id": act_meta.get("id", ""),
            "section": number,
            "section_heading": heading,
        },
        "source_url": source_url,
        "retrieved_at": retrieved_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checksum": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "topics": ["patent", "traditional_knowledge", "regulatory"],
        "review_status": "auto_ingested",
    }


def harvest_sections_for_act(
    act: dict[str, Any],
    sections: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch the requested sections of an Act as extraction-schema documents.

    An IndiaCode act id is resolved first (so act metadata is authoritative),
    then each section is fetched and shaped. Sections that fail silently are
    skipped — callers see which ones returned via ``retrieved`` in their result.
    """
    act_meta = resolve_act(act.get("title", ""), act_id=act.get("id"))
    if not act_meta:
        logger.warning("India Code act unresolvable: %s", act.get("id"))
        return []

    targets = sections or act.get("priority_sections") or []
    docs: list[dict[str, Any]] = []
    for section in targets:
        resp = fetch_section(act_meta.get("id", act["id"]), section)
        if not resp or not (resp.get("section") or {}).get("text"):
            logger.debug("Section %s of %s not returned", section, act.get("id"))
            continue
        docs.append(statute_document(act, resp, section))
    return docs


def india_code_status() -> dict[str, Any]:
    meta = _http_get(f"{API_BASE}/meta")
    return {
        "enabled": True,
        "base_url": BASE_URL,
        "api_responsive": bool(meta),
        "corpus_counts": meta if meta else None,
        "tracked_acts": [a["id"] for a in INDIA_CODE_ACTS],
    }


def _quote(value: Any) -> str:
    from urllib.parse import quote
    return quote(str(value).strip(), safe="")


def _heading_text(heading: str) -> str:
    return re.sub(r"\s+", " ", heading or "").strip()