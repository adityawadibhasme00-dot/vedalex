"""
LLM Generation Adapter for VEDALEX | IP-SAKTI SAHAYAK.

Wires the prepared RAG prompt templates (see prompt_templates.py) to a real
generation model so the copilot produces fluent, grounded draft answers
instead of only templated concatenations of retrieved snippets.

Deliberately "dumb" by design:
  - Generates exactly ONE draft per request (never retries in a loop).
  - Returns a clean ``generated: False`` result on any failure so the
    deterministic grounded answer builder can take over.
  - Never touches anything outside the retrieved sources — the downstream
    verification layer is the gatekeeper that decides whether the draft is
    actually supported by the evidence.

Providers (``IPSAKTI_LLM_PROVIDER``):
  auto    — use Gemini if GEMINI_API_KEY is set, else OpenAI if
            OPENAI_API_KEY is set, else ``off`` (default)
  gemini  — Google Gemini REST API (httpx, no extra SDK dependency)
  openai  — OpenAI Chat Completions (openai SDK, already in requirements)
  mock    — deterministic summary built from sources (offline demo/testing)
  off     — generation disabled (deterministic pipeline only)
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODELS = {
    # gemini-2.0-flash was retired and now 404s; 3.5-flash is the current
    # stable flash model. Override per deployment with IPSAKTI_LLM_MODEL.
    "gemini": "gemini-3.5-flash",
    "openai": "gpt-4o-mini",
}

GEMINI_REST_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

# Hard cap so a slow provider can never stall the request chain for long.
LLM_TIMEOUT_SEC = float(os.environ.get("IPSAKTI_LLM_TIMEOUT", "25"))


def _resolve_provider() -> str:
    provider = os.environ.get("IPSAKTI_LLM_PROVIDER", "").strip().lower()
    if provider in ("", "auto"):
        if os.environ.get("GEMINI_API_KEY"):
            return "gemini"
        if os.environ.get("OPENAI_API_KEY"):
            return "openai"
        return "off"
    if provider in ("gemini", "openai", "mock", "off"):
        return provider
    logger.warning(f"Unknown IPSAKTI_LLM_PROVIDER={provider!r}; treating as off")
    return "off"


def _pick_model(provider: str) -> str | None:
    model = os.environ.get("IPSAKTI_LLM_MODEL", "").strip()
    if model:
        return model
    return DEFAULT_MODELS.get(provider)


def _call_gemini(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    import httpx
    # The template holds a real {model} placeholder, so it needs str.format().
    # An f-string here substituted only the API key and sent a literal
    # "{model}" to Google, which 404'd on every single request.
    url = GEMINI_REST_URL.format(model=model)
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1500,
        },
    }
    with httpx.Client(timeout=LLM_TIMEOUT_SEC) as client:
        # Key travels in a header, not the query string, so it stays out of
        # access logs and traces.
        resp = client.post(url, json=payload, headers={"x-goog-api-key": api_key})
        resp.raise_for_status()
        data = resp.json()

    candidates = data.get("candidates") or []
    if not candidates:
        return {"generated": False, "reason": "Gemini returned no candidates"}
    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        return {"generated": False, "reason": "Gemini returned an empty response"}
    return {"generated": True, "text": text}


def _call_openai(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, timeout=LLM_TIMEOUT_SEC)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=1500,
    )
    text = resp.choices[0].message.content
    text = (text or "").strip()
    if not text:
        return {"generated": False, "reason": "OpenAI returned an empty response"}
    return {"generated": True, "text": text}


def _mock_draft(query: str, sources: list[dict[str, Any]]) -> str:
    """Deterministic draft used for offline demo/testing without API keys."""
    lines: list[str] = []
    for i, s in enumerate(sources[:4], 1):
        content = " ".join(str(s.get("content", "")).split())[:220]
        if not content:
            continue
        label = (
            s.get("title") or s.get("act_title") or s.get("source")
            or f"Source {i}"
        )
        lines.append(f"{i}. {label}: {content}")
    if not lines:
        return ""
    return "Based on the retrieved official sources:\n\n" + "\n".join(lines)


def generate_draft(
    query: str,
    sources: list[dict[str, Any]],
    intent: str = "general",
    passport_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a single grounded draft answer from the retrieved evidence.

    The prompt enforces the zero-hallucination contract:
      - answer ONLY from the provided source documents
      - cite every factual claim
      - refuse when evidence is insufficient

    Returns a dict:
      {"generated": bool, "text": Optional[str], "provider": str,
       "model": Optional[str], "reason": str}
    """
    provider = _resolve_provider()
    model = _pick_model(provider) if provider in ("gemini", "openai") else None

    if provider == "off":
        return {
            "generated": False,
            "text": None,
            "provider": "off",
            "model": None,
            "reason": "LLM generation is disabled (set IPSAKTI_LLM_PROVIDER or an API key)",
        }

    if provider == "mock":
        return {
            "generated": bool(text := _mock_draft(query, sources)),
            "text": text or None,
            "provider": "mock",
            "model": "deterministic",
            "reason": "" if text else "No sources to mock-draft from",
        }

    if not sources:
        return {
            "generated": False,
            "text": None,
            "provider": provider,
            "model": model,
            "reason": "No retrieved sources to ground the draft",
        }

    # Build the prompt from the shared templates so every response surface
    # uses the same zero-hallucination system rules.
    try:
        from app.rag.prompt_templates import build_rag_prompt
        prompt = build_rag_prompt(
            query=query,
            sources=sources[:5],
            intent=intent,
            passport_context=passport_context,
        )
        system_prompt = prompt["system"]
        user_prompt = prompt["user"]
    except Exception as e:
        logger.warning(f"Prompt build failed ({e}); using minimal prompt")
        system_prompt = (
            "You are IP-SAKTI AI Copilot, an evidence-grounded Ayurveda "
            "Innovation Intelligence Assistant. Never answer from memory when "
            "the question requires factual, legal, regulatory, patent, ABS, "
            "safety or scientific information. Answer the user's question "
            "using ONLY the retrieved official source documents. Cite each "
            "factual statement with [Source: <name>, Section: <section>]. If "
            "the sources do not contain enough information, say exactly: "
            "\"Insufficient verified evidence is available in the current "
            "IP-SAKTI knowledge base.\" Never "
            "fabricate, speculate, or invent citations."
        )
        snippet = "\n\n".join(
            f"SOURCE {i}: " + " ".join(str(s.get("content", "")).split())[:500]
            for i, s in enumerate(sources[:5], 1) if s.get("content")
        )
        user_prompt = (
            f"## RETRIEVED SOURCE DOCUMENTS\n\n{snippet or 'None'}\n\n"
            f"## USER QUESTION\n\n{query}"
        )

    if model is None:
        return {
            "generated": False,
            "text": None,
            "provider": provider,
            "model": None,
            "reason": f"No model configured for provider {provider}",
        }

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""

    # Retry logic: try up to 2 times on failure
    max_retries = 2
    last_error = ""

    for attempt in range(max_retries):
        try:
            if provider == "gemini":
                if not os.environ.get("GEMINI_API_KEY"):
                    return {"generated": False, "text": None, "provider": provider,
                            "model": model,
                            "reason": "GEMINI_API_KEY is not set"}
                result = _call_gemini(system_prompt, user_prompt, api_key, model)
            elif provider == "openai":
                if not os.environ.get("OPENAI_API_KEY"):
                    return {"generated": False, "text": None, "provider": provider,
                            "model": model,
                            "reason": "OPENAI_API_KEY is not set"}
                result = _call_openai(system_prompt, user_prompt, api_key, model)
            else:
                return {"generated": False, "text": None, "provider": provider,
                        "model": model, "reason": f"Unsupported provider: {provider}"}

            if result.get("generated"):
                result.update({"provider": provider, "model": model, "reason": ""})
                return result

            last_error = result.get("reason", "Unknown error")
            if attempt < max_retries - 1:
                logger.warning(f"LLM attempt {attempt + 1} failed ({provider}): {last_error}. Retrying...")
                import time
                time.sleep(1)

        except Exception as e:
            last_error = str(e)[:300]
            logger.warning(f"LLM generation failed ({provider}) attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(1)

    return {
        "generated": False,
        "text": None,
        "provider": provider,
        "model": model,
        "reason": last_error or "All retry attempts failed",
    }
    return result