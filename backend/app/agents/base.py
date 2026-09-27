"""Agentic RAG base infrastructure — Master Prompt v7.0.0, Phase 2.

Shared building blocks for the 12 agentic components:

- ``AgentContext``  — the context object the orchestrator passes to every
  downstream agent (jurisdiction, category, ingredients, language, ...).
- ``load_prompt``   — cached loader for ``backend/app/prompts/*.txt``.
- ``extract_json``  — tolerant JSON extraction from raw LLM output.
- ``AgentBase``     — prompt loading + structured-JSON LLM call with a
  deterministic fallback so every agent works offline (provider ``off``).

The LLM plumbing deliberately reuses the existing ``app.rag.llm_adapter``
provider contract (``IPSAKTI_LLM_PROVIDER`` / Gemini / OpenAI) instead of
introducing a second one.
"""

from __future__ import annotations

import json
import logging
import os
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from app.rag import llm_adapter

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)
_BARE_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class AgentContext:
    """Context object maintained by the orchestrator and passed to agents."""

    language: str = "en"
    jurisdiction: str = "india"
    query_type: str = "GENERAL_LEGAL"
    needs_classifier: bool = False
    product_category: str | None = None
    product_name: str | None = None
    ingredients: list[str] = field(default_factory=list)
    prior_classifications: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentContext:
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@cache
def load_prompt(name: str) -> str:
    """Load and cache one prompt file from ``backend/app/prompts``."""
    path = PROMPTS_DIR / name
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Prompt file {name!r} is empty")
    return text


def extract_json(text: str) -> dict[str, Any] | None:
    """Pull the first JSON object out of raw LLM output.

    Handles fenced blocks (```json ... ```), prose-wrapped objects, and
    returns ``None`` when no parseable JSON object is present.
    """
    if not text or not text.strip():
        return None
    match = _FENCE_RE.search(text)
    candidate = match.group(1) if match else None
    if candidate is None:
        bare = _BARE_OBJECT_RE.search(text)
        candidate = bare.group(0) if bare else None
    if candidate is None:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class AgentBase:
    """Base class for agentic components: prompt file + JSON LLM call."""

    name: str = "agent"
    prompt_file: str = ""

    @property
    def system_prompt(self) -> str:
        if not self.prompt_file:
            return ""
        return load_prompt(self.prompt_file)

    def llm_json(self, user_prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
        """Call the configured LLM for a JSON decision.

        Always returns a dict: parsed JSON on success, ``fallback`` when the
        provider is off/misconfigured, the call fails, or the output is not
        valid JSON. Never raises — agents must stay deterministic offline.
        """
        provider = llm_adapter._resolve_provider()
        if provider not in ("gemini", "openai"):
            return deepcopy(fallback)
        model = llm_adapter._pick_model(provider)
        key_env = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
        api_key = os.environ.get(key_env, "").strip()
        if model is None or not api_key:
            return deepcopy(fallback)
        try:
            if provider == "gemini":
                result = llm_adapter._call_gemini(
                    self.system_prompt, user_prompt, api_key, model
                )
            else:
                result = llm_adapter._call_openai(
                    self.system_prompt, user_prompt, api_key, model
                )
        except Exception as exc:  # noqa: BLE001 — provider failures are expected
            logger.warning("Agent %s LLM call failed: %s", self.name, exc)
            return deepcopy(fallback)
        if not result.get("generated"):
            return deepcopy(fallback)
        parsed = extract_json(str(result.get("text") or ""))
        if parsed is None:
            logger.warning(
                "Agent %s returned non-JSON output; using fallback", self.name
            )
            return deepcopy(fallback)
        return parsed
