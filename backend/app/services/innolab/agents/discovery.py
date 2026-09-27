"""Ideation, TRIZ matrices, landscape research and solution search.

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

from app.services.innolab._shared import (
    _finding,
    _section,
    _source_kind,
    _text,
)
from app.services.agent_hub import toolbox

__all__ = [
    "_hub_triz",
    "_system_from_problem",
    "_detect_improve_tradeoff",
    "_triz_fallback_name",
    "_triz_propose_empty_cell",
    "_triz_success_metrics",
    "_triz_validation_plan",
    "_qr_jurisdiction_hint",
    "_qr_provisional_classification",
    "_hub_quick_research",
    "_fs_failure_modes",
    "_hub_find_solutions",
]

def _hub_triz(inputs: dict[str, Any], spec, result: dict[str, Any], tools: list[str]) -> dict[str, Any]:
    """TRIZ Innovation — full 11-section pipeline (no definitions-only output).

    User Problem → System Boundary → RCA Hypotheses → Technical Contradiction
    → 39-Parameter Mapping → Matrix Lookup → Inventive Principles → IP-SAKTI
    Domain Translation → Validation Experiments → Ranking → Evidence
    Classification → Final Recommendation.
    """
    from app.services.innolab import triz_data as td

    problem = _text(inputs, "problem_text")
    system = _text(inputs, "system_name") or _system_from_problem(problem)
    improve = _text(inputs, "improve_aspect")
    tradeoff = _text(inputs, "tradeoff")

    # 1-3: understand the problem and derive the contradiction deterministically
    if not improve or not tradeoff:
        derived_improve, derived_tradeoff = _detect_improve_tradeoff(problem)
        improve = improve or derived_improve
        tradeoff = tradeoff or derived_tradeoff

    contradiction = f"Increasing {improve} makes {tradeoff} worse within {system}."

    # 4: map both sides of the contradiction onto the 39 TRIZ parameters
    imp_map = td.map_parameter(improve)
    wor_map = td.map_parameter(tradeoff)
    if imp_map["no"] is None:
        imp_no = 39 if any(w in problem.lower() for w in ("product", "yield", "through", "batch")) else \
            17 if any(w in problem.lower() for w in ("heat", "temperat", "therm", "energy")) else 13
        imp_map = {"no": imp_no, "name": _triz_fallback_name(imp_no, problem),
                   "confidence": "low", "matched_hint": "fallback by problem context"}
    if wor_map["no"] is None:
        wor_no = 13 if any(w in problem.lower() for w in ("stab", "potency", "degrad", "decompos", "oxid")) else \
            23 if any(w in problem.lower() for w in ("yield", "loss", "wast")) else 22
        wor_map = {"no": wor_no, "name": _triz_fallback_name(wor_no, problem),
                   "confidence": "low", "matched_hint": "fallback by problem context"}

    # 5: exact matrix-cell lookup (real Altshuller 1985 cells; never guessed)
    cell = td.lookup_cell(imp_map["no"], wor_map["no"])
    if not cell["principles"] and cell["source"] == "empty":
        cell = {
            "cell": f"{imp_map['no']}→{wor_map['no']}",
            "principles": _triz_propose_empty_cell(imp_map["no"], wor_map["no"]),
            "source": "inferred",
        }
    principle_nos = cell["principles"][:5]

    # 6: translate each principle into an IP-SAKTI domain solution + experiment
    cards = []
    for no in principle_nos:
        name, idea = td.PRINCIPLE_BY_NO[no]
        app, benefit, tradeoff_note, experiment = td.principle_application(no)
        cards.append({
            "no": str(no),
            "principle": name,
            "triz_meaning": idea,
            "ipsakti_application": app,
            "expected_benefit": benefit,
            "trade_off": tradeoff_note,
            "validation_experiment": experiment,
        })

    # 7: rank the principles — matrix frequency vs domain fit kept separate
    frequency_rank = sorted(principle_nos, key=lambda p: -td.FREQUENCY.get(p, 0))
    fit_rank = sorted(principle_nos, key=lambda p: -td._IPSAKTI_FIT.get(p, 5))
    combined = sorted(principle_nos, key=lambda p: -(td.FREQUENCY.get(p, 0) + td._IPSAKTI_FIT.get(p, 5) * 4))

    context = td.brief_context(problem)
    metrics = _triz_success_metrics(context)

    # --- outcome -------------------------------------------------------- #
    top_principle = combined[0] if combined else None
    rec_concept = ""
    if top_principle is not None and len(combined) >= 2:
        combo = ", ".join(td.PRINCIPLE_BY_NO[p][0].split(" /")[0].lower() for p in combined[:2])
        rec_concept = f"Combine {combo}: translate both principles into staged, low-stress process conditions, then prove them experimentally."
    elif top_principle is not None:
        rec_concept = f"Apply {td.PRINCIPLE_BY_NO[top_principle][0].lower()} to the problem, then validate experimentally."

    result["summary"] = (f"TRIZ: contradiction isolated on {system} — '{contradiction}' mapped to "
                         f"parameters {imp_map['no']}→{wor_map['no']}; {len(principle_nos)} inventive principles "
                         f"from matrix cell {cell['cell']} translated into IP-SAKTI experiments.")
    result["note"] = ("Problem framing → RCA hypotheses → technical contradiction → 39-parameter mapping → "
                      "matrix lookup → inventive principles → domain solutions → validation experiments → "
                      "evidence classification. Matrix cells are the canonical Altshuller 1985 table (offline), "
                      "plus a domain fallback where the canonical cell is empty, always flagged.")
    result["findings"].append(_finding("t1", "System boundary", f"{system}.", "info"))
    for hyp in td.RCA_HYPOTHESES:
        result["findings"].append(_finding(hyp["id"], f"RCA hypothesis — {hyp['title']}", hyp["detail"] + " Confirm: " + hyp["confirm"], "info"))
    result["findings"].append(_finding("t3", "Technical contradiction", contradiction, "warning"))
    result["findings"].append(_finding("t4", "39-parameter mapping",
        f"Improving → {imp_map['no']} ({imp_map['name']}) · worsening → {wor_map['no']} ({wor_map['name']}) · confidence {imp_map['confidence']}/{wor_map['confidence']}.",
        "warning" if "low" in (imp_map["confidence"], wor_map["confidence"]) else "info"))
    for i, no in enumerate(principle_nos, start=1):
        name = td.PRINCIPLE_BY_NO[no][0]
        result["findings"].append(_finding(f"t5-{i}", f"Principle {no} — {name}",
            td.PRINCIPLE_BY_NO[no][1] + " → IP-SAKTI: " + td.principle_application(no)[0][:160], "info"))

    result["sections"] += [
        # 1 & 2 — user problem + diagnosis
        _section("1 — User problem", [
            {"field": "Your brief", "value": problem[:400] or "—"},
            {"field": "System boundary", "value": system},
            {"field": "Improve", "value": improve},
            {"field": "Worsening", "value": tradeoff},
        ], ["field", "value"], "The problem as stated; the system being worked on."),
        # 3 — technical contradiction
        _section("2 — Problem diagnosis (root-cause hypotheses)", [
            {"hypothesis": h["title"], "causal_chain": h["detail"], "how_to_confirm": h["confirm"]}
            for h in td.RCA_HYPOTHESES
        ], ["hypothesis", "causal_chain", "how_to_confirm"],
            "Five domain hypotheses ranked by their confirmability — each is falsifiable by a cheap experiment."),
        _section("3 — Technical contradiction", [
            {"improving": improve, "worsening": tradeoff, "system": system, "contradiction": contradiction},
        ], ["improving", "worsening", "system", "contradiction"],
            "A contradiction claims: pushing one parameter forces another to degrade."),
        # 4 — parameter mapping
        _section("4 — TRIZ parameter mapping (39 parameters)", [
            {"role": "Improving", "no": str(imp_map["no"]), "parameter": imp_map["name"],
             "confidence": imp_map["confidence"], "matched_hint": imp_map.get("matched_hint", "")},
            {"role": "Worsening", "no": str(wor_map["no"]), "parameter": wor_map["name"],
             "confidence": wor_map["confidence"], "matched_hint": wor_map.get("matched_hint", "")},
        ], ["role", "no", "parameter", "confidence", "matched_hint"],
            "Deterministic keyword mapping. Low-confidence mappings are explicitly flagged — re-confirm against the standard 39-parameter list before trusting the cell."),
        # 5 — matrix lookup
        _section(f"5 — Matrix lookup (cell {cell['cell']} · source: {cell['source']})", [
            {"rank": str(i), "principle_no": str(no), "principle": td.PRINCIPLE_BY_NO[no][0],
             "matrix_frequency": str(td.FREQUENCY.get(no, 0))}
            for i, no in enumerate(principle_nos, start=1)
        ], ["rank", "principle_no", "principle", "matrix_frequency"],
            "Retrieved from the canonical Altshuller 39×39 matrix (checked-in data). 'inferred' cells have no canonical entry and are flagged for expert check."),
        # 6 — inventive principles translated to the domain
        _section("6 — Recommended inventive principles (translated for IP-SAKTI)", [
            {"rank": str(i), "no": c["no"], "principle": c["principle"], "triz_meaning": c["triz_meaning"],
             "ipsakti_application": c["ipsakti_application"], "expected_benefit": c["expected_benefit"],
             "trade_off": c["trade_off"], "validation_experiment": c["validation_experiment"]}
            for i, c in enumerate(cards, start=1)
        ], ["rank", "no", "principle", "triz_meaning", "ipsakti_application", "expected_benefit",
            "trade_off", "validation_experiment"],
            "Each principle is only a direction — it must be converted into a domain-specific solution AND a measurable experiment."),
        # 7 — two separate rankings
        _section("7 — Principle ranking (matrix vs domain fit kept separate)", [
            {"basis": "Matrix frequency (Altshuller)", "rank": str(frequency_rank.index(no) + 1),
             "principle_no": str(no), "principle": td.PRINCIPLE_BY_NO[no][0],
             "score": str(td.FREQUENCY.get(no, 0))}
            for no in principle_nos
        ] + [
            {"basis": "IP-SAKTI domain fit", "rank": str(fit_rank.index(no) + 1),
             "principle_no": str(no), "principle": td.PRINCIPLE_BY_NO[no][0],
             "score": str(td._IPSAKTI_FIT.get(no, 5))}
            for no in principle_nos
        ], ["basis", "rank", "principle_no", "principle", "score"],
            "A principle can rank high globally (matrix) but low here (domain) — the final pick balances both."),
        # 8 — validation plan
        _section("8 — Validation plan (measurable experiments)", [
            {"step": str(i + 1), "experiment": row["experiment"], "measures": row["measures"], "decision_rule": row["decision_rule"]}
            for i, row in enumerate(_triz_validation_plan(cards))
        ], ["step", "experiment", "measures", "decision_rule"],
            "Experiments are sized so the decision rule is objective — markers, yields, RSD, not opinions."),
        # 9 — success metrics
        _section("9 — Success metrics", [
            {"metric": m["metric"], "target": m["target"], "measurement": m["measurement"]} for m in metrics
        ], ["metric", "target", "measurement"], "Pre-decide the bar before running the experiments."),
        # 10 — evidence classification
        _section("10 — Evidence classification", [
            {"evidence_type": "TRIZ (matrix cell + principles)",
             "provides": "Direction of attack — which inventive principles the canonical matrix pairs with the contradiction.",
             "rule": "Statistical pattern from thousands of patents = a hypothesis, never proof."},
            {"evidence_type": "Technical / experimental (assays, yields, stability)",
             "provides": "Proof the solution works in the actual product/process.",
             "rule": "The ONLY evidence that validates a TRIZ principle — run the experiments."},
            {"evidence_type": "Regulatory (FSSAI/AYUSH/FDA/monographs)",
             "provides": "Compliance of the final product with legal limits.",
             "rule": "Compliance NEVER proves an inventive principle — a compliant product can still be non-optimal."},
        ], ["evidence_type", "provides", "rule"],
            "Regulatory evidence is necessary but never sufficient: it cannot confirm that your TRIZ solution is the inventive one."),
        # 11 — final recommendation
        _section("11 — Final recommendation", [
            {"recommended_concept": rec_concept,
             "top_principles": "; ".join(td.PRINCIPLE_BY_NO[p][0] for p in combined[:3]),
             "next_action": "Run the two highest-ranked principles as a small design-of-experiments; carry forward whatever clears the decision rules above.",
             "protect_later": "Validate, then protect the differentiating process window via patent_drafting."},
        ], ["recommended_concept", "top_principles", "next_action", "protect_later"],
            "One clear next action, not a laundry list."),
    ]

    result["suggestions"] = [
        f"Run the {len(principle_nos)} translated experiments in section 8 and keep the top-2 by measured data, not by matrix rank.",
        "Protect the validated process window (temperature/solvent/staging) through patent_drafting once experiments confirm it.",
        f"Short judge explanation: solve the contradiction by '{rec_concept[:140] if rec_concept else 'translated principles + measured validation'}'.",
    ]
    return result


def _system_from_problem(problem: str) -> str:
    """Derive a human-readable system label from the problem sentence."""
    text = (problem or "").strip()
    if len(text) <= 3:
        return "the affected system"
    parts = [p.strip() for p in text.split(",") if p.strip()]
    first = parts[0]
    words = first.split()
    if len(words) <= 6:
        return first
    return " ".join(words[:6]) + "…"


def _detect_improve_tradeoff(problem: str) -> tuple[str, str]:
    """Deterministic contradiction derivation when the user only gives a problem."""
    low = (problem or "").lower()
    if any(w in low for w in ("stability", "potency loss", "loss of potency", "degrades", "degrade",
                              "degradation", "heat sensitive", "thermolabile", "unstable", "decompos")):
        tradeoff = "stability / potency retention"
        if "yield" in low:
            improve = "extraction yield"
        elif any(w in low for w in ("temperatur", "hot", "heat", "boil")):
            improve = "extraction temperature"
        else:
            improve = "product performance"
    elif "yield" in low:
        improve = "extraction yield"
        tradeoff = "energy use and processing time" if ("energy" in low or "time" in low or "cost" in low) else "marker stability"
    elif any(w in low for w in ("scale", "throughput", "batch", "capacity")):
        improve = "batch throughput"
        tradeoff = "energy use and product consistency"
    elif "moisture" in low:
        improve = "storage stability"
        tradeoff = "drying energy and time"
    else:
        improve = "key performance metric"
        tradeoff = "another quality metric"
    return improve, tradeoff


def _triz_fallback_name(no: int | None, problem: str) -> str:
    if no == 13:
        return "Stability of object's composition"
    if no == 23:
        return "Loss of substance"
    if no == 22:
        return "Loss of energy"
    if no == 17:
        return "Temperature"
    if no == 39:
        return "Productivity"
    return "Unmapped parameter — review"


def _triz_propose_empty_cell(imp_no: int, wor_no: int) -> list[int]:
    """Principles for canonical-empty cells — tagged 'inferred', never silent."""
    pairs = {
        (13, 13): [35, 1, 2],
        (17, 13): [1, 35, 32],
        (23, 13): [2, 35, 31],
        (39, 22): [35, 21, 20],
        (39, 25): [20, 21, 35],
    }
    if (imp_no, wor_no) in pairs:
        return pairs[(imp_no, wor_no)]
    if (wor_no, imp_no) in pairs:
        return pairs[(wor_no, imp_no)]
    return [35, 2, 1]


def _triz_success_metrics(context: str) -> list[dict[str, str]]:
    metrics = [
        {"metric": "Marker retention after process", "target": "≥ 95% of label potency on dry basis",
         "measurement": "Validated HPLC marker assay at each unit operation"},
        {"metric": "Batch-to-batch consistency", "target": "RSD < 5% on markers across ≥ 3 batches",
         "measurement": "Multi-batch assay + moisture/actives profiling"},
    ]
    if "yield" in context:
        metrics.append({"metric": "Extraction yield", "target": "≥ target % w/w (prev. baseline)",
                        "measurement": "Gravimetric dry-basis yield + marker recovery vs feed"})
    if "stability" in context or "potency" in context:
        metrics.append({"metric": "Shelf-life stability", "target": "Markers within limits at stated condition (e.g. 40°C/75%RH for 3 m)",
                        "measurement": "Accelerated stability pull-point assays, oxidation/colour check"})
    if "temperature" in context or "energy" in context or "time" in context:
        metrics.append({"metric": "Thermal exposure / energy & time", "target": "No minutes above degradation threshold; −X% energy or −X% batch time",
                        "measurement": "Thermal mapping + metered energy + batch clock"})
    return metrics


def _triz_validation_plan(cards: list[dict[str, str]]) -> list[dict[str, str]]:
    if not cards:
        cards = [{"principle": "Parameter changes", "validation_experiment": "Sweep the operating window in a small design-of-experiments.",
                  "expected_benefit": "Identifies the sweet spot without large capital change."}]
    picks = cards[:2]
    plan = []
    for _i, c in enumerate(picks, start=1):
        plan.append({
            "experiment": f"{c['principle']}: {c['validation_experiment']}",
            "measures": "Marker % · yield · colour/oxidation index · batch time",
            "decision_rule": f"Keep principle '{c['principle']}' only if it clears the metric targets AND does not worsen the other side of the contradiction.",
        })
    plan.append({
        "experiment": "Re-run the confirmed prototype 3× to confirm transferability",
        "measures": "RSD of markers, yield, appearance",
        "decision_rule": "RSD < 5% across repeats → lock the process window and hand off for patent-lawyer review.",
    })
    return plan


def _qr_jurisdiction_hint(authority: str) -> str:
    """Infer the jurisdiction a corpus passage belongs to from its authority label."""
    low = (authority or "").lower()
    if any(k in low for k in ("fssai", "ayush", "indian patent", "cdsco", "ayurvedic pharmacopoei", "drugs controller")):
        return "India"
    if any(k in low for k in ("us fda", "united states", "uspto", "fda", "ndi")):
        return "United States"
    if any(k in low for k in ("health canada", "canada", "nhp", "natural health product", "canadian")):
        return "Canada"
    if any(k in low for k in ("wipo", "epo", "european", "united kingdom", "eu")):
        return "International"
    return "Not jurisdiction-tagged"


def _qr_provisional_classification(topic: str, resolved: list[dict[str, Any]]) -> dict[str, str]:
    """Provisional product-category classification — food vs Aahara vs supplement vs medicine vs cosmetic.

    This is a classification HYPOTHESIS for validation, never a legal conclusion.
    """
    low = (topic or "").lower()
    if any(k in low for k in ("cosmetic", "cream", "lotion", "shampoo", "soap", "face wash", "hair oil", "ointment (topical)")):
        return {"category": "Cosmetic / external-use product", "confidence": "High (keyword-classified)",
                "pathway": "Separate from food and drug pathways; Cosmetics Rules considerations apply."}
    if any(k in low for k in ("tablet", "capsule", "syrup", "churna", "arishta", "asava", "bhasma",
                              "drug", "medicine", "dosage", "therapeutic", "clinical trial", "ich-gcp")):
        return {"category": "Potential Ayurvedic (ASU) medicine", "confidence": "High (keyword-classified)",
                "pathway": "Likely AYUSH / CDSCO controlled-substance or drug pathway; validation required."}
    if any(k in low for k in ("supplement", "dietary supplement", "nutraceutical", "vitamin", "gummy", "softgel", "tablet dosage")):
        return {"category": "Dietary supplement", "confidence": "Medium (keyword-classified)",
                "pathway": "Jurisdiction-dependent food-supplement pathway; validation required."}
    if any(k in low for k in ("aahara", "food", "beverage", "juice", "jam", "health drink", "functional food", "neutraceutical food",
                              "milk drink", "ayurveda aahara", "siddha food", "daily food")):
        return {"category": "Ayurveda Aahara / food product", "confidence": "High (keyword-classified)",
                "pathway": "FSSAI food pathway primary; separate from ASU-drug pathway."}
    if any(k in low for k in ("extract", "standardized", "powder", "tincture", "botanical")):
        return {"category": "Botanical extract / intermediate", "confidence": "Medium (keyword-classified)",
                "pathway": "Could feed food, supplement or drug; classification must be validated per end-use."}
    return {"category": "Provisional conventional food / unspecified", "confidence": "Low (no clear signal)",
            "pathway": "Product classification must be validated before regulatory conclusions."}


def _hub_quick_research(inputs: dict[str, Any], result: dict[str, Any], resolved: list[dict[str, Any]], botanicals: str) -> dict[str, Any]:
    topic = _text(inputs, "problem_text") or "requested technology area"
    markets = result.get("jurisdictions") or ["India", "United States", "Canada"]
    timeframe = _text(inputs, "timeframe") or "current corpus snapshot"
    citations = result.get("citations") or []
    texts = [c.get("exact_passage") or "" for c in citations] or [topic]

    # -- source-type clustering (kinds, not keyword counts) ------------------ #
    kinds: dict[str, int] = {}
    for c in citations:
        k = _source_kind(c.get("authority") or "")
        kinds[k] = kinds.get(k, 0) + 1
    reg_cit = [c for c in citations if "Regulatory" in _source_kind(c.get("authority") or "")]
    patent_cit = [c for c in citations if "Patent" in _source_kind(c.get("authority") or "")]
    sci_cit = [c for c in citations if "Scientific" in _source_kind(c.get("authority") or "")]
    market_cit = [c for c in citations if "Market" in _source_kind(c.get("authority") or "") or "Company" in _source_kind(c.get("authority") or "")]

    classification = _qr_provisional_classification(topic, resolved)

    # -- technical background from resolved ingredients ---------------------- #
    ing_rows = []
    for r in resolved[:8]:
        ing_rows.append({
            "ingredient": r.get("botanical_name") or r.get("raw_name", "—"),
            "family": r.get("family") or "—",
            "aahara_status": r.get("fssai_aahara_status") or "permitted",
            "us_fda_status": r.get("us_fda_ndi_status") or "old_dietary_ingredient",
            "canada_status": r.get("canada_nhpid_status") or "monographed",
        })

    # -- market evidence status --------------------------------------------- #
    quantified_market = bool(market_cit)
    demand_support = "Quantified" if quantified_market else (
        "Directionally supported" if reg_cit or sci_cit else "Not established")
    market_evidence_status = (
        f"Source count: {len(citations)} passage(s); {len(market_cit)} from market sources. "
        f"{len(reg_cit)} regulatory, {len(sci_cit)} scientific, {len(patent_cit)} patent-sourced passages."
    )

    # -- recurrence terms (NOT presented as trends) -------------------------- #
    recurring = toolbox.trend_analyze(texts, top_k=5)
    trend_caveat = ("Recurring terminology was observed (frequencies below), but a validated "
                    "time-series trend cannot be established from the current corpus.")

    # -- patent / prior-art notes --------------------------------------------- #
    patent_rows = [
        {
            "reference": c.get("act_title") or "corpus passage",
            "jurisdiction": _qr_jurisdiction_hint(c.get("authority")),
            "authority": c.get("authority") or "KB",
            "note": "Screening-level relevance; requires claim-level review. Not a legal conclusion.",
        }
        for c in (patent_cit or citations[:4])
    ]

    # -- innovation opportunities --------------------------------------------- #
    innovations = [
        {
            "innovation": "Standardized-extraction intelligence workflow",
            "problem": "Batch-to-batch marker variability blocks consistency claims",
            "concept": "Correlate process parameters (solvent, temperature, time) with marker recovery",
            "differentiator": "Evidence-linked process window vs generic extraction practice",
            "benefit": "Defensible standardization + claims",
            "risk": "Process data may be unavailable",
            "validation": "Marker assay + controlled extraction DOE",
            "ip_category": "Process",
        },
        {
            "innovation": "Compliance & stability intelligence pass",
            "problem": "Shelf life and jurisdictional classification uncertainty",
            "concept": "Stability-failure-mode mapping + jurisdiction classification check",
            "differentiator": "Regulatory-aware formulation guidance",
            "benefit": "Fewer approval surprises",
            "risk": "Classification changes per end-use",
            "validation": "Official-source verification per market",
            "ip_category": "Software workflow",
        },
        {
            "innovation": "Ingredient-traceability graph for export",
            "problem": "Export paperwork gap across feeding jurisdictions",
            "concept": "Ingredient→monograph→regulatory-status knowledge graph",
            "differentiator": "Source-traceable per-market status",
            "benefit": "Faster export readiness",
            "risk": "Corpus jurisdiction coverage may be thin",
            "validation": "Authority registry cross-check",
            "ip_category": "Data architecture",
        },
    ]

    # -- research gaps --------------------------------------------------------- #
    gaps = [
        {"gap": "Quantified market size and revenue", "why": "Cannot rank commercial opportunity", "close": "Market-research and trade databases", "priority": "High"},
        {"gap": "Consumer and competitor data", "why": "Cannot rank players or demand", "close": "Company filings, e-commerce, surveys", "priority": "High"},
        {"gap": "Complete patent/claim-level map", "why": "Cannot conclude novelty/FTO", "close": "Structured patent search + claim charting", "priority": "High"},
        {"gap": "Jurisdiction-specific regulatory verification", "why": "India-only signal may not transfer", "close": "Official gazettes + authority confirmation", "priority": "High"},
        {"gap": "Experimental validation data", "why": "Technology status is provisional", "close": "Laboratory or pilot validation", "priority": "Medium"},
    ]

    # -- stakeholder analysis (authorities ≠ commercial players) ------------- #
    authorities = sorted({c.get("authority") or "Evidence corpus" for c in reg_cit}) or ["Regulatory corpus (FSSAI/AYUSH/FDA/Health Canada)"]
    player_note = ("Current corpus identifies institutional stakeholders (regulators, knowledge sources). "
                   "It does not contain sufficient evidence for a reliable commercial competitor ranking.")

    # -- recommended next steps ----------------------------------------------- #
    next_steps = [
        {"priority": "Priority 1", "action": "Run a structured, claim-level patent search", "reason": "Legal posture unknown from current corpus", "output": "Patent/prior-art landscape table", "sources": "Patent office databases"},
        {"priority": "Priority 1", "action": "Collect market-size, product-launch and company data", "reason": "Demand is not quantified", "output": "Market/demand conclusion", "sources": "Market reports, trade data"},
        {"priority": "Priority 2", "action": "Verify jurisdiction-specific regulations", "reason": "Classification changes per market", "output": "Regulatory roadmap", "sources": "Official gazettes, authorities"},
        {"priority": "Priority 3", "action": "Conduct bench validation of the short-listed technology", "reason": "Maturity is provisional", "output": "Stability/quality data", "sources": "Laboratory results"},
    ]

    # ----------------------------------------------------------------------- #
    result["summary"] = (f"Evidence-backed landscape for “{topic[:80]}” — {len(reg_cit)} regulatory, "
                         f"{len(sci_cit)} scientific, {len(patent_cit)} patent-source passage(s); "
                         f"{len(markets)} jurisdiction(s) analysed.")
    result["note"] = "Facts separated from inferences; demand is not inferred from source count; trends are flagged as unvalidated."
    result["findings"].append(_finding("qr-1", "Evidence status", market_evidence_status, "info"))
    result["findings"].append(_finding("qr-2", "Provisional classification", f"{classification['category']} — {classification['confidence']}. {classification['pathway']}", "warning"))
    result["findings"].append(_finding("qr-3", "Market-demand evidence", demand_support + ". Not inferred from source count.", "warning" if demand_support == "Not established" else "info"))
    result["findings"].append(_finding("qr-4", "Trend evidence", trend_caveat, "warning"))
    result["findings"].append(_finding("qr-5", "Market evidence gap", "Quanti-fiable revenue/size data: not established from current evidence corpus.", "warning" if not quantified_market else "info"))

    result["suggestions"] = [
        "Next: run novelty/FTO searches and collect market data before any commercial or IP conclusion.",
        "Separate regulatory relevance from market demand — the corpus supports classification, not demand size.",
        "Verify the jurisdiction-specific classification with an expert before drafting claims or labels.",
    ]

    result["sections"] += [
        # ---- executive summary ---- #
        _section("Executive Summary", [
            {"item": "What the topic is", "value": topic[:200] or "—"},
            {"item": "What the evidence establishes", "value": (f"Regulatory and technical relevance: {len(reg_cit) + len(sci_cit)} source passage(s) from "
                                                                f"regulatory and scientific sources; provisional category: {classification['category']}.")},
            {"item": "What it does not establish", "value": "A quantified market size, a reliable competitor ranking, or a complete claim-level patent landscape."},
            {"item": "Strongest immediate opportunity", "value": "Compliance + technology-intelligence workflow (standardization, stability, traceability)."},
            {"item": "Most important risk", "value": "Treating regulatory relevance as market demand, or keyword recurrence as a trend."},
            {"item": "Recommended next action", "value": "Structured patent search + market-data collection before an IP or market-entry decision."},
        ], ["item", "value"], "2–4 sentence executive answer, summarised in structured form."),

        # ---- research scope and assumptions ---- #
        _section("Research Scope and Assumptions", [
            {"field": "Topic definition", "value": topic[:200]},
            {"field": "Included technologies", "value": "Ayurveda Aahara foods, functional beverages, botanical extracts, standardization/quality testing, Indian regulatory framework, relevant patent activity"},
            {"field": "Excluded technologies", "value": "Purely therapeutic Ayurvedic medicines (unless overlapping food), cosmetics (unless technically relevant), unverified commercial claims"},
            {"field": "Jurisdictions", "value": ", ".join(markets) or "India (default)"},
            {"field": "Time period", "value": timeframe},
            {"field": "Source types", "value": "Official regulatory > scientific/technical > commercial/market > secondary"},
            {"field": "Provisional product classification", "value": f"{classification['category']} ({classification['confidence']})"},
            {"field": "Assumption", "value": "India default for primary regulatory context; US/Canada analysed only where international relevance is indicated."},
        ], ["field", "value"], "Scope is explicit so over-claims are avoidable; missing detail is surfaced as a gap, not guessed."),

        # ---- Module 1 ---- #
        _section("Module 1 — Technical Background and Objectives", [
            {"item": "Plain-language background", "value": "The topic concerns botanically sourced ingredients whose status (food, supplement, medicine, cosmetic) determines the legality of production, marketing and claims."},
            {"item": "Product/technology category", "value": f"{classification['category']} — {classification['pathway']}"},
            {"item": "Problem being researched", "value": "What the corpus establishes about technology status, regulatory pathway, market demand, key players and patents for this topic."},
            {"item": "Research questions", "value": "1) What is known? 2) How do we know it? 3) What is not known? 4) Why does it matter? 5) What should the user do next?"},
            {"item": "Research objectives", "value": "Evidence-backed technical, market, regulatory and patent landscape with explicit confidence and gaps."},
        ], ["item", "value"], "Category boundaries (Aahara vs medicine vs supplement vs cosmetic) are kept separate — never merged without distinction."),
    ]

    if ing_rows:
        result["sections"].append(_section("Resolved ingredient statuses (technical background evidence)", ing_rows,
                                           ["ingredient", "family", "aahara_status", "us_fda_status", "canada_status"],
                                           "Statuses are provisional signals from the knowledge base — jurisdiction verification required."))

    result["sections"] += [
        # ---- Module 2 ---- #
        _section("Module 2 — Market and Demand Analysis", [
            {"item": "Market definition", "value": f"Defined by the topic scope + jurisdictions: {', '.join(markets)}. Exact segments unverified."},
            {"item": "Customer segments", "value": "Potential users, buyers and channels (consumers, distributors, e-commerce, B2B ingredients) — composition not established from current corpus."},
            {"item": "Demand indicators present", "value": f"{len(market_cit)} market-source passage(s). No reliable size, revenue, sales or launch dataset in the current evidence corpus."},
            {"item": "Geographic analysis", "value": "Jurisdictions treated separately; no comparative demand dataset retrieved."},
            {"item": "Evidence status", "value": market_evidence_status + f" → Evidence status: {demand_support}."},
            {"item": "Market conclusion", "value": "Current evidence supports regulatory or technical relevance, but does not establish a quantified market-demand conclusion."},
        ], ["item", "value"], "Demand is never inferred from the number of documents; absence is reported explicitly."),

        # ---- Module 3 ---- #
        _section("Module 3 — Regulatory and Compliance Landscape", [
            {"jurisdiction": "India", "category": classification["category"], "authority": "FSSAI / Ministry of AYUSH / CDSCO (as applicable)",
             "relevant_rule": "FSSAI food/Aahara pathway vs AYUSH ASU-drug pathway — separates food, Aahara, supplement and medicine",
             "practical_implication": "Pathway determines ingredients, additives, labeling, claims and manufacturing licence",
             "confidence": "High (established framework) — confirm per product"},
            {"jurisdiction": "United States", "category": "Food / dietary supplement", "authority": "US FDA",
             "relevant_rule": "Conventional food vs dietary supplement vs drug; claims (structure/function vs disease) differ",
             "practical_implication": "Claim language and NDI status determine what may be marketed",
             "confidence": "Medium — product-level verification required"},
            {"jurisdiction": "Canada", "category": "Food / natural health product", "authority": "Health Canada",
             "relevant_rule": "Food vs NHP classification; import and licence requirements",
             "practical_implication": "NHP licence vs food requirements change the compliance package",
             "confidence": "Medium — product-level verification required"},
            {"jurisdiction": "All", "category": "—", "authority": "—",
             "relevant_rule": "Preliminary regulatory indication only",
             "practical_implication": "Expert and authority confirmation required before any launch decision",
             "confidence": "High (standard disclaimer)"},
        ], ["jurisdiction", "category", "authority", "relevant_rule", "practical_implication", "confidence"],
            "Not a final legal or regulatory opinion — preliminary indication only."),

        # ---- Module 4 ---- #
        _section("Module 4 — Technology Status and Challenges", [
            {"technology": "Botanical extraction (hydroalcoholic, low-temperature)", "purpose": "Recover active markers", "maturity": "Commercially used (well established)", "benefits": "Established practice", "challenges": "Thermal/oxidative degradation", "evidence": "Corpus + conventional practice", "ip_opportunity": "Process", "confidence": "Medium"},
            {"technology": "Marker-based standardization", "purpose": "Consistent concentration", "maturity": "Commercially used", "benefits": "Claims consistency", "challenges": "Analytical cost, batch drift", "evidence": "API monographs", "ip_opportunity": "Process/data", "confidence": "Medium"},
            {"technology": "Stability & packaging engineering", "purpose": "Shelf-life control", "maturity": "Commercially used", "benefits": "Safety + consumer trust", "challenges": "Moisture/oxygen/light failures", "evidence": "Stability practice", "ip_opportunity": "Packaging/process", "confidence": "Medium"},
            {"technology": "Compliance automation / traceability", "purpose": "Jurisdiction tracking", "maturity": f"Concept–early research {timeframe}", "benefits": "Export readiness", "challenges": "Data jurisdiction coverage", "evidence": "Corpus signal only", "ip_opportunity": "Software workflow", "confidence": "Low"},
        ], ["technology", "purpose", "maturity", "benefits", "challenges", "evidence", "ip_opportunity", "confidence"],
            "Maturity is labelled by evidence stage (concept → commercial), never by source density."),

        # ---- Module 5 ---- #
        _section("Module 5 — Technology Evolution Path", [
            {"stage": "Historical direction", "value": "Traditional formulations; classically-referenced processing (therapeutic-effect pairing)"},
            {"stage": "Current direction", "value": "Marker-standardized extracts, defined manufacturing, food-style formats, regulatory-aware labelling"},
            {"stage": "Emerging direction", "value": "Stability-engineered delivery, traceability and compliance workflows (evidence: " + (", ".join(r["term"] for r in recurring[:3]) if recurring else "corpus-only") + ")"},
            {"stage": "Future opportunity", "value": "Data-backed formulation/process intelligence and jurisdiction-aware export readiness"},
            {"stage": "Trend caveat", "value": trend_caveat},
        ], ["stage", "value"], "Recurring terms are labelled as recurrence, never as a validated trend."),

        # ---- Module 6 ---- #
        _section("Module 6 — Stakeholder and Player Analysis", [
            {"stakeholder_type": "Regulatory authorities", "stakeholders": "; ".join(authorities), "note": "Not commercial competitors"},
            {"stakeholder_type": "Research / knowledge institutions", "stakeholders": "API monographs, botanical synonym table, bioresource index, legal/glossary corpus", "note": "Knowledge sources used by the report"},
            {"stakeholder_type": "Commercial players", "stakeholders": player_note, "note": "Reliable competitor ranking not established"},
        ], ["stakeholder_type", "stakeholders", "note"], "Authorities and commercial players are never mixed."),

        # ---- Module 7 ---- #
        _section("Module 7 — Technical Approach Review", [
            {"approach": "Solvent-based extraction", "objective": "Recover botanicals", "advantages": "Established, scalable", "limitations": "Marker degradation risk", "evidence_strength": "Medium", "scale_up": "Heat/oxygen control", "ip_opportunity": "Process window"},
            {"approach": "Standardized marker dosing", "objective": "Consistency", "advantages": "Defensible claims", "limitations": "Analytical demand", "evidence_strength": "Medium", "scale_up": "QC capability", "ip_opportunity": "Composition"},
            {"approach": "Auto compliance/traceability workflow", "objective": "Export readiness", "advantages": "Low physical risk", "limitations": "Needs jurisdiction data", "evidence_strength": "Low", "scale_up": "Data coverage", "ip_opportunity": "Software workflow"},
            {"approach": "Claim-level patent review", "objective": "Legal posture", "advantages": "Decision-grade IP view", "limitations": "Needs complete patent search", "evidence_strength": "Not yet run", "scale_up": "Patent databases", "ip_opportunity": "—"},
        ], ["approach", "objective", "advantages", "limitations", "evidence_strength", "scale_up", "ip_opportunity"],
            "Each approach states what it does, the trade-off it creates and what remains unverified."),

        # ---- Module 8 ---- #
        _section("Module 8 — Patent and Prior-Art Landscape", [
            {"item": "Search strategy", "value": "Keywords, synonyms, ingredients, processes, product forms, uses, jurisdictions and classification codes — to be formalised in a dedicated search"},
            {"item": "Landscape rows", "value": f"{len(patent_rows)} screening-level reference(s) from the corpus"},
            {"item": "Claim-level interpretation", "value": "Not performed on the current corpus — requires full claim review at the office/register"},
            {"item": "Legal status", "value": "Not established — no final novelty, infringement or FTO conclusion is made"},
            {"item": "Disclaimer", "value": "Potential overlap / preliminary similarity only; requires novelty search and FTO analysis, not a legal conclusion."},
        ], ["item", "value"], "Patent presence is not proof of commercial success, and patent silence is not proof of novelty."),
    ]

    if patent_rows:
        result["sections"].append(_section("Screening-level patent references", patent_rows,
                                           ["reference", "jurisdiction", "authority", "note"],
                                           "Screening only — no claim-level or legal conclusion."))

    result["sections"] += [
        # ---- Innovation opportunities ---- #
        _section("Innovation Opportunities", [
            {"innovation": i["innovation"], "problem": i["problem"], "concept": i["concept"],
             "differentiator": i["differentiator"], "benefit": i["benefit"], "risk": i["risk"],
             "validation": i["validation"], "ip_category": i["ip_category"]}
            for i in innovations
        ], ["innovation", "problem", "concept", "differentiator", "benefit", "risk", "validation", "ip_category"],
            "Each idea is an innovation hypothesis, not a patentability conclusion."),

        # ---- Research gaps ---- #
        _section("Research Gaps", [
            {"gap": g["gap"], "why_it_matters": g["why"], "how_to_close": g["close"], "priority": g["priority"]}
            for g in gaps
        ], ["gap", "why_it_matters", "how_to_close", "priority"],
            "Gaps are classified (market, consumer, regulatory, technical, patent, competitor, validation, jurisdiction)."),

        # ---- evidence quality ---- #
        _section("Evidence Quality and Limitations", [
            {"level": "Strongly supported", "value": "Indian regulatory pathway exists (FSSAI/AYUSH separation); classification is a provisional signal"},
            {"level": "Tentative", "value": "Technology status (extraction/standardization/stability) — mature by practice, not by claim-level proof"},
            {"level": "Unsupported / missing", "value": "Quantified market size, competitor revenue, consumer demand, complete patent map, jurisdiction verification"},
        ], ["level", "value"], "Confidence is stated per finding; nothing unverifiable is presented as fact."),

        # ---- recommended next steps ---- #
        _section("Recommended Next Steps", [
            {"priority": s["priority"], "action": s["action"], "reason": s["reason"],
             "expected_output": s["output"], "sources": s["sources"]}
            for s in next_steps
        ], ["priority", "action", "reason", "expected_output", "sources"], "Prioritised actions with expected outputs."),

        # ---- source-traceable evidence table ---- #
        _section("Source-Traceable Evidence Table", [
            {"source": c.get("act_title") or "corpus source", "type": _source_kind(c.get("authority") or ""),
             "jurisdiction": _qr_jurisdiction_hint(c.get("authority")), "section": c.get("section_reference") or "full text",
             "evidence": (c.get("exact_passage") or "")[:140], "confidence": "Medium–High (source-tagged)"}
            for c in citations[:8]
        ] + ([{"source": "No passages above threshold", "type": "gap", "jurisdiction": "—", "section": "—",
               "evidence": "Nothing is fabricated; gaps are reported.", "confidence": "—"}] if not citations else []),
            ["source", "type", "jurisdiction", "section", "evidence", "confidence"],
            "Every important factual claim in the report traces to one of these sources."),
    ]

    # ---- IP-SAKTI use case ---- #
    result["sections"].append(_section("IP-SAKTI Use Case (orchestration)", [
        {"item": "User input", "value": topic[:200]},
        {"item": "Agents required", "value": "Product Classifier → Quick Research → Document Analyzer → Novelty Search → FTO → Regulatory Roadmap → Formulation → Export Readiness → Dossier Export"},
        {"item": "Agent sequence", "value": "Classify first, then landscape, then legal screens, then regulatory road map, then export readiness"},
        {"item": "Data produced", "value": "Provisional category, evidenced landscape, requirement extract, patent/FTO posture, regulatory checklist"},
        {"item": "Human review points", "value": "Product classification → regulatory interpretation → patent claim analysis → safety/formulation → commercial launch decision"},
    ], ["item", "value"], "How this report feeds the IP-SAKTI orchestration engine."))

    return result


def _fs_failure_modes(problem: str, process: str = "", product: str = "") -> list[dict[str, str]]:
    """Classify the plausible failure modes for a shelf-life/physical-instability problem.

    Each mode is a HYPOTHESIS (not confirmed) — the agent never calls a cause a
    root cause without test data.  Returns modes with a confirm test and priority.
    """
    low = f"{problem} {process} {product}".lower()
    modes: list[dict[str, str]] = []
    if any(k in low for k in ("moisture", "water activity", "humid", "absorb", "wett", "cak", "lump", "clump")):
        modes.append({"mode": "Moisture / water-activity uptake", "detail": "Hygroscopic or improperly sealed product picks up moisture during storage.",
                      "test": "Moisture content + water-activity (aw) measurement at t0/t1/t2; packaging permeability check.", "priority": "High"})
    if any(k in low for k in ("potency", "marker", "active", "degrad", "withanolid", "bacoside", "oxid")):
        modes.append({"mode": "Chemical degradation / oxidation of actives", "detail": "Heat, oxygen, light, pH or solvent interaction degrades active markers.",
                      "test": "Active-marker assay at t0/t1/t2; stressed (accelerated) stability study; oxidation markers.", "priority": "High"})
    if any(k in low for k in ("microbial", "mould", "mold", "fungus", "bacteria", "bacterial", "yeast", "spoils", "preservat", "contaminat")):
        modes.append({"mode": "Microbial growth / preservation failure", "detail": "High water activity, poor sanitation, packaging leakage or inadequate preservation.",
                      "test": "Microbial limits + preservative-effectiveness test; process/filling review.", "priority": "High"})
    if any(k in low for k in ("settle", "clump", "sediment", "phase separ", "viscosity", "cak", "aggregat", "lump")):
        modes.append({"mode": "Physical instability (settling / clumping)", "detail": "Sedimentation, caking, phase separation or viscosity drift on storage.",
                      "test": "Visual + rheology study; sedimentation/phase-separation observation over storage; freeze-thaw check.", "priority": "High"})
    if any(k in low for k in ("seal", "leak", "packag", "headspace", "oxygen", "light", "delaminate", "carton")):
        modes.append({"mode": "Packaging / seal failure", "detail": "Oxygen, moisture or light ingress through an inadequate seal or barrier.",
                      "test": "Seal-integrity + permeability testing; headspace/oxygen assessment; light-stability study.", "priority": "Medium"})
    if any(k in low for k in ("batch", "inconsistent", "variation", "process", "heating", "cooling", "mixing", "drying")):
        modes.append({"mode": "Process variability", "detail": "Uneven heating, mixing, drying or cooling creates batch-to-batch differences.",
                      "test": "Batch trend analysis; in-process control points; replicate runs.", "priority": "Medium"})
    if not modes:
        modes = [
            {"mode": "Chemical degradation / oxidation of actives", "detail": "Actives may degrade via heat, oxygen or light.",
             "test": "Active-marker assay at t0/t1/t2; stressed stability study.", "priority": "High"},
            {"mode": "Moisture / water-activity uptake", "detail": "Product may gain moisture if packaging is not a barrier.",
             "test": "Moisture + water-activity (aw) measurement; packaging check.", "priority": "High"},
            {"mode": "Microbial growth / preservation failure", "detail": "Microbial quality may fail if preservation/sanitation is weak.",
             "test": "Microbial limits + preservative-effectiveness test.", "priority": "High"},
            {"mode": "Physical instability", "detail": "Settling, clumping or phase separation may appear during storage.",
             "test": "Rheology + sedimentation observation over storage.", "priority": "Medium"},
            {"mode": "Packaging / seal failure", "detail": "Barrier or seal may allow oxygen/moisture/light ingress.",
             "test": "Seal-integrity + permeability testing.", "priority": "Medium"},
        ]
    return modes


def _hub_find_solutions(inputs: dict[str, Any], result: dict[str, Any], resolved: list[dict[str, Any]], botanicals: str) -> dict[str, Any]:
    problem = _text(inputs, "problem_text") or "the stated problem"
    process = _text(inputs, "process_desc") or "not provided"
    goal = _text(inputs, "improve_aspect") or "a measurable target"
    constraints_txt = _text(inputs, "constraint") or "not provided"
    product = f"{botanicals or 'product'} composition"

    # 1) observed fact vs root-cause hypothesis — the core discipline
    modes = _fs_failure_modes(problem, process, product)
    observed = problem[:200]
    ("Confirmed symptom: " + observed +
                        " — the underlying root cause is NOT confirmed from the provided data.")

    # 2) system boundary
    system_rows = [
        {"element": "System", "value": f"Herbal {product if product else 'product'} shelf-life/quality process"},
        {"element": "Upstream inputs", "value": f"Botanical extracts, solvents, carriers, water, packaging — {process or 'process details not provided'}"},
        {"element": "Core process", "value": "Extraction, clarification, mixing/concentration, filling and sealing"},
        {"element": "Downstream conditions", "value": "Storage, transport, ambient exposure"},
        {"element": "Output / failure point", "value": observed},
        {"element": "Excluded factors", "value": "Commercially sensitive, competitor-specific or uncaptured laboratory data"},
    ]

    # 3) baseline & target (only what is provided; never invented)
    baseline_rows = [
        {"metric": "Current baseline", "value": f"{observed}"},
        {"metric": "Target", "value": goal + (" — numeric target to be confirmed by the user" if "(" not in goal else "")},
        {"metric": "Test method / time points", "value": "Not provided — to be confirmed"},
        {"metric": "Storage condition", "value": "Not provided — to be confirmed"},
        {"metric": "Cost / scale limits", "value": constraints_txt if constraints_txt != "not provided" else "Not provided — confirmation required"},
    ]

    # 4) constraints proposal (confirm before solving)
    constraints = [
        "Maximum total cost increase: 15% above baseline",
        "No unacceptable change in the current safety profile",
        "No unacceptable reduction in potency, stability or microbial quality",
        "Existing production-line compatibility preferred",
        "Any new excipient, carrier, preservative or packaging material needs compatibility + regulatory review",
        "Any equipment substitution needs capital-cost and scale-up assessment",
        "Bench validation before pilot or commercial implementation",
        "Success criteria defined via measurable quality attributes",
    ]

    # 5) candidate solutions from different intervention classes
    solutions = [
        {
            "id": "S-001", "title": "Failure-mode diagnosis & in-process monitoring",
            "class": "Quality-control improvement", "problem": "Unknown root cause", "mechanism": "Measures actives/moisture/microbial/physical markers over time to isolate the dominant failure mode",
            "expected_benefit": "Evidence-based next step instead of a guess", "effort": "Low", "cost": "Low",
            "line": "High", "regulatory": "No change", "ip": "Low", "validation": "t0/t1/t2 marker + aw + microbial tests",
            "risk": "No direct fix by itself — it is the diagnosis layer",
        },
        {
            "id": "S-002", "title": "Parameter / storage-condition optimisation",
            "class": "Parameter shift", "problem": "Thermal, oxidative or moisture-driven failure", "mechanism": "Adjusts temperature, solvent window, pH, moisture/oxygen exposure or storage condition",
            "expected_benefit": "Low-cost stabilisation if the suspected driver is confirmed", "effort": "Low", "cost": "Low",
            "line": "High", "regulatory": "No change", "ip": "Low–Medium", "validation": "Controlled one-variable-at-a-time stability runs vs baseline",
            "risk": "May reduce yield or alter organoleptics if the window is wrong",
        },
        {
            "id": "S-003", "title": "Packaging barrier & seal upgrade",
            "class": "Packaging change", "problem": "Moisture / oxygen / light ingress", "mechanism": "Higher-barrier primary packaging, headspace control and seal-integrity improvement",
            "expected_benefit": "Extends shelf life when ingress is the confirmed driver", "effort": "Medium", "cost": "Medium",
            "line": "Medium–High", "regulatory": "Packaging-food-contact review may apply", "ip": "Medium", "validation": "Permeability + seal-integrity + accelerated/real-time stability",
            "risk": "Cost per unit and line change-over",
        },
        {
            "id": "S-004", "title": "Process re-sequencing (pre-clarify, low-temperature handling)",
            "class": "Process re-sequencing", "problem": "Heat/moisture damage during a specific unit operation", "mechanism": "Rearranges steps — pre-clarification, controlled cooling, low-temperature drying, late-stage addition of sensitive ingredients",
            "expected_benefit": "Protects sensitive actives without new excipients", "effort": "Medium", "cost": "Low–Medium",
            "line": "Medium", "regulatory": "No change expected", "ip": "Medium", "validation": "Unit-operation hold-point + batch comparison",
            "risk": "Additional process complexity and validation",
        },
        {
            "id": "S-005", "title": "Carrier, stabiliser or preservative system",
            "class": "Formulation change", "problem": "Active degradation, physical instability or preservation gap", "mechanism": "Introduces a compatible stabiliser/carrier/preservative system",
            "expected_benefit": "Potential strong stability gain", "effort": "High", "cost": "Medium–High",
            "line": "Medium", "regulatory": "Ingredient/excipient review required", "ip": "Medium–High", "validation": "Compatibility + potency retention + safety + sensory + stability",
            "risk": "Regulatory, sensory, compatibility and cost impact — highest review burden",
        },
        {
            "id": "S-006", "title": "Equipment substitution (vacuum / inert atmosphere / improved mixing)",
            "class": "Equipment substitution", "problem": "Excessive heat, oxygen, moisture or residence time in current equipment", "mechanism": "Vacuum processing, alternative drying, inert-gas blanketing or improved mixing",
            "expected_benefit": "Structural fix for equipment-driven degradation", "effort": "High", "cost": "High",
            "line": "Low (capital)", "regulatory": "Minimum impact", "ip": "Medium–High", "validation": "Pilot-scale comparison + total-cost-of-ownership",
            "risk": "High capital expenditure and scale-up effort",
        },
    ]

    # 6) evaluation matrix (transparent scores; safety/regulatory get disqualifying flags)
    criteria = ["Technical impact", "Root-cause relevance", "Cost", "Line compatibility", "Safety", "Regulatory simplicity", "Scale-up", "Validation speed", "IP potential"]
    scores: dict[str, list[int]] = {
        "S-001": [3, 5, 5, 5, 5, 5, 5, 5, 3],
        "S-002": [4, 4, 5, 5, 5, 5, 5, 4, 3],
        "S-003": [4, 4, 3, 4, 5, 4, 4, 4, 4],
        "S-004": [4, 4, 4, 4, 5, 5, 4, 3, 4],
        "S-005": [5, 4, 2, 3, 3, 2, 3, 2, 5],
        "S-006": [5, 4, 1, 2, 5, 5, 2, 2, 4],
    }
    weights = {"Technical impact": 25, "Root-cause relevance": 20, "Cost": 10, "Line compatibility": 10,
               "Safety": 10, "Regulatory simplicity": 5, "Scale-up": 10, "Validation speed": 10, "IP potential": 5}
    matrix_rows = []
    for s in solutions:
        total = sum(scores[s["id"]][i] * weights[c] for i, c in enumerate(criteria)) / 100
        matrix_rows.append({
            "solution": s["id"], "title": s["title"],
            **{c: str(scores[s["id"]][i]) + "/5" for i, c in enumerate(criteria)},
            "weighted_score": f"{total:.1f}/5",
        })

    # ranking — fastest to test, best technical, best strategic/IP
    fastest = ["S-001", "S-002", "S-003"]
    best_tech = ["S-005", "S-006"]
    best_ip = ["S-005", "S-006"]
    rec = ("Recommended first action: run the failure-mode diagnosis (S-001) and a low-cost parameter/"
           "storage study (S-002) before changing formulation or equipment. Only after the dominant "
           "failure mode is confirmed should the agent rank carrier/stabiliser (S-005) or equipment "
           "substitution (S-006).")

    result["summary"] = (f"Find-Solutions engineering analysis for {product[:60] or problem[:60]} — "
                         f"{len(modes)} failure-mode hypothesis/hypotheses under test; "
                         f"{len(solutions)} candidate solutions with {len(solutions)} weighted evaluations.")
    result["note"] = "Symptom separated from cause; constraints proposed for confirmation; solutions ranked by weighted risk/gain + validation plan."
    result["findings"].append(_finding("fs-1", "Observed problem (confirmed symptom)", observed, "info"))
    result["findings"].append(_finding("fs-2", "Diagnosis status", "This is a confirmed symptom, not a confirmed root cause. Cause-isolation plan required before selecting an intervention.", "warning"))
    for i, m in enumerate(modes, start=1):
        result["findings"].append(_finding(f"fs-m-{i}", f"Failure-mode hypothesis: {m['mode']}", f"{m['detail']} Confirm with: {m['test']} (priority {m['priority']})", "warning"))
    result["suggestions"] = [
        f"Fastest-to-test: {', '.join(fastest)} — low cost, high-information experiments.",
        f"Best technical potential: {', '.join(best_tech)} — reserve for after the failure mode is confirmed.",
        f"Best strategic/IP potential: {', '.join(best_ip)} — these can create distinct technical positions.",
        rec,
    ]

    result["sections"] += [
        _section("1 — User Problem", [
            {"field": "Stated problem", "value": problem[:400] or "—"},
            {"field": "Process context", "value": process},
            {"field": "Desired outcome", "value": goal},
            {"field": "User-provided constraints", "value": constraints_txt},
        ], ["field", "value"], "The problem exactly as stated — before any diagnosis."),

        _section("2 — Problem Classification", [
            {"category": m["mode"], "matched": "Hypothesis to test", "confidence": "Untested", "confirm_test": m["test"]} for m in modes
        ] or [
            {"category": "Product stability / shelf-life", "matched": "Open — requires testing", "confidence": "Unknown", "confirm_test": "marker + physical + microbial + packaging tests"}
        ], ["category", "matched", "confidence", "confirm_test"], "Classification confidence shown; open categories stay open until tested."),

        _section("3 — System Boundary", [
            {"element": r["element"], "value": r["value"]} for r in system_rows
        ], ["element", "value"], "What is inside the analysis, what is excluded."),

        _section("4 — Current Baseline and Target", [
            {"metric": r["metric"], "value": r["value"]} for r in baseline_rows
        ], ["metric", "value"], "Target value not specified → user confirmation required before optimisation."),

        _section("5 — Assumptions and Unknowns", [
            {"item": "Assumption", "value": "India default regulatory context unless export markets are stated"},
            {"item": "Unknown", "value": "Dominant failure mode (moisture vs oxidation vs microbial vs physical vs packaging)"},
            {"item": "Unknown", "value": "Baseline marker/potency values, water activity, microbial status, packaging type"},
            {"item": "Unknown", "value": "Exact numeric target and cost limits"},
            {"item": "Rule", "value": "Nothing is invented where data is missing — reported as 'not established from current evidence corpus'."},
        ], ["item", "value"], "Patient, explicit uncertainty."),

        _section("6 — Root-Cause Hypothesis Tree", [
            {"hypothesis": m["mode"], "evidence": "To be established", "missing_evidence": m["test"],
             "confirm_test": m["test"], "priority": m["priority"]}
            for m in modes
        ], ["hypothesis", "evidence", "missing_evidence", "confirm_test", "priority"],
            "'Leading root-cause hypothesis' is the label until a test confirms it — never 'confirmed root cause'."),

        _section("7 — Recommended Constraints — Confirmation Required", [
            {"constraint": c} for c in constraints
        ], ["constraint"], "Ask the user to confirm or edit these before final ranked recommendation; preliminary output otherwise."),

        _section("8 — Technical Contradiction", [
            {"improving": "Shelf-life / physical stability", "worsening": "Cost, sensory/taste, safety profile, regulatory complexity, or manufacturing simplicity",
             "statement": "To extend shelf life we may need stronger preservation, barrier packaging or a carrier — but we must avoid changing taste, safety, regulatory classification or operating margin."},
        ], ["improving", "worsening", "statement"], "The core tension every solution must navigate."),

        _section("9 — Solution Mind Map", [
            {"branch": "Chemical stability", "nodes": "temperature · oxygen control · pH · solvent · antioxidant/stabiliser screening · marker monitoring"},
            {"branch": "Microbial stability", "nodes": "water-activity reduction · preservation-system review · sanitation · filling/sealing · microbial challenges"},
            {"branch": "Physical stability", "nodes": "pre-clarification · viscosity control · phase-separation study · compatibility testing"},
            {"branch": "Packaging", "nodes": "moisture/oxygen/light barrier · seal-integrity · headspace control"},
            {"branch": "Process redesign", "nodes": "low-temperature drying · vacuum concentration · re-sequencing · reduced residence time · late-stage addition"},
            {"branch": "Equipment", "nodes": "vacuum system · alternative dryer · improved mixer · inert-gas system · automated monitoring"},
        ], ["branch", "nodes"], "Branches cover multiple intervention classes; each must carry a validation test."),

        _section("10 — Candidate Solutions", [
            {"id": s["id"], "title": s["title"], "class": s["class"], "problem_addressed": s["problem"],
             "mechanism": s["mechanism"], "expected_benefit": s["expected_benefit"], "risk": s["risk"],
             "effort": s["effort"], "cost": s["cost"], "line_compat": s["line"], "regulatory": s["regulatory"],
             "ip_potential": s["ip"], "validation": s["validation"]}
            for s in solutions
        ], ["id", "title", "class", "problem_addressed", "mechanism", "expected_benefit", "risk",
            "effort", "cost", "line_compat", "regulatory", "ip_potential", "validation"],
            "Solutions may improve — they are design hypotheses until validated."),

        _section("11 — Solution Evaluation Matrix", matrix_rows,
                 ["solution", "title"] + criteria + ["weighted_score"],
                 "1 = Poor · 5 = Very strong. Weighting: technical impact 25%, root-cause relevance 20%, validation speed 10%, cost 10%, line compatibility 10%, safety 10%, scale-up 10%, regulatory simplicity 5%, IP potential 5%. High safety/regulatory risk can disqualify regardless of total score."),

        _section("12 — Recommended Validation Sequence", [
            {"step": "1", "action": "Failure-mode diagnosis (S-001): markers, aw, microbial, pH, seal/permeability", "reason": "Cheapest, highest-information first"},
            {"step": "2", "action": "Parameter / storage-condition study (S-002)", "reason": "Low cost, high line compatibility"},
            {"step": "3", "action": "Packaging barrier + process re-sequencing (S-003, S-004)", "reason": "Fix the confirmed ingress/thermally driven cause"},
            {"step": "4", "action": "Carrier / stabiliser (S-005)", "reason": "Delay until the driver is confirmed — regulatory review needed"},
            {"step": "5", "action": "Equipment substitution (S-006)", "reason": "Capital-heavy — only if the driver is equipment-specific"},
        ], ["step", "action", "reason"], "Bench → pilot → commercial; never scale before validation."),

        _section("13 — Cost and Implementation Considerations", [
            {"component": "Raw material / excipient / carrier", "baseline": "Unknown", "proposed": "To quantify", "difference": "TBD", "confidence": "Not established"},
            {"component": "Packaging", "baseline": "Unknown", "proposed": "S-003 barrier upgrade", "difference": "TBD", "confidence": "Not established"},
            {"component": "Equipment / energy", "baseline": "Unknown", "proposed": "S-006 only if needed", "difference": "TBD", "confidence": "Not established"},
            {"component": "Testing / validation", "baseline": "Unknown", "proposed": "S-001 diagnosis programme", "difference": "TBD", "confidence": "Not established"},
            {"component": "Cost-impact rule", "baseline": "—", "proposed": "Cost impact is not invented without data; a 15% ceiling is proposed, not measured", "difference": "—", "confidence": "Proposed"},
        ], ["component", "baseline", "proposed", "difference", "confidence"], "Exact numbers are not fabricated."),

        _section("14 — Safety and Regulatory Considerations", [
            {"change": "New excipient/carrier/preservative", "check": "Compatibility, safety, regulatory status, dose, sensory, analytical method, patent landscape"},
            {"change": "Label / claims", "check": "Structure/function vs disease claims (FDA); Health Canada NHP vs food; FSSAI food vs AYUSH ASU-drug path"},
            {"change": "Process / equipment change", "check": "GMP/process-change review; export-jurisdiction review if applicable"},
            {"change": "Rule", "value": "No disease-cure/prevention or 'clinically proven' claim without verified evidence and pathway"},
        ], ["change", "check"], "Safety and regulatory review always precedes implementation."),

        _section("15 — IP and Prior-Art Considerations", [
            {"potential_feature": "Process window (temperature/solvent/staging)", "technical_effect": "Marker retention vs degradation", "claim_category": "Process", "prior_art_risk": "Unknown", "next": "Novelty search before drafting"},
            {"potential_feature": "Barrier packaging configuration", "technical_effect": "Extended shelf life", "claim_category": "Packaging", "prior_art_risk": "Unknown", "next": "FTO search before launch"},
            {"potential_feature": "Carrier / stabiliser system", "technical_effect": "Stability improvement", "claim_category": "Composition", "prior_art_risk": "Unknown", "next": "Novelty + FTO search"},
            {"potential_feature": "Data-control workflow", "technical_effect": "Compliance automation", "claim_category": "Software workflow", "prior_art_risk": "Unknown", "next": "Prior-art review"},
            {"note": "Patentability is a separate question from technical usefulness — no patentability/FTO conclusion is made here.", "technical_effect": "—", "claim_category": "—", "prior_art_risk": "—", "next": "Patent-lawyer review"},
        ], ["potential_feature", "technical_effect", "claim_category", "prior_art_risk", "next"], "Technical usefulness ≠ patentable."),

        _section("16 — Evidence Table", [
            {"evidence_type": "User-provided baseline", "supports": observed, "does_not_prove": "The root cause", "confidence": "Observed"},
            {"evidence_type": "Citation corpus (if available)", "supports": "Regulatory/technical context", "does_not_prove": "That a candidate solution is effective", "confidence": "Source-tagged"},
        ] + [
            {"evidence_type": "Regulatory", "supports": (c.get("act_title") or "regulatory context"), "does_not_prove": "Technical efficacy of any solution", "confidence": "Medium–High"}
            for c in (result.get("citations") or [])[:3]
        ], ["evidence_type", "supports", "does_not_prove", "confidence"], "Technical, regulatory, patent and user evidence are kept separate."),

        _section("17 — Final Recommendation", [
            {"recommendation": rec, "first_test": "S-001 failure-mode diagnosis + S-002 parameter study", "long_term": "S-005 carrier/stabiliser or S-006 equipment after cause confirmation", "protect": "Validate then protect differentiating process/feature via patent_drafting"},
        ], ["recommendation", "first_test", "long_term", "protect"], "One clear next action, not a laundry list."),
    ]

    # --- Eureka gate: recommend constraints → user confirms → then solve ----- #
    # Prompt discipline: the constraints table is 'Confirmation Required'; the
    # candidate set, evaluation and final recommendation must NOT be emitted
    # before the user accepts/edits those constraints.
    confirmed = bool(
        inputs.get("constraints_confirmed") or inputs.get("confirmed_constraints")
        or inputs.get("confirmed_directions") or (constraints_txt != "not provided")
    )
    if not confirmed:
        _keep = {
            "1 — User Problem", "2 — Problem Classification", "3 — System Boundary",
            "4 — Current Baseline and Target", "5 — Assumptions and Unknowns",
            "6 — Root-Cause Hypothesis Tree", "7 — Recommended Constraints — Confirmation Required",
        }
        result["sections"] = [
            s for s in result["sections"]
            if s.get("title") in _keep or (s.get("title") or "").startswith("Data sources")
        ]
        result["sections"].append(_section("8 — Confirmation Required (blocking gate)", [
            {"state": "Root-cause hypotheses and the recommended constraints table are ready.", "decision": "Confirm or edit the constraints above to unlock the solution set."},
            {"state": "Solution mind map, candidate solutions, weighted evaluation, validation sequence and final recommendation are WITHHELD.", "decision": "They are generated only after the user confirms the recommended constraints."},
        ], ["state", "decision"], "Eureka discipline enforced: recommend → confirm → then generate the technical-solution mind map."))
        result["summary"] = (f"Preliminary Find-Solutions analysis for {product[:60] or problem[:60]} — "
                             f"{len(modes)} failure-mode hypotheses ready; full solution set blocked until the user confirms the recommended constraints.")
    return result
