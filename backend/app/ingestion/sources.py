"""
Authoritative corpus registry for IP-SAKTI ingestion.

Implements the master corpus-priority table:
  P0  Traditional Knowledge Digital Library (TKDL), India Code,
      Intellectual Property India (CGPDTM), National Biodiversity Authority (NBA)
  P1  Ministry of AYUSH, WIPO, WHO
  P2  US FDA, Health Canada
  P3  API Monographs / Pharmacopoeia (Indian Pharmacopoeia Commission, AYUSH)

Licensing guardrail: TKDL content is licensed and must not be scraped or
bulk-downloaded. It is treated as authoritative prior-art; it can only be
ingested through authorized integration or metadata pointers plus citations
(``access_mode="restricted"``).
"""

from typing import Any

ACCESS_PUBLIC = "public"
ACCESS_AUTHORIZED = "authorized"
ACCESS_RESTRICTED = "restricted"

CORPUS: list[dict[str, Any]] = [
    {
        "id": "tkdl",
        "name": "Traditional Knowledge Digital Library (TKDL)",
        "priority": "P0",
        "jurisdiction": "India",
        "authority": "CSIR-TKDL / Ministry of AYUSH",
        "authority_level": 2,
        "document_type": "traditional_knowledge",
        "category": "tkdl",
        "access_mode": ACCESS_RESTRICTED,
        "schedule": "weekly",
        "domain": "tkdl.res.in",
        "canonical_urls": ["https://tkdl.res.in/tkdl/langdefault/common/Home.asp"],
        "pointer_urls": ["https://tkdl.res.in/tkdl/langdefault/common/About%20TKDL.asp"],
        "search_terms": [],
        "licensing_note": "TKDL is licensed — authorizations required. Authorized pointers and citations only; no scrape or bulk download.",
    },
    {
        "id": "india_code",
        "name": "India Code (eCourtsIndia / Legislative Department)",
        "priority": "P0",
        "jurisdiction": "India",
        "authority": "Legislative Department, Government of India",
        "authority_level": 1,
        "document_type": "regulations",
        "category": "regulatory",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "daily",
        "domain": "indiacode.ecourtsindia.com",
        "canonical_urls": [
            "https://indiacode.ecourtsindia.com/llms.txt",
            "https://indiacode.ecourtsindia.com/patents-act/",
        ],
        "api_base": "https://indiacode.ecourtsindia.com/api/v1",
        "pointer_urls": [
            "https://www.indiacode.nic.in/",
            "https://www.indiacode.nic.in/handle/123456789/1366",
        ],
        "search_terms": ["patents act 1970 section 3 subsection p", "biological diversity act 2002 section 6", "trade marks act section 9"],
        "licensing_note": "IndiaCode publishes statutory text under s.52(1)(q)(ii) Copyright Act 1957; keyless API, open CORS.",
    },
    {
        "id": "ip_india_status",
        "name": "IP India — InPASS Application Status (via Parse.bot)",
        "priority": "P1",
        "jurisdiction": "India",
        "authority": "Office of the Controller General of Patents, Designs & TM",
        "authority_level": 1,
        "document_type": "status_api",
        "category": "patent",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "on_demand",
        "domain": "iprsearch.ipindia.gov.in",
        "canonical_urls": ["https://iprsearch.ipindia.gov.in/PublicSearch/"],
        "api_wrapper": "https://parse.bot/marketplace/1cd78895-70f4-4672-b429-0ce8cb939d89",
        "pointer_urls": [],
        "search_terms": ["patent application status", "get_application_status"],
        "licensing_note": "Dynamic search app — do not bulk scrape; query application status on demand via the API wrapper only.",
    },
    {
        "id": "patentscope",
        "name": "WIPO PATENTSCOPE (International + PCT)",
        "priority": "P1",
        "jurisdiction": "International",
        "authority": "World Intellectual Property Organization",
        "authority_level": 2,
        "document_type": "patents",
        "category": "patent",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "on_demand",
        "domain": "patentscope.wipo.int",
        "canonical_urls": ["https://patentscope.wipo.int/"],
        "api_base": "https://patentscope.wipo.int/api",
        "pointer_urls": ["https://apicatalog.wipo.int/"],
        "search_terms": ["patentscope prior art search by titania", "wipo patent search api"],
        "licensing_note": "PATENTSCOPE API requires a WIPO/OpenAPI account + key for programmatic search; search surface is free for interactive use.",
    },
    {
        "id": "ip_india",
        "name": "Intellectual Property India (CGPDTM)",
        "priority": "P0",
        "jurisdiction": "India",
        "authority": "Office of the Controller General of Patents, Designs & TM",
        "authority_level": 1,
        "document_type": "patents",
        "category": "patent",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "daily",
        "domain": "ipindia.gov.in",
        "canonical_urls": ["https://ipindia.gov.in/"],
        "pointer_urls": [],
        "search_terms": ["patents act filing", "patent application status", "guidelines of working of patents"],
        "licensing_note": "",
    },
    {
        "id": "nba",
        "name": "National Biodiversity Authority (NBA)",
        "priority": "P0",
        "jurisdiction": "India",
        "authority": "National Biodiversity Authority of India",
        "authority_level": 2,
        "document_type": "biodiversity",
        "category": "regulatory",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "daily",
        "domain": "nbaindia.org",
        "canonical_urls": ["https://nbaindia.org/"],
        "pointer_urls": [],
        "search_terms": ["access and benefit sharing", "biological diversity act 2002", "abs guidelines"],
        "licensing_note": "",
    },
    {
        "id": "ayush",
        "name": "Ministry of AYUSH",
        "priority": "P1",
        "jurisdiction": "India",
        "authority": "Ministry of AYUSH, Government of India",
        "authority_level": 2,
        "document_type": "regulations",
        "category": "regulatory",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "weekly",
        "domain": "ayush.gov.in",
        "canonical_urls": ["https://ayush.gov.in/"],
        "pointer_urls": [],
        "search_terms": ["ayurveda guidelines", "ayurvedic pharmacopoeia", "national ayush mission"],
        "licensing_note": "",
    },
    {
        "id": "wipo",
        "name": "World Intellectual Property Organization (WIPO)",
        "priority": "P1",
        "jurisdiction": "International",
        "authority": "World Intellectual Property Organization",
        "authority_level": 3,
        "document_type": "patents",
        "category": "who",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "weekly",
        "domain": "wipo.int",
        "canonical_urls": ["https://www.wipo.int/"],
        "pointer_urls": [],
        "search_terms": ["traditional knowledge intellectual property", "patentscope", "wipo ik tkgrl"],
        "licensing_note": "",
    },
    {
        "id": "who",
        "name": "World Health Organization (WHO)",
        "priority": "P1",
        "jurisdiction": "International",
        "authority": "World Health Organization",
        "authority_level": 3,
        "document_type": "safety",
        "category": "who",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "weekly",
        "domain": "who.int",
        "canonical_urls": ["https://www.who.int/health-topics/traditional-complementary-and-integrative-medicine"],
        "pointer_urls": [],
        "search_terms": ["who traditional medicine strategy", "who safety guidelines herbal"],
        "licensing_note": "",
    },
    {
        "id": "fda_us",
        "name": "US Food and Drug Administration (FDA)",
        "priority": "P2",
        "jurisdiction": "United States",
        "authority": "US Food and Drug Administration",
        "authority_level": 2,
        "document_type": "safety",
        "category": "regulatory",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "weekly",
        "domain": "fda.gov",
        "canonical_urls": ["https://www.fda.gov/food/dietary-supplements"],
        "pointer_urls": [],
        "search_terms": ["dietary supplements dshea", "botanical drug development", "new dietary ingredient"],
        "licensing_note": "",
    },
    {
        "id": "health_canada",
        "name": "Health Canada",
        "priority": "P2",
        "jurisdiction": "Canada",
        "authority": "Health Canada, Government of Canada",
        "authority_level": 2,
        "document_type": "safety",
        "category": "regulatory",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "weekly",
        "domain": "canada.ca",
        "canonical_urls": [
            "https://www.canada.ca/en/health-canada/services/drugs-health-products/natural-non-prescription/regulation.html",
            "https://www.canada.ca/en/health-canada/services/drugs-health-products/natural-non-prescription.html",
        ],
        "pointer_urls": [],
        "search_terms": ["natural health products regulations", "nhp licence canada", "health canada natural health products"],
        "licensing_note": "",
    },
    {
        "id": "apharmacopoeia",
        "name": "API Monographs / Pharmacopoeia (AYUSH & IPC)",
        "priority": "P3",
        "jurisdiction": "India",
        "authority": "AYUSH Pharmacopoeia Commission / Indian Pharmacopoeia Commission",
        "authority_level": 2,
        "document_type": "quality_standards",
        "category": "pharmacopoeia",
        "access_mode": ACCESS_PUBLIC,
        "schedule": "monthly",
        "domain": "ayush.gov.in",
        "canonical_urls": ["https://ayush.gov.in/", "https://ipc.gov.in/"],
        "pointer_urls": [],
        "search_terms": ["ayurvedic pharmacopoeia of india", "api monograph ashwagandha"],
        "licensing_note": "Pharmacopoeia content is copyrighted; ingest reference/monograph summaries and cite official pages.",
    },
]

CORPUS_BY_ID: dict[str, dict[str, Any]] = {s["id"]: s for s in CORPUS}

PRIORITY_ORDER: list[str] = ["P0", "P1", "P2", "P3"]

SCHEDULE_MAP: dict[str, list[str]] = {
    "daily": [s["id"] for s in CORPUS if s.get("schedule") == "daily"],
    "weekly": [s["id"] for s in CORPUS if s.get("schedule") == "weekly"],
    "monthly": [s["id"] for s in CORPUS if s.get("schedule") == "monthly"],
}


def list_sources(priority: str = "") -> list[dict[str, Any]]:
    """Return the corpus registry, optionally filtered by priority (P0..P3)."""
    sources = sorted(CORPUS, key=lambda s: PRIORITY_ORDER.index(s["priority"]))
    if priority:
        sources = [s for s in sources if s["priority"] == priority.upper()]
    return sources


def resolve_source_ids(ids: list[str]) -> list[dict[str, Any]]:
    """Resolve user-supplied source ids (or magic selectors) to source dicts."""
    out: list[dict[str, Any]] = []
    for raw in ids or []:
        key = raw.strip().lower()
        if key == "p0":
            out.extend(list_sources("P0"))
        elif key == "p1":
            out.extend(list_sources("P1"))
        elif key == "p2":
            out.extend(list_sources("P2"))
        elif key == "p3":
            out.extend(list_sources("P3"))
        elif key == "all":
            out.extend(list_sources())
        elif key == "daily":
            out.extend(CORPUS_BY_ID[s] for s in SCHEDULE_MAP["daily"])
        elif key == "weekly":
            out.extend(CORPUS_BY_ID[s] for s in SCHEDULE_MAP["weekly"])
        elif key == "monthly":
            out.extend(CORPUS_BY_ID[s] for s in SCHEDULE_MAP["monthly"])
        else:
            src = CORPUS_BY_ID.get(key)
            if src:
                out.append(src)
    return out