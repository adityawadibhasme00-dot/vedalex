"""Legal/Ayurveda bilingual glossary (EN <-> HI) lookup.

Grounds legal terms to their canonical Hindi renderings so the copilot can
attach a glossary-verified bilingual term to answers. Loads once from
``app/knowledge/legal_glossary.json``.

Legal terminology carries statutory meaning; glossary terms are an aid, never
a substitute for the official Hindi text of a statute.
"""

import json
import os
import re


class LegalGlossary:
    glossary_path = os.path.join(
        os.path.dirname(__file__), "..", "knowledge", "legal_glossary.json"
    )
    _data: dict[str, dict] = {}

    @classmethod
    def load(cls) -> None:
        if cls._data:
            return
        if os.path.exists(cls.glossary_path):
            with open(cls.glossary_path, encoding="utf-8") as fh:
                cls._data = json.load(fh).get("terms", {})

    @classmethod
    def terms(cls) -> dict[str, dict]:
        cls.load()
        return cls._data

    @classmethod
    def lookup(cls, term_en: str) -> dict | None:
        """Exact lookup by glossary key (snake_case) or English term."""
        cls.load()
        key = term_en.strip().lower().replace(" ", "_").replace("-", "_")
        if key in cls._data:
            return cls._data[key]
        for entry in cls._data.values():
            if entry.get("en", "").lower() == term_en.strip().lower():
                return entry
        return None

    @classmethod
    def detect_glossary_terms(cls, text: str) -> list[tuple[str, dict]]:
        """Scan free text for glossary English terms. Returns (matched_term, entry)."""
        cls.load()
        lower = text.lower()
        hits: list[tuple[str, dict]] = []
        for _key, entry in cls._data.items():
            en_term = entry.get("en", "")
            if not en_term:
                continue
            # Boundary-aware match on the multiword English term.
            pattern = re.compile(rf"\b{re.escape(en_term)}\b", re.IGNORECASE)
            if pattern.search(lower) and entry not in [e for _, e in hits]:
                hits.append((en_term, entry))
        return hits

    @classmethod
    def to_hindi(cls, text: str) -> str:
        """Append bilingual glosses (EN → HI) for detected glossary terms.

        Returns the original text plus a trailing '\n[शब्दावली] hi_term (en_term)' block."""
        cls.load()
        hits = cls.detect_glossary_terms(text)
        if not hits:
            return text
        lines = ["", ""]
        for en_term, entry in hits:
            lines.append(f"{entry.get('hi', '')} ({en_term})")
        return text + "\n" + "\n".join(lines)

    @classmethod
    def describe(cls) -> dict[str, object]:
        cls.load()
        return {
            "available": bool(cls._data),
            "term_count": len(cls._data),
            "languages": ["en", "hi"],
            "sample_terms": list(cls._data.keys())[:8],
        }