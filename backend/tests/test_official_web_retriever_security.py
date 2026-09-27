import pytest

from app.rag import official_web_retriever as owr

pytestmark = pytest.mark.security


@pytest.fixture(autouse=True)
def _cache_and_env(monkeypatch):
    owr._cache.clear()
    monkeypatch.delenv("IPSAKTI_LIVE_WEB", raising=False)
    yield
    owr._cache.clear()


def test_allowed_domain_accepts_official_host():
    assert owr._is_allowed_domain("https://ipindia.gov.in/patents") is True


def test_allowed_domain_accepts_official_subdomain():
    assert owr._is_allowed_domain("https://www.tkdl.res.in/foo") is True


def test_allowed_domain_rejects_arbitrary_host():
    assert owr._is_allowed_domain("https://evil.example.com/") is False


def test_allowed_domain_rejects_lookalike_suffix():
    assert owr._is_allowed_domain("https://ipindia.gov.in.evil.com/") is False


def test_allowed_domain_rejects_userinfo_trick():
    assert owr._is_allowed_domain("https://ipindia.gov.in@evil.com/") is False


def test_allowed_domain_rejects_internal_addresses():
    assert owr._is_allowed_domain("http://169.254.169.254/latest/meta-data/") is False
    assert owr._is_allowed_domain("http://localhost:8080/admin") is False
    assert owr._is_allowed_domain("http://127.0.0.1/") is False


def test_allowed_domain_rejects_non_http_scheme():
    assert owr._is_allowed_domain("file:///etc/passwd") is False


def test_live_web_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LIVE_WEB", "0")
    assert owr.fetch_official_sources("patent filing status india") == []


def test_short_query_returns_empty_without_fetch():
    assert owr.fetch_official_sources("ab") == []


def test_get_status_reports_configuration():
    status = owr.get_status()
    assert status["enabled"] is True
    assert "ipindia.gov.in" in status["official_domains"]
    assert status["max_fetches_per_query"] >= 0
    assert status["timeout_sec"] > 0


class _FakeResponse:
    status_code = 200
    text = "<html><title>probe</title><body>probe body</body></html>"


class _RecordingClient:
    fetched: list = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kwargs):
        _RecordingClient.fetched.append((url, self.kwargs))
        return _FakeResponse()


@pytest.fixture
def recording_httpx(monkeypatch):
    import httpx

    _RecordingClient.fetched = []
    monkeypatch.setattr(httpx, "Client", _RecordingClient)
    yield _RecordingClient
    _RecordingClient.fetched = []
    owr._cache.clear()


@pytest.mark.xfail(
    reason="_fetch_url performs no URL validation; any caller can fetch internal addresses "
    "(169.254.169.254, localhost) before any whitelist is applied",
    strict=False,
)
def test_fetch_url_refuses_internal_addresses(recording_httpx):
    owr._fetch_url("http://169.254.169.254/latest/meta-data/")
    assert recording_httpx.fetched == []


@pytest.mark.xfail(
    reason="_fetch_url follows redirects without re-validating the target against the whitelist",
    strict=False,
)
def test_fetch_url_does_not_follow_unvalidated_redirects(recording_httpx):
    owr._fetch_url("https://ipindia.gov.in/patents")
    assert recording_httpx.fetched
    _, kwargs = recording_httpx.fetched[0]
    assert not kwargs.get("follow_redirects")


def test_fetch_url_caches_successful_responses(recording_httpx):
    owr._fetch_url("https://ipindia.gov.in/page-a")
    owr._fetch_url("https://ipindia.gov.in/page-a")
    assert len(recording_httpx.fetched) == 1
