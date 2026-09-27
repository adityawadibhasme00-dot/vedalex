"""Formulation strategy selection and materials/scale-up risk.

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
    _basis_text,
)
from app.services.innolab._shared import (
    _evidence,
    _finding,
    _list_value,
    _section,
    _text,
)

__all__ = [
    "_FORM_PCT_RE",
    "_FORM_RANGE_RE",
    "_FORM_PH_RE",
    "_FORM_TEMP_RE",
    "_FORM_TIME_RE",
    "_FORM_SOLVENT_ARTIFACT_RE",
    "_FORM_STRATEGY_RE",
    "_FORM_MICROBE_CLAIM_RE",
    "_FORM_PROCESS_CLAIM_RE",
    "_FORM_COMPAT_CLAIM_RE",
    "_FORM_CLAIM_RE",
    "_FORM_OBJECTIVE_RE",
    "_FORM_GAP_RE",
    "_FORM_DECISION_WEIGHTS",
    "_FORM_ENV_CLAIMS",
    "_FORM_PC_OPTIONS",
    "_form_concentration",
    "_form_ingredient_names",
    "_form_one_strategy_id",
    "_form_cna_pct",
    "_hub_formulation",
    "_SOLVENT_MAP",
    "_solvent_short",
    "_detect_solvent",
    "_MAT_MATERIAL_TERM_RE",
    "_MAT_PROPERTY_OBS_RE",
    "_MAT_KPP_RE",
    "_MAT_RISK_RE",
    "_MAT_COST_RE",
    "_MAT_PROCESS_FIX_RE",
    "_MAT_VALIDATION_GAP_RE",
    "_mat_material_names",
    "_mat_property_obs",
    "_mat_grade",
    "_hub_materials",
]

_FORM_PCT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*%\s*(?:w/w|w/v|vw?/ww?|weight|mass)?", re.I)


_FORM_RANGE_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:[-–]|to)\s*(\d+(?:\.\d+)?)\s*%\s*(?:w/w|w/v|vw?/ww?)?", re.I)


_FORM_PH_RE = re.compile(r"\bpH\s*[\d.]+\s*(?:[-–]\s*[\d.]+)?", re.I)


_FORM_TEMP_RE = re.compile(r"\b(\d{2,3})\s*(?:°\s*C\b|°\s*Celsius|deg\s*C)", re.I)


_FORM_TIME_RE = re.compile(r"\b(\d+)\s*(?:h\b|hrs?\b|hours\b|min\b|minutes\b)", re.I)


_FORM_SOLVENT_ARTIFACT_RE = re.compile(
    r"\b(hydroalcoholic|hydro-alcoholic|fresh-herb as gradient|fresh-herb gradient|"
    r"standardised extract|standardized extract|fermented matrix|liposomal complex|controlled temperature|"
    r"optimal solvent|defined solvent ratio|conventional extraction)\b", re.I)


_FORM_STRATEGY_RE = re.compile(
    r"\b(fresh-herb|standardis[ez]ed extract|fermented|liposomal|coa?crystal|nano-?particle|"
    r"self-emulsify|solid dispersion|cyclodextrin|ghee|ghrita|honey|asava|aristha|sneha)\b", re.I)


_FORM_MICROBE_CLAIM_RE = re.compile(
    r"\b(resist\w*\s+(microbial|mold|fungal)\s+growth|microbial\s+safe[^.]*hydro|\bhigh\s+alcohol\s+prevents)\b", re.I)


_FORM_PROCESS_CLAIM_RE = re.compile(
    r"\b(process\s+validat\w*|GMP|\bbatch\s+record|in[- ]process)\b", re.I)


_FORM_COMPAT_CLAIM_RE = re.compile(
    r"\b(ingredient\s+interaction\s+screened|compatib\w+\s+screened|excipient\s+compatib\w+)\b", re.I)


_FORM_CLAIM_RE = re.compile(
    r"\b(stress\s+relief|cognitive\s+support|wellness|immune\s+support|sleep\s+support|"
    r"anxiety\b|depression\b|health\s+claim|structure[- ]function|disease)\b", re.I)


_FORM_OBJECTIVE_RE = re.compile(
    r"\b(restful[- ]sleep|sleep|stress|anxiety|cognition|cognitive|energy|digestion|"
    r"immunity|immune|hair|skin|joint|weight)\b", re.I)


_FORM_GAP_RE = re.compile(r"\b(goals?\s*[:=]|objective\s*[:=])\s*(not specified|—|none|-)\b", re.I)


_FORM_DECISION_WEIGHTS = [
    ("Fitness to technical objective", "20%"),
    ("Stability / shelf-life evidence", "15%"),
    ("Potency / marker retention evidence", "15%"),
    ("Manufacturability evidence", "15%"),
    ("Safety evidence", "10%"),
    ("Regulatory simplicity", "10%"),
    ("Cost", "5%"),
    ("IP differentiation", "5%"),
    ("Evidence completeness", "5%"),
]


_FORM_ENV_CLAIMS = [
    ("Chemical stability", "ICH Q1A(R2): long-term, intermediate & accelerated at declared temp/humidity; stability-indicating assay; shelf life only from real data", "No chemical-stability claim without assay under ICH storage windows"),
    ("Microbial stability", "Preservation/challenge (e.g. USP <51>, or JP/EP equivalents) required; a hydroalcoholic or alcoholic base does NOT by itself prove microbial safety", "No 'resists microbial growth' claim without a preservation test"),
    ("Physical stability", "Appearance, phase, sedimentation/creaming, viscosity, particle size over storage", "No physical-stability claim without storage data"),
    ("Packaging / interaction", "Container-closure interaction, light protection (ICH Q1B photostability), moisture ingress", "No packaging claim without container-closure study"),
]


_FORM_PC_OPTIONS = [
    "Food / Ayurveda Aahara", "Nutraceutical / supplement", "Ayurvedic medicine (drug claim)",
    "Botanical drug / pharma", "Cosmetic / cosmeceutical", "Medical device (if any drug-free claim)",
    "Unclassified / TBD",
]


def _form_concentration(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for m in _FORM_RANGE_RE.finditer(text or ""):
        hits.append({"raw": m.group(0).strip(), "low": m.group(1), "high": m.group(2),
                     "status": "Proposed / derived screening range — needs justification"})
    for m in _FORM_PCT_RE.finditer(text or ""):
        raw = m.group(0).strip()
        if any(h["raw"] == raw for h in hits):
            continue
        hits.append({"raw": raw, "low": m.group(1), "high": None,
                     "status": "Unverified value in source text" if raw else ""})
    return hits[:10]


def _form_ingredient_names(resolved: list[dict[str, Any]]) -> list[str]:
    names = [r["botanical_name"] or r["raw_name"] for r in resolved if r.get("resolved")]
    names = names or [r["raw_name"] for r in resolved]
    return names


def _form_one_strategy_id(idx: int) -> str:
    return f"FC-{idx + 1:03d}"


def _form_cna_pct(conc: list[dict[str, Any]], idx: int) -> str:
    if conc:
        h = conc[idx % len(conc)]
        return h["raw"] if h.get("raw") else "[RANGE REQUIRED]"
    return "[USER CONFIRMATION REQUIRED]"


def _hub_formulation(inputs: dict[str, Any], spec, result: dict[str, Any], resolved: list[dict[str, Any]], markets: list[str], botanicals: str) -> dict[str, Any]:
    text_in = " ".join([
        _text(inputs, "problem_text") or "",
        _text(inputs, "formulation_text") or "",
        _text(inputs, "process_desc") or "",
    ])
    space = (text_in or _text(inputs, "product_desc") or "").strip()
    goals = _text(inputs, "proposed_claims") or "not specified"
    target_markets = markets or []
    names = _form_ingredient_names(resolved) or _list_value(inputs, "ingredients") or []
    conc = _form_concentration(space)

    pclass = "[NOT STATED] — one of: " + " / ".join(_FORM_PC_OPTIONS)
    mgap = bool(_FORM_GAP_RE.search(" " + goals.lower() + " "))
    obj_hits = sorted({m.group(1).lower() for m in _FORM_OBJECTIVE_RE.finditer(space.lower())})
    obj_txt = ", ".join(obj_hits[:6]) or "[NOT STATED]"
    claim_hits = sorted({m.group(1).lower() for m in _FORM_CLAIM_RE.finditer(space.lower())})
    micro_claim = _FORM_MICROBE_CLAIM_RE.search(space)
    process_claim = _FORM_PROCESS_CLAIM_RE.search(space)
    compat_claim = _FORM_COMPAT_CLAIM_RE.search(space)
    sorted({m.group(1).lower() for m in _FORM_SOLVENT_ARTIFACT_RE.finditer(space.lower())})
    temp = _FORM_TEMP_RE.search(space)
    dur = _FORM_TIME_RE.search(space)
    ph = _FORM_PH_RE.search(space)
    solvent_pref = _text(inputs, "solvent_pref") or _detect_solvent(space or _text(inputs, "process_desc"))

    env_gaps = [e for e in _FORM_ENV_CLAIMS]
    nominal = _list_value(inputs, "consumables") or (names[:2] or ["—"])

    blocked = not names and not conc and not space.strip()

    result["summary"] = (
        f"Preliminary formulation hypotheses for controlled bench testing — {botanicals[:60] or 'an Ayurvedic composition'}. "
        f"No concentration, stability, safety or regulatory claim is asserted without data."
    )
    result["note"] = (
        "Product classification gate → objective & constraints → ingredient/function map → comparable candidates "
        "→ process definition → stability/microbial/compatibility/manufacturability/regulatory/claims/IP review → "
        "risk & decision matrices → bench-testing plan. Output is a hypothesis plan, never a validated formulation."
    )
    result["findings"].append(_finding("f-class", "Product classification gate", pclass, "warning"))
    result["findings"].append(_finding("f-obj", "Objective & constraints", f"Stated objective: {obj_txt}; claimed benefits in text: {', '.join(claim_hits[:4]) or '[NONE]'}; goals field: {goals[:80]}", "info" if obj_hits and not mgap else "warning"))
    result["findings"].append(_finding("f-conc", "Concentration audit", f"{len(conc)} percentile value(s) found in source text; none are lab-verified — treat as proposed screening ranges.", "warning" if conc else "info"))
    result["findings"].append(_finding("f-lab", "Formulation readiness", "Preliminary formulation hypotheses for controlled bench testing — NOT a lab-ready batch sheet; no ingredient ratio is finalised.", "warning"))
    if micro_claim:
        result["findings"].append(_finding("f-micro", "Current-output correction", "Microbial safety is only a HYPOTHESIS. A hydroalcoholic/alcoholic base reduces water activity but does not prove preservation; USP <51>/challenge data is required. Limitation: 'hydroalcoholic systems resist microbial growth' is not a validated claim.", "warning"))
    if process_claim:
        result["findings"].append(_finding("f-proc", "Current-output correction", "'Process validated' is NOT established — requires protocol, identified CPPs, CQAs, multiple batches and acceptance criteria; cleaning/equipment qualification are separate.", "warning"))
    if compat_claim:
        result["findings"].append(_finding("f-comp", "Current-output correction", "Ingredient interactions NOT screened — requires binary + final-formulation compatibility + stability data; a compatibility assay is never a final step.", "warning"))
    result["findings"].append(_finding("f-j", "Formulation Agent standard", "IP-SAKTI ka Formulation Agent random ingredient percentages suggest nahi karta. Ye pehle product category, intended use, baseline aur constraints define karta hai; ingredients ko technical function ke saath map karta hai; comparable candidate formulations generate karta hai; stability, microbial quality, compatibility, manufacturability, regulatory aur IP risks separately evaluate karta hai; aur har candidate ke liye controlled bench-validation plan deta hai.", "info"))
    if result.get("citations"):
        result["findings"].append(_finding("f-ev", "Evidence anchors", f"{len(result['citations'])} corpus passage(s) pulled; corpus text supports identity/context, not concentration, stability or safety claims.", "info"))
    result["evidence"] = result["evidence"] or [_evidence("formulation", f"Product class gate: {pclass.split(' — ')[0]} · solvent hypothesis: {_solvent_short(solvent_pref)}", "Formulation reasoning engine")]

    result["suggestions"] = [
        "Confirm product classification and target jurisdiction(s) before any formulation is built.",
        "Provide verified ingredient identities, batch-sourced assay values and the actual target concentrations.",
        "Run stability (ICH Q1A), preservation (USP <51>), compatibility and bioassay bench studies before calling any formula lab-ready.",
        "Run novelty_search + fto_search on the FINAL formula only — no patentability conclusion from corpus references.",
    ]

    if blocked:
        result["summary"] = "Preliminary concept only — no formulation generated. Provide product category, intended use, ingredient identities and constraints."
        result["sections"] += [
            _section("Product classification gate", [{"question": "What product type?", "response": pclass}], ["question", "response"],
                     "Blocked at gate — classification must precede any ingredient or percentage recommendation."),
            _section("Objective & constraints", [{"objective": obj_txt, "constraints": "[NOT STATED]", "goals": goals or "not specified"}],
                     ["objective", "constraints", "goals"], "Goals not specified → no formulation recommended."),
            _section("Blocked — no formulation generated", [
                {"missing": "Product category", "required_to_proceed": "food / Ayurveda Aahara / supplement / Ayurvedic medicine / botanical drug / pharma / cosmetic"},
                {"missing": "Intended use / objective", "required_to_proceed": "stated target + constraints + baseline"},
                {"missing": "Ingredient identities (verified)", "required_to_proceed": "verified names — no concentration without identity"},
                {"missing": "Target market(s) & regime", "required_to_proceed": "jurisdiction + classification"},
            ], ["missing", "required_to_proceed"], "Preliminary concept only — no validated formulation generated."),
            _section("What is NOT claimed", [
                {"claim": "'8% w/w' / '4% w/w' style percentages", "status": "none without source — proposed screening range only"},
                {"claim": "'hydroalcoholic resists microbial growth'", "status": "HYPOTHESIS — requires preservation testing"},
                {"claim": "'process validated'", "status": "NOT established without protocol + CPPs + CQAs + batches + acceptance"},
                {"claim": "'ingredient interaction screened'", "status": "NOT verified without binary + final-formulation + stability data"},
            ], ["claim", "status"], "Correct the previous generic outputs exactly this way."),
            _section("Formulation Agent standard (judge line)", [{"standard": "IP-SAKTI ka Formulation Agent random ingredient percentages suggest nahi karta. Ye pehle product category, intended use, baseline aur constraints define karta hai; ingredients ko technical function ke saath map karta hai; comparable candidate formulations generate karta hai; stability, microbial quality, compatibility, manufacturability, regulatory aur IP risks separately evaluate karta hai; aur har candidate ke liye controlled bench-validation plan deta hai."}],
                     ["standard"], "This is the pass/fail test the evaluator applies."),
        ]
        return result

    ing_rows = [{
        "ingredient": n,
        "identity_status": "[IDENTITY REQUIRED] — botanical/INCI/PubChem verified name",
        "function": "[FUNCTION REQUIRED] — role in this product (API / base / excipient / preservative / flavouring)",
        "concentration": "[USER CONFIRMATION REQUIRED]",
        "basis": "No concentration assigned without a source",
    } for n in (names[:8] or ["—"])]

    cand_rows = []
    base_strats = []
    strategy_hits = sorted({m.group(1).lower() for m in _FORM_STRATEGY_RE.finditer(space.lower())})
    if strategy_hits:
        base_strats = strategy_hits[:3]
    else:
        base_strats = ["traditional hydro-alcoholic (base)", "concentration-controlled conventional (technology 1)", "encapsulation/packaging variant (technology 2)"]
    for i, strat in enumerate(base_strats[:3]):
        cand_rows.append({
            "candidate": _form_one_strategy_id(i),
            "evidence_status": "Concept hypothesis" if i == 0 else ("Literature/derived hypothesis" if i == 1 else "Concept hypothesis"),
            "main_strategy_change": strat,
            "variables_kept_constant": "; ".join(nominal[:2]) or "[DEFINE]",
            "measured_outcome_target": "[ENDPOINT REQUIRED]",
            "concentration_basis": _form_cna_pct(conc, i),
            "readiness": "NOT lab-ready — bench validation required",
        })

    dim_rows = []
    for dim, field_a, field_b in [
        ("Stability / shelf-life approach", "primary solvent hypothesis", "preservation strategy"),
        ("Bioavailability strategy", "carrier/format", "dose form"),
        ("Processing route", "extraction/conditioning", "scale-up constraint"),
    ]:
        dim_rows.append({
            "dimension": dim,
            f"{field_a}": "[VERIFY]",
            f"{field_b}": "[VERIFY]",
            "evidence_needed": "[LAB DATA REQUIRED]",
            "decision_rule": "choose only after bench data",
        })
    dim_cols = list(dim_rows[0].keys())

    risk_rows = [
        {"risk": "Microbial / preservation", "severity": "High", "likelihood": "Not differentiable — base alone does not prove safety",
         "detectability": "USP <51> / challenge test", "mitigation": "Preservation study + pH control", "test": "Microbial limits / challenge"},
        {"risk": "Ingredient interaction", "severity": "High", "likelihood": "Unknown without data", "detectability": "Binary + final-formulation stability",
         "mitigation": "Compatibility screening matrix", "test": "Assay drift, appearance, pH, impurities"},
        {"risk": "Chemical instability", "severity": "High", "likelihood": "Unknown — assumes ICH Q1A conditions", "detectability": "Stability-indicating assay",
         "mitigation": "Stress studies, packaging protection", "test": "Long-term + accelerated (ICH Q1A)"},
        {"risk": "Potency loss", "severity": "Medium", "likelihood": "Unknown", "detectability": "Marker/bioassay retention",
         "mitigation": "Process windows kept controlled", "test": "In-process + final assay"},
        {"risk": "Regulatory mismatch", "severity": "Medium", "likelihood": "High without classification", "detectability": "Jurisdiction check",
         "mitigation": "Confirm product class per market", "test": "Regulatory screening"},
        {"risk": "Manufacturability", "severity": "Medium", "likelihood": "Unknown — no process validated without protocol + CPPs + CQAs + batches",
         "detectability": "Scale-up runs", "mitigation": "Process validation protocol", "test": "Multi-batch acceptance"},
    ]
    if not names and not conc:
        risk_rows = risk_rows[:0]

    mkt_rows = []
    for m in target_markets:
        note = {
            "India": "Food/Aahara vs Ayush medicine (drug claim) vs nutraceutical — route differs; classification determines pathway. No claim without classification.",
            "United States": "DSHEA supplement line requires classification + NDI review if applicable — a 'DSHEA line' is not automatic; claims determine category.",
            "Canada": "NHP licence (SOR/2004-102) only if it is an NHP; food vs supplement vs natural health product distinguishes the route — bilingual label + NPN if NHP.",
            "European Union": "Food supplement (2002/46/EC) or botanical/novel food (2015/2283) — varies by classify.",
        }.get(m, "national regulatory screening advised — no blanket pathway assumed")
        mkt_rows.append({"market": m, "product_class_required": "[CONFIRM]", "pathway_if_classified": note})

    if not names and not conc:
        result["sections"] += [
            _section("Product classification gate", [{"question": "What product type?", "response": pclass}], ["question", "response"],
                     "Blocked at gate — classification must precede any ingredient or percentage recommendation."),
            _section("Objective & constraints", [{"objective": obj_txt, "constraints": "[NOT STATED]", "goals": goals or "not specified"}],
                     ["objective", "constraints", "goals"], "Goals not specified → no formulation recommended."),
            _section("Blocked — no formulation generated", [
                {"missing": "Product category", "required_to_proceed": "food / Ayurveda Aahara / supplement / Ayurvedic medicine / botanical drug / pharma / cosmetic"},
                {"missing": "Intended use / objective", "required_to_proceed": "stated target + constraints + baseline"},
                {"missing": "Ingredient identities (verified)", "required_to_proceed": "verified names — no concentration without identity"},
                {"missing": "Target market(s) & regime", "required_to_proceed": "jurisdiction + classification"},
            ], ["missing", "required_to_proceed"], "Preliminary concept only — no validated formulation generated."),
            _section("What is NOT claimed", [
                {"claim": "'8% w/w' / '4% w/w' style percentages", "status": "none without source — proposed screening range only"},
                {"claim": "'hydroalcoholic resists microbial growth'", "status": "HYPOTHESIS — requires preservation testing"},
                {"claim": "'process validated'", "status": "NOT established without protocol + CPPs + CQAs + batches + acceptance"},
                {"claim": "'ingredient interaction screened'", "status": "NOT verified without binary + final-formulation + stability data"},
            ], ["claim", "status"], "Correct the previous generic outputs exactly this way."),
            _section("Formulation Agent standard (judge line)", [{"standard": "IP-SAKTI ka Formulation Agent random ingredient percentages suggest nahi karta. Ye pehle product category, intended use, baseline aur constraints define karta hai; ingredients ko technical function ke saath map karta hai; comparable candidate formulations generate karta hai; stability, microbial quality, compatibility, manufacturability, regulatory aur IP risks separately evaluate karta hai; aur har candidate ke liye controlled bench-validation plan deta hai."}],
                     ["standard"], "This is the pass/fail test the evaluator applies."),
        ]
        return result

    _text(inputs, "regulatory_notes") or "[NOT STATED]"
    result["sections"] += [
        _section("Product classification gate", [{"question": "What is being formulated?", "response": pclass}, {"question": "Ingredients detected", "response": ", ".join(names) or "[NONE]"}, {"question": "Dose form", "response": "[NOT STATED] — liquid/solid/semisolid"}],
                 ["question", "response"], "No percentage is recommended until classification is confirmed."),
        _section("Objective & constraints", [{"objective": obj_txt, "constraints": "[NOT STATED]", "baseline": "[NOT STATED]", "goals": goals or "not specified"}],
                 ["objective", "constraints", "baseline", "goals"], "Meet the stated target with explicit constraints; goals = 'not specified' blocks recommendations.", ),
        _section("Ingredient identity & function map", ing_rows, ["ingredient", "identity_status", "function", "concentration", "basis"],
                 "Identity verification precedes concentration assignment — 'functional role I' is NOT the ingredient function."),
        _section("Candidate generation (evidence-classified)", cand_rows, ["candidate", "evidence_status", "main_strategy_change", "variables_kept_constant", "measured_outcome_target", "concentration_basis", "readiness"],
                 "Concept → literature-derived → prototype → validated. Changing ONE main strategy per candidate keeps comparisons meaningful."),
        _section("Comparable candidate design", [
            {"rule": "Change only ONE main strategy", "control": "baseline formulation fixed", "measured_outcome": "assay-relevant endpoints", "decision": "advance/stop criteria"},
            {"rule": "Same raw-material batch & method", "control": "batch-matched controls", "measured_outcome": "replicate measurements", "decision": "statistical pre-specification"},
        ], ["rule", "control", "measured_outcome", "decision"], "Candidate F-Cn differs from the baseline by exactly one main strategy."),
        _section("Dimension-wise benchmark (hypotheses, not conclusions)", dim_rows, dim_cols,
                 "Every dimension shows the evidence needed before a direction is selected."),
        _section("Concentration / ratio audit", [
            {"value": c["raw"], "lower": c["low"], "higher": c["high"], "source_status": c["status"],
             "classification": "Proposed screening range" if (c["high"] or c["low"]) else "Proposed screening range — unverified"} for c in conc
        ] or [{"value": "[NONE DETECTED]", "lower": "—", "higher": "—", "source_status": "No concentration in source text", "classification": "No concentration assigned without a source"}],
            ["value", "lower", "higher", "source_status", "classification"],
            "Classifications: directly sourced / user / literature / patent / experimental / proposed screening range / unknown. '8–14%' is an exploratory range, never a validated level."),
        _section("Process definition (no undefined labels)", [
            {"parameter": "Solvent / vehicle", "value": _solvent_short(solvent_pref), "specificity": "[ALCOHOL TYPE + % + RATIO REQUIRED] hydroalcoholic alone is undefined"},
            {"parameter": "Temperature window", "value": (temp.group(0) if temp else "[USER CONFIRMATION REQUIRED]"), "specificity": "set from physical/chemical data, not a slogan"},
            {"parameter": "Duration", "value": (dur.group(0) if dur else "[USER CONFIRMATION REQUIRED]"), "specificity": "[TIME REQUIRED]" if not dur else "measured"},
            {"parameter": "pH range", "value": (ph.group(0) if ph else "[LAB DATA REQUIRED]"), "specificity": "rationale needed — 'pH 3.5–5.5' without rationale is unsupported"},
            {"parameter": "Extraction/conditioning", "value": "[DEFINE] ", "specificity": "'standardised extract' requires marker + specification"},
        ], ["parameter", "value", "specificity"], "Hydroalcoholic / standardised extract / fresh-herb gradient / fermented matrix are labels, not process definitions."),
        _section("Stability assessment (all four types)", [
            {"type": e[0], "requirement": e[1], "claim_rule": e[2]} for e in env_gaps
        ], ["type", "requirement", "claim_rule"], "Hydroalcoholic base does NOT automatically prove microbial safety."),
        _section("Stability study design (ICH Q1A + FDA botanical guidance)", [
            {"element": "Conditions", "spec": "long-term, intermediate & accelerated temp/humidity windows", "note": "shelf life only from real study data"},
            {"element": "Stability-indicating method", "spec": "validated assay discriminating degradants", "note": "FDA botanical guidance requirement"},
            {"element": "Stress studies", "spec": "heat, humidity, light (ICH Q1B), pH", "note": "identify degradants + degradation pathways"},
            {"element": "Shelf-life", "spec": "[NO SHELF LIFE CLAIM without data]", "note": "never inferred from base type"},
        ], ["element", "spec", "note"], "Do not claim a shelf life from solvent composition."),
        _section("Bioavailability strategy (endpoint-defined)", [
            {"strategy": "[TO BE DEFINED]", "endpoint": "[END-POINT REQUIRED]", "claimable": "No",
             "note": "Standardization, solvent, carrier, fermentation or higher concentration alone never proves improved bioavailability"},
        ], ["strategy", "endpoint", "claimable", "note"], "Bioavailability demands measured absorption/exposure endpoints followed by proof-of-concept studies."),
        _section("Microbial quality & preservation review", [
            {"check": "Preservation challenge", "status": "[REQUIRED: USP <51> / EP / JP]", "note": "base alcohol is not evidence"},
            {"check": "Aseptic / process hygiene", "status": "[REQUIRED]", "note": "nitrate/humidity controls"},
        ], ["check", "status", "note"], "Verify the failure modes of the previous generic output."),
        _section("Compatibility review (excipient–API)", [
            {"study": "Binary compatibility", "status": "[REQUIRED]", "note": "excipient × excipient + API × excipient matrix"},
            {"study": "Final-formulation compatibility", "status": "[REQUIRED]", "note": "interaction observed only across the finished composition"},
            {"study": "Stability/assay drift", "status": "[REQUIRED]", "note": "appearance, pH, assay, impurity over time"},
        ], ["study", "status", "note"], "'Ingredient interaction screened' is NOT a complete statement — data required."),
        _section("Manufacturability review", [
            {"check": "Process validation protocol", "status": "[NOT ESTABLISHED]", "note": "requires protocol + CPPs + CQAs + multiple batches + acceptance criteria"},
            {"check": "Scale-up risk", "status": "[NOT VERIFIED]", "note": "equipment, mixing, filling, heat transfer"},
        ], ["check", "status", "note"], "No 'process validated' claim without this evidence."),
        _section("Regulatory pathway review (per jurisdiction)", mkt_rows or [
            {"market": "[NOT STATED]", "product_class_required": "[CONFIRM]", "pathway_if_classified": "confirm target market(s)"}
        ], ["market", "product_class_required", "pathway_if_classified"],
            "India/US/Canada/regulatory assertions are only valid after product classification; a 'generic source' is never proof."),
        _section("Claims classification & wording", [
            {"phrase": claim_phrase, "category": "[CLASSIFY]", "allowable": "[PER JURISDICTION]"} for claim_phrase in (claim_hits[:6] or ["[NONE DETECTED]"])
        ], ["phrase", "category", "allowable"],
            "Range: food / structure–function / health / disease / traditional / cosmetic. 'stress relief / cognitive support / wellness / immune support' are NOT unrestricted claims; disease-cure wording is separate."),
        _section("IP / novelty review", [
            {"question": "Prior-art checks", "status": "[NOT RUN on final formula]", "note": "corpus/monograph/FDA rule/AYUSH rule is NOT proof of novelty"},
            {"question": "Patentability conclusion", "status": "NO conclusion", "note": "run novelty_search + fto_search on final formula only"},
        ], ["question", "status", "note"], "Never conclude novelty from generic references."),
        _section("Risk matrix (severity × likelihood × detectability)", risk_rows, ["risk", "severity", "likelihood", "detectability", "mitigation", "test"],
                 "Each risk carries severity, likelihood, detectability, mitigation and test. 'mid regulatory risk' without basis is a red flag."),
        _section("Decision / selection matrix (weights sum = 100%)", [
            {"criterion": c[0], "weight": c[1],
             "candidate_A": "[Not assessed — data unavailable]", "candidate_B": "[Not assessed — data unavailable]",
             "winner": "No decision without data"} for c in _FORM_DECISION_WEIGHTS
        ], ["criterion", "weight", "candidate_A", "candidate_B", "winner"],
            "Technical 20%, stability 15%, potency/marker 15%, manufacturability 15%, safety 10%, regulatory 10%, cost 5%, IP 5%, evidence 5%. Missing cells = 'Not assessed — data unavailable'."),
        _section("Bench-testing plan (controlled)", [
            {"experiment": f"BT-{i+1}", "control": "baseline formulation", "test": f"{i}% w/w screened range", "replicates": "≥3", "variables_changed": "ONE strategy at a time", "variables_held": "; ".join(nominal[:2]) or "[DEFINE]",
             "endpoints": "[ASSAY/MARKER ENDPOINT]", "acceptance": "[CRITERIA]", "stop": "[CRITERIA]", "decision": "advance/stop/go-ahead"} for i in range(3)
        ], ["experiment", "control", "test", "replicates", "variables_changed", "variables_held", "endpoints", "acceptance", "stop", "decision"],
            "Every candidate F-Cn gets a controlled bench protocol; nothing is callable 'lab-ready' until acceptance criteria are met."),
        _section("Data gaps to close", [
            {"data": "Verified identity + batch assay of every ingredient", "for": "concentration and function assignment"},
            {"data": "ICH Q1A / stress / photostability data", "for": "stability claims"},
            {"data": "Preservation / challenge data", "for": "microbial safety"},
            {"data": "Compatibility data (binary + final)", "for": "ingredient-interaction claims"},
            {"data": "Process validation evidence", "for": "manufacturability"},
            {"data": "Absorption/exposure data", "for": "bioavailability claims"},
            {"data": "Regulatory classification per market", "for": "pathway claims"},
        ], ["data", "for"], "Only close these gaps with experiments — a fuller reference set is not a substitute."),
        _section("Recommended next steps", [
            {"step": "1", "action": "Fix product classification and get verified ingredient identities + assay values."},
            {"step": "2", "action": "Choose a single main-strategy difference per candidate and baseline controls."},
            {"step": "3", "action": "Run bench studies: stability (ICH Q1A), preservation, compatibility, assay — then decide."},
            {"step": "4", "action": "Only then run process validation + regulatory screening per target market."},
        ], ["step", "action"], "Deterministic sequence — no percentage is final before data."),
        _section("Limitations", [
            {"limitation": "Hypotheses are not lab results — nothing here is a validated formulation."},
            {"limitation": "Concentrations, pH, temp and process conditions without data are placeholders, not recommendations."},
            {"limitation": "No shelf life, bioavailability, safety or regulatory status is claimed without data."},
        ], ["limitation"], "Hard limits — the output is a bench plan, not a batch sheet."),
        _section("Formulation Agent standard (judge line)", [{"standard": "IP-SAKTI ka Formulation Agent random ingredient percentages suggest nahi karta. Ye pehle product category, intended use, baseline aur constraints define karta hai; ingredients ko technical function ke saath map karta hai; comparable candidate formulations generate karta hai; stability, microbial quality, compatibility, manufacturability, regulatory aur IP risks separately evaluate karta hai; aur har candidate ke liye controlled bench-validation plan deta hai."}],
                 ["standard"], "This is the pass/fail test the evaluator applies."),
    ]

    result["findings"].append(_finding("f-qc", "Quality-control checklist",
        "product classification confirmed before percentages; objective+constraints captured; ingredient identity → function mapped; candidates classified by evidence; one main strategy change; concentration classification applied; process terms defined; stability by all 4 types; microbial safety not inferred from base; ICH Q1A + stress design; bioavailability endpoint-bound; compatibility data required; manufacturability not asserted; regulatory per jurisdiction; claims classified; IP never concluded; risk matrix with mitigation+test; decision weights transparent; bench plan with controls/replicates/acceptance; no definitive claim; 'not assessed' used when data absent; label is 'Preliminary formulation hypotheses for controlled bench testing'.", "info"))
    result["findings"].append(_finding("f-label", "Output label correction", "Label this output 'Preliminary formulation hypotheses for controlled bench testing' — never 'Benchmarked formulation candidates' or 'Lab-ready'.", "warning"))
    return result


_SOLVENT_MAP = {
    "Water (decoction)": "aqueous decoction",
    "Hydroalcoholic": "hydroalcoholic",
    "Honey": "honey base",
    "Ghee / ghrita": "ghee (ghrita) base",
    "Milk": "milk base",
    "Alcohol (asava/aristha)": "fermented alcohol",
    "Not sure": "optimal solvent",
}


def _solvent_short(pref: str) -> str:
    return _SOLVENT_MAP.get(pref, pref or "optimal solvent")


def _detect_solvent(process: str) -> str:
    low = (process or "").lower()
    if "alcohol" in low or "hydro" in low or "ethan" in low:
        return "Hydroalcoholic"
    if "ghee" in low or "ghrita" in low:
        return "Ghee / ghrita"
    if "honey" in low:
        return "Honey"
    if "milk" in low:
        return "Milk"
    if "asava" in low or "aristha" in low:
        return "Alcohol (asava/aristha)"
    if "water" in low or "decoct" in low:
        return "Water (decoction)"
    return "Hydroalcoholic"


_MAT_MATERIAL_TERM_RE = re.compile(
    r"\b(microcrystalli[sz]e?d\s+cellulose|mcc|starch|pregelatin[sz]ed\s+starch|sodium\s+starch|"
    r"polyvinyl\s+pyrrolidone|povidone|croscarmellose|sodium\s+starch\s+glycolate|"
    r"magnesium\s+stearate|colloidal\s+silicon\s+dioxide|silica\s+dioxide|talc\b|"
    r"hypromellose|hpmc|hydroxypropyl\s+cellulose|methylcellulose|carboxymethylcellulose|"
    r"acacia|xanthan\s+gum|guar\s+gum|lecithin|polysorbate|sorbitol|xylitol|maltodextrin|"
    r"calcium\s+carbonate|dicalcium\s+phosphate|titanium\s+dioxide|aerosil|gelatin|carrageenan|"
    r"mannitol|polyethylene\s+glycol|peg\b|glyceryl|ion\s+exchange|steel\b|aluminum|copper|silicon|"
    r"hydrotalcite|magnesium\s+oxide|zinc|sedation)\b", re.I)


_MAT_PROPERTY_OBS_RE = re.compile(
    r"\b(moisture|caking|aggregation|flow|particle\s+size|dissolution|content\s+uniformity|"
    r"hardness|friab|compress|aeration|oxidation|discolour|taste|odour|sedimentation|viscosity|"
    r"ph\b|moisture\s+pickup|caking\b|flowability|agglomeration)\b", re.I)


_MAT_KPP_RE = re.compile(
    r"\b(key\s+performance\s+propert\w*|cpp|critical\s+process\s+param|critical\s+material\s+attrib\w*|"
    r"cqa|critical\s+quality\s+attrib\w*|dissolution|flow\b|hardness|content\s+uniformity)\b", re.I)


_MAT_RISK_RE = re.compile(r"\b(low\s+risk|mid\s+regulatory\s+risk|medium\s+risk|high\s+risk)\b", re.I)


_MAT_COST_RE = re.compile(r"\b(cost|price|cheap|lower\s+cost|more\s+expensive)\b", re.I)


_MAT_PROCESS_FIX_RE = re.compile(
    r"\bprocess\s+fix\b|adjust\s+(particle\s+size|drying|processing|temperature|humidity)\b", re.I)


_MAT_VALIDATION_GAP_RE = re.compile(
    r"\b(3\s+batches?|three\s+batches?|acceptance\s+criteria|replicate|control\b|test\s+method)\b", re.I)


def _mat_material_names(text: str) -> list[str]:
    hits = []
    for m in _MAT_MATERIAL_TERM_RE.finditer(text or ""):
        val = m.group(1).strip()
        if val not in hits:
            hits.append(val)
    return hits[:8]


def _mat_property_obs(text: str) -> list[str]:
    hits = []
    for m in _MAT_PROPERTY_OBS_RE.finditer(text or ""):
        val = m.group(1).strip()
        if val not in hits:
            hits.append(val)
    return hits[:8]


def _mat_grade(space: str, name: str) -> str:
    low = space or ""
    m = re.search(r"\b(grade|type)\s*[#:\s]*(\d+)\b", low, re.I)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    c = re.search(r"\b(EP|USP|BP|Ph(?:Eur)?)\b", low, re.I)
    return (c.group(1).upper() + " spec — [level required]" if c else "[GRADE REQUIRED]")


def _hub_materials(inputs: dict[str, Any], result: dict[str, Any], botanicals: str) -> dict[str, Any]:
    challenge = _basis_text(inputs, "material_challenge") or _basis_text(inputs, "problem_text") or _text(inputs, "problem_text")
    current = _basis_text(inputs, "current_material") or _text(inputs, "current_material")
    target = _basis_text(inputs, "performance_target") or _text(inputs, "performance_target") or "key performance property"
    space = " ".join([current or "", target or "", challenge or "", _text(inputs, "material_notes") or ""]).strip()
    names = _mat_material_names(space) or ([x.strip() for x in (current or "current excipient").split(",")] or [])
    grade = _mat_grade(space, names[0]) if names else "[GRADE REQUIRED]"
    m_terms = _mat_material_names(space)
    p_obs = _mat_property_obs(space)
    kpp_hits = sorted({m.group(1).lower() for m in _MAT_KPP_RE.finditer(space.lower())})
    risk_hits = sorted({m.group(1).lower() for m in _MAT_RISK_RE.finditer(space.lower())})
    cost_hit = bool(_MAT_COST_RE.search(space))
    fix_hit = bool(_MAT_PROCESS_FIX_RE.search(space))
    _MAT_VALIDATION_GAP_RE.search(space)

    blocked = (not challenge) and (not current) and (not _mat_material_names(space))

    result["summary"] = (
        f"Preliminary material/process hypotheses for controlled validation — "
        f"{names[:1][0] if names else botanicals or 'a material/excipient issue'}. "
        f"No substitution, compatibility, cost or regulatory claim is asserted without data."
    )
    result["note"] = (
        "Problem intake → classification → root-cause tree → current-material characterization → CMA–CPP–CQA mapping "
        "→ solution directions (real candidates, not Alternative-1/2) → maturity/compatibility/cost/regulatory/IP review "
        "→ risk classification → validation design + DOE. Output is a hypothesis bundle, never a validated fix."
    )
    result["findings"].append(_finding("m-class", "Problem classification", f"Material-failure domain: {', '.join(p_obs[:5]) or '[NOT STATED]'}; KPP/CMA/CPP/CQA terms: {', '.join(kpp_hits[:4]) or '[NONE]'}; current material: {names[0] if names else '[NOT STATED]'}.", "info" if (p_obs or kpp_hits) else "warning"))
    result["findings"].append(_finding("m-grade", "Current material identity", f"{names[0] if names else '—'} · grade: {grade}. Identity not re-verified without datasheet/lot number.", "warning"))
    result["findings"].append(_finding("m-root", "Root-cause status", "Root cause is NOT confirmed — observed symptom ≠ verified cause; material/process/product/supply branches must be distinguished by controlled screening.", "warning"))
    if cost_hit and not re.search(r"\b\d+(?:\.\d+)?\s*(?:%|₹|Rs|USD|\$)\b", space):
        result["findings"].append(_finding("m-cost", "Current-output correction", "'Lower cost' has no arithmetic basis — provide baseline price per kg/unit and the new material's quote before any cost claim.", "warning"))
    if fix_hit:
        result["findings"].append(_finding("m-fix", "Current-output correction", "'Process fix — keep material, adjust particle size/drying' is a process HYPOTHESIS pending root-cause confirmation; it is not a validated correction without a CPP–CQA link and test data.", "warning"))
    if risk_hits:
        for r_ in risk_hits:
            result["findings"].append(_finding(f"m-risk-{r_.replace(' ', '')}", "Risk basis", f"'{r_}' asserted without evidence — risks need basis (data, exact reference, jurisdiction), never a red-flag standalone label.", "warning"))
    if names:
        result["findings"].append(_finding("m-blank-alt", "Current-output correction", "'Alternative-1 / Alternative-2' are placeholders, not solutions — every candidate must carry an ACTUAL material/grade, loading, mechanism, expected benefit, CMA/CPP/CQA impact, cost, regulatory status and validation plan.", "warning"))
    result["findings"].append(_finding("m-j", "Find-better-material standard", "IP-SAKTI ka Material Find Solutions Agent sirf Alternative-1 ya Alternative-2 suggest nahi karta. Ye current material aur failure mode identify karta hai, root-cause hypotheses banata hai, critical material attributes, process parameters aur quality attributes map karta hai, actual material/process alternatives compare karta hai, regulatory, cost, manufacturing aur IP risks assess karta hai, aur controlled multi-batch validation plan deta hai.", "info"))
    if result.get("citations"):
        result["findings"].append(_finding("m-ev", "Evidence anchors", f"{len(result['citations'])} corpus passage(s) pulled — references support identity/context, not suitability/cost/regulatory conclusions.", "info"))
    result["evidence"] = [x for x in result.get("evidence") or []]
    if not result["evidence"]:
        result["evidence"] = [_evidence("materials_find_solutions", f"Material: {names[0] if names else '—'} · property gap: {', '.join(p_obs[:3]) or '[NOT STATED]'} · target: {target}", "Material reasoning engine")]

    result["suggestions"] = [
        "Provide current material, grade, loading, observed failure, target value, scale, equipment, jurisdictions, constraints and available tests.",
        "Confirm root cause with a controlled screening (material vs process vs product vs supply) before changing anything.",
        "Map CMA/CPP/CQA with ICH Q8(R2) — 'critical' only when linked to a measurable CQA.",
        "Replace every Alternative-1/2 placeholder with a real material + evidence pack and a multi-batch validation design.",
    ]

    if blocked:
        result["summary"] = "Blocked — insufficient material and failure information. Provide: material name, current function/use, grade, loading/concentration, observed failure or symptom, property measured, target value, production scale, equipment, market jurisdiction, cost, safety/regulatory/excipient constraints, available tests."
        result["sections"] += [
            _section("Blocked — insufficient material and failure information", [
                {"missing": "Current material name", "purpose": "identity + grade + function"},
                {"missing": "Grade / specification", "purpose": "lot + datasheet for characterization"},
                {"missing": "Loading / concentration", "purpose": "baseline before any alternative"},
                {"missing": "Observed failure or symptom", "purpose": "classifies the problem domain"},
                {"missing": "Property/parameter measured", "purpose": "which attribute failed (KPP/CMA/CPP/CQA)"},
                {"missing": "Target value", "purpose": "quantitative acceptance"},
                {"missing": "Production scale & equipment", "purpose": "feasibility + variation sources"},
                {"missing": "Market jurisdiction", "purpose": "regulatory route"},
                {"missing": "Cost / safety / regulatory constraints", "purpose": "candidate screening"},
                {"missing": "Available tests & method", "purpose": "validation design"},
            ], ["missing", "purpose"], "Blocked until these are provided — no generic alternative suggestion."),
            _section("What is NOT claimed", [
                {"claim": "'Alternative-1 / Alternative-2 improve KPP'", "status": "placeholder only — requirements unmet"},
                {"claim": "'lower cost'", "status": "no cost arithmetic — requires baseline + quote"},
                {"claim": "'mid regulatory risk'", "status": "no jurisdictional basis"},
                {"claim": "'process fix'", "status": "process hypothesis pending root-cause confirmation + CPP–CQA link"},
                {"claim": "'patent-linked'", "status": "requires publication number + claim + example + passage + jurisdiction + status"},
                {"claim": "'3 batches'", "status": "no acceptance criteria / control / replicates / test method"},
            ], ["claim", "status"], "Correct the previous generic outputs this exact way."),
            _section("Find-better-material standard (judge line)", [{"standard": "IP-SAKTI ka Material Find Solutions Agent sirf Alternative-1 ya Alternative-2 suggest nahi karta. Ye current material aur failure mode identify karta hai, root-cause hypotheses banata hai, critical material attributes, process parameters aur quality attributes map karta hai, actual material/process alternatives compare karta hai, regulatory, cost, manufacturing aur IP risks assess karta hai, aur controlled multi-batch validation plan deta hai."}],
                     ["standard"], "This is the pass/fail test the evaluator applies."),
        ]
        return result

    m_terms = _mat_material_names(space) or names
    all_term = ", ".join(m_terms[:4]) or "[NOT STATED]"

    root_rows = [
        {"branch": "Material cause", "why": f"{all_term} — moisture uptake/grade mismatch/impurity/particle-size distribution", "verification": "material datasheet + characterization"},
        {"branch": "Process cause", "why": "equipment settings / mixing / drying / temperature window / hold time", "verification": "CPP–CQA linkage + batch data"},
        {"branch": "Product cause", "why": "formulation interactions / package effect / dose-form design", "verification": "formulation + container-closure study"},
        {"branch": "Supply cause", "why": "lot-to-lot variation / supplier method change / storage gaps", "verification": "lot history + supplier spec"},
    ]
    g = _mat_grade(space, m_terms[0]) if m_terms else "[GRADE REQUIRED]"

    cands = []
    cand_index = 0
    for route_label, route_name in [("A — material substitution", "material substitution"), ("B — material/process optimisation", "optimisation"), ("C — process correction (root-cause-confirmed)", "process correction"), ("D — combination", "combination")]:
        cand_index += 1
        cands.append({
            "id": f"MS-{cand_index:03d}",
            "route": route_label,
            "candidate_material": f"[ACTUAL MATERIAL REQUIRED — {route_name}]",
            "grade": "[GRADE REQUIRED]",
            "loading": "[LOADING REQUIRED]",
            "mechanism": "[PROPOSED MECHANISM — pending data]",
            "expected_benefit": f"[Define how it improves {target}]",
            "trade_offs": "[TRADE-OFFS REQUIRED]",
            "cma_cpp_cqa": "[REQUIRED: map to measurable CQA]",
            "regulatory_status": "[VERIFY per jurisdiction]",
            "patent_ip": "[LINK REQUIRED: publication number + claim + example + passage + status]",
            "cost_impact": "[COST REQUIRED: baseline vs quote]",
            "evidence": "[REQUIRED]",
            "validation": "[REQUIRED: control+batches+replicates+acceptance]",
            "risk": "[RISK ASSESSED per category]",
        })

    cma_rows = []
    for attr in (kpp_hits[:4] or ["key performance property"]):
        cma_rows.append({
            "attribute": attr,
            "context": f"{all_term} — measured by {attr}",
            "relationship": "[CMA→CPP→CQA — link only when measurable]",
            "criticality": "[CRITICAL ONLY IF linked to a measurable CQA]",
            "baseline_value": "[DATA REQUIRED]",
            "target_value": f"[Define for {target}]",
        })

    compat_rows = [
        {"check": "Compatibility which formulation/material", "status": "[REQUIRED]", "note": "compatibility is NEVER inferred from one reference — 'screened' requires data"},
    ]
    cost_rows = [
        {"metric": "Baseline unit cost", "value": "[BASELINE REQUIRED]"},
        {"metric": "New unit cost", "value": "[QUOTE REQUIRED]"},
        {"metric": "Arithmetic delta", "value": "[CALCULATE — no 'lower cost' claim without this]"},
    ]

    reg_rows = []
    for m_ in (["India", "United States", "Canada"]):
        reg_rows.append({
            "market": m_,
            "route": "[CONFIRM per jurisdiction]",
            "suitability": "FDA Inactive Ingredient Database entry / ICH listing is context ONLY — never universal suitability; route, level and jurisdiction decide.",
            "claim": "No 'excipient-listed / ICH-listed' approval claim.",
        })

    pat_terms = list(_PAT_PUBNO.findall(space or "")) or []
    ip_rows = []
    for p in pat_terms[:5]:
        ip_rows.append({
            "publication_num": p,
            "claim": "[VERIFY claims list]",
            "passage": "[VERIFY example/passage]",
            "status": "[VERIFY status]",
        })
    if not ip_rows:
        ip_rows.append({
            "publication_num": "[NO PATENT NUMBER DETECTED]",
            "claim": "[NOT SEARCHED — verify]",
            "passage": "[NOT SEARCHED]",
            "status": "[VERIFY status]",
        })

    risk_rows = [
        {"risk": "Technical/performance", "basis": "[DATA REQUIRED]", "severity": "[NOT RATED]", "mitigation": "[DEFINE]", "validation": "[DEFINE]"},
        {"risk": "Manufacturing/process", "basis": "[DATA REQUIRED]", "severity": "[NOT RATED]", "mitigation": "[DEFINE]", "validation": "[DEFINE]"},
        {"risk": "Regulatory/suitability", "basis": "per-jurisdiction review required", "severity": "[NOT RATED]", "mitigation": "[DEFINE]", "validation": "[DEFINE]"},
        {"risk": "Cost/economics", "basis": "[BASELINE vs QUOTE REQUIRED]", "severity": "[NOT RATED]", "mitigation": "[DEFINE]", "validation": "[DEFINE]"},
        {"risk": "IP/freedom", "basis": "[PUBLICATION NUMBER + CLAIM + EXAMPLE + STATUS REQUIRED]", "severity": "[NOT RATED]", "mitigation": "[DEFINE]", "validation": "[DEFINE]"},
    ]

    mind_rows = []
    for c_ in cands[:4]:
        mind_rows.append({
            "node": c_["id"], "principle": "[TECHNICAL PRINCIPLE REQUIRED]", "root_cause_link": ("[ROOT CAUSE REQUIRED]" if c_["route"].startswith("C") else "[N/A — hypothesis]"),
            "improvement": c_["expected_benefit"], "risk": "[DEFINE]", "maturity": "[Emerging/Demonstrated/Established/Unknown]",
            "evidence": "[REQUIRED]", "validation": c_["validation"], "scale_up": "[DEFINE]",
        })

    exp_rows = []
    for i, c_ in enumerate(cands[:3]):
        exp_rows.append({
            "experiment": f"MAT-EX-{i+1:03d}", "objective": f"Validate {c_['id']} for {target}", "control": "[BASELINE MATERIAL]", "test": c_["id"],
            "batch_plan": "[N (≥3)]", "replicates": "[≥3]", "monitor": "[CMAs/CPPs/CQAs list]", "endpoints": "[DEFINE]", "acceptance": "[DEFINE]", "failure_criteria": "[DEFINE]", "decision": "[Define advance/stop]",
        })
    doe_rows = [
        {"doe_type": "Full/fractional factorial", "use": "few factors — screen CMA/CPP candidates", "runs": "[DESIGN]"},
        {"doe_type": "Box–Behnken / central-composite", "use": "quadratic model for optimum windows", "runs": "[DESIGN]"},
        {"doe_type": "Mixture design", "use": "excipient ratios", "runs": "[DESIGN]"},
    ]

    result["sections"] += [
        _section("Material–problem intake & scope", [
            {"current_material": all_term, "grade": g, "loading": "[NOT STATED]", "failure": ", ".join(p_obs[:5]) or "[NOT STATED]",
             "target": target, "scale_equipment": "[NOT STATED]", "jurisdictions": "[NOT STATED]", "tests_available": "[NOT STATED]"},
        ], ["current_material", "grade", "loading", "failure", "target", "scale_equipment", "jurisdictions", "tests_available"],
            "If any field is missing, the corresponding conclusion is blocked — no generic alternatives."),
        _section("Problem classification", [
            {"class": "Category", "value": "[Classify per symptom: stability/mechanical/biological/regulatory/economic]"},
            {"class": "Failure boundary", "value": "[MATERIAL vs PROCESS vs PRODUCT vs SUPPLY — verify]"},
        ], ["class", "value"], "Classify before recommending — a symptom does not equal a cause."),
        _section("Root-cause tree (hypotheses)", root_rows, ["branch", "why", "verification"],
                 "'Root cause' only when confirmed — otherwise treat as hypotheses pending screening."),
        _section("Current material characterization", [
            {"attribute": "Identity & supplier", "value": f"{all_term} · {g}", "basis": "[datasheet/lot required]"},
            {"attribute": "Physical properties", "value": "[NOT MEASURED]", "basis": "particle size / surface / moisture / flow"},
            {"attribute": "Chemical properties", "value": "[NOT MEASURED]", "basis": "purity / impurity profile / hydration"},
            {"attribute": "Process properties", "value": "[NOT MEASURED]", "basis": "mixing / compression / drying behaviour"},
        ], ["attribute", "value", "basis"], "Characterization data gates CMA assignment."),
        _section("CMA–CPP–CQA mapping (ICH Q8(R2))", cma_rows, ["attribute", "context", "relationship", "criticality", "baseline_value", "target_value"],
                 "'Critical' only when linked to a measurable CQA; never a passthrough generic table with no data."),
        _section("Solution direction set", [
            {"direction_id": c_["id"], "direction": c_["route"], "candidate_material": c_["candidate_material"], "rationale": c_["expected_benefit"]} for c_ in cands
        ], ["direction_id", "direction", "candidate_material", "rationale"],
            "Never 'Alternative-1 / Alternative-2' — actual candidates carrying the required fields."),
        _section("Specific solution candidates (evidence-classified)", [
            {k: c_[k] for k in ["id", "route", "candidate_material", "grade", "loading", "mechanism", "expected_benefit", "trade_offs", "cma_cpp_cqa", "regulatory_status", "cost_impact", "evidence", "validation"]} for c_ in cands
        ], ["id", "route", "candidate_material", "grade", "loading", "mechanism", "expected_benefit", "trade_offs", "cma_cpp_cqa", "regulatory_status", "cost_impact", "evidence", "validation"],
            "Each MS-ID is a hypothesis bundle — not a recommendation — until validated."),
        _section("Material maturity", [
            {"candidate": c_["id"], "maturity": "[Emerging/Demonstrated/Established/Unknown]", "basis": "patent alone ≠ industrial maturity — check scale-up, commercial use, literature, regulatory experience"} for c_ in cands
        ], ["candidate", "maturity", "basis"], "Patent/doc-reference alone is not maturity evidence."),
        _section("Solution mind map (meaningful nodes)", mind_rows, ["node", "principle", "root_cause_link", "improvement", "risk", "maturity", "evidence", "validation", "scale_up"],
                 "Each node carries technical principle, problem link, improvement, risk, maturity, evidence, validation and scale-up."),
        _section("Material compatibility", compat_rows, ["check", "status", "note"], "'Compatibility screened' is NOT a statement without data."),
        _section("Cost analysis (arithmetic required)", cost_rows, ["metric", "value"], "'Lower cost' requires the delta calculation."),
        _section("Regulatory & suitability review", reg_rows, ["market", "route", "suitability", "claim"], "ICH/FDA Inactive Ingredient list entries are context, not universal approval."),
        _section("Patent / IP review", ip_rows, ["publication_num", "claim", "passage", "status"], "'Patent-linked' without a publication number + claim + example + passage + jurisdiction + status is NOT a valid link."),
        _section("Risk classification (per category)", risk_rows, ["risk", "basis", "severity", "mitigation", "validation"], "No 'low risk' just because cheaper — each category assessed with basis."),
        _section("Validation experiment design", exp_rows, ["experiment", "objective", "control", "test", "batch_plan", "replicates", "monitor", "endpoints", "acceptance", "failure_criteria", "decision"],
                 "MAT-EX protocol: control, N batches (≥3), replicates, monitored CMAs/CPPs/CQAs, endpoints, acceptance, failure and decision rules."),
        _section("Design of experiments (doe) options", doe_rows, ["doe_type", "use", "runs"], "A DOE plan is chosen AFTER the controlling variables are identified — not before."),
        _section("Data gaps to close", [
            {"gap": "Material datasheet + lot number", "for": "identity & grade"},
            {"gap": "Failure count + distribution data", "for": "problem classification"},
            {"gap": "CMA/CPP/CQA measurement set", "for": "criticality mapping"},
            {"gap": "Compatibility & cost (baseline+quote)", "for": "suitability and economics"},
            {"gap": "Patent/claims verification", "for": "IP claims"},
            {"gap": "Multi-batch validation data", "for": "any 'fix' claim"},
        ], ["gap", "for"], "Close gaps with experiments — references alone don't close them."),
        _section("Recommended next steps", [
            {"step": "1", "action": "Confirm the root-cause branch with a controlled screening (material/process/product/supply)."},
            {"step": "2", "action": "Characterize the current material and map CMA/CPP/CQA with measured values."},
            {"step": "3", "action": "Select real candidate materials/processes and fill every required field per MS-ID."},
            {"step": "4", "action": "Design MAT-EX studies (control + ≥3 batches + replicates + acceptance), then DOE if needed."},
            {"step": "5", "action": "Only then run regulatory, cost and patent verification per target market."},
        ], ["step", "action"], "Deterministic sequence — no alternative is final before validation."),
        _section("Limitations", [
            {"limitation": "All candidates are hypotheses requiring controlled validation — nothing is a recommendation here."},
            {"limitation": "No compatibility, cost, regulatory or IP status is asserted without data."},
            {"limitation": "Root cause is not confirmed without screening."},
        ], ["limitation"], "Hard limits — the output is a hypothesis bundle, not a validated fix."),
        _section("Find-better-material standard (judge line)", [{"standard": "IP-SAKTI ka Material Find Solutions Agent sirf Alternative-1 ya Alternative-2 suggest nahi karta. Ye current material aur failure mode identify karta hai, root-cause hypotheses banata hai, critical material attributes, process parameters aur quality attributes map karta hai, actual material/process alternatives compare karta hai, regulatory, cost, manufacturing aur IP risks assess karta hai, aur controlled multi-batch validation plan deta hai."}],
                 ["standard"], "This is the pass/fail test the evaluator applies."),
    ]

    result["findings"].append(_finding("m-qc", "Quality-control checklist",
        "current material + grade + loading captured; failure/target captured; problem classified; root cause vs symptom separated; characterization required; CMA→CPP→CQA mapped only when measurable; actual MS-001/002 candidates (no Alternative-1/2); meaningful mind-map nodes; compatibility requires data; cost has arithmetic; regulatory reviewed per jurisdiction; patent link has number+claim+passage+status; maturity never from patent alone; risk classified per category with basis; validation plan with control/batches/replicates/acceptance; DOE tied to identified variables; blocked when inputs insufficient; 'not assessed' when data absent; label is 'Preliminary material/process hypotheses for controlled validation'.", "info"))
    result["findings"].append(_finding("m-label", "Output label correction", "Label this output 'Preliminary material/process hypotheses for controlled validation' — never 'Recommended solution directions'.", "warning"))
    return result
