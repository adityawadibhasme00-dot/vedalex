import difflib
import json
import os
import unicodedata
from typing import Dict, List, Any, Optional, Tuple

from app.models.intelligence import TerminologyMapResponse

_KNOWLEDGE = os.path.join(os.path.dirname(__file__), "..", "knowledge")

TRANSLITERATIONS: Dict[str, List[str]] = {
    "ING-ASHWAGANDHA": ["Aśvagandhā", "Aśvagandha", "Ashwagandha", "Ashvagandha", "Withania somnifera"],
    "ING-BRAHMI": ["Brāhmī", "Brahmi", "Bacopa monnieri", "Nīlabrāhmī"],
    "ING-SHANKHAPUSHPI": ["Śaṅkhapuṣpī", "Shankhapushpi", "Shankhpushpi", "Shankha-pushpi", "Convolvulus pluricaulis"],
    "ING-HARIDRA": ["Haridrā", "Haridra", "Haldi", "Halad", "Curcuma longa"],
    "ING-TULSI": ["Tulasī", "Tulasi", "Tulsi", "Ocimum sanctum", "Ocimum tenuiflorum", "Holy basil"],
}


class TerminologyMapper:
    """
    Terminology Mapper for a Retrieval-Augmented Genalpha pipeline.
    Resolves the many names of an Ayurvedic botanical (script native names, IAST
    transliterations, regional synonyms, botanical binomials) to a single canonical
    entity key — the same canonical_id consumed by the passport and RAG index.
    """

    _synonyms: Dict[str, Dict[str, Any]] = {}
    _monographs: Dict[str, Dict[str, Any]] = {}
    _alias_lookup: Dict[str, str] = {}
    _alias_surface: List[str] = []

    @classmethod
    def load_data(cls):
        if cls._alias_lookup:
            return
        if not cls._synonyms:
            path = os.path.join(_KNOWLEDGE, "botanical_synonyms.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._synonyms = json.load(f)
        if not cls._monographs:
            path = os.path.join(_KNOWLEDGE, "api_monographs.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    for item in json.load(f):
                        cls._monographs[item["canonical_id"]] = item

        for cid, entry in cls._synonyms.items():
            for lang, names in entry.items():
                if lang in ("canonical_id", "botanical_name"):
                    continue
                for name in names:
                    key = cls._norm(name)
                    if key:
                        cls._alias_lookup[key] = cid
            cls._alias_lookup[cls._norm(entry.get("botanical_name", ""))] = cid
            for t in TRANSLITERATIONS.get(cid, []):
                cls._alias_lookup[cls._norm(t)] = cid
        cls._alias_surface = sorted(set(cls._alias_lookup.keys()))

    @staticmethod
    def _norm(text: str) -> str:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        return text.strip().lower()

    @classmethod
    def map(cls, query: str) -> TerminologyMapResponse:
        cls.load_data()
        norm_q = cls._norm(query)
        matched = False
        matched_via = "none"
        canonical_id = None

        if norm_q:
            cid = cls._alias_lookup.get(norm_q)
            if cid:
                matched = True
                matched_via = "exact"
                canonical_id = cid
            else:
                close = difflib.get_close_matches(norm_q, cls._alias_surface, n=5, cutoff=0.62)
                if close:
                    matched = True
                    matched_via = "fuzzy"
                    canonical_id = cls._alias_lookup[close[0]]

        entry = cls._synonyms.get(canonical_id or "", {})
        monograph = cls._monographs.get(canonical_id or "", {})

        names: Dict[str, List[str]] = {}
        for lang, lst in entry.items():
            if lang in ("canonical_id", "botanical_name"):
                continue
            names[lang] = lst

        nearest_possible: List[str] = []
        if not canonical_id:
            close = difflib.get_close_matches(norm_q, cls._alias_surface, n=3, cutoff=0.45)
            nearest_possible = [s for s in close]

        rag_hint = (
            f"Canonical entity: {canonical_id} — use this key as the RAG metadata filter "
            f"(botanical_name, api_monograph_id, family) to scope retrieval chunks."
            if canonical_id
            else "No canonical entity matched — run the spelling transliteration or treat the term as out-of-vocabulary before retrieval."
        )

        return TerminologyMapResponse(
            query=query,
            matched=matched,
            matched_via=matched_via,
            canonical_id=canonical_id,
            botanical_name=monograph.get("botanical_name") or entry.get("botanical_name"),
            api_monograph_id=monograph.get("api_monograph_id"),
            family=monograph.get("family"),
            classical_uses=monograph.get("classical_therapeutic_uses", []),
            names=names,
            transliterations=TRANSLITERATIONS.get(canonical_id or "", []),
            nearest_possible=nearest_possible,
            rag_hint=rag_hint,
            source="API monographs · botanical synonyms · IAST transliteration set",
        )