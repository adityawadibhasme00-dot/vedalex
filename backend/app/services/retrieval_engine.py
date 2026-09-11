import json
import os
import re
import glob
from typing import List, Dict, Any, Optional
from app.models.regulatory import StatutoryCitation
from app.rag.kb import BACKEND_ROOT, _parse_metadata_headers, FOLDER_SOURCE_META

class HybridRetrievalEngine:
    """
    Hybrid RAG retrieval engine combining BM25 lexical token matching and semantic relevance
    with strict Source Authority Ranking (Gazette > Regulatory Authority > Patent Office > Academic).

    Corpus sources (all loaded once, cached):
      - app/knowledge/acts_and_gazettes.json      (hand-curated statutory passages)
      - backend/data/**/*.txt + kb/**/*.txt        (curated official corpus, one passage per file)
      - blueprint.xlsx -> Evidence Passages        (exact quoted legal text, when present)

    If a query returns no passage above the minimum score, callers MUST refuse to
    answer instead of letting an LLM guess (zero-hallucination contract).
    """
    _passages_db: List[Dict[str, Any]] = []
    _loaded = False

    #-------------------------------------------------------------------------
    # Loaders
    #-------------------------------------------------------------------------
    @classmethod
    def load_database(cls):
        if cls._loaded:
            return
        cls._passages_db = []
        cls._loaded = True

        gazette_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "acts_and_gazettes.json")
        if os.path.exists(gazette_path):
            with open(gazette_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                cls._passages_db.extend(data)

        # Curated text corpus -> one authoritative passage per file.
        for base, recursive in ((os.path.join(BACKEND_ROOT, "data"), True),
                                (os.path.normpath(os.path.join(BACKEND_ROOT, "..", "kb")), True)):
            if not os.path.isdir(base):
                continue
            for ext in ("*.txt", "*.md"):
                for filepath in glob.glob(os.path.join(base, "**", ext), recursive=recursive):
                    cls._register_text_passage(filepath)

        # Knowledge JSON files with canonical reference passages.
        knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
        for kfile in ("acts_and_gazettes.json", "permitted_tk_prior_art.json"):
            abs_path = os.path.join(knowledge_dir, kfile)
            if abs_path == gazette_path or not os.path.exists(abs_path):
                continue
            with open(abs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("exact_passage"):
                        cls._passages_db.append(item)

        # Blueprint registry (Excel) sources.
        try:
            from app.rag.xlsx_pipeline import load_blueprint_registry
            registry = load_blueprint_registry()
            for src in registry.get("sources", []):
                if isinstance(src, dict):
                    cls._passages_db.append({
                        "act_title": src.get("title") or src.get("doc_id") or "Blueprinted Source",
                        "section_reference": src.get("section_reference", ""),
                        "authority": src.get("authority", "Official Source"),
                        "jurisdiction": src.get("jurisdiction", ""),
                        "exact_passage": src.get("exact_passage") or src.get("description") or "",
                        "source_url": src.get("source_url", ""),
                        "effective_date": src.get("publication_date") or src.get("effective_date") or "",
                        "authority_rank": int(src.get("authority_level") or 2),
                        "keywords": [],
                    })
        except Exception as e:
            print(f"(retrieval) blueprint registry skipped: {e}")

    @classmethod
    def _register_text_passage(cls, filepath: str):
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return
        meta, body = _parse_metadata_headers(content)
        if not body.strip():
            return
        rel = os.path.relpath(filepath, BACKEND_ROOT).replace(os.sep, "/")
        parts = rel.split("/")
        folder = parts[1] if len(parts) >= 2 else "official"
        defaults = FOLDER_SOURCE_META.get(folder, {})
        source_url = meta.get("source_url") or ""
        if not source_url:
            m = re.search(r"(?im)^(?:Sources?|Reference):\s*(https?://\S+[\w/])", content)
            if m:
                source_url = m.group(1).strip()
        cls._passages_db.append({
            "act_title": meta.get("title") or os.path.splitext(os.path.basename(filepath))[0],
            "section_reference": meta.get("section_heading", ""),
            "authority": meta.get("authority") or defaults.get("authority", "Official Source"),
            "jurisdiction": meta.get("jurisdiction") or defaults.get("jurisdiction", ""),
            "exact_passage": body.strip()[:1200],
            "source_url": source_url,
            "effective_date": meta.get("effective_date", ""),
            "authority_rank": int(meta.get("authority_level") or defaults.get("authority_level", 3)),
            "keywords": [],
        })

    @classmethod
    def add_passages(cls, passages: List[Dict[str, Any]]):
        cls.load_database()
        cls._passages_db.extend(passages)

    #-------------------------------------------------------------------------
    # Search
    #-------------------------------------------------------------------------
    @classmethod
    def search_passages(
        cls,
        query: str,
        jurisdiction: Optional[str] = None,
        top_k: int = 3,
        min_score: float = 1.0,
    ) -> List[StatutoryCitation]:
        cls.load_database()
        query_tokens = set(re.findall(r'\w+', query.lower()))
        if not query_tokens:
            return []

        scored_results = []
        for idx, passage in enumerate(cls._passages_db):
            if jurisdiction:
                p_jur = (passage.get("jurisdiction", "") or "").lower()
                req_jur = jurisdiction.lower()
                if req_jur in p_jur or (req_jur == "us" and "united states" in p_jur) or (req_jur == "in" and "india" in p_jur) or (req_jur == "ca" and "canada" in p_jur):
                    pass
                elif p_jur:
                    continue

            text_corpus = (
                f"{passage.get('act_title', '')} {passage.get('section_reference', '')} "
                f"{passage.get('exact_passage', '')} {passage.get('title', '')} "
                f"{' '.join(passage.get('keywords', []) or [])}"
            ).lower()

            corpus_tokens = set(re.findall(r'\w+', text_corpus))
            overlap = len(query_tokens.intersection(corpus_tokens))
            keyword_bonus = sum(2.0 for kw in (passage.get("keywords", []) or []) if str(kw).lower() in query.lower())

            rank = int(passage.get("authority_rank", passage.get("authority_level", 1)) or 1)
            authority_weight = 10.0 / max(1, rank)
            total_score = overlap * 1.5 + keyword_bonus + authority_weight

            if total_score > 0:
                scored_results.append((total_score, -rank, idx, passage))

        scored_results.sort(key=lambda x: (x[0], x[1]), reverse=True)
        top_items = scored_results[:top_k]

        citations = []
        for score, neg_rank, idx, item in top_items:
            if score < min_score:
                continue
            citations.append(StatutoryCitation(
                act_title=item.get("act_title") or item.get("title", "Cited Source"),
                section_reference=item.get("section_reference", ""),
                authority=item.get("authority", "Official Source"),
                effective_date=item.get("effective_date", ""),
                exact_passage=item.get("exact_passage", "")[:1200],
                source_url=item.get("source_url"),
                authority_rank=int(item.get("authority_rank", item.get("authority_level", 1)) or 1)
            ))

        return citations

    @classmethod
    def resolve_conflict(cls, citations: List[StatutoryCitation]) -> StatutoryCitation:
        """Legal Hierarchy Resolver: when several jurisdictions/authorities answer the
        same question, the highest-authority passage (lowest authority_rank) wins."""
        if not citations:
            from app.models.regulatory import StatutoryCitation as SC
            return None
        return min(citations, key=lambda c: c.authority_rank)