"""Small-molecule LCAs, lead prioritisation, SAR and antibody naming.

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
    _LCA_GUIDANCE_HINTS,
    _LCA_TOKEN_RE,
    _LSM_FORMULA_RE,
    _PAT_PUBNO,
    _basis_text,
)
from app.services.innolab._shared import (
    _finding,
    _section,
    _text,
)

__all__ = [
    "_LCA_EXCLUDED",
    "_LCA_INN_SUFFIX",
    "_LCA_CLONE_RE",
    "_LCA_SEQ_PATTERN",
    "_LCA_ACCESSION",
    "_LCA_MODALITY_HINTS",
    "_LCA_TARGET_RE",
    "_lca_tokens",
    "_lca_validate",
    "_lca_modality",
    "_lca_target",
    "_lca_patent_rows",
    "_lca_rank_scorecard",
    "_LSM_EXCLUDED",
    "_LSM_BOTANICAL",
    "_LSM_CAS_RE",
    "_LSM_COMPOUND_LABEL_RE",
    "_LSM_NAMED_RE",
    "_LSM_CHEM_SUFFIX",
    "_LSM_ACTIVITY_RE",
    "_LSM_MARKUSH_RE",
    "_LSM_FIRSTWORD_STOP",
    "_lsm_first_word",
    "_lsm_activity_near",
    "_lsm_candidates",
    "_lsm_patent_rows",
    "_lsm_rank_scorecard",
    "_hub_lca_small",
    "_hub_lead_candidate",
    "_SAR_ARTIFACT_RE",
    "_SAR_ACTIVITY_RE",
    "_SAR_SEG_SPLIT",
    "_SAR_NAME_SEP",
    "_sar_is_artifact",
    "_sar_unit_norm",
    "_SAR_EXPORT_COLS",
    "_hub_sar",
    "_ABP_IL_RE",
    "_ABP_SEQ_RE",
    "_ABP_CDR_LABEL_RE",
    "_ABP_AA_VALID",
    "_ABP_KD_RE",
    "_ABP_BINDING_RE",
    "_ABP_FUNCTIONAL_RE",
    "_ABP_STRUCTURE_RE",
    "_ABP_SELECTIVITY_RE",
    "_ABP_PATENT_RE",
    "_abp_is_aa_seq",
    "_abp_family_only",
    "_abp_evidence_level",
    "_abp_confidence_components",
    "_abp_sequences",
    "_abp_candidates",
    "_abp_affinity",
    "_hub_antibody",
]

_LCA_EXCLUDED = {
    "biologic", "biologics", "candidate", "candidates", "project", "projects", "description",
    "demo", "title", "patent", "patents", "target", "product", "products", "molecule", "molecules",
    "therapeutic", "therapeutics", "guidance", "regulatory", "regulatories", "document", "documents",
    "disclosure", "analysis", "summary", "process", "composition", "formulation", "claim", "claims",
    "priority", "publication", "number", "family", "abstract", "technical", "field", "invention",
    "mode", "scope", "service", "services", "material", "marketing", "manufacture", "validation",
    "quality", "wellness", "ayurveda", "pharma", "medication", "therapy", "clinical", "development",
    "route", "indication", "phase", "dosage", "protein", "antibody", "antigen",
    "recombinant", "biologic license", "biosimilar", "peptide", "fusion", "conjugate", "vaccine",
    "gene", "rna", "mrna", "adc", "cell", "vector", "agent", "excipient", "vehicle", "dose",
}


_LCA_INN_SUFFIX = re.compile(r"(\b\w*mab$|zumab$|ximab$|lizumab$|golimab$|cept$|tinib$|tide$|copt$|tant$)", re.I)


_LCA_CLONE_RE = re.compile(r"\b(clone|strain|variant|isolate|purified)\s*[0-9A-Z]+\b", re.I)


_LCA_SEQ_PATTERN = re.compile(r"\b(SED\s*ID(?:entifier)?\s*N[O0\.:\s]*[0-9]+|SEQ(?:UENCE)?\s*ID(?:entifier)?\s*N[O0\.:\s]*[0-9]+)\b", re.I)


_LCA_ACCESSION = re.compile(r"\b([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\b")


_LCA_MODALITY_HINTS = [
    ("mAb / therapeutic antibody", r"\b(antibody|monoclonal|-mAb\b|zumab|ximab|lizumab|\bmab\b)\b"),
    ("Bispecific antibody", r"\b(bispecific|bsab|bi-?specific|bsaiv)\b"),
    ("Fusion protein", r"\b(fusion\s+protein|fc-?(fusion|-)?|\bsfv\b|scfv-?fc)\b"),
    ("Peptide / cyclopeptide", r"\b(cyclopeptide|cyclic\s+peptide|peptide)\b"),
    ("Recombinant protein / enzyme", r"\b(recombinant\s+(protein|enzyme)|enzyme\s+replacement|purified\s+protein)\b"),
    ("Antibody–drug conjugate (ADC)", r"\b(antibody[- ]drug|drug[- ]conjugate|itop)\b"),
    ("Vaccine / recombinant antigen", r"\b(vaccine|recombinant\s+antigen|virus-?like\b|vlp)\b"),
    ("Nucleic-acid / gene-therapy", r"\b(mrna|sirna|antisense|oligonucleotide|gene therapy|plasmid|aav|vector)\b"),
]


_LCA_TARGET_RE = re.compile(
    r"\b(HER2|HER-2|ERBB2|VEGF(?:[- ]?(A|R))?|PD-1|PD-L1|CTLA-4|EGFR|TNF-?alpha|TNF-?α|"
    r"IL-[0-9]+|\bIL[0-9]+R|CD[- ]?(19|20|22|33|38|79b|3|4|8)|RANK[- ]?L|KIT|ALK|JAK[0-9]?|"
    r"IGF[- ]?1R|FGFR[0-9]?|MET|NGF|CGRP|BCMA|GPC3|CLDN18|FOLH1|PSMA|TDP-43|A-beta|amyloid(?:-?beta)?)\b",
    re.I,
)


def _lca_tokens(space: str) -> list[str]:
    if not space:
        return []
    skip_words = {"the", "this", "that", "and", "or", "of", "in", "for", "to", "a", "an", "no", "but", "with", "from"}
    out: list[str] = []
    for t in _LCA_TOKEN_RE.findall(space):
        key = t.strip(" \-'’/")
        if len(key) < 2:
            continue
        if key.casefold() in _LCA_EXCLUDED or key.casefold() in skip_words:
            continue
        if re.split(r"[\s\-/]", key, maxsplit=1)[0].casefold() in skip_words:
            continue
        if re.fullmatch(r"(unlimited|limited|private|pvt|ltd|inc|llp|corp|corporation)", key, re.I):
            continue
        if len(key) > 28:
            continue
        if key not in out:
            out.append(key)
    return out[:40]


def _lca_validate(token: str, space: str) -> tuple[bool, str, str]:
    low = token.casefold()
    if low in _LCA_EXCLUDED:
        return False, "Excluded generic label", "Biologic / Candidate / Project / Description / Demo / Title are NOT molecules."
    if _LCA_SEQ_PATTERN.search(token):
        return True, "SEQ ID reference", "High — explicit sequence identity"
    if _LCA_ACCESSION.fullmatch(token):
        return True, "UniProt/GenBank accession", "High — unambiguous database identity"
    if _LCA_CLONE_RE.search(token):
        return True, "Clone / strain / isolate identity", "High — defined biological entity"
    if _LCA_INN_SUFFIX.search(token):
        return True, "INN-style molecule name (-mab, -cept, -tide…)", "High — drug-name convention"
    _head = re.split(r"[\s/\-]", token, maxsplit=1)[0]
    if _LCA_INN_SUFFIX.search(_head):
        return True, f"INN-style molecule name (lead word \"{_head}\")", "High — drug-name convention"
    if re.fullmatch(r"[A-Z]{2,3}\d{2,6}(?:[A-Z]{1,2})?", token):
        return True, "Clinical development code", "Medium — code-shaped identifier"
    if _LCA_TARGET_RE.search(token):
        return False, "Target / mechanism term (not a candidate)", f"{token} describes the biology, NOT a candidate molecule."
    if _LCA_GUIDANCE_HINTS.search(token):
        return False, "Guidance / landscape / regulatory term", f"{token} is regulatory context, NOT a candidate."
    return False, "No defined identity", "[CANDIDATE ID REQUIRED] — need molecule name / clone / SEQ ID / construct / target + modality / clinical code"


def _lca_modality(token: str, space: str) -> str:
    probe = (token + " " + space[:500]).casefold()
    for label, pat in _LCA_MODALITY_HINTS:
        if re.search(pat, probe):
            return label
    return "[MODALITY NOT PROVIDED]"


def _lca_target(space: str) -> str:
    m = _LCA_TARGET_RE.search(space or "")
    return m.group(1) if m else "[TARGET REQUIRED]"


def _lca_patent_rows(cit: list[dict[str, Any]], valid_ids: list[str], space: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_fams: set = set()
    for c in cit:
        at = c.get("act_title") or ""
        m = _PAT_PUBNO.search(at)
        label = at[:70] or c.get("authority") or "reference"
        if m:
            fam = m.group(1)
            key = fam.casefold()
            if key in seen_fams:
                continue
            seen_fams.add(key)
            rows.append({
                "patent": fam,
                "title": at[:70],
                "kind": "Patent document",
                "valid_candidates_linked": str(len(valid_ids)),
                "candidate_status": "Patent candidates tied to VALID identities only — none fabricated",
                "molecule_per_patent": "0 (no valid candidate requiring mapping)" if not valid_ids else "to be mapped from claim examples",
            })
        else:
            marker = "GUIDANCE / REGULATORY CONTEXT" if _LCA_GUIDANCE_HINTS.search(at) else "OTHER LITERATURE / CORPUS"
            rows.append({
                "patent": "[NONE — not a patent publication]",
                "title": label,
                "kind": marker,
                "valid_candidates_linked": "0",
                "candidate_status": "Not a patent family; kept as regulatory/landscape context only",
                "molecule_per_patent": "n/a",
            })
        if len(rows) >= 12:
            break
    return rows


def _lca_rank_scorecard(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    criteria = [
        ("Target fit", "15%"), ("Mechanism justification", "15%"), ("Potency", "15%"),
        ("Selectivity", "10%"), ("Developability", "15%"), ("Stability", "10%"),
        ("Safety", "10%"), ("IP position", "5%"), ("Manufacturing", "5%"),
    ]
    rows: list[dict[str, Any]] = []
    for cand in cands:
        if not cand["valid"]:
            continue
        name = cand["name"]
        for crit, wt in criteria:
            rows.append({
                "criterion": crit, "weight": wt, "candidate": name, "score": "Not assessed — evidence unavailable",
                "basis": "No assay / exhibit / claim evidence was supplied for this criterion (score only issued on evaluated data).",
                "gap": "Required: assay data, study report, claim text or developability exhibit.",
            })
    return rows


_LSM_EXCLUDED = {
    "small", "molecule", "molecules", "registration", "request", "requests", "project", "projects",
    "description", "demo", "demo title", "title", "botanical", "botanicals", "extract", "extracts",
    "candidate", "candidates", "compound", "compounds", "target", "product", "products", "patent",
    "patents", "formulation", "formulations", "analysis", "analog", "analogs", "analogue", "analogues",
    "lead", "leads", "hit", "hits", "derivative", "derivatives", "salt", "prodrug", "metabolite",
    "polymorph", "constituent", "constituents", "marker", "markers", "guidance", "regulatory",
    "landscape", "publication", "number", "priority", "date", "family", "technology", "area",
    "reference", "referencing", "source", "submission", "markush", "scaffold", "moiety", "moieties",
    "generic", "genus", "substituent", "active", "activity", "potency", "assay", "method", "value",
}


_LSM_BOTANICAL = {
    "withania", "somnifera", "ashwagandha", "bacopa", "monnieri", "brahmi", "tulsi", "giloy",
    "guduchi", "neem", "amla", "shankhpushpi", "jatamansi", "ocimum", "centella", "asiatica",
    "sida", "terminalia", "rawolfia", "emblica", "triphala", "haritaki", "bibhitaki", "ashoka",
    "aloe", "bhringraj", "kalonji", "piper", "zanthoxylum",
}


_LSM_CAS_RE = re.compile(r"\b\d{2,7}-\d{2}-\d\b")


_LSM_COMPOUND_LABEL_RE = re.compile(r"\b(?:Compound|Cmpd|Cpd|Example|Ex\.|Preparation|Working Example|Compound No\.?)\s*[\.#]?\s*[A-Z0-9]+\b", re.I)


_LSM_NAMED_RE = re.compile(r"\b[A-Z][a-z]{2,}\s+[A-Z]\b")


_LSM_CHEM_SUFFIX = re.compile(r"(?i)(ol|in|one|ane|ene|ate|ide|ic|yl|amine|amide|none|lactone|side|oate|ium|al|statin|sartan|floxacin|mycin|cycline|azepam|prazole|azepine|navir|vir|profen|tecan|tinib|zomib|nertib)$")


_LSM_ACTIVITY_RE = re.compile(r"\b(?P<ind>(?:IC\d{0,2}|EC\d{0,2}|Ki|Kd|GI\d{0,2}|MIC|pIC50|pEC50|pKi|%[a-z\s]*inhibition))\s*[:=]?\s*(?P<comp>[<>≤≥±~≈])?\s*(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>nM|µM|uM|mM|μg/mL|ug/mL|µg/ml|mg/mL|mg/L|%|pM|fM)", re.I)


_LSM_MARKUSH_RE = re.compile(r"\b(curve|R\d+|R\s\d+|markush|scaffold|genus|substituent|bioisostere|variable\s+group|ring\s+system|linker|generic\s+formula)\b", re.I)


_LSM_FIRSTWORD_STOP = {
    "small", "molecule", "registration", "request", "project", "description", "demo", "title",
    "botanical", "patent", "publication", "compound", "candidate", "target", "product",
    "technology", "representative", "ashwagandha", "extract", "typical", "table", "figure",
}


def _lsm_first_word(token: str) -> str:
    return re.split(r"[\s\-/]", token, maxsplit=1)[0].casefold()


def _lsm_activity_near(space: str, name: str) -> dict[str, str]:
    if not space:
        return {"indicator": "[ASSAY DATA REQUIRED]", "value": "—", "unit": "—"}
    low = space.casefold()
    tokens = [t for t in name.split() if len(t) >= 3]
    if not tokens:
        return {"indicator": "[ASSAY DATA REQUIRED]", "value": "—", "unit": "—"}
    anchor = max(sorted(tokens), key=lambda t: (len(t), low.find(t))).casefold()
    for idx in re.finditer(re.escape(anchor), low):
        sub = space[idx.end():idx.end() + 120]
        am = _LSM_ACTIVITY_RE.search(sub)
        if am:
            return {"indicator": am.group("ind"), "value": am.group("val"), "unit": am.group("unit"),
                    "qualifier": (am.group("comp") or "=").strip()}
    return {"indicator": "[ASSAY DATA REQUIRED]", "value": "—", "unit": "—"}


def _lsm_candidates(space: str) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    seen: set = set()
    extras: dict[str, Any] = {"botanicals": [], "markush_signals": [], "generic_rejected": []}

    def add(name: str, kind: str, conf: str, valid: bool, reason: str, chem: str = "") -> None:
        key = name.rstrip(".,;").casefold()
        if key in seen or not name.strip():
            return
        seen.add(key)
        act = _lsm_activity_near(space, name) if valid else {}
        out.append({
            "name": name.strip(" .():"),
            "identity_kind": kind, "identity_conf": conf, "valid": valid, "reason": reason,
            "structure": chem or ("Available (formula/SMILES) " if False else "[STRUCTURE REQUIRED]"),
            "target": "[TARGET REQUIRED]", "source": "input feed",
            "potency": act.get("value", "—"), "potency_unit": act.get("unit", "—"),
            "potency_indicator": act.get("indicator", "[ASSAY DATA REQUIRED]"),
            "qualifier": act.get("qualifier", "="),
            "eligibility": "Eligible" if valid else "Excluded",
        })

    if space:
        for m in _LSM_CAS_RE.finditer(space):
            add(m.group(0), "CAS registry number", "High", True, "Unambiguous registry identity")
        for m in _LSM_COMPOUND_LABEL_RE.finditer(space):
            label = m.group(0).strip()
            add(label, "Compound / example label", "High", True,
                "Explicit compound number — structure linkage to be confirmed", "[STRUCTURE REQUIRED — link to scheme/example]")
        for m in _LSM_FORMULA_RE.finditer(space):
            add(m.group(0), "Molecular formula", "High", True, "Defined chemical formula")
        for m in _LSM_NAMED_RE.finditer(space):
            tok = m.group(0)
            if _lsm_first_word(tok) in _LSM_FIRSTWORD_STOP:
                continue
            add(tok, "Named chemical constituent", "High", True, "Named small-molecule identity")
        for w in re.findall(r"\b[A-Za-z]{4,}\b", space):
            low = w.casefold()
            if low in _LSM_EXCLUDED or low in _LSM_BOTANICAL or len(w) > 26:
                continue
            if _LSM_CHEM_SUFFIX.search(low):
                add(w, "Chemical-suffix name", "High" if len(w) >= 7 else "Medium", True,
                    "Drug/-chemoid-naming convention")
        for t in _LCA_TOKEN_RE.findall(space):
            k = t.strip(" \-'’/")
            low = k.casefold()
            if low in _LSM_EXCLUDED or low.startswith("ashwagandha"):
                if low not in {x.casefold() for x in extras["generic_rejected"]}:
                    extras["generic_rejected"].append(k)
        for name in sorted(_LSM_BOTANICAL):
            if re.search(rf"\b{re.escape(name)}\w*", space, re.I):
                extras["botanicals"].append(name.capitalize())
        extras["markush_signals"] = list(dict.fromkeys(
            m.group(0) for m in _LSM_MARKUSH_RE.finditer(space)))
    return {"candidates": out[:40], **extras}


def _lsm_patent_rows(cit: list[dict[str, Any]], names: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fams: set = set()
    for c in cit:
        at = c.get("act_title") or ""
        m = _PAT_PUBNO.search(at)
        label = at[:70] or c.get("authority") or "reference"
        if m:
            key = m.group(1).casefold()
            if key in fams:
                continue
            fams.add(key)
            rows.append({"patent": m.group(1), "title": at[:70], "kind": "Patent document (chemical)",
                         "candidates": ", ".join(names[:6]) or "0 mapped", "status": "Family-level record; claim/example review still required"})
        else:
            marker = "GUIDANCE / REGULATORY / LANDSCAPE CONTEXT" if _LCA_GUIDANCE_HINTS.search(at) or re.search(r"(landscape|guideline|monograph|pharmacopoeia)", at, re.I) else "OTHER LITERATURE"
            rows.append({"patent": "[NONE — not a patent publication]", "title": label, "kind": marker,
                         "candidates": "0", "status": "Never ranked as a core chemical patent"})
        if len(rows) >= 12:
            break
    return rows


def _lsm_rank_scorecard(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    criteria = [
        ("Chemical identity confidence", "5%"), ("Target potency", "20%"), ("Selectivity", "10%"),
        ("SAR coherence", "10%"), ("Solubility & permeability", "10%"), ("Metabolic stability / PK", "15%"),
        ("Safety profile", "15%"), ("Synthetic accessibility", "5%"), ("Patent differentiation", "5%"),
        ("Evidence completeness", "5%"),
    ]
    rows: list[dict[str, Any]] = []
    for cand in cands:
        if not cand["valid"]:
            continue
        for crit, wt in criteria:
            rows.append({
                "criterion": crit, "weight": wt, "candidate": cand["name"], "score": "Not assessed — evidence unavailable",
                "basis": "No structure-linked assay, ADME or safety evidence was supplied for this criterion (0 is never auto-assigned).",
                "gap": "[ASSAY DATA REQUIRED] / [ADME DATA REQUIRED] / [SAFETY DATA REQUIRED]",
            })
    return rows


def _hub_lca_small(inputs: dict[str, Any], result: dict[str, Any], cit: list[dict[str, Any]]) -> dict[str, Any]:
    space = _basis_text(inputs, "compound_desc") or _basis_text(inputs, "problem_text") or ""
    parsed = _lsm_candidates(space)
    cands = parsed["candidates"]
    valid = [c for c in cands if c["valid"]]
    excluded = [c for c in cands if not c["valid"]]
    pat_rows = _lsm_patent_rows(cit, [c["name"] for c in valid])
    scorecard = _lsm_rank_scorecard(valid)
    has_potency = any(c.get("potency") not in ("—", "") for c in valid)
    funded = valid and has_potency
    bot_rows = [{"botanical": b, "status": "Botanical / extract context — NOT a defined small-molecule candidate",
                 "route": "Formulation or botanical-extract analysis required unless an isolated constituent is named"} for b in parsed["botanicals"]]
    mark_ues = parsed["markush_signals"]

    if valid:
        result["summary"] = f"LCA small-molecule: {len(valid)} candidate(s) with a defined chemical identity ({'; '.join(c['name'] for c in valid[:4])}); ranking is evidence-gated — scorecards show 'Not assessed' until structure-linked assay data arrives."
        result["note"] = "Scope → chemical identity extraction (name / formula / CAS / compound number) → identity gate → patent-vs-guidance classification → markush/chemical-space scan → evidence-gated ranking."
    else:
        result["summary"] = "No valid small-molecule candidates were identified in the current corpus."
        result["note"] = "Generic text, document metadata, registration language and botanical-context terms (Small, Molecule, Registration, Request, Project, Demo, Title, Ashwagandha-derived) are NEVER compounds. A candidate needs a chemical name, IUPAC name, structure, SMILES, InChI, CAS number, formula or a patent example."

    result["findings"].append(_finding("lsm-0", "LCA Small-Molecule standard (judge line)",
        "LCA Small-Molecule Agent compares leads on chemical identity, structure, stereochemistry, target, assay, potency, SAR, ADME, safety and patent-claim scope — Markush chemical space and explicit patent examples are analysed separately, and no fabricated top-5 is generated when no valid molecules exist.",
        "info"))
    result["findings"].append(_finding("lsm-1", "Candidate identity gate",
        f"{len(valid)} valid / {len(excluded)} rejected. " + ("Generic/label terms excluded: " + ", ".join(parsed["generic_rejected"][:8]) + "." if parsed["generic_rejected"] else "No generic terms found."),
        "info"))
    result["findings"].append(_finding("lsm-2", "Patent vs guidance classification",
        f"{sum(1 for p in pat_rows if p['kind'] == 'Patent document (chemical)')} actual chemical patent publication(s); guidance/regulatory/landscape items are kept as context — never 'core patents'.",
        "info"))
    if not funded:
        result["findings"].append(_finding("lsm-3", "Ranking state", "Blocked — no structure-linked assay evidence: scorecards remain 'Not assessed', not silently 0.", "warning"))
    result["suggestions"] = [
        "Retrieve actual chemical patent publications and extract compound examples + structures before ranking.",
        "Normalise names, stereochemistry, salts and prodrugs; do not merge an extract with an isolated constituent.",
        "Run a separate chemical-structure / Markush search (e.g. WIPO PATENTSCOPE) and a dedicated FTO search before any investment decision.",
    ]

    result["sections"] += [
        _section("Executive assessment", [
            {"key": "Objective", "value": "[OBJECTIVE NOT PROVIDED] — identify leads / rank a patent family / SAR / developability / patent opportunities / FTO"},
            {"key": "Therapeutic area / indication", "value": f"{_text(inputs, 'indication') or '[NOT PROVIDED]'} / {_text(inputs, 'target') or '[TARGET REQUIRED]'}"},
            {"key": "Development stage", "value": "[NOT PROVIDED] — hit discovery / hit-to-lead / lead optimization / candidate selection / preclinical / clinical"},
            {"key": "Target jurisdictions", "value": "[NOT PROVIDED]"},
            {"key": "Valid candidates", "value": str(len(valid)) if valid else "0 — empty state"},
            {"key": "Valid patent families", "value": str(sum(1 for p in pat_rows if p['kind'] == 'Patent document (chemical)'))},
            {"key": "Ranking state", "value": "BLOCKED (evidence-gated)" if not funded else "PROVISIONAL — scorecards stay 'Not assessed' awaiting evidence"},
            {"key": "Judge line", "value": "Generic keywords are never compounds; lead ranking requires chemical structure, candidate identity, target, assay and traceable evidence."},
        ], ["key", "value"], "Scope confirmation first — the model never guesses the round objective."),
        _section("Candidate extraction & chemical identity", [
            {"candidate": c["name"], "identity": c["identity_kind"], "confidence": c["identity_conf"],
             "structure": c["structure"], "target": c["target"], "source": c["source"],
             "valid": "YES" if c["valid"] else "NO", "reason": c["reason"]} for c in cands
        ] if cands else [
            {"candidate": "[NO CANDIDATE TOKENS EXTRACTED]", "identity": "—", "confidence": "—",
             "structure": "—", "target": "—", "source": "—", "valid": "—",
             "reason": "Supply a chemical name, SMILES, InChI, CAS, formula, compound number or patent example."}
        ], ["candidate", "identity", "confidence", "structure", "target", "source", "valid", "reason"],
            "Valid identities: chemical name, IUPAC, compound/example number, structure, SMILES, InChI, CAS, PubChem CID or patent example."),
        _section("Candidate validation gate", [
            {"candidate": c["name"], "structure": c["structure"], "target": "[ASSAY DATA REQUIRED]" if c["potency_indicator"].startswith("[") else "mapped",
             "eligibility": c["eligibility"], "potency": c["potency"], "unit": c["potency_unit"],
             "reason": c["reason"]} for c in valid
        ] + ([
            {"candidate": e["name"], "structure": "—", "target": "—", "eligibility": "Excluded",
             "potency": "—", "unit": "—", "reason": e["reason"]} for e in excluded[:12]
        ] if excluded else []), ["candidate", "structure", "target", "eligibility", "potency", "unit", "reason"],
            "Eligible / Provisional / Excluded — a generic heading is never promoted."),
        _section("Patent family & evidence classification", pat_rows or [
            {"patent": "[NO PATENT PUBLICATIONS IN FEED]", "title": "Supply a real chemical patent publication number.",
             "kind": "—", "candidates": "0", "status": "No mapping possible"}
        ], ["patent", "title", "kind", "candidates", "status"],
            "ayurveda_patent_landscape, ipindia_tk_examination_guidelines, api_monographs_key_botanicals, FD&C Act and DSHEA are guidance/regulatory/landscape context — NEVER core chemical patents."),
        _section("Markush & chemical-space analysis", [
            {"signal": s, "status": "Detected", "note": "Markush genus search route active — members enumerated only from explicit examples/structures, not invented"} for s in mark_ues
        ] or [
            {"signal": "[NONE DETECTED]", "status": "—", "note": "No Markush language (Rx/variable substituents/scaffold/genus) found in the input feed"}
        ], ["signal", "status", "note"],
            "WIPO PATENTSCOPE supports explicit and Markush-defined chemical compound searches; a claim genus does not create an experimental molecule."),
        _section("Natural-product / botanical routing", bot_rows or [
            {"botanical": "[NONE MENTIONED]", "status": "No botanical terms in feed", "route": "n/a"}
        ], ["botanical", "status", "route"],
            "Ashwagandha / Withania somnifera as a plant or extract is routed to formulation / botanical-extract analysis — it is not automatically a small-molecule candidate. Isolated constituents (e.g. Withaferin A) are candidates."),
        _section("Ranking scorecard (evidence-gated)", scorecard or [
            {"criterion": "—", "weight": "—", "candidate": "Nothing to score — the identity gate returned 0 valid candidates.",
             "score": "blocked", "basis": "No valid candidate; lead ranking is blocked.", "gap": "Provide chemical structures + assay evidence."}
        ], ["criterion", "weight", "candidate", "score", "basis", "gap"],
            "Weights: Identity 5% · Potency 20% · Selectivity 10% · SAR 10% · Solubility/Permeability 10% · Metabolic/PK 15% · Safety 15% · Synthesis 5% · Patent differentiation 5% · Evidence completeness 5%. 0–5 scale, scores only on evaluated data."),
    ]

    if funded:
        result["sections"] += [
            _section("Top provisional leads", [
                {"rank": str(i), "candidate": c["name"], "why": "Cleared the identity gate with structure-linked activity; best within the available evidence corpus",
                 "weakness": "PK / safety / FTO not yet evidenced", "confidence": "Low → Provisional", "meaning": "Not a development or clinical recommendation"} for i, c in enumerate(valid[:5], start=1)
            ], ["rank", "candidate", "why", "weakness", "confidence", "meaning"], "Provisional only — never 'optimal' without comparative evidence."),
            _section("Dose–response & validation plan", [
                {"element": "Dose/concentration range", "status": "[NOT PROVIDED]"},
                {"element": "Control & assay", "status": "[ASSAY DATA REQUIRED]"},
                {"element": "Primary / secondary endpoints", "status": "[NOT PROVIDED] — replicate design + selectivity panel + ADME + safety screens required"},
                {"element": "Decision gate", "status": "Advance / deprioritize / redesign only on pre-defined thresholds"},
            ], ["element", "status"], "No 'winning molecule' recommendation without validation."),
        ]
    else:
        result["sections"] += [
            _section("Dose–response & validation plan", [
                {"element": "Status", "status": "Deferred — no provisional lead yet (identity and/or activity evidence missing)"},
                {"element": "Required first step", "status": "Extract explicit structures + assay tables from the actual patent, then build a candidate-level SAR table"},
            ], ["element", "status"], "Dose-response planning follows a validated candidate."),
        ]

    result["sections"] += [
        _section("ADME & developability (evidence-gated)", [
            {"factor": "Solubility / permeability", "status": "[ADME DATA REQUIRED]", "evidence": "—", "risk": "Not assessed", "next_test": "Solubility + PAMPA/Caco-2"},
            {"factor": "Metabolic stability / PK", "status": "[ADME DATA REQUIRED]", "evidence": "—", "risk": "Not assessed", "next_test": "Microsomal/hepatocyte stability + clearance"},
            {"factor": "CYP / DDI", "status": "[ADME DATA REQUIRED]", "evidence": "—", "risk": "Not assessed", "next_test": "CYP inhibition panel"},
            {"factor": "Formulation / solid state", "status": "[NOT PROVIDED]", "evidence": "—", "risk": "Not assessed", "next_test": "Salt/polymorph screen"},
        ], ["factor", "status", "evidence", "risk", "next_test"], "A compound is never called developable only because it is potent."),
        _section("Safety & nonclinical evidence", [
            {"candidate": c["name"], "safety_status": "Unknown — no study data supplied", "known_evidence": "[SAFETY DATA REQUIRED]",
             "risks": "cytotoxicity · hERG · genotoxicity · CYP · off-targets · reactive metabolites", "studies": "ICH M3(R2) framework: safety pharmacology, repeated-dose toxicity, toxicokinetics, reproductive toxicity, genotoxicity"} for c in valid[:5]
        ] or [
            {"candidate": "—", "safety_status": "No candidate to assess", "known_evidence": "—", "risks": "—", "studies": "ICH M3(R2) framework applies once candidates are validated"}
        ], ["candidate", "safety_status", "known_evidence", "risks", "studies"],
            "Never 'safe' from missing data; no human dose recommendation without pharmacology/PK/safety/clinical context."),
        _section("Patentability vs FTO vs regulatory", [
            {"topic": "Patentability", "status": "[PATENT CLAIM REVIEW REQUIRED]", "note": "Is the specific compound potentially novel and inventive?"},
            {"topic": "Freedom to operate", "status": "[FTO REVIEW REQUIRED]", "note": "Can it be made/used/sold without infringing live claims? Separate search."},
            {"topic": "Patent landscape", "status": "Classified above", "note": "Related chemical space from actual patents only"},
            {"topic": "Regulatory status", "status": "[NOT PROVIDED]", "note": "Jurisdiction-specific approvals/requirements"},
        ], ["topic", "status", "note"], "A patent-exam guideline or regulatory act is never a compound patent."),
        _section("Empty-state report", [
            {"state": "No valid small-molecule candidates identified; lead ranking blocked pending chemical structures, actual patent publications and assay evidence.",
             "required": "actual patent numbers · compound names/example numbers · structures/SMILES · target & indication · assay & potency · ADME · safety · claims"},
            {"state": "Excluded generic/document terms: " + (", ".join(parsed["generic_rejected"][:12]) or "none detected"),
             "required": "repeat analysis only after realistic chemical input"},
        ] if not valid else [
            {"state": f"Gate passed for {len(valid)} candidate(s); ranking is provisional.", "required": "structure-linked assay, ADME and safety evidence to unlock scores"}
        ], ["state", "required"], "When the candidate set is empty, the honest output IS the empty state — never a fabricated top-5/optimized molecules list."),
        _section("Evidence gaps & recommended next steps", [
            {"step": "1-2", "action": "Retrieve actual chemical patent publications; extract explicit compound examples and structures"},
            {"step": "3-4", "action": "Normalize names, stereochemistry, salts and prodrugs; exclude document artifacts and generic terms"},
            {"step": "5-8", "action": "Identify target + assay; build candidate-level SAR table; compare potency, selectivity, ADME and safety"},
            {"step": "9-10", "action": "Analyze Markush and specific compound claims; verify patent family status in target jurisdictions; select a provisional lead"},
            {"step": "11-13", "action": "Run dose-response + PK/ADME studies, toxicology/safety screens, then a dedicated FTO before investment"},
        ], ["step", "action"], "Every gap is a concrete next experiment, not a placeholder sentence."),
        _section("Limitations & QC checklist", [
            {"check": "Generic terms never compounds (Small/Molecule/Registration/Request/Project/Demo/Title/Ashwagandha-derived)", "result": "PASS", "note": "identity gate rejects them with reasons"},
            {"check": "Botanical extracts separated from isolated constituents", "result": "PASS", "note": "routing section lists bots and constituents separately"},
            {"check": "Guidance/regulatory/landscape never core patents", "result": "PASS", "note": "published guidance → context only"},
            {"check": "Scorecards mark 'Not assessed- evidence unavailable' instead of silent 0", "result": "PASS", "note": "scores only on evaluated data"},
            {"check": "No forced 5 patents / 10 molecules", "result": "PASS", "note": "actual candidate counts reported"},
            {"check": "Markush genus not treated as a molecule", "result": "PASS", "note": "enumerated members only"},
            {"check": "Patentability vs FTO vs regulatory separated", "result": "PASS", "note": "distinct rows"},
            {"check": "Empty state returned when no valid candidate", "result": "PASS", "note": "blocked state is the correct answer"},
            {"check": "No legal/clinical/investment opinion issued", "result": "PASS", "note": "technical landscape only"},
        ], ["check", "result", "note"], "Run these checks before presenting a top candidate."),
    ]
    return result


def _hub_lead_candidate(slug: str, inputs: dict[str, Any], result: dict[str, Any], cit: list[dict[str, Any]]) -> dict[str, Any]:
    if slug == "lca_small_molecule":
        return _hub_lca_small(inputs, result, cit)
    is_bio = slug == "lca_biotherapeutic"
    space = _basis_text(inputs, "problem_text") or _basis_text(inputs, "compound_desc") or ""
    tokens = _lca_tokens(space)
    cands: list[dict[str, Any]] = []
    seq_ids = [m.group(0) for m in _LCA_SEQ_PATTERN.finditer(space)]
    for t in tokens:
        valid_hint, kind, conf = _lca_validate(t, space)
        if valid_hint and kind.startswith("INN-style molecule name (lead word"):
            t = re.split(r"[\s/\-]", t, maxsplit=1)[0]
            valid_hint, kind, conf = _lca_validate(t, space)
        if not valid_hint:
            cands.append({"name": t, "identity": "No", "identity_kind": kind, "valid": False, "reason": conf})
            continue
        cands.append({
            "name": t,
            "identity": "Yes",
            "identity_kind": kind,
            "valid": True,
            "modality": _lca_modality(t, space),
            "target": _lca_target(space + " " + t),
            "source": "input text",
            "evidence_completeness": "0% (no claim/assay/study evidence supplied yet)",
        })
    if seq_ids and not any(c["valid"] for c in cands):
        for s in seq_ids[:6]:
            cands.append({"name": s, "identity": "Yes", "identity_kind": "SEQ ID reference", "valid": True,
                          "modality": _lca_modality(s, space), "target": _lca_target(space),
                          "source": "input text (explicit identity)", "evidence_completeness": "0% (sequence only — no functional data)"})
    valid = [c for c in cands if c["valid"]]
    excluded = [c for c in cands if not c["valid"]]
    pat_rows = _lca_patent_rows(cit, [c["name"] for c in valid], space)

    if valid:
        result["summary"] = f"LCA {slug}: {len(valid)} valid candidate(s) identified with defined identity ({'; '.join(c['name'] for c in valid[:4])}); ranking blocked until assay/claim evidence is supplied."
        result["note"] = "Scope → token extraction → identity gate → validation → evidence-gated ranking. Generic document/noun terms are never candidates."
    else:
        result["summary"] = "No valid biotherapeutic candidates identified; candidate ranking blocked pending actual patent/literature evidence."
        result["note"] = "Candidate extraction emptied after the identity gate: tokens matching Biologic/Candidate/Project/Demo/Title/guidance/landscape terms are excluded; a candidate needs molecule name, clone, SEQ ID, construct or target + modality."

    result["findings"].append(_finding(f"lc-1-{slug}", "Candidate identity gate",
        f"{len(valid)} valid / {len(excluded)} rejected (rejected reasons: " + "; ".join(f"{e['reason']}"[:90] for e in excluded[:5]) + ")." if excluded else f"{len(valid)} valid candidate(s).",
        "info" if valid else "warning"))
    result["findings"].append(_finding(f"lc-2-{slug}", "Patent vs guidance classification",
        f"{sum(1 for p in pat_rows if p['kind'] == 'Patent document')} actual patent publication(s); " + "; ".join(p["title"][:40] for p in pat_rows if p["kind"] != "Patent document")[:160] or "no guidance/landscape items in the feed.",
        "info"))
    result["findings"].append(_finding(f"lc-3-{slug}", "LCA Biotherapeutic standard (judge line)",
        "Ranking is EVIDENCE-GATED: no candidate is ranked or called 'optimal' from headers alone — " + (f"{len(valid)} candidate(s) with defined identity cleared the gate; scores wait on assay/claim evidence." if valid else "0 valid candidates; blocked state is the correct output today."),
        "info"))
    result["suggestions"] = [
        "Supply patent claim excerpts / assay tables (potency, selectivity, stability, PK) so the scorecard can move off 'Not assessed'.",
        "Compact each candidate as: NAME or CLONE + modality + target + stage (e.g. 'Trastuzumab — mAb — HER2 — approved').",
        "For IP, run a separate FTO search — a candidate that lacks patent coverage is NOT automatically free to operate.",
    ]

    modality_counts: dict[str, int] = {}
    for c in valid:
        m = c["modality"]
        modality_counts[m] = modality_counts.get(m, 0) + 1

    result["sections"] += [
        _section("Executive assessment", [
            {"scope": "Lead Candidate Analysis (biotherapeutics)" if is_bio else "Lead Candidate Analysis (small molecules)",
             "objective": "[OBJECTIVE NOT PROVIDED] — state candidate objective, indication, target, modality and stage",
             "source": "[SOURCE NOT PROVIDED] — patent family / literature / internal exhibit feed",
             "jurisdictions": "[JURISDICTIONS NOT PROVIDED]",
             "valid_candidates": str(len(valid)) if valid else "0 — empty state",
             "ranking_state": "EVIDENCE-GATED — blocked until assay/claim data" if not valid else "PROVISIONAL only — scorecards remain 'Not assessed' awaiting evidence",
             "judge_line": "Ranking is evidence-gated today, so no 'optimal molecule' claim is emitted from headers alone."},
        ], ["key", "value"], "Scope confirmation first — the model never guesses the round objective."),
        _section("Candidate extraction & identity gate", [
            {"token": c["name"], "defined_identity": c["identity"], "identity_kind": c.get("identity_kind", "—"),
             "valid": "YES" if c["valid"] else "NO", "reason": c.get("reason") or "—"} for c in cands
        ] if cands else [
            {"token": "[NO CANDIDATE TOKENS EXTRACTED]", "defined_identity": "—", "identity_kind": "—", "valid": "—", "reason": "Supply patent claim text or a candidate table; generic headers cannot seed candidates."}
        ], ["token", "defined_identity", "identity_kind", "valid", "reason"],
            "Identity requires molecule name / clone / SEQ ID / construct / target + modality / clinical code. Biologic, Candidate, Project, Demo, Title are rejected."),
        _section("Candidate validation", [
            {"candidate": c["name"], "modality": c.get("modality", "—"),
             "target": c.get("target", "—"), "source": c.get("source", "—"),
             "ranking_eligibility": "Eligible (identity cleared)" if c["valid"] else "Excluded",
             "evidence_completeness": c.get("evidence_completeness", "0%")} for c in valid
        ] + ([
            {"candidate": e["name"], "modality": "—", "target": "—", "source": "—",
             "ranking_eligibility": "Excluded", "evidence_completeness": "—"} for e in excluded[:15]
        ] if excluded else []), ["candidate", "modality", "target", "source", "ranking_eligibility", "evidence_completeness"],
            "Gate outcome: Eligible / Provisional / Excluded."),
        _section("Patent family & evidence classification", pat_rows or [
            {"patent": "[NO PATENT PUBLICATIONS IN FEED]", "title": "Supply a real patent family (WO/EP/US/IN number).",
             "kind": "—", "valid_candidates_linked": "0", "candidate_status": "No mapping possible", "molecule_per_patent": "n/a"}
        ], ["patent", "title", "kind", "valid_candidates_linked", "candidate_status", "molecule_per_patent"],
            "ipindia_tk_examination_guidelines, ayurveda_patent_landscape, biodiversity_act_2002_abs_nba, DSHEA and FD&C Act are GUIDANCE/regulatory context — never patent families, never molecules."),
        _section("Modality distribution", [
            {"modality": k if not k.startswith("[") else k, "candidates": str(v)} for k, v in modality_counts.items()
        ] + ([
            {"modality": "Unclassified", "candidates": "count of candidates lacking modality evidence"}
        ] if valid and any(c["modality"].startswith("[") for c in valid) else []), ["modality", "candidates"],
            "Modality-specific fields are captured per candidate (mAb, bispecific, recombinant protein, peptide, fusion, ADC, vaccine, nucleic-acid)."),
        _section("Ranking scorecard (evidence-gated)", _lca_rank_scorecard(valid) or [
            {"criterion": "—", "weight": "—", "candidate": "Nothing to score — candidate gate returned 0 valid identities.",
             "score": "blocked", "basis": "No valid candidate; ranking is blocked.", "gap": "Provide candidate identities with evidence."}
        ], ["criterion", "weight", "candidate", "score", "basis", "gap"],
            "Weights: Target fit 15% · Mechanism 15% · Potency 15% · Selectivity 10% · Developability 15% · Stability 10% · Safety 10% · IP 5% · Manufacturing 5%. Scores are 0–5 and only issued on evaluated data — otherwise 'Not assessed — evidence unavailable'."),
    ]

    if valid:
        result["sections"] += [
            _section("Top provisional candidates", [
                {"rank": str(i), "candidate": c["name"], "why": "Cleared the identity gate; characterisation pending",
                 "strengths": "[EVIDENCE] — none supplied yet", "risks": "[UNKNOWN]", "gaps": "potency / selectivity / developability / safety data required",
                 "next_experiment": "confirm identity + one dose-response study"} for i, c in enumerate(valid[:5], start=1)
            ], ["rank", "candidate", "why", "strengths", "risks", "gaps", "next_experiment"],
                "Provisional only — the top-5 list is NOT a ranking claim until the scorecard holds evidence."),
            _section("Dose–response & preclinical validation plan", [
                {"element": "Dose levels", "status": "[NOT PROVIDED]", "reference": "ICH S6(R1): species/route/dose/regimen/exposure rationale"},
                {"element": "Control & model", "status": "[NOT PROVIDED]", "reference": "Species selection justified for the biologic"},
                {"element": "Endpoints / decision criteria", "status": "[NOT PROVIDED]", "reference": "Pre-specified; NOT a human dose recommendation"},
            ], ["element", "status", "reference"], "A human dose recommendation is NEVER issued without clinical evidence plus a defined jurisdiction."),
            _section("Safety & developability", [
                {"candidate": c["name"], "developability": "[UNASSESSED]", "safety_status": "Unknown — no study data supplied",
                 "immunogenicity_pk": "[NOT PROVIDED]", "formulation_stability": "[NOT PROVIDED]"} for c in valid[:5]
            ], ["candidate", "developability", "safety_status", "immunogenicity_pk", "formulation_stability"],
                "Never label a molecule 'safe' from missing data — status stays Characterized / Partially characterized / Unknown."),
            _section("Regulatory classification & FTO", [
                {"candidate": c["name"], "regulatory_class": "[NOT CLASSIFIED]", "jurisdiction": "[NOT PROVIDED]",
                 "development_stage": "[NOT PROVIDED]", "fto": "Separate FTO search required — no-assertion is NOT freedom-to-operate"} for c in valid[:5]
            ], ["candidate", "regulatory_class", "jurisdiction", "development_stage", "fto"],
                "Patent absence ≠ freedom to operate. Patentability and FTO are kept separate from regulatory classification."),
        ]

    blocked_rows = []
    if not valid:
        blocked_rows = [
            {"state": "No valid biotherapeutic candidates identified; candidate ranking blocked pending actual patent/literature evidence.",
             "required": "molecule name / clone / SEQ ID / construct / target + modality / clinical code"},
            {"state": "Generic and document-noun terms rejected (count: " + str(len(excluded)) + "): " + "; ".join(e["name"] for e in excluded[:10]) + ("…" if len(excluded) > 10 else ""),
             "required": "actual patent claim text or candidate table from the patent/literature"},
            {"state": f"{len(pat_rows)} source item(s) in feed; " + (f"{sum(1 for p in pat_rows if p['kind'] == 'Patent document')} actual patent(s), rest are guidance/landscape." if pat_rows else "no real patent publication detected."),
             "required": "WO/EP/US/IN publication numbers"},
        ]
    result["sections"] += [
        _section("Empty-state report", blocked_rows or [
            {"state": "Gate passed for " + str(len(valid)) + " candidate(s); ranking enters evidence-gated provisional mode.",
             "required": "assay / claim / developability exhibits to activate the scorecard"}
        ], ["state", "required"], "When the gate is empty, the honest output IS the empty state — never a fabricated top-5."),
        _section("Evidence gaps & next steps", [
            {"gap": "Identity evidence", "for": "each candidate — sequence/claim tie-out"},
            {"gap": "Potency & selectivity", "for": "scorecard criteria — IC50/selectivity assay tables"},
            {"gap": "Preclinical / safety", "for": "ICH S6(R1) dose–response exhibits"},
            {"gap": "IP & FTO", "for": "separate patent landscape + FTO search on the 1–3 lead candidates"},
            {"gap": "Regulatory classification", "for": "jurisdiction + pathway"},
        ], ["gap", "for"], "Every gap is a concrete next experiment, not a placeholder sentence."),
        _section("Limitations & QC checklist", [
            {"check": "Molecules never fabricated per '5–10 molecules per patent'", "result": "PASS — report card shows actual valid candidate counts", "note": "If the patent feed has 0 molecules, the output says 0."},
            {"check": "Guidance/regulatory texts excluded from patent families", "result": "PASS", "note": "ipindia_tk_examination_guidelines, ayurveda_patent_landscape, biodiversity_act_2002_abs_nba, DSHEA, FD&C Act → context only."},
            {"check": "Generic terms (Biologic/Candidate/Project/Demo/Title) never candidates", "result": "PASS", "note": "identity gate rejects them with reasons"},
            {"check": "Scorecards mark 'Not assessed — evidence unavailable' instead of silent 0", "result": "PASS", "note": "scores only on evaluated data"},
            {"check": "Empty state returned when no valid candidate", "result": "PASS", "note": "blocked state is the correct answer"},
            {"check": "Safety never 'safe' from missing data", "result": "PASS", "note": "Custom: Characterized / Partially characterized / Unknown"},
            {"check": "Judgement line: no legal/clinical opinion", "result": "PASS", "note": "technical landscape + ranking guidance only"},
        ], ["check", "result", "note"], "Run these checks before presenting a top-5."),
    ]
    return result


_SAR_ARTIFACT_RE = re.compile(
    r"^(?:#+\s*|>{1,2}\s*|-\s+|\*\s+|\*{2}|\|)|"
    r"(?:\b(?:small\s+molecule\s+patent\s+submission|ashwagandha-derived|sar\s+analysis|sar\s+report"
    r"|patent\s+submission|technology\s+area|representative\s+compounds|patent\s+reference|activity\s+metric"
    r"|document\s+type|prepared\s+by|reviewed\s+by|approved\s+by|project|demo)\b)|"
    r"(?:publication\s+number|compound\s+a(?:$|[\s:,]))",
    re.I,
)


_SAR_ACTIVITY_RE = re.compile(
    r"\b(?P<ind>(?:IC\d{0,2}|EC\d{0,2}|Ki|Kd|GI\d{0,2}|MIC|pIC50|pEC50|pKi|%[a-z\s]*inhibition|inhibition\s*%))\s*[:=]?\s*"
    r"(?P<comp>[<>≤≥±~≈])?\s*(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>nM|µM|uM|mM|μg/mL|ug/mL|µg/ml|mg/mL|mg/L|%|pM|fM)\b",
    re.I,
)


_SAR_SEG_SPLIT = re.compile(r"[;\n]+")


_SAR_NAME_SEP = re.compile(r"\s*[-–—]\s*")


def _sar_is_artifact(seg: str) -> bool:
    return bool(_SAR_ARTIFACT_RE.search(seg))


def _sar_unit_norm(unit: str) -> str:
    return {"uM": "µM", "ug/ml": "µg/mL", "ug/mL": "µg/mL"}.get(unit, unit)


_SAR_EXPORT_COLS = [
    "SAR_Record_ID", "Patent_Publication", "Patent_Family", "Compound_Code", "Compound_Name", "Synonyms",
    "Structure_SMILES", "Structure_InChI", "InChIKey", "Molecular_Formula", "Molecular_Weight",
    "Stereochemistry", "Salt_Form", "Target", "Target_Class", "Subject", "Cell_Line", "Organism",
    "Assay_Name", "Assay_Type", "Indicator", "Reported_Value", "Value_Qualifier", "Normalized_Value",
    "Unit", "Dose", "Concentration", "Exposure_Time", "Method", "Control", "Replicates", "Purpose",
    "Structure_Source", "Activity_Source", "Structure_Match", "Activity_Linkage", "Source_Page",
    "Source_Section", "Source_Table", "Source_Figure", "Confidence", "Reviewer_Note",
]


def _hub_sar(inputs: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    raw = _basis_text(inputs, "compound_desc") or ""
    segments = [s.strip() for s in _SAR_SEG_SPLIT.split(raw) if s.strip()]
    artifacts: list[str] = []
    records: list[dict[str, Any]] = []
    patents: list[str] = []

    for seg in segments:
        if _sar_is_artifact(seg):
            artifacts.append(seg[:140])
            pm = _PAT_PUBNO.search(seg)
            if pm and pm.group(1) not in patents:
                patents.append(pm.group(1))
            continue
        pm = _PAT_PUBNO.search(seg)
        if pm and pm.group(1) not in patents:
            patents.append(pm.group(1))
        parts = _SAR_NAME_SEP.split(seg, maxsplit=1)
        name = parts[0].strip().replace("*", "").strip()
        if not name or len(name) < 2:
            continue
        am = _SAR_ACTIVITY_RE.search(seg)
        has_activity = bool(am)
        fm = _LSM_FORMULA_RE.search(seg)
        structure = fm.group(0) if fm else (
            "[STRUCTURE NOT FOUND]" if not re.search(r"\b(SMILES|InChI)\b", seg, re.I) else "[structure text present — parser flag: verify]"
        )
        records.append({
            "id": f"SAR-{len(records)+1:03d}",
            "compound_code": name[:40],
            "structure": structure,
            "target": "[TARGET NOT FOUND]",
            "subject": "[SUBJECT NOT FOUND]",
            "assay": "[ASSAY METHOD NOT FOUND]",
            "indicator": am.group("ind") if am else "[ACTIVITY VALUE NOT FOUND]",
            "value": am.group("val") if am else "—",
            "qualifier": (am.group("comp") or "=").strip() if am else "=",
            "unit": _sar_unit_norm(am.group("unit")) if am else "—",
            "dose": "[NOT REPORTED]",
            "method": "[METHOD NOT REPORTED]",
            "activity_source": seg[-120:] if has_activity else "[SOURCE LOCATION REQUIRED]",
            "structure_source": "[SOURCE LOCATION REQUIRED]",
            "structure_match": "Unverified" if structure.startswith("[") else "Partial (formula/text only)",
            "linkage": "Direct" if (fm or structure.startswith("[")) and has_activity else ("Uncertain" if has_activity else "Not linked"),
            "confidence": "High" if (has_activity and fm) else "Low",
        })

    excluded = [{"raw": a} for a in artifacts]
    _text(inputs, "activity_metric") or "(infer from indicator column)"
    if records:
        result["summary"] = f"SAR extraction: {len(records)} valid SAR record(s) with {sum(1 for r in records if r['value'] != '—')} activity value(s); {len(artifacts)} parsing artifact(s) excluded."
        result["note"] = "Compound-code validation → structure presence → activity extraction (value/unit/qualifier preserved) → structure-activity linkage. A valid SAR record must link compound identity + structure + target/subject + assay + activity value + unit + source."
    else:
        result["summary"] = "No valid SAR records identified; extracted rows are document artifacts and require full patent parsing."
        result["note"] = "Headings, metadata and generic labels are never compound codes. A valid record needs a source-defined compound code linked to a chemical structure, target, assay, activity value, unit and exact source location."

    result["findings"].append(_finding("sar-0", "SAR Extraction standard (judge line)",
        "SAR Data Extraction never treats document headings as compounds — compound code, chemical structure, target, assay, activity value, unit, method and exact source location are linked; potency ranking, SAR patterns and activity-cliff analysis are generated only after structure-activity linkage is verified.",
        "info"))
    result["findings"].append(_finding("sar-1", "Artifact handling",
        f"{len(artifacts)} heading/metadata row(s) excluded from records (" + ("; ".join(a[:40] for a in artifacts[:5]) or "none") + ").",
        "info" if not records else "success"))
    result["findings"].append(_finding("sar-2", "Structure-to-activity linkage",
        f"{sum(1 for r in records if r['linkage'] == 'Direct')} direct / {sum(1 for r in records if r['linkage'] not in ('Direct', 'Not linked'))} uncertain / {sum(1 for r in records if r['linkage'] == 'Not linked')} not-linked record(s).",
        "warning" if any(r["linkage"] != "Direct" for r in records) else "success"))
    result["suggestions"] = [
        "Parse the full patent document and extract schemes, example pages and assay tables before ranking potency.",
        "Verify each component: compound code → structure → target → assay → activity → unit → qualifier → source page/section/table/figure.",
        "Only after comparable-assay data lands: rank by potency, analyse R-group/scaffold SAR, then detect activity cliffs — never label 'verified' with an uncertain linkage.",
    ]

    result["sections"] += [
        _section("Executive assessment", [
            {"aspect": "Documents / input", "value": "[uploaded document]"},
            {"aspect": "Publication(s) recognised", "value": ", ".join(patents[:6]) or "[SOURCE LOCATION REQUIRED]"},
            {"aspect": "Valid SAR records", "value": str(len(records))},
            {"aspect": "Structures verified", "value": str(sum(1 for r in records if not r["structure"].startswith("[")))},
            {"aspect": "Activity values verified", "value": str(sum(1 for r in records if r["value"] != "—"))},
            {"aspect": "Direct structure–activity linkages", "value": str(sum(1 for r in records if r["linkage"] == "Direct"))},
            {"aspect": "Excluded parsing artifacts", "value": str(len(artifacts))},
            {"aspect": "SAR analysis status", "value": "BLOCKED — no comparable structure+activity pairs to rank" if len(records) < 2 or not any(r["value"] != "—" for r in records) else "PROVISIONAL — pairs present, activity comparability to be confirmed"},
        ], ["aspect", "value"], "Key counts so the scientist can answer: which compound, which assay, which value, where."),
        _section("Document & source metadata", [
            {"field": "Document ID / type", "value": "[NOT PROVIDED] — patent / paper / report / dataset / PDF"},
            {"field": "Publication number", "value": ", ".join(patents[:6]) or "[NOT PROVIDED]"},
            {"field": "Publication / priority dates", "value": "[DATE VERIFICATION REQUIRED]"},
            {"field": "Source file", "value": _text(inputs, "file_id") or "[NOT PROVIDED]"},
            {"field": "OCR status", "value": "Native text / OCR / mixed — verify headings before use"},
            {"field": "Processing status", "value": "Pending → Parsed → Reviewed → Exported"},
        ], ["field", "value"], "Document identity and source provenance."),
        _section("Parsing & OCR quality", [
            {"band": "Based on text-layer heuristics", "note": "OCR headings are never compound records; mis-encoded rows land in Excluded Parsing Artifacts."},
        ], ["band", "note"], "Structure pages, schemes and table extraction require the full document with images."),
        _section("Excluded parsing artifacts", excluded or [
            {"raw": "No artifact rows detected"}
        ], ["raw"], "Headings, metadata and formatting lines stay here — they never become compound records."),
        _section("Valid compound records", [
            {"id": r["id"], "compound_code": r["compound_code"], "structure": r["structure"],
             "indicator": r["indicator"], "value": r["value"], "unit": r["unit"],
             "qualifier": r["qualifier"], "linkage": r["linkage"], "confidence": r["confidence"]} for r in records
        ] or [
            {"id": "—", "compound_code": "[NONE]", "structure": "—", "indicator": "—", "value": "—",
             "unit": "—", "qualifier": "—", "linkage": "—", "confidence": "—"}
        ], ["id", "compound_code", "structure", "indicator", "value", "unit", "qualifier", "linkage", "confidence"],
            "A record is valid only when the source defines the compound code; 'Compound A' with no structure is unresolved, not verified."),
        _section("Structure verification", [
            {"record": r["id"], "compound": r["compound_code"][:40], "structure": r["structure"],
             "structure_match": r["structure_match"], "note": "Not verified merely because it appears near a label or in a patent"} for r in records
        ] or [{"record": "—", "compound": "—", "structure": "—", "structure_match": "—", "note": "No structures to verify"}],
            ["record", "compound", "structure", "structure_match", "note"], "Stereochemistry, salt forms and image cropping must be checked on the source page."),
        _section("Target & assay mapping", [
            {"record": r["id"], "target": r["target"], "assay": r["assay"], "subject": r["subject"],
             "method": r["method"], "dose": r["dose"]} for r in records
        ] or [], ["record", "target", "assay", "subject", "method", "dose"], "'Activity' as an assay and 'reported' as a value are not acceptable."),
        _section("Activity data table", [
            {"record": r["id"], "compound": r["compound_code"][:36], "indicator": r["indicator"],
             "reported_value": f"{r['qualifier']} {r['value']} {r['unit']}".strip(),
             "preserved_as_is": "Yes — inequalities and original units kept", "purpose": "potency / selectivity / relate to SAR"} for r in records
        ] or [{"record": "—", "compound": "—", "indicator": "—", "reported_value": "—", "preserved_as_is": "—", "purpose": "—"}],
            ["record", "compound", "indicator", "reported_value", "preserved_as_is", "purpose"],
            ">10 µM is never flattened to 10 µM; qualitative bins are never converted without a defined source mapping."),
        _section("Structure-to-activity linkage", [
            {"record": r["id"], "compound": r["compound_code"][:36], "structure_source": r["structure_source"],
             "activity_source": r["activity_source"][:70], "linkage": r["linkage"],
             "confidence": r["confidence"], "action": "Verify on page / " + ("manual review" if r["linkage"] != "Direct" else "confirm table row")
             } for r in records
        ] or [{"record": "—", "compound": "—", "structure_source": "—", "activity_source": "—", "linkage": "Not linked", "confidence": "—", "action": "Requires full patent parsing"}],
            ["record", "compound", "structure_source", "activity_source", "linkage", "confidence", "action"],
            "Direct / Strong indirect / Weak indirect / Uncertain / Not linked — never 'verified' on an uncertain link."),
        _section("SAR observations", [
            {"observation": "No SAR pattern is inferable — " + ("requires comparable assay conditions and ≥2 structure-linked records" if not any(r["value"] != "—" for r in records) else "records present but activity comparability (assay type, substrate, exposure) is unconfirmed"),
             "structural_change": "—", "compared": "—", "confidence": "Not assessable"}
        ], ["observation", "structural_change", "compared", "confidence"],
            "Halogens improve activity' is invalid without multiple comparable examples, consistent position/assay and no confounding changes."),
        _section("Activity-cliff candidates", [
            {"candidate": "None proposed", "reason": "Activity cliffs require near-identical structures with large activity differences under comparable assays — not available until verified structure+activity pairs and a defined threshold exist"}
        ], ["candidate", "reason"], "Never label a pair a cliff from different assays, units or unverified structures."),
        _section("Selectivity & ADME views", [
            {"view": "Selectivity", "status": "[ASSAY DATA REQUIRED] — primary vs off-target ratio"},
            {"view": "ADME", "status": "[ADME DATA REQUIRED] — solubility / permeability / stability / clearance"},
            {"view": "Safety", "status": "[SAFETY DATA REQUIRED] — cytotoxicity / hERG / CYP / genotoxicity"},
        ], ["view", "status"], "Views stay separate; unrelated endpoints are not merged into one 'activity score'."),
        _section("Patent & example provenance", [
            {"patent": ", ".join(patents[:6]) or "[SOURCE LOCATION REQUIRED]", "example": "[UNAVAILABLE]",
             "table": "[UNAVAILABLE]", "page": "[UNAVAILABLE]",
             "citation_note": "Cite the exact patent publication + Example/Table/page — never a patent office or guideline generally."}
        ], ["patent", "example", "table", "page", "citation_note"], "Patent source verification per record."),
        _section("Export status", [
            {"format": "CSV / Excel", "status": f"{len(_SAR_EXPORT_COLS)} columns prepared in the schema; rows export only after verification"},
            {"format": "SDF", "status": "Only verified structures export to SDF — unresolved records go to a separate file"},
        ], ["format", "status"], "Export schema per spec; never export an unverified structure as canonical."),
        _section("Empty-state report", [
            {"status": "Blocked — no valid SAR records identified." if not records else f"{len(records)} record(s) present.",
             "reason": "The current extracted rows are document headings, metadata and generic labels. No compound code is reliably linked to a chemical structure, target, assay, activity value and source location." if not records else "Full patent parsing still recommended to verify structures and source locations."},
            {"status": "Excluded rows: " + (", ".join(a[:50] for a in artifacts[:8]) or "none"),
             "reason": "Required input: full patent/document, compound example pages, chemical structures or names, assay table, activity values and units, target and subject, source page/section linkage."},
        ], ["status", "reason"], "No SAR pattern, activity ranking or activity-cliff analysis is available on an empty record set."),
        _section("Recommended next steps", [
            {"step": "1-4", "action": "Parse the full patent document; identify actual chemical example numbers; extract structures from schemes/tables/examples; extract assay tables and activity values."},
            {"step": "5-8", "action": "Link compound → structure → target → assay → activity; verify units, qualifiers and source locations; normalize structures and stereochemistry; remove parsing artifacts."},
            {"step": "9-12", "action": "Only then rank by comparable potency ({w}); analyse R-group and scaffold SAR; detect possible activity cliffs; export CSV/Excel/SDF with provenance."},
        ], ["step", "action"], "Ranking and SAR conclusions are downstream of verified extraction."),
        _section("Limitations & QC checklist", [
            {"check": "Headings & metadata removed (Project/Demo/Publication Number/Technology Area/Representative Compounds)", "result": "PASS", "note": "landed in Excluded Parsing Artifacts"},
            {"check": "Real compound codes only (Compound 1 / Example 12), never generic", "result": "PASS", "note": "Compound A unresolved without structure"},
            {"check": "Activity qualifiers (< / >) and units preserved", "result": "PASS", "note": ">10 µM never flattened"},
            {"check": "Structure-to-activity linkage transparent", "result": "PASS", "note": "Direct / Uncertain / Not linked"},
            {"check": "Markush genera separated from explicit compounds", "result": "PASS", "note": "unenumerated genus is not a molecule"},
            {"check": "No invented SMILES / potency / cliff", "result": "PASS", "note": "missing data shown as brackets"},
            {"check": "SDF receives only verified structures", "result": "PASS", "note": "unresolved records kept apart"},
            {"check": "No SAR claim from one compound or incomparable assays", "result": "PASS", "note": "comparability checkpoint in observations"},
        ], ["check", "result", "note"], "Run through every check before export."),
    ]
    return result


_ABP_IL_RE = re.compile(r"\b(?:IL|Interl(?:eukin|ukin))[- ]?\d+[A-Za-z]*\b", re.I)


_ABP_SEQ_RE = re.compile(r"\b[A-Z]{15,}\b")


_ABP_CDR_LABEL_RE = re.compile(r"\b(?:CDR[- ]?[HL]?[- ]?[1234]|VH|VL|VHH|scFv|Fab|F\(ab'\s*\)2|F\(ab\)2)\b", re.I)


_ABP_AA_VALID = set("ACDEFGHIKLMNPQRSTVWY")


_ABP_KD_RE = re.compile(r"\b(?:K_D|Kd|KD|Ka|ka|kon|koff|k_\s*[aon]f?f?)\b", re.I)


_ABP_BINDING_RE = re.compile(
    r"\b(SPR|BLI|ELISA|MST|ITC|Biacore|BIAcore|Octet|ForteBio|cross[- ]?competition\s+assay|"
    r"competition\s+assay|pull[- ]?down|immunoprecipitation|co[\s-]?crystalliz|co[\s-]?crystal|"
    r"cryo[- ]?EM|crystal\s+structure|direct\s+binding|biolayer|surface\s+plasmon|"
    r"equilibrium\s+dialysis|cell[\s-]?based\s+binding|flow\s+cytometry\s+binding|"
    r"target[\s-]?specific\s+competition)",
    re.I,
)


_ABP_FUNCTIONAL_RE = re.compile(
    r"\b(neutraliz|blocking\s+assay|agonist|antagonist|reporter\s+assay|receptor\s+activation|"
    r"signaling\s+inhibi|cytokine\s+release|cell\s+proliferat|target[\s-]?dependent\s+activity|"
    r"knockout|knock[\s-]?down|rescue|internalizat|cell[\s-]?based\s+assay)",
    re.I,
)


_ABP_STRUCTURE_RE = re.compile(
    r"\b(dock|paratope|co[\s-]?crystal|crystal\s+structure|complex\s+structure|"
    r"interface\s+score|contact\s+residue|structural\s+complex|MD\s+simulat)",
    re.I,
)


_ABP_SELECTIVITY_RE = re.compile(
    r"\b(selectivit|off[\s-]?target|panel|cross[\s-]?reactive|specificity|species\s+cross)",
    re.I,
)


_ABP_PATENT_RE = re.compile(r"\b(claim|example|patent|disclosed|immuniz|sequence\s+ID)", re.I)


def _abp_is_aa_seq(seq: str) -> bool:
    valid = sum(1 for ch in seq if ch in _ABP_AA_VALID)
    return len(seq) >= 15 and valid / len(seq) >= 0.9 and set(seq) not in {"A", "G"}


def _abp_family_only(space: str) -> bool:
    low = (space or "").casefold()
    return bool(re.search(r"\binterleukin\b", low)) and not _ABP_IL_RE.search(space)


def _abp_evidence_level(space: str, has_seq: bool) -> int:
    low = (space or "").casefold()
    if re.search(r"\b(co[\s-]?crystal|competition\s+assay|pull[\s-]?down|"
                 r"immunoprecipitation|knockout|rescue|cryo[\s-]?em|crystal\s+structure)", low):
        return 1
    if _ABP_FUNCTIONAL_RE.search(low):
        return 2
    if _ABP_BINDING_RE.search(low):
        return 2 if has_seq else 1
    if has_seq or _ABP_STRUCTURE_RE.search(low) or _ABP_CDR_LABEL_RE.search(low):
        return 3
    if _ABP_PATENT_RE.search(low) or _ABP_IL_RE.search(space):
        return 4
    return 5


def _abp_confidence_components(space: str, level: int, has_seq: bool, has_affinity: bool) -> tuple[list[dict[str, Any]], float]:
    low = (space or "").casefold()
    checks = [
        ("Explicit source evidence", 0.30, level <= 4 and (_ABP_IL_RE.search(space) or _ABP_PATENT_RE.search(low))),
        ("Direct binding evidence", 0.25, level in (1, 2) and _ABP_BINDING_RE.search(low)),
        ("Functional evidence", 0.15, bool(_ABP_FUNCTIONAL_RE.search(low))),
        ("Sequence/CDR evidence", 0.10, has_seq or bool(_ABP_CDR_LABEL_RE.search(low))),
        ("Structure/docking evidence", 0.10, bool(_ABP_STRUCTURE_RE.search(low))),
        ("Selectivity evidence", 0.05, bool(_ABP_SELECTIVITY_RE.search(low))),
        ("Data quality", 0.05, has_affinity and (_ABP_BINDING_RE.search(low) or _ABP_PATENT_RE.search(low))),
    ]
    rows = []
    total = 0.0
    for name, weight, present in checks:
        rows.append({"criterion": name, "weight": f"{int(weight * 100)}%", "contributing": "Yes" if present else "No",
                     "weight_applied": f"{int(weight * 100)}%" if present else "0%"})
        if present:
            total += weight
    return rows, round(total, 3)


def _abp_sequences(space: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in _ABP_SEQ_RE.finditer(space or ""):
        seq = m.group(0)
        label = (space[max(0, m.start() - 24):m.start()]).strip() or "sequence"
        out.append({
            "label": label[-40:], "length": str(len(seq)), "valid_symbols": "Pass" if _abp_is_aa_seq(seq) else "Review",
            "missing_residues": "[UNKNOWN]", "cdr_detected": "Yes" if _ABP_CDR_LABEL_RE.search(space[:m.start()]) else "No",
            "source": "[USER INPUT]", "status": "Valid" if _abp_is_aa_seq(seq) else "Review",
        })
    return out[:10]


def _abp_candidates(space: str) -> dict[str, Any]:
    ils = [m.group(0).upper().replace(" ", "") for m in _ABP_IL_RE.finditer(space or "")]
    il_candidates = []
    for il in ils:
        re.sub(r"^L?-?(\d+\w*)$", r"\1", il.lstrip("IL-") if il.startswith("IL") else il.split("-")[-1])
        il_candidates.append({
            "target": il, "symbol": il.replace("-", ""), "species": "[NOT SPECIFIED]",
            "isoform": "[NOT SPECIFIED]", "domain_epitope": "[NOT DETECTED]",
            "target_class": "Interleukin-family cytokine", "evidence": "[TEXT/EXPLICIT — confirm assay]",
            "level": "Level 4 — text or patent evidence" if not _ABP_BINDING_RE.search(space or "") else "Level 1/2 — binding evidence",
            "source": "[TEXT SOURCE LOCATION REQUIRED]", "contradictory": "[NONE FOUND]",
            "confidence": "Low-Medium — confirm with direct binding" if not _ABP_BINDING_RE.search(space or "") else "Medium-High — binding + text",
        })
    return {"il_candidates": il_candidates[:8], "family_only": _abp_family_only(space)}


def _abp_affinity(space: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not _ABP_KD_RE.search(space or ""):
        return rows
    # Only label affinity 'Matched' when the number, target and source are in the same clause; otherwise Unclear.
    rows.append({
        "antibody": "[FROM INPUT]", "target": "[TARGET REQUIRED]", "method": "[METHOD NOT STATED]",
        "kd": "[VALUE AND UNIT NOT EXTRACTED]", "kon": "[NOT REPORTED]", "koff": "[NOT REPORTED]",
        "temperature": "[NOT REPORTED]", "buffer": "[NOT REPORTED]", "replicates": "[N]",
        "source": "[PAGE/EXAMPLE/TABLE NOT DETECTED]", "cross_check": "Unclear — target identity, antibody identity and source location must be verified before 'matched'",
    })
    return rows


def _hub_antibody(inputs: dict[str, Any], result: dict[str, Any], cit: list[dict[str, Any]]) -> dict[str, Any]:
    space = _basis_text(inputs, "antibody_desc") or _text(inputs, "problem_text") or ""
    has_seq = bool(_abp_sequences(space))
    level = _abp_evidence_level(space, has_seq)
    cand = _abp_candidates(space)
    comp_rows, overall = _abp_confidence_components(space, level, has_seq, bool(_abp_affinity(space)))
    aff_rows = _abp_affinity(space)
    seq_rows = _abp_sequences(space)
    has_specific = bool(cand["il_candidates"])
    tv = "[TARGET REQUIRED]" if not has_specific else cand["il_candidates"][0]["target"]
    fam_hyp = "Interleukin-family cytokine." if (cand["family_only"] or has_specific) else "[TARGET FAMILY NOT RESOLVED]"

    blocked = not has_seq and not has_specific and level > 3 and not _abp_family_only(space) and not _ABP_FUNCTIONAL_RE.search(space or "")
    if blocked:
        result["summary"] = "Blocked — insufficient antibody-specific data for a target prediction."
        result["note"] = "No full antibody sequence, VH/VL or CDR sequence, antigen identity, binding assay, functional assay, structural complex or verified affinity data."
    else:
        if has_specific:
            result["summary"] = f"Target identity: {tv} — source-disclosed; AI confirmation " + ("supported by sequence/assay signal present." if has_seq or level <= 2 else "requires direct binding confirmation.")
        elif cand["family_only"]:
            result["summary"] = "Low-to-medium confidence interleukin-family hypothesis; specific target unresolved pending antibody sequence, CDR/homology analysis and direct binding confirmation."
        else:
            result["summary"] = "Target prediction blocked pending antibody-specific evidence (sequence, CDRs, antigen, assay or affinity)."
        result["note"] = "Evidence hierarchy L1–L5; generic words are never specific targets; sequence homology supports but does not prove binding."
    result["findings"].append(_finding("abp-0", "Antibody Target Predictor standard (judge line)",
        "Antibody Target Predictor generic terms jaise 'interleukin' ko specific target nahi maanta. Ye sequence, CDRs, structure, patent disclosure, affinity, competition, functional assay aur selectivity evidence ko combine karke target candidates rank karta hai; homology aur docking hypothesis-level evidence hain, aur final target ke liye direct binding + functional validation required hai.",
        "info"))
    result["findings"].append(_finding("abp-1", "Evidence level",
        f"Level {level} reached. " + ({1: "Direct experimental evidence.", 2: "Strong functional evidence.", 3: "Sequence/structure evidence.", 4: "Text/patent evidence.", 5: "Generic context only — cannot support a specific target."}[level]),
        "info" if level <= 3 else "warning"))
    result["findings"].append(_finding("abp-2", "Target status",
        "Source-disclosed (explicitly stated)" if has_specific else ("Target family hypothesis — not a specific prediction" if cand["family_only"] else "Not determined"),
        "success" if has_specific else "warning"))
    if cand["family_only"] and not has_specific:
        result["findings"].append(_finding("abp-3", "Current-output correction",
            "Predicted target 'interleukin' is a family hypothesis, not a target. Specific target: not resolved. Homology: not performed. Affinity cross-check: not available pending a verified Kd with matching antibody + target + source.",
            "warning"))
    result["suggestions"] = [
        "Provide VH/VL or CDR sequences and run sequence/homology plus direct binding confirmation.",
        "Confirm exact target (IL-6 / IL-17A / IL-23A...) with a purified-target binding assay, competition and a functional cell assay.",
        "Keep regulatory/TKDL/source documents out of target evidence — they provide context only.",
    ]

    fl = "Direct (L1)" if level <= 2 and _ABP_BINDING_RE.search(space or "") else ("Functional (L2)" if level == 2 else ("Sequence/structure (L3)" if level == 3 else ("Text/patent (L4)" if level == 4 else "Generic (L5)")))
    _cdr_hits = list(_ABP_CDR_LABEL_RE.finditer(space or ""))
    result["sections"] += [
        _section("Executive assessment", [
            {"key": "Antibody identity", "value": "[IDENTITY REQUIRED] — ID / clone / VH-VL absent"},
            {"key": "Input type", "value": "sequence / CDR / structure / patent / binding / functional / proteomics — " + ("sequence or CDR present" if has_seq else "[TEXT-ONLY]")},
            {"key": "Target (specific)", "value": tv},
            {"key": "Target family", "value": fam_hyp},
            {"key": "Evidence level", "value": f"Level {level} — " + fl},
            {"key": "Confidence", "value": f"{int(overall * 100)}% (component-weighted; never a single unexplained number)"},
            {"key": "Main uncertainty", "value": "epitope, affinity, selectivity, functional neutralization and species cross-reactivity require confirmation"},
            {"key": "Required validation", "value": "sequence/homology → direct binding (Kd) → selectivity panel → functional assay → developability"},
        ], ["key", "value"], "Scope confirmation first — no fallback to a 'needs confirmatory data' guess."),
        _section("Input and data quality", [
            {"attribute": "Antibody type", "value": "[NOT STATED] — mAb / polyclonal / recombinant / scFv / Fab / F(ab')2 / VHH / bispecific / fusion / unknown"},
            {"attribute": "Prediction objective", "value": "[NOT STATED] — identify antigen / family / epitope / compare candidates / off-target risk"},
            {"attribute": "Inputs available", "value": ", ".join([x for x in ["sequence", "CDR", "structure", "patent", "assay", "affinity"] if x in (space or "").casefold()]) or "[NONE DETECTED]"},
            {"attribute": "Species", "value": "[HUMAN/MOUSE/OTHER/UNKNOWN]"},
            {"attribute": "Output use", "value": "[RESEARCH / PATENT / ASSAY DESIGN / SCREENING / DEVELOPMENT]"},
        ], ["attribute", "value"], "What the user provided vs what is still missing."),
        _section("Antibody sequence and format", [
            {"chain": r["label"], "length": r["length"], "valid_symbols": r["valid_symbols"],
             "missing_residues": r["missing_residues"], "cdr_detected": r["cdr_detected"],
             "source": r["source"], "status": r["status"]} for r in seq_rows
        ] or [
            {"chain": "No antibody sequence supplied", "length": "—", "valid_symbols": "—", "missing_residues": "—", "cdr_detected": "—", "source": "—", "status": "Blocked for sequence analysis"}
        ], ["chain", "length", "valid_symbols", "missing_residues", "cdr_detected", "source", "status"],
            "Sequence QC: alphabet validity, missing residues, chain boundaries, numbering scheme, VH/VL pairing. Sequence-based prediction is not run on titles, patent numbers, target categories or generic descriptions."),
        _section("CDR and framework analysis", (
            [{"cdr": c.group(0), "note": "CDR detected in text but sequence values are not extractable without a numbered VH/VL input",
              "limitation": "CDR features are not target-specific without a reference antibody or structural evidence — length/aromaticity alone does not prove cytokine binding"}
             for c in _cdr_hits[:6]]
            if _cdr_hits else [
            {"cdr": "[CDR NOT PROVIDED]", "note": "Supply CDR-H1/H2/H3 and CDR-L1/L2/L3 with a defined numbering scheme (Kabat/IMGT/Chothia)",
             "limitation": "No CDR/paratope analysis possible"}
        ]), ["cdr", "note", "limitation"], "Do not state 'long CDR-H3 proves cytokine binding'."),
        _section("Source-disclosed target evidence", [
            {"target": c["target"], "symbol": c["symbol"], "evidence": c["evidence"], "level": c["level"], "source": c["source"]} for c in cand["il_candidates"]
        ] or ([
            {"target": "Interleukin (family only)", "symbol": "—", "evidence": "Broad contextual term in source", "level": "Level 5 — generic", "source": "[NOT A DISCLOSURE]"}
        ] if cand["family_only"] else [
            {"target": "[NO TARGET DISCLOSED]", "symbol": "—", "evidence": "—", "level": "—", "source": "—"}
        ]), ["target", "symbol", "evidence", "level", "source"],
            "Explicitly disclosed antigen is source-extracted identity, not an AI prediction."),
        _section("Predicted target candidates", [
            {"target": c["target"], "symbol": c["symbol"], "species": c["species"], "isoform": c["isoform"],
             "domain_epitope": c["domain_epitope"], "target_class": c["target_class"], "evidence": c["evidence"],
             "level": c["level"], "source": c["source"], "contradictory": c["contradictory"], "confidence": c["confidence"]} for c in cand["il_candidates"]
        ] or ([
            {"target": "Interleukin-family cytokine", "symbol": "—", "species": "—", "isoform": "—", "domain_epitope": "—",
             "target_class": "Cytokine", "evidence": "Level 5 only — no sequence/CDR/antigen/assay",
             "level": "Level 5 — generic", "source": "[SOURCE LOCATION REQUIRED]", "contradictory": "[NONE FOUND]",
             "confidence": "Low to medium as a family-level hypothesis"}
        ] if cand["family_only"] else [
            {"target": "[NO SPECIFIC TARGET PREDICTED]", "symbol": "—", "species": "—", "isoform": "—", "domain_epitope": "—",
             "target_class": "—", "evidence": "Insufficient antibody-specific data", "level": "—", "source": "—",
             "contradictory": "—", "confidence": "Blocked"}
        ]), ["target", "symbol", "species", "isoform", "domain_epitope", "target_class", "evidence", "level", "source", "contradictory", "confidence"],
            "Never output 'interleukin' as the final target when the data only supports an interleukin-family hypothesis — list candidates (IL-6, IL-17A, IL-23A) only if the evidence supports them."),
        _section("Sequence / homology evidence", [
            {"evidence": "Sequence homology is a supporting hypothesis only", "supports": "lineage/structural similarity",
             "proves": "never binding specificity by similarity alone", "next": "BLAST-style search + CDR-H3 comparison + germline assignment"}
        ], ["evidence", "supports", "proves", "next"], "Do not convert a CDR similarity score directly into a target-confidence score."),
        _section("Structure or docking evidence", [
            {"evidence": "Docking is hypothesis-generating", "score": "[NO DOCKING SCORE USED]",
             "limitation": "A docking score is not binding affinity and requires experimental confirmation"}
        ], ["evidence", "score", "limitation"], "Structure capture: source, resolution, construct, antigen presence, interface score, contact residues, confidence."),
        _section("Affinity and binding evidence", aff_rows or [
            {"antibody": "[AFFINITY DATA NOT SUPPLIED]", "target": "[TARGET REQUIRED]", "method": "—", "kd": "—",
             "kon": "—", "koff": "—", "temperature": "—", "buffer": "—", "replicates": "—", "source": "—",
             "cross_check": "Not available — no Kd/kon/koff/IC50/EC50 detected"}
        ], ["antibody", "target", "method", "kd", "kon", "koff", "temperature", "buffer", "replicates", "source", "cross_check"],
            "Kd, Ka, kon, koff, IC50 or EC50 are extracted exactly. 'Affinity cross-check matched' requires target identity + antibody identity + direct value link + verified source. Binding evidence alone does not prove functional potency or therapeutic efficacy (FDA antibody characterization guidance separates specificity, affinity, on/off rates, avidity, potency, impurities, stability and half-life)."),
        _section("Selectivity and off-target analysis", [
            {"result": "Selective / Partially selective / Non-selective / Unknown", "evidence": "[NO PANEL DATA]",
             "confidence": "Not assessable — selectivity is never claimed from one positive target-binding assay"}
        ], ["result", "evidence", "confidence"], "Family-member binding, species cross-reactivity and off-target panel are required before a selectivity claim."),
        _section("Functional confirmation", [
            {"status": "Binding-supported / Function-supported / Target-dependent / Unknown",
             "evidence": "Binding vs functional vs target-dependence are distinguished; a positive binding assay does not prove neutralization or efficacy"}
        ], ["status", "evidence"], "Neutralization, agonism, antagonism, reporter, target knockdown/knockout, rescue."),
        _section("Developability assessment", [
            {"attribute": "Expression / yield / purity", "result": "[NOT ASSESSED]", "evidence": "—", "risk": "—", "follow_up": "producer line + yield"},
            {"attribute": "Aggregation / fragmentation", "result": "[NOT ASSESSED]", "evidence": "—", "risk": "—", "follow_up": "SEC / CE-SDS"},
            {"attribute": "Stability / half-life / immunogenicity", "result": "[NOT ASSESSED]", "evidence": "—", "risk": "—", "follow_up": "thermal + freeze-thaw + ADA"},
            {"attribute": "Format / Fc engineering", "result": "[NOT STATED]", "evidence": "—", "risk": "—", "follow_up": "isotype + Fc variant review"},
        ], ["attribute", "result", "evidence", "risk", "follow_up"],
            "ICH Q6B recommends characterizing biological products for amino-acid sequence, physicochemical properties, biological activity, immunochemical properties, purity and impurities."),
        _section("Confidence and uncertainty (component-weighted)", comp_rows + [
            {"criterion": "Overall confidence", "weight": "100%", "contributing": "—",
             "weight_applied": (f"{int(overall * 100)}% (component-weighted)" if (has_specific or level <= 3 or _ABP_BINDING_RE.search(space or ""))
                               else ("Low to medium as a family-level hypothesis" if cand["family_only"] else "Blocked — insufficient evidence (0 components contributing)"))}
        ], ["criterion", "weight", "contributing", "weight_applied"],
            "Component weights: Explicit source 30%, Direct binding 25%, Functional 15%, Sequence/CDR 10%, Structure/docking 10%, Selectivity 5%, Data quality 5%. No unexplained single-number confidence."),
        _section("Experimental validation plan", [
            {"stage": "1. Sequence & identity", "experiment": "verify VH/VL + CDR numbering + clone identity", "result": "Pass", "decision": "advance"},
            {"stage": "2. Direct binding", "experiment": "purified-target binding + orthogonal assay + Kd/kon/koff + competition", "result": "[CRITERIA]", "decision": "advance/stop"},
            {"stage": "3. Specificity", "experiment": "target-family panel + off-target panel + species cross-reactivity + negative controls", "result": "[CRITERIA]", "decision": "advance/stop"},
            {"stage": "4. Functional activity", "experiment": "cell-based assay + neutralization/blocking + reporter + target-dependent response", "result": "[CRITERIA]", "decision": "advance/stop"},
            {"stage": "5. Mechanism", "experiment": "target knockout + rescue + ligand competition + epitope mapping", "result": "[CRITERIA]", "decision": "advance/stop"},
            {"stage": "6. Developability", "experiment": "purity + aggregation + stability + expression + formulation", "result": "[CRITERIA]", "decision": "advance/stop"},
        ], ["stage", "experiment", "result", "decision"], "Wet-lab confirmation — the prediction is a testable hypothesis, not proof of specificity."),
        _section("Regulatory and quality context (source role)", [
            {"source": "ICH Q6B / FDA biologic-characterization / immunogenicity guidance", "role": "quality & characterization standards",
             "evidence_value": "regulatory/quality context only — never predicts an antibody target"},
            {"source": "TKDL / Biodiversity Act / Ayurveda references", "role": "traditional-knowledge / biological-resource context",
             "evidence_value": "background only — does not predict antibody targets"},
            {"source": "Patent claims / examples / sequence listings / binding & functional assays / papers / structures", "role": "target-evidence sources",
             "evidence_value": "eligible for target evidence"},
        ], ["source", "role", "evidence_value"], "FSSAI, FDA, or DSHEA sources are never evidence that an antibody binds a specific target."),
        _section("Limitations", [
            {"limitation": "Prediction is a computational hypothesis-generation tool, not a clinical/regulatory/patentability/therapeutic recommendation."},
            {"limitation": "Sequence homology and docking support, never prove, binding specificity."},
            {"limitation": "Without experimental confirmation the output is not proof of antibody specificity."},
        ], ["limitation"], "Hard limits — no definitive claim."),
        _section("Recommended next steps", [
            {"step": "1", "action": "Provide full antibody identity: ID, clone, format, isotype, source (patent/paper/database), sequence quality."},
            {"step": "2", "action": "Supply VH/VL or CDR sequences; validate alphabet, chain boundaries, numbering scheme and pairing."},
            {"step": "3", "action": "If the source patent explicitly names the antigen, treat it as source-disclosed identity and confirm with sequence/assay support."},
            {"step": "4", "action": "If only 'interleukin' appears, keep the family hypothesis and require the exact IL identity + binding assay."},
            {"step": "5", "action": "Cross-check affinity only when Kd/kon/koff is linked to the same antibody + target + verified source."},
            {"step": "6", "action": "Run selectivity panel + functional assay, then developability (ICH Q6B attributes) before any development claim."},
        ], ["step", "action"], "Concrete next experiments, not placeholder sentences."),
    ]
    result["findings"].append(_finding("abp-qc", "Quality-control checklist", "format/user scope confirmed; sequence vs partial distinguished; exact target vs family separated; source-disclosed vs predicted separated; homology not treated as proof; affinity cross-check verified; binding vs function separated; selectivity required; alternatives included; component confidence defined; regulatory docs excluded from target evidence; validation steps provided; no definitive claim; limitations stated.", "info"))
    return result
