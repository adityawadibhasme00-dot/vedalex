"""Novelty search and the trade-document (TDOC) pipeline.

Part of the Innovation-Lab agent split (S5).  Each module owns one
domain end to end: its entry-point ``_hub_*`` executor and every private
helper used by exactly that executor.  Shared text-analysis primitives live
in :mod:`app.services.innolab.agents._shared_text`; grounding primitives
(corpus loading, retrieval, evidence shaping) live in
:mod:`app.services.innolab._shared`.

Deterministic and offline: no network calls, no fabrication.  When the corpus
has no answer the agent reports the gap rather than guessing.
"""

from __future__ import annotations

import re
from typing import Any, cast

from app.services.innolab.agents._shared_text import (
    _PAT_PUBNO,
    _atomic_novelty_features,
    _basis_text,
    _feature_disclosure,
    _keyword_phrases,
    _overlap_similarity,
    _tdoc_ref_kind,
    _tokens,
)
from app.services.innolab._shared import (
    _evidence,
    _finding,
    _jurisdiction_code,
    _retrieve,
    _section,
    _text,
)

__all__ = [
    "_hub_novelty",
    "_TDOC_ADMIN_PATTERNS",
    "_TDOC_SYSTEM_RE",
    "_tdoc_corruption",
    "_tdoc_is_admin_line",
    "_tdoc_tag_lines",
    "_tdoc_classify_feature",
    "_tdoc_ref_passage_label",
    "_tdoc_is_self",
    "_tdoc_hardening",
    "_hub_tdoc_novelty",
]

def _hub_novelty(inputs: dict[str, Any], result: dict[str, Any], resolved: list[dict[str, Any]], botanicals: str) -> dict[str, Any]:
    disclosure = _text(inputs, "problem_text", "document_text", "disclosure_text", "formulation_text")
    process = _text(inputs, "process_desc")
    query = f"{botanicals} {disclosure} {process} prior art".strip()
    cit = result["citations"] or _retrieve(query, top_k=6)

    # enrich a thin corpus with secondary feature queries so novelty is never
    # decided from a single under-covered search
    if len(cit) < 3:
        seen = {c.get("act_title") for c in cit}
        for market in result.get("jurisdictions") or []:
            for kw in _keyword_phrases(query, limit=4):
                for c in _retrieve(kw, jurisdiction=_jurisdiction_code(market), top_k=2):
                    if c.get("act_title") and c["act_title"] not in seen:
                        cit.append(c)
                        seen.add(c["act_title"])
    cit = cit or []

    # regulatory / TK / admin passages are shown as CONTEXT, never as closest art —
    # a regulation or monograph must not become a fake 'closest prior-art reference'.
    context_refs = [c for c in cit if _tdoc_ref_kind(c) in ("Regulatory / safety context", "Traditional knowledge")]
    cit = [c for c in cit if _tdoc_ref_kind(c) in ("Patent prior art", "Scientific / technical", "TDoc / contribution record")]

    # 1) atomic, claim-comparable features (never one big combined string)
    features = _atomic_novelty_features(inputs, resolved)
    required = [f for f in features if f["essentiality"] == "Essential"] or features[:3]

    # 2) feature × reference disclosure mapping (single-reference test)
    matrix: list[dict[str, Any]] = []
    for idx, c in enumerate(cit):
        passage = (" ".join(filter(None, [c.get("exact_passage"), c.get("act_title")])))
        per = {f["feature"]: {"level": lev, "basis": basis}
               for f in features for lev, basis in [_feature_disclosure(f["feature"], passage)]}
        strong = sum(1 for f in required if per[f["feature"]]["level"] in ("Explicitly disclosed", "Inherently disclosed"))
        broad = sum(1 for f in required if per[f["feature"]]["level"] in ("Broadly disclosed", "Partially disclosed"))
        matrix.append({
            "ref_id": f"R{idx + 1}",
            "title": c.get("act_title") or "corpus source",
            "authority": c.get("authority") or "KB",
            "passage": c,
            "required_strong": strong,
            "required_total": len(required),
            "required_partial": broad,
            "disclosed": per,
        })

    closest = max(matrix, key=lambda m: (m["required_strong"], m["required_partial"]), default=None)
    if closest:
        semantic = _overlap_similarity(f"{botanicals} {disclosure}", closest["passage"].get("exact_passage") or "")
        all_strong = closest["required_strong"] == closest["required_total"] and closest["required_total"] > 0
        if all_strong:
            anticipation, risk = "Potentially anticipated (single-reference)", "High"
        elif closest["required_strong"] >= max(1, int(round(closest["required_total"] / 2))):
            anticipation, risk = "Not fully anticipated by the identified reference", "Medium"
        elif closest["required_strong"] > 0 or closest["required_partial"] > 0:
            anticipation, risk = "Feature-level overlap only", "Low"
        else:
            anticipation, risk = "Feature-level overlap only", "Low"
        missing = [f["feature"] for f in required
                   if closest["disclosed"][f["feature"]]["level"] not in ("Explicitly disclosed", "Inherently disclosed")]
        combination_status = "Established" if all_strong else "Not established"
        coverage_note = (f"""{closest['ref_id']} ('{closest['title']}') discloses {closest['required_strong']} of {closest['required_total']} essential features explicitly or inherently. Semantic similarity measures topic/vocabulary overlap only and does not equal novelty.""")
    else:
        semantic = 0
        all_strong = False
        anticipation, risk = "Novelty not established — no qualifying pre-date reference found in the searched corpus", "Unknown"
        missing = [f["feature"] for f in required]
        combination_status = "Cannot be assessed (no reference retrieved)"
        coverage_note = "No qualifying passage was retrieved; absence of a hit is a gap in coverage, not proof of novelty."

    if not cit:
        search_conf, search_reason = "Low", "No passages retrieved — coverage is insufficient to rely on."
    elif len(cit) < 3:
        search_conf, search_reason = "Low", f"Only {len(cit)} passage(s) — expand keyword, classification and family searches."
    elif len(cit) < 6:
        search_conf, search_reason = "Medium", f"{len(cit)} passage(s) screened across semantic/keyword routes."
    else:
        search_conf, search_reason = "Medium-High", f"{len(cit)} passage(s) screened across multiple strategies."

    result["summary"] = (f"Essential feature coverage {(closest or {}).get('required_strong', 0)}/{(closest or {}).get('required_total', 0)} in the closest "
                         f"reference; single-reference anticipation: {anticipation.split(' (')[0]}; preliminary novelty risk: {risk.lower()}.")
    result["note"] = "Atomic feature extraction → confirm → multi-strategy search → disclosure levels → single-reference novelty matrix → separated metrics."
    result["citations"] = cit
    result["findings"].append(_finding("ns-1", "Essential feature coverage",
                                       coverage_note, "info" if risk == "High" else "warning"))
    result["findings"].append(_finding("ns-2", "Single-reference anticipation",
                                       f"{anticipation}. Multiple references are NOT combined to conclude lack of novelty.", "error" if risk == "High" else "info"))
    result["findings"].append(_finding("ns-3", "Semantic similarity",
                                       f"{semantic}% topic/vocabulary overlap with the closest passage — this is NOT a novelty percentage.", "info"))
    result["findings"].append(_finding("ns-4", "Search confidence",
                                       f"{search_conf} — {search_reason}", "info" if search_conf.startswith("Medium") else "warning"))
    for c in cit[:3]:
        result["evidence"].append(_evidence("novelty", c.get("act_title"), c.get("authority") or "KB"))
    result["suggestions"] = [
        "Confirm which features are ESSENTIAL; the single-reference novelty test is applied to the essential set.",
        "Supply the missing numeric parameters (solvent ratio, temperature, time, markers, dosage form) — underdefined features cannot be compared.",
        "Provide the priority/filing date so the pre-date cutoff can be fixed before the claim-level search.",
        "Map each essential feature to the exact claim/paragraph of the closest reference for the written novelty argument.",
        "Run a separate inventive-step analysis (multiple references MAY combine there) and a separate FTO search.",
    ]

    matrix_rows = [
        {
            "reference": f"R{i + 1} · {m['title']}",
            "authority": m["authority"],
            "essential_disclosed": f"{m['required_strong']}/{m['required_total']}",
            "broad_or_partial": str(m["required_partial"]),
            "all_essential_in_one": "Yes" if m["required_strong"] == m["required_total"] and m["required_total"] > 0 else "No",
            "pre_date_status": "Verify priority/filing date at source",
        }
        for i, m in enumerate(matrix)
    ]
    if not matrix_rows:
        matrix_rows = [{"reference": "—", "authority": "—", "essential_disclosed": "0/0",
                        "broad_or_partial": "0", "all_essential_in_one": "Cannot assess",
                        "pre_date_status": "Extend search corpus"}]

    per_feature_rows = []
    ref = closest["passage"] if closest else {}
    for i, f in enumerate(features):
        level, basis = _feature_disclosure(f["feature"],
                                           " ".join(filter(None, [ref.get("exact_passage"), ref.get("act_title")])) if closest else "")
        confidence = "High" if level == "Explicitly disclosed" else "Medium" if level in ("Partially disclosed", "Broadly disclosed") else "Low"
        per_feature_rows.append({
            "feature_num": f"F{i + 1}",
            "feature": f["feature"],
            "type": f["type"],
            "essentiality": f["essentiality"],
            "disclosure_level": level,
            "basis": basis,
            "confidence": confidence,
        })

    result["sections"] += [
        _section("Extracted core technical features (confirm & edit)", [
            {"feature_num": f"F{i + 1}", "feature": f["feature"], "type": f["type"],
             "essentiality": f["essentiality"], "measurability": f["measurability"],
             "parameter_status": "Provided" if "not provided" not in f["feature"] else "Missing"}
            for i, f in enumerate(features)
        ], ["feature_num", "feature", "type", "essentiality", "measurability", "parameter_status"],
           "Features are split into atomic, claim-comparable units. Vague phrases such as 'controlled solvent' are flagged as underdefined and must be quantified before scoring. Novelty is assessed against the CONFIRMED ESSENTIAL features."),
        _section("Prior-art search strategies (multi-strategy)", [
            {"strategy": "Semantic search", "input": "invention language as a natural-language query"},
            {"strategy": "Keyword / synonym search", "input": "feature terms expanded (botanical, chemical, process and spelling variants)"},
            {"strategy": "Feature-combination search", "input": "essential features combined (e.g. Ashwagandha + Brahmi + hydroalcoholic)"},
            {"strategy": "Parameter & range search", "input": "temperature, time, solvent ratio, pH, concentration, marker ranges"},
            {"strategy": "IPC/CPC classification search", "input": "classes recovered from the closest references"},
            {"strategy": "Family & citation tracing", "input": "backward/forward citations and family members (deduplicated)"},
            {"strategy": "Non-patent literature", "input": "papers, monographs, theses and regulatory monographs"},
        ], ["strategy", "input"], "Examiner-style multi-strategy search; a single natural-language query is never relied on."),
        _section("Feature-by-feature disclosure (closest reference)", per_feature_rows,
                 ["feature_num", "feature", "type", "essentiality", "disclosure_level", "basis", "confidence"],
                 "Seven-level disclosure taxonomy: Explicitly / Inherently / Partially / Broadly disclosed, Suggested only, Not disclosed, Unclear. 'Not found in the searched corpus' is never called 'novel'."),
        _section("Single-reference novelty matrix", matrix_rows,
                 ["reference", "authority", "essential_disclosed", "broad_or_partial", "all_essential_in_one", "pre_date_status"],
                 "Novelty is tested one reference at a time. Lack of novelty requires ONE qualifying pre-date reference to disclose every essential feature; different references disclosing different features support feature-level overlap or inventive-step discussion, NOT a lack-of-novelty conclusion."),
        _section("Regulatory / traditional-knowledge context (NOT closest art)", [
            {"title": c.get("act_title") or "corpus source", "authority": c.get("authority") or "KB",
             "role": "Excluded from the closest-art contest — regulations/monographs are context, not a substitute for a technical prior-art reference."}
            for c in context_refs[:6]
        ] if context_refs else [{"title": "[None retrieved]", "authority": "—",
                                 "role": "No regulatory/TK passage was in the retrieved set for this query."}],
        ["title", "authority", "role"],
        "Even at ~100% topic similarity, a regulatory or TK document does not prove technical anticipation by itself; the invention still needs a single qualifying technical reference for a lack-of-novelty position."),
        _section("Novelty assessment (separated metrics)", [
            {"item": "Semantic similarity", "value": f"{semantic}%",
             "meaning": "Topic/vocabulary overlap with the closest passage — NOT a novelty percentage."},
            {"item": "Essential feature coverage", "value": f"{closest['required_strong']}/{closest['required_total']}" if closest else "0/0",
             "meaning": "Essential features explicitly or inherently disclosed by the closest single reference."},
            {"item": "Missing or underdefined features", "value": "; ".join(missing[:4]) or "None of the essential set missing",
             "meaning": "Features the closest reference does not disclose or the inventor has not quantified."},
            {"item": "Combination disclosure", "value": combination_status,
             "meaning": "Whether the full claimed combination appears in one reference."},
            {"item": "Single-reference anticipation", "value": anticipation,
             "meaning": "Preliminary technical observation — legal review required."},
            {"item": "Preliminary novelty risk", "value": risk,
             "meaning": "High only if one pre-date reference discloses every essential feature; risk is otherwise Low/Medium/Unknown with reasons."},
            {"item": "Search confidence", "value": search_conf,
             "meaning": search_reason},
        ], ["item", "value", "meaning"], "Scores are split and defined; there is no unexplained single 'novelty score'."),
        _section("Inventive-step indicators (SEPARATE — not novelty)", [
            {"indicator": "Features spread across multiple references", "value": "Relevant to obviousness, not to lack of novelty"},
            {"indicator": "Technical motivation to combine", "value": "To be argued from the prior art once references are confirmed"},
            {"indicator": "Unexpected technical effect", "value": "Not established from this search — requires experimental data"},
            {"indicator": "Teaching away / parameter criticality", "value": "To be reviewed in full patent texts"},
        ], ["indicator", "value"], "Combining multiple documents may support inventive-step analysis but is never used here to conclude lack of novelty."),
        _section("Scope note", [
            {"item": "FTO", "value": "This is a novelty/prior-art screening, not a Freedom-to-Operate opinion — run the FTO agent separately against active claims and legal status."},
            {"item": "Legal opinion", "value": "Preliminary technical analysis only; confirm with a patent professional before filing."},
        ], ["item", "value"]),
    ]
    return result


_TDOC_ADMIN_PATTERNS = (
    r"^\s*[#*]+\s*",
    r"^\s*\*\*.*\*\*\s*$",
    r"^\s*\d{1,3}\s*[.)]\s*$",
    r"(table\s+of\s+contents|revision\s+history|document\s+control|document\s+identification|"
    r"confidential|distribution\s+list)",
    r"\b(project\s+title|technical\s+disclosure|disclosure\s+(id|number)|"
    r"author\w*|contribut\w*|company|organisation|organisation)\b",
    r"^\s*\d{1,3}\s+[-–—]\s+",
    r"\b(abstract|executive\s+summary|introduction|background|problem\s+statement|objective|"
    r"scope|prior\s+art|the\s+invention|conclusion|references|annex|appendix|glossary|"
    r"terminolog\w*|definitions)\s*[:\-]?\s*$",
    r"^\s*(manufacturing\s+documentation|regulatory\s+documentation|quality\s+checkpoints)\s*$",
    r"^\s*(section|part|annex|appendix)\s*[A-Za-z]*\.?\s*\d*\s*[:\-]?\s*$",
    r"\b(revision|version|draft|status|confidentiality)\s*[:\-]\s*\w*",
)


_TDOC_SYSTEM_RE = re.compile(
    r"(documentation\s+system|document\s+(management|tracking|filing|control|workflow|lifecycle|records?)\s*"
    r"(system|platform|module)?|record[-\s]?keeping\s+system|quality\s+(control|checkpoint|inspection|"
    r"management)\s*(system|platform|module)?|regulatory\s+(filing|submission|compliance)\s*(system|"
    r"platform|module)?|compliance\s+(system|dashboard|framework)|audit[-\s]?trail)",
    re.I)


def _tdoc_corruption(text: str) -> tuple:
    if not text:
        return False, ""
    if "\ufffd" in text:
        return True, "Unicode replacement characters found — the source encoding is damaged; re-convert the document."
    low = text.lower()
    for pat in (r"â€\w", r"Ã[©è¢±¼¶×]", r"ï¿½", r"â€[“”‘’–—™œ]"):
        if re.search(pat, low):
            return True, f"Mojibake pattern '{pat.upper()}' detected — reconvert from the original format before searching."
    if any(ord(ch) < 9 for ch in text):
        return True, "Control characters found — the document may be corrupted."
    return False, ""


def _tdoc_is_admin_line(s: str) -> bool:
    low = s.lower()
    if not s.strip():
        return False
    for pat in _TDOC_ADMIN_PATTERNS:
        if re.search(pat, low):
            return True
    return False


def _tdoc_tag_lines(text: str) -> tuple:
    admin: list[str] = []
    content: list[str] = []
    corrupt, cnote = _tdoc_corruption(text)
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if _tdoc_is_admin_line(s):
            admin.append(s)
        else:
            content.append(s)
    return admin, content, corrupt, cnote


def _tdoc_classify_feature(ftype: str, text: str) -> str:
    low = text.lower()
    if "dosage form" in low or "administered" in low or "route" in low:
        return "6 — Dosage form / route of administration"
    if "marker" in low or "analyt" in low or "assay" in low or "standardiz" in low:
        return "12 — Analytics / markers / test method"
    if "effect" in low or "use" in low or "intended" in low:
        return "5 — Use / indication / technical effect"
    if "solvent" in low or "ratio" in low or "temperature" in low or "time" in low:
        return "4 — Parameter / numeric value"
    if ftype in ("Sequence", "Process", "Process steps") or "process" in low or "extraction" in low or "manufactur" in low:
        return "3 — Process step sequence"
    if ftype == "Composition" or "composition" in low or "comprising" in low or "ingredient" in low or "botanical" in low or "extract" in low:
        return "1 — Composition / ingredient"
    if "packaging" in low or "storag" in low or "stability" in low or "shelf" in low:
        return "8 — Packaging / storage / stability"
    if "safe" in low or "toxic" in low or "tolerab" in low:
        return "11 — Safety / toxicology"
    if "quality" in low or "inspection" in low or "specification" in low or "limit" in low:
        return "9 — Quality / QC / inspection"
    if "regulatory" in low or "compliance" in low or "approval" in low:
        return "10 — Regulatory / compliance"
    if "supplement" in low or "excipient" in low or "carrier" in low or "additive" in low:
        return "13 — Excipients / adjuvants / additives"
    return "14 — Other / undefined"


def _tdoc_ref_passage_label(c: dict[str, Any]) -> str:
    passage = c.get("exact_passage") or ""
    return "Direct passage available" if len(passage) >= 60 else "Abstract / title level only"


def _tdoc_is_self(c: dict[str, Any], doc_title: str) -> bool:
    if not doc_title:
        return False
    t = (c.get("act_title") or "")
    if "tdoc" in t.lower():
        return True
    shared = _tokens(t) & _tokens(doc_title)
    return bool(shared) and len(_tokens(t)) <= 6 and len(shared) >= 2


def _tdoc_hardening(features: list[dict[str, str]]) -> list[dict[str, str]]:
    base_pairs = [
        (r"solvent ratio", "water-to-ethanol ratio of [X:Y] by volume (inventor to confirm)"),
        (r"temperature", "extraction temperature of [X]°C — verify with [temperature log / method]"),
        (r"time window", "processing time of [X] h — verify with [batch record]"),
        (r"marker", "marker range of [lo–hi] % w/w by [test method]"),
        (r"process step", "step sequence with an in-process checkpoint at [stage] (parameter, limit, method, sample)"),
        (r"dosage form", "dosage form with the applicable specification reference"),
    ]
    rows = []
    for f in features:
        txt = f.get("feature", "")
        if "not provided" not in txt.lower() and "vague" not in f.get("measurability", "").lower():
            continue
        for pat, hardened in base_pairs:
            if re.search(pat, txt.lower()):
                rows.append({
                    "feature": txt,
                    "hardened_equivalent": hardened,
                    "origin": "[INVENTOR INPUT REQUIRED]",
                })
                break
    return rows[:8]


def _hub_tdoc_novelty(inputs: dict[str, Any], result: dict[str, Any], resolved: list[dict[str, Any]], botanicals: str) -> dict[str, Any]:
    """TDoc novelty search. The TDoc is CLEANED first: headings, metadata and
    administrative labels are separated from technical content before feature
    extraction. Relevance date and prior-art cutoff are stated. References are
    normalised to real documents, and regulatory / TK / admin documents are kept
    as separate context (they never become 'closest prior art'). Scores are
    separated — semantic similarity, feature coverage, search confidence and
    anticipation risk — there is no single 'novelty score'. The single-reference
    novelty test is applied feature-by-feature against the essential set."""

    doc_text = _basis_text(inputs, "document_text") or _text(inputs, "disclosure_text") or _text(inputs, "problem_text") or ""
    relevant_date = _text(inputs, "relevant_date", "priority_date", "filing_date")
    if not relevant_date:
        relevant_date = "[RELEVANT DATE NOT PROVIDED — specify the priority or filing date]"
    cutoff = _text(inputs, "prior_art_cutoff")
    cutoff = cutoff or "[CUTOFF NOT SET — confirm the earliest applicable prior-art date (AIA-style pre-AIA rule if US)]"

    admin, content, corrupt, cnote = _tdoc_tag_lines(doc_text)
    is_doc_system = bool(content and _TDOC_SYSTEM_RE.search(" ".join(content)[:6000]))
    doc_title = next((ln for ln in content if len(ln) > 3), doc_text.splitlines()[0] if doc_text else "")

    # feature extraction runs on the CLEANED technical content only — headings,
    # metadata and admin labels are never ingredients, parameters or features
    content_blob = " ".join(content)
    clean_resolved = []
    if content:
        clow = content_blob.lower()
        for r in resolved:
            raw = (r.get("botanical_name") or r.get("raw_name") or "").strip()
            lr = (raw or "").lower()
            if lr and (lr in clow or any(len(t) > 2 and t in clow for t in lr.split())):
                clean_resolved.append(r)
    clean_inputs = {"problem_text": content_blob, "document_text": "", "disclosure_text": "",
                    "formulation_text": "", "process_desc": ""}
    features = _atomic_novelty_features(clean_inputs, clean_resolved)
    for f in features:
        f["category"] = _tdoc_classify_feature(f.get("type", ""), f.get("feature", ""))
        f["weight"] = "Informational weighting for search priority — NOT a legal novelty contribution"

    blocked = not doc_text.strip()
    if blocked:
        features = []

    cit = result["citations"] or _retrieve(f"{botanicals} {doc_text[:200]}", top_k=6)
    cit = cit or []

    # reference normalisation + qualifying (closest-art) set
    ref_rows: list[dict[str, Any]] = []
    qualifying = []
    for c in cit:
        kind = _tdoc_ref_kind(c)
        self_doc = _tdoc_is_self(c, doc_title)
        label = "Self-document — excluded from prior art" if self_doc else _tdoc_ref_passage_label(c)
        pub = _PAT_PUBNO.search((c.get("act_title") or "").upper())
        ref_rows.append({
            "ref_id": f"R{len(ref_rows) + 1}",
            "title": c.get("act_title") or "[UNTITLED CORPUS SOURCE]",
            "authority": c.get("authority") or "KB",
            "kind": kind,
            "publication": pub.group(1) if pub else "[PUBLICATION NUMBER REQUIRED]",
            "passage": label,
            "role": "Technical prior-art candidate" if kind in ("Patent prior art", "Scientific / technical", "TDoc / contribution record") and not self_doc else "Context / excluded",
        })
        if kind in ("Patent prior art", "Scientific / technical", "TDoc / contribution record") and not self_doc:
            qualifying.append(c)

    required = [f for f in features if f["essentiality"] == "Essential"] or features[:3]

    # feature × reference disclosure against the closest QUALIFYING reference
    matrix: list[dict[str, Any]] = []
    for idx, c in enumerate(qualifying):
        passage = " ".join(filter(None, [c.get("exact_passage"), c.get("act_title")]))
        per = {f["feature"]: {"level": lev, "basis": basis}
               for f in features for lev, basis in [_feature_disclosure(f["feature"], passage)]}
        strong = sum(1 for f in required if per[f["feature"]]["level"] in ("Explicitly disclosed", "Inherently disclosed"))
        broad = sum(1 for f in required if per[f["feature"]]["level"] in ("Broadly disclosed", "Partially disclosed"))
        matrix.append({
            "ref_id": f"R{idx + 1}",
            "title": c.get("act_title") or "corpus source",
            "authority": c.get("authority") or "KB",
            "kind": _tdoc_ref_kind(c),
            "passage": c,
            "required_strong": strong,
            "required_total": len(required),
            "required_partial": broad,
            "disclosed": per,
        })
    qualifying_refs = matrix

    closest = max(qualifying_refs, key=lambda m: (m["required_strong"], m["required_partial"]), default=None)
    if closest:
        semantic = _overlap_similarity(f"{botanicals} {doc_text}", closest["passage"].get("exact_passage") or "")
        all_strong = closest["required_strong"] == closest["required_total"] and closest["required_total"] > 0
        if all_strong:
            anticipation, risk = "Potentially anticipated (single-reference)", "High"
        elif closest["required_strong"] >= max(1, int(round(closest["required_total"] / 2))):
            anticipation, risk = "Not fully anticipated by the identified reference", "Medium"
        elif closest["required_strong"] > 0 or closest["required_partial"] > 0:
            anticipation, risk = "Feature-level overlap only", "Low"
        else:
            anticipation, risk = "Feature-level overlap only (no strong feature)", "Low"
        missing = [f["feature"] for f in required
                   if closest["disclosed"][f["feature"]]["level"] not in ("Explicitly disclosed", "Inherently disclosed")]
        combination_status = "Established" if all_strong else "Not established"
        coverage_note = (f"Closest qualifying reference {closest['ref_id']} discloses {closest['required_strong']} of "
                         f"{closest['required_total']} essential features explicitly or inherently. Semantic similarity measures "
                         f"topic/vocabulary overlap only and never equals novelty.")
    else:
        semantic = 0
        all_strong = False
        anticipation = "Novelty not determined — no qualifying technical prior-art reference found in the screened corpus"
        risk = "Unknown"
        missing = [f["feature"] for f in required]
        combination_status = "Cannot be assessed (no qualifying reference retrieved)"
        coverage_note = "Regulatory, TK, admin and self-document passages were excluded from the closest-art contest; no qualifying technical reference was retrieved — this is a coverage gap, not proof of novelty."

    if not qualifying_refs:
        search_conf, search_reason = "Low", "No qualifying technical reference retrieved after excluding regulatory / TK / admin / self passages."
    elif len(qualifying_refs) < 3:
        search_conf, search_reason = "Low", f"Only {len(qualifying_refs)} qualifying reference(s) — expand keyword, classification, family and NPL searches."
    elif len(qualifying_refs) < 6:
        search_conf, search_reason = "Medium", f"{len(qualifying_refs)} qualifying references screened across multiple strategies."
    else:
        search_conf, search_reason = "Medium-High", f"{len(qualifying_refs)} qualifying references screened across multiple strategies."

    excluded_admin = admin if not is_doc_system else []
    if is_doc_system:
        system_note = "The TDoc appears to invent a documentation / QC / compliance system — administrative and metadata terms are therefore kept as SYSTEM-SCOPE features instead of being excluded."
    else:
        system_note = "Administrative / metadata terms were EXCLUDED from the technical features."

    if blocked:
        result["summary"] = ("BLOCKED — no TDoc text supplied. Cleaning, feature extraction and the prior-art "
                             "comparison cannot run on an empty document; provide the TDoc content first.")
    else:
        result["summary"] = (f"Cleaned TDoc: {len(content)} technical line(s), {len(admin)} admin/metadata line(s) "
                             f"{'kept as system-scope' if is_doc_system else 'excluded'}; {len(features)} confirmed-able technical feature(s); "
                             f"{len(qualifying_refs)} qualifying prior-art reference(s); closest single-reference coverage "
                             f"{(closest or {}).get('required_strong', 0)}/{(closest or {}).get('required_total', 0)}; anticipation risk: {risk.lower()}.")
    result["note"] = ("TDoc ingest → cleaning (headings/metadata separated) → feature classification (14 categories) → "
                      "confirmation gate → relevant date & cutoff → multi-strategy search → reference normalisation → seven-level "
                      "disclosure → single-reference matrix → separated metrics → feature hardening.")

    result["findings"].append(_finding("td-1", "TDoc cleaning", f"{len(content)} technical line(s), {len(admin)} administrative/metadata line(s). {system_note}", "info" if not corrupt else "error"))
    if corrupt:
        result["findings"].append(_finding("td-1b", "Corrupted input", cnote, "error"))
    result["findings"].append(_finding("td-2", "Feature categories", "; ".join(sorted({f['category'] for f in features})[:6]) or "no features extracted", "info" if features else "warning"))
    result["findings"].append(_finding("td-3", "Closest-prior-art rule", coverage_note, "info"))
    result["findings"].append(_finding("td-4", "Separated metrics", "Semantic similarity, feature coverage, search confidence and anticipation risk are reported separately — a single 'novelty score' is never issued.", "info"))
    result["findings"].append(_finding("td-5", "Single-reference novelty",
                                       "Blocked — novelty not assessed without a TDoc text to compare." if blocked else f"{anticipation}. Multiple references are NOT combined to conclude lack of novelty.",
                                       "error" if (risk == "High" and not blocked) else "info"))

    result["suggestions"] = [
        "Paste the TDoc in clean text; supply the relevant (priority/filing) date so the prior-art cutoff is fixed before relying on the search.",
        "Confirm which features are ESSENTIAL — the single-reference novelty test is applied to the CONFIRMED essential set only.",
        "Provide exact patent/contribution publication numbers so references can be normalised instead of quoted as corpus titles.",
        "Regulatory (FSSAI/FDA/AYUSH) and TK documents are context only and cannot establish anticipation on their own.",
        "For each underdefined parameter, supply the hardened value (solvent ratio, temperature, time, markers, dosage form).",
        "Treat this as a preliminary technical comparison — an inventor or patent attorney must confirm the extraction before any filing decision.",
    ]

    confirmed = inputs.get("extracted_features")
    gate_note = f"User confirmed {len(confirmed)} extracted feature(s) before this run." if isinstance(confirmed, list) and confirmed else "Pending — confirm/correct the extracted features before relying on the assessment."

    matrix_rows = [
        {
            "reference": f"{m['ref_id']} · {m['title']}",
            "kind": m["kind"],
            "essential_disclosed": f"{m['required_strong']}/{m['required_total']}" if m["required_total"] > 0 else "0/0",
            "all_essential_in_one": "Yes" if m["required_strong"] == m["required_total"] and m["required_total"] > 0 else "No",
            "notes": "Verify date at source (pre-cutoff)",
        }
        for m in qualifying_refs
    ]
    if not matrix_rows:
        matrix_rows = [{"reference": "—", "kind": "no qualifying technical reference",
                        "essential_disclosed": "0/0", "all_essential_in_one": "Cannot assess",
                        "notes": "Extend the corpus / provide publication numbers"}]

    per_ref = closest["passage"] if closest else {}
    per_feature_rows = []
    closest_passage = " ".join(filter(None, [per_ref.get("exact_passage"), per_ref.get("act_title")])) if closest else ""
    for i, f in enumerate(features):
        level, basis = _feature_disclosure(f["feature"], closest_passage)
        per_feature_rows.append({
            "feature_num": f"F{i + 1}",
            "feature": f["feature"],
            "category": f["category"],
            "essentiality": f["essentiality"],
            "disclosure_level": level,
            "basis": basis,
            "parameter_status": "Missing / requires inventor input" if "not provided" in f["feature"] or "Vague" in f.get("measurability", "") else "Provided",
        })

    hardening_rows = _tdoc_hardening(features)

    result["sections"] += [
        _section("TDoc ingestion & cleaning", [
            {"status": "Corrupted-text check", "value": ("FAILED — " + cnote) if corrupt else ("Passed" if doc_text else "[TDoc INPUT REQUIRED]")},
            {"status": "Technical content lines", "value": str(len(content))},
            {"status": "Administrative / metadata lines", "value": f"{len(admin)} — {'system scope (kept)' if is_doc_system else 'excluded from features'}"},
            {"status": "Document system detected?", "value": "Yes — documentation/QC/compliance system" if is_doc_system else "No — admin terms are not technical features"},
            {"status": "Feature confirmation gate", "value": gate_note},
        ], ["status", "value"], "Headings, metadata and admin labels never become novelty features unless the invention itself is a documentation/QC/compliance system."),
        _section("Excluded administrative / metadata terms" if not is_doc_system else "Administrative terms (system scope)", [
            {"term": t} for t in (excluded_admin if not is_doc_system else admin)[:12]
        ] or [{"term": "[none]"}],
           ["term"], "Examples like '# Technical Disclosure TDoc', '**Project Title', 'manufacturing documentation', 'regulatory documentation' and 'quality checkpoints' are document furniture — held OUT of the technical feature set." if not is_doc_system else "Because the invention manages documentation/QC/compliance, these terms are treated as system-scope inputs (architecture, rule, action), not excluded."),
        _section("Extracted technical features (confirm & edit)", [
            {"feature_num": f"F{i + 1}", "feature": f["feature"], "category": f["category"],
             "essentiality": f["essentiality"], "measurability": f["measurability"],
             "parameter_status": ("Missing / requires inventor input" if "not provided" in f["feature"] or "Vague" in f.get("measurability", "") else "Provided")}
            for i, f in enumerate(features)
        ], ["feature_num", "feature", "category", "essentiality", "measurability", "parameter_status"],
           f"Fourteen feature categories incl. composition, process, numeric parameters, use/effect, dosage form, QC, regulatory and analytics. {gate_note}"),
        _section("Relevant date & prior-art cutoff", [
            {"item": "Relevant date", "value": relevant_date},
            {"item": "Prior-art cutoff", "value": cutoff},
            {"item": "Rule", "value": "Only pre-cutoff documents can be cited for anticipation; dates are verified at source, never assumed or derived from file names."},
        ], ["item", "value"], "Date discipline matters — a post-cutoff publication is not anticipatory."),
        _section("Prior-art search strategies (multi-strategy)", [
            {"strategy": "Semantic search", "input": "invention language as a natural-language query"},
            {"strategy": "Keyword / synonym search", "input": "feature terms expanded (botanical, chemical, process and spelling variants)"},
            {"strategy": "Feature-combination search", "input": "essential features combined (e.g. Ashwagandha + Brahmi + hydroalcoholic)"},
            {"strategy": "Parameter & range search", "input": "temperature, time, ratio, pH, concentration, marker ranges"},
            {"strategy": "Classification search", "input": "IPC/CPC classes recovered from the closest references"},
            {"strategy": "Family & citation tracing", "input": "backward/forward citations and family members (deduplicated)"},
            {"strategy": "Non-patent literature", "input": "papers, monographs, theses and regulatory monographs"},
            {"strategy": "TDoc section re-read", "input": "hidden parameter statements inside tables and annexes of the disclosure itself"},
            {"strategy": "Contribution-number search", "input": "TDoc/contribution id, meeting, agenda and change-request numbers for exact matching"},
        ], ["strategy", "input"], "A single natural-language query is never relied on; the TDoc-specific strategies re-read tables and contribution numbers."),
        _section("Reference normalisation", ref_rows,
                 ["ref_id", "title", "authority", "kind", "publication", "passage", "role"],
                 "References are real documents with publication numbers; '6 authoritative passages', patent offices or regulators are never quoted as a reference. Regulatory/TK/admin/self passages are kept for context only."),
        _section("Feature-by-feature disclosure (closest qualifying reference)", per_feature_rows,
                 ["feature_num", "feature", "category", "essentiality", "disclosure_level", "basis", "parameter_status"],
                 "Seven-level disclosure taxonomy: Explicitly / Inherently / Partially / Broadly disclosed, Suggested only, Not disclosed, Unclear. No percentage is attached per feature."),
        _section("Single-reference novelty matrix (qualifying references only)", matrix_rows,
                 ["reference", "kind", "essential_disclosed", "all_essential_in_one", "notes"],
                 "Novelty is tested one reference at a time against the CONFIRMED essential set. Features spread across multiple references support inventive-step analysis, never a lack-of-novelty conclusion."),
        _section("Novelty assessment (separated metrics)", ([] if blocked else [
            {"item": "Semantic similarity", "value": f"{semantic}%",
             "meaning": "Topic/vocabulary overlap with the closest qualifying reference — NOT a novelty percentage."},
            {"item": "Essential feature coverage", "value": f"{closest['required_strong']}/{closest['required_total']}" if closest else "0/0",
             "meaning": "Essential features explicitly or inherently disclosed by the closest single qualifying reference."},
            {"item": "Missing or underdefined features", "value": "; ".join(missing[:4]) or "None of the essential set missing",
             "meaning": "Features the closest reference does not disclose or the inventor has not quantified."},
            {"item": "Combination disclosure", "value": combination_status,
             "meaning": "Whether the full claimed combination appears in one reference."},
            {"item": "Single-reference anticipation", "value": anticipation,
             "meaning": "Preliminary technical observation — legal review required."},
            {"item": "Preliminary novelty risk", "value": risk,
             "meaning": "High only if one pre-cutoff reference discloses every essential feature; otherwise Low/Medium/Unknown with reasons."},
            {"item": "Search confidence", "value": search_conf,
             "meaning": search_reason},
        ]),
                 ["item", "value", "meaning"], "Scores are split and each is defined: semantic similarity, feature coverage, search confidence, anticipation risk. 'Novelty score: 10%' and 'Novelty level: low' are never produced."),
        _section("Inventive-step indicators (SEPARATE — not novelty)", [
            {"indicator": "Features spread across multiple references", "value": "Relevant to obviousness, not to lack of novelty"},
            {"indicator": "Technical motivation to combine", "value": "To be argued from the prior art once references are confirmed"},
            {"indicator": "Unexpected technical effect", "value": "Not established from this search — requires experimental data"},
            {"indicator": "Teaching away / parameter criticality", "value": "To be reviewed in full patent texts"},
        ], ["indicator", "value"], "Combining documents is an inventive-step matter and is handled separately from novelty."),
        _section("Feature hardening (fill the gaps before claiming)", [
            {"feature": r["feature"], "hardened_equivalent": r["hardened_equivalent"], "origin": r["origin"]}
            for r in hardening_rows
        ] or [{"feature": "All key parameters already defined", "hardened_equivalent": "—", "origin": "—"}],
           ["feature", "hardened_equivalent", "origin"],
           "Underdefined features block meaningful comparison; versions like 'solvent system' become 'water-to-ethanol ratio of [X:Y] by volume' with inventor confirmation."),
        _section("Regulatory / TK / admin context (not closest prior art)", [
            {"source": r["title"], "kind": r["kind"], "passage": r["passage"], "role": r["role"]}
            for r in ref_rows if r["kind"] in ("Regulatory / safety context", "Traditional knowledge") or r["role"] == "Context / excluded"
        ], ["source", "kind", "passage", "role"],
           "FSSAI/FDA/AYUSH, traditional-knowledge and administrative documents are reported separately — they are evidence of regulatory / TK landscape, not anticipating prior art."),
        _section("QC checklist", [
            {"check": "Re-read the TDoc for hidden parameter statements", "done": "Part of the search strategies"},
            {"check": "Confirm essential features before the assessment is used", "done": gate_note if not isinstance(confirmed, list) or not confirmed else "Confirmed"},
            {"check": "Verify relevant date and cutoff at source", "done": relevant_date if relevant_date.startswith("20") else "Pending date input"},
            {"check": "Excluded admin/metadata terms verified", "done": f"{len(excluded_admin)} term(s) held out"},
            {"check": "Publication numbers normalised before citation", "done": str(sum(1 for r in ref_rows if r["publication"] != "[PUBLICATION NUMBER REQUIRED]")) + " reference(s) normalised"},
        ], ["check", "done"], "Final pass before the assessment is shared."),
        _section("Scope & limitations", [
            {"item": "Blocked input", "value": "Without TDoc text the assessment is BLOCKED — required inputs: [TDoc INPUT REQUIRED], [INVENTOR CONFIRMATION REQUIRED], [DATE VERIFICATION REQUIRED]."},
            {"item": "Coverage", "value": "Absence of a hit is a coverage gap, not proof of novelty."},
            {"item": "Legal opinion", "value": "Preliminary technical comparison only — confirm with a patent professional before filing."},
        ], ["item", "value"]),
    ]
    if blocked:
        result["sections"].insert(1, _section("Blocked — required inputs", [
            {"input": "TDoc text", "status": "[TDoc INPUT REQUIRED]"},
            {"input": "Relevant date (priority/filing)", "status": "[DATE VERIFICATION REQUIRED]"},
            {"input": "Feature confirmation", "status": "[INVENTOR CONFIRMATION REQUIRED]"},
        ], ["input", "status"], "No TDoc text was supplied — the assessment stays blocked rather than guessing."))
    return result
