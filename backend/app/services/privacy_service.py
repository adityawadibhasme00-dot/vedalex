"""Privacy layer for IP-SAKTI — DPDP-aligned scrubbing, consent gating and
audit hashing for chat/product data.

Design principles implemented from the product spec:
  - Data minimisation: only non-sensitive derived values are persisted
    (hashed query, source IDs, confidence) unless the user opts in to store
    the full formulation details.
  - Purpose limitation: audit log stores hashes + citation IDs, never raw
    formulation text.
  - Consent gate: chat persistence requires an explicit opt-in flag.
"""

import hashlib
import re
import time
from typing import Any

_SENSITIVE_PATTERNS = (
    r"\b\d{4}\s*[-/]?\s*\d{4}\s*[-/]?\s*\d{4}\s*[-/]?\s*\d{4}\b",  # card-style numbers
    r"\b\d{10,}\b",                       # long numeric strings (UID/mobile)
    r"\b[2-9]\d{9}\b",                    # 10-digit phone numbers
    r"[\w.+-]+@[\w-]+\.[\w.]+",           # emails
    r"\b\d{6}\b",                         # postal codes
    r"%(?=\s*\d)",                        # concentration percentages
    r"\b\d+(\.\d+)?\s*(mg|g|kg|ml|l|µg|mcg|gm)\b",  # quantities
    r"\b(?:¥|₹|\$|€|£)\s?\d[\d,.]*",     # currency amounts
)


def _hash(value: str, salt: str | None = None) -> str:
    raw = f"{salt or ''}:{value}".encode()
    return hashlib.sha256(raw).hexdigest()


def scrub_text(text: str) -> str:
    """Remove PII and sensitive formulation details (quantities, amounts,
    identifiers) while preserving legal/technical wording for auditability."""
    if not text:
        return ""
    scrubbed = text
    for pattern in _SENSITIVE_PATTERNS:
        scrubbed = re.sub(pattern, "[REDACTED]", scrubbed, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", scrubbed).strip()


def hash_audit_token(text: str) -> str:
    """Stable, salted query fingerprint used for audit correlation."""
    return _hash(scrub_text(text or ""), salt="ipsakti-audit-v1")


class QueryAuditLog:
    """In-memory audit trail of (query-hash, source-ids, citations, answer-hash).
    The raw question/answer text is never retained unless opt_in_store is true."""

    _log: list[dict[str, Any]] = []

    @classmethod
    def record(
        cls,
        query_hash: str,
        answer_hash: str,
        source_ids: list[str],
        citation_ids: list[str],
        jurisdiction: str | None,
        confidence: float | None,
        language: str | None,
        user_id: str | None = None,
        opt_in_store: bool = False,
    ) -> dict[str, Any]:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "query_hash": query_hash,
            "answer_hash": answer_hash,
            "source_ids": source_ids or [],
            "citation_ids": citation_ids or [],
            "jurisdiction": jurisdiction,
            "confidence": confidence,
            "language": language,
            "user_hash": _hash(user_id or "-", salt="ipsakti-user-v1"),
            "stored_full_record": opt_in_store,
        }
        cls._log.append(entry)
        return entry

    @classmethod
    def get_trail(cls, limit: int = 50) -> list[dict[str, Any]]:
        return cls._log[-limit:]

    @classmethod
    def reset(cls) -> None:
        cls._log = []