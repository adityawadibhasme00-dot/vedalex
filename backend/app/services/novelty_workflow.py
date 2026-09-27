"""Eureka-style Novelty Search workflow for IP-SAKTI.

Reproduces PatSnap Eureka's Novelty Search agent as a reviewable, offline
pipeline whose seven steps all pull real signal from the local corpus:

    1. Technical Solution Summary  – cleaned description the user can edit
    2. Feature Extraction          – ingredient + keyword/phrase features
    3. Extract the Search Elements – per-feature keywords & botanical synonyms
    4. Search Strategy             – semantic + Boolean Search 1..5 + patent
                                      / paper / internet resource searches
    5. Reference List              – merged hits bucketed into tabs
6. Feature Comparison          – per-feature 7-level disclosure taxonomy
                                       against ONE common closest reference
                                       (single-reference novelty test)
     7. Search Report               – structured summary (Word-exportable)

Nothing is fabricated: when a surface is unavailable (e.g. live internet
disabled) its status is ``not_searched`` rather than an invented result.
"""

import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

_MEANINGFUL = re.compile(r"[a-z0-9]+")


def _meaningful_tokens(text: str) -> set:
    return set(_MEANINGFUL.findall((text or "").lower()))


def _detect_ingredients(text: str) -> list[dict[str, str]]:
    """Scan free-text description for known botanical ingredients.

    Matches any synonym (common name, scientific name, regional name) present
    in the botanical lexicon, longest-match first, with word boundaries so
    'sea' never matches 'search'. Returns canonical ingredient records.
    """
    import json
    import os

    path = os.path.join(
        os.path.dirname(__file__), "..", "knowledge", "botanical_synonyms.json"
    )
    try:
        lexicon = json.load(open(path, encoding="utf-8"))
    except OSError:  # pragma: no cover - defensive
        return []

    low = text.lower()
    found: list[dict[str, str]] = []
    for entry in lexicon.values():
        botanical = entry.get("botanical_name", "")
        variants: set = {botanical}
        for value in entry.values():
            if isinstance(value, str) and value != botanical:
                variants.add(value)
            elif isinstance(value, list):
                variants.update(str(x) for x in value)
        ordered_variants = sorted((v for v in variants if v), key=len, reverse=True)
        for variant in ordered_variants:
            probe = variant.strip().lower()
            if len(probe) < 3 or "(" in probe:
                continue
            if re.search(r"(?<![a-z0-9])" + re.escape(probe) + r"(?![a-z0-9])", low):
                if not any(f["canonical_id"] == entry.get("canonical_id") for f in found):
                    found.append({
                        "canonical_id": entry.get("canonical_id", ""),
                        "botanical_name": botanical,
                        "matched_name": variant.strip(),
                    })
                break
    return found


# --------------------------------------------------------------------------
# Step-based pipeline
# --------------------------------------------------------------------------

def _step_summary(problem: str) -> dict[str, Any]:
    clean = " ".join((problem or "").split())
    return {
        "status": "complete",
        "label": "Technical Solution Summary",
        "original_problem": clean,
        "summary": clean[:3000],
        "edit_hint": "Editable before the search runs — shorter summaries search better.",
    }


def _step_features(problem: str, markets: list[str]) -> dict[str, Any]:
    from app.services.innolab.agent_executors import _keyword_phrases, extract_features

    try:
        fe = extract_features(
            "novelty_search",
            {"problem_text": problem, "target_markets": markets or ["India"]},
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("feature extraction failed: %s", exc)
        fe = {"summary": "", "features": [], "markets": markets, "ingredients": []}

    # Ingredient features first (core weight), then keyword/phrase features.
    detected = _detect_ingredients(problem)
    resolved_names = [d["matched_name"] for d in detected]
    ingredients = list(dict.fromkeys([*fe.get("ingredients", []), *resolved_names]))

    features: list[dict[str, Any]] = []
    seen: set = set()

    def _add(text: str, kind: str, core: bool) -> None:
        text = str(text).strip()
        if not text or text in seen:
            return
        seen.add(text)
        features.append({
            "id": f"F{len(features) + 1}",
            "text": text[:90],
            "kind": kind,
            "core": core,
        })

    for d in detected:
        _add(d["matched_name"], "ingredient", True)

    for kw in _keyword_phrases(problem):
        if len(features) >= 12:
            break
        _add(kw, "keyword", False)

    # Cap at 12 features, always keeping core ingredients first.
    features = features[:12]

    return {
        "status": "complete",
        "label": "Feature Extraction",
        "features": features,
        "understanding": fe.get("summary", ""),
        "ingredients": ingredients,
        "detected_ingredients": detected[:6],
        "confirmed": False,
        "edit_hint": "Core features drive the search weight — toggle the flag to prioritise.",
    }


def _step_elements(features: list[dict[str, Any]]) -> dict[str, Any]:
    from app.rag.boolean_search import _meaningful_terms, _term_variants

    groups = []
    for f in features:
        terms = _meaningful_terms(f["text"])
        if not terms:
            continue
        keywords = [_fmt_term(t) for t in terms[:4]]
        synonyms: list[str] = []
        for t in terms[:3]:
            for v in _term_variants(t)[1:6]:
                if v not in synonyms:
                    synonyms.append(v)
        groups.append({
            "feature": f["id"],
            "feature_text": f["text"],
            "keywords": keywords,
            "synonyms": synonyms[:8],
        })
    return {
        "status": "complete",
        "label": "Extract the Search Elements",
        "groups": groups,
        "groups_by_feature": {f["id"]: f["text"] for f in features},
    }


def _fmt_term(t: str) -> str:
    return f'"{t}"' if " " in t else t


def _step_strategy(problem: str, features: list[dict[str, Any]], jurisdiction: str) -> dict[str, Any]:
    from app.rag.boolean_search import build_searches
    from app.rag.retrieval_pipeline import HybridRetriever

    feature_text = " ".join(f["text"] for f in features) or problem

    # Weight core ingredients in the probe query (they carry the search signal).
    core = " ".join(f["text"] for f in features if f.get("core"))
    weights = core or feature_text
    query = f"{weights} {feature_text} {problem}"[:600].strip()

    semantic: dict[str, Any] = {}
    try:
        res = HybridRetriever.retrieve(query=query, top_k=10)
        semantic = {
            "status": "complete",
            "matched": len(res.get("sources", [])),
            "formula": "SEMANTIC: " + query[:220],
            "results": [_doc_view(s, "Semantic search") for s in res.get("sources", [])],
        }
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("semantic search failed: %s", exc)
        semantic = {"status": "not_searched", "matched": 0, "results": []}

    boolean = []
    try:
        for s in build_searches(query, top_k=6, jurisdiction=jurisdiction):
            boolean.append({
                "name": s["name"],
                "formula": s["expression"],
                "matched": s["matched"],
                "results": [_doc_view(r, s["name"]) for r in s["results"]],
            })
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("boolean searches failed: %s", exc)

    # Patent-focused pass over the corpus.
    patent = {}
    try:
        res = HybridRetriever.retrieve(query=query, top_k=10)
        res["sources"] = [s for s in res.get("sources", []) if _kind(s) == "patent"]
        patent = {
            "status": "complete",
            "matched": len(res.get("sources", [])),
            "formula": "PATENT SEARCH: patent corpus subset filtered",
            "results": [_doc_view(s, "Patent Search") for s in res.get("sources", [])],
        }
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("patent search failed: %s", exc)
        patent = {"status": "not_searched", "matched": 0, "results": []}

    # Paper / journal pass.
    papers = {}
    try:
        res = HybridRetriever.retrieve(query=query, top_k=6, domains=None)
        res["sources"] = [s for s in res.get("sources", []) if _kind(s) == "paper"]
        papers = {
            "status": "complete",
            "matched": len(res.get("sources", [])),
            "formula": "NON-PATENT LITERATURE: journal/pubmed subset",
            "results": [_doc_view(s, "Paper Search") for s in res.get("sources", [])],
        }
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("paper search failed: %s", exc)
        papers = {"status": "not_searched", "matched": 0, "results": []}

    # Internet resource search (guarded — silent when live web is off).
    internet = {"status": "not_searched", "matched": 0, "formula": "INTERNET RESOURCE SEARCH", "results": []}
    try:
        from app.rag.official_web_retriever import _live_web_enabled, fetch_official_sources
        if _live_web_enabled():
            web = fetch_official_sources(query, top_k=5)
            internet = {
                "status": "complete",
                "matched": len(web),
                "formula": "INTERNET RESOURCE SEARCH: official/government web sources",
                "results": [_doc_view(w, "Internet Resource Search") for w in web],
            }
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("internet search failed: %s", exc)

    return {
        "status": "complete",
        "label": "Search Strategy",
        "query": query,
        "semantic": semantic,
        "boolean": boolean,
        "patent": patent,
        "papers": papers,
        "internet": internet,
    }


def _kind(doc: dict[str, Any]) -> str:
    src = str(doc.get("source") or doc.get("source_url") or doc.get("url") or "").lower()
    pno = str(doc.get("patent_number") or doc.get("publication_number") or "")
    if pno or "/patents/" in src or "patent" in src:
        return "patent"
    cat = str(doc.get("category") or "").lower()
    if "pubmed" in src or "journal" in src or ".pdf" in src and "doi" in src or cat in ("pubmed", "paper"):
        return "paper"
    if src.startswith("http") or "://" in src:
        return "internet"
    if doc.get("act_title") or "/acts/" in src or "/regulations/" in src or cat == "statutory":
        return "official"
    return "official"


def _doc_view(doc: dict[str, Any], via: str) -> dict[str, Any]:
    content = " ".join(str(doc.get("content") or "").split())
    pub = (doc.get("publication_year") or doc.get("date") or doc.get("publication_date") or "")
    return {
        "id": (doc.get("patent_number") or doc.get("doc_id") or doc.get("source")
               or doc.get("act_title") or doc.get("title") or ""),
        "title": (doc.get("title") or doc.get("act_title") or doc.get("source") or "Retrieved passage"),
        "publication_number": doc.get("patent_number") or "",
        "publication_date": str(pub) if pub else "",
        "assignee": doc.get("assignee") or doc.get("current_assignee") or "",
        "abstract": content[:260],
        "authority": doc.get("authority") or "",
        "source": doc.get("source") or "",
        "kind": _kind(doc),
        "via": via,
        "score": round(float(doc.get("score") or doc.get("bool_ratio") or doc.get("combined_score") or 0), 2),
    }


def _step_reference_list(strategy: dict[str, Any]) -> dict[str, Any]:
    seen: dict[str, dict[str, Any]] = {}
    surfaces = [
        ("semantic", strategy.get("semantic", {})),
        ("patent", strategy.get("patent", {})),
        ("papers", strategy.get("papers", {})),
        ("internet", strategy.get("internet", {})),
    ] + [("boolean", b) for b in strategy.get("boolean", [])]

    for via_key, surf in surfaces:
        for res in surf.get("results", []):
            key = res.get("id") or res.get("title", "")
            if not key:
                continue
            entry = seen.get(key)
            if entry is None:
                entry = dict(res)
                entry["via_list"] = [res.get("via", via_key)]
                delta = res.get("score") or 0
                entry["score"] = round(max(entry.get("score") or 0, delta), 2)
                seen[key] = entry
            else:
                if res.get("via") not in entry["via_list"]:
                    entry["via_list"].append(res.get("via"))

    reference_list = sorted(
        seen.values(), key=lambda e: e.get("score", 0), reverse=True
    )[:40]

    tabs: dict[str, list[dict[str, Any]]] = {"patent": [], "paper": [], "internet": [], "official": []}
    for ref in reference_list:
        tabs.setdefault(ref.get("kind", "official"), []).append(ref)

    tab_meta: list[dict[str, Any]] = [
        {"key": "patent", "label": "Patents", "count": len(tabs.get("patent", [])), "results": tabs.get("patent", [])},
        {"key": "paper", "label": "Papers", "count": len(tabs.get("paper", [])), "results": tabs.get("paper", [])},
        {"key": "internet", "label": "Internet Resources", "count": len(tabs.get("internet", [])), "results": tabs.get("internet", [])},
        {"key": "official", "label": "Official Publications", "count": len(tabs.get("official", [])), "results": tabs.get("official", [])},
    ]
    return {
        "status": "complete",
        "label": "Reference List",
        "total": len(reference_list),
        "tabs": [t for t in tab_meta if t["count"] > 0],
        "results": reference_list,
    }


def _step_comparison(
    features: list[dict[str, Any]], reference_list: list[dict[str, Any]]
) -> dict[str, Any]:
    """Single-reference novelty test over the extracted invention features.

    Every feature is measured against ONE common closest reference, so a
    feature's disclosure level and its similarity value always come from the
    same comparison (no "novel, 91%" contradictions). Disclosure levels are
    derived from term overlap against that single reference using a fixed
    7-level taxonomy; conclusions that need human judgment (inherent /
    implicit disclosure, priority or legal-status checks) are surfaced as
    reviewer questions instead of being asserted. Metrics are kept separate:
    semantic similarity is topic overlap and is explicitly not a novelty
    score.
    """
    pool = reference_list[:10]

    def _overlap(feat_tokens, ref) -> float:
        rtoks = _meaningful_tokens(ref.get("abstract") or "")
        if not rtoks:
            return 0.0
        return len(feat_tokens & rtoks) / len(feat_tokens)

    def _level(ratio: float) -> str:
        if ratio >= 0.85:
            return "Explicitly disclosed"
        if ratio >= 0.6:
            return "Broadly disclosed"
        if ratio >= 0.35:
            return "Partially disclosed"
        if ratio > 0.0:
            return "Suggested only"
        return "Not disclosed"

    def _basis(level: str, ratio: float) -> str:
        pct = round(ratio * 100)
        if level == "Explicitly disclosed":
            return f"All searchable terms of the feature appear in the closest reference passage ({pct}% term overlap)."
        if level == "Broadly disclosed":
            return f"The feature appears in the closest reference in broad/general terms ({pct}% term overlap); limitations may differ."
        if level == "Partially disclosed":
            return f"The feature is only partially traceable in the closest reference ({pct}% term overlap); one or more limitations differ."
        if level == "Suggested only":
            return f"Only a hint of the concept appears in the closest reference ({pct}% term overlap); not an enabling disclosure."
        return "No searchable term of the feature appears in the closest reference passage (0% term overlap)."

    feature_rows = []  # (feature, tokens) pairs with searchable tokens
    for f in features[:8]:
        ftoks = _meaningful_tokens(f["text"])
        if ftoks:
            feature_rows.append((f, ftoks))

    essential = [f for f in features if f.get("core")]
    if not essential:
        essential = [f for f, _ in feature_rows[:3]]
    essential_ids = {f["id"] for f in essential}
    protected = [f for f, _ in feature_rows if f["id"] in essential_ids]

    # Score every reference against every essential feature; pick the single
    # common reference that discloses the most essential features (strong
    # disclosure first, then partial, then raw overlap). References without a
    # usable passage rank below any usable one.
    ranked: list[dict[str, Any]] = []
    for ref in pool:
        usable = bool((ref.get("abstract") or "").strip())
        strong = partial = 0
        top = 0.0
        for f, ftoks in feature_rows:
            if f["id"] not in essential_ids:
                continue
            r = _overlap(ftoks, ref)
            if r >= 0.6:
                strong += 1
            elif 0.35 <= r < 0.6:
                partial += 1
            top = max(top, r)
        ranked.append({
            "ref": ref, "usable": usable,
            "key": (strong, partial, top) if usable else (-1, -1, -1.0),
        })
    closest = max(ranked, key=lambda r: r["key"])["ref"] if ranked else None
    closest_title = (closest or {}).get("title", "no qualifying reference") if closest else "no qualifying reference"

    rows: list[dict[str, Any]] = []
    disclosed = partially = novel = unclear = 0
    for f, ftoks in feature_rows:
        if closest is None:
            ratio, level, basis = 0.0, "Unclear", "No usable reference passage was retrieved to judge this feature against."
            unclear += 1
        else:
            ratio = _overlap(ftoks, closest)
            level = _level(ratio)
            basis = _basis(level, ratio)
            if level in ("Explicitly disclosed", "Broadly disclosed"):
                disclosed += 1
            elif level == "Partially disclosed":
                partially += 1
            else:
                novel += 1  # Suggested only / Not disclosed -> not established
        rows.append({
            "feature": f["id"],
            "feature_text": f["text"],
            "essentiality": "essential" if f["id"] in essential_ids else "optional",
            "disclosure_level": level,
            "score": round(ratio * 100),
            "closest_reference": closest_title,
            "evidence": (closest or {}).get("authority", "gap reported") if closest else "gap reported",
            "basis": basis,
        })

    covered = sum(
        1 for r in rows
        if r["essentiality"] == "essential"
        and r["disclosure_level"] in ("Explicitly disclosed", "Broadly disclosed")
    )
    m = sum(1 for r in rows if r["essentiality"] == "essential")
    missing = [
        r["feature_text"] for r in rows
        if r["essentiality"] == "essential"
        and r["disclosure_level"] in ("Not disclosed", "Suggested only", "Unclear")
    ]

    all_disclosed = m > 0 and covered == m
    if closest is None:
        anticipation = "Novelty not established — no qualifying pre-date reference found in the searched corpus."
        risk = "Unknown"
    elif all_disclosed:
        anticipation = "Potentially anticipated — a single reference discloses all essential features."
        risk = "High"
    elif m and covered * 2 >= m:
        anticipation = "Not fully anticipated by the identified single reference, but most essential features are disclosed in it."
        risk = "Medium"
    elif covered > 0:
        anticipation = "Feature-level overlap only — no single reference discloses all essential features together."
        risk = "Low"
    else:
        anticipation = "Feature-level overlap only — no essential feature is disclosed by the closest reference."
        risk = "Low"

    combination_disclosure = (
        "A single reference discloses all essential features together; combination novelty therefore "
        "depends on feature-by-feature review of limitations."
        if all_disclosed
        else "No single reference was found that discloses ALL essential features together — the combination "
             "itself is not shown in any single document."
    )

    usable_refs = sum(1 for r in reference_list if (r.get("abstract") or "").strip())
    n_refs = len(reference_list)
    if n_refs == 0:
        confidence = "Low — the searched corpus returned no references"
    elif usable_refs < 5:
        confidence = "Low — only a small number of comparable passages were retrieved"
    elif usable_refs < 20:
        confidence = "Medium — moderate corpus coverage; wider synonyms may surface additional prior art"
    else:
        confidence = "High — broad corpus coverage for this feature set (results are corpus-bound, not a global novelty opinion)"

    semantic_similarity = (
        round(max((_overlap(ftoks, closest) for _, ftoks in feature_rows), default=0.0) * 100)
        if closest is not None else None
    )

    reviewer_questions = []
    if missing:
        reviewer_questions.append(
            "Confirm each missing essential feature manually — absence in the closest reference may still be "
            "an inherent disclosure or appear under a non-matching synonym."
        )
    if closest is not None:
        reviewer_questions.append(
            f"Verify the legal/priority status of '{closest_title[:60]}' at the official patent register "
            "before relying on it."
        )
    if m and not all_disclosed:
        reviewer_questions.append(
            "Confirm combination novelty: no retrieved reference discloses all essential features in a single document."
        )
    if any(r.get("kind") == "official" for r in pool):
        reviewer_questions.append(
            "Regulatory/statutory sources were retrieved — they describe practice, not patent rights; keep them as "
            "background only and exclude them from the novelty test."
        )

    return {
        "status": "complete",
        "label": "Feature Comparison",
        "rows": rows,
        "semantic_similarity": semantic_similarity,
        "feature_coverage": f"{covered}/{m}",
        "feature_coverage_n": covered,
        "feature_coverage_m": m,
        "essential_features": [f["text"] for f in protected],
        "missing_features": missing,
        "combination_disclosure": combination_disclosure,
        "single_reference_anticipation": anticipation,
        "anticipation_risk": risk,
        "search_confidence": confidence,
        "closest_reference": closest_title,
        "reviewer_questions": reviewer_questions,
        "tally": {"novel": novel, "partially": partially, "disclosed": disclosed},
        "compare_pool": (
            f"Single-reference novelty test: every feature is measured against one common closest reference "
            f"('{closest_title}') drawn from {len(pool)} screened reference(s) — never against a combination."
        ),
    }


def _step_report(steps: dict[str, Any]) -> dict[str, Any]:
    summary = steps.get("2_features", {}).get("summary")
    comparison = steps.get("6_comparison", {})
    refs = steps.get("5_reference_list", {}).get("results", [])
    compact = (
        f"Single-reference novelty test: {comparison.get('feature_coverage', '0/0')} essential feature(s) "
        f"disclosed by '{comparison.get('closest_reference', 'closest retrieved reference')}'. "
        f"{comparison.get('single_reference_anticipation', '')} "
        f"Preliminary risk: {comparison.get('anticipation_risk', 'Unknown')}. "
        f"Semantic similarity ({comparison.get('semantic_similarity', 'n/a')}%) is topic overlap only and "
        f"is not a novelty score. {len(comparison.get('rows', []))} feature(s) compared; "
        f"search confidence {comparison.get('search_confidence', 'Low').split(' ')[0]} "
        f"across {len(refs)} retrieved reference(s)."
    )
    return {
        "status": "complete",
        "label": "Search Report",
        "summary": summary,
        "compact": compact,
        "note": "Original + summarized technical solutions, search elements, strategies, "
                "reference list, feature comparison and novelty assessment. "
                "Exports to a Word document. Not a legal opinion.",
    }


# --------------------------------------------------------------------------
# Workflow orchestrator
# --------------------------------------------------------------------------

def run_workflow(
    problem_text: str,
    target_markets: list[str] | None = None,
    jurisdiction: str = "IN",
) -> dict[str, Any]:
    """Run the full Eureka-style Novelty Search workflow."""
    problem = (problem_text or "").strip()
    if not problem:
        raise ValueError("problem_text is required")

    wf_id = f"ns-{int(time.time() * 1000)}"
    markets = [m for m in (target_markets or ["India"]) if m]
    steps: dict[str, Any] = {}
    steps["1_summary"] = _step_summary(problem)
    steps["2_features"] = _step_features(problem, markets)
    steps["3_elements"] = _step_elements(steps["2_features"]["features"])
    steps["4_strategy"] = _step_strategy(problem, steps["2_features"]["features"], jurisdiction)
    steps["5_reference_list"] = _step_reference_list(steps["4_strategy"])
    steps["6_comparison"] = _step_comparison(
        steps["2_features"]["features"], steps["5_reference_list"]["results"]
    )
    steps["7_report"] = _step_report(steps)

    return {
        "workflow_id": wf_id,
        "status": "complete",
        "problem_text": problem,
        "target_markets": markets,
        "jurisdiction": jurisdiction,
        "steps": steps,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# --------------------------------------------------------------------------
# Word export shape (compatible with the Innovation-Lab docx builder)
# --------------------------------------------------------------------------

def build_export_result(workflow: dict[str, Any]) -> dict[str, Any]:
    """Shape a finished workflow into the generic agent-result document model."""
    steps = workflow.get("steps", {})
    s1 = steps.get("1_summary", {})
    s2 = steps.get("2_features", {})
    s5 = steps.get("5_reference_list", {})
    s6 = steps.get("6_comparison", {})
    s7 = steps.get("7_report", {})

    workflow_labels = []
    for key in sorted(steps.keys()):
        label = steps[key].get("label", key)
        workflow_labels.append({"label": label, "description": steps[key].get("edit_hint", "")})

    sections = []
    sections.append({
        "title": "Technical Solution Summary",
        "rows": [{"item": "Original description", "value": s1.get("original_problem", "")[:400]}],
        "columns": ["item", "value"],
        "caption": "Review and edit before confirming.",
    })
    sections.append({
        "title": "Extracted core technical features (F1…Fn; confirm & edit)",
        "rows": [
            {"feature": f.get("id"), "text": f.get("text"), "kind": f.get("kind"),
             "weight": "core + keyword" if f.get("core") else "topic + keyword"}
            for f in s2.get("features", [])
        ],
        "columns": ["feature", "text", "kind", "weight"],
        "caption": str(s2.get("understanding", ""))[:200],
    })
    sections.append({
        "title": "Prior-art search strategies",
        "rows": [
            {"strategy": "Semantic search", "input": str(steps.get("4_strategy", {}).get("semantic", {}).get("formula", ""))[:180]},
            {"strategy": "Boolean Search 1–5", "input": "; ".join(b.get("formula", "") for b in steps.get("4_strategy", {}).get("boolean", []))[:300]},
            {"strategy": "Patent search", "input": "patent corpus subset with metadata filters"},
            {"strategy": "Paper / internet", "input": "non-patent literature + official web resources"},
        ],
        "columns": ["strategy", "input"],
        "caption": "Multi-strategy examiner-style search across the local corpus.",
    })
    sections.append({
        "title": "Reference list",
        "rows": [
            {"title": r.get("title", "")[:80], "date": r.get("publication_date", ""),
             "kind": r.get("kind", ""), "via": ", ".join(r.get("via_list", []))}
            for r in s5.get("results", [])[:20]
        ],
        "columns": ["title", "date", "kind", "via"],
        "caption": f"{s5.get('total', 0)} total reference(s) across the tabs.",
    })
    sections.append({
        "title": "Feature-by-feature disclosure (single-reference novelty test)",
        "rows": [
            {"feature": r.get("feature"), "feature_text": r.get("feature_text"),
             "essentiality": r.get("essentiality"), "disclosure_level": r.get("disclosure_level"),
             "semantic_overlap": f"{r.get('score', 0)}%",
             "closest_reference": r.get("closest_reference", ""), "basis": r.get("basis", "")}
            for r in s6.get("rows", [])
        ],
        "columns": ["feature", "feature_text", "essentiality", "disclosure_level", "semantic_overlap", "closest_reference", "basis"],
        "caption": "Each feature judged against the single closest reference; semantic overlap (%) is shown separately from the disclosure level and is not a novelty score.",
    })
    sections.append({
        "title": "Novelty assessment",
        "rows": [
            {"item": "Single-reference test", "value": s6.get("compare_pool", "")},
            {"item": "Semantic similarity", "value": f"{s6.get('semantic_similarity') if s6.get('semantic_similarity') is not None else 'n/a'}% — topic/vocabulary overlap, not a novelty score"},
            {"item": "Essential feature coverage", "value": s6.get("feature_coverage", "0/0")},
            {"item": "Missing features", "value": "; ".join(s6.get("missing_features", [])[:4]) or "none identified"},
            {"item": "Combination disclosure", "value": s6.get("combination_disclosure", "")},
            {"item": "Single-reference anticipation", "value": s6.get("single_reference_anticipation", "")},
            {"item": "Preliminary novelty risk", "value": s6.get("anticipation_risk", "Unknown")},
            {"item": "Search confidence", "value": s6.get("search_confidence", "Low")},
            {"item": "Reviewer questions", "value": "; ".join(s6.get("reviewer_questions", [])) or "none"},
            {"item": "Closest prior art", "value": f"{s5.get('total', 0)} reference(s) screened; closest: {s6.get('closest_reference', '—')}"},
        ],
        "columns": ["item", "value"],
        "caption": "Not a legal opinion — verify priority/legal status before final conclusion.",
    })

    return {
        "summary": s7.get("compact", "") or (s7.get("summary") or ""),
        "note": s7.get("note", ""),
        "workflow": workflow_labels,
        "sections": sections,
        "findings": [
            {"code": "ns-coverage", "title": "Essential feature coverage",
             "detail": f"{s6.get('feature_coverage', '0/0')} essential feature(s) disclosed by the closest reference. "
                       f"{s6.get('single_reference_anticipation', '')}",
             "severity": "info" if s6.get("anticipation_risk") in ("Low", "Unknown") else "warning"},
            {"code": "ns-ant", "title": "Anticipation risk",
             "detail": f"Preliminary {s6.get('anticipation_risk', 'Unknown')} from the single-reference novelty test; "
                       "confirm legal/priority status before reliance.",
             "severity": "warning" if s6.get("anticipation_risk") == "High" else "info"},
            {"code": "ns-refs", "title": "Reference list",
             "detail": f"{s5.get('total', 0)} reference(s) across patents / papers / internet / official tabs.",
             "severity": "info"},
        ],
        "citations": [
            {"id": "ns-ref", "act_title": r.get("title", "")[:80],
             "authority": r.get("authority", "KB")}
            for r in s5.get("results", [])[:8]
        ],
    }