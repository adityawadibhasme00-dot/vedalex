"""
Official-Website Retriever for VEDALEX | IP-SAKTI SAHAYAK.

Augments the local knowledge base with content fetched LIVE from official
government and intergovernmental sources (IP India, TKDL, WIPO, Ministry of
AYUSH, FSSAI, CDSCO, NBA, WHO, FDA, ...).

This addresses a core judge question — "where does the evidence come from?" —
because every fetched chunk carries full provenance metadata (source URL,
authority, jurisdiction, authority_level) that flows straight into the
verification layer as a citable, real web source.

Design rules:
  - Whitelisted: only official domains in OFFICIAL_SOURCES are ever fetched.
  - Network-guarded: never raises; returns [] when offline/blocked.
  - Cached: per-URL in-memory TTL cache (default 6h) so official sites are
    not hammered by repeated queries.
  - Time-boxed: short HTTP timeouts and a per-query fetch budget.
  - Offline toggle: IPSAKTI_LIVE_WEB=0 disables all network I/O so the
    demo still works with the local KB alone.
"""

import hashlib
import logging
import os
import re
from html import unescape
from typing import Any
from urllib.parse import quote, unquote, urlparse

from app.core.cache import get_cache

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 IP-SAKTI ResearchBot"
)

HTTP_TIMEOUT_SEC = float(os.environ.get("IPSAKTI_WEB_TIMEOUT", "8"))
CACHE_TTL_SEC = float(os.environ.get("IPSAKTI_WEB_CACHE_TTL", "21600"))  # 6h
MAX_FETCHES_PER_QUERY = int(os.environ.get("IPSAKTI_WEB_MAX_FETCHES", "3"))
DEFAULT_MAX_FETCH_PAGES = int(os.environ.get("IPSAKTI_WEB_MAX_PAGES", "2"))

# Canonical official sources the bot is allowed to read.
# domain    — hostname suffix used in the whitelist check
# keywords  — query signals used to select the right authority for a question
# authority — displayed issuing authority (feeds citation metadata)
OFFICIAL_SOURCES: list[dict[str, Any]] = [
    {
        "name": "Section 3 — Indian Patents Act (India Code)",
        "domain": "indiacode.nic.in",
        "keywords": ["patents act", "section 3", "3(p)", "3(d)", "patent"],
        "authority": "Legislative Department, Government of India (India Code)",
        "jurisdiction": "India",
        "authority_level": 1,
        "category": "official",
        "canonical_url": "https://www.indiacode.nic.in/",
        "search_terms": ["patents act 1970 full text"],
    },
    {
        "name": "Intellectual Property India (CGPDTM)",
        "domain": "ipindia.gov.in",
        "keywords": ["ip india", "patent office", "cgpdtm", "filing", "patent application", "trademark"],
        "authority": "Office of the Controller General of Patents, Designs & TM (CGPDTM)",
        "jurisdiction": "India",
        "authority_level": 1,
        "category": "official",
        "canonical_url": "https://ipindia.gov.in/",
        "search_terms": ["patents act filing", "guidelines examiner"],
    },
    {
        "name": "Ministry of AYUSH",
        "domain": "ayush.gov.in",
        "keywords": ["ayush", "ayurveda", "ayurvedic", "ministry of ayush", "nccih", "research council"],
        "authority": "Ministry of AYUSH, Government of India",
        "jurisdiction": "India",
        "authority_level": 2,
        "category": "official",
        "canonical_url": "https://ayush.gov.in/",
        "search_terms": ["ayurveda guidelines", "drugs and cosmetics act"],
    },
    {
        "name": "Traditional Knowledge Digital Library (TKDL)",
        "domain": "tkdl.res.in",
        "keywords": ["tkdl", "traditional knowledge", "prior art", "traditional medicine"],
        "authority": "CSIR-TKDL / Ministry of AYUSH",
        "jurisdiction": "India",
        "authority_level": 2,
        "category": "official",
        "canonical_url": "https://tkdl.res.in/tkdl/langdefault/common/Home.asp",
        "search_terms": ["traditional knowledge digital library patents", "prior art"],
    },
    {
        "name": "WIPO",
        "domain": "wipo.int",
        "keywords": ["wipo", "patentscope", "pct", "madrid", "intergovernmental", "international ip"],
        "authority": "World Intellectual Property Organization (WIPO)",
        "jurisdiction": "International",
        "authority_level": 3,
        "category": "official",
        "canonical_url": "https://www.wipo.int/",
        "search_terms": ["traditional knowledge ip", "patentscope search"],
    },
    {
        "name": "FSSAI",
        "domain": "fssai.gov.in",
        "keywords": ["fssai", "food safety", "ayurveda aahara", "food standards", "nutraceutical"],
        "authority": "Food Safety and Standards Authority of India (FSSAI)",
        "jurisdiction": "India",
        "authority_level": 2,
        "category": "official",
        "canonical_url": "https://www.fssai.gov.in/",
        "search_terms": ["ayurveda aahara regulation", "health claims food"],
    },
    {
        "name": "CDSCO",
        "domain": "cdsco.gov.in",
        "keywords": ["cdsco", "central drugs", "drug controller", "asyu", "schedule t", "drugs and cosmetics"],
        "authority": "Central Drugs Standard Control Organisation (CDSCO)",
        "jurisdiction": "India",
        "authority_level": 2,
        "category": "official",
        "canonical_url": "https://cdsco.gov.in/",
        "search_terms": ["ayurvedic drugs schedule t", "drugs and cosmetics act"],
    },
    {
        "name": "National Biodiversity Authority (NBA)",
        "domain": "nbaindia.org",
        "keywords": ["nba", "biodiversity", "access and benefit sharing", "abs", "biological resources"],
        "authority": "National Biodiversity Authority of India (NBA)",
        "jurisdiction": "India",
        "authority_level": 2,
        "category": "official",
        "canonical_url": "https://nbaindia.org/",
        "search_terms": ["access benefit sharing biological resources", "abs application"],
    },
    {
        "name": "Press Information Bureau (PIB)",
        "domain": "pib.gov.in",
        "keywords": ["press release", "government", "policy", "notification", "section 3"],
        "authority": "Press Information Bureau, Government of India",
        "jurisdiction": "India",
        "authority_level": 2,
        "category": "official",
        "canonical_url": "https://pib.gov.in/",
        "search_terms": ["patents act amendment", "ayush"],
    },
    {
        "name": "US FDA",
        "domain": "fda.gov",
        "keywords": ["fda", "dietary supplement", "dshea", "nda", "united states", "ius"],
        "authority": "US Food and Drug Administration (FDA)",
        "jurisdiction": "United States",
        "authority_level": 2,
        "category": "official",
        "canonical_url": "https://www.fda.gov/",
        "search_terms": ["dietary supplements dshea", "herbal products regulation"],
    },
    {
        "name": "Health Canada",
        "domain": "canada.ca",
        "keywords": ["health canada", "nhp", "natural health product", " canada", "canadian"],
        "authority": "Health Canada, Government of Canada",
        "jurisdiction": "Canada",
        "authority_level": 2,
        "category": "official",
        "canonical_url": "https://www.canada.ca/en/health-canada/services/drugs-health-products/natural-non-prescription/regulation.html",
        "search_terms": ["natural health products regulations", "nhp licence canada"],
    },
    {
        "name": "World Health Organization (WHO)",
        "domain": "who.int",
        "keywords": ["who", "world health", "traditional medicine", "global", "international"],
        "authority": "World Health Organization (WHO)",
        "jurisdiction": "International",
        "authority_level": 3,
        "category": "official",
        "canonical_url": "https://www.who.int/",
        "search_terms": ["traditional medicine strategy", "ayurveda"],
    },
]


# ---------------------------------------------------------------------------
# TTL cache (Redis-shared, in-memory fallback)
# ---------------------------------------------------------------------------
# Named `_cache` as well as `_page_cache`: tests (and callers that want to
# force a cold fetch) clear this object directly, and the two names are the same
# SharedCache instance, so clearing one clears both.
_page_cache = get_cache("official_web", default_ttl=CACHE_TTL_SEC,
                        max_memory_entries=256)
_cache = _page_cache


def _cache_get(key: str) -> str | None:
    value = _page_cache.get(key)
    return value if isinstance(value, str) else None


def _cache_set(key: str, value: str) -> str:
    _page_cache.set(key, value)
    return value


def _live_web_enabled() -> bool:
    return os.environ.get("IPSAKTI_LIVE_WEB", "1").strip().lower() not in (
        "0", "false", "off", "no",
    )


# ---------------------------------------------------------------------------
# HTTP helpers (guarded)
# ---------------------------------------------------------------------------

def _fetch_url(url: str, timeout: float = HTTP_TIMEOUT_SEC) -> str | None:
    cached = _cache_get(url)
    if cached is not None:
        return cached

    import httpx
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = client.get(url)
            if resp.status_code >= 400:
                return None
            text = resp.text
    except Exception as e:
        logger.debug(f"Fetch failed for {url}: {e}")
        return None

    _cache_set(url, text)
    return text


def _html_to_text(html: str) -> tuple[str, str]:
    """Return (title, cleaned_text) from raw HTML."""
    title = "Official Source"
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        title = re.sub(r"<[^>]+>", " ", m.group(1)).strip() or title

    text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<(?:br|p|div|li|h[1-6]|tr|td|section|article)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"\s+", " ", text).strip()
    return title, text


def _chunk_web_text(text: str, size: int = 450, overlap: int = 70) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    step = size - overlap
    seen = set()
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + size]).strip()
        if not chunk or chunk in seen:
            continue
        seen.add(chunk)
        chunks.append(chunk)
    return chunks


# ---------------------------------------------------------------------------
# Search (DuckDuckGo HTML, no API key) filtered to official domains
# ---------------------------------------------------------------------------

def _decode_bing_target(url: str) -> str:
    """Decode a Bing ``/ck/a?...u=<base64url>`` redirect back to the real URL.

    Real Bing results prefix the payload with an ``a1`` scheme marker
    (``u=a1aHR0cHM6...``); the raw candidate is tried as a fallback so plain
    payloads without the prefix keep working.
    """
    if "ck/a" not in url or "u=" not in url:
        return url
    m = re.search(r"(?:^|[?&])u=([A-Za-z0-9_-]+)", url)
    if not m:
        return url
    import base64

    enc = m.group(1)
    candidates = [enc[2:], enc] if enc.startswith("a1") else [enc]
    for candidate in candidates:
        try:
            padded = candidate + "=" * (-len(candidate) % 4)
            out = base64.urlsafe_b64decode(padded).decode("utf-8")
        except Exception:
            continue
        if out.startswith("http") or not enc.startswith("a1"):
            return out
    return url


def _host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return ""


def _is_bing_host(host: str) -> bool:
    return host == "bing.com" or host.endswith(".bing.com")


def _parse_bing_links(html: str, top: int = 5) -> list[str]:
    """Extract (redirect-decoded) result URLs from a Bing HTML results page.

    Modern Bing SERPs return results as absolute ``/ck/a`` redirect URLs with
    HTML-entity-encoded query params (``&amp;u=a1<base64url>``); navigation
    links are filtered by HOST so official result URLs that merely contain
    path words like ``/news`` or ``/images`` are never dropped.
    """
    links: list[str] = []
    seen = set()
    for m in re.finditer(r'<a[^>]+href="([^"]+)"', html):
        raw = unescape(m.group(1))
        if raw.startswith("/ck/a"):
            raw = "https://www.bing.com" + raw
        host = _host_of(raw)
        is_redirect = _is_bing_host(host) and "/ck/a" in raw
        if not is_redirect:
            if not raw.startswith("http"):
                continue
            # Skip Bing navigation/utility links by host only.
            if _is_bing_host(host) or host == "go.microsoft.com":
                continue
        url = _decode_bing_target(raw).split("#")[0]
        if not url.startswith("http") or url in seen:
            continue
        # An undecodable redirect still points at Bing — drop it.
        if _is_bing_host(_host_of(url)):
            continue
        seen.add(url)
        links.append(url)
        if len(links) >= top:
            break
    return links


def _parse_ddg_links(html: str, top: int = 5) -> list[str]:
    """Extract decoded result URLs from a DuckDuckGo HTML results page."""
    links: list[str] = []
    for m in re.finditer(r'uddg=([^&"]+)', html):
        try:
            decoded = unquote(m.group(1))
        except Exception:
            continue
        if decoded.startswith("http"):
            links.append(decoded)
        if len(links) >= top:
            break
    return links


def _search_candidate_links(query: str, top: int = 5) -> list[str]:
    """Search the web and return result URLs (not yet domain-filtered).

    Tries Bing HTML search first (tolerates automated reads), then falls back
    to DuckDuckGo. Never raises — returns [] when both are blocked.
    """
    bing_url = "https://www.bing.com/search?q=" + quote(query)
    html = _fetch_url(bing_url, timeout=max(HTTP_TIMEOUT_SEC, 10))
    if html:
        links = _parse_bing_links(html, top=top)
        if links:
            return links

    ddg_url = "https://html.duckduckgo.com/html/?q=" + quote(query)
    html = _fetch_url(ddg_url, timeout=max(HTTP_TIMEOUT_SEC, 10))
    if html:
        return _parse_ddg_links(html, top=top)
    return []


def _is_allowed_domain(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return False
    for src in OFFICIAL_SOURCES:
        domain = src["domain"].lower()
        if host == domain or host.endswith("." + domain):
            return True
    return False


# ---------------------------------------------------------------------------
# Source selection
# ---------------------------------------------------------------------------

def _select_sources(query: str, top_n: int = 3) -> list[dict[str, Any]]:
    q = query.lower()
    scored = []
    for src in OFFICIAL_SOURCES:
        score = 0
        for kw in src["keywords"]:
            if kw in q:
                score += 1
        # Any keyword match is a signal; the URL whitelist keeps us safe.
        if score > 0:
            scored.append((score, src))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [s for _, s in scored[:top_n]]
    if not selected:
        # No keyword matched — fall back to the most authoritative generic
        # sources (IP India + TKDL) so patentability/regulatory questions
        # still reach an official page.
        for domain in ("ipindia.gov.in", "tkdl.res.in"):
            match = next((s for s in OFFICIAL_SOURCES if s["domain"] == domain), None)
            if match:
                selected.append(match)
    return selected


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_official_sources(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """
    Fetch live passage chunks from official websites relevant to ``query``.

    Returns a list of source dicts (with full citation metadata) ready to be
    merged into the retrieval pipeline. Always returns [] on failure —
    this function never raises and never blocks the answer path.
    """
    if not _live_web_enabled():
        logger.info("Live web retrieval disabled (IPSAKTI_LIVE_WEB=0)")
        return []

    query = (query or "").strip()
    if len(query) < 3:
        return []

    selected = _select_sources(query, top_n=DEFAULT_MAX_FETCH_PAGES)
    results: list[dict[str, Any]] = []
    fetches = 0

    for src in selected:
        if fetches >= MAX_FETCHES_PER_QUERY:
            break

        search_q = f"site:{src['domain']} {query}"
        links = _search_candidate_links(search_q, top=3)
        # Safety: keep only whitelisted official domains.
        links = [u for u in links if _is_allowed_domain(u)]

        if not links:
            # Fall back to the source's curated canonical URL (known-good page
            # on an official domain) when search engines are blocked/degraded.
            canonical = src.get("canonical_url")
            if canonical and _is_allowed_domain(canonical):
                links = [canonical]
            else:
                fallback_term = (src.get("search_terms") or ["reference"])[0]
                fallback_q = f"site:{src['domain']} {fallback_term}"
                links = _search_candidate_links(fallback_q, top=2)
                links = [u for u in links if _is_allowed_domain(u)]

        for link in links[:DEFAULT_MAX_FETCH_PAGES]:
            if fetches >= MAX_FETCHES_PER_QUERY:
                break
            html = _fetch_url(link, timeout=HTTP_TIMEOUT_SEC)
            fetches += 1
            if not html:
                continue
            title, raw_text = _html_to_text(html)
            if len(raw_text) < 200:
                continue

            chunks = _chunk_web_text(raw_text)
            for ci, chunk in enumerate(chunks[:3]):
                if not chunk.strip():
                    continue
                digest = hashlib.sha1(link.encode("utf-8")).hexdigest()[:10]
                results.append({
                    "content": chunk[:1500],
                    "title": title,
                    "source": src["name"],
                    "source_url": link,
                    "category": "official",
                    "jurisdiction": src["jurisdiction"],
                    "authority": src["authority"],
                    "authority_level": src["authority_level"],
                    "section_heading": "",
                    "doc_id": f"LIVE-{digest}-{ci}",
                    "retrieval_method": "live_web",
                    "effective_date": "",
                })

    if results:
        logger.info(f"Live official retrieval: {len(results)} chunks for query "
                    f"{query[:60]!r} ({fetches} fetches)")
    else:
        logger.info(f"Live official retrieval: no usable content for {query[:60]!r}")

    return results[:top_k]


def get_status() -> dict[str, Any]:
    """Health/status metadata for the live-web retriever."""
    cache_stats = _page_cache.stats()
    return {
        "enabled": _live_web_enabled(),
        "official_domains": [s["domain"] for s in OFFICIAL_SOURCES],
        "cache": cache_stats,
        # Kept as a flat field because the admin status endpoint surfaces it;
        # `cache.backend` says whether this is the shared or the local view.
        "cache_entries": cache_stats["memory_entries"],
        "cache_backend": cache_stats["backend"],
        "cache_ttl_sec": CACHE_TTL_SEC,
        "timeout_sec": HTTP_TIMEOUT_SEC,
        "max_fetches_per_query": MAX_FETCHES_PER_QUERY,
    }