"""
Text cleanup + deduplication for ingested corpus documents.
"""

import re
import unicodedata
from typing import Any

_BOILERPLATE = re.compile(
    r"(navigation menu|skip to content|privacy policy|terms of use|cookies|"
    r"©20\d{2}|copyright \d{4}|all rights reserved|site map|search search|"
    r"sign in|sign up|subscribe to our|share this page)+",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    """Fold unicode, strip boilerplate, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u200b", " ").replace("\xa0", " ")
    text = _BOILERPLATE.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def dedupe_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop duplicate documents sharing the same source + content hash."""
    seen = set()
    out: list[dict[str, Any]] = []
    for doc in documents:
        key = (doc.get("source", ""), doc.get("content_hash", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(doc)
    return out