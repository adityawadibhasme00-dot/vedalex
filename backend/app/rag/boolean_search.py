"""Boolean Search engine (Eureka-style Boolean Search 1..5).

Adds a deterministic, operator-based retrieval layer over the full local
retrieval corpus. Unlike pure semantic search it lets an operator (or the
Novelty Search workflow) express precise queries:

    expression := or_expr
    or_expr    := and_expr (OR and_expr)*
    and_expr   := not_expr (AND not_expr)*
    not_expr   := NOT not_expr | near_expr
    near_expr  := term (NEAR/n term)*
    term       := word | "phrase" | field:value | ( or_expr )

Supported fields: patent_number, jurisdiction, year, date, assignee,
title, source, act, collection.

Also exposes :func:`build_searches`, which turns a natural-language technical
description into the five boolean strategies shown in Eureka's Search
Strategy panel (core-AND, synonym OR-groups, statutory/classification,
phrase + recency, broad recall), each with its readable formula and hits.
"""

import json
import logging
import os
import re
from typing import Any

from app.core.cache import get_cache

logger = logging.getLogger(__name__)

_FIELD_ALIASES = {
    "patent_number": ("patent_number", "publication_number", "doc_id", "document_id", "patent_id"),
    "jurisdiction": ("jurisdiction", "country_code"),
    "year": ("publication_year", "year", "publication_date", "date", "effective_date"),
    "assignee": ("assignee", "current_assignee", "assignees", "applicant", "filer"),
    "title": ("title", "act_title", "heading"),
    "source": ("source", "source_url", "url", "document_path", "file_path"),
    "act": ("act_title", "regulation", "legal_reference"),
    "collection": ("collection", "category", "domain"),
}

_STOPWORDS = {
    "a", "an", "the", "and", "or", "not", "of", "to", "is", "are", "was",
    "be", "in", "on", "for", "with", "comprises", "comprising", "said",
    "such", "its", "thereof", "wherein", "method", "process", "formulation",
    "using", "based", "via", "that", "this", "from", "as", "at", "by", "it",
}

_WEAK_TERMS = {
    "wellness", "natural", "multifunctional", "standardized", "controlled",
    "blend", "mixture", "product", "prepared", "comprise", "comprises",
    "comprising", "solution", "level", "amount", "improved", "enhanced",
}

_SYNONYMS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "knowledge", "botanical_synonyms.json"
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_PHRASE_RE = re.compile(r'"([^"]+)"')


def _load_synonyms() -> dict[str, list[str]]:
    """map: canonical_id -> [all known surface names (ascii-lower)]."""
    try:
        with open(_SYNONYMS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.debug("synonyms load failed: %s", exc)
        return {}
    out: dict[str, list[str]] = {}
    for cid, entry in (data or {}).items():
        names: list[str] = []
        botan = entry.get("botanical_name")
        if botan:
            names.append(str(botan))
        for lang in ("english", "sanskrit", "hindi", "marathi", "tamil",
                     "telugu", "kannada", "bengali", "gujarati", "malayalam"):
            for n in (entry.get(lang) or []):
                names.append(str(n))
        names = [re.sub(r"\s+", " ", n).strip().lower() for n in names]
        names = [n for n in names if n and len(n) > 1]
        out[cid] = list(dict.fromkeys(names))
    return out


_SYNONYMS = _load_synonyms()


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _term_variants(term: str) -> list[str]:
    """Synonym-expand a single query term against the botanical lexicon."""
    lowered = term.lower().strip()
    variants = [lowered]
    for _cid, names in _SYNONYMS.items():
        if lowered in names:
            for n in names:
                if n not in variants:
                    variants.append(n)
            break
    return variants


def _is_botanical_term(term: str) -> bool:
    return any(term in names for names in _SYNONYMS.values())


def _meaningful_terms(query: str) -> list[str]:
    """Collapse a natural-language query into meaningful search terms.

    Botanical names and concrete technical tokens are preferred over filler
    so the core-AND strategy targets distinctive features (as Eureka does
    with its core technical features).
    """
    terms: list[str] = []
    for raw in _PHRASE_RE.findall(query.lower()):
        clean = " ".join(_tokenize(raw))
        if clean and clean not in terms:
            terms.append(clean)
    for tok in _tokenize(query):
        if tok in _STOPWORDS or tok.isdigit() or tok in terms:
            continue
        terms.append(tok)

    def _rank(t: str) -> tuple:
        score = 0
        if _is_botanical_term(t):
            score -= 4
        elif t in _WEAK_TERMS:
            score += 4
        elif len(t) > 2:
            score += 1
        return (score, len(t))

    ranked = sorted(terms, key=_rank)
    return ranked[:6]


# --------------------------------------------------------------------------
# DSL parser
# --------------------------------------------------------------------------

class _Node:  # pragma: no cover - simple data holder
    pass


class _Term(_Node):
    __slots__ = ("text", "is_phrase")

    def __init__(self, text: str, is_phrase: bool = False):
        self.text = text
        self.is_phrase = is_phrase


class _Field(_Node):
    __slots__ = ("field", "op", "value")

    def __init__(self, field: str, op: str, value: str):
        self.field = field
        self.op = op
        self.value = value


class _And(_Node):
    __slots__ = ("left", "right")

    def __init__(self, left, right):
        self.left = left
        self.right = right


class _Or(_Node):
    __slots__ = ("left", "right")

    def __init__(self, left, right):
        self.left = left
        self.right = right


class _Not(_Node):
    __slots__ = ("child",)

    def __init__(self, child):
        self.child = child


class _Near(_Node):
    __slots__ = ("n", "left", "right")

    def __init__(self, n: int, left, right):
        self.n = n
        self.left = left
        self.right = right


def _tokenize_expr(expr: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    n = len(expr)
    while i < n:
        ch = expr[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "()":
            tokens.append(ch)
            i += 1
            continue
        if ch == '"':
            j = i + 1
            while j < n and expr[j] != '"':
                j += 1
            tokens.append("PHRASE:" + expr[i + 1:j])
            i = j + 1
            continue
        j = i
        while j < n and expr[j] not in "()" and not expr[j].isspace():
            j += 1
        tokens.append(expr[i:j].upper())
        i = j
    return tokens


class _Parser:
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self) -> str | None:
        t = self.peek()
        self.pos += 1
        return t

    def term(self) -> _Node:
        tok = self.consume()
        if tok == "(":
            node = self.or_expr()
            if self.peek() == ")":
                self.consume()
            return node
        if tok is None:
            raise ValueError("unexpected end of expression")
        if tok.startswith("PHRASE:"):
            return _Term(tok[7:], is_phrase=True)
        if ":" in tok or "=" in tok:
            field, val = re.split(r"[:=]", tok, maxsplit=1)
            op = "="
            if val[:1] in (">", "<"):
                op = val[:1]
                val = val[1:]
            if not val:
                raise ValueError(f"missing value for field {field}")
            return _Field(field.lower(), op, val)
        field = tok
        if self.peek() in (":", "="):
            self.consume()
            val = self.consume()
            if val is None:
                raise ValueError(f"missing value for field {field}")
            op = "="
            if val[:1] in (">", "<"):
                op = val[:1]
                val = val[1:]
            return _Field(field.lower(), op, val)
        return _Term(tok)

    def near_expr(self) -> _Node:
        left = self.term()
        while (tok := self.peek()) is not None and tok.startswith("NEAR"):
            near_tok = self.consume() or ""
            m = re.match(r"NEAR/(\d+)", near_tok)
            n = int(m.group(1)) if m else 5
            right = self.term()
            left = _Near(n, left, right)
        return left

    def not_expr(self) -> _Node:
        if self.peek() == "NOT":
            self.consume()
            return _Not(self.not_expr())
        return self.near_expr()

    def and_expr(self) -> _Node:
        left = self.not_expr()
        while self.peek() == "AND":
            self.consume()
            left = _And(left, self.not_expr())
        return left

    def or_expr(self) -> _Node:
        left = self.and_expr()
        while self.peek() == "OR":
            self.consume()
            left = _Or(left, self.and_expr())
        return left

    def parse(self) -> _Node:
        node = self.or_expr()
        if self.pos != len(self.tokens):
            raise ValueError(f"unexpected token at {self.tokens[self.pos:]}")
        return node


def compile_expression(expression: str) -> _Node:
    if not expression or not expression.strip():
        raise ValueError("empty boolean expression")
    return _Parser(_tokenize_expr(expression)).parse()


# --------------------------------------------------------------------------
# Evaluation against corpus documents
# --------------------------------------------------------------------------

def _doc_text(doc: dict[str, Any]) -> str:
    return str(doc.get("content", "") or "").lower()


def _term_match(doc: dict[str, Any], term: str, is_phrase: bool) -> bool:
    text = _doc_text(doc)
    key = term.lower()
    if is_phrase or " " in key:
        return key in text
    return key in _TOKEN_RE.findall(text + " " + str(doc.get("source", "") or "").lower())


def _field_match(doc: dict[str, Any], field: str, op: str, value: str) -> bool:
    haystack = ""
    for alias in _FIELD_ALIASES.get(field, (field,)):
        val = doc.get(alias)
        if val is None:
            continue
        if isinstance(val, (int, float)):
            haystack += f" {val} "
        else:
            haystack += f" {val} "
    haystack = haystack.lower()

    # Text-only corpora carry little structured metadata. For qualitative
    # fields, fall back to substring search over the passage + source so
    # `jurisdiction:IN`, `act:Patents Act` still retrieve real hits.
    if not haystack and field in ("jurisdiction", "act", "source", "collection", "title"):
        haystack = _doc_text(doc) + " " + str(doc.get("source", "") or "").lower()

    lval = value.lower()
    if op in (">", "<") or (field in ("year", "date") and lval.isdigit()):
        years = [int(v) for v in _TOKEN_RE.findall(haystack) if v.isdigit() and len(v) == 4]
        if op in (">", "<"):
            if not years:
                return False
            return any((int(y) > int(lval)) if op == ">" else (int(y) < int(lval)) for y in years)
        if years:
            target = int(lval)
            return any(int(y) == target for y in years)
    if lval.isdigit() and field in ("year", "date"):
        return f" {value} " in haystack
    return lval in haystack


def _evaluate(doc: dict[str, Any], node: _Node) -> bool:
    if isinstance(node, _Term):
        return _term_match(doc, node.text, node.is_phrase)
    if isinstance(node, _Field):
        return _field_match(doc, node.field, node.op, node.value)
    if isinstance(node, _And):
        return _evaluate(doc, node.left) and _evaluate(doc, node.right)
    if isinstance(node, _Or):
        return _evaluate(doc, node.left) or _evaluate(doc, node.right)
    if isinstance(node, _Not):
        return not _evaluate(doc, node.child)
    if isinstance(node, _Near):
        return _near_match(doc, node.n, node.left, node.right)
    return False


def _near_match(doc: dict[str, Any], n: int, left: _Node, right: _Node) -> bool:
    if not _evaluate(doc, left) or not _evaluate(doc, right):
        return False
    pos: dict[str, list[int]] = {}
    for idx, tok in enumerate(_tokenize(_doc_text(doc))):
        pos.setdefault(tok, []).append(idx)
    def _positions(node: _Node) -> list[int]:
        if isinstance(node, _Term):
            return pos.get(node.text, [])
        if isinstance(node, _Field):
            return []
        out: list[int] = []
        for child in _children(node):
            out.extend(_positions(child))
        return out
    lp = _positions(left)
    rp = _positions(right)
    for a in lp:
        for b in rp:
            if abs(a - b) <= n:
                return True
    return False


def _children(node: _Node) -> list[_Node]:
    if isinstance(node, _And):
        return [node.left, node.right]
    if isinstance(node, _Or):
        return [node.left, node.right]
    if isinstance(node, _Near):
        return [node.left, node.right]
    if isinstance(node, _Not):
        return [node.child]
    return []


def _leaf_terms(node: _Node) -> list[str]:
    if isinstance(node, (_Term, _Field)):
        return [
            str(
                getattr(node, "text", None)
                or getattr(node, "field", None)
                or ""
            )
        ]
    out: list[str] = []
    for c in _children(node):
        out.extend(_leaf_terms(c))
    return out


# --------------------------------------------------------------------------
# Corpus access
# --------------------------------------------------------------------------
#
# The corpus itself stays in-process: it is the *same list object* as
# ``HybridRetriever._bm25_corpus``, so caching it again would double memory for
# no gain, and pushing megabytes of documents through Redis on every replica
# would be worse.  What actually needs to be shared is *invalidation* — after a
# reindex one replica knows the corpus changed, and every other replica must
# notice.  A generation counter in the shared cache carries that signal.
#
# (The expensive part this guards against is the ``get_all_documents(limit=5000)``
# Qdrant round-trip, which used to be repeated per process after every restart.)

_corpus_cache = get_cache("boolean_corpus", default_ttl=0, max_memory_entries=1)
_CORPUS_GENERATION_KEY = "generation"

_CORPUS_CACHE: list[dict[str, Any]] = []
_CORPUS_LOADED_AT_GENERATION: str | None = None


def _current_generation() -> str:
    value = _corpus_cache.get(_CORPUS_GENERATION_KEY)
    if isinstance(value, str) and value:
        return value
    return "0"


def invalidate_corpus_cache():
    """Drop the cached corpus (call after a reindex to see new documents).

    Bumps the shared generation counter so replicas that are not the one
    performing the reindex also drop their copy.
    """
    global _CORPUS_CACHE, _CORPUS_LOADED_AT_GENERATION
    _CORPUS_CACHE = []
    _CORPUS_LOADED_AT_GENERATION = None
    _corpus_cache.set(
        _CORPUS_GENERATION_KEY, f"{int(_current_generation() or 0) + 1}", ttl=0
    )


def _load_corpus() -> list[dict[str, Any]]:
    """Full local retrieval corpus (shared with the hybrid pipeline)."""
    global _CORPUS_CACHE, _CORPUS_LOADED_AT_GENERATION
    generation = _current_generation()
    if _CORPUS_CACHE:
        if _CORPUS_LOADED_AT_GENERATION is None:
            # Corpus was supplied by a caller (tests, or a custom index) rather
            # than loaded here, so there is no recorded generation to invalidate
            # against. Adopt the current one and use it — an explicitly supplied
            # corpus is authoritative.
            _CORPUS_LOADED_AT_GENERATION = generation
            return _CORPUS_CACHE
        if _CORPUS_LOADED_AT_GENERATION == generation:
            return _CORPUS_CACHE
        # else: the generation moved (a reindex happened, possibly in another
        # replica) — fall through and reload.
    _CORPUS_CACHE = []
    _CORPUS_LOADED_AT_GENERATION = None
    try:
        from app.rag.retrieval_pipeline import HybridRetriever

        if HybridRetriever._bm25_corpus:
            _CORPUS_CACHE = HybridRetriever._bm25_corpus
            _CORPUS_LOADED_AT_GENERATION = generation
            return _CORPUS_CACHE
        from app.rag.qdrant_store import QdrantVectorStore
        docs = QdrantVectorStore().get_all_documents(limit=5000)
        if docs:
            HybridRetriever.build_bm25_index(docs)
            _CORPUS_CACHE = HybridRetriever._bm25_corpus
            _CORPUS_LOADED_AT_GENERATION = generation
            return _CORPUS_CACHE
    except Exception as exc:
        logger.debug("boolean corpus via qdrant failed: %s", exc)
    try:
        from app.rag.kb import collect_knowledge_documents
        docs = collect_knowledge_documents()
        if docs:
            _CORPUS_CACHE = docs
            _CORPUS_LOADED_AT_GENERATION = generation
            return _CORPUS_CACHE
    except Exception as exc:
        logger.debug("boolean corpus via kb failed: %s", exc)
    return []


def search(
    expression: str,
    top_k: int = 10,
    corpus: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one boolean expression over the corpus (deterministic)."""
    node = compile_expression(expression)
    docs = corpus if corpus is not None else _load_corpus()
    leaves = _leaf_terms(node)
    leaf_count = len(leaves) or 1

    scored: list[tuple[int, int, dict[str, Any]]] = []
    for doc in docs:
        if not (doc.get("content") or "").strip():
            continue
        if _evaluate(doc, node):
            matched = sum(
                1 for leaf in leaves for view in _one_leaf_views(node, leaf)
                if _evaluate(doc, view)
            )
            scored.append((matched, len(_doc_text(doc)), doc))
    scored = [s for s in scored if s[1] > 0] if False else scored
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    results: list[dict[str, Any]] = []
    for matched, _length, doc in scored[:top_k]:
        out = dict(doc)
        out["bool_matches"] = matched
        out["bool_ratio"] = round(matched / leaf_count, 2)
        out["bool_rank"] = len(results) + 1
        results.append(out)
    return {
        "expression": expression,
        "matched": len(scored),
        "results": results,
        "leaf_terms": leaves,
    }


def _one_leaf_views(node: _Node, leaf: str) -> list[_Node]:
    """Yield each leaf as a standalone node for per-leaf match counting."""
    views: list[_Node] = []
    if isinstance(node, _Term):
        views.append(_Term(leaf, is_phrase=bool(node.text and " " in node.text)))
    elif isinstance(node, _Field):
        views.append(_Field(node.field, node.op, node.value))
    else:
        for c in _children(node):
            views.extend(_one_leaf_views(c, leaf))
    return views


# --------------------------------------------------------------------------
# Eureka-style multi-boolean search generation  (Boolean Search 1..5)
# --------------------------------------------------------------------------

def _fmt(term: str) -> str:
    if " " in term:
        return f'"{term}"'
    return term.upper()


def build_searches(
    query: str,
    top_k: int = 8,
    jurisdiction: str | None = "IN",
) -> list[dict[str, Any]]:
    """Generate the five boolean search strategies for a technical solution."""
    terms = _meaningful_terms(query)
    if not terms:
        return []

    groups = [[_fmt(t)] + [_fmt(v) for v in _term_variants(t)[1:][:5]] for t in terms]
    searches: list[dict[str, Any]] = []

    def _run(name: str, formula: str, top: int = top_k) -> dict[str, Any]:
        try:
            res = search(formula, top_k=top)
            res["name"] = name
            return res
        except Exception as exc:
            logger.debug("boolean search %s failed: %s", name, exc)
            return {
                "name": name, "expression": formula,
                "matched": 0, "results": [], "leaf_terms": [],
            }

    # Boolean Search 1 — Core AND: every essential term must appear.
    formula1 = " AND ".join(_fmt(t) for t in terms[:4])
    searches.append(_run("Boolean Search 1", formula1))

    # Boolean Search 2 — Synonym OR-groups: terms OR'd with botanical synonyms.
    or_groups = [f"({' OR '.join(g[:6])})" for g in groups[:4]]
    formula2 = " AND ".join(or_groups) if len(or_groups) > 1 else or_groups[0]
    searches.append(_run("Boolean Search 2", formula2))

    # Boolean Search 3 — Classification/statutory combination.
    class_terms = [t for t in ("composition", "formulation", "extract", "preparation") if t not in _STOPWORDS]
    combo = " OR ".join(class_terms[:3])
    extra = [f"jurisdiction:{jurisdiction}"] if jurisdiction else []
    formula3 = " AND ".join(extra + [f"({combo})"] + [_fmt(t) for t in terms[:2]])
    if extra and terms:
        searches.append(_run("Boolean Search 3", formula3))

    # Boolean Search 4 — Phrase + recency (patent landscape phrasing).
    phrase_terms = [f'"{t}"' for t in terms[:3]]
    formula4 = " OR ".join(phrase_terms[:2]) + (" OR " + phrase_terms[2] if len(phrase_terms) > 2 else "")
    searches.append(_run("Boolean Search 4", formula4))

    # Boolean Search 5 — Broad recall: all expanded terms OR'd.
    all_terms: list[str] = []
    for g in groups:
        for t in g:
            if t not in all_terms:
                all_terms.append(t)
    formula5 = " OR ".join(all_terms[:14])
    searches.append(_run("Boolean Search 5", formula5))

    return searches


def merged_reference_list(
    searches: list[dict[str, Any]], top_k: int = 20
) -> list[dict[str, Any]]:
    """De-duplicate hits across the boolean searches into one ranked list."""
    seen: dict[str, dict[str, Any]] = {}
    for s in searches:
        for _idx, res in enumerate(s.get("results", [])):
            key_parts = [
                str(res.get("patent_number") or res.get("doc_id") or res.get("source", "")),
                str(res.get("content") or "")[:80],
            ]
            key = "|".join(key_parts)
            entry = seen.get(key)
            if entry is None:
                entry = dict(res)
                entry["bool_searches"] = [s["name"]]
                entry["bool_search_count"] = 1
                seen[key] = entry
            else:
                if s["name"] not in entry["bool_searches"]:
                    entry["bool_searches"].append(s["name"])
                    entry["bool_search_count"] = len(entry["bool_searches"])
    merged = []
    for entry in sorted(
        seen.values(),
        key=lambda e: (e.get("bool_search_count", 0), e.get("bool_matches", 0)),
        reverse=True,
    ):
        merged.append(entry)
        if len(merged) >= top_k:
            break
    return merged