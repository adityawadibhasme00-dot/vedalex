import base64
import time as _time
from typing import Any
from urllib.parse import quote

import pytest

from app.rag import official_web_retriever as owr

_PAGE_HTML = (
    "<html><head><title>Patent Office Bulletin</title></head><body>"
    + "<p>The patent office publishes examination guidelines every quarter. </p>" * 12
    + "</body></html>"
)

_LONG_PAGE_HTML = (
    "<html><head><title>Long Register</title></head><body><p>"
    + "Registration of formulations requires documented evidence. " * 150
    + "</p></body></html>"
)


def _bing_page(*urls):
    anchors = "".join(f'<a href="{u}" class="r">result</a>' for u in urls)
    return f"<html><body>{anchors}</body></html>"


def _ddg_page(*urls):
    anchors = "".join(
        f'<a rel="nofollow" href="//duckduckgo.com/l/?uddg={quote(u, safe="")}">'
        for u in urls
    )
    return f"<html><body>{anchors}</body></html>"


@pytest.fixture(autouse=True)
def _retriever_env(monkeypatch):
    owr._cache.clear()
    monkeypatch.setenv("IPSAKTI_LIVE_WEB", "1")
    monkeypatch.setattr(owr, "MAX_FETCHES_PER_QUERY", 3)
    yield
    owr._cache.clear()


class _FakeWeb:
    """Scripted replacement for ``_fetch_url`` — fully offline."""

    def __init__(self):
        self.calls = []
        self.bing = []
        self.ddg = []
        self.pages = {}

    def fetch(self, url, timeout=None):
        self.calls.append(url)
        if "bing.com/search" in url:
            return self.bing.pop(0) if self.bing else None
        if "duckduckgo.com" in url:
            return self.ddg.pop(0) if self.ddg else None
        return self.pages.get(url)

    @property
    def page_calls(self):
        return [u for u in self.calls
                if "bing.com" not in u and "duckduckgo.com" not in u]


@pytest.fixture
def web(monkeypatch):
    fake = _FakeWeb()
    monkeypatch.setattr(owr, "_fetch_url", fake.fetch)
    return fake


# ---------------------------------------------------------------------------
# _html_to_text
# ---------------------------------------------------------------------------

def test_html_to_text_extracts_title_and_strips_markup():
    html = (
        "<html><head><title>Patent Office Registry</title>"
        "<style>p { color: red; }</style></head>"
        "<body><script>var x = 1;</script><!-- internal note -->"
        "<p>Line one</p><div>Line two</div></body></html>"
    )
    title, text = owr._html_to_text(html)

    assert title == "Patent Office Registry"
    assert "var x = 1" not in text
    assert "internal note" not in text
    assert "Line one Line two" in text
    assert "<" not in text
    assert text == " ".join(text.split())


def test_html_to_text_defaults_title_when_absent():
    title, text = owr._html_to_text("<html><body>body only content</body></html>")
    assert title == "Official Source"
    assert "body only content" in text


def test_html_to_text_falls_back_when_title_is_blank():
    title, _ = owr._html_to_text("<html><head><title>   </title></head>"
                                 "<body>content</body></html>")
    assert title == "Official Source"


def test_html_to_text_strips_nested_tags_inside_title():
    title, _ = owr._html_to_text("<html><head><title><b>Deep</b> Title</title>"
                                 "</head><body>content</body></html>")
    assert "<" not in title
    assert "Deep" in title
    assert "Title" in title


def test_html_to_text_decodes_entities_in_body():
    _, text = owr._html_to_text("<html><body><p>Tom &amp; Jerry report</p>"
                                "</body></html>")
    assert "Tom & Jerry report" in text


def test_html_to_text_handles_multiline_title():
    title, _ = owr._html_to_text("<html><head><title>\n  Annual\n  Report\n"
                                 "</title></head><body>x</body></html>")
    assert "Annual" in title
    assert "Report" in title
    assert title == title.strip()


# ---------------------------------------------------------------------------
# _chunk_web_text
# ---------------------------------------------------------------------------

def test_chunk_web_text_splits_with_overlap():
    words = [f"w{i}" for i in range(30)]
    chunks = owr._chunk_web_text(" ".join(words), size=10, overlap=2)

    assert chunks[0].split() == words[:10]
    assert chunks[1].split() == words[8:18]
    assert len(set(chunks)) == len(chunks)


def test_chunk_web_text_returns_single_chunk_for_short_text():
    assert owr._chunk_web_text("short passage", size=10, overlap=2) == ["short passage"]


def test_chunk_web_text_returns_nothing_for_empty_text():
    assert owr._chunk_web_text("") == []


def test_chunk_web_text_defaults_produce_bounded_chunks():
    text = " ".join(f"w{i}" for i in range(1000))
    chunks = owr._chunk_web_text(text)

    assert len(chunks) == 3
    assert all(len(c.split()) <= 450 for c in chunks)
    assert len(set(chunks)) == 3
    assert chunks[0].split()[0] == "w0"


def test_chunk_web_text_dedupes_repeated_windows():
    text = " ".join("same" for _ in range(20))
    chunks = owr._chunk_web_text(text, size=10, overlap=6)
    assert len(chunks) == len(set(chunks))
    assert len(chunks) < 5


# ---------------------------------------------------------------------------
# _decode_bing_target
# ---------------------------------------------------------------------------

def _b64url(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode().rstrip("=")


def test_decode_bing_target_passes_plain_urls_through():
    url = "https://ipindia.gov.in/patents"
    assert owr._decode_bing_target(url) == url


def test_decode_bing_target_decodes_ck_redirect():
    real = "https://ipindia.gov.in/patents/application-status"
    url = f"https://www.bing.com/ck/a?!&p=1&u={_b64url(real)}&ntb=1"
    assert owr._decode_bing_target(url) == real


def test_decode_bing_target_keeps_url_without_redirect_param():
    url = "https://www.bing.com/ck/a?ntb=1&q=patent"
    assert owr._decode_bing_target(url) == url


def test_decode_bing_target_keeps_url_when_payload_is_not_base64():
    url = "https://www.bing.com/ck/a?u=!!!not-base64!!!&ntb=1"
    assert owr._decode_bing_target(url) == url


def test_decode_bing_target_keeps_url_when_payload_is_not_utf8():
    url = "https://www.bing.com/ck/a?u=aaaa&ntb=1"
    assert owr._decode_bing_target(url) == url


# ---------------------------------------------------------------------------
# _parse_bing_links
# ---------------------------------------------------------------------------

def test_parse_bing_links_extracts_and_dedupes_results():
    html = _bing_page(
        "https://ipindia.gov.in/patents",
        "https://ipindia.gov.in/patents",
        "https://tkdl.res.in/prior-art",
        "https://evil.example.com/x",
    )
    links = owr._parse_bing_links(html)
    assert links == ["https://ipindia.gov.in/patents",
                     "https://tkdl.res.in/prior-art",
                     "https://evil.example.com/x"]


def test_parse_bing_links_respects_top_limit():
    html = _bing_page(*[f"https://ipindia.gov.in/p{i}" for i in range(10)])
    assert len(owr._parse_bing_links(html, top=3)) == 3


def test_parse_bing_links_skips_navigation_links():
    html = (
        '<a href="https://www.bing.com/images?q=x">images</a>'
        '<a href="https://www.bing.com/news?q=x">news</a>'
        '<a href="https://www.bing.com/maps?q=x">maps</a>'
        '<a href="https://go.microsoft.com/fwlink/?linkid=1">fw</a>'
        '<a href="https://ipindia.gov.in/patents">real</a>'
    )
    assert owr._parse_bing_links(html) == ["https://ipindia.gov.in/patents"]


def test_parse_bing_links_strips_fragments():
    html = _bing_page("https://ipindia.gov.in/patents#section-3")
    assert owr._parse_bing_links(html) == ["https://ipindia.gov.in/patents"]


def test_parse_bing_links_without_results_returns_empty():
    assert owr._parse_bing_links("<html><body>no anchors</body></html>") == []


def test_parse_bing_links_decodes_redirect_result_urls():
    html = _bing_page(f"https://www.bing.com/ck/a?u={_b64url('https://wipo.int/pct')}"
                      "&amp;ntb=1")
    assert owr._parse_bing_links(html) == ["https://wipo.int/pct"]


def test_parse_bing_links_keeps_official_urls_containing_skip_words():
    html = _bing_page(
        "https://pib.gov.in/news/2024/12345",
        "https://www.fssai.gov.in/images/labelling",
    )
    links = owr._parse_bing_links(html)
    assert "https://pib.gov.in/news/2024/12345" in links


def test_parse_bing_links_decodes_real_world_a1_redirects():
    """Real Bing SERPs: entity-encoded hrefs with the ``a1`` base64 prefix."""
    real = "https://indiacode.ecourtsindia.com/patents-act/"
    enc = "a1" + _b64url(real)
    html = (
        '<a href="https://www.bing.com/ck/a?!&amp;&amp;p=abc123&amp;ptn=3&amp;'
        f'ver=2&amp;fclid=xyz-123&amp;u={enc}&amp;ntb=1" class="t">result</a>'
        '<a href="https://www.bing.com/search?q=more">nav</a>'
        '<a href="https://ipindia.gov.in/guidelines">direct</a>'
    )
    assert owr._parse_bing_links(html) == [real, "https://ipindia.gov.in/guidelines"]


def test_parse_bing_links_handles_relative_ck_redirects():
    real = "https://ipindia.gov.in/patents"
    enc = "a1" + _b64url(real)
    html = f'<a href="/ck/a?u={enc}&amp;ntb=1">result</a>'
    assert owr._parse_bing_links(html) == [real]


def test_decode_bing_target_strips_a1_scheme_prefix():
    real = "https://wipo.int/pct"
    url = f"https://www.bing.com/ck/a?u=a1{_b64url(real)}&ntb=1"
    assert owr._decode_bing_target(url) == real


# ---------------------------------------------------------------------------
# _parse_ddg_links
# ---------------------------------------------------------------------------

def test_parse_ddg_links_decodes_redirect_targets():
    html = _ddg_page("https://ipindia.gov.in/patents",
                     "https://tkdl.res.in/prior-art")
    assert owr._parse_ddg_links(html) == ["https://ipindia.gov.in/patents",
                                          "https://tkdl.res.in/prior-art"]


def test_parse_ddg_links_skips_non_http_targets():
    html = _ddg_page("ftp://files.example.org/a",
                     "https://ipindia.gov.in/patents")
    assert owr._parse_ddg_links(html) == ["https://ipindia.gov.in/patents"]


def test_parse_ddg_links_respects_top_limit():
    html = _ddg_page(*[f"https://ipindia.gov.in/p{i}" for i in range(8)])
    assert len(owr._parse_ddg_links(html, top=2)) == 2


def test_parse_ddg_links_without_results_returns_empty():
    assert owr._parse_ddg_links("<html><body>blocked</body></html>") == []


# ---------------------------------------------------------------------------
# _search_candidate_links
# ---------------------------------------------------------------------------

def test_search_candidate_links_prefers_bing(web):
    web.bing = [_bing_page("https://ipindia.gov.in/patents")]
    web.ddg = [_ddg_page("https://tkdl.res.in/x")]

    links = owr._search_candidate_links("site:ipindia.gov.in patent")

    assert links == ["https://ipindia.gov.in/patents"]
    assert web.ddg == [_ddg_page("https://tkdl.res.in/x")]


def test_search_candidate_links_falls_back_to_ddg(web):
    web.bing = ["<html><body>no results</body></html>"]
    web.ddg = [_ddg_page("https://ipindia.gov.in/patents")]

    assert owr._search_candidate_links("site:ipindia.gov.in patent") == [
        "https://ipindia.gov.in/patents"]
    assert len(web.calls) == 2


def test_search_candidate_links_returns_empty_when_both_engines_blocked(web):
    assert owr._search_candidate_links("site:ipindia.gov.in patent") == []
    assert len(web.calls) == 2


def test_search_candidate_links_uses_fallback_query_when_ddg_has_no_results(web):
    web.bing = ["<html><body>no results</body></html>"]
    web.ddg = ["<html><body>no results</body></html>"]
    assert owr._search_candidate_links("site:wipo.int pct") == []


# ---------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------

def test_cache_roundtrip():
    assert owr._cache_set("k1", "value") == "value"
    assert owr._cache_get("k1") == "value"
    assert "k1" in owr._cache


def test_cache_get_returns_none_for_missing_key():
    assert owr._cache_get("absent") is None


def test_cache_get_drops_expired_entries():
    # Entries are written through the SharedCache API, not as raw tuples.
    owr._cache.set("stale", "old", ttl=0.01)
    assert owr._cache_get("stale") == "old"
    _time.sleep(0.05)
    assert owr._cache_get("stale") is None


def test_cache_get_keeps_fresh_entries():
    owr._cache_set("fresh", "new")
    assert owr._cache_get("fresh") == "new"


def test_cache_set_stays_within_capacity():
    # Over capacity the cache evicts oldest-first rather than wiping itself, so
    # the entry just written must always survive.
    for i in range(owr._page_cache.max_memory_entries + 8):
        owr._cache_set(f"filler-{i}", "x")
    owr._cache_set("after", "y")
    assert owr._cache_get("after") == "y"
    assert len(owr._page_cache._mem) <= owr._page_cache.max_memory_entries


def test_allowed_domain_treats_malformed_authority_as_rejected():
    assert owr._is_allowed_domain("http://[unterminated") is False


# ---------------------------------------------------------------------------
# _fetch_url
# ---------------------------------------------------------------------------

class _StubResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


@pytest.fixture
def http_stub(monkeypatch):
    import httpx

    class _Client:
        calls: list[Any] = []
        script: list[Any] = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, **kwargs):
            _Client.calls.append((url, self.kwargs))
            if not _Client.script:
                return _StubResponse(200, "<html><title>ok</title>body</html>")
            item = _Client.script.pop(0)
            if isinstance(item, Exception):
                raise item
            status, text = item
            return _StubResponse(status, text)

    monkeypatch.setattr(httpx, "Client", _Client)
    yield _Client
    _Client.calls = []
    _Client.script = []


def test_fetch_url_returns_body_and_sets_browser_headers(http_stub):
    out = owr._fetch_url("https://ipindia.gov.in/page")

    assert out == "<html><title>ok</title>body</html>"
    _, kwargs = http_stub.calls[0]
    assert kwargs["follow_redirects"] is True
    assert kwargs["timeout"] == owr.HTTP_TIMEOUT_SEC
    assert "IP-SAKTI" in kwargs["headers"]["User-Agent"]


def test_fetch_url_caches_successful_response(http_stub):
    owr._fetch_url("https://ipindia.gov.in/page")
    owr._fetch_url("https://ipindia.gov.in/page")
    assert len(http_stub.calls) == 1
    assert owr._cache_get("https://ipindia.gov.in/page")


def test_fetch_url_returns_none_on_http_error(http_stub):
    http_stub.script = [(404, "not found")]
    assert owr._fetch_url("https://ipindia.gov.in/missing") is None
    assert owr._cache_get("https://ipindia.gov.in/missing") is None


def test_fetch_url_retries_after_an_http_error(http_stub):
    http_stub.script = [(404, "not found"), (200, "later")]
    assert owr._fetch_url("https://ipindia.gov.in/flaky") is None
    assert owr._fetch_url("https://ipindia.gov.in/flaky") == "later"
    assert len(http_stub.calls) == 2


def test_fetch_url_swallows_transport_errors(http_stub):
    http_stub.script = [RuntimeError("connection refused")]
    assert owr._fetch_url("https://ipindia.gov.in/down") is None


def test_fetch_url_honours_custom_timeout(http_stub):
    owr._fetch_url("https://ipindia.gov.in/slow", timeout=3.0)
    _, kwargs = http_stub.calls[0]
    assert kwargs["timeout"] == 3.0


# ---------------------------------------------------------------------------
# _select_sources
# ---------------------------------------------------------------------------

def test_select_sources_ranks_keyword_matches():
    selected = owr._select_sources("filing patent application status tracker")
    domains = [s["domain"] for s in selected]

    assert domains[0] == "ipindia.gov.in"
    assert "indiacode.nic.in" in domains


def test_select_sources_respects_top_n():
    selected = owr._select_sources("patent act section 3 prior art", top_n=1)
    assert len(selected) == 1


def test_select_sources_falls_back_to_authoritative_defaults():
    selected = owr._select_sources("completely unrelated wording")
    assert [s["domain"] for s in selected] == ["ipindia.gov.in", "tkdl.res.in"]


def test_select_sources_returns_empty_when_fallback_also_misses(monkeypatch):
    monkeypatch.setattr(owr, "OFFICIAL_SOURCES",
                        [dict(owr.OFFICIAL_SOURCES[4])])
    assert owr._select_sources("completely unrelated wording") == []


def test_select_sources_matches_regulatory_authorities():
    assert [s["domain"] for s in owr._select_sources("fssai nutraceutical")] == [
        "fssai.gov.in"]
    assert [s["domain"] for s in owr._select_sources("schedule t cdsco drugs")] == [
        "cdsco.gov.in"]
    assert [s["domain"] for s in owr._select_sources("access benefit sharing nba")] == [
        "nbaindia.org"]


# ---------------------------------------------------------------------------
# fetch_official_sources
# ---------------------------------------------------------------------------

def test_fetch_official_sources_requires_live_web_toggle(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LIVE_WEB", "0")
    assert owr.fetch_official_sources("patent filing status india") == []


@pytest.mark.parametrize("query", ["", "ab", None])
def test_fetch_official_sources_rejects_short_queries(query):
    assert owr.fetch_official_sources(query) == []


def test_fetch_official_sources_builds_provenanced_chunks(web):
    web.bing = [_bing_page("https://fssai.gov.in/nutraceutical-guidance")]
    web.pages["https://fssai.gov.in/nutraceutical-guidance"] = _PAGE_HTML

    results = owr.fetch_official_sources("fssai nutraceutical labelling", top_k=3)

    assert results
    first = results[0]
    assert first["category"] == "official"
    assert first["retrieval_method"] == "live_web"
    assert first["source_url"] == "https://fssai.gov.in/nutraceutical-guidance"
    assert first["title"] == "Patent Office Bulletin"
    assert first["source"] == "FSSAI"
    assert first["jurisdiction"] == "India"
    assert first["authority_level"] == 2
    assert first["doc_id"].startswith("LIVE-")
    assert first["content"].strip()
    assert "guidelines" in first["content"]


def test_fetch_official_sources_respects_top_k(web):
    web.bing = [_bing_page("https://fssai.gov.in/nutraceutical-guidance")]
    web.pages["https://fssai.gov.in/nutraceutical-guidance"] = _PAGE_HTML

    results = owr.fetch_official_sources("fssai nutraceutical labelling", top_k=1)
    assert len(results) == 1


def test_fetch_official_sources_emits_at_most_three_chunks_per_page(web):
    web.bing = [_bing_page("https://fssai.gov.in/nutraceutical-guidance")]
    web.pages["https://fssai.gov.in/nutraceutical-guidance"] = _LONG_PAGE_HTML

    results = owr.fetch_official_sources("fssai nutraceutical labelling", top_k=10)
    assert len(results) == 3


def test_fetch_official_sources_drops_non_whitelisted_links_and_uses_canonical(
        web):
    web.bing = [_bing_page("https://evil.example.com/fake")]
    web.pages["https://www.fssai.gov.in/"] = _PAGE_HTML

    results = owr.fetch_official_sources("fssai nutraceutical labelling")

    assert results
    assert results[0]["source_url"] == "https://www.fssai.gov.in/"
    assert all("evil.example.com" not in r["source_url"] for r in results)


def test_fetch_official_sources_uses_search_terms_when_canonical_is_unavailable(
        web, monkeypatch):
    stripped = dict(owr.OFFICIAL_SOURCES[0])
    stripped.pop("canonical_url")
    monkeypatch.setattr(owr, "OFFICIAL_SOURCES", [stripped])

    web.bing = [
        _bing_page("https://evil.example.com/fake"),
        _bing_page("https://www.indiacode.nic.in/acts/1970"),
    ]
    web.pages["https://www.indiacode.nic.in/acts/1970"] = _PAGE_HTML

    results = owr.fetch_official_sources("patents act section 3")

    assert results
    assert results[0]["source_url"] == "https://www.indiacode.nic.in/acts/1970"
    assert "https://www.indiacode.nic.in/acts/1970" in web.calls


def test_fetch_official_sources_stops_at_fetch_budget(web, monkeypatch):
    monkeypatch.setattr(owr, "MAX_FETCHES_PER_QUERY", 1)
    web.bing = [_bing_page("https://www.indiacode.nic.in/a",
                           "https://ipindia.gov.in/b")]
    web.pages["https://www.indiacode.nic.in/a"] = _PAGE_HTML
    web.pages["https://ipindia.gov.in/b"] = _PAGE_HTML

    owr.fetch_official_sources("patent filing")

    assert len(web.page_calls) == 1


def test_fetch_official_sources_skips_pages_that_are_too_short(web):
    web.bing = [_bing_page("https://fssai.gov.in/nutraceutical-guidance")]
    web.pages["https://fssai.gov.in/nutraceutical-guidance"] = (
        "<html><head><title>Stub</title></head><body>too short</body></html>")

    assert owr.fetch_official_sources("fssai nutraceutical labelling") == []


def test_fetch_official_sources_skips_unreachable_pages(web):
    web.bing = [_bing_page("https://fssai.gov.in/nutraceutical-guidance")]

    assert owr.fetch_official_sources("fssai nutraceutical labelling") == []
    assert web.page_calls == ["https://fssai.gov.in/nutraceutical-guidance"]


def test_fetch_official_sources_returns_empty_when_search_is_blocked(web):
    assert owr.fetch_official_sources("fssai nutraceutical labelling") == []
    assert web.page_calls == ["https://www.fssai.gov.in/"]


# ---------------------------------------------------------------------------
# _live_web_enabled / get_status
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("0", False), ("false", False), ("OFF", False), ("no", False),
    ("1", True), ("yes", True), ("", True),
])
def test_live_web_enabled_flag(monkeypatch, value, expected):
    monkeypatch.setenv("IPSAKTI_LIVE_WEB", value)
    assert owr._live_web_enabled() is expected


def test_get_status_reports_runtime_configuration():
    owr._cache_set("https://ipindia.gov.in/x", "body")
    status = owr.get_status()

    assert status["enabled"] is True
    assert status["official_domains"] == [
        s["domain"] for s in owr.OFFICIAL_SOURCES]
    assert status["cache_entries"] == 1
    assert status["cache_ttl_sec"] == owr.CACHE_TTL_SEC
    assert status["timeout_sec"] == owr.HTTP_TIMEOUT_SEC
    assert status["max_fetches_per_query"] == owr.MAX_FETCHES_PER_QUERY


def test_get_status_reflects_disabled_toggle(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LIVE_WEB", "0")
    assert owr.get_status()["enabled"] is False


# ---------------------------------------------------------------------------
# defects
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="chunk step is size-overlap with no validation, so overlap >= size "
           "raises range() step zero or silently yields no chunks "
           "(official_web_retriever.py:262)",
    strict=False)
def test_chunk_web_text_survives_overlap_not_smaller_than_size():
    text = " ".join(f"w{i}" for i in range(40))
    chunks = owr._chunk_web_text(text, size=10, overlap=10)
    assert chunks


@pytest.mark.xfail(
    reason="source keyword match is a raw substring test, so short keywords "
           "like 'who' match inside unrelated words and pick the wrong "
           "authority (official_web_retriever.py:370)",
    strict=False)
def test_select_sources_picks_regulatory_authority_for_food_query():
    selected = owr._select_sources("wholesome food labels for children")
    assert "fssai.gov.in" in [s["domain"] for s in selected]
