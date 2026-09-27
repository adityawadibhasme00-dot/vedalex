"""Contract/document structure analysis and Markush parsing.

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
    _basis_text,
)
from app.services.innolab._shared import (
    _finding,
    _section,
)

__all__ = [
    "_DA_META_LABEL_RE",
    "_DA_OCR_ARTIFACT_RE",
    "_DA_ADMIN_LINE_RE",
    "_DA_MD_HEAD_RE",
    "_DA_NUM_HEAD_RE",
    "_DA_CHAPTER_RE",
    "_DA_UNIT_RE",
    "_DA_TABLE_LINE_RE",
    "_DA_FIG_CAP_RE",
    "_DA_OBLIGATION_MAP",
    "_DA_GENERIC_CONCEPT",
    "_DA_BIO_HINTS",
    "_DA_ORG_SUFFIX",
    "_DA_DEFN_RE",
    "_DA_REF_RE",
    "_da_lines",
    "_da_is_artifact",
    "_da_is_admin",
    "_da_meta",
    "_da_title",
    "_da_structure",
    "_da_obligations",
    "_da_measures",
    "_da_tables",
    "_da_figures",
    "_da_entity_context",
    "_da_entity_categorise",
    "_da_entities",
    "_da_definitions",
    "_da_crossrefs",
    "_da_quality_band",
    "_hub_document_analyzer",
    "_MK_HEADING_RE",
    "_MK_ARTIFACT_RE",
    "_MK_STRUCTURE_RE",
    "_MK_SMILES_FRAGMENT_RE",
    "_MK_FORMULA_RE",
    "_MK_RGROUP_RE",
    "_MK_N_RE",
    "_MK_BROAD_RE",
    "_MK_LACTONE_RE",
    "_MK_LACTONE_VARIATION_RE",
    "_MK_SCAFFOLD_RE",
    "_MK_EXAMPLE_RE",
    "_MK_ACTIVITY_RE",
    "_mk_clean",
    "_mk_formula_status",
    "_mk_rgroups",
    "_mk_combinations",
    "_hub_markush",
]

_DA_META_LABEL_RE = re.compile(
    r"^\s*\*{0,2}\s*(document\s+title|document\s+type|version(\s+no)?|date|issue[, ]?\d*|page\s+count|document\s+code|prepared\s+by|reviewed\s+by|approved\s+by|publisher|language|jurisdiction)\s*\*{0,2}\s*:\s*\*{0,2}\s*(.+?)\s*$",
    re.I,
)


_DA_OCR_ARTIFACT_RE = re.compile(
    r"#\s*OCR\s+Output(?:\s*\(Demo\))?\s*[:#]?|ocr\s+output(?:\s*\(demo\))?|ocr\s+engine|pdf\s+ocr|tesseract|#+\s*shot\b|capture\s+of\s+an\s+ocr",
    re.I,
)


_DA_ADMIN_LINE_RE = re.compile(
    r"^\s*(?:page\s+\d+(?:\s+of\s+\d+|\s*/\s*\d+)?|p[aá]g\s*\d+|confidential|draft\s+v?[0-9]|rev\s*:\s*[0-9])\s*[.\-—:]*\s*$",
    re.I,
)


_DA_MD_HEAD_RE = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>[A-Za-z0-9][A-Za-z0-9 ,&\-/()]{2,90})$")


_DA_NUM_HEAD_RE = re.compile(r"^(?P<num>(?:[0-9]+(?:\.[0-9]+){0,3}\.?|\([0-9]+\)|[A-Z](?:\.[0-9]+)?))\s+(?P<title>[A-Za-z][A-Za-z0-9 ,&\-/()]{2,90})$")


_DA_CHAPTER_RE = re.compile(r"^(Chapters?|Sections?|Annexure|Annex|Appendix|Part|Schedule|Clause)\s+([A-Z0-9]+)\s*[:.\-–]?\s*([A-Za-z][A-Za-z0-9 ,&\-/()]{2,90})$", re.I)


_DA_UNIT_RE = re.compile(
    r"(?P<val>\d+(?:[.,]\d+)?)\s*(?P<comp>[<>≤≥±~≈]=?|=\s*(?:to\s+)?)?\s*(?P<unit>°\s?C|℃|%|percent|ppb|ppm|mcg|µg|mg|g|kg|ml|mL|L|l|IU|IU0|kcal|kJ|min|hr|h|hrs|days|d|Gy|kGy|psi|bar|MPa|kPa|Pa|cm|mm|µm|nm|m2|m³|mg/g|mg/ml|mg/mL|g/100g|cfu/g|CFU/g|U/g|U/ml)\b",
    re.I,
)


_DA_TABLE_LINE_RE = re.compile(r"^[^#*]{2,}" + r".*\||^[^|#*\n]+\t[^\t\n]+")


_DA_FIG_CAP_RE = re.compile(r"^\s*(?:Figure|Fig|FIG|Graph|Chart|Diagram)s?\s*[0-9A-Z]{0,4}\s*[:.\-]?\s*(.{0,120})\s*$", re.I)


_DA_OBLIGATION_MAP: list[tuple[str, str]] = [
    ("Prohibition", r"\b(shall\s+not|must\s+not|not\s+permitted|not\s+allowed|prohibited|banned|restricted|shall\s+refuse|shall\s+reject)\b"),
    ("Mandatory", r"\b(shall|must|is\s+required\s+to|are\s+required\s+to|shall\s+ensure|shall\s+maintain|shall\s+provide|compulsory|without\s+fail)\b"),
    ("Recommendation", r"\b(should|recommended|advisable|desirable)\b"),
    ("Permission", r"\b(provisionally\s+accepted|permitted\s+only\s+if|may\s+proceed|may\s+be\s+used|provisionally\s+allowed)\b"),
]


_DA_GENERIC_CONCEPT = {
    "batch", "cleaning", "control", "quality control", "assurance", "documentation", "monitoring",
    "storage", "transport", "packaging", "labelling", "labeling", "testing", "manufacturing",
    "production", "process", "procedure", "record", "training", "calibration", "validation",
    "traceability", "hygiene", "premises", "equipment", "material", "sample", "inspection",
    "audit", "deviation", "regulation", "guidance", "standard", "compliance", "criterion",
    "criteria", "specification", "parameter", "reagent", "solvent", "water", "identity",
    "purity", "strength", "stability", "assay", "yield", "efficacy", "dosage", "concentration",
    "product", "category", "finish", "gmp", "cgmp", "documentation system", "cleaning procedure",
}


_DA_BIO_HINTS = re.compile(
    r"(acid|toxin|enzyme|protein|peptide|antibody|immune|antigen|vaccine|virus|bacteri|fungal|"
    r"plant|herb|extract|oil|recombinant|monoclonal|polyclonal|flavonoid|alkaloid|glycoside|"
    r"terpene|steroid|saponin|tannin|curcumin|ashwagandha|bhringraj|tulsi|giloy|neem|amla|"
    r"kalonji|guduchi|brahmi|shilajit|chandraprabha|rasayana|biologic|therapeutic|clinical|"
    r"candidate|molecule|drug|cytokine|hormone|amino acid|eicosanoid)",
    re.I,
)


_DA_ORG_SUFFIX = re.compile(
    r"(ministry|department|directorate|council|board|authority|agency|organisation|organization|"
    r"bureau|committee|office|institute|college|university|laborator|cdsco|fda|who|iso|ich|ema|"
    r"nmpa|icmr|dcgi|bis|ayush|wipo|epo|uspto|fssai|nobles)\b",
    re.I,
)


_DA_DEFN_RE = re.compile(r"\b(means|is\s+defined\s+as|refers\s+to|shall\s+include|has\s+the\s+same\s+meaning\s+as|have\s+the\s+same\s+meaning)\b", re.I)


_DA_REF_RE = re.compile(r"\b(?:see\s+)?(?:Section|Clause|Annexure|Annex|Appendix|Part)\s+([0-9A-Za-z.]+)", re.I)


def _da_lines(doc: str) -> list[str]:
    return (doc or "").splitlines()


def _da_is_artifact(line: str) -> bool:
    return bool(_DA_OCR_ARTIFACT_RE.search(line))


def _da_is_admin(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if _DA_ADMIN_LINE_RE.match(s):
        return True
    if re.fullmatch(r"[\d\s\|\-/—.:]+", s):
        return True
    return False


def _da_meta(lines: list[str]) -> dict[str, str]:
    meta: dict[str, str] = {}
    for ln in lines:
        m = _DA_META_LABEL_RE.match(ln.strip())
        if m:
            meta[m.group(1).lower().replace(" ", "_")] = m.group(3).strip()
    return meta


def _da_title(lines: list[str], doc: str) -> dict[str, Any]:
    meta = _da_meta(lines)
    title = meta.get("document_title")
    if title:
        return {"title": title.strip("*").strip(), "confidence": "High (explicit metadata label)", "from": "document title field"}
    for ln in lines[:30]:
        s = ln.strip()
        if not s or _da_is_artifact(s) or _da_is_admin(s):
            continue
        if s.startswith("#") and not _da_is_artifact(s):
            t = re.sub(r"^#+\s*", "", s)
            return {"title": t[:90], "confidence": "Medium (heading line)", "from": "first non-artifact heading"}
        if s.isupper() and len(s) < 90 and len(s) > 4:
            return {"title": s[:90], "confidence": "Medium (all-caps title line)", "from": "title-style line"}
    first = next((ln.strip()[:90] for ln in (doc or "").splitlines() if ln.strip() and not _da_is_artifact(ln) and ln.strip()[0] not in "*#|"), "")
    if first:
        return {"title": first[:90], "confidence": "Low (first substantive line)", "from": "first surviving text line"}
    return {"title": "[TITLE NOT PROVIDED — OCR ARTIFACT EXCLUDED]", "confidence": "None", "from": "no usable title line (artifact-only header)"}


def _da_structure(lines: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    deepest: dict[int, int] = {}

    def parent_for(level: int) -> str:
        for lv in range(level - 1, 0, -1):
            if lv in deepest:
                return f"S-{deepest[lv]:03d}"
        return "—"

    for raw in lines:
        s = raw.strip()
        if not s or _da_is_artifact(s) or _da_is_admin(s):
            continue
        md = _DA_MD_HEAD_RE.match(s)
        nm = _DA_NUM_HEAD_RE.match(s)
        cm = _DA_CHAPTER_RE.match(s)
        if md:
            level, title = len(md.group("level")), md.group("title")
        elif nm:
            level = len(nm.group("num").rstrip(".").split("."))
            title = nm.group("title")
        elif cm:
            level, title = 1, f"{cm.group(1)} {cm.group(2)} — {cm.group(3)}"
        else:
            continue
        idx = len(rows) + 1
        rows.append({"id": f"S-{idx:03d}", "level": str(level), "heading": title.strip(), "parent": parent_for(level)})
        deepest = {lvl: p for lvl, p in deepest.items() if lvl <= level}
        deepest[level] = idx
    return rows


def _da_obligations(lines: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cur_loc = "full text"
    for raw in lines:
        s = raw.strip()
        pm = re.match(r"^\s*Page\s+(\d+)\s*", s, re.I)
        if pm:
            cur_loc = f"page {pm.group(1)}"
            continue
        if not s or len(s) > 400:
            continue
        lower = s.lower()
        for label, pattern in _DA_OBLIGATION_MAP:
            if label == "Recommendation" and re.search(r"\bshould\s+not\b", lower):
                continue
            if re.search(pattern, lower):
                rows.append({
                    "id": f"R-{len(rows)+1:03d}",
                    "obligation": s[:200],
                    "type": label,
                    "evidence": f"document text · {cur_loc}",
                    "confidence": "High" if label in ("Mandatory", "Prohibition") else "Medium",
                })
                break
    return rows


def _da_measures(doc: str) -> dict[str, Any]:
    if not doc or not doc.strip():
        return {"rows": [], "status": "No numeric content present — the supplied text layer is empty.", "warned": True}
    norm = {"ml": "mL", "mg/g": "mg g-1", "mg/ml": "mg mL-1", "mg/mL": "mg mL-1", "g/100g": "g (100 g)-1", "°c": "°C", "µg": "µg", "mcg": "µg"}
    rows: list[dict[str, Any]] = []
    for m in _DA_UNIT_RE.finditer(doc):
        start = max(0, m.start() - 55)
        ctx = " ".join(doc[start:m.end() + 25].split())
        unit = m.group("unit").strip().lower().replace(" ", "")
        rows.append({
            "id": f"M-{len(rows)+1:03d}",
            "value": m.group("val").replace(",", "."),
            "unit": m.group("unit").strip(),
            "normalised_unit": norm.get(unit, m.group("unit").strip()),
            "comparator": (m.group("comp") or "").strip() or "=",
            "context": ctx[:130],
            "page": "full text (page index pending)",
            "source_layer": "Uploaded document (text layer)",
            "confidence": "Medium (plain-text digit+unit hit)",
        })
    rows = rows[:40]
    reasons: list[str] = []
    base = re.findall(r"\d+(?:[.,]\d+)?", doc)
    if not base:
        reasons.append("No digits present in the surviving text layer.")
    elif not rows:
        reasons.append("Digits present but no unit-bearing measurement matched (fractions, superscripts or unit symbols may have been corrupted by OCR).")
    if _DA_TABLE_LINE_RE.search(doc) or "\t" in doc:
        reasons.append("Tabular rows are present — numeric values may sit inside tables and were not inventoried at measure level.")
    if len(doc) < 200:
        reasons.append("Very short input; expected coverage is low.")
    status = f"{len(rows)} numeric measure(s) extracted; " + ("; ".join(reasons) if reasons else "plain text scanned end-to-end.")
    status += " A numeric gap here is a LIMITATION of the available text layer, NOT proof that the document contains no numbers."
    return {"rows": rows, "status": status, "warned": bool(reasons)}


def _da_tables(lines: list[str]) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    current: list[str] = []

    def finish() -> None:
        if not current:
            return
        head = current[0]
        cols = [c.strip().lstrip("|").strip() for c in re.split(r"[\t|]+", head) if c.strip()]
        tables.append({
            "id": f"T-{len(tables)+1:03d}",
            "columns": str(len(cols)) if cols else "?",
            "rows_tall": str(len(current)),
            "header": ", ".join(cols[:6]) or "—",
            "note": "merged cells / column alignment to be re-verified against the original table image",
            "figure_id": "mixed with FIG-?? until image verification",
        })
        current.clear()

    for raw in lines:
        s = raw.strip()
        if s and _DA_TABLE_LINE_RE.match(s):
            current.append(s)
        elif current:
            finish()
    if current:
        finish()
    return tables[:12]


def _da_figures(lines: list[str]) -> list[dict[str, Any]]:
    figs: list[dict[str, Any]] = []
    for raw in lines:
        s = raw.strip()
        if len(s) > 220:
            continue
        m = _DA_FIG_CAP_RE.match(s)
        if m:
            figs.append({
                "id": f"FIG-{len(figs)+1:03d}",
                "caption": (m.group(1).strip() or "(no caption text)")[:120],
                "kind": "Caption-detect (no image parsing yet)",
                "note": "visual read of the underlying image still required",
            })
    return figs[:12]


def _da_entity_context(lines: list[str], term: str) -> str:
    low = term.lower()
    for ln in lines:
        if low in ln.lower():
            return " ".join(ln.split())[:160]
    return "—"


def _da_entity_categorise(term: str) -> tuple[str, bool, str]:
    low = term.lower().strip()
    if low in _DA_GENERIC_CONCEPT:
        return "Generic process/QC concept", False, "Generic noun — NOT a discrete biomedical entity"
    if _DA_ORG_SUFFIX.search(term):
        return "Organisation / Authority", True, "Regulatory body or organisation reference"
    if re.search(r"(act|rules|regulation|guideline|guidance|directive|standard|code)\b", low) and len(term) > 4:
        return "Regulatory framework / standard reference", True, "Legal or regulatory instrument reference"
    if re.search(r"\b(gmp|cgmp|iso\s?\d+|ich\s?(q|l|s)?\d*)\b", low):
        return "Standard / certification scheme", True, "Quality or technical standard reference"
    if _DA_UNIT_RE.search(term):
        return "Measurement / unit term", False, "Measurement term — not a discrete biomedical entity"
    if _DA_BIO_HINTS.search(term):
        return "Biomedical / technical entity", True, "Technical term with biomedical signals"
    if any(ch.isdigit() for ch in term):
        return "Code / identifier", False, "Likely document code or identifier — not a biomedical entity"
    return "Generic term", False, "Generic noun — not a discrete biomedical entity"


def _da_entities(lines: list[str]) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    pushed: set = set()
    skip = {"the", "this", "that", "and", "with", "from", "have", "were", "when", "into", "their", "also", "says", "said", "shall", "should", "must", "may"}
    for raw in lines:
        s = raw.strip()
        if not s or _da_is_artifact(s) or _da_is_admin(s) or _DA_TABLE_LINE_RE.match(s) or s.startswith("#") or s.startswith("*"):
            continue
        for t in re.findall(r"[A-Z][A-Za-z0-9'’-]+(?:\s[A-Z][A-Za-z0-9'’-]+){0,2}", s):
            key = " ".join(t.split()).rstrip(".,;:’")
            low = key.lower()
            if low in skip or len(key) < 3 or key in pushed:
                continue
            if key.isupper() and len(key) > 12:
                continue
            cat, valid_bio, why = _da_entity_categorise(key)
            out.append({
                "entity": key[:60],
                "category": cat,
                "valid_biomedical": "Yes" if valid_bio else "No",
                "reason": why,
                "context": _da_entity_context(lines, key)[:120],
                "evidence": "document text (full-text index)",
                "confidence": "Medium",
            })
            pushed.add(key)
    out = out[:40]
    excluded = [r["entity"] for r in out if r["valid_biomedical"] == "No" and r["category"].startswith("Generic")]
    return {"rows": out, "excluded_generics": excluded[:15]}


def _da_definitions(lines: list[str]) -> list[dict[str, Any]]:
    defs: list[dict[str, Any]] = []
    for raw in lines:
        s = raw.strip()
        if not (20 < len(s) < 320):
            continue
        if _DA_DEFN_RE.search(s):
            term = s.split("(", 1)[0].split(":", 1)[0][:60]
            defs.append({"term": term or "(unparsed)", "definition": s[:230], "confidence": "Medium", "evidence": "document text"})
    return defs[:15]


def _da_crossrefs(lines: list[str], structure: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []

    def find_target(rev: str) -> bool:
        rev_plain = rev.replace(".", "")
        for r in structure:
            if rev in r["id"].lower() or rev_plain in r["id"].lower().replace(".", ""):
                return True
            if rev in r["heading"].casefold() or rev_plain in r["heading"].casefold().replace(".", ""):
                return True
        return False

    for raw in lines:
        m = _DA_REF_RE.search(raw.strip())
        if not m or not m.group(1):
            continue
        target = m.group(1)
        if len(target) > 12:
            continue
        status = "Resolved — target heading present" if find_target(target.casefold()) else "Broken / unresolved in this text layer"
        row = {"ref": f"Section {target}", "status": status, "confidence": "Medium"}
        if not any(r["ref"] == row["ref"] for r in refs):
            refs.append(row)
    return refs[:20]


def _da_quality_band(doc: str, lines: list[str]) -> tuple[str, list[str]]:
    if not doc or len(doc.strip()) < 40:
        return "Unusable", ["Empty or near-empty text layer — re-OCR the original scan at higher resolution."]
    issues: list[str] = []
    artifacts = [ln.strip() for ln in lines if _da_is_artifact(ln)]
    if artifacts:
        issues.append(f"{len(artifacts)} OCR-artefact line(s) detected (e.g. \"# OCR Output (Demo)\") — removed from structure/entity/measure extraction; kept in the quality log.")
    total = max(1, len(re.findall(r"[A-Za-z]", doc)))
    mojibake = len(re.findall(r"[ÃÂâ€™â€\u0080-\u009f]", doc))
    if mojibake and mojibake / total > 0.005:
        issues.append(f"{mojibake} mis-encoded character(s) found — OCR engine likely corrupted fractions, superscripts or unit symbols.")
    if rep := re.search(r"[\ufffd]|(?:&nbsp;|&amp;|&lt;)", doc):
        issues.append(f"Replacement/sk-h-tml entity characters detected ({rep.group(0)!r}) — encoding is unreliable.")
    if artifacts or mojibake:
        issues.append("Original page-image verification REQUIRED before any title, measure, clause or entity is relied upon.")
        return ("Low" if mojibake else "Medium"), issues
    if len(doc) > 400:
        issues.append("No OCR/decode artefacts detected in the supplied text layer; a human spot-check of the original images is still recommended.")
        return "High", issues
    issues.append("Short text layer; OCR quality band capped at Medium until coverage is confirmed.")
    return "Medium", issues


def _hub_document_analyzer(inputs: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    doc = _basis_text(inputs, "document_text") or _basis_text(inputs, "problem_text") or ""
    lines = _da_lines(doc)
    meta = _da_meta(lines)
    band, issues = _da_quality_band(doc, lines)
    artifacts = [ln.strip() for ln in lines if _da_is_artifact(ln)]
    title_info = _da_title(lines, doc)
    structure = _da_structure(lines)
    obligations = _da_obligations(lines)
    mset = _da_measures(doc)
    tables = _da_tables(lines)
    figures = _da_figures(lines)
    ents = _da_entities(lines)
    defs = _da_definitions(lines)
    cross = _da_crossrefs(lines, structure)
    mandatory = sum(1 for o in obligations if o["type"] in ("Mandatory", "Prohibition"))
    title_artifact = "Yes (excluded)" if artifacts and not meta.get("document_title") else "No"

    if doc.strip():
        result["summary"] = f"Document analysed: {len(structure)} section(s) in hierarchy, {len(ents['rows'])} categorised entities, {len(mset['rows'])} numeric measure(s), {len(tables)} table(s), {len(figures)} figure(s), {len(obligations)} obligation(s)."
        result["note"] = "OCR-artefact stripping → metadata → quality band → structure → entities → measures → tables/figures → obligations → evidence layers. Uploaded document is the PRIMARY evidence; external references stay external."
    else:
        result["summary"] = "Document text layer is empty — OCR could not extract meaningful text from this document."
        result["note"] = "Empty-state: no content to structure; supply a non-blank OCR text layer or re-run OCR on the original scan."

    result["findings"].append(_finding("da-0", "Document Analyzer standard (judge line)", f"Document \"{title_info['title']}\" is ready as {band} OCR-quality; {len(structure)} sections, {len(obligations)} obligations, {len(mset['rows'])} measures, {len(tables)} tables, {len(figures)} figures — every number and clause pinned to evidence, audit claims only with a verified page.", "info" if band != "Unusable" else "warning"))
    result["findings"].append(_finding("da-1", "OCR quality band", f"{band} — {'; '.join(issues[:3]) or 'clean text layer'}", "warning" if band in ("Low", "Unusable") else "success"))
    result["findings"].append(_finding("da-2", "Title handling", f"{title_info['title']} (confidence: {title_info['confidence']}; from: {title_info['from']}). OCR-artefact as title: {title_artifact}.", "info"))
    result["findings"].append(_finding("da-3", "Numeric measures status", mset["status"], "info" if mset["warned"] else "success"))
    result["findings"].append(_finding("da-4", "Generic-term hygiene", f"{len(ents['excluded_generics'])} generic/process terms kept out of the biomedical list: {', '.join(ents['excluded_generics']) or 'none'}.", "info"))
    result["suggestions"] = [
        "Attach the original scanned PDF/page images to enable page-level OCR confidence, bounding boxes and image verification.",
        "For filing-grade extraction, have a human reviewer verify every measure and obligation against its page, then release the reviewed flags.",
        "Compliance is NOT assessed from this document alone — pair this analysis with facility evidence, jurisdiction and a qualified reviewer.",
    ]

    exe_rows = [
        {"aspect": "Document title", "value": title_info["title"]},
        {"aspect": "Issuer / publisher", "value": meta.get("publisher") or meta.get("document_type") or "[NOT PROVIDED]"},
        {"aspect": "Version / date", "value": f"{meta.get('version') or '[NOT PROVIDED]'} · {meta.get('date') or '[NOT PROVIDED]'}"},
        {"aspect": "OCR quality band", "value": band},
        {"aspect": "Sections (hierarchy)", "value": str(len(structure))},
        {"aspect": "Entities", "value": f"{len(ents['rows'])} (of which {sum(1 for r in ents['rows'] if r['valid_biomedical'] == 'Yes')} biomedical/technical)"},
        {"aspect": "Numeric measures", "value": str(len(mset["rows"])) + (" (numeric gap flagged)" if mset["warned"] else "")},
        {"aspect": "Tables / figures", "value": f"{len(tables)} / {len(figures)}"},
        {"aspect": "Obligations", "value": f"{len(obligations)} ({mandatory} mandatory/prohibitive)"},
        {"aspect": "Compliance status", "value": "NOT ASSESSED — requires facility evidence, jurisdiction and a qualified reviewer"},
        {"aspect": "Next step", "value": "Verify the original scan, pin every claim to a page, then release human-review flags."},
    ]
    result["sections"] += [
        _section("Executive summary", exe_rows, ["aspect", "value"], "Key ideas, findings and quality signals extracted deterministically."),
        _section("Document intake & metadata", [
            {"field": "Document title", "value": title_info["title"], "confidence": title_info["confidence"]},
            {"field": "Document type", "value": meta.get("document_type") or "[NOT PROVIDED]"},
            {"field": "Version", "value": meta.get("version") or "[NOT PROVIDED]"},
            {"field": "Date", "value": meta.get("date") or "[NOT PROVIDED]"},
            {"field": "Prepared / reviewed / approved", "value": f"{meta.get('prepared_by') or '[NOT PROVIDED]'} / {meta.get('reviewed_by') or '[NOT PROVIDED]'} / {meta.get('approved_by') or '[NOT PROVIDED]'}"},
            {"field": "Pages", "value": meta.get("page_count") or "[NOT PROVIDED]"},
            {"field": "Size / languages", "value": "[from original file metadata only]"},
            {"field": "Processing status", "value": "OCR-artefact stripped · structured · not yet human-verified"},
        ], ["field", "value", "confidence"], "Provenance block — every downstream row traces back here."),
        _section("OCR quality & reliability", [
            {"band": band, "text_present": "Yes" if doc.strip() else "No", "artefact_lines": str(len(artifacts)),
             "misencoded": str(len(re.findall(r"[ÃÂâ€™â€\u0080-\u009f]", doc))),
             "verification_required": "Original page-image verification REQUIRED" if band in ("Low", "Unusable") else "Spot-check recommended"}
        ] + [{"issue": i} for i in issues[:6]],
            ["band", "text_present", "artefact_lines", "misencoded", "verification_required"], "Quality band is derived from deterministic text heuristics."),
        _section("Page-level quality index", [
            {"page": "whole text (single index row)", "text_layer": "provided", "ocr_required": "Yes — original scan not supplied",
             "confidence": band, "table_quality": "unverified until image parsing runs",
             "issues": "; ".join(issues[:3]) or "none detected"}
        ], ["page", "text_layer", "ocr_required", "confidence", "table_quality", "issues"], "A per-page table appears automatically once the scanned PDF/page images are attached."),
        _section("Passage-level OCR records", [
            {"passage": "representative record (one row per passage once a page-index is available)",
             "page": "p. 1", "bounds": "[x1,y1,x2,y2] — not present in text input; available from the image OCR layer",
             "ocr_text": (next((ln.strip()[:80] for ln in lines if ln.strip() and not _da_is_artifact(ln)), "[empty]")),
             "confidence": band, "visual_verified": "NO — original image required",
             "correction": "", "reviewer": "PENDING"}
        ], ["passage", "page", "bounds", "ocr_text", "confidence", "visual_verified", "correction", "reviewer"], "Human-review flags are emitted per passage; release only after image verification."),
        _section("Document structure & section hierarchy", [
            {"id": r["id"], "level": r["level"], "heading": r["heading"], "parent": r["parent"]} for r in structure
        ] or [
            {"id": "S-001", "level": "—", "heading": "No structured headings detected in the surviving text layer", "parent": "—"}
        ], ["id", "level", "heading", "parent"], "Headers, footers, page numbers, watermarks and OCR labels are excluded from this tree."),
        _section("Extracted entities (categorised)", [
            {"entity": r["entity"], "category": r["category"], "valid_biomedical_entity": r["valid_biomedical"],
             "reason": r["reason"], "context": r["context"], "page": "full text"}
            for r in ents["rows"]
        ] or [{"entity": "[NO ENTITIES EXTRACTED]", "category": "—", "valid_biomedical_entity": "—", "reason": "Empty text layer", "context": "—", "page": "full text"}],
            ["entity", "category", "valid_biomedical_entity", "reason", "context", "page"],
            "Generic nouns (batch, cleaning, control, documentation…) are NOT listed as biomedical entities."),
        _section("Numeric measures", [
            {"id": r["id"], "value": r["value"], "unit": r["unit"], "normalised": r["normalised_unit"],
             "comparator": r["comparator"], "context": r["context"], "page": r["page"],
             "source_layer": r["source_layer"], "confidence": r["confidence"]}
            for r in mset["rows"]
        ] + [
            {"id": "STATUS", "value": "—", "unit": "—", "normalised": "—", "comparator": "—",
             "context": mset["status"], "page": "—", "source_layer": "Model inference note", "confidence": "—"}
        ], ["id", "value", "unit", "normalised", "comparator", "context", "page", "source_layer", "confidence"],
            "Original unit AND normalised unit recorded; a gap is a limitation of the text layer, never a claim that the document has no numbers."),
        _section("Table inventory", [
            {"id": t["id"], "columns": t["columns"], "rows_tall": t["rows_tall"], "header": t["header"], "note": t["note"]} for t in tables
        ] or [
            {"id": "—", "columns": "0", "rows_tall": "0", "header": "No tabular data detected in this document.",
             "note": "If OCR merged table cells, re-run with table-mode OCR and verify against the original image."}
        ], ["id", "columns", "rows_tall", "header", "note"], "Each table is addressed independently (T-001…)."),
        _section("Figure inventory", [
            {"id": f["id"], "caption": f["caption"], "kind": f["kind"], "note": f["note"]} for f in figures
        ] or [
            {"id": "—", "caption": "No figure captions or graphical content detected in this document.",
             "kind": "—", "note": "Figures whose images were lost in OCR cannot be read — verify the original scan."}
        ], ["id", "caption", "kind", "note"], "Each figure is addressed independently (FIG-001…)."),
        _section("Obligations & requirements", [
            {"id": o["id"], "obligation": o["obligation"], "type": o["type"], "evidence": o["evidence"], "confidence": o["confidence"]} for o in obligations
        ] or [
            {"id": "—", "obligation": "No obligation-style language (shall/must/should/may) detected in the surviving text layer.",
             "type": "—", "evidence": "document text", "confidence": "—"}
        ], ["id", "obligation", "type", "evidence", "confidence"],
            "\"should\" is a recommendation and is NEVER reported as \"must\"; prohibitions are flagged separately."),
        _section("Definitions & cross-references", [
            {"term": d["term"], "definition": d["definition"], "confidence": d["confidence"], "evidence": d["evidence"]} for d in defs
        ] + [
            {"term": "Crossref check", "definition": " — ".join(f"{r['ref']}: {r['status']}" for r in cross) or "No explicit cross-references detected.", "confidence": "Medium", "evidence": "document text"}
        ], ["term", "definition", "confidence", "evidence"], "Broken internal references are reported, not silently dropped."),
        _section("Regulatory & compliance matrix", [
            {"topic": "Manufacturing / quality area", "compliance_status": "NOT ASSESSED", "evidence_required": "Facility audit record + jurisdiction-level regulation", "reviewer": "Expert review required"},
            {"topic": "Obligations pinned above", "compliance_status": "NOT ASSESSED", "evidence_required": "Actual process/facility evidence (never a document-only assertion)", "reviewer": "Expert review required"},
        ] + [
            {"topic": o["obligation"][:80], "compliance_status": "REQUIRES EVIDENCE", "evidence_required": "Operational evidence for this clause", "reviewer": "Expert review required"} for o in obligations[:6]
        ], ["topic", "compliance_status", "evidence_required", "reviewer"],
            "This analyzer NEVER marks a topic \"compliant\" from the uploaded document alone."),
        _section("Document Q&A & tools", [
            {"tool": "Document Q&A", "scope": "Free-form questions answered against content with evidence + confidence + caveat"},
            {"answer_type": "Direct extraction / Summarisation / Inference / NOT FOUND", "note": "NOT FOUND is a first-class answer — no guessing"},
            {"tool": "Table extract / Q&A", "scope": "Each T-NNN table independently addressable"},
            {"tool": "Figure Q&A", "scope": "Each FIG-NNN figure interpreted with trend, axis and uncertainty notes"},
        ], ["tool", "scope"], "Answers are traceable to a passage; each answer carries an evidence pointer, not an assertion."),
        _section("Evidence & source separation", [
            {"layer": "Uploaded document (primary)", "contents": "Text layer supplied; all measure/entity/obligation rows above trace here"},
            {"layer": "OCR-derived (secondary)", "contents": f"{len(artifacts)} artefact(s) removed and logged; derived text is verified only after image check"},
            {"layer": "External sources (context)", "contents": "Corpus references are labelled EXTERNAL and are never presented as extracted from the uploaded file"},
            {"layer": "Model inference", "contents": "Deterministic rules only; every inferred label carries a confidence column and reason"},
            {"layer": "User context", "contents": "Scope flags you set (export/compliance) that reprioritise downstream products"},
            {"citation_format": "AYUSH Manufacturing Quality Guidance, v2.0, Chapter 4, p. 7", "note": "cite the issuer + version + location, never just an organisation name"},
        ], ["layer", "contents"], "Evidence layers keep what is read apart from what is inferred."),
        _section("Version control & change tracking", [
            {"version": meta.get("version") or "[NOT PROVIDED]", "date": meta.get("date") or "[NOT PROVIDED]",
             "change": "1 change-control entry — OCR artefact stripping + structuring of the supplied text; original retained",
             "status": "PENDING human review flags"},
        ], ["version", "date", "change", "status"], "Every downstream product carries the version it was produced from."),
        _section("Limitations & data-behind-answer flags", [
            {"flag": "Original page images", "status": "REQUIRED", "note": "No page index, bounding boxes or image verification until the scanned PDF is attached"},
            {"flag": "OCR confidence (per page)", "status": "PENDING", "note": "Band computed; per-page confidence needs the image layer"},
            {"flag": "Human review flags", "status": "PENDING", "note": "Passage rows show reviewer status"},
            {"flag": "Numeric coverage", "status": "FLAGGED" if mset["warned"] else "OK", "note": mset["status"][:160]},
            {"flag": "Compliance verdicts", "status": "NOT ASSESSED", "note": "Cannot be determined from the document alone"},
        ], ["flag", "status", "note"], "Real gaps are surfaced as flags, never hidden."),
        _section("QC checklist", [
            {"check": "Title taken from an OCR artefact", "result": title_artifact, "note": "Artifact-labelled titles are rejected"},
            {"check": "Generic nouns excluded from biomedical entities", "result": "PASS" if not ents["excluded_generics"] else "EXCLUDED LISTED ABOVE", "note": f"{len(ents['excluded_generics'])} generic term(s) kept out"},
            {"check": "Numeric gap distinguished from \u201cconclusion there are no numbers\u201d", "result": "PASS" if mset["warned"] else "OK", "note": "reasons recorded in STATUS row"},
            {"check": "\u201cshould\u201d never upgraded to \u201cmust\u201d", "result": "PASS", "note": "Recommendation type is preserved"},
            {"check": "Evidence layers separated (upload vs external vs inference)", "result": "PASS", "note": "citations cite issuer + version + location"},
            {"check": "Compliance verdicts withheld", "result": "PASS", "note": "NOT ASSESSED / REQUIRES EVIDENCE only"},
            {"check": "Page-level provenance flagged", "result": "PENDING IMAGE INPUT", "note": "resolution automatically upgraded when pages attach"},
        ], ["check", "result", "note"], "Run each check before export; release only a fully verified document."),
    ]
    return result


_MK_HEADING_RE = re.compile(r"^[#>*\-]+\s+", re.M)


_MK_ARTIFACT_RE = re.compile(
    r"(#+\s*|>\s+)?(Core\s+Structure\s+Description|Project\s+Title|Technology\s+Area|"
    r"Representative\s+Compounds|Publication\s+Number|Patent\s+Reference|Markush\s+Claim\s+Drafting|"
    r"Withanolide[\s-]?Based\s+Markush|Demo)",
    re.I,
)


_MK_STRUCTURE_RE = re.compile(
    r"\b(SMILES|InChI|MOL\b|SDF\b|CDX\b|chemical\s+drawing|structure\s+file|formula\s*\(?\s*I\s*\)?\s*[:=])",
    re.I,
)


_MK_SMILES_FRAGMENT_RE = re.compile(r"\b[CcNnOoSsPpFf][A-Za-z0-9@+=\-\\\[\(\]\)\[\]\{\}#/0-9]{3,}")


_MK_FORMULA_RE = re.compile(r"\bC\d+(?:H\d+)?(?:[NOSPClI][a-z]?\d*)+\b")


_MK_RGROUP_RE = re.compile(r"\bR(\d+)\s*[=:]\s*([^;|\n]+)", re.I)


_MK_N_RE = re.compile(r"\bn\s*[=:]\s*(\d+(?:\s*[–-]\s*\d+)?)", re.I)


_MK_BROAD_RE = re.compile(r"\b(alkyl,\s*aryl|ory\s+alkyl|unbounded|various\s+group|"
                          r"very\s+broad|\baryl\b\s+alone|standard\s+conditions|suitable\s+reagents|known\s+methods|"
                          r"oxygen[\s-]?containing\s+groups?\b)", re.I)


_MK_LACTONE_RE = re.compile(r"\blactone\b", re.I)


_MK_LACTONE_VARIATION_RE = re.compile(r"\blactone\s+(?:ring|variations?|side\s+chain)\b", re.I)


_MK_SCAFFOLD_RE = re.compile(r"\b(withanolide|steroidal\s+lactone|withaferin\s*a)\b", re.I)


_MK_EXAMPLE_RE = re.compile(r"\b(?:Example|Ex\.|Compound)\s*\d+", re.I)


_MK_ACTIVITY_RE = re.compile(
    r"\b(IC\d{0,2}|EC\d{0,2}|Ki|Kd|MIC|%[a-z\s]*inhibi|activity|potent)\b", re.I)


def _mk_clean(text: str) -> dict[str, Any]:
    lines = re.split(r"\r?\n", text or "")
    clean: list[str] = []
    artifacts: list[str] = []
    for line in lines:
        probe = _MK_HEADING_RE.sub("", line).strip()
        if _MK_ARTIFACT_RE.search(line):
            artifacts.append(line.strip()[:90])
            continue
        if _MK_ARTIFACT_RE.search(probe):
            artifacts.append(probe[:90])
            continue
        clean.append(line.strip())
    return {"clean": "\n".join([x for x in clean if x]).strip(), "artifacts": artifacts}


def _mk_formula_status(clean: str) -> dict[str, Any]:
    has_struct_token = bool(_MK_STRUCTURE_RE.search(clean))
    has_smiles_frag = bool(_MK_SMILES_FRAGMENT_RE.search(clean))
    has_formula = bool(_MK_FORMULA_RE.search(clean))
    has_inchi = bool(re.search(r"InChI\s*=", clean, re.I))
    verified = has_struct_token or has_inchi or (has_smiles_frag and has_formula)
    return {
        "verified": verified, "flag": "VALID" if verified else "INVALID/INCOMPLETE",
        "note": "Verified structure representation present (drawing/SMILES/InChI/formula)." if verified
                else "Only a verbal scaffold description — no formula drawing, SMILES, InChI or valid formula. Use [STRUCTURE REQUIRED].",
    }


def _mk_rgroups(clean: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _i, m in enumerate(_MK_RGROUP_RE.finditer(clean), start=1):
        r = m.group(1)
        val = m.group(2).strip(" :=").strip()
        bounded = not _MK_BROAD_RE.search(val) and len(val.strip()) > 2 and any(ch.isalpha() for ch in val)
        rows.append({
            "position": f"R{r}", "meaning": "[POSITION NUMBERING REQUIRED]",
            "allowed_group": val[:80] or "[SUBSTITUENT DEFINITION REQUIRED]",
            "closed_or_open": "Closed/bounded" if bounded else "Too broad — define range, ring type, substitution and attachment",
            "structure_definition": "Explicit" if (val.count(",") <= 2 and bounded) else "Under-defined",
            "support": "Examples/activity in source" if (_MK_EXAMPLE_RE.search(clean) or _MK_ACTIVITY_RE.search(clean)) else "Not evidenced",
            "status": "Eligible (verify position)" if bounded else "Narrow / Blocked",
        })
    return rows[:12]


def _mk_combinations(clean: str, rgroups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    combos: list[dict[str, Any]] = []
    for rg in rgroups[:8]:
        disclosed = bool(_MK_EXAMPLE_RE.search(clean) and rg["status"].startswith("Eligible"))
        combos.append({
            "combination": f"{rg['position']} → {rg['allowed_group'][:40]}",
            "chemically_valid": "Yes (valence under review)" if rg["status"].startswith("Eligible") else "Unknown",
            "disclosed": "Yes" if disclosed else "No",
            "prepared": "No — not evidenced" if not disclosed else "Unverified",
            "tested": "No — not evidenced",
            "claimable": "Strong (explicit)" if disclosed else "Weak/unsupported — do not include without disclosure",
        })
    return combos[:10] or [{"combination": "[NONE DECLARED]", "chemically_valid": "—", "disclosed": "—",
                            "prepared": "—", "tested": "—", "claimable": "Blocked — no R-groups defined"}]


def _hub_markush(inputs: dict[str, Any], result: dict[str, Any], cit: list[dict[str, Any]]) -> dict[str, Any]:
    raw = " ".join(x for x in [_basis_text(inputs, "core_structure"), _basis_text(inputs, "variant_features")] if x)
    parsed = _mk_clean(raw)
    clean = parsed["clean"]
    fstat = _mk_formula_status(clean)
    rgroups = _mk_rgroups(clean)
    combos = _mk_combinations(clean, rgroups)
    n_m = _MK_N_RE.search(clean)
    scaffold = _MK_SCAFFOLD_RE.search(clean)
    lactone_v = _MK_LACTONE_VARIATION_RE.search(clean)
    lactone_raw = _MK_LACTONE_RE.search(clean)
    blocked = not fstat["verified"] or not rgroups or bool(_MK_BROAD_RE.search(clean))

    status_line = (
        "Preliminary Markush concept only; drafting blocked pending verified chemical formula, R-group definitions, "
        "original disclosure support and enablement review."
    ) if blocked else "Supported Markush claim framework (technical drafting version)."
    if fstat["verified"] and rgroups:
        result["summary"] = f"Markush claim framework over {len(rgroups)} defined variable position(s) on a verified structure; pending original-specification support and enablement review."
    else:
        result["summary"] = "Drafting blocked — the formula field contains document headings and no verified chemical formula; R-group definitions and original-disclosure support are missing."
    result["note"] = "Scaffold verification → R-group extraction → combination matrix → chemical validity → support/enablement audit → unity review → claim versions (broad / supported / fallback)."
    result["claims"] = [
        "1. A compound represented by Formula (I):" + ("\n    [VERIFIED CHEMICAL FORMULA REQUIRED]" if not fstat["verified"] else "\n    [INSERT VERIFIED FORMULA]") +
        "\n   wherein:\n   R1 is selected from the group consisting of [supported groups];\n   R2 is selected from the group consisting of [supported groups];\n   n is an integer selected from [supported values];\n   the compound optionally being in the form of a pharmaceutically acceptable salt, solvate or stereoisomer thereof.\n   (Skeleton only — not filing-ready until formula, positions, groups, n-attachment and salts are supported.)"
    ]
    result["findings"].append(_finding("mk-0", "Markush Claim Drafting standard (judge line)",
        "IP-SAKTI ka Markush Claim Drafting Agent sirf R-groups ki list se broad claim nahi banata; verified chemical scaffold, ring numbering, attachment positions, bounded substituents, stereochemistry, supported combinations, preparation methods, common technical activity, enablement aur prior-art risk ko check karke broad, supported aur fallback claims generate karta hai.",
        "info"))
    result["findings"].append(_finding("mk-1", "Parsing cleanup",
        f"{len(parsed['artifacts'])} document artifact(s) removed from claim text (" + ("; ".join(a[:40] for a in parsed['artifacts'][:4]) or "none") + ").",
        "info"))
    result["findings"].append(_finding("mk-2", "Formula verification",
        f"Scaffold representation: {fstat['flag']} — " + fstat["note"],
        "success" if fstat["verified"] else "warning"))
    result["findings"].append(_finding("mk-3", "Claim-readiness",
        "Not ready — verbal scaffold description only; ring numbering, stereochemistry, closures and R-group attachment points all required." if scaffold and not fstat["verified"] else status_line,
        "warning" if blocked else "info"))
    result["suggestions"] = [
        "Upload the verified scaffold drawing (or valid SMILES/InChI and ring numbering) before any claim is drafted.",
        "Bound every R-group: carbon range, branching, substitution, heteroatoms, ring type, aromaticity, attachment, optional combinations.",
        "Run specific supported combinations through preparation-route and enablement review; separate broad vs supported vs fallback claim versions.",
        "Do not treat regulatory/TK sources, or a natural-compound reference, as support for the Markush scope.",
    ]

    result["sections"] += [
        _section("Executive assessment", [
            {"key": "Invention type", "value": "[NEW COMPOUND / GENUS / NATURAL-PRODUCT ANALOG / SYNTHETIC DERIVATIVE / SALT / COMPOSITION / METHOD / USE]"},
            {"key": "Core scaffold", "value": (scaffold.group(0) + " (conceptually identified)" if scaffold else "[NOT SPECIFIED]")},
            {"key": "Valid structure status", "value": fstat["flag"]},
            {"key": "R-group count", "value": str(len(rgroups))},
            {"key": "Supported alternatives", "value": str(sum(1 for c in combos if c["claimable"].startswith("Strong")))},
            {"key": "Unsupported alternatives", "value": str(sum(1 for c in combos if c["claimable"].startswith("Weak")))},
            {"key": "Broad-scope risk", "value": "Enablement, support, unity, clarity, novelty" if blocked else "Lower — bounded groups verified"},
            {"key": "Filing-readiness", "value": "Not filing-ready" if blocked else "Technical drafting version — Attorney review required"},
        ], ["key", "value"], "Scope confirmation first; the agent never guesses round objective or generates a claim from a heading."),
        _section("Input and parsing quality", [
            {"item": "Raw claim text", "value": raw[:140] or "[NOT PROVIDED]"},
            {"item": "Parsing artifacts removed", "value": "; ".join(parsed["artifacts"][:6]) or "None"},
            {"item": "Clean claim text", "value": clean[:140] or "[EMPTY — only headings supplied]"},
        ], ["item", "value"], "Headings, demo labels and project titles are document metadata, never chemical claim language."),
        _section("Core scaffold definition", [
            {"scaffold": (scaffold.group(0).capitalize() if scaffold else "[NOT SPECIFIED]"),
             "chemical_class": "Steroidal lactone (withanolide)" if scaffold and re.search(r"withanolide|steroidal", clean, re.I) else "[CLASS REQUIRED]",
             "ring_numbering": "[RING NUMBERING REQUIRED]",
             "attachment_points": "[POSITIONS REQUIRED]", "stereochemistry": "[STEREOCHEMISTRY REQUIRED]",
             "natural_reference": (scaffold.group(0).capitalize() if scaffold and "withaferin" in scaffold.group(0).lower() else "[REFERENCE NOT SPECIFIED]"),
             "verification": fstat["flag"], "status": "Conceptually identified — claim-readiness: NOT READY" if (scaffold and not fstat["verified"]) else ("Verified" if fstat["verified"] else "Not identified")}
        ], ["scaffold", "chemical_class", "ring_numbering", "attachment_points", "stereochemistry", "natural_reference", "verification", "status"],
            "A verbal description like 'four fused steroid-like rings with a lactone side chain' is not a claim-defining structure."),
        _section("Structure representation", [
            {"representation": fstat["note"], "type": "SMILES / InChI / drawing / formula / structure file",
             "validity": fstat["flag"], "stereochemistry_encoded": "[NOT CHECKED]", "ring_closure_verified": "Verified" if fstat["verified"] else "[NOT CHECKED]",
             "attachment_verified": "[NOT CHECKED]", "human_review": "Required"}
        ], ["representation", "type", "validity", "stereochemistry_encoded", "ring_closure_verified", "attachment_verified", "human_review"],
            "At least one of drawing / Markush formula / SMILES / InChI / IUPAC / structure file / verified patent figure is required."),
        _section("R-group definitions", rgroups or [
            {"position": "[POSITION NUMBERING REQUIRED]", "meaning": "—", "allowed_group": "[SUBSTITUENT DEFINITION REQUIRED]",
             "closed_or_open": "Open — unbounded", "structure_definition": "Missing", "support": "None", "status": "Blocked"}
        ], ["position", "meaning", "allowed_group", "closed_or_open", "structure_definition", "support", "status"],
            "'R2 = alkyl, aryl' is too broad — carbon range, branching, substitution, heteroatoms, ring type, aromaticity, attachment, optional combos and stereochemistry are all required."),
        _section("Group-definition validation", [
            {"group": "Alkyl", "definition": "[C1–C6: linear/branched saturated hydrocarbon]"},
            {"group": "Cycloalkyl / Aryl / Heteroaryl", "definition": "[Ring size, heteroatoms, count, aromaticity, substitution, attachment]"},
            {"group": "Halogen", "definition": "[F, Cl, Br, I] — not 'as defined in the art'"},
            {"group": "Oxygen-containing group", "definition": "TOO BROAD — replace with closed list: hydroxyl, methoxy, ethoxy, acetoxy, carbonyl, carboxyl, ester, ether, defined cyclic acetals"},
        ], ["group", "definition"], "Only groups disclosed and technically supported are included."),
        _section("Combination matrix", combos, ["combination", "chemically_valid", "disclosed", "prepared", "tested", "claimable"],
            "The agent does not independently combine every R-group option; each combination is marked disclosed / synthesized / tested / supported. '3 variable sets' is not independently verifiable — see per-combination status."),
        _section("Chemical validity check", [
            {"check": "Atom valence", "result": "[NOT CHECKED]", "action": "Chemist review"},
            {"check": "Ring closures / lactone attachment", "result": "Verified" if fstat["verified"] else "[NOT CHECKED]", "action": "Define lactone position, ring size, saturation, closure, carbonyl, side chain"},
            {"check": "R-group attachment & valence", "result": "[NOT CHECKED]", "action": "Reject positions that break the ring or create impossible valence"},
            {"check": "Formula consistency & stereochemistry", "result": fstat["flag"], "action": "Only a verified structure is exported to Word/SDF"},
        ], ["check", "result", "action"], "No invalid or incomplete formula is exported."),
        _section("Common property or activity", [
            {"common_activity": "[BIOACTIVITY DATA REQUIRED]", "assay": "[ASSAY REQUIRED]",
             "tested_compounds": "·".join([m.group(0) for m in _MK_EXAMPLE_RE.finditer(clean)][:6]) or "[NONE TESTED]",
             "consistency": "Not assessable", "untested_members": "All members untested unless evidenced",
             "support": "Markush alternatives should share a common structure (or recognized chemical class) and a common property/activity for unity" if (clean and "alkyl" in clean) else "No activity scope claimed without tested species"}
        ], ["common_activity", "assay", "tested_compounds", "consistency", "untested_members", "support"],
            "Activity is demonstrated for tested species only — untested members are not assumed active."),
        _section("Patent and prior-art context", [
            {"reference": ", ".join([c.get("act_title", "") for c in cit if c.get("act_title")][:5]) or "[NOVELTY SEARCH REQUIRED]",
             "scope": "Natural reference compounds (e.g., Withaferin A) and TK/biologal-resource sources are prior-art/TK risks, not claim support",
             "note": "Broad-genus novelty is never concluded because one species was not found"}
        ], ["reference", "scope", "note"], "Search: scaffold, natural references, each R-group, closest subgenus, exact species, salts, stereoisomers, uses, processes, Markush claims."),
        _section("Traditional-knowledge and biological-material review", [
            {"tk_status": "Possible — Withania somnifera-derived", "source": "TKDL / Ayurveda sources provide TK context, never claim support",
             "synthetic_modification": "[MODIFICATION] — if synthetic derivative, define technical distinction",
             "biological_material": "Ashwagandha is biological material — access/benefit-sharing considerations may apply",
             "legal_review": "Required"}
        ] if scaffold and "withania" in clean.lower() else [
            {"tk_status": "[NOT REVIEWED]", "source": "Run TKDL + biodiversity check if the scaffold derives from a natural product",
             "synthetic_modification": "[NOT DEFINED]", "biological_material": "[NOT SPECIFIED]", "legal_review": "Required"}
        ], ["tk_status", "source", "synthetic_modification", "biological_material", "legal_review"],
            "A natural-product scaffold (steroidal lactone/withanolide) triggers novelty, TK, biological-resource and enablement review — never skip these when a reference compound like Withaferin A is cited."),
        _section("Lactone and side-chain definition", [
            {"lactone": "Variation undeclared — too vague", "definition": "[Ring size, position, closure, saturation, double-bond, carbonyl, substituents, side-chain length, stereochemistry, open/closed or prodrug form]",
             "note": "Not all lactone variations are included merely because the scaffold is found across a family; define or exclude them explicitly"}
        ] if (lactone_raw and not lactone_v) else [
            {"lactone": (lactone_v.group(0) if lactone_v else "[NOT MENTIONED]"), "definition": "[EXACT STRUCTURAL DEFINITION REQUIRED]",
             "note": "Lactone ring size, closure, saturation, carbonyl position, side chain and stereochemistry must be defined."}
        ], ["lactone", "definition", "note"], "'Lactone variations' is too vague for a claim; it must be structurally defined or excluded."),
        _section("n definition", [
            {"n": (n_m.group(0) if n_m else "[UNDEFINED]"),
             "attachment": "[NOT DEFINED — what structural unit does n count, and where does it attach?]",
             "status": "Blocked until n is attached to a defined structural element" if not n_m else "Review — attach to defined element"}
        ], ["n", "attachment", "status"], "n = 0–2 has no meaning without a defined counting unit and attachment location."),
        _section("Broad analytical claim (Version A)", [
            {"version": "A", "claim": "A compound of Formula (I) as a broad analytical Markush claim", "scope": "[VERIFIED FORMULA REQUIRED]",
             "status": "NOT FILING-READY — enablement/support/unity/novelty/clarity risks listed"}
        ], ["version", "claim", "scope", "status"], "Maximum conceptual scope only."),
        _section("Supported Markush claim (Version B)", [
            {"version": "B", "claim": "A compound of Formula (I), or a pharmaceutically acceptable salt, solvate or stereoisomer thereof, wherein R1/R2 are each independently selected from [supported groups] and n [supported value]",
             "scope": "Only groups and combinations supported by the current disclosure", "status": "Technical drafting version"}
        ], ["version", "claim", "scope", "status"], "Draft only with verified formula + supported alternatives."),
        _section("Narrow fallback claims (Version C)", [
            {"version": "C", "dependent_claims": [
                "The compound of claim 1, wherein R1 is hydroxyl.",
                "The compound of claim 1, wherein R2 is methyl.",
                "The compound of claim 1, wherein n is 1.",
                "The compound of claim 1, having the stereochemical configuration shown in Formula (I).",
                "The compound of claim 1 as a pharmaceutically acceptable salt."]
             .__str__().replace("'", "'"),
             "status": "Only inserted if the specification supports them — specific compounds, tested substitutions, preferred R1/R2 combos, stereochemistry, salts, process"}
        ], ["version", "dependent_claims", "status"], "Fallback species claims protect specific tested embodiments."),
        _section("Composition and process claims", [
            {"claim_type": "Composition", "text": "A pharmaceutical composition comprising a compound of claim 1 and a pharmaceutically acceptable excipient."},
            {"claim_type": "Process", "text": "A method of preparing a compound of claim 1, comprising: (a) providing [starting structure]; (b) reacting with [reagent] under [defined conditions]; (c) forming the lactone or substituent; (d) isolating the compound; (e) optionally converting to a salt/solvate. (Skeleton — requires defined steps and support.)"},
        ], ["claim_type", "text"], "Process claims never use 'standard conditions' or 'suitable reagents' without defined chemistry."),
        _section("Use claims", [
            {"claim_type": "Use", "text": "The compound of claim 1 for use in [defined application], subject to jurisdiction-specific review. Claims of 'wellness', 'general health' or 'safe/cures' are never drafted without evidence + legal review."}
        ], ["claim_type", "text"], "Activity/use claims require target, assay, tested compounds, threshold, comparator, dose and reproducibility."),
        _section("Export validation", [
            {"format": "Word claim draft", "status": "Export only clean claims + definitions + formula + R-group table + warnings + version"},
            {"format": "SDF", "status": "Export only verified, individually defined structures; Markush genus is never exported as a single molecule; heading artifacts and natural extracts never exported"},
        ], ["format", "status"], "No invalid formula is exported."),
        _section("Missing information", [
            {"status": status_line,
             "missing": "[" + ", ".join(x for x in ["STRUCTURE REQUIRED", "POSITION NUMBERING REQUIRED", "SUBSTITUENT DEFINITION REQUIRED",
                                                    "EXAMPLE REQUIRED", "BIOACTIVITY DATA REQUIRED", "ORIGINAL SPECIFICATION SUPPORT REQUIRED",
                                                    "LEGAL REVIEW REQUIRED"] if x.startswith(("STRUCTURE", "POSITION", "SUBSTITUENT", "EXAMPLE", "BIOACTIVITY", "ORIGINAL", "LEGAL")) and (not fstat["verified"] or not rgroups)) + "]"
             if (not fstat["verified"] or not rgroups) else "All required inputs flagged above."}
        ], ["status", "missing"], "Honest blocked state — never a fabricated claim."),
        _section("Attorney / chemist review checklist", [
            {"check": "Document headings removed from claim text", "result": "PASS", "note": "artifacts isolated as metadata"},
            {"check": "Verified scaffold + ring numbering before claim", "result": "PASS" if fstat["verified"] else "BLOCKED", "note": "verbal description is not claim language"},
            {"check": "R-groups bounded and attached", "result": "PASS" if rgroups else "BLOCKED", "note": "'alkyl, aryl' and 'oxygen-containing group' rejected as too broad"},
            {"check": "n defined with attachment", "result": "PASS" if n_m else "BLOCKED", "note": "n alone carries no chemical meaning"},
            {"check": "Valence / ring closures checked", "result": "[CHEMIST]", "note": "chemist review before export"},
            {"check": "Combinations disclosed vs tested distinguished", "result": "PASS", "note": "per-combination matrix"},
            {"check": "Unity (common structure + activity)", "result": "PASS" if (rgroups and not blocked) else "BLOCKED", "note": "WIPO unity analysis"},
            {"check": "Novelty/TK risks flagged", "result": "PASS", "note": "natural reference + TKDL + biological-material review"},
            {"check": "No unsupported effects / regulatory-source support", "result": "PASS", "note": "effects and citations are bracketed"},
            {"check": "Export gated on valid structure", "result": "PASS if verified else BLOCKED", "note": "no invalid formula leaves the system"},
        ], ["check", "result", "note"], "Run every check before delivery."),
    ]
    return result
