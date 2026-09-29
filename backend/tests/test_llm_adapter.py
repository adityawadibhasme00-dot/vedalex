import types
from typing import Any

import pytest

from app.rag import llm_adapter as la

SOURCES = [
    {"title": "Patents Act", "content": "UNIQUEMARK1 Section 3(p) excludes evergreening."},
    {"act_title": "Drugs and Cosmetics Act", "content": "UNIQUEMARK2 Rule 158-B governs ASU GMP."},
    {"source": "TKDL", "content": "UNIQUEMARK3 traditional knowledge database."},
    {"title": "FSSAI", "content": "UNIQUEMARK4 nutraceutical regulations."},
    {"title": "WHO", "content": "UNIQUEMARK5 monograph list."},
    {"title": "Sixth", "content": "SIXTHMARKER must stay out of the prompt."},
]


@pytest.fixture(autouse=True)
def _keyless_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("IPSAKTI_LLM_MODEL", raising=False)
    yield


class _FakeGeminiResponse:
    def __init__(self, payload=None, status_error=None):
        self.payload = payload if payload is not None else {}
        self.status_error = status_error
        self.checked = False

    def raise_for_status(self):
        self.checked = True
        if self.status_error is not None:
            raise self.status_error

    def json(self):
        return self.payload


class _FakeGeminiClient:
    def __init__(self, response, **kwargs):
        self.response = response
        self.kwargs = kwargs
        self.posts = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, json=None, headers=None):
        self.posts.append((url, json, headers))
        return self.response


def _install_fake_httpx(monkeypatch, response):
    import httpx

    created = {}

    def factory(**kwargs):
        client = _FakeGeminiClient(response, **kwargs)
        created["client"] = client
        return client

    monkeypatch.setattr(httpx, "Client", factory)
    return created


def _install_fake_openai(monkeypatch, content):
    import openai

    created = {}

    class _Completions:
        def create(self, **kwargs):
            created["kwargs"] = kwargs
            message = types.SimpleNamespace(content=content)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    class _Chat:
        def __init__(self):
            self.completions = _Completions()

    class _Client:
        def __init__(self, api_key=None, timeout=None):
            created["api_key"] = api_key
            created["timeout"] = timeout
            self.chat = _Chat()

    monkeypatch.setattr(openai, "OpenAI", _Client)
    return created


def test_resolve_provider_auto_without_keys(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "auto")
    assert la._resolve_provider() == "off"


def test_resolve_provider_auto_prefers_gemini(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    assert la._resolve_provider() == "gemini"


def test_resolve_provider_auto_falls_back_to_openai(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "auto")
    monkeypatch.setenv("OPENAI_API_KEY", "o-key")
    assert la._resolve_provider() == "openai"


@pytest.mark.parametrize("provider", ["gemini", "openai", "mock", "off"])
def test_resolve_provider_passes_explicit_values(monkeypatch, provider):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", provider)
    assert la._resolve_provider() == provider


def test_resolve_provider_unknown_value_disables_generation(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "  BoGuS ")
    assert la._resolve_provider() == "off"


def test_pick_model_defaults(monkeypatch):
    assert la._pick_model("gemini") == la.DEFAULT_MODELS["gemini"] == "gemini-3.5-flash"
    assert la._pick_model("openai") == "gpt-4o-mini"
    assert la._pick_model("mock") is None
    assert la._pick_model("off") is None


def test_pick_model_env_override(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_MODEL", "  custom-model ")
    assert la._pick_model("gemini") == "custom-model"


def test_generate_draft_disabled_provider(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "off")
    out = la.generate_draft("what is section 3(p)?", SOURCES)
    assert out["generated"] is False
    assert out["text"] is None
    assert out["provider"] == "off"
    assert out["model"] is None
    assert "disabled" in out["reason"]


def test_generate_draft_unknown_provider_is_off(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "warp-speed")
    out = la.generate_draft("query", SOURCES)
    assert out["provider"] == "off"
    assert out["generated"] is False
    assert out["text"] is None


def test_generate_draft_mock_builds_deterministic_draft(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "mock")
    first = la.generate_draft("what is section 3(p)?", SOURCES)
    second = la.generate_draft("what is section 3(p)?", SOURCES)
    assert first == second
    assert first["generated"] is True
    assert first["provider"] == "mock"
    assert first["model"] == "deterministic"
    assert first["reason"] == ""
    text = first["text"]
    assert text.startswith("Based on the retrieved official sources:\n\n")
    assert "1. Patents Act: UNIQUEMARK1 Section 3(p) excludes evergreening." in text
    assert "2. Drugs and Cosmetics Act: UNIQUEMARK2" in text
    assert "3. TKDL: UNIQUEMARK3" in text
    assert "4. FSSAI: UNIQUEMARK4" in text
    assert "SIXTHMARKER" not in text
    assert "UNIQUEMARK5" not in text


def test_generate_draft_mock_without_sources(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "mock")
    out = la.generate_draft("query", [])
    assert out["generated"] is False
    assert out["text"] is None
    assert out["reason"] == "No sources to mock-draft from"


def test_mock_draft_label_fallbacks():
    text = la._mock_draft(
        "q",
        [{"content": "alpha"}, {"content": "beta"}, {"content": "gamma"}, {"content": "delta"}],
    )
    lines = text.split("\n\n", 1)[1].splitlines()
    assert text.split("\n\n", 1)[0] == "Based on the retrieved official sources:"
    assert lines == [
        "1. Source 1: alpha",
        "2. Source 2: beta",
        "3. Source 3: gamma",
        "4. Source 4: delta",
    ]


def test_mock_draft_normalizes_and_truncates_content():
    text = la._mock_draft("q", [{"title": "T", "content": "  spaced \n\n content " + "x" * 400}])
    lines = text.split("\n\n", 1)[1].splitlines()
    assert len(lines) == 1
    body = lines[0]
    assert body.startswith("1. T: spaced content ")
    payload = body.split(": ", 1)[1]
    assert len(payload) == 220
    assert "  " not in payload


def test_mock_draft_skips_blank_sources():
    assert la._mock_draft("q", []) == ""
    assert la._mock_draft("q", [{"content": ""}, {"content": "   "}]) == ""


def test_call_gemini_success(monkeypatch):
    response = _FakeGeminiResponse(
        {"candidates": [{"content": {"parts": [{"text": "draft "}, {"text": "text"}]}}]}
    )
    created = _install_fake_httpx(monkeypatch, response)
    out = la._call_gemini("SYSTEM PROMPT", "USER PROMPT", "key-123", "gemini-2.0-flash")
    assert out == {"generated": True, "text": "draft text"}
    assert response.checked is True
    client = created["client"]
    assert client.kwargs["timeout"] == la.LLM_TIMEOUT_SEC
    url, payload, headers = client.posts[0]
    assert url.startswith("https://generativelanguage.googleapis.com/v1beta/models/")
    assert url.endswith("gemini-2.0-flash:generateContent")
    # The key travels as a header so it never lands in an access log.
    assert "key-123" not in url
    assert headers["x-goog-api-key"] == "key-123"
    assert payload["system_instruction"]["parts"][0]["text"] == "SYSTEM PROMPT"
    assert payload["contents"][0]["role"] == "user"
    assert payload["contents"][0]["parts"][0]["text"] == "USER PROMPT"
    assert payload["generationConfig"] == {"temperature": 0.1, "maxOutputTokens": 1500}


def test_call_gemini_without_candidates(monkeypatch):
    _install_fake_httpx(monkeypatch, _FakeGeminiResponse({"candidates": []}))
    out = la._call_gemini("s", "u", "k", "m")
    assert out == {"generated": False, "reason": "Gemini returned no candidates"}
    _install_fake_httpx(monkeypatch, _FakeGeminiResponse({}))
    assert la._call_gemini("s", "u", "k", "m") == {
        "generated": False,
        "reason": "Gemini returned no candidates",
    }


def test_call_gemini_with_empty_text(monkeypatch):
    _install_fake_httpx(
        monkeypatch, _FakeGeminiResponse({"candidates": [{"content": {"parts": [{"text": "   "}]}}]})
    )
    out = la._call_gemini("s", "u", "k", "m")
    assert out == {"generated": False, "reason": "Gemini returned an empty response"}
    _install_fake_httpx(monkeypatch, _FakeGeminiResponse({"candidates": [{"content": {}}]}))
    assert la._call_gemini("s", "u", "k", "m") == {
        "generated": False,
        "reason": "Gemini returned an empty response",
    }


def test_call_gemini_propagates_http_errors(monkeypatch):
    _install_fake_httpx(monkeypatch, _FakeGeminiResponse(status_error=RuntimeError("upstream 500")))
    with pytest.raises(RuntimeError, match="upstream 500"):
        la._call_gemini("s", "u", "k", "m")


def test_call_openai_success(monkeypatch):
    created = _install_fake_openai(monkeypatch, "  grounded draft  ")
    out = la._call_openai("SYSTEM PROMPT", "USER PROMPT", "o-key", "gpt-4o-mini")
    assert out == {"generated": True, "text": "grounded draft"}
    assert created["api_key"] == "o-key"
    assert created["timeout"] == la.LLM_TIMEOUT_SEC
    kwargs = created["kwargs"]
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["temperature"] == 0.1
    assert kwargs["max_tokens"] == 1500
    assert kwargs["messages"][0] == {"role": "system", "content": "SYSTEM PROMPT"}
    assert kwargs["messages"][1] == {"role": "user", "content": "USER PROMPT"}


@pytest.mark.parametrize("content", [None, "   ", ""])
def test_call_openai_with_empty_response(monkeypatch, content):
    _install_fake_openai(monkeypatch, content)
    out = la._call_openai("s", "u", "k", "m")
    assert out == {"generated": False, "reason": "OpenAI returned an empty response"}


def test_generate_draft_gemini_happy_path(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    captured: dict[str, Any] = {}

    def _fake_call(system, user, api_key, model):
        captured.update(system=system, user=user, api_key=api_key, model=model)
        return {"generated": True, "text": "grounded draft"}

    monkeypatch.setattr(la, "_call_gemini", _fake_call)
    out = la.generate_draft("what is section 3(p)?", SOURCES, intent="patent")
    assert out == {
        "generated": True,
        "text": "grounded draft",
        "provider": "gemini",
        "model": la.DEFAULT_MODELS["gemini"],
        "reason": "",
    }
    assert captured["api_key"] == "gem-key"
    assert captured["model"] == la.DEFAULT_MODELS["gemini"]
    assert "what is section 3(p)?" in captured["user"]
    assert "UNIQUEMARK1" in captured["user"]
    assert "SIXTHMARKER" not in captured["user"]
    assert "IP-SAKTI" in captured["system"]


def test_generate_draft_openai_happy_path(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    _install_fake_openai(monkeypatch, "openai draft")
    out = la.generate_draft("query", SOURCES)
    assert out == {
        "generated": True,
        "text": "openai draft",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "reason": "",
    }


def test_generate_draft_without_sources_short_circuits(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    out = la.generate_draft("query", [])
    assert out["generated"] is False
    assert out["text"] is None
    assert out["provider"] == "gemini"
    assert out["reason"] == "No retrieved sources to ground the draft"


def test_generate_draft_gemini_without_api_key(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "gemini")
    out = la.generate_draft("query", SOURCES)
    assert out["generated"] is False
    assert out["text"] is None
    assert out["model"] == la.DEFAULT_MODELS["gemini"]
    assert out["reason"] == "GEMINI_API_KEY is not set"


def test_generate_draft_openai_without_api_key(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "openai")
    out = la.generate_draft("query", SOURCES)
    assert out["generated"] is False
    assert out["text"] is None
    assert out["model"] == "gpt-4o-mini"
    assert out["reason"] == "OPENAI_API_KEY is not set"


def test_generate_draft_provider_exception_becomes_clean_failure(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")

    def _boom(system, user, api_key, model):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(la, "_call_gemini", _boom)
    out = la.generate_draft("query", SOURCES)
    assert out["generated"] is False
    assert out["text"] is None
    assert out["provider"] == "gemini"
    assert out["model"] == la.DEFAULT_MODELS["gemini"]
    assert out["reason"] == "provider exploded"


def test_generate_draft_falls_back_when_prompt_build_fails(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    import app.rag.prompt_templates as prompt_templates

    def _broken_build(**kwargs):
        raise RuntimeError("template missing")

    monkeypatch.setattr(prompt_templates, "build_rag_prompt", _broken_build)
    captured: dict[str, Any] = {}

    def _fake_call(system, user, api_key, model):
        captured.update(system=system, user=user)
        return {"generated": True, "text": "fallback draft"}

    monkeypatch.setattr(la, "_call_gemini", _fake_call)
    out = la.generate_draft("query", SOURCES)
    assert out["generated"] is True
    assert out["text"] == "fallback draft"
    assert "## RETRIEVED SOURCE DOCUMENTS" in captured["user"]
    assert "## USER QUESTION" in captured["user"]
    assert "UNIQUEMARK1" in captured["user"]
    assert "SIXTHMARKER" not in captured["user"]
    assert "evidence-grounded" in captured["system"]


@pytest.mark.xfail(
    reason="generate_draft overwrites the provider failure reason with an empty string, hiding "
    "'OpenAI returned an empty response' from callers (llm_adapter.py:248)",
    strict=False,
)
def test_generate_draft_preserves_provider_failure_reason(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr(
        la,
        "_call_openai",
        lambda *args, **kwargs: {"generated": False, "reason": "OpenAI returned an empty response"},
    )
    out = la.generate_draft("query", SOURCES)
    assert out["generated"] is False
    assert out["reason"] == "OpenAI returned an empty response"


@pytest.mark.xfail(
    reason="provider failure results omit the documented 'text' key entirely, so callers doing "
    "result['text'] hit a KeyError (llm_adapter.py:117 and llm_adapter.py:248)",
    strict=False,
)
def test_generate_draft_result_always_contains_text_key(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr(
        la,
        "_call_openai",
        lambda *args, **kwargs: {"generated": False, "reason": "OpenAI returned an empty response"},
    )
    out = la.generate_draft("query", SOURCES)
    assert "text" in out
    assert out["text"] is None


@pytest.mark.xfail(
    reason="the api key is resolved as GEMINI_API_KEY or OPENAI_API_KEY, so the OpenAI provider "
    "receives the Gemini key whenever both are configured (llm_adapter.py:221)",
    strict=False,
)
def test_generate_draft_openai_uses_openai_key(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "openai")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    created = _install_fake_openai(monkeypatch, "draft")
    la.generate_draft("query", SOURCES)
    assert created["api_key"] == "openai-key"


@pytest.mark.xfail(
    reason="_call_gemini appends the API key as a URL query parameter, leaking it into logs and "
    "traces (llm_adapter.py:73)",
    strict=False,
)
def test_call_gemini_keeps_api_key_out_of_url(monkeypatch):
    created = _install_fake_httpx(monkeypatch, _FakeGeminiResponse({"candidates": []}))
    la._call_gemini("s", "u", "TOP-SECRET-KEY", "gemini-2.0-flash")
    url, _payload, _headers = created["client"].posts[0]
    assert "TOP-SECRET-KEY" not in url


@pytest.mark.xfail(
    reason="the {model} placeholder in GEMINI_REST_URL is never substituted, so every Gemini "
    "request targets a literal /models/{model}:generateContent endpoint (llm_adapter.py:73)",
    strict=False,
)
def test_call_gemini_substitutes_model_into_url(monkeypatch):
    created = _install_fake_httpx(monkeypatch, _FakeGeminiResponse({"candidates": []}))
    la._call_gemini("s", "u", "key-123", "gemini-2.0-flash")
    url, _payload, _headers = created["client"].posts[0]
    assert "gemini-2.0-flash:generateContent" in url


@pytest.mark.xfail(
    reason="_mock_draft stringifies a null content value to 'None' and publishes it as evidence "
    "in the draft (llm_adapter.py:125)",
    strict=False,
)
def test_generate_draft_mock_ignores_null_content(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "mock")
    out = la.generate_draft("query", [{"title": "T", "content": None}])
    assert out["generated"] is False
    assert out["text"] is None
    assert out["reason"] == "No sources to mock-draft from"
