"""Invention disclosure drafting and block-reason analysis.

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
    _DOSAGE_FORM,
    _citation_kind,
    _draft_block_reasons,
    _ingredient_benefit_split,
    _parse_invention,
    _process_steps,
    _short_name,
    _solvent_word,
)
from app.services.innolab._shared import (
    _finding,
    _markets,
    _section,
    _text,
)
from app.services.agent_hub import toolbox

__all__ = [
    "_disclosure_ratio",
    "_PART_MARKERS",
    "_SKIP_MENTION",
    "_mention_candidates",
    "_hub_invention_disclosure",
]

def _disclosure_ratio(text: str, names: list[str]) -> str | None:
    """Capture 'N parts X ... M parts Y' → 'about N:M' from raw notes."""
    parts = re.findall(r"([\d.]+)\s*parts?", text or "")
    if len(parts) >= 2:
        return f"about {parts[0]}:{parts[1]}"
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\b", text or "")
    if m:
        return f"about {m.group(1)}:{m.group(2)}"
    return None


_PART_MARKERS = ("root", "extract", "powder", "berry", "leaf", "leaves", "seed", "bark",
                 "stem", "rhizome", "resin", "flower", "fruit", "kernel", "wood", "tuber")


_SKIP_MENTION = ("alcohol", "water", "ethanol", "hydroalcoholic", "glycerol", "methanol",
                 "isopropyl", "acetone", "extraction", "solvent", "solution", "process",
                 "parts", "mixture", "blend", "composition", "formulation")


def _mention_candidates(notes: str) -> list[str]:
    """Surface capitalized botanical mentions from raw notes WITHOUT inventing resolution —
    output is labelled 'candidate, not confirmed' by the caller."""
    txt = (notes or "")[:2000]
    out: list[str] = []
    seen: set = set()
    patterns = [
        r"(\d+(?:\.\d+)?\s*parts?)\s+(?:of\s+)?([A-Za-z][A-Za-z .'-]{1,40}?)(?=\s+(?:with|and|at|for|by|,)|,|\.|$)",
        r"([A-Za-z][A-Za-z -]{1,30}?)\s+(" + "|".join(_PART_MARKERS) + r")\b",
    ]
    for pat in patterns:
        for m in re.finditer(pat, txt, re.I):
            name = (m.group(2) if pat.startswith(r"(\d+") else m.group(1)).strip().rstrip(".")
            first = re.split(r"\s+", name)[0].strip()
            low = name.lower()
            if not first or len(first) < 4 or any(re.search(r"\b" + w + r"\b", low) for w in _SKIP_MENTION):
                continue
            key = first.lower()
            if key not in seen:
                seen.add(key)
                out.append(first[:1].upper() + first[1:])
    return out[:8]


def _hub_invention_disclosure(inputs: dict[str, Any], result: dict[str, Any], resolved: list[dict[str, Any]], botanicals: str) -> dict[str, Any]:
    """SOURCE-OF-TRUTH invention disclosure — a complete Problem → Means → Mechanism → Effect →
    Evidence → Scope record, never a polished generic report. Every missing datum is an explicit
    [TO BE CONFIRMED] / [NOT PROVIDED] / [EXPERIMENTAL DATA REQUIRED] marker. Nothing is invented:
    not inventors, dates, ingredients, ratios, process parameters, results, advantages,
    patentability or regulatory status. Patent-drafting handoff is blocked until the record is
    inventor-confirmed and evidence-backed."""
    import datetime

    notes = _text(inputs, "problem_text", "document_text", "disclosure_text", "formulation_text") or "[NO NOTES PROVIDED]"
    try:
        toolbox.document_entities(notes)
    except Exception:  # noqa: BLE001
        pass
    inventors = _text(inputs, "inventors")
    inventors_known = bool(inventors) and inventors.strip().lower() not in ("tbd", "unknown", "n/a", "none", "?")
    filing_intent = _text(inputs, "filing_intent") or "Undecided"
    effect_statement = _text(inputs, "improve_aspect") or _text(inputs, "intended_use")
    process_desc = _text(inputs, "process_desc", "process", "formulation_text")
    markets = _markets(inputs)

    inv = _parse_invention(inputs, resolved)
    split = _ingredient_benefit_split(inv, resolved, inputs)
    blockers = _draft_block_reasons(inv, inputs)
    disc_steps = _process_steps(process_desc)
    ratio = _disclosure_ratio(notes, inv["ingredients"]) or inv["ratio"]

    resolved_names = [_short_name(cast(str, r.get("botanical_name") or r.get("raw_name"))) for r in resolved if r.get("resolved") and r.get("raw_name")]
    mentioned = _mention_candidates(notes)
    confirmed_names = [n for n in (resolved_names or [_short_name(n) for n in split["ingredients"]] or []) if not any(w in n.lower() for w in _SKIP_MENTION)]
    ingredients_known = bool(confirmed_names or mentioned)
    display_names = confirmed_names or mentioned
    confirmed_any = bool(confirmed_names)
    solvent = inv["solvent"]
    solvent_known = bool(solvent) and _solvent_word(solvent) != "solvent"
    markers_known = bool(inv["markers"])
    dosage_generic = not _DOSAGE_FORM.search(str(inv["dosage_form"]))
    temp_m = re.search(r"(\d{2,3})\s*[°]?\s*C(?:elsius)?", notes, re.I)
    temperature = (temp_m.group(0).replace("Celsius", "°C").replace("C", "°C")) if temp_m else "[INVENTOR INPUT REQUIRED]"
    time_m = re.search(r"(\d+(?:\.\d+)?)\s*h(?:ours?)?", f"{notes} {process_desc}", re.I)
    processing_time = str(time_m.group(0)) if time_m else "[INVENTOR INPUT REQUIRED]"
    steps_known = bool(disc_steps)

    benefits = [b for b in split["benefit_terms"] if b != "none detected"]
    unsupported_terms = benefits + [b["title"] for b in blockers]
    chain_supported = ingredients_known and steps_known and solvent_known and markers_known and bool(effect_statement)
    concept_status = (
        "Partially evidenced — the problem→means→effect chain has detectable technical means, but measurable "
        "endpoints and comparative data are still required; inventor confirmation pending."
        if chain_supported else
        "Preliminary — the problem, technical means and measured effect are not yet fully defined. Confirm the "
        "exact problem, essential technical features and mechanism, and attach comparative data."
    )

    citations = result.get("citations") or []
    tk_hit = any(re.search(r"traditional|ayurveda|charaka|susruta|tkdl|monograph", (c.get("act_title") or ""), re.I) for c in citations)
    tk_status = "Possible — Ayurvedic / traditional-text review required" if ingredients_known and not tk_hit else (
        "Confirmed — traditional-knowledge material present in the corpus context" if tk_hit else "Unknown — [INVENTOR INPUT REQUIRED]")

    doc_date = datetime.date.today().isoformat()
    ing_phrase = (f"{len(display_names)} ingredient(s) — {', '.join(display_names)[:80]}" if ingredients_known
                  else "0 ingredient(s)")
    result["summary"] = (
        f"Disclosure record drafted as a DRAFT (not inventor-confirmed). Extracted from the notes: "
        f"{ing_phrase}, {len(disc_steps)} process step(s), solvent "
        f"{solvent or '[none detected]'}, marker(s) {'present' if markers_known else 'absent'}, "
        f"ratio {ratio or '[not confirmed]'}. {len(unsupported_terms)} unsupported/invalid term(s) flagged. "
        f"Inventor confirmation and experimental evidence are pending — patent-drafting handoff is BLOCKED."
    )
    result["note"] = ("Raw inventor notes → inventor & ownership capture → What–Where–Why–How questionnaire → problem "
                      "definition → technical feature extraction → mechanism/effect mapping → evidence & experiment "
                      "capture → embodiment & best-mode → traditional-knowledge review → public-disclosure timeline → "
                      "missing-data gate → inventor confirmation → signed disclosure record.")
    result["findings"].extend([
        _finding("id-status", "Disclosure status",
                 "Draft — inventor confirmation and technical data pending. Not 'filing-ready'.", "warning"),
        _finding("id-ing", "Confirmed ingredients",
                 f"{len(confirmed_names)} ingredient(s) mentioned in the notes: {', '.join(confirmed_names)[:150]}.",
                 "info" if ingredients_known else "warning"),
        _finding("id-invalid", "Unsupported / invalid terms",
                 (f"{len(unsupported_terms)} flagged: " + "; ".join(unsupported_terms)[:150])
                 if unsupported_terms else "No benefit terms, corrupted text or undefined drafting terms detected.",
                 "error" if unsupported_terms else "info"),
        _finding("id-concept", "Inventive concept status", concept_status, "warning"),
        _finding("id-problem", "Problem → means → effect chain",
                 ("Technical means detected (steps/solvent/ratio); measurable endpoints still required: exactly one "
                  "baseline, comparator and metric per claimed advantage.")
                 if steps_known or solvent_known else
                 "Chain incomplete — problem, technical means and measured effect all require inventor input.", "warning"),
        _finding("id-evidence", "Evidence classification",
                 f"{sum(1 for c in citations if 'patent' in ((c.get('act_title') or '') + ' ' + (c.get('authority') or '')).lower())} "
                 f"patent / prior-art item(s) and {max(0, len(citations))} other corpus item(s); regulatory sources are "
                 f"context only — they prove neither that the invention works nor patentability.", "info"),
        _finding("id-handoff", "Patent-drafting handoff",
                 "BLOCKED — inventor identities, complete technical means, essential features, ≥1 reproducible "
                 "embodiment, support data and the public-disclosure timeline are required first.", "error"),
    ])
    result["suggestions"] = [
        "Answer the inventor questionnaire: complete formulation, scientific names, plant part, solvent, solvent ratio, "
        "temperature, time, extraction sequence, marker identity and range, dosage form and botanical ratio.",
        "Record full inventor names, contributions, organization, applicant/owner, signature and date — the record "
        "cannot be inventor-confirmed without them.",
        "Attach at least one controlled comparative experiment per claimed advantage (with control, condition, result "
        "and replicates) — e.g. stability measured at the stated storage condition.",
        "Document the public-disclosure timeline and any NDA; confirm confidentiality before further sharing.",
        "Run novelty_search and patent drafting only after the essential features above are inventor-confirmed.",
    ]

    inventor_rows = [
        {"item": "Inventor 1 — full name", "value": inventors if inventors_known else "[INVENTOR INPUT REQUIRED]"},
        {"item": "Role / organization / country / email", "value": "[NOT PROVIDED]"},
        {"item": "Contribution to the inventive concept", "value": "[NOT PROVIDED]"},
        {"item": "Signature & date", "value": "[INVENTOR INPUT REQUIRED]"},
        {"item": "Applicant / proposed owner", "value": "[NOT PROVIDED]"},
        {"item": "Employer / institution", "value": "[NOT PROVIDED]"},
        {"item": "Funding source / grant", "value": "[NOT PROVIDED]"},
        {"item": "Collaboration partners / joint-development", "value": "[NOT PROVIDED]"},
        {"item": "Contributors who are not inventors", "value": "[NOT PROVIDED]"},
        {"item": "Traditional-knowledge community / source", "value": "[NOT PROVIDED]"},
        {"item": "Assignment status", "value": "[NOT PROVIDED]"},
    ]
    confirmed_rows = [
        {"item": "Botanical components",
         "value": (", ".join(confirmed_names)
                   if confirmed_any else
                   (", ".join(mentioned) + " — [CONFIRM scientific & as-written names]") if mentioned else "[NOT PROVIDED]")},
        {"item": "Process steps", "value": "; ".join(disc_steps) if steps_known else "[NOT PROVIDED]"},
        {"item": "Solvent system", "value": solvent if solvent_known else "[NOT PROVIDED]"},
        {"item": "Botanical / solvent ratio", "value": ratio or "[NOT CONFIRMED]"},
        {"item": "Temperature (as written)", "value": temperature if temperature.startswith("[") else temperature},
        {"item": "Processing time (as written)", "value": processing_time if processing_time.startswith("[") else processing_time},
        {"item": "Marker compounds & ranges", "value": ", ".join(inv["markers"]) if markers_known else "[EXPERIMENTAL DATA REQUIRED]"},
        {"item": "Dosage form", "value": inv["dosage_form"] if not dosage_generic else "[TO BE CONFIRMED]"},
        {"item": "Claimed advantage (inventor statement)", "value": effect_statement or "[INVENTOR INPUT REQUIRED]"},
    ]
    unconfirmed_rows = [
        {"item": f"Inclusion of {' and '.join(mentioned) if mentioned else 'additional botanicals'}"
                 " & exact plant parts", "value": "[TO BE CONFIRMED]"},
        {"item": "Exact plant part & extract type", "value": "[INVENTOR INPUT REQUIRED]"},
        {"item": "Solvent ratio & solid-to-liquid ratio", "value": "[INVENTOR INPUT REQUIRED]"},
        {"item": "Extraction temperature window & time", "value": "[INVENTOR INPUT REQUIRED]"},
        {"item": "Simultaneous vs sequential extraction & downstream filtration/concentration/drying", "value": "[INVENTOR INPUT REQUIRED]"},
        {"item": "Marker identity & target range", "value": "[EXPERIMENTAL DATA REQUIRED]"},
        {"item": "Baseline, comparator and measured endpoint per advantage", "value": "[EXPERIMENTAL DATA REQUIRED]"},
        {"item": "Reproducibility (batches / replicates)", "value": "[EXPERIMENTAL DATA REQUIRED]"},
        {"item": "Public-disclosure history & ownership", "value": "[INVENTOR INPUT REQUIRED]"},
    ]

    feature_rows = [
        {"feature": n, "category": "Composition", "essentiality": "To be confirmed by inventor",
         "confirmed": ("Yes — registry match" if confirmed_any else "Candidate — mentioned in notes"),
         "evidence": "Inventor note",
         "missing_detail": "Plant part · grade · purity · extract type"}
        for n in display_names[-6:]
    ] + [
        {"feature": "Extraction solvent", "category": "Process", "essentiality": "To be confirmed by inventor",
         "confirmed": "Partial" if solvent_known else "No", "evidence": "Inventor note" if solvent_known else "Not provided",
         "missing_detail": "Exact system, ratio and grade"},
        {"feature": "Extraction temperature", "category": "Process parameter", "essentiality": "To be confirmed by inventor",
         "confirmed": "Partial", "evidence": "Inventor note", "missing_detail": "Exact working range"},
        {"feature": "Processing time", "category": "Process parameter", "essentiality": "To be confirmed by inventor",
         "confirmed": "Partial", "evidence": "Inventor note", "missing_detail": "Exact duration and endpoint"},
        {"feature": "Botanical ratio", "category": "Composition", "essentiality": "To be confirmed by inventor",
         "confirmed": "Partial" if ratio else "No", "evidence": "Inventor note" if ratio else "Not provided",
         "missing_detail": "Ratio basis and acceptable range"},
        {"feature": "Marker standardisation", "category": "Quality control", "essentiality": "Optional / to be confirmed",
         "confirmed": "No" if not markers_known else "Partial", "evidence": "Not provided" if not markers_known else "Notes",
         "missing_detail": "Marker identity and quantitative range"},
        {"feature": "Dosage form", "category": "Product form", "essentiality": "To be confirmed by inventor",
         "confirmed": "Partial" if not dosage_generic else "No", "evidence": "Inventor note" if not dosage_generic else "Not provided",
         "missing_detail": "Exact dosage form, unit and packaging"},
    ]
    param_rows = [
        {"parameter": "Botanical ratio", "value_now": ratio or "[NOT PROVIDED]", "tested_range": "[NOT VERIFIED]",
         "preferred": "[TO BE CONFIRMED]", "proposed_unverified": "[NOT TESTED]", "missing": "Ratio basis and range"},
        {"parameter": "Solvent system / ratio", "value_now": solvent or "[NOT PROVIDED]", "tested_range": "[NOT VERIFIED]",
         "preferred": "[TO BE CONFIRMED]", "proposed_unverified": "[NOT TESTED]", "missing": "Solvent identity, ratio, solid-to-liquid"},
        {"parameter": "Temperature", "value_now": temperature, "tested_range": "[NOT VERIFIED]", "preferred": "[TO BE CONFIRMED]",
         "proposed_unverified": "[NOT TESTED]", "missing": "Working window and control method"},
        {"parameter": "Processing time", "value_now": processing_time, "tested_range": "[NOT VERIFIED]", "preferred": "[TO BE CONFIRMED]",
         "proposed_unverified": "[NOT TESTED]", "missing": "Endpoint criterion"},
        {"parameter": "Marker content & range", "value_now": ", ".join(inv["markers"]) if markers_known else "[NOT PROVIDED]",
         "tested_range": "[NOT VERIFIED]", "preferred": "[TO BE CONFIRMED]", "proposed_unverified": "[NOT TESTED]",
         "missing": "Identity, method, unit, reproducibility"},
        {"parameter": "pH / moisture / stability condition", "value_now": "[NOT PROVIDED]", "tested_range": "[NOT VERIFIED]",
         "preferred": "[TO BE CONFIRMED]", "proposed_unverified": "[NOT TESTED]", "missing": "Storage condition, timepoints, limit"},
    ]
    evidence_rows = [
        {"experiment": "EX-001", "objective": "[Defined endpoint for the claimed advantage]",
         "control": "[Baseline / comparator]", "test_condition": "[Condition]", "metric": "[Metric]",
         "result": "[EXPERIMENTAL DATA REQUIRED]", "replicates": "[N]", "status": "Pending"}
    ]
    [
        {"section": "Title", "content": inv["title"][:140]},
        {"section": "Technical field", "content": "Ayurvedic / nutraceutical botanical compositions and their preparation processes."},
        {"section": "Background — current approach", "content": ("Prior context assembled from corpus passages (" + str(len(citations)) + "). "
                                                                  "Status: [SEPARATE inventor-observed problems from literature context before speaking of limitations.]"
                                                                  if citations else "No retrieved background passages — inventor assumptions must be labelled as such.")},
        {"section": "Problem", "content": f"(Inventor-stated need) {effect_statement or '[INVENTOR INPUT REQUIRED]'} — baseline and failure conditions [EXPERIMENTAL DATA REQUIRED]."},
        {"section": "Solution", "content": f"Composition: {', '.join(display_names) if ingredients_known else '[NOT PROVIDED]'}; process: {'; '.join(disc_steps) or '[NOT PROVIDED]'}; solvent: {solvent or '[NOT PROVIDED]'}."},
        {"section": "Mechanism", "content": f"Features → process interaction → intermediate change → final technical effect. Measured effect: {'[EXPERIMENTAL DATA REQUIRED]' if not markers_known and not effect_statement else effect_statement + ' — objective evidence not yet attached.'}"},
        {"section": "Essential features", "content": "F1..Fn per the feature matrix — essentiality to be confirmed by the inventor, not assumed from notes."},
        {"section": "Examples / best mode", "content": "[TO BE CONFIRMED] — the inventor must disclose the best known method (Sec. 10 complete-specification rule)."},
        {"section": "Results", "content": "[EXPERIMENTAL DATA REQUIRED] — one controlled experiment per claimed advantage, with comparator and replicates."},
        {"section": "Public disclosure", "content": "[NOT PROVIDED] — confidential until the disclosure timeline and NDA status are recorded."},
        {"section": "Signatures", "content": "[INVENTOR INPUT REQUIRED] — inventor and reviewer signatures and dates pending."},
    ]

    proc_detail_rows = []
    if disc_steps:
        for _pnum, _pstep in enumerate(disc_steps[:8], start=1):
            proc_detail_rows.append({
                "step": f"Step {_pnum}", "input": _pstep, "operation": "[CONFIRM WITH THE INVENTOR]",
                "equipment": "[NOT PROVIDED]", "temperature": temperature, "time": processing_time,
                "solvent": solvent or "[NOT PROVIDED]",
                "solvent_ratio": ratio if ":" in (ratio or "") else "[TO BE CONFIRMED]",
                "output": "[TO BE CONFIRMED]", "critical_control": "[TO BE CONFIRMED]"})
    else:
        proc_detail_rows.append({"step": "Step 1", "input": "[INVENTOR INPUT REQUIRED]",
                                 "operation": "[INVENTOR INPUT REQUIRED]", "equipment": "[INVENTOR INPUT REQUIRED]",
                                 "temperature": "[INVENTOR INPUT REQUIRED]", "time": "[INVENTOR INPUT REQUIRED]",
                                 "solvent": "[INVENTOR INPUT REQUIRED]", "solvent_ratio": "[INVENTOR INPUT REQUIRED]",
                                 "output": "[INVENTOR INPUT REQUIRED]", "critical_control": "[INVENTOR INPUT REQUIRED]"})

    mat_rows = [
        {"material": n, "scientific_name": "[CONFIRM]", "plant_part": "[TO BE CONFIRMED]", "source": "[NOT PROVIDED]",
         "grade_purity": "[NOT PROVIDED]", "extract_type": "[TO BE CONFIRMED]", "markers": "[EXPERIMENTAL DATA REQUIRED]",
         "ratio": ratio or "[TO BE CONFIRMED]", "confirmed": "Candidate — mentioned in notes" if not confirmed_any else "Registry match"}
        for n in display_names[:8]
    ] or [
        {"material": "[NONE MENTIONED]", "scientific_name": "—", "plant_part": "—", "source": "—", "grade_purity": "—",
         "extract_type": "—", "markers": "—", "ratio": "—", "confirmed": "—"},
    ]
    mat_rows += [
        {"material": "Solvent system", "scientific_name": "—", "plant_part": "—", "source": "[NOT PROVIDED]",
         "grade_purity": "[NOT PROVIDED]", "extract_type": "—", "markers": "—", "ratio": ratio or "[TO BE CONFIRMED]",
         "confirmed": "Detected from notes" if solvent_known else "[NONE MENTIONED]"},
        {"material": "Dosage-form excipients / carriers", "scientific_name": "—", "plant_part": "—",
         "source": "[NOT PROVIDED]", "grade_purity": "[NOT PROVIDED]", "extract_type": "—", "markers": "—",
         "ratio": "—", "confirmed": "[TO BE CONFIRMED]"},
    ]

    comparative_rows = [
        {"example": "Baseline (existing approach)", "condition": "[Control — INVENTOR INPUT REQUIRED]",
         "result": "[EXPERIMENTAL DATA REQUIRED]", "outcome_vs_invention": "—"},
        {"example": "Invention (as per notes)", "condition": "; ".join(disc_steps[:4]) or "[Process steps required]",
         "result": "[EXPERIMENTAL DATA REQUIRED]", "outcome_vs_invention": "—"},
        {"example": "Alternative embodied variant", "condition": "[Variant — INVENTOR INPUT REQUIRED]",
         "result": "[EXPERIMENTAL DATA REQUIRED]", "outcome_vs_invention": "—"},
        {"example": "Negative / contradictory results", "condition": "[Noted? — [NOT PROVIDED]]",
         "result": "[EXPERIMENTAL DATA REQUIRED]", "outcome_vs_invention": "—"},
    ]
    industrial_rows = [
        {"aspect": "Manufacturing", "value": "Process as written: " + ("; ".join(disc_steps[:4]) or "[NOT PROVIDED]")
                                           + " — [SCALE-UP STATUS REQUIRED]"},
        {"aspect": "Use", "value": inv["use"]},
        {"aspect": "Scale-up status", "value": "[INVENTOR INPUT REQUIRED] — laboratory / pilot / commercial"},
        {"aspect": "Quality control", "value": "[EXPERIMENTAL DATA REQUIRED] — marker identity, assay method, batch release"},
        {"aspect": "Commercial application", "value": "[INVENTOR INPUT REQUIRED] — product form, packaging, market"},
    ]

    result["sections"] += [
        _section("# Invention Disclosure Record — document status", [
            {"item": "Disclosure ID", "value": "[NOT PROVIDED — allocate at inventor confirmation]"},
            {"item": "Version", "value": "0.1 (system draft)"},
            {"item": "Date / last updated", "value": doc_date + " (system generation date)"},
            {"item": "Disclosure status", "value": "Draft — inventor confirmation and technical data pending"},
            {"item": "Confidentiality status", "value": "Unknown — [INVENTOR INPUT REQUIRED]"},
            {"item": "Public disclosure status", "value": "Not provided — [INVENTOR INPUT REQUIRED]"},
            {"item": "Filing intent", "value": filing_intent},
            {"item": "Prepared by", "value": "IP-SAKTI Innovation Disclosure Agent (deterministic build)"},
            {"item": "Inventor confirmation", "value": "Pending — not confirmed in this build"},
        ], ["item", "value"], "This is not 'filing-ready': the record is a draft until inventors confirm it, technical "
                              "details are complete, evidence is attached, public-disclosure status is known and a "
                              "patent professional reviews it."),
        _section("1. Inventor and ownership (Who)", inventor_rows,
                 ["item", "value"], "Inventorship requires contribution to the inventive concept — not supervision, "
                                    "funding, lab management or report writing. Legal inventorship review is always required."),
        _section("2. Invention identification (What)", [
            {"item": "One-line summary", "value": inv["title"][:160]},
            {"item": "Primary type", "value": "Composition" + (" + Process" if steps_known else "")},
            {"item": "Secondary type / variants", "value": "[TO BE CONFIRMED]"},
            {"item": "Completion status", "value": "Concept / notes only — inventor must confirm the experimental stage"},
            {"item": "Technical field", "value": "Ayurvedic / nutraceutical botanical compositions and preparation processes"},
        ], ["item", "value"], "Vague titles ('herbal wellness solution', 'improved natural formulation') are avoided; the title is precise and technical."),
        _section("3. Confirmed vs unconfirmed (evidence-backed record)", confirmed_rows + unconfirmed_rows,
                 ["item", "value"], "Confirmed items come from the notes; everything else is an explicit pending item."),
        _section("4. Unsupported / invalid terms", [
            {"term": t, "status": "Excluded from the record until the inventor clarifies its status as an effect vs a component"}
            for t in unsupported_terms
        ] + ([{"term": "[none detected]", "status": "clean"} ] if not unsupported_terms else []),
                 ["term", "status"], "'Cognitive support', 'general wellness', undefined 'effective amounts' and similar "
                                     "terms are treated as outcomes, never as claim components."),
        _section("5. Existing technical background", [
            {"source": (c.get("act_title") or "passage")[:70], "type": _citation_kind(c),
             "authority": c.get("authority") or "KB", "relevance": "[Separate verified background from inventor assumptions]"}
            for c in citations[:5]
        ] + ([{"source": "[No retrieved passages]", "type": "—", "authority": "—", "relevance": "Inventor assumptions must be labelled"}]
             if not citations else []),
                 ["source", "type", "authority", "relevance"], "Regulatory documents (FSSAI / AYUSH / FDA) are context only."),
        _section("6. Technical problem (Why)", [
            {"item": "Observed problem / need", "value": ("Inventor-stated need: " + effect_statement) if effect_statement else "[INVENTOR INPUT REQUIRED]"},
            {"item": "Baseline performance", "value": "[EXPERIMENTAL DATA REQUIRED]"},
            {"item": "Failure condition", "value": "[INVENTOR INPUT REQUIRED]"},
            {"item": "Existing approach tried", "value": "[INVENTOR INPUT REQUIRED]"},
            {"item": "Measurement / test method", "value": "[EXPERIMENTAL DATA REQUIRED]"},
            {"item": "Constraints (safety · cost · production · regulatory · scale-up)", "value": "[INVENTOR INPUT REQUIRED]"},
        ], ["item", "value"], "Never a broad benefit — the problem must be a directly observable technical fact."),
        _section("7. Objectives (measurable)", [
            {"objective": "Define exactly one measurable endpoint per claimed advantage", "status": "Pending"},
            {"objective": "Establish marker identity and target range", "status": "Provided" if markers_known else "Pending"},
            {"objective": "Confirm stability condition and storage claim", "status": "Pending — attach data"},
            {"objective": "Define baseline and comparator", "status": "Pending"},
        ], ["objective", "status"], "Objectives are tracked to data, not to generic statements."),
        _section("8. Core technical solution (How)", [
            {"item": "Composition", "value": ", ".join(confirmed_names) if ingredients_known else "[NOT PROVIDED]"},
            {"item": "Process steps", "value": "; ".join(disc_steps) if steps_known else "[NOT PROVIDED]"},
            {"item": "Solvent system", "value": solvent if solvent_known else "[NOT PROVIDED]"},
            {"item": "Ratio", "value": ratio or "[NOT CONFIRMED]"},
            {"item": "Dosage form", "value": inv["dosage_form"] if not dosage_generic else "[TO BE CONFIRMED]"},
        ], ["item", "value"], "The solution is described in complete detail — never summarized as 'structure extracted from notes'."),
        _section("9. Problem → Cause → Solution → Mechanism → Effect → Evidence → Scope chain", [
            {"link": "Problem", "content": f"{effect_statement or '[INVENTOR INPUT REQUIRED]'} — a specific technical limitation in measurable terms, not a broad benefit",
             "state": "Stated (inventor)" if effect_statement else "Missing"},
            {"link": "Cause", "content": "Why the limitation occurs — [INVENTOR INPUT REQUIRED]", "state": "Unknown"},
            {"link": "Solution", "content": f"Composition: {', '.join(display_names[:4]) if ingredients_known else '[NOT PROVIDED]'}; process: {'; '.join(disc_steps[:4]) or '[NOT PROVIDED]'}; solvent: {solvent or '[NOT PROVIDED]'}",
             "state": "Detected — not yet inventor-confirmed"},
            {"link": "Mechanism", "content": "Feature(s) F1..Fn → process interaction → intermediate change → final technical effect", "state": "Preliminary"},
            {"link": "Effect", "content": "[EXPERIMENTAL DATA REQUIRED] — measurable change versus a baseline", "state": "Missing"},
            {"link": "Evidence", "content": "[EXPERIMENTAL DATA REQUIRED] — experiment, observation or document per statement", "state": "Missing"},
            {"link": "Scope", "content": "Essential vs optional features per the feature matrix — [INVENTOR CONFIRMATION REQUIRED]", "state": "Pending"},
        ], ["link", "content", "state"], "A broad benefit is never treated as the invention itself. The chain is complete only when every link is supported."),
        _section("10. Technical mechanism & effect", [
            {"item": "Cause-effect chain", "value": "Feature(s) F1..Fn → process interaction → intermediate change → final technical effect"},
            {"item": "Mechanism explanation", "value": ("Hydroalcoholic extraction + standardisation chain per the notes — [CONFIRM mechanism with the inventor]" if steps_known or solvent_known else "[NOT ESTABLISHED]")},
            {"item": "Expected effect", "value": effect_statement or "[INVENTOR INPUT REQUIRED]"},
            {"item": "Measured effect", "value": "[EXPERIMENTAL DATA REQUIRED]"},
            {"item": "Comparator / baseline", "value": "[EXPERIMENTAL DATA REQUIRED]"},
            {"item": "Test method / confidence", "value": "Confirmed / Preliminary / Hypothesis → currently 'Preliminary' unless standard measures are attached"},
            {"item": "Claimed benefit status", "value": (f"'{effect_statement}' is an inventor hypothesis only — no standard measure provided in the notes." if effect_statement and not markers_known else "Inventor-stated advantage; objective evidence not yet attached.")},
            {"item": "Action", "value": "Design a controlled comparative experiment per claimed advantage before treating it as a technical effect."},
        ], ["item", "value"], "Technical effect, biological effect, therapeutic claim, wellness claim and marketing statement are separated — never blended."),
        _section("11. Essential feature matrix", feature_rows,
                 ["feature", "category", "essentiality", "confirmed", "evidence", "missing_detail"],
                 "Essentiality is based on technical necessity, reproducibility, role in the effect, inventor confirmation and experimental evidence — notes alone do not make a feature essential."),
        _section("12. Embodiments, optional & alternative features", [
            {"embodiment": "Primary (from notes)", "content": f"Composition {' + '.join(confirmed_names[:4]) if ingredients_known else '[NOT PROVIDED]'} · {'; '.join(disc_steps) or '[process — NOT PROVIDED]'} · solvent {solvent or '[NOT PROVIDED]'} · ratio {ratio or '[NOT CONFIRMED]'}",
             "verified": "[NOT EXPERIMENTALLY VERIFIED]" if not (steps_known and markers_known) else "Reported in notes — confirm with data"},
            {"embodiment": "Alternative 2 — ratio / process-condition variant", "content": "[INVENTOR INPUT REQUIRED]", "verified": "Proposed only — not experimentally verified"},
            {"embodiment": "Alternative 3 — dosage-form variant", "content": "[INVENTOR INPUT REQUIRED]", "verified": "Proposed only — not experimentally verified"},
            {"embodiment": "Alternative 4 — equipment / packaging variant", "content": "[INVENTOR INPUT REQUIRED]", "verified": "Proposed only — not experimentally verified"},
        ], ["embodiment", "content", "verified"], "An untested alternative is never called a working embodiment."),
        _section("13. Detailed process & construction", proc_detail_rows,
                 ["step", "input", "operation", "equipment", "temperature", "time", "solvent", "solvent_ratio", "output", "critical_control"],
                 "Every step records input, operation, equipment, temperature, time, solvent, ratio, output and critical control — process text is converted into a structured table, never summarized as 'structure extracted from notes'."),
        _section("14. Materials & components", mat_rows,
                 ["material", "scientific_name", "plant_part", "source", "grade_purity", "extract_type", "markers", "ratio", "confirmed"],
                 "Exact identities, sources and specifications for every material; markers and quantitative ranges remain [EXPERIMENTAL DATA REQUIRED]."),
        _section("15. Parameters & ranges", param_rows,
                 ["parameter", "value_now", "tested_range", "preferred", "proposed_unverified", "missing"],
                 "Exact values, tested ranges, preferred ranges, untested proposed ranges and missing values are listed separately."),
        _section("16. Experimental evidence / results table", evidence_rows,
                 ["experiment", "objective", "control", "test_condition", "metric", "result", "replicates", "status"],
                 "Measurement status: no standard measures can be confirmed from the current notes. Impact: the technical "
                 "effect cannot yet be verified. Next action: define analytical endpoints and run controlled comparative experiments."),
        _section("17. Comparative examples", comparative_rows,
                 ["example", "condition", "result", "outcome_vs_invention"],
                 "Baseline vs invention vs alternatives vs negative results — each row requires measured data or an explicit [EXPERIMENTAL DATA REQUIRED] marker."),
        _section("18. Best known mode & reproducibility", [
            {"item": "Best known mode", "value": "[TO BE CONFIRMED] — the best way the inventor knows to perform the invention"},
            {"item": "Verification status", "value": "Demonstrated / Partially demonstrated / Not demonstrated — [INVENTOR INPUT REQUIRED]"},
            {"item": "Reproducibility", "value": "[EXPERIMENTAL DATA REQUIRED] — failed and tacit steps must be disclosed"},
            {"item": "Missing enabling information", "value": "Parameters, equipment, raw materials, quality checks and undocumented steps required."},
            {"item": "Regulatory rule", "value": "A complete specification must fully and particularly describe the invention, its operation/use and the method of performing it, including the best method known (Indian Patents Act, 1970, Sec. 10)."},
        ], ["item", "value"], "Known critical parameters are never hidden."),
        _section("19. Industrial applicability", industrial_rows,
                 ["aspect", "value"], "Manufacturing, use, scale-up, quality control and commercial application — confirmed by data, not assumed."),
        _section("20. Traditional-knowledge & biological-material review", [
            {"item": "Traditional-knowledge status", "value": tk_status},
            {"item": "Biological-material source", "value": "[NOT PROVIDED] — where and how the material was accessed"},
            {"item": "Prior-art concern", "value": "Documented traditional knowledge can create prior-art and exclusion risks — confirm overlap texts and pages"},
            {"item": "Technical distinction over known knowledge", "value": "[TO BE CONFIRMED] — a new process, standardisation or parameter, demonstrated by data"},
            {"item": "Legal review", "value": "Not yet determined"},
        ], ["item", "value"], "A documented traditional formulation is not automatically patentable."),
        _section("21. Public-disclosure timeline & confidentiality", [
            {"disclosure_event": "Publication / conference / customer demo / sale / online upload / investor / NDA / "
                                 "employee-contractor / competition / exhibition", "date": "[NOT PROVIDED]",
             "audience": "[NOT PROVIDED]", "country": "[NOT PROVIDED]", "nda": "[NOT PROVIDED]",
             "enabling": "[NOT PROVIDED]", "evidence": "[NOT PROVIDED]"},
            {"disclosure_event": "Overall status", "date": "[INVENTOR INPUT REQUIRED]", "audience": "—", "country": "—",
             "nda": "—", "enabling": "—", "evidence": "No public-disclosure history recorded"},
        ], ["disclosure_event", "date", "audience", "country", "nda", "enabling", "evidence"],
           "Confidentiality warning: public disclosure may affect patent rights depending on jurisdiction, timing, "
           "content and applicable law. Confirm the disclosure timeline with a patent professional before filing or "
           "sharing further."),
        _section("22. Filing intent & strategy", [
            {"item": "Filing intent", "value": filing_intent},
            {"item": "Target jurisdictions", "value": ", ".join(markets) if markets else "[NOT PROVIDED]"},
            {"item": "Target filing date / priority basis", "value": "[NOT PROVIDED] / [NOT PROVIDED]"},
            {"item": "Public-disclosure risk", "value": "Unknown — timeline not recorded"},
            {"item": "Candidate strategies", "value": "Broad composition · process protection · product-by-process · use · fallback claims · trade secret for process details — [AFTER INVENTOR CONFIRMATION]"},
        ], ["item", "value"], "Strategy is recommended only after considering disclosure, prior art, enablement, TK, value, "
                              "reverse-engineering, jurisdiction, cost and ownership."),
        _section("23. Preliminary IP handoff (gated)", [
            {"agent": "Novelty Search", "required": "Confirmed technical features, relevant dates, exact ingredients/process, essential & optional features",
             "status": "Blocked — features not inventor-confirmed"},
            {"agent": "Patent Drafting", "required": "Confirmed inventor info, complete technical means, essential features, ≥1 reproducible embodiment, support data or clear 'data pending' labels, disclosure timeline",
             "status": "Blocked — inventor confirmation and evidence pending"},
            {"agent": "FTO Search", "required": "Product/process definition, commercial activities, jurisdictions, review date, proposed formulation/process",
             "status": "Blocked — product/process not fully defined"},
            {"agent": "Regulatory review", "required": "Product category, intended use, ingredients, dosage form, claims, target jurisdiction",
             "status": "Conditional — provides context, never a patentability proof"},
            {"agent": "Identity gate", "required": "Inventor names, contributions, applicant/owner, signatures and dates",
             "status": "[INVENTOR INPUT REQUIRED]" if not inventors_known else "Identities captured"},
            {"agent": "Technical gate", "required": "Precise definition, complete parameters," + (" no [TO BE CONFIRMED] remaining" if (ingredients_known and steps_known and solvent_known and ratio) else " parameters/ratios pending"),
             "status": "Partial — confirm with the inventor"},
            {"agent": "Evidence gate", "required": "Baseline, comparator, measured results, replicates, attachments",
             "status": "[EXPERIMENTAL DATA REQUIRED]"},
        ], ["agent", "required", "status"], "Incomplete or corrupted terms are never sent downstream to drafting agents."),
        _section("24. Missing information (aggregate)", unconfirmed_rows + [{"item": t, "value": "Unsupported term — excluded from handoff."} for t in unsupported_terms],
                 ["item", "value"], "Every unresolved item blocks a specific downstream decision; nothing is silently filled."),
        _section("25. Inventor confirmation & signatures", [
            {"check": "Inventor identities and contributions recorded", "status": "Pending"},
            {"check": "Applicant / owner confirmed", "status": "Pending"},
            {"check": "Technical detail complete (no [TO BE CONFIRMED] remaining)", "status": "Pending"},
            {"check": "Evidence and results attached", "status": "Pending"},
            {"check": "Public-disclosure timeline recorded", "status": "Pending"},
            {"check": "Inventor signatures and dates", "status": "[INVENTOR INPUT REQUIRED]"},
        ], ["check", "status"], "The record becomes inventor-confirmed only when every box is complete."),
        _section("26. Interpretation panel (confirm & edit)", [
            {"dimension": "Subject", "value": f"{botanicals[:90]} composition and preparation" if botanicals else "[TO BE CONFIRMED]"},
            {"dimension": "Application", "value": (f"Formulated as {inv['dosage_form']} for oral administration — [intended-use context to confirm]."
                                                   if not dosage_generic else "Intended use context [INVENTOR INPUT REQUIRED]")},
            {"dimension": "Mechanism", "value": ("Hydroalcoholic extraction and standardisation chain " + (solvent or "")) if steps_known or solvent_known else "[NOT ESTABLISHED]"},
            {"dimension": "Outcome", "value": f"{effect_statement or '[INVENTOR INPUT REQUIRED]'} — Inventor-stated advantage; objective evidence not yet attached."},
            {"dimension": "Essential features", "value": ", ".join(confirmed_names[:4]) if ingredients_known else "[NOT CONFIRMED] — essentiality decided with the inventor"},
            {"dimension": "Technical effect status", "value": "Measured / Preliminary / Hypothesis / Not established → currently 'Preliminary'" if not markers_known else "Measurements indicated; evidence pending"},
        ], ["dimension", "value"], "The panel only converts confirmed information into interpretation — never 'advantages recorded' into a confirmed effect."),
        _section("Required disclaimer", [
            {"item": "Legal status", "value": "This invention disclosure is a technical and administrative record, not a patent application or legal opinion. "
                                            "Inventorship, ownership, confidentiality, public-disclosure impact, novelty, inventive step, "
                                            "traditional-knowledge provisions, biological-material requirements, regulatory classification and "
                                            "claim scope require review by qualified professionals before filing or commercial disclosure."},
        ], ["item", "value"], "End of disclosure record."),
    ]
    return result
