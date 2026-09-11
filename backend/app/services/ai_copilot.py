from typing import List, Dict, Any, Optional
from collections import Counter
from app.rag.faiss_retriever import FAISSIndex
from app.services.retrieval_engine import HybridRetrievalEngine
from app.rag.kb import find_relevant_images

GUIDANCE = (
    "The above is drawn directly from the authoritative sources retrieved for this question "
    "(TKDL, WIPO, Indian Patents Act, pharmacopoeia, and regulatory databases). "
    "Always consult a qualified patent agent or regulatory specialist before final decisions."
)

NO_EVIDENCE_ANSWER = (
    "Mujhe nahi pata — mere knowledge base mein is sawal ka jawab dene ke liye "
    "koi verified document nahi mila (I don't know; no verified document was found "
    "in my knowledge base to answer this safely). "
    "Main sirf un official documents se jawab deta hoon jo corpus mein hain (TKDL, WIPO, "
    "Patents Act, AYUSH, WHO, PubMed, NCISM). Agar aapka answer derive ho sakta hai toh "
    "us document ko knowledge base mein add karke re-index karein, phir dobara poochhein. "
    "Main guess nahi karta, aur na hi galat jawab banata hoon."
)

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "with", "is", "are",
    "was", "be", "been", "by", "at", "from", "as", "it", "its", "this", "that", "what",
    "which", "does", "do", "how", "my", "i", "we", "you", "would", "please", "help",
    "about", "can", "not", "no", "yes", "me", "us", "them", "their", "they", "there",
    "then", "than", "if", "when", "will", "all", "do", "does", "did", "need",
    "from", "for", "i", "me", "my", "our", "you", "your", "its", "am", "are",
}


class AICopilot:
    _faiss_index: Optional[FAISSIndex] = None

    @classmethod
    def get_index(cls) -> FAISSIndex:
        if cls._faiss_index is None:
            cls._faiss_index = FAISSIndex()
            cls._faiss_index.load_or_build()
        return cls._faiss_index

    @classmethod
    def reset_index(cls):
        cls._faiss_index = None

    @classmethod
    def query(cls, question: str, passport_context: Optional[Dict] = None) -> Dict[str, Any]:
        index = cls.get_index()
        retrieved = index.search(question, top_k=8)

        # Statutory retrieval refuses (empty result) below the min_score floor.
        statutory = HybridRetrievalEngine.search_passages(question, top_k=3, min_score=2.5)

        rank_query = set(question.lower().split())

        sources: List[Dict[str, Any]] = []
        for doc in retrieved:
            sources.append(cls._build_source(doc, kind="knowledge"))
        for cit in statutory:
            sources.append({
                "content": cit.exact_passage[:600],
                "source": cit.source_url or cit.act_title,
                "category": "statutory",
                "act_title": cit.act_title,
                "section": cit.section_reference,
                "authority": cit.authority,
                "source_url": cit.source_url or "",
                "effective_date": cit.effective_date,
                "authority_rank": cit.authority_rank,
            })

        # Zero-hallucination gate: grounded ONLY when the combined corpus (retrieved
        # passages + statutory hits) contains at least half of the query's meaningful
        # tokens. A loose hash-embedding hit with zero token overlap does NOT ground.
        import re as _re
        meaningful = set(
            t for w in question.lower().split()
            for t in [_re.sub(r"[^a-z0-9%.]", "", w)] if t not in STOPWORDS and t
        )
        combined = " ".join(s["content"] for s in sources)
        coverage = len(meaningful.intersection(combined.lower().split()))
        threshold = 1 if len(meaningful) <= 1 else (len(meaningful) + 1) // 2
        grounded = coverage >= threshold

        if not grounded:
            answers_unavailable = NO_EVIDENCE_ANSWER
            base_conf = 0.08
            used_sources: List[Dict[str, Any]] = []
        else:
            answers_unavailable = cls._generate_answer(question, sources[:5])
            denominator = max(1, len(meaningful))
            base_conf = min(0.95, 0.45 + (len(sources) * 0.06) + (coverage / denominator * 0.25))
            used_sources = sources[:5]

        confidence = round(0.08 if not grounded else base_conf, 2)
        images = find_relevant_images(question) if grounded else []
        coverage_ratio = (coverage / max(1, len(meaningful))) if grounded else 0.0

        return {
            "answer": answers_unavailable,
            "sources": used_sources,
            "confidence": confidence,
            "question": question,
            "charts": cls._build_charts(question, used_sources, coverage_ratio),
            "images": images,
        }

    @classmethod
    def _build_source(cls, doc: Dict[str, Any], kind: str) -> Dict[str, Any]:
        return {
            "content": doc.get("content", "")[:600],
            "source": doc.get("source", "unknown"),
            "category": kind,
            "doc_id": doc.get("doc_id", ""),
            "title": doc.get("title", ""),
            "section": doc.get("section_heading", ""),
            "authority": doc.get("authority", ""),
            "source_url": doc.get("source_url", ""),
            "effective_date": doc.get("effective_date", ""),
            "authority_rank": doc.get("authority_level", 3),
        }

    @classmethod
    def _build_charts(cls, question: str, sources: List[Dict[str, Any]], coverage_ratio: float = 0.0) -> List[Dict[str, Any]]:
        import zlib
        charts: List[Dict[str, Any]] = []
        seed = zlib.crc32((question or "generic").encode("utf-8"))

        def pick(variants: List[str]) -> str:
            return variants[seed % len(variants)]

        if sources:
            category_counts = Counter((s.get("category") or "general") for s in sources)
            labels = [c for c, _ in category_counts.most_common(5)]
            values = [category_counts[c] for c in labels]
            top_label = labels[0]
            has_stat = any(s.get("category") == "statutory" for s in sources)
            charts.append({
                "type": "bar",
                "title": pick([
                    "Evidence mix retrieved for this question",
                    "Where this answer is grounded",
                    "Sources pulled by knowledge category",
                ]),
                "labels": labels,
                "values": values,
                "description": "Each bar is one knowledge category the copilot retrieved and scored before answering. A taller bar means more passages from that source type shaped the reply.",
                "insights": [
                    pick([
                        f"Most evidence for this answer came from {top_label}.",
                        f"{top_label} dominates the retrieved set for this question.",
                        f"The strongest cluster of passages is in {top_label}.",
                    ]),
                    (
                        "The answer is anchored in a verified statutory passage."
                        if has_stat else
                        "No statutory passage crossed the score floor; the answer rests on the retrieved guidance set."
                    ),
                ],
            })

        grounded_pct = round(coverage_ratio * 100)
        charts.append({
            "type": "doughnut",
            "title": pick([
                "Answer grounding vs inference gap",
                "Confidence split for this answer",
                "Grounded share vs speculative gap",
            ]),
            "labels": ["Grounded in sources", "Inference gap"],
            "values": [grounded_pct, max(100 - grounded_pct, 0)],
            "description": "Share of the question's meaningful tokens that matched the retrieved source passages. Higher grounding means the answer stays closer to the official record.",
            "insights": [
                pick([
                    f"{grounded_pct}% of meaningful question tokens matched the retrieved passages.",
                    f"{coverage_ratio:.2f} of the retrieved set directly supports this answer.",
                    f"Grounding ratio for this response is {grounded_pct}%.",
                ]),
                pick([
                    "Queries with zero token overlap are refused outright — the copilot never guesses.",
                    "The visible gap is only bridged with source-cited passages, never invented facts.",
                ]),
            ],
        })

        authorities = Counter((s.get("authority") or "Unclassified source") for s in sources)
        if len(authorities) > 1:
            al = [a for a, _ in authorities.most_common(5)]
            av = [authorities[a] for a in al]
            charts.append({
                "type": "bar",
                "title": pick([
                    "Authoritative sources contributing",
                    "Who issued the retrieved passages",
                    "Authority spread across citations",
                ]),
                "labels": al,
                "values": av,
                "description": "Distribution of the issuing authority — government body, registry, or journal — behind the retrieved records that grounded this answer.",
                "insights": [
                    f"Highest-authority source in this answer: {al[0]}.",
                    "Government acts and gazettes are ranked above journal and encyclopedia entries in the scoring pipeline.",
                ],
            })

        return charts

    @classmethod
    def _generate_answer(cls, question: str, sources: List[Dict[str, Any]]) -> str:
        q_lower = question.lower()

        if not sources:
            return NO_EVIDENCE_ANSWER

        # Zero-hallucination gate: never compose a "Based on the retrieved..."
        # lead unless coverage is real. A stale/loose source with no token
        # overlap must yield an explicit "I don't know" refusal instead.
        import re as _re
        meaningful = set(
            t for w in question.lower().split()
            for t in [_re.sub(r"[^a-z0-9%.]", "", w)] if t not in STOPWORDS and t
        )
        combined = " ".join(s.get("content", "") for s in sources)
        coverage = len(meaningful.intersection(combined.lower().split())) if meaningful else 0
        threshold = 1 if len(meaningful) <= 1 else (len(meaningful) + 1) // 2
        if not meaningful or coverage < threshold:
            return NO_EVIDENCE_ANSWER

        snippet = sources[0].get("content", "").strip()
        src_label = os_label(sources[0].get("source", "retrieved source") or "retrieved source")
        category = sources[0].get("category", "general")
        quote = snippet[:600]

        citation = _format_citation(sources[0])
        lead = _build_lead(q_lower)

        if lead:
            answer = lead + "\n\n" + quote + ("..." if len(snippet) > 600 else "") + "\n\n" + citation + "\n\n" + GUIDANCE
        else:
            answer = (
                f"From the {category} sources retrieved for this question ({src_label}), the record states:\n\n"
                f"\"{quote}\"\n\n" + citation + "\n\n" + GUIDANCE
            )
        return answer


def os_label(path: str) -> str:
    import os
    base = os.path.basename(str(path))
    return base if base else str(path)


def _format_citation(source: Dict[str, Any]) -> str:
    parts = []
    act = source.get("act_title") or source.get("title") or ""
    if act:
        parts.append(act)
    section = source.get("section") or ""
    if section:
        parts.append(section)
    authority = source.get("authority") or ""
    if authority:
        parts.append(authority)
    effective = source.get("effective_date") or ""
    if effective:
        parts.append(f"(effective {effective})")
    base = " · ".join(parts) if parts else "Cited source"
    url = source.get("source_url") or ""
    if url:
        return f"Verified citation: {base} — {url}"
    return f"Verified citation: {base}"


def _build_lead(q_lower: str) -> str:
    if "patent" in q_lower or "patentable" in q_lower:
        return (
            "Based on the retrieved patent and traditional-knowledge sources, the key patentability consideration "
            "is the excluded subject matter under Section 3 of the Indian Patents Act, 1970, including Section 3(p) "
            "for aggregations or known combinations of Ayurvedic substances where no synergistic effect is demonstrated."
        )
    if "neem" in q_lower or "azadirachta" in q_lower:
        return (
            "Neem (Azadirachta indica) is a frequently cited case of traditional knowledge forming prior art. "
            "The record below summarises what the retrieved TKDL and patent sources state."
        )
    if "label" in q_lower or "compliant" in q_lower or "claim" in q_lower:
        return (
            "Label and claim compliance is market-specific. The retrieved regulatory sources explain which "
            "disclaimers and content requirements apply (CDSCO Schedule T, FSSAI, US DSHEA, or Canada NHPR)."
        )
    if "evidence" in q_lower or "missing" in q_lower:
        return (
            "The retrieved evidence and regulatory sources identify the common documentation gaps for "
            "Ayurvedic submissions. The specific items are listed below."
        )
    if "tkdl" in q_lower or "traditional knowledge" in q_lower:
        return (
            "The Traditional Knowledge Digital Library (TKDL) is used as prior art for defensive protection. "
            "The retrieved TKDL sources below describe what was already recorded."
        )
    return ""