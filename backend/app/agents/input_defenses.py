"""Security pack B1 + B2 — input defenses for every user query.

Runs BEFORE any LLM call or retrieval:

- ``redact_pii`` (B1): Aadhaar / Indian mobile / email / GSTIN are replaced
  with typed placeholders so raw identifiers never reach a model, log or
  embedding call.
- ``sanitize_injection`` (B2): jailbreak phrasing, fake role markers and
  chat-template smuggling are neutralised to ``[FILTERED]`` while the benign
  remainder of the query is preserved.
- ``InputDefenses.defend`` wraps both and optionally consults the
  ``sanitizer_prompt.txt`` judge; the deterministic pass is a sticky floor —
  the judge may add findings, never remove them (same doctrine as
  GuardrailJudge).

Rule R7 (retrieved context is DATA, not instructions) is enforced in two
places: ``app/prompts/rag_prompt.txt`` (generation) and GuardrailJudge's
``context_injection`` check (deterministic, offline).
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.base import AgentBase

_AADHAAR_RE = re.compile(r"\b(?:\d{4}[\s-]\d{4}[\s-]\d{4}|\d{12})\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_GSTIN_RE = re.compile(
    r"\b\d{2}[A-Za-z]{5}\d{4}[A-Za-z][1-9A-Za-z]Z[0-9A-Za-z]\b"
)
_PHONE_RE = re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b")

_PII_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("email", _EMAIL_RE, "[EMAIL]"),
    ("gstin", _GSTIN_RE, "[GSTIN]"),
    ("aadhaar", _AADHAAR_RE, "[AADHAAR]"),
    ("phone", _PHONE_RE, "[PHONE]"),
)

INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ignore_instructions",
        re.compile(
            r"ignore\s+(?:all\s+|any\s+|the\s+|your\s+|these\s+)?"
            r"(?:previous|prior|above|earlier|preceding|system)\s+"
            r"(?:instructions?|rules?|prompts?|messages?)",
            re.IGNORECASE,
        ),
    ),
    (
        "disregard_instructions",
        re.compile(
            r"disregard\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)?"
            r"\s*(?:instructions?|rules?|prompts?)",
            re.IGNORECASE,
        ),
    ),
    (
        "forget_context",
        re.compile(
            r"forget\s+(?:everything|all\s+(?:previous|prior)|the\s+above)",
            re.IGNORECASE,
        ),
    ),
    (
        "role_override",
        re.compile(
            r"you\s+are\s+now\s+(?:a|an|the)\s+"
            r"(?:unrestricted|uncensored|jailbroken|different|new|no\s+longer)"
            r"\b[^\n.?!]*",
            re.IGNORECASE,
        ),
    ),
    (
        "reveal_system",
        re.compile(
            r"\b(?:reveal|print|show|repeat|dump|display)\s+"
            r"(?:your|the|this|all)\s+(?:hidden\s+|system\s+)?"
            r"(?:prompt|instructions?|rules?)",
            re.IGNORECASE,
        ),
    ),
    ("system_prompt", re.compile(r"\bsystem\s+prompt\b", re.IGNORECASE)),
    (
        "jailbreak_mode",
        re.compile(r"\b(?:developer|jailbreak|dan)\s+mode\b", re.IGNORECASE),
    ),
    (
        "unrestricted_roleplay",
        re.compile(
            r"act\s+as\s+(?:an?\s+)?"
            r"(?:unrestricted|uncensored|jailbroken|unfiltered|evil)\b[^\n.?!]*",
            re.IGNORECASE,
        ),
    ),
    (
        "fake_role_marker",
        re.compile(r"(?:^|\n)\s*(?:system|assistant|developer|user)\s*:", re.IGNORECASE),
    ),
    (
        "chat_template",
        re.compile(r"\[INST\]|<<\s*sys\s*>>|<\|im_start\|>|<<SYS>>", re.IGNORECASE),
    ),
    (
        "override_guard",
        re.compile(
            r"\boverride\s+(?:your\s+|the\s+|all\s+)?"
            r"(?:instructions?|rules?|guardrails?|safety)",
            re.IGNORECASE,
        ),
    ),
    (
        "dont_obey",
        re.compile(
            r"\b(?:do\s+not|don't|never)\s+(?:follow|obey|listen\s+to)\s+"
            r"(?:the\s+|your\s+|any\s+)?(?:previous|prior|system|above|initial)",
            re.IGNORECASE,
        ),
    ),
)


def redact_pii(text: str) -> tuple[str, dict[str, int]]:
    """Replace PII identifiers with typed placeholders; returns counts."""
    redacted = text or ""
    counts: dict[str, int] = {}
    for label, pattern, token in _PII_PATTERNS:
        redacted, n = pattern.subn(token, redacted)
        if n:
            counts[label] = counts.get(label, 0) + n
    return redacted, counts


def find_injections(text: str) -> list[str]:
    """Labels of every injection pattern that matches ``text``."""
    found: list[str] = []
    for label, pattern in INJECTION_PATTERNS:
        if label not in found and pattern.search(text or ""):
            found.append(label)
    return found


def sanitize_injection(text: str) -> tuple[str, list[str]]:
    """Neutralise injection spans to [FILTERED]; keeps benign remainder."""
    cleaned = text or ""
    found: list[str] = []
    for label, pattern in INJECTION_PATTERNS:
        cleaned, n = pattern.subn("[FILTERED]", cleaned)
        if n and label not in found:
            found.append(label)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned, found


def defend_query(text: str) -> dict[str, Any]:
    """Full deterministic defense: PII redaction then injection sanitation."""
    original = text or ""
    redacted, pii_counts = redact_pii(original)
    cleaned, injections = sanitize_injection(redacted)
    return {
        "query": cleaned,
        "pii_redacted": pii_counts,
        "injections_neutralized": injections,
        "changed": cleaned != original,
    }


class InputDefenses(AgentBase):
    """B1 + B2 wrapper with the optional sanitizer judge."""

    name = "input_defenses"
    prompt_file = "sanitizer_prompt.txt"

    def defend(self, query: str) -> dict[str, Any]:
        """Deterministic defense first; judge may add, never remove."""
        deterministic = defend_query(query)
        if not deterministic["changed"]:
            return deterministic
        judged = self.llm_json(
            f"Query:\n{deterministic['query']}",
            fallback=deterministic,
        )
        merged = dict(deterministic)
        extra = [
            str(label)
            for label in (judged.get("injections") or [])
            if str(label) not in merged["injections_neutralized"]
        ]
        if extra:
            merged["injections_neutralized"] = (
                merged["injections_neutralized"] + extra
            )
        return merged
