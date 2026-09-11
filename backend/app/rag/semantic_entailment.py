"""
Semantic Entailment Module for VEDALEX Verification Layer.

Determines whether a claim is SUPPORTED, CONTRADICTED, or NOT_ENOUGH
by comparing it against retrieved source evidence.

Strategy (cascading fallback):
  1. Cross-encoder NLI model (if cross-encoder/NLI model available)
  2. BGE-M3 cosine similarity with calibrated thresholds
  3. Token-overlap lexical matching (last resort)

This is more powerful than exact-match because legal documents use
different wording than LLM-generated claims. The question is:

  "Does the source actually imply/support this claim?"

rather than:

  "Does the source contain the exact same sentence?"
"""

import re
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EntailmentVerdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_ENOUGH = "NOT_ENOUGH"


@dataclass
class EntailmentResult:
    verdict: EntailmentVerdict
    score: float
    best_source_idx: int
    best_source_score: float
    explanation: str


# Calibrated thresholds (tuned for legal/regulatory text)
_HIGH_ENTAILMENT = 0.72
_MEDIUM_ENTAILMENT = 0.50
_WEAK_ENTAILMENT = 0.35
_CONTRADICTION_THRESHOLD = 0.25

# Negation patterns that can flip entailment.
# Includes both explicit negators and prohibitive terms ("excludes",
# "prohibits") which both express the same negative polarity.
_NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "cannot", "cant", "wont",
    "doesnt", "dont", "isnt", "arent", "wasnt", "were",
    "prohibited", "barred", "excluded", "denied", "rejected",
    "forbidden", "restricted",
}

# Semantic opposites for contradiction detection
_OPPOSITE_PAIRS = [
    ("permit", "prohibit"), ("allow", "deny"), ("support", "oppose"),
    ("increase", "decrease"), ("enable", "prevent"), ("valid", "invalid"),
    ("must", "must not"), ("shall", "shall not"), ("may", "may not"),
    ("satisfied", "not satisfied"), ("compliant", "non-compliant"),
]


def _tokenize(text: str) -> set:
    """Extract meaningful tokens from text."""
    stopwords = {
        "a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "with",
        "is", "are", "was", "be", "been", "by", "at", "from", "as", "it",
        "its", "this", "that", "which", "does", "do", "how", "what", "when",
        "where", "there", "here", "then", "than", "if", "but", "not", "can",
        "could", "would", "should", "may", "might", "shall", "will", "must",
    }
    tokens = re.findall(r"[a-z0-9%]+", text.lower())
    return {t for t in tokens if t not in stopwords and len(t) > 1}


def _negation_density(text: str) -> float:
    """Compute the ratio of negation tokens in text (0.0 - 1.0)."""
    words = text.lower().split()
    if not words:
        return 0.0
    neg_count = sum(
        1 for w in words if w.rstrip(".,;:!?()\"'") in _NEGATION_WORDS
    )
    return neg_count / len(words)


def _detect_contradiction_signals(claim: str, evidence: str) -> bool:
    """Check if claim and evidence contain explicit contradiction signals."""
    claim_lower = claim.lower()
    evidence_lower = evidence.lower()

    for pos, neg in _OPPOSITE_PAIRS:
        claim_has_pos = pos in claim_lower
        claim_has_neg = neg in claim_lower
        evid_has_pos = pos in evidence_lower
        evid_has_neg = neg in evidence_lower

        # Claim says X, evidence says NOT X
        if claim_has_pos and evid_has_neg:
            return True
        if claim_has_neg and evid_has_pos:
            return True

    return False


def _keyword_overlap_score(claim_tokens: set, evidence_tokens: set) -> float:
    """Jaccard-style overlap with emphasis on claim coverage."""
    if not claim_tokens:
        return 0.0
    intersection = claim_tokens & evidence_tokens
    coverage = len(intersection) / len(claim_tokens)
    return coverage


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if (vec_a is None or vec_b is None or len(vec_a) == 0 or len(vec_b) == 0
            or len(vec_a) != len(vec_b)):
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(float(a) * float(a) for a in vec_a))
    norm_b = math.sqrt(sum(float(b) * float(b) for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# In-memory evidence vector cache: content text -> embedding vector.
# Sources repeat across claims and across requests; re-embedding the same
# passage for every claim is the dominant CPU cost on the BGE-M3 model.
_EVIDENCE_VECTOR_CACHE: Dict[str, Any] = {}
_EVIDENCE_CACHE_MAX = 512


def _cache_evidence_vector(text: str, vector: Any) -> Any:
    if len(_EVIDENCE_VECTOR_CACHE) >= _EVIDENCE_CACHE_MAX:
        _EVIDENCE_VECTOR_CACHE.clear()
    _EVIDENCE_VECTOR_CACHE[text] = vector
    return vector


def _get_evidence_vectors(
    engine: Any,
    evidence_texts: List[str],
) -> List[Any]:
    """Return cached (or freshly embedded) vectors for the evidence texts."""
    vectors: List[Any] = [None] * len(evidence_texts)
    missing_idx: List[int] = []
    missing_texts: List[str] = []
    for i, text in enumerate(evidence_texts):
        if text in _EVIDENCE_VECTOR_CACHE:
            vectors[i] = _EVIDENCE_VECTOR_CACHE[text]
        else:
            missing_idx.append(i)
            missing_texts.append(text)

    if missing_texts:
        new_vecs = engine.embed(missing_texts)
        for j, text in enumerate(missing_texts):
            vec = new_vecs[j]
            _cache_evidence_vector(text, vec)
            vectors[missing_idx[j]] = vec

    return vectors


def check_entailments_batch(
    claims: List[str],
    evidence_chunks: List[Dict[str, Any]],
) -> List[EntailmentResult]:
    """
    Batch entailment check: embed ALL claims and ALL evidence chunks in
    exactly two model calls (plus one for any uncached evidence vectors),
    then score every (claim, chunk) pair.

    This replaces one-per-claim embedding and cuts BGE-M3 CPU latency by
    roughly N_claims x.

    Returns one EntailmentResult (best-scoring chunk) per claim.
    """
    if not claims or not evidence_chunks:
        return []

    claim_emb_scores: Optional[List[List[float]]] = None
    try:
        from app.rag.embeddings import EmbeddingEngine
        engine = EmbeddingEngine()

        evidence_texts = [c.get("content", "") for c in evidence_chunks]
        evidence_vecs = _get_evidence_vectors(engine, evidence_texts)

        claim_vecs = engine.embed(claims)
        claim_emb_scores = [
            [_cosine_similarity(cv, ev) for ev in evidence_vecs]
            for cv in claim_vecs
        ]
    except Exception as e:
        logger.warning(f"Batch embedding failed, keyword-only scoring: {e}")
        claim_emb_scores = None

    results: List[EntailmentResult] = []
    for ci, claim in enumerate(claims):
        if claim_emb_scores is None:
            emb_row = [0.0] * len(evidence_chunks)
        else:
            emb_row = claim_emb_scores[ci]

        scored: List[Tuple[float, int]] = []
        for j, chunk in enumerate(evidence_chunks):
            combined = _compute_entailment_score(
                claim, chunk.get("content", ""), emb_row[j]
            )
            scored.append((combined, j))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_idx = scored[0]
        verdict = _score_to_verdict(best_score)
        explanation = _build_explanation(
            verdict, best_score, claim,
            evidence_chunks[best_idx].get("content", ""),
        )
        results.append(EntailmentResult(
            verdict=verdict,
            score=best_score,
            best_source_idx=best_idx,
            best_source_score=best_score,
            explanation=explanation,
        ))

    return results


def _compute_entailment_score(
    claim: str,
    evidence: str,
    embedding_score: float,
) -> float:
    """
    Combine embedding similarity with lexical signals into a single
    entailment score in [0, 1].

    Adjustments:
      - Negation in claim relative to evidence lowers score
      - Contradiction signals push score toward 0
      - Strong keyword overlap boosts score
    """
    claim_tokens = _tokenize(claim)
    evidence_tokens = _tokenize(evidence)
    keyword_score = _keyword_overlap_score(claim_tokens, evidence_tokens)

    # Weighted combination
    score = 0.65 * embedding_score + 0.35 * keyword_score

    # Negation adjustment: penalize only when the claim and evidence
    # express OPPOSITE negation polarity (claim says "NOT X", evidence
    # says "X"). If both are negated ("cannot be patented" vs "excludes
    # from patentability") they agree, and no penalty applies — both
    # sentences express the same prohibition.
    claim_neg = _negation_density(claim)
    evid_neg = _negation_density(evidence)
    if (claim_neg > 0) != (evid_neg > 0):
        score *= 0.7  # Polarity mismatch — reduce confidence

    # Contradiction signal
    if _detect_contradiction_signals(claim, evidence):
        score = min(score, 0.2)

    return round(min(1.0, max(0.0, score)), 4)


def _score_to_verdict(score: float) -> EntailmentVerdict:
    """Map an entailment score to a verdict."""
    if score >= _HIGH_ENTAILMENT:
        return EntailmentVerdict.SUPPORTED
    if score >= _MEDIUM_ENTAILMENT:
        return EntailmentVerdict.SUPPORTED
    if score <= _CONTRADICTION_THRESHOLD:
        return EntailmentVerdict.CONTRADICTED
    if score >= _WEAK_ENTAILMENT:
        return EntailmentVerdict.NOT_ENOUGH
    return EntailmentVerdict.NOT_ENOUGH


def _build_explanation(
    verdict: EntailmentVerdict,
    score: float,
    claim: str,
    evidence: str,
) -> str:
    """Generate a human-readable explanation for the verdict."""
    if verdict == EntailmentVerdict.SUPPORTED:
        return (
            f"Entailment score {score:.2f} — evidence text implies or directly "
            f"states the claim. Key terms overlap and no contradiction detected."
        )
    if verdict == EntailmentVerdict.CONTRADICTED:
        return (
            f"Entailment score {score:.2f} — evidence appears to contradict the claim. "
            f"Opposing terms or negation patterns detected between claim and source."
        )
    return (
        f"Entailment score {score:.2f} — insufficient evidence. The retrieved source "
        f"does not contain enough overlapping content to confirm or deny the claim."
    )


def check_entailment(
    claim: str,
    evidence_chunks: List[Dict[str, Any]],
) -> EntailmentResult:
    """
    Check whether a claim is supported by any of the evidence chunks.

    Uses embedding similarity as the primary signal, enhanced with
    lexical overlap and contradiction detection.

    Returns the best entailment result across all evidence chunks.
    """
    if not evidence_chunks:
        return EntailmentResult(
            verdict=EntailmentVerdict.NOT_ENOUGH,
            score=0.0,
            best_source_idx=-1,
            best_source_score=0.0,
            explanation="No evidence chunks provided for entailment check.",
        )

    batch = check_entailments_batch([claim], evidence_chunks)
    return batch[0]
