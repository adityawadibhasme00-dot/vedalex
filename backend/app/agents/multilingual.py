"""Component 10 — Multilingual Layer, Master Prompt v7.0.0.

Post-generation translation pass. Delegates to the EXISTING Bhashini adapter
(``BhashiniClient``), which masks statute names / citation tokens before
translation and restores them afterwards — exactly the preservation rule
required by ``multilingual_prompt.txt``.

Offline (no Bhashini keys): the answer is returned unchanged with an honest
note; legal caveats and citations are therefore never corrupted.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentBase
from app.services.bhashini_client import BhashiniClient

_NO_TRANSLATION_NOTE = (
    "Translation service unavailable — returning the original English answer "
    "with statute names and citations preserved."
)


class MultilingualLayer(AgentBase):
    """Component 10: answer → target language, citations untouched."""

    name = "multilingual"
    prompt_file = "multilingual_prompt.txt"

    def translate(
        self,
        text: str,
        target_lang: str = "en",
        source_lang: str = "en",
    ) -> dict[str, Any]:
        """Localise a final answer. ``target_lang`` ``en`` is a no-op."""
        target = (target_lang or "en").strip().lower()
        result: dict[str, Any] = {
            "text": text,
            "translated": False,
            "target_lang": target,
            "source_lang": source_lang,
            "provider": "none",
            "note": "",
            "citations_preserved": True,
        }
        if target in ("en", "english") or target == (source_lang or "").lower():
            result["note"] = "Target language matches answer language."
            return result

        if not BhashiniClient.is_enabled():
            result["provider"] = "off"
            result["note"] = _NO_TRANSLATION_NOTE
            return result

        translated = BhashiniClient.translate_answer_to_lang(text, target)
        if not translated:
            result["provider"] = "bhashini"
            result["note"] = _NO_TRANSLATION_NOTE
            return result

        result.update(
            {
                "text": translated,
                "translated": True,
                "provider": "bhashini",
                "note": (
                    "Statute names and citations preserved in English with "
                    "transliteration where applicable."
                ),
            }
        )
        return result
