import os
import re
from typing import Any

# Legal / regulatory terms that must NEVER be machine-translated, because a
# translated citation (e.g. "Section 3(p)" -> Hindi "धारा 3(p)") would break
# citation validation and statute lookups downstream. They are extracted before
# translation, replaced with placeholders, and restored after.
LEGAL_TERM_PATTERNS: list[str] = [
    r"Section\s+\d+[A-Za-z]?(?:\(\s*[A-Za-z0-9]+\s*\))?",
    r"Rule\s+\d+(?:\(\s*[0-9]+\s*\))?",
    r"Schedule\s+[A-Z]",
    r"(?:Patents|Drugs|Biological\s+Diversity|Copyright|Trade\s+[Mm]arks?)\s+Act(?:,\s*\d{4})?",
    r"(?:Biological\s+Diversity\s+Rules|Drugs\s+and\s+Cosmetics\s+Rules)\s+\d{4}",
    r"First\s+Schedule",
    r"Issue\s+No\.[A-Za-z0-9]+",
]
LEGAL_ACRONYMS: list[str] = [
    "TKDL", "NBA", "SBB", "ABS", "RIAF", "FDA", "CDSCO", "FSSAI", "AYUSH",
    "ASU", "CCReM", "IP", "GI", "TM", "PCT", "TRIPS", "GRATK", "WIPO", "WHO",
    "EPA", "USPTO", "WTO", "BDA", "D&C", "DPDP", "WHO", "GATT", "APC", "NMPB",
    "API", "GMP", "CAS", "ISO", "NABL", "NLT",
]


class BhashiniClient:
    """
    Bhashini / AI4Bharat translation adapter (blueprint: multilingual pipeline).

    Enabled only when IPSAKTI_BHASHINI_API_KEY is set. It translates the user's
    query to English for retrieval and the final answer back to the user's
    language, preserving legal citations and statute acronyms verbatim.

    If the API is not configured or a call fails, the client degrades silently:
    translate() returns None and callers keep the original text (the existing
    regex/script-range + glossary fallback continues to work).
    """

    API_URL = os.environ.get(
        "IPSAKTI_BHASHINI_API_URL",
        "https://api.bhashini.gov.in/v1/model/compute",
    )
    DEFAULT_SERVICE = "ai4bharat/indictrans-v2-all-gpu--t4"

    _acronym_scanner = re.compile(r"\b(" + "|".join(sorted(LEGAL_ACRONYMS, key=len, reverse=True)) + r")\b")

    @classmethod
    def is_enabled(cls) -> bool:
        return bool(os.environ.get("IPSAKTI_BHASHINI_API_KEY") and os.environ.get("IPSAKTI_BHASHINI_USER_ID"))

    @classmethod
    def mask_legal_terms(cls, text: str) -> tuple[str, list[str]]:
        """Return (masked_text, legal_terms) — legal terms replaced by
        ASCII-safe tokens `@@N@@` so a translation model won't mangle them."""
        masked = text
        terms: list[str] = []
        patterns = [cls._acronym_scanner] + [re.compile(p, re.IGNORECASE) for p in LEGAL_TERM_PATTERNS]
        [None] * len(patterns)
        for pattern in patterns:
            def _repl(m):
                terms.append(m.group(0))
                return f"@@{len(terms)}@@"
            masked = pattern.sub(_repl, masked)
        return masked, terms

    @staticmethod
    def unmask_legal_terms(translated: str, terms: list[str]) -> str:
        if not terms:
            return translated
        out = translated
        for i, term in enumerate(terms, start=1):
            out = out.replace(f"@@{i}@@", term)
        return out

    @classmethod
    def translate(cls, text: str, source_lang: str, target_lang: str) -> str | None:
        """Translate text between Bhashini-supported Indic languages and English.
        Returns None (caller keeps original) when the API is unavailable."""
        if not text or not text.strip():
            return None
        if source_lang == target_lang or not cls.is_enabled():
            return None
        if source_lang in ("mr", "hi", "ta", "te", "kn", "bn", "gu", "ml", "sa") and target_lang == "en":
            pass
        elif target_lang in ("mr", "hi", "ta", "te", "kn", "bn", "gu", "ml", "sa") and source_lang == "en":
            pass
        else:
            return None

        masked, terms = cls.mask_legal_terms(text)
        payload: dict[str, Any] = {
            "pipelineTasks": [
                {
                    "taskType": "translation",
                    "config": {
                        "language": {"sourceLanguage": source_lang, "targetLanguage": target_lang},
                        "serviceId": cls.DEFAULT_SERVICE,
                    },
                }
            ],
            "inputData": {"input": [{"source": masked}]},
        }
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": os.environ.get("IPSAKTI_BHASHINI_API_KEY", ""),
            "X-User-ID": os.environ.get("IPSAKTI_BHASHINI_USER_ID", ""),
        }
        try:
            import requests
            resp = requests.post(cls.API_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            translated = cls._parse_response(data, target_lang)
        except Exception:
            return None
        if not translated:
            return None
        return cls.unmask_legal_terms(translated, terms)

    @staticmethod
    def _parse_response(data: dict, target_lang: str) -> str | None:
        try:
            for task in data.get("pipelineResponse", []):
                for out in task.get("output", []):
                    if out.get("target"):
                        return out["target"]
            # Alternate response shape used by the ULCA compute contract.
            output = data.get("output", [])
            if isinstance(output, list) and output:
                first = output[0]
                translated = first.get("target") or first.get("translation") or first.get("text")
                if translated:
                    return translated
        except Exception:
            return None
        return None

    @classmethod
    def translate_query_to_english(cls, question: str, source_lang: str) -> str | None:
        if source_lang == "en":
            return None
        return cls.translate(question, source_lang, "en")

    @classmethod
    def translate_answer_to_lang(cls, text: str, target_lang: str) -> str | None:
        if target_lang == "en":
            return None
        return cls.translate(text, "en", target_lang)

    @classmethod
    def status(cls) -> dict[str, object]:
        return {
            "enabled": cls.is_enabled(),
            "provider": "Bhashini / AI4Bharat (IndicTrans-v2)" if cls.is_enabled() else "regex/glossary fallback",
            "api_url": cls.API_URL,
        }