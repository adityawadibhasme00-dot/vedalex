"""Claim drafting, office action response and claim charting.

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
    _BENEFIT_AS_COMPONENT,
    _DEVICE_TERM,
    _DOSAGE_FORM,
    _UNDEFINED_AMOUNT,
    _UNSUPPORTED_SYNERGY,
    _VAGUE_PROCESS,
    _basis_text,
    _citation_kind,
    _claim_elements,
    _draft_block_reasons,
    _ingredient_benefit_split,
    _keyword_phrases,
    _parse_invention,
    _short_name,
    _solvent_word,
    _split_claims_txt,
    _tokens,
)
from app.services.innolab._shared import (
    _evidence,
    _finding,
    _jurisdiction_code,
    _list_value,
    _markets,
    _retrieve,
    _section,
    _text,
)

__all__ = [
    "_VAGUE_CLAIM_TERMS",
    "_UNRESOLVED_MARKER",
    "_draft_blocker_check",
    "_skeleton_claims",
    "_use_phrase",
    "_build_terms_map",
    "_embedded_prior_art",
    "_essential_features",
    "_draft_patent_claims",
    "_compliance_checks",
    "_draft_abstract",
    "_draft_figures",
    "_draft_spec_sections",
    "_hub_patent_drafting",
    "_OA_GROUNDS",
    "_OA_STRATEGY",
    "_OA_EVIDENCE",
    "_extract_claims",
    "_classify_ground",
    "_segment_objections",
    "_claim_blocks",
    "_hub_office_action",
    "_STANDARD_BODY_WORDS",
    "_standard_hint",
    "_is_standard_source",
    "_chart_type",
    "_clause_obligation",
    "_feature_match_label",
    "_essentiality_verdict",
    "_evidence_tier",
    "_hub_claim_chart",
]

_VAGUE_CLAIM_TERMS = re.compile(
    r"\b(about|approximately|substantially|essentially|preferably|optionally|such as|"
    r"etc\.?|a suitable|in one embodiment)\b",
    re.I,
)


_UNRESOLVED_MARKER = re.compile(r"\[[^\]]*TO BE CONFIRMED[^\]]*\]|\[EXPERIMENTAL DATA REQUIRED\]|\[SOURCE SUPPORT REQUIRED\]", re.I)


def _draft_blocker_check(blocker: dict[str, str]) -> dict[str, Any]:
    return {"track": "semantic", "check": "Blocker: " + blocker["title"], "result": "fail", "detail": blocker["detail"]}


def _skeleton_claims(inv: dict[str, Any]) -> list[dict[str, Any]]:
    """Preliminary claim skeleton emitted ONLY when drafting is blocked — every missing datum is
    an explicit [TO BE CONFIRMED] marker, never silently filled. Not filing-ready by definition."""
    names = inv["ingredients"]
    comp = ", ".join(names[:3]) if names else "[defined botanical component(s) — TO BE CONFIRMED]"
    tree: list[dict[str, Any]] = []
    n = 0

    def _add(layer: str, text: str, depends_on: int | None = None, status: str = "Preliminary skeleton — NOT filing-ready") -> None:
        nonlocal n
        n += 1
        tree.append({"claim_no": n, "layer": layer, "kind": "independent" if depends_on is None else "dependent",
                     "depends_on": depends_on, "text": text, "status": status})

    _add("product", f"A composition comprising {comp}.")
    if inv["steps"]:
        step_txt = "; ".join(f"({c}) {s.lower()}" for c, s in zip("abcde", inv["steps"][:5], strict=False))
        _add("method", f"A method of preparing the composition of claim 1, the method comprising: {step_txt}.")
    else:
        _add("method", "A method of preparing the composition of claim 1, the method comprising: "
                        "[extraction / separation / concentration / formulation steps with solvent, temperature and "
                        "time — TO BE CONFIRMED by the inventor].")
    _add("use", f"Use of the composition of claim 1 for {_use_phrase(inv['use'])}.",
         status="Preliminary skeleton — jurisdiction-specific claim-type review required")
    if len(names) > 1:
        _add("product", f"The composition of claim 1, wherein the ratio of {names[0]} to {names[1]} is "
                        "[numeric ratio — TO BE CONFIRMED from the formulation and lab sheets].", depends_on=1)
    _add("product", f"The composition of claim 1 formulated as {inv['dosage_form']}.", depends_on=1)
    _add("product", "The composition of claim 1, wherein each extract is standardised to contain "
                    "[marker compound(s) and quantitative range — TO BE CONFIRMED].", depends_on=1)
    if inv["solvent"] and _solvent_word(inv["solvent"]) != "solvent":
        solvent_txt = "a hydroalcoholic solvent" if _solvent_word(inv["solvent"]) in ("hydroalcoholic", "hydro alcoholic") else inv["solvent"].lower()
        _add("method", f"The method of claim 2, wherein the extraction solvent system comprises {solvent_txt} — "
                       "[water/solvent ratio, temperature and time — TO BE CONFIRMED].", depends_on=2)
    return tree


def _use_phrase(use: str) -> str:
    u = (use or "").strip().lower().strip(".")
    if re.match(r"^(for|in|by|comprising)", u):
        return u
    if re.match(r"^(supporting|maintaining|promoting|improving|aiding)", u):
        return u
    if not u:
        return "nutritional or wellness application in a subject in need thereof"
    u = re.sub(r"^(supports?|supporting|maintains?|maintaining|promotes?|promoting|aids?|improves?|improving)\s+", "", u)
    return f"supporting {u}"


def _build_terms_map(inv: dict[str, Any], inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Eureka step 2 — terms map with synonyms / broader vs narrower terms built from the invention."""
    rows: list[dict[str, Any]] = []
    seen: set = set()

    def _add(term: str, kind: str, broader: str, narrower: str, source: str, essential: bool = False) -> None:
        term = (term or "").strip()
        key = term.lower()
        if not term or len(term) < 3 or key in seen:
            return
        seen.add(key)
        rows.append({
            "term": term[:70],
            "kind": kind,
            "broader": broader[:44],
            "narrower": narrower[:64],
            "source": source,
            "essential": "yes" if essential else "candidate",
        })

    for ing in inv["ingredients"]:
        _add(ing, "botanical", "plant material / extract", "marker assay · local synonym · analytical standard", "composition", essential=True)
    if inv["dosage_form"]:
        _add(inv["dosage_form"], "dosage", "pharmaceutical form", "unit dose · oral preparation", "product form", essential=True)
    for s in inv["steps"]:
        _add(s, "process", "manufacturing method", "operating parameter · endpoint", "process description")
    for m in inv["markers"]:
        _add(m, "characteristic", "quality standard", "quantitative marker", "standardisation", essential=True)
    for kw in _keyword_phrases(inv["problem"], limit=5):
        _add(kw, "context", "technical domain", "embodiment", "invention description")
    user = inputs.get("extracted_features")
    if isinstance(user, list):
        for u in user:
            _add(str(u), "confirmed", "user-confirmed term", "user-confirmed term", "user confirmation", essential=True)
    return rows[:16]


def _embedded_prior_art(terms: list[str], markets: list[str]) -> list[dict[str, Any]]:
    """Eureka step 3 — prior-art search executed INSIDE the drafting workflow per terms-map concept."""
    results: list[dict[str, Any]] = []
    seen: set = set()
    for market in markets[:2]:
        js = _jurisdiction_code(market)
        for term in terms[:5]:
            for c in _retrieve(term[:120], jurisdiction=js, top_k=2):
                key = (c.get("act_title"), c.get("section_reference"))
                if key in seen:
                    continue
                seen.add(key)
                row = dict(c)
                row["query_term"] = term[:60]
                row["market"] = market
                results.append(row)
    results.sort(key=lambda c: c.get("authority_rank", 9))
    return results[:10]


def _essential_features(inv: dict[str, Any], user_confirmed: Any = None) -> list[dict[str, str]]:
    """Eureka step 4 — confirm which parsed features are essential and must anchor the claims."""
    feats: list[dict[str, str]] = []
    seen: set = set()

    def _add(text, why) -> None:
        key = str(text).strip().lower()
        if not text or len(str(text).strip()) < 3 or key in seen:
            return
        seen.add(key)
        feats.append({"feature": str(text).strip()[:90], "why": why})

    for ing in inv["ingredients"]:
        _add(ing, "Core composition element — must appear in the independent composition claim")
    if inv["ratio"] and len(inv["ingredients"]) > 1:
        _add(f"Ratio {inv['ratio']} of {' to '.join(inv['ingredients'][:2])}", "Quantitative relationship defining claim scope")
    if inv["dosage_form"]:
        _add(inv["dosage_form"], "Defining product form limiting the claim scope")
    for m in inv["markers"][:2]:
        _add(m, "Quantitative characterising parameter (novelty anchor)")
    if inv["steps"]:
        _add(inv["steps"][0], "First process step anchors the method claim")
    _add(_use_phrase(inv["use"]), "Functional effect anchors the use claim")
    if isinstance(user_confirmed, list):
        for u in user_confirmed:
            _add(str(u), "User-confirmed essential feature")
    return feats[:10]


def _draft_patent_claims(inv: dict[str, Any], strategy: str = "Balanced") -> list[dict[str, Any]]:
    """Eureka step 5 — claims tree: independent product/method/use layers then dependents,
    each sentence built from the parsed invention data (not boilerplate). Where a required datum
    is absent the claim states [TO BE CONFIRMED] explicitly — it is never silently filled."""
    names = inv["ingredients"]
    comp = ", ".join(names[:3])
    tree: list[dict[str, Any]] = []
    n = 0

    def _add(layer: str, text: str, depends_on: int | None = None, status: str = "Preliminary — not filing-ready") -> None:
        nonlocal n
        n += 1
        tree.append({"claim_no": n, "layer": layer, "kind": "independent" if depends_on is None else "dependent",
                     "depends_on": depends_on, "text": text, "status": status})

    _add("product", f"A composition comprising {comp}.")
    if inv["steps"]:
        step_txt = "; ".join(f"({c}) {s.lower()}" for c, s in zip("abcde", inv["steps"][:5], strict=False))
        _add("method", f"A method of preparing the composition of claim 1, the method comprising the steps of: {step_txt}.")
    else:
        _add("method", "A method of preparing the composition of claim 1, the method comprising: "
                       "[process steps with solvent, temperature and time — TO BE CONFIRMED].",
             status="Preliminary — process parameters to be confirmed by the inventor")
    _add("use", f"Use of the composition of claim 1 for {_use_phrase(inv['use'])}.",
         status="Preliminary — jurisdiction-specific claim-type review required")
    if inv["ratio"] and len(names) > 1:
        _add("product", f"The composition of claim 1, wherein the ratio of {names[0]} to {names[1]} is {inv['ratio']}.", depends_on=1)
    elif len(names) > 1:
        _add("product", f"The composition of claim 1, wherein {names[0]} and {names[1]} are present in a defined ratio "
                        "[numeric ratio — TO BE CONFIRMED].", depends_on=1)
    _add("product", f"The composition of claim 1 formulated as {inv['dosage_form']} adapted for oral administration.", depends_on=1)
    if inv["markers"]:
        marker_txt = inv["markers"][0] + (f" and {inv['markers'][1]}" if len(inv["markers"]) > 1 else "")
        _add("product", f"The composition of claim 1, wherein the extract is standardised to contain {marker_txt}.", depends_on=1)
    if inv["solvent"] and _solvent_word(inv["solvent"]) != "solvent":
        solvent_txt = "a hydroalcoholic solvent" if _solvent_word(inv["solvent"]) in ("hydroalcoholic", "hydro alcoholic") else inv["solvent"].lower()
        _add("method", f"The method of claim 2, wherein the extraction solvent system comprises {solvent_txt} — "
                       "[water/solvent ratio, temperature and time — TO BE CONFIRMED].", depends_on=2)
    return tree


def _compliance_checks(claims_tree: list[dict[str, Any]], strategy: str, jurisdiction: str, inv: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Mandatory dual-track compliance review — deterministic + semantic checks,
    now grounding the review in the parsed invention features."""
    texts = {c["claim_no"]: c["text"] for c in claims_tree}
    body = " ".join(texts.values())
    checks: list[dict[str, Any]] = []
    inv = inv or {}

    dependency_ok = all(
        c["kind"] == "independent" or (c["depends_on"] and c["depends_on"] in texts)
        for c in claims_tree
    )
    checks.append({
        "track": "deterministic", "check": "Claim dependency validity",
        "result": "pass" if dependency_ok else "fail",
        "detail": "Every dependent claim references a valid, earlier claim number.",
    })

    vague = sorted(_VAGUE_CLAIM_TERMS.findall(body))
    unique_vague = sorted(set(vague))
    checks.append({
        "track": "semantic", "check": "Vague / broadening language",
        "result": "warn" if unique_vague else "pass",
        "detail": ("Flagged: " + ", ".join(unique_vague)) if unique_vague else "No vague terms like 'about' or 'preferably' detected.",
    })

    pro = re.search(r"\b(cure|cures|cured|heal|treats?|prevents?) (diabetes|cancer|covid|hypertension|aids|hiv)\b", body, re.I)
    checks.append({
        "track": "semantic", "check": "Prohibited / promotional therapeutic wording",
        "result": "fail" if pro else "pass",
        "detail": ("Blocked: " + pro.group(0)) if pro else "No disease-cure or promotional wording in the claim set.",
    })

    antecedent = all(("said " not in t or " the composition of claim " in t or " the method of claim " in t) for t in texts.values())
    checks.append({
        "track": "semantic", "check": "Antecedent basis",
        "result": "pass" if antecedent else "warn",
        "detail": "Terms are introduced before they are referred back to ('said X').",
    })

    abstract = _draft_abstract(body)
    words = len(abstract.split())
    limit = 150 if "uspt" in jurisdiction.lower() or "united states" in jurisdiction.lower() else 250
    checks.append({
        "track": "deterministic", "check": f"Abstract length (≤{limit} words)",
        "result": "pass" if words <= limit else "warn",
        "detail": f"Abstract drafted at {words} words for {jurisdiction or 'the selected office'}.",
    })

    numbering_ok = (
        sorted(c["claim_no"] for c in claims_tree) == list(range(1, len(claims_tree) + 1))
        and all(c["text"].strip() for c in claims_tree)
    )
    checks.append({
        "track": "deterministic", "check": "Claim numbering & formatting",
        "result": "pass" if numbering_ok else "fail",
        "detail": "Claims numbered consecutively 1..N, each a single non-empty sentence.",
    })

    c1 = next((c for c in claims_tree if c["claim_no"] == 1 and c["kind"] == "independent"), None)
    missing: list[str] = []
    if c1 and inv.get("ingredients"):
        missing = [
            i for i in inv["ingredients"][:2]
            if not re.search(r"\b" + re.escape(_short_name(i)) + r"\b", c1["text"], re.I)
        ]
    checks.append({
        "track": "deterministic", "check": "Independent-claim ingredient coverage",
        "result": "fail" if missing and c1 else "pass",
        "detail": ("Claim 1 must recite parsed composition ingredient(s): missing " + ", ".join(missing)) if missing and c1 else "Claim 1 recites the parsed invention's essential ingredients.",
    })

    use_claim: Any = next((c for c in claims_tree if c["layer"] == "use"), None)
    use_ok = bool(use_claim) and not bool(re.search(r"\b(cure|treat|prevent)\s+(?:of\s+)?(diabetes|cancer|covid|hypertension|aids|hiv)\b", use_claim["text"], re.I))
    checks.append({
        "track": "semantic", "check": "Use-claim claim-type safety",
        "result": "pass" if use_ok else "fail",
        "detail": "The use claim stays on wellness/effect territory and avoids a prohibited therapeutic phrasing.",
    })

    markers = sorted(set(_UNRESOLVED_MARKER.findall(body)))
    checks.append({
        "track": "semantic", "check": "Unresolved placeholders (blocking)",
        "result": "fail" if markers else "pass",
        "detail": ("Draft NOT filing-ready — unresolved marker(s): " + "; ".join(markers[:3]))
                  if markers else "No unresolved [TO BE CONFIRMED] markers in the claim set.",
    })

    ben = _BENEFIT_AS_COMPONENT.search(body)
    checks.append({
        "track": "semantic", "check": "Benefit language as a component",
        "result": "fail" if ben else "pass",
        "detail": ("Draft BLOCKED — '" + ben.group(0) + "' is a benefit/effect, not a defined ingredient.")
                  if ben else "No benefit terms drafted as ingredients.",
    })

    syn = _UNSUPPORTED_SYNERGY.search(body)
    checks.append({
        "track": "semantic", "check": "Unsupported synergy",
        "result": "fail" if syn else "pass",
        "detail": ("Unsupported 'synergistic' language — requires comparative experimental data and an "
                   "additive-model basis which the disclosure does not provide.")
                  if syn else "No unsupported synergy language.",
    })

    eff = _UNDEFINED_AMOUNT.search(body)
    checks.append({
        "track": "semantic", "check": "Defined quantities",
        "result": "fail" if eff else "pass",
        "detail": ("Undefined 'effective amounts' — claims need a concrete concentration, weight ratio or "
                   "dosage range from the formulation.")
                  if eff else "No undefined 'effective amount' language.",
    })

    ctrl = _VAGUE_PROCESS.search(body)
    checks.append({
        "track": "semantic", "check": "Concrete process parameters",
        "result": "fail" if ctrl else "pass",
        "detail": ("Vague 'controlled conditions' — specify solvent system, temperature, time, ratio and "
                   "scale before the method claim is accepted.")
                  if ctrl else "No vague 'controlled conditions' wording.",
    })

    solvent: Any = inv.get("solvent")
    generic_solvent = bool(solvent) and _solvent_word(solvent) == "solvent"
    checks.append({
        "track": "semantic", "check": "Solvent system identity",
        "result": "fail" if (re.search(r"\bsolvent\b", body, re.I) and generic_solvent) else "pass",
        "detail": ("Solvent named without identity — name the system (water / ethanol / hydroalcoholic etc.) "
                   "before drafting process claims.")
                  if (re.search(r"\bsolvent\b", body, re.I) and generic_solvent) else "Solvent system is identified or not required.",
    })
    return checks


def _draft_abstract(claim_body: str) -> str:
    words = claim_body.split()
    abstract = " ".join(words[:150])
    return (abstract or "A composition and associated preparation process are disclosed.").strip()


def _draft_figures(inv: dict[str, Any]) -> list[dict[str, Any]]:
    """Eureka step — figures whose subjects reference the parsed invention, emitted ONLY where
    technically meaningful: a concrete dosage form / device structure, or a process flow
    with real steps. Generic 'an Ayurvedic dosage form' without structure produces no drawings."""
    real_form = _DOSAGE_FORM.search(str(inv.get("dosage_form", "")))
    use_text = str(inv.get("use", ""))
    device_like = _DEVICE_TERM.search(str(inv.get("dosage_form", "")) + " " + use_text)
    has_structure = bool(real_form or device_like)
    figs: list[dict[str, Any]] = []
    if has_structure:
        ref_line = "; ".join(f"{10 + 4 * (i + 1)} {n}" for i, n in enumerate(inv["ingredients"][:4]))
        figs.append({"fig": "FIG. 1", "subject": f"{inv['dosage_form']} of {' '.join(inv['ingredients'][:3])}",
                     "refs": "10 dosage form · " + (ref_line or "12 composition")})
    if inv["steps"]:
        step_ref = "; ".join(f"{30 + 4 * i} step {i + 1} ({inv['steps'][i][:28]})" for i in range(min(len(inv["steps"]), 4)))
        figs.append({"fig": "FIG. 2", "subject": "Preparation process flow", "refs": step_ref or "30 process vessel"})
    if has_structure and figs:
        figs.append({"fig": "FIG. 3", "subject": f"{inv['dosage_form']} unit dose detail", "refs": "70 shell · 72 fill · 74 seal"})
    return figs


def _draft_spec_sections(inv: dict[str, Any], tree: list[dict[str, Any]], claims_text: list[str], checks: list[dict[str, Any]],
                         prior_art: list[dict[str, Any]], terms: list[dict[str, Any]],
                         essentials: list[dict[str, str]], figures: list[dict[str, Any]], jurisdiction: str) -> list[dict[str, Any]]:
    """Eureka step 6 — specification written from the parsed invention, background citing the prior art."""
    components = ", ".join(inv["ingredients"][:3])
    composition_para = f"The composition of the present invention comprises {components}."
    if inv["solvent"]:
        solvent_txt = "a hydroalcoholic solvent" if _solvent_word(inv["solvent"]) in ("hydroalcoholic", "hydro alcoholic") else inv["solvent"].lower()
        composition_para += f" The botanicals are extracted with {solvent_txt}."
    if inv["markers"]:
        composition_para += f" The extract is standardised to contain {', '.join(inv['markers'])}."
    if inv["ratio"] and len(inv["ingredients"]) > 1:
        composition_para += f" The ratio of {inv['ingredients'][0]} to {inv['ingredients'][1]} is {inv['ratio']}."

    process_para = inv["steps"] or ["[process steps with solvent, temperature and time — TO BE CONFIRMED by the inventor]"]
    example_src = inv["steps"] or ["Blend the botanicals", "Extract and clarify", "Standardise the markers", "Fill the dosage form"]
    example_markers = f" standardised to {', '.join(inv['markers'])}." if inv["markers"] else "."

    background_rows = [
        {
            "reference": (c.get("act_title") or c.get("query_term") or "passage")[:60],
            "authority": c.get("authority") or "KB",
            "passage": (c.get("exact_passage") or c.get("section_reference") or "relevant passage")[:110],
        }
        for c in prior_art[:5]
    ] or [{"reference": "No passage above threshold", "authority": "—", "passage": "Reported as a search gap — not extrapolated."}]

    return [
        _section("Terms map (editable — confirm before re-drafting)", terms,
                 ["term", "kind", "broader", "narrower", "source", "essential"],
                 "Auto-built from the invention description; broader/narrower expansions drive the embedded prior-art search."),
        _section("Embedded prior-art search", [
            {"query": p.get("query_term") or "—", "document": (p.get("act_title") or "passage")[:60],
             "section": p.get("section_reference") or "—", "authority": p.get("authority") or "KB",
             "passage": (p.get("exact_passage") or "")[:120]}
            for p in prior_art[:6]
        ] + ([{"query": "—", "document": "search gap", "section": "—", "authority": "—", "passage": "re-run per terms map after any edit"}]
             if not prior_art else []),
        ["query", "document", "section", "authority", "passage"], "Ran inside the drafting workflow per terms-map concept — every citation is a retrieved passage."),
        _section("Essential technical features (confirmed)", [
            {"feature": e["feature"], "why": e["why"], "status": "confirmed"} for e in essentials
        ], ["feature", "why", "status"], "The features that must anchor the independent claims; edit then regenerate to reshape the claim tree."),
        _section("Claims tree (product / method / use)", [
            {"claim": f"Claim {c['claim_no']}", "layer": c["layer"], "kind": c["kind"], "text": c["text"]} for c in tree
        ], ["claim", "layer", "kind", "text"], "Independent claims (product/method/use) then dependents narrowing ratios, dosage form, standardisation and solvent."),
        _section("Specification — filing application map (jurisdiction: " + jurisdiction + ")", [
            {"section": "Title", "content": inv["title"][:140]},
            {"section": "Technical field", "content": "Ayurvedic botanical composition, its preparation process and use thereof."},
            {"section": "Background", "content": "Prior-art context assembled from the embedded search (" + str(len(prior_art)) + " passage(s)) — " + background_rows[0]["reference"] + "."},
            {"section": "Summary of the invention", "content": composition_para},
            {"section": "Detailed description", "content": process_para[0] if len(process_para) == 1 else ("; ".join(f"({c}) {s.lower()}" for c, s in zip("abcde", process_para[:5], strict=False)) + ".")},
            {"section": "Claims (independent + dependent)", "content": "\n".join(claims_text)[:220] + ("…" if len("\n".join(claims_text)) > 220 else "")},
            {"section": "Abstract", "content": _draft_abstract(" ".join(claims_text))},
            {"section": "Drawing descriptions", "content": ", ".join(f["fig"] + " (" + f["subject"] + ")" for f in figures) or "No drawings yet — none technically meaningful without a concrete dosage form/device structure or an explicit process flow."},
        ], ["section", "content"], "Preliminary drafting structure — per-jurisdiction attorney review required before filing."),
        _section("Detailed description & example", [
            {"part": "Composition", "content": composition_para},
            {"part": "Preparation process", "content": "; ".join(f"({c}) {s.lower()}" for c, s in zip("abcde", process_para[:5], strict=False)) + ("; " + (("a hydroalcoholic solvent" if _solvent_word(inv["solvent"]) in ("hydroalcoholic", "hydro alcoholic") else inv["solvent"].lower()) + " at elevated temperature.") if inv["solvent"] else "")},
            {"part": "Standardisation", "content": (", ".join(inv["markers"]) + " — quantitative characterising parameters.") if inv["markers"] else "Include batch-specific marker data before filing."},
            {"part": "Dosage & administration", "content": f"Formulated as {inv['dosage_form']} for oral administration; dose per the intended effect: {_use_phrase(inv['use'])}."},
            {"part": "Example 1 — preparation", "content": ("; ".join(f"{i + 1}. {s}" for i, s in enumerate(example_src[:5])) + example_markers)},
        ], ["part", "content"], "Embodiments, ratios, process parameters and a worked example derived from the disclosure."),
        _section("Figures & reference numerals", figures, ["fig", "subject", "refs"], "Views planned from the actual composition and process steps; references auto-numbered."),
        _section("Compliance review (mandatory dual-track)", [
            {"track": c["track"], "check": c["check"], "result": c["result"], "detail": c["detail"]} for c in checks
        ], ["track", "check", "result", "detail"], "Dual-track review — deterministic (numbering, dependencies, coverage, abstract limit) + semantic (antecedent basis, placeholders, undefined quantities, synergy, benefit-as-component, vague process). The draft is NOT filing-ready while any fail remains."),
    ]


def _hub_patent_drafting(inputs: dict[str, Any], result: dict[str, Any], resolved: list[dict[str, Any]], botanicals: str, cit: list[dict[str, Any]]) -> dict[str, Any]:
    """Eureka-exact patent drafting — every advertised step executes on the parsed invention.
    Drafting is GATED: corrupted / vague / undefined terms block structural drafting until the
    inventor confirms them. Output is a preliminary drafting package, never 'filing-ready'."""
    strategy = _text(inputs, "claim_strategy") or "Balanced"
    mode = _text(inputs, "mode") or "Auto"
    markets = _markets(inputs)
    jurisdiction = _text(inputs, "filing_jurisdiction") or ", ".join(markets) or "selected office"

    inv = _parse_invention(inputs, resolved)
    terms = _build_terms_map(inv, inputs)
    split = _ingredient_benefit_split(inv, resolved, inputs)
    block = _draft_block_reasons(inv, inputs)
    prior_art = _embedded_prior_art([t["term"] for t in terms], markets)
    essentials = _essential_features(inv, inputs.get("extracted_features"))

    blocked = bool(block)
    if blocked:
        tree = _skeleton_claims(inv)
        claims_text = [f"{c['claim_no']}. PRELIMINARY SKELETON — NOT FILING-READY: {c['text']}" for c in tree]
        checks = _compliance_checks(tree, strategy, jurisdiction, inv) + [_draft_blocker_check(b) for b in block]
        blocker_labels = "; ".join(b["title"] for b in block)
    else:
        tree = _draft_patent_claims(inv, strategy)
        claims_text = [f"{c['claim_no']}. {c['text']}" for c in tree]
        checks = _compliance_checks(tree, strategy, jurisdiction, inv)
        blocker_labels = ""
    passed = sum(1 for c in checks if c["result"] == "pass")
    figures = _draft_figures(inv)

    result["claims"] = claims_text
    result["claims_blocked"] = blocked
    if prior_art:
        result["citations"] = prior_art

    if blocked:
        result["summary"] = (f"DRAFTING BLOCKED for {jurisdiction} — the disclosure contains unresolved/invalid "
                             f"technical term(s): {blocker_labels}. Only a preliminary claim skeleton (NOT "
                             f"filing-ready) is emitted. {passed}/{len(checks)} compliance check(s) cleared; "
                             f"the remaining fail(s) must be resolved with the inventor first.")
        result["note"] = ("Disclosure parsed → terms map → corrupted/vague-term detection → ingredient/benefit "
                          "split → prior-art scan → preliminary skeleton → compliance review → blocked hand-off. "
                          "Structural drafting resumes only after inventor confirmation of every blocker.")
        result["execution"] = {
            "planner": "Patent drafting workflow resolved: parse → terms map → block detection → split → prior art → skeleton claims → compliance (blocked) → clarification questionnaire",
            "reasoning": f"Drafting is gated: structural claims cannot be drafted while {len(block)} unresolved "
                         f"technical term(s) remain in the disclosure ({blocker_labels}).",
            "validation": "Claim text never invents missing data, never uses 'effective amounts', 'synergistic proportions' "
                          "or 'under controlled conditions', never treats benefit terms as components, and marks every "
                          "missing datum as [TO BE CONFIRMED].",
        }
    else:
        result["summary"] = (f"{mode} mode · {strategy} · preliminary draft of {len(tree)} claim(s) from "
                             f"{len(inv['ingredients'])} ingredient(s), {len(inv['steps'])} process step(s), "
                             f"{len(inv['markers'])} marker(s); {passed}/{len(checks)} compliance check(s) passed — "
                             f"NOT filing-ready; resolve the remaining warning(s)/fail(s) before filing.")
        result["note"] = ("Disclosure parsed → terms map → ingredient/benefit split → embedded prior-art search → "
                          "confirm essential features → claim versioning (A/B/C) → specification → figures → "
                          "compliance review → Word export.")
        result["execution"] = {
            "planner": "Patent drafting workflow resolved: parse invention → terms map → split → prior art → essentials → claims → spec → figures → compliance → export",
            "reasoning": f"Claims grounded on {len(inv['ingredients'])} resolved botanical(s), {len(inv['steps'])} "
                         f"process step(s) and {len(inv['markers'])} quantitative marker(s) parsed from the invention description.",
            "validation": "Every claim traces to a parsed input element or a retrieved prior-art passage; gaps are "
                          "reported as [TO BE CONFIRMED] markers, never silently filled.",
        }

    result["findings"].extend([
        _finding("pd-block", "Drafting gate",
                 ("BLOCKED — " + str(len(block)) + " unresolved technical term(s): " + blocker_labels)
                 if blocked else "Gate cleared — no corrupted or undefined drafting terms detected.",
                 "error" if blocked else "info"),
        _finding("pd-split", "Ingredient vs benefit split",
                 f"{len(split['ingredients'])} confirmed ingredient(s); benefit/effect term(s): "
                 f"{', '.join(split['benefit_terms']) if split['benefit_terms'] != ['none detected'] else 'none detected'}; "
                 f"unresolved candidate(s): {', '.join(split['unresolved_candidates'])}.", "info"),
        _finding("pd-parse", "Invention description parsed",
                 f"{len(inv['ingredients'])} ingredient(s), {len(inv['steps'])} process step(s), "
                 f"{len(inv['markers'])} marker(s), solvent {inv['solvent'] or 'n/a'}, ratio {inv['ratio'] or 'n/a'}.", "info"),
        _finding("pd-terms", "Terms map built",
                 f"{len(terms)} term(s) with broader/narrower expansions from the invention description.", "info"),
        _finding("pd-prio", "Embedded prior-art scan",
                 f"{len(prior_art)} passage(s) retrieved per terms-map concept — cited, not assumed.",
                 "info" if prior_art else "warning"),
        _finding("pd-ess", "Essential features confirmed",
                 f"{len(essentials)} essential feature(s) carried into the claims.", "info"),
        _finding("pd-tree", "Claims",
                 ("Preliminary skeleton — NOT filing-ready: " + str(len(tree)) + " claim(s).")
                 if blocked else (str(len(tree)) + " claim(s) drafted as a preliminary package — not filing-ready."), "warning"),
        _finding("pd-fig", "Figures planned",
                 f"{len(figures)} technically-meaningful drawing(s) generated — generic dosage forms without "
                 f"structure or process steps produce no drawings.", "info"),
    ])
    for c in checks:
        if c["result"] == "fail":
            result["findings"].append(_finding("pd-cx-" + re.sub(r"[^a-z0-9]+", "_", c["check"].lower()), c["check"], c["detail"], "warning" if not blocked else "error"))
        elif c["result"] == "warn":
            result["findings"].append(_finding("pd-cx-" + re.sub(r"[^a-z0-9]+", "_", c["check"].lower()), c["check"], c["detail"], "warning"))
    for p in prior_art[:3]:
        result["evidence"].append(_evidence("claim_anchor", p.get("act_title"), p.get("authority") or "KB"))
    if blocked:
        result["suggestions"] = [
            "Answer the clarification questionnaire below — especially the exact composition list, ratios, extraction parameters and solvent identity.",
            "Confirm the status of each effect term ('cognitive support', 'general wellness'): is it an ingredient to claim, or an effect to support? Benefit terms are not drafted as components.",
            "Resolve the corrupted text (e.g., words run together such as 'wellnessHowever') against the original inventor notes.",
            "After the blockers are cleared, re-run drafting, confirm each essential feature, and run a novelty/FTO check per claim.",
        ]
    else:
        result["suggestions"] = [
            "Confirm/edit the terms map and essential features, then regenerate — claims and specification rebuild from your edits (Eureka does this interactively).",
            "Attach experimental stability, marker and ratio data per technical effect — the [TO BE CONFIRMED] markers must be resolved before filing.",
            f"Verify the ratio claim against the lab data sheet for {', '.join(inv['ingredients'][:2])} before export.",
            "Run novelty_search on the independent product claim to confirm scope before Word export.",
            "Have a registered patent agent/attorney review the final claims for the filing jurisdiction before submission.",
        ]
    result["sections"] += _draft_spec_sections(
        inv, tree, claims_text, checks, prior_art, terms, essentials, figures, jurisdiction
    )
    split_rows = [
        {"item": "Confirmed ingredients", "value": ", ".join(split["ingredients"]) or "—"},
        {"item": "Unresolved candidate terms", "value": ", ".join(split["unresolved_candidates"]) or "—"},
        {"item": "Benefit / effect terms", "value": ", ".join([b for b in split["benefit_terms"] if b != "none detected"]) or "none detected"},
        {"item": "Rule applied", "value": "Benefit and unresolved terms are excluded from claim language until the inventor confirms what is a component vs an effect."},
    ]
    ver_rows = [
        {"version": "A — broad", "purpose": "Maximum scope to anchor the filing and reserve room during examination", "status": "Generated once composition list and ratios are confirmed"},
        {"version": "B — supported", "purpose": "Narrow, fully-supported version tied to experiments, markers and examples", "status": "Requires laboratory/marker data from the inventor"},
        {"version": "C — fallback", "purpose": "Narrowest defensible fallback for prosecution", "status": "Drafted from version B at the attorney's direction"},
    ]
    data_rows = [
        {"item": "Exact ingredient list & defined amounts/ratio", "status": "Provided" if inv["ratio"] else "Missing — [TO BE CONFIRMED]"},
        {"item": "Extraction / process parameters", "status": "Provided" if inv["steps"] else "Missing — inventor confirmation required"},
        {"item": "Solvent system identity", "status": "Confirmed" if (inv["solvent"] and _solvent_word(inv["solvent"]) != "solvent") else "Missing / unspecified"},
        {"item": "Marker compounds & quantitative ranges", "status": "Provided" if inv["markers"] else "Missing — experimental data required"},
        {"item": "Effect terms separated from components", "status": "Done" if split["benefit_terms"] == ["none detected"] else "Pending — clarify 'cognitive support' / 'general wellness' etc."},
        {"item": "Corrupted / miscopied text resolved", "status": "Pending — blockers active" if blocked else "Done"},
    ]
    jt_rows = [
        {"item": "Claim-type rules", "value": "US: composition + method + use claim types available; India: method-of-treatment claims not permitted and use claims restricted; EU/EPO: second (and further) medical-use style claims constrained."},
        {"item": "Grace period", "value": "US: 12-month grace; India: limited new-disclosure exceptions (Sections 2(1)(j) and 30); EU: no general grace period — file before any public disclosure."},
        {"item": "Priority / continuations", "value": "File divisional/continuation applications before parent grant to preserve claim scope."},
        {"item": "Foreign filing", "value": "A foreign-filing licence (India Section 39) may be required before filing abroad for inventions made in India."},
    ]
    st_rows = [
        {"item": "Status", "value": "DRAFTING BLOCKED — not filing-ready" if blocked else "PRELIMINARY draft — not filing-ready"},
        {"item": "Compliance review", "value": f"{passed}/{len(checks)} checks passed; every remaining fail is listed above and must be cleared before any filing."},
        {"item": "Designations", "value": "This draft is generated by software and is not a legal opinion; a registered patent agent/attorney must review the final claims and specification for the filing jurisdiction."},
        {"item": "Figures", "value": f"{len(figures)} drawing(s) — only technically meaningful drawings are generated."},
    ]
    result["sections"] += [
        _section("Ingredient vs benefit split (confirm with inventor)", split_rows,
                 ["item", "value"], "Separates actual ingredients from effect terms and unresolved candidates so claims never treat benefits as components."),
        _section("Claim versioning strategy (A / B / C)", ver_rows,
                 ["version", "purpose", "status"], "Version A (broad) → B (supported) → C (fallback) — generated from confirmed features, never from guessed data."),
        _section("Missing-data & inventor-confirmation checklist", data_rows,
                 ["item", "status"], "Every missing datum blocks a specific section of the draft and appears as [TO BE CONFIRMED] — nothing is silently filled."),
        _section("Jurisdiction notes (before filing)", jt_rows,
                 ["item", "value"], "Rules that a drafting agent must flag before an attorney files — claim types, grace periods, priorities and licences."),
        _section("Required disclaimers & draft status", st_rows,
                 ["item", "value"], "The draft is software-generated and preliminary; only an attorney can certify it as filing-ready."),
    ]
    return result


_OA_GROUNDS = [
    ("Novelty (prior-art anticipation)", re.compile(r"\bnovelt(?:y|ous)?\b|\banticipat|\bnew per\b|\bnot (?:new|novel)\b|\b102\b|\b(?:article|art\.?)\s*54\b", re.I)),
    ("Inventive step / obviousness", re.compile(r"\binventive step\b|\bobvious(?:ness)?\b|\bn[oa]n-?obvious\b|\b103\b|\b(?:article|art\.?)\s*56\b", re.I)),
    ("Clarity / conciseness", re.compile(r"\bclar(?:ity|ify)?\b|\bambiguous|\bantecedent (?:basis|references?)\b|\buncertain(?:ty)?\b|\bunclear\b|\b(?:article|art\.?)\s*84\b", re.I)),
    ("Support / written description", re.compile(r"\bsupport(?:ed|ing)?\b|\bwritten description\b|\bdoes not (?:find support|extend)\b|\b(?:article|art\.?)\s*84\b", re.I)),
    ("Enablement / sufficiency", re.compile(r"\benabl(?:ement|ing)?\b|\bsufficien(?:cy|t)\b|\breproduc|\bcannot be (?:performed|carried out)\b|\b(?:article|art\.?)\s*83\b", re.I)),
    ("Unity of invention", re.compile(r"\bunit(?:y of invention)?\b|\brestriction\b|\bplurality of inventions?\b", re.I)),
    ("Excluded subject matter", re.compile(r"\bexcluded (?:subject.?matter|matter)\b|\bnon-?patentable\b|\bmere (?:admixture|aggregation)\b|\btraditional knowledge\b|\btkdl\b|\bsection 3\b|3\([ceijklp]\)|\bmethod of (?:treatment|diagnosi)\b|\b(?:article|art\.?)\s*52\b|\b(?:article|art\.?)\s*53\b", re.I)),
    ("Formal / procedural", re.compile(r"\bformal(?:ities)?\b|\bdrawings?\b|\babstract\b|\bfees?\b|\bsequence listing\b|\bsignature\b|\bpriority document\b|\bassignment\b", re.I)),
]


_OA_STRATEGY = {
    "Novelty (prior-art anticipation)": ("Argue without amendment first — apply the single-reference test; fallback: narrow with an originally disclosed limitation",
                                          "Anticipation requires one prior-art reference that discloses every claimed element in the claimed combination before the relevant date."),
    "Inventive step / obviousness": ("Argue lack of motivation to combine and the supported technical effect; fallback: add a supported process parameter / comparative-result limitation",
                                      "Obviousness must be addressed separately from novelty — 'the invention is new' is not a response."),
    "Clarity / conciseness": ("Scope-preserving clarification using only terminology already present in the original disclosure",
                              "Replace undefined terms (e.g. 'effective amount') with supported quantitative language."),
    "Support / written description": ("Cancel or narrow the unsupported feature and cite the exact original basis if it exists",
                                      "Every claim feature must have a basis in the originally filed specification."),
    "Enablement / sufficiency": ("Supply reproducible process detail / examples or narrow scope to what is enabled",
                                 "A skilled person must be able to perform the claim across its whole scope."),
    "Unity of invention": ("Verify the single common inventive concept; consider a divisional/restriction filing if genuinely distinct",
                           "Unity is a procedural objection, not a substantive rejection of patentability."),
    "Excluded subject matter": ("Demonstrate the specific technical contribution over the excluded category; legal review required",
                                "Adding generic wording does not create patentability — the technical distinction must be shown."),
    "Formal / procedural": ("Correct the formal defect and confirm the correct format and fees",
                            "Formal objections are cured by compliance; verify deadlines separately."),
    "default": ("[AFTER FULL OBJECTION-TEXT REVIEW] Preliminary triage only — an objection-specific strategy needs the exact ground, claims and cited passages",
                "No final strategy can be produced from this record alone."),
}


_OA_EVIDENCE = {
    "Novelty (prior-art anticipation)": ("Prior-art distinction — exact reference passage plus filing/publication dates", "Patent team"),
    "Inventive step / obviousness": ("Comparative experimental data demonstrating an unexpected technical effect", "Inventor / technical team"),
    "Clarity / conciseness": ("Definition of the disputed term with the intended scope", "Patent team"),
    "Support / written description": ("Originally filed specification, claims and drawings for basis tracing", "Applicant / attorney"),
    "Enablement / sufficiency": ("Process details, batch records and reproducibility evidence", "Technical team"),
    "Unity of invention": ("Claim grouping and the shared-technical-feature analysis", "Attorney"),
    "Excluded subject matter": ("Technical distinction analysis and any expert input", "Inventor / attorney"),
    "Formal / procedural": ("None beyond compliant documents", "Applicant"),
}


def _extract_claims(text: str) -> str:
    m = re.search(r"claims?\s+([0-9]+(?:\s*[-–,&]\s*[0-9]+)*)", text or "", re.I)
    if m:
        return "Claims " + m.group(1).strip()
    return "[CLAIMS TO BE EXTRACTED FROM FULL ACTION]"


def _classify_ground(segment: str) -> str:
    for label, pattern in _OA_GROUNDS:
        if pattern.search(segment or ""):
            return label
    return "Unclassified — specific statutory/examination ground required"


def _segment_objections(oa: str) -> list[dict[str, Any]]:
    segs = [s.strip() for s in re.split(
        r"(?im)(?=(?:objection|rejection|rejected)(?:[ \t]*(?:under|against|to|of)\b)?|\n[ \t]*\d{1,2}[.)]?[ \t]+Claims?)",
        oa or "") if s.strip()]
    if not segs:
        segs = [oa or ""]
    objs = []
    for i, seg in enumerate(segs, start=1):
        if not seg.strip():
            continue
        objs.append({
            "id": f"O-{i:03d}",
            "excerpt": seg.strip()[:200],
            "words": seg.strip()[:260],
            "claims": _extract_claims(seg),
            "ground": _classify_ground(seg),
        })
    return objs or [{"id": "O-000", "excerpt": "[OFFICE ACTION TEXT REQUIRED]",
                     "words": "[OFFICE ACTION TEXT REQUIRED]",
                     "claims": "[CLAIMS TO BE EXTRACTED FROM FULL ACTION]",
                     "ground": "Unclassified — [OFFICE ACTION TEXT REQUIRED]"}]


def _claim_blocks(text: str) -> list[tuple]:
    """Split claim text into (claim number, body) pairs, tolerating multiple
    numbered claims pasted on a single line (e.g. '1. A ... 2. The ...')."""
    normalised = re.sub(r"(?<=[.!;])\s+(?=\d{1,2}\s*[.)]\s+[A-Z])", "\n", text or "")
    return _split_claims_txt(normalised)


def _hub_office_action(inputs: dict[str, Any], result: dict[str, Any], cit: list[dict[str, Any]]) -> dict[str, Any]:
    """OBJECTION-SPECIFIC office-action response planning. Without the complete office action, the exact
    claim text, the cited-reference passages and the original specification, this is PRELIMINARY REJECTION
    TRIAGE only — formal response drafting stays blocked. Nothing is invented: not objection wording, claim
    language, prior-art passages, publication dates, specification support, deadlines or hearing dates."""
    oa = _basis_text(inputs, "office_action_text") or ""
    raw_claims = _basis_text(inputs, "proposed_claims")
    app_no = _basis_text(inputs, "application_number", "app_number") or "[NOT PROVIDED]"
    markets = _markets(inputs)
    market_label = ", ".join(markets) if markets else "[JURISDICTION NOT IDENTIFIED]"

    if re.search(r"35 u\.?s\.?c|uspto|102\b|103\b|112\b", f"{oa} {market_label}", re.I):
        office = "USPTO (United States)"
        basis = "35 U.S.C. §§101–103, 112 (as applicable) — [CONFIRM THE EXACT GROUNDS FROM THE ACTION]"
    elif re.search(r"patents act|india|section 59|sec\.?\s*59", f"{oa} {market_label}", re.I):
        office = "Indian Patent Office"
        basis = "Patents Act, 1970 (India) — incl. Sec. 59 amendment limits — [CONFIRM THE EXACT GROUNDS FROM THE ACTION]"
    elif re.search(r"european|epo|ep\.", f"{oa} {market_label}", re.I):
        office = "EPO (Europe)"
        basis = "EPC Articles 52–57, 83–84 — [CONFIRM THE EXACT GROUNDS FROM THE ACTION]"
    else:
        office = "[OFFICE NOT IDENTIFIED FROM TEXT — CONFIRM]"
        basis = "[STATUTORY BASIS REQUIRED — UPLOAD THE COMPLETE OFFICE ACTION]"

    if re.search(r"first examination report|\bfer\b", oa, re.I):
        action_type = "First Examination Report (FER)"
    elif re.search(r"hearing notice|\bhearing\b", oa, re.I):
        action_type = "Hearing notice"
    elif re.search(r"written opinion", oa, re.I):
        action_type = "Written opinion"
    elif re.search(r"\bfinal\b", oa, re.I):
        action_type = "Final office action"
    else:
        action_type = "[NOT IDENTIFIED FROM TEXT]"

    deadline = _basis_text(inputs, "response_deadline", "deadline") or "[NOT VERIFIED — check the official patent-office record immediately]"
    objs = _segment_objections(oa)
    claims_affected = ", ".join(dict.fromkeys(o["claims"] for o in objs)) or "[CLAIMS TO BE EXTRACTED FROM FULL ACTION]"
    claims_tuples = _split_claims_txt(raw_claims)

    patent_refs = [c for c in cit if _citation_kind(c) == "Patent prior-art"]
    regulatory_refs = [c for c in cit if _citation_kind(c) == "Regulatory material"]
    other_refs = [c for c in cit if _citation_kind(c) not in ("Patent prior-art", "Regulatory material")]

    result["summary"] = (f"Office-action TRIAGE for {office}: {len(objs)} objection segment(s) classified "
                         f"({objs[0]['ground']} first), {len(patent_refs)} patent prior-art item(s) separated from "
                         f"{len(regulatory_refs)} regulatory source(s). FORMAL RESPONSE DRAFTING IS BLOCKED — the "
                         f"complete office action, exact claims, cited-reference passages, relevant dates and the "
                         f"original specification are required.")
    result["note"] = ("Office-action upload → document & deadline extraction → objection segmentation → ground "
                      "classification → reference verification → claim element mapping → novelty / inventive-step "
                      "analysis → amendment-basis & new-matter audit → objection-specific strategy ranking → "
                      "evidence requests → patent-agent review → filing checklist.")
    result["findings"].extend([
        _finding("oa-intake", "Office-action intake",
                 f"Application {app_no} · {office} · action type {action_type} · claims affected: {claims_affected}.",
                 "warning" if "[NOT" in app_no or "[NOT" in action_type else "info"),
        _finding("oa-obj", "Objection segmentation",
                 f"{len(objs)} objection segment(s) extracted and classified by ground.", "info"),
        _finding("oa-gate", "Response-drafting status",
                 "Preliminary rejection triage only — a formal response is NOT drafted until the complete office "
                 "action, exact claims, cited references, relevant dates and the original specification are available.", "error"),
        _finding("oa-refs", "Citation-type separation",
                 f"{len(patent_refs)} patent prior-art · {len(regulatory_refs)} regulatory (context only, never "
                 f"overcoming a rejection by itself) · {len(other_refs)} other technical material.", "info"),
        _finding("oa-claim", "Claim element mapping",
                 f"{len(claims_tuples)} claim(s) decomposed into {sum(len(_claim_elements(b)) for _, b in claims_tuples)} "
                 "atomic element(s); reference passages and disclosure status still [TO BE VERIFIED].", "warning" if claims_tuples else "info"),
        _finding("oa-amend", "Amendment / new-matter gate",
                 "Every proposed amendment must trace to an explicit original-disclosure basis; new matter and scope "
                 "expansion beyond the original framework are not permitted (India: Patents Act, 1970, Sec. 59).", "warning"),
        _finding("oa-exec", "Most serious objection & strategy",
                 f"{objs[0]['ground']} — recommended: {_OA_STRATEGY.get(objs[0]['ground'], _OA_STRATEGY['default'])[0]}.",
                 "error"),
    ])
    for c in cit[:3]:
        result["evidence"].append(_evidence(_citation_kind(c).lower().replace(" ", "_"), c.get("act_title"), c.get("authority") or "KB"))
    result["suggestions"] = [
        "Upload the complete office action with annexures, the search report, the exact claims and the cited references before requesting a draft.",
        "Record the office-action date and verify the response deadline on the official record immediately — do not rely on this system for deadline computation.",
        "Decompose each rejected claim into its elements and map every element to the exact cited passage (claim/paragraph/page).",
        "For every amendment, locate the explicit original specification basis and record the new-matter risk.",
        "Have a registered patent agent/attorney review the response package before filing.",
    ]

    objection_rows = [
        {"objection": o["id"], "exact_wording": o["excerpt"] + (" …" if len(o["words"]) > 200 else ""),
         "ground": o["ground"], "claims": o["claims"],
         "cited_reference": "[REFERENCE PASSAGE REQUIRED]", "page_para": "[PAGE/PARAGRAPH REQUIRED]",
         "priority": ("Critical" if o["ground"] in ("Novelty (prior-art anticipation)", "Inventive step / obviousness",
                                                    "Excluded subject matter") else
                      "High" if o["ground"] not in ("Formal / procedural",) else "Low")}
        for o in objs
    ]
    ref_rows = [
        {"reference": (c.get("act_title") or "passage")[:70], "type": _citation_kind(c),
         "jurisdiction": _jurisdiction_code(str(c.get("authority") or "")[:2]) or "—",
         "publication_date": "[DATE VERIFICATION REQUIRED]", "relevant_date": "[DATE VERIFICATION REQUIRED]",
         "prior_art_status": "[TO BE VERIFIED — compare each date against the filing/priority date]",
         "passage": (c.get("exact_passage") or c.get("section_reference") or "relevant passage")[:80],
         "verification": ("Passage context retrieved" if c.get("exact_passage") else "[REFERENCE PASSAGE REQUIRED]")}
        for c in cit[:6]
    ] + ([{"reference": "No patent-cited references available", "type": "—", "jurisdiction": "—", "publication_date": "—",
           "relevant_date": "—", "prior_art_status": "—", "passage": "—", "verification": "-"}
          ] if not cit else [])

    element_rows = []
    for num, body in claims_tuples:
        for el in _claim_elements(body):
            element_rows.append({
                "claim": "Claim " + num, "element": el,
                "reference_passage": "[REFERENCE PASSAGE REQUIRED]",
                "disclosure_status": "[TO BE VERIFIED]", "applicant_position": "[AFTER REFERENCE REVIEW]",
            })
    if not element_rows:
        element_rows.append({
            "claim": "[CLAIM TEXT REQUIRED]", "element": "—",
            "reference_passage": "[CLAIM TEXT REQUIRED]", "disclosure_status": "—", "applicant_position": "—"})

    strategy_rows = [
        {"objection": o["id"], "ground": o["ground"],
         "recommended": _OA_STRATEGY.get(o["ground"], _OA_STRATEGY["default"])[0],
         "fallback": "Amend with an explicitly supported limitation (see amendment gate)" if o["ground"] in ("Novelty (prior-art anticipation)", "Inventive step / obviousness") else "Cancel / consolidate / hearing — [PER STRATEGY RANKING]",
         "reason": _OA_STRATEGY.get(o["ground"], _OA_STRATEGY["default"])[1]}
        for o in objs
    ]

    amendment_rows = []
    for _num, body in claims_tuples:
        for el in _claim_elements(body)[:4]:
            amendment_rows.append({
                "proposed_feature": el[:80],
                "original_basis": "[ORIGINAL SPECIFICATION SUPPORT REQUIRED]",
                "explicit_or_implicit": "[TO BE VERIFIED]",
                "new_matter_risk": "Unknown until the originally filed disclosure is reviewed",
                "scope_effect": "[REQUIRES ATTORNEY DRAFTING]",
            })
    if not amendment_rows:
        amendment_rows.append({
            "proposed_feature": "—", "original_basis": "[CLAIM TEXT REQUIRED]",
            "explicit_or_implicit": "—", "new_matter_risk": "—", "scope_effect": "—"})

    evidence_rows = [
        {"objection": o["id"], "evidence_needed": _OA_EVIDENCE.get(o["ground"], ("Review of the full action record", "Attorney"))[0],
         "why_needed": "Supports a factual and technical position without fabrication",
         "owner": _OA_EVIDENCE.get(o["ground"], ("—", "Attorney"))[1], "deadline": "[NOT PROVIDED]"}
        for o in objs
    ]
    checklist_rows = [
        {"check": "Application number correct", "status": app_no},
        {"check": "Office-action date captured", "status": "[REQUIRED]"},
        {"check": "Response deadline verified", "status": deadline},
        {"check": "Hearing date / status", "status": "[NOT PROVIDED]"},
        {"check": "Every objection extracted with exact wording", "status": "Pending" if oa else "Blocked"},
        {"check": "Cited references verified (type, dates, status)", "status": "Pending"},
        {"check": "Claims decomposed and mapped element-by-element", "status": "Pending" if claims_tuples else "Blocked"},
        {"check": "Each amendment has an original basis + new-matter risk", "status": "Gate enforced"},
        {"check": "Arguments cite exact passages — no promotional wording", "status": "Gate enforced"},
        {"check": "Registered patent-agent review", "status": "Required"},
    ]
    timeline_rows = [
        {"item": "Office-action received", "value": "[DATE REQUIRED]"},
        {"item": "Response deadline", "value": deadline},
        {"item": "Internal triage complete", "value": "This package (preliminary)"},
        {"item": "Inventor/attorney input", "value": "[INVENTOR INPUT REQUIRED]"},
        {"item": "Filing of response", "value": "[AFTER PROFESSIONAL REVIEW — NOT SET BY THIS SYSTEM]"},
    ]
    limit_rows = [
        {"item": "Scope", "value": "This package is a technical and procedural drafting aid — a preliminary rejection triage. It is not a legal opinion and must not be filed without review by a qualified patent professional."},
        {"item": "Deadlines", "value": "Deadlines and hearing dates are not computed here — verify on the official record."},
        {"item": "Dates", "value": "Prior-art dates (filing/publication/priority) are [DATE VERIFICATION REQUIRED] for every cited reference."},
        {"item": "Amendment rule", "value": "No amendment may add matter not in substance disclosed in the original filing, and may not expand scope beyond the original framework (India — Patents Act, 1970, Sec. 59)."},
        {"item": "Regulatory material", "value": "FSSAI / AYUSH / FDA / other regulatory sources are context only — they are not patent prior-art evidence unless the examiner relies on them for a specific ground."},
    ]

    excl_trig = any("Excluded" in o["ground"] for o in objs) or bool(re.search(r"mere (?:admixture|aggregation)|section 3|non-?patentable", oa, re.I))
    tk_trig = excl_trig or bool(re.search(r"\btkdl\b|traditional knowledge|ayurvedic (?:text|formulation)", oa, re.I))
    most_serious = objs[0]["ground"] if objs else "[AFTER FULL OFFICE-ACTION REVIEW]"
    execd_rows = [
        {"aspect": "Application / jurisdiction", "value": f"{app_no} · {office}"},
        {"aspect": "Office-action type / date", "value": f"{action_type} · [DATE REQUIRED]"},
        {"aspect": "Objections detected", "value": f"{len(objs)} segment(s); most serious ground: {most_serious}"},
        {"aspect": "Best response strategy", "value": _OA_STRATEGY.get(objs[0]["ground"], _OA_STRATEGY["default"])[0] if objs else "[AFTER FULL OFFICE-ACTION REVIEW]"},
        {"aspect": "Deadline status", "value": deadline},
        {"aspect": "Missing documents", "value": "Complete office action · exact claims · cited-reference passages · original specification, claims & drawings · relevant dates"},
        {"aspect": "Attorney review", "value": "Required before filing"},
    ]
    invt_rows = [
        {"document": "Office action / examination report (full text + annexures + search report)", "available": "Partial (summary/uploaded text only)" if oa else "Missing", "required": "Yes", "notes": "Exact wording of every objection"},
        {"document": "Exact claims (affected only)", "available": "Provided" if raw_claims else "Missing", "required": "Yes", "notes": "For claim-element mapping"},
        {"document": "Cited references", "available": f"{len(patent_refs)} patent item(s) retrieved — [PUBLICATION NUMBERS REQUIRED]", "required": "Yes", "notes": "Numbers, dates, passages (claim/paragraph/page)"},
        {"document": "Original specification, claims & drawings", "available": "[UPLOAD REQUIRED]", "required": "Yes", "notes": "Sec. 59 / new-matter audit"},
        {"document": "Deadline / hearing notice", "available": deadline if "[NOT" not in deadline else "Missing", "required": "Yes", "notes": "Verify on the official record"},
    ]
    novelty_rows = [
        {"check": "Reference publicly available before the relevant date?", "status": "[DATE VERIFICATION REQUIRED]"},
        {"check": "A single reference discloses every claimed element?", "status": "[REQUIRES CLAIM + CITED PASSAGE]"},
        {"check": "Elements disclosed in the claimed combination?", "status": "[TO BE VERIFIED]"},
        {"check": "Disclosure direct and unambiguous (no reading-in)?", "status": "[TO BE VERIFIED]"},
        {"check": "Any element only optional or confined to a separate embodiment?", "status": "[TO BE VERIFIED]"},
        {"check": "Examiner combining multiple references for a novelty ground?", "status": "[TO BE VERIFIED]"},
        {"check": "Novelty position", "status": "[well-founded / incomplete / unclear feature / improper combination / date unresolved / attorney review]" if oa else "[OFFICE ACTION TEXT REQUIRED]"},
    ]
    is_rows = [
        {"item": "Closest prior art", "value": "[R1 — AFTER REFERENCE VERIFICATION]"},
        {"item": "Claimed distinguishing features", "value": "[F1, F2 — FROM CLAIM MAPPING]"},
        {"item": "Objective technical problem", "value": "[DERIVED FROM THE ORIGINAL DISCLOSURE]"},
        {"item": "Technical effect", "value": "[SUPPORTED EFFECT — EXPERIMENTAL DATA REQUIRED]"},
        {"item": "Examiner's combination", "value": "[R1 + R2 — MOTIVATION TO COMBINE TO BE ADDRESSED]"},
        {"item": "Applicant response", "value": "R1 does not teach [feature]; R2 does not suggest applying it to R1; the combination changes the technical operation; the claimed parameters produce [supported effect]; the prior art provides no motivation or reasonable expectation of success."},
    ]
    clarity_rows = [
        {"term_or_issue": "[PROBLEMATIC TERM — e.g. 'effective amount', 'synergistic', 'controlled conditions', 'improved', 'substantially', 'about', 'stable', 'high purity']",
         "why_unclear": "[EXAMINER'S CONCERN — REQUIRED]", "existing_definition": "[FROM ORIGINAL SPEC]",
         "proposed_replacement": "[SUPPORTED QUANTITATIVE LANGUAGE — NEVER INVENTED NUMBERS]",
         "original_basis": "[PAGE/PARAGRAPH]", "scope_impact": "[NARROWS / CLARIFIES]", "new_matter_risk": "[LOW/MEDIUM/HIGH/UNKNOWN]"},
        {"term_or_issue": "Claim feature lacking a written-description / support basis",
         "why_unclear": "Claim extends beyond the description or examples", "existing_definition": "[TRACE IN ORIGINAL SPEC]",
         "proposed_replacement": "Cancel or narrow to the supported scope", "original_basis": "[REQUIRED]", "scope_impact": "Narrows", "new_matter_risk": "Low if basis exists"},
        {"term_or_issue": "Enablement across the claimed scope",
         "why_unclear": "A skilled person may not be able to perform the claim across its full breadth", "existing_definition": "[MISSING PARAMETERS / EXAMPLES]",
         "proposed_replacement": "Supply reproducible detail or narrow scope", "original_basis": "[REQUIRED]", "scope_impact": "Narrows", "new_matter_risk": "Medium — verify support"},
    ]
    unity_rows = [
        {"analysis": "Unity of invention", "trigger": ("Unity / restriction objection detected" if any("Unity" in o["ground"] for o in objs) else "No unity ground in the segmented objections"),
         "status": "[TO BE VERIFIED — claim groups, single common inventive concept, shared technical effect; divisional/restriction only if genuinely distinct inventions were originally disclosed]"},
        {"analysis": "Excluded subject matter (TK / mere admixture / aggregation / treatment method / etc.)",
         "trigger": ("Present in segments / full-action text" if excl_trig else "Not detected — review the full action"),
         "status": "A specific technical contribution over the excluded category must be demonstrated; generic wording creates nothing (India: Sec. 3 / Sec. 3(p))"},
    ]
    tk_rows = [
        {"item": "TK reference (TKDL / traditional text)", "value": "[IDENTIFY THE CITED TK SOURCE — TKDL / text / edition / page]" if tk_trig else "Not triggered by the segmented objections"},
        {"item": "Claimed feature / overlap", "value": "[FEATURE vs KNOWN KNOWLEDGE]" if tk_trig else "—"},
        {"item": "Technical distinction", "value": "New process, standardisation, parameter, composition or effect demonstrated by evidence — [REQUIRED IF TK IS CITED]"},
        {"item": "Biological-material source / access", "value": "[NOT PROVIDED] — access-and-benefit-sharing obligations to be checked"},
        {"item": "Risk / review", "value": "High — professional review required whenever TK or biological material is involved"},
    ]
    amend_type_rows = [
        {"type": "Correction", "definition": "Fixes an obvious error without changing substantive scope", "risk": "Low — verify the error and basis", "note": "Obvious typographical/clerical errors"},
        {"type": "Clarification", "definition": "Explains existing terminology without adding new technical matter", "risk": "Low", "note": "Scope-preserving"},
        {"type": "Disclaimer", "definition": "Removes or narrows subject matter", "risk": "Low–Medium", "note": "Ensure a disclaimer basis exists in the record"},
        {"type": "Narrowing amendment", "definition": "Adds an originally disclosed limitation to distinguish prior art", "risk": "Low — basis must be explicit", "note": "Preferred for novelty / inventive-step objections"},
        {"type": "Scope-preserving amendment", "definition": "Rearranges/clarifies existing language without materially changing scope", "risk": "Low", "note": "Used for clarity objections"},
        {"type": "Broadening amendment", "definition": "May expand protection", "risk": "High risk", "note": "Requires professional review"},
        {"type": "New-matter amendment", "definition": "Adds a feature not in substance disclosed in the original filing", "risk": "NOT PERMITTED (India — Patents Act, 1970, Sec. 59)", "note": "Consider a separate filing or other lawful strategy, subject to advice"},
    ]
    prop_amend_rows = [
        {"claim": num, "original": body[:90],
         "marked_up": "[MARKED-UP — ATTORNEY DRAFTING: bold additions / strikethrough deletions after basis audit]",
         "clean": "[CLEAN AMENDED CLAIM — AFTER BASIS AUDIT]",
         "basis": "[ORIGINAL SPECIFICATION SUPPORT REQUIRED — page/paragraph/claim/figure]",
         "new_matter_risk": "[LOW/MEDIUM/HIGH/UNKNOWN]"}
        for num, body in claims_tuples[:6]
    ] or [
        {"claim": "—", "original": "[CLAIM TEXT REQUIRED]", "marked_up": "—", "clean": "—", "basis": "—", "new_matter_risk": "—"},
    ]
    next_rows = [
        {"order": "1", "action": "Upload the complete office action (full text, annexures, search report, exact claims and cited references)."},
        {"order": "2", "action": "Identify the statutory/examination ground for each O-001... objection and verify every cited reference's publication dates and prior-art status."},
        {"order": "3", "action": "Decompose each rejected claim into atomic elements and map every element to the exact cited passage (claim/paragraph/page)."},
        {"order": "4", "action": "Trace each proposed amendment to an explicit original-specification basis; record new-matter risk and scope impact (India Sec. 59)."},
        {"order": "5", "action": "Select argument / amendment / combined strategy per objection; prepare marked-up and clean claims."},
        {"order": "6", "action": "Have a registered patent agent/attorney review before filing; verify deadlines and hearing dates on the official record."},
    ]

    result["sections"] += [
        _section("# Office Action Response Analysis — intake & status", [
            {"item": "Application", "value": app_no},
            {"item": "Jurisdiction / office", "value": office + (f" (markets: {market_label})" if markets else "")},
            {"item": "Office-action type", "value": action_type},
            {"item": "Office-action date", "value": "[DATE REQUIRED]"},
            {"item": "Response deadline", "value": deadline},
            {"item": "Hearing status", "value": "[NOT PROVIDED]"},
            {"item": "Claims affected", "value": claims_affected},
            {"item": "Documents available", "value": "Partial (summary/uploaded text only) unless the full action is attached"},
            {"item": "Response-drafting status", "value": "Preliminary rejection triage — formal drafting BLOCKED pending the complete office action, exact claims, cited references, dates and the original specification"},
        ], ["item", "value"], "If only a summary is uploaded, the full response is blocked; never guess the legal basis from a summary."),
        _section("1. Executive summary", execd_rows,
                 ["aspect", "value"], "Application, most serious objection, best strategy, deadline status, missing documents and the attorney-review requirement in one view."),
        _section("2. Office-action document inventory", invt_rows,
                 ["document", "available", "required", "notes"], "Documents are either complete or partial — a summary-only record blocks formal drafting."),
        _section("3. Legal / statutory basis", [
            {"basis": basis},
        ], ["basis"], "The exact statutory and examination grounds must be read from the complete action, not inferred."),
        _section("4. Objection segmentation & classification", objection_rows,
                 ["objection", "exact_wording", "ground", "claims", "cited_reference", "page_para", "priority"],
                 "Every objection is extracted individually — unrelated objections are never merged."),
        _section("5. Cited-reference verification & type separation", ref_rows,
                 ["reference", "type", "jurisdiction", "publication_date", "relevant_date", "prior_art_status", "passage", "verification"],
                 "Patent prior-art, non-patent prior art, regulatory material and traditional-knowledge material are separated. "
                 "Regulatory documents never automatically overcome a novelty or inventive-step rejection."),
        _section("6. Claim-by-claim element mapping", element_rows,
                 ["claim", "element", "reference_passage", "disclosure_status", "applicant_position"],
                 "Disclosure labels: explicitly / inherently / partially / broadly disclosed · suggested only · not "
                 "disclosed · unclear. Lack of novelty is never concluded from partial overlap."),
        _section("7. Novelty analysis (single-reference test)", novelty_rows,
                 ["check", "status"], "Novelty is decided by one reference that discloses every claimed element in the claimed "
                                        "combination, direct and unambiguous, before the relevant date. Partial overlap never "
                                        "concludes lack of novelty."),
        _section("8. Inventive-step / obviousness analysis", is_rows,
                 ["item", "value"], "Obviousness is addressed separately from novelty — 'the invention is new' is never a response."),
        _section("9. Clarity, support & enablement analysis", clarity_rows,
                 ["term_or_issue", "why_unclear", "existing_definition", "proposed_replacement", "original_basis", "scope_impact", "new_matter_risk"],
                 "Undefined terms are replaced only with supported quantitative language — never invented numbers. Every "
                 "claim feature must have an original basis and be enabled across its scope."),
        _section("10. Unity & excluded-subject-matter analysis", unity_rows,
                 ["analysis", "trigger", "status"], "Unity is procedural; excluded subject matter needs a demonstrated technical "
                                                    "contribution over the excluded category (e.g. India Sec. 3 / Sec. 3(p))."),
        _section("11. Traditional-knowledge & biological-material analysis", tk_rows,
                 ["item", "value"], "TKDL / traditional-text citations and biological material trigger access-and-benefit-"
                                     "sharing and exclusion risks — professional review required."),
        _section("12. Amendment support & new-matter audit", amendment_rows,
                 ["proposed_feature", "original_basis", "explicit_or_implicit", "new_matter_risk", "scope_effect"],
                 "Amendment gate: no feature may be added unless a precise original basis is located. Types: correction · "
                 "clarification · disclaimer · narrowing · scope-preserving; broadening and new-matter amendments are high "
                 "risk and require professional review."),
        _section("13. Amendment types & classification", amend_type_rows,
                 ["type", "definition", "risk", "note"], "Every proposed change is one of: correction, clarification, "
                                                        "disclaimer, narrowing, scope-preserving, broadening or new matter. "
                                                        "New matter is not permitted (India — Patents Act, 1970, Sec. 59)."),
        _section("14. Ranked response strategies (per objection)", strategy_rows,
                 ["objection", "ground", "recommended", "fallback", "reason"],
                 "Strategies are objection-specific — 'amend to distinguish' / 'argue without amendment' / 'scope-preserving "
                 "clarification' / 'cancel or consolidate' / 'request hearing or interview' / 'divisional review'."),
        _section("15. Proposed amendments (original · marked-up · clean)", prop_amend_rows,
                 ["claim", "original", "marked_up", "clean", "basis", "new_matter_risk"],
                 "Three versions per amended claim (original, marked-up with bold additions / strikethrough deletions, and "
                 "clean) — every amendment ships with its original basis and risk. Marked-up/clean drafting requires the "
                 "full claim text and specification, so this stays under attorney drafting here."),
        _section("16. Evidence & inventor data requests", evidence_rows,
                 ["objection", "evidence_needed", "why_needed", "owner", "deadline"],
                 "Evidence is requested, never fabricated."),
        _section("17. Proposed response arguments (templates pending verification)", [
            {"objection": o["id"], "ground": o["ground"], "argument":
             "The applicant respectfully submits that the cited passage does not disclose the claimed feature in the "
             "required combination. [CONFIRM the exact passage, claim element and relevant dates before use.]"}
            for o in objs
        ], ["objection", "ground", "argument"], "Arguments stay professional; phrases like 'the examiner is wrong' or "
                                                "'the invention is obviously novel' are never used."),
        _section("18. Procedural checklist", checklist_rows,
                 ["check", "status"], "Run before finalisation."),
        _section("19. Response timeline", timeline_rows,
                 ["item", "value"], "Track externally — this system does not compute statutory deadlines."),
        _section("20. Limitations & legal-review points", limit_rows,
                 ["item", "value"], "This is a preliminary rejection triage, not a filing-ready response."),
        _section("21. Recommended next steps", next_rows,
                 ["order", "action"], "The sequence for converting this triage into a filing-ready response package."),
    ]
    return result


_STANDARD_BODY_WORDS = (
    "etsi", "3gpp", "iso", "iec", "itu", "ieee", "w3c", "astm", "cen", "aisc",
    "bis", "tia", "din", "jis", "asme", "ansi", "nist", "gsma", "etsi ts",
)


def _standard_hint(text: str) -> list[str]:
    low = re.sub(r"[^A-Za-z0-9]", " ", text or "").lower().split()
    return sorted({t for t in low if t in _STANDARD_BODY_WORDS})


def _is_standard_source(c: dict[str, Any]) -> bool:
    blob = f"{c.get('act_title') or ''} {c.get('authority') or ''}"
    low = blob.lower()
    hits = _standard_hint(blob)
    if not hits:
        return bool(re.search(r"\b(ts|tr)\s?[\w.-]+\b|technical standard|specification document|release \d|ver\.?\s?\d+", low))
    if any(w in low for w in ("fda", "fssai", "ayush", "cdsco", "patent office", "uspto", "inpass", "epo")):
        return False
    return True


def _chart_type(inputs: dict[str, Any], standard: str) -> tuple:
    """Classify the chart into one of five types. Never assumed — if not declared
    and no standard is supplied, the type is 'Not declared'."""
    intent = (inputs.get("chart_intent") or "").lower()
    if any(k in intent for k in ("litigat", "court", "infringement", "suit")):
        return ("Patent-to-chart — litigation preparation", "Claim mapping for litigation preparation; NOT 'court-ready' without attorney review.")
    if any(k in intent for k in ("licens", "pool", "frand", "royalt")):
        return ("Patent-to-standard — licensing / pool / FRAND", "FRAND/pool context; optimistic + cautious-sided mapping both shown.")
    if inputs.get("product_versions") or inputs.get("product_desc"):
        return ("Patent-to-product — implementation mapping", "Claims mapped to a specific product implementation with version tracking.")
    if any(k in intent for k in ("validity", "prior art", "invalidate", "opposition")):
        return ("Patent-to-prior-art — validity support", "Claims mapped against prior-art disclosure level; essentiality is out of scope.")
    if standard:
        return ("Standard-essentiality mapping (type not declared — confirm)", "Chart type selected by default because a standard was provided.")
    return ("Not declared — chart type is a required input", "Declare the chart purpose before the claim chart is finalised.")


def _clause_obligation(clause_text: str | None) -> str:
    """Classify standard-clause obligation level — deterministic, keyword-based.
    Only a normative clause can support a positive essentiality mapping."""
    c = (clause_text or "").lower()
    if not c.strip():
        return "Unclear — clause text required for classification"
    if any(w in c for w in ("deprecated", "discontinued", "withdrawn", "obsolete")):
        return "Deprecated / obsolete"
    if any(w in c for w in ("shall not", "must not", "shall be prohibited", "is not permitted")):
        return "Normative — prohibition (shall not / must not)"
    if re.search(r"(if|when|where)\b[^.;]{0,90}\bshall\b", c):
        return "Normative — conditional (if/when/where … shall)"
    if "shall" in c or "must" in c or "is required" in c or "required to" in c:
        return "Normative — mandatory (shall / must)"
    if "should" in c:
        return "Recommended (should)"
    if any(w in c for w in ("may", "can optionally", "optionally", "optional", "is permitted", "allowed", "need not")):
        return "Optional / permitted (may)"
    if any(w in c for w in ("informative", "informational", "appendix", "notes", "note:")):
        return "Informative (non-normative)"
    if "profile" in c and "specific" in c:
        return "Profile-specific (applies to a declared profile only)"
    if any(w in c for w in ("implementation-dependent", "implementation specific", "depends on the implementation", "implementation dependent")):
        return "Implementation-dependent"
    if any(w in c for w in ("for example", "e.g.", "example", "illustrative", "such as")):
        return "Example / illustrative"
    return "Unclear — clause text to review"


def _feature_match_label(feature: str, clause_text: str, obligation: str) -> tuple:
    """Feature-to-clause match label: Direct / Partial / Functional / Optional /
    Not found / Unclear. Labels are evidence-based, never a fabricated percentage."""
    if not clause_text or not clause_text.strip():
        return "Unclear", "No clause text retrieved — supply the standard clause text."
    if not feature or "not provided" in feature.lower() or "to be stated" in feature.lower():
        return "Not classifiable", "The claim limitation is underdefined — quantify it before mapping."
    qt = _tokens(feature)
    plow = clause_text.lower()
    present = [t for t in qt if t in plow]
    ratio = (len(present) / len(qt)) if qt else 0
    basis = f"{len(present)}/{len(qt)} claim term(s) appear in the retrieved clause text."
    ob = (obligation or "").lower()
    if ratio >= 0.8:
        if "conditional" in ob:
            return "Direct match (conditional clause)", basis + " Clause applies only under its conditional trigger."
        if "prohibition" in ob:
            return "Direct match (prohibited feature)", basis
        return "Direct match", basis
    if ratio >= 0.5:
        return "Partial match", basis + " One or more claim terms are absent from the clause line."
    if ratio > 0.0:
        if "optional" in ob or "permitted" in ob:
            return "Optional (mentioned only as permitted)", basis
        if "recommended" in ob:
            return "Recommended only", basis
        if "informative" in ob or "example" in ob or "illustrative" in ob:
            return "Informative / example level", basis
        return "Weak overlap", basis + " Occasional term overlap — not a specific teaching."
    return "Not found in the retrieved clause text", "No claim term appears in the clause line."


def _essentiality_verdict(match_label: str, obligation: str) -> str:
    """Five-level essentiality verdict. Never conclusive — always a position for
    technical/legal confirmation."""
    ml = match_label.lower()
    ob = (obligation or "").lower()
    if "not found" in ml:
        return "Not mapped"
    if ml.startswith("unclear") or ml == "not classifiable":
        return "Uncertain — clause text / quantified limitation required"
    if "optional" in ml or "recommended only" in ml or "informative" in ml or "example level" in ml:
        return "Not shown to be essential (non-mandatory clause)"
    if "direct match" in ml and "conditional" in ob:
        return "Conditional — potentially essential when the conditional trigger applies"
    if "direct match" in ml:
        return "Potentially essential — technical essentiality to be confirmed"
    if "partial" in ml or "weak overlap" in ml:
        return "Not shown to be essential — incomplete feature mapping"
    return "Uncertain"


def _evidence_tier(c: dict[str, Any]) -> str:
    """Tier the chart evidence. Regulatory / patent-office / TK statements can
    NOT evidence a standard clause — they are context only."""
    blob = f"{c.get('act_title') or ''} {c.get('authority') or ''}"
    low = blob.lower()
    if _is_standard_source(c) or _standard_hint(blob):
        return "Tier 1 — official standard text (clause-level evidence)"
    if any(w in low for w in ("essentiality declaration", "declaration", "claim chart", "patent")):
        return "Tier 2 — patent / essentiality-declaration record"
    if any(w in low for w in ("implementation", "technical", "manual", "specification note", "contribution")):
        return "Tier 3 — technical / implementation documentation"
    if any(w in low for w in ("fda", "fssai", "ayush", "cdsco", "who", "efsa", "health canada", "patent office", "uspto", "inpass", "act 1970")):
        return "Tier 4 — regulatory / patent-office context (does NOT prove a clause)"
    return "Tier 5 — secondary"


def _hub_claim_chart(inputs: dict[str, Any], result: dict[str, Any], cit: list[dict[str, Any]]) -> dict[str, Any]:
    """SPEC-IMPLEMENTING AICC ESSENTIALITY CLAIM CHART.

    Claim text, the standard and its version are required inputs. Claims are split
    into atomic limitations (including inherited parent limitations for dependent
    claims); the standard is identified with a version gate; retrieved corpus
    passages are classified as standard clauses vs context-only sources; each
    limitation is mapped clause-by-clause with a feature-match label (Direct /
    Partial / Optional / Not found / Unclear) and a five-level essentiality
    verdict. Regulatory / patent-office / FK statements are NEVER treated as
    clause evidence. Without claims OR a standard the chart is BLOCKED and shows
    '0 of 0' nowhere. Nothing numeric is fabricated. No legal conclusion is made."""
    import datetime

    claims_txt = _basis_text(inputs, "proposed_claims") or _text(inputs, "problem_text") or ""
    standard = _text(inputs, "standard_name") or ""
    version = _text(inputs, "standard_version") or ""
    patent_no = _text(inputs, "patent_number") or "[NOT PROVIDED]"
    product_versions = _list_value(inputs, "product_versions")
    product_desc = _text(inputs, "product_desc") or ""

    chart_type, type_note = _chart_type(inputs, standard)
    today = datetime.date.today().isoformat()
    chart_id = f"AICC-{datetime.date.today().strftime('%Y%m%d')}-01"

    claims = _claim_blocks(claims_txt)
    result["claims"] = [f"{num}. {body}" for num, body in claims]

    # atomic limitation breakdown with dependency inheritance
    per_claim: dict[str, list[str]] = {}
    atoms = []
    for num, body in claims:
        dep_m = re.search(r"\bof\s+claim\s+(\d+)", body, re.I)
        dep = dep_m.group(1) if dep_m else None
        parts = _claim_elements(body)
        per_claim[num] = parts
        for i, el in enumerate(parts):
            atoms.append({
                "claim": f"Claim {num}",
                "limitation": el,
                "type": "Preamble / core element" if i == 0 else "Limitation",
                "foundation": (f"Depends on claim {dep} — inherits all of its limitations" if dep else "Independent claim — self-contained"),
                "depends": (f"claim {dep}" if dep else "—"),
            })
    # dependency inheritance — dependent rows also receive their parent's elements
    inherited: list[dict[str, str]] = []
    for num, body in claims:
        dep_m = re.search(r"\bof\s+claim\s+(\d+)", body, re.I)
        dep = dep_m.group(1) if dep_m else None
        if not dep or dep not in per_claim:
            continue
        for _i, el in enumerate(per_claim[dep]):
            inherited.append({
                "claim": f"Claim {num} (inherited)",
                "limitation": el,
                "type": "Inherited from claim " + dep,
                "foundation": f"Automatically inherited from claim {dep} per the dependency — re-verify against the granted text",
                "depends": "—",
            })
    atoms += inherited
    if not atoms:
        atoms = [{
            "claim": "Claim 1", "limitation": "[CLAIM TEXT REQUIRED]",
            "type": "—", "foundation": "No claim text supplied",
            "depends": "—",
        }]

    # version gate
    if version:
        version_status = f"VERSION GATE PASSED — {standard} {version} (effective/release date: [CONFIRM AT SOURCE])"
    else:
        version_status = "VERSION GATE BLOCKED — specify the standard version/release plus its effective date before any clause mapping is finalised"

    # standard clauses from corpus (only standard-body sources are clause evidence)
    clause_sources = [c for c in cit if _is_standard_source(c)]

    gates_blocked = not claims_txt.strip() or not standard.strip()
    if gates_blocked:
        status = "STATUS: BLOCKED — required inputs missing (claim text and standard)"
        missing = ["Claim text (proposed_claims / claim_wording)"] + ([] if claims_txt.strip() else [])
        missing += ["Standard name/number (standard_name)"] + ([] if standard.strip() else [])
        missing += (["Standard version + effective date (standard_version)"] if not version.strip() else [])
        export_status = "Template only — no chart rows can be produced without claims and a standard"
    elif not version.strip():
        status = "STATUS: DRAFT — claims and standard present, version gate not passed"
        missing = ["Standard version + effective date (standard_version)"]
        export_status = "Template only — version gate prevents export"
    elif not clause_sources:
        status = "STATUS: DRAFT — claims and standard present, no standard clause evidence retrieved"
        missing = ["Standard clause text (supply it so the mapping is evidence-grounded, never guessed)"]
        export_status = "Template only — no evidence-backed mapping can be produced without the standard clause text"
    else:
        status = "STATUS: DRAFT — mapping produced; essentiality pending technical/legal confirmation"
        missing = []
        export_status = "Ready for review — do NOT release as a legal opinion without attorney review"

    clause_texts = [c.get("exact_passage") or c.get("act_title") or "" for c in clause_sources]
    clause_rows = [
        {
            "source": f"{c.get('act_title') or 'corpus standard source'} · {c.get('authority') or 'KB'}",
            "clause": (c.get("section_reference") or "full text"),
            "obligation": _clause_obligation(c.get("exact_passage") or c.get("act_title")),
            "standard_body": ", ".join(_standard_hint(f"{c.get('act_title')} {c.get('authority')}")) or "standard corpus",
        }
        for c in clause_sources
    ]
    if not clause_rows:
        clause_rows = [{
            "source": "[STANDARD CLAUSE TEXT REQUIRED]",
            "clause": "[paste the standard's clause]",
            "obligation": "Unclear — clause text required for classification",
            "standard_body": standard or "[STANDARD NOT PROVIDED]",
        }]

    # ETSI-style essentiality test (recorded as open questions — never auto-answered)
    test_rows = [
        {"q": "Q1 — Must the claim be implemented to comply with the (mandatory) clause?", "status": "To be confirmed from the normative clause text"},
        {"q": "Q2 — Is it technically impossible (no commercially reasonable alternative) to implement without infringing at the standard's relevant date?", "status": "Requires technical review against the standard version"},
        {"q": "Q3 — Was the feature part of the standard's technical specification / state of the art at the relevant date?", "status": "To verify against version + effective date"},
        {"q": "Q4 — Does any alternative achieve compliance without infringement?", "status": "Not assessed — alternative feasibility study required"},
        {"q": "Q5 — Does the mapping hold across all versions and modes?", "status": "Depends on the version gate"},
        {"q": "Q6 — Is the mapping anchored on a normative (mandatory/conditional) clause, not an informative one?", "status": "Checked via the clause-obligation classification"},
        {"q": "Q7 — Tentative essentiality position", "status": "Verdicts below are PRELIMINARY — attorney confirmation required"},
    ]

    # limitation × clause matching (only against retrieved standard clause text)
    chart_rows = []
    match_summary: dict[str, int] = {}
    for a in atoms:
        clause_text = clause_texts[0] if clause_texts else ""
        matched_piece, _ = _feature_match_label(a["limitation"], clause_text, _clause_obligation(clause_text))
        verdict = _essentiality_verdict(matched_piece, _clause_obligation(clause_text))
        match_summary[verdict] = match_summary.get(verdict, 0) + 1
        chart_rows.append({
            "claim": a["claim"],
            "limitation": a["limitation"],
            "foundation": a["foundation"],
            "standard_section": (clause_sources[0].get("section_reference") or "§ to be pinned") if clause_sources else "§ [CLAUSE TEXT REQUIRED]",
            "feature_match": matched_piece,
            "evidence_tier": _evidence_tier(clause_sources[0]) if clause_sources else "Tier 1 — none supplied",
            "obligation": _clause_obligation(clause_text),
            "verdict": verdict,
        })

    # evidence tiers — with 'Supports / Does not prove' role
    evidence_rows = []
    for c in cit:
        tier = _evidence_tier(c)
        tier.startswith("Tier 1") or tier.startswith("Tier 2")
        evidence_rows.append({
            "source": c.get("act_title") or "corpus source",
            "authority": c.get("authority") or "KB",
            "tier": tier,
            "role": "Supports a clause mapping" if tier.startswith("Tier 1") else (
                "Cross-check with the official standard" if tier.startswith("Tier 2") else "Does not prove a standard clause (context only)"),
        })
    if not evidence_rows:
        evidence_rows = [{"source": "[STANDARD / PATENT EVIDENCE REQUIRED]", "authority": "—",
                          "tier": "Tier 1 — none supplied", "role": "Attach the official standard text and patent claims."}]

    # product-implementation mapping (patent-to-product charts & version tracking)
    product_rows = []
    if inputs.get("product_versions") or product_desc:
        plow = product_desc.lower()
        for a in atoms:
            toks = [t for t in _tokens(a["limitation"]) if len(t) > 2]
            reported = sum(1 for t in toks if t in plow) >= max(1, len(toks) // 3)
            product_rows.append({
                "claim": a["claim"],
                "limitation": a["limitation"],
                "product_component": "[CONFIRM the corresponding component]",
                "implementation": "Reported in the product description" if reported else "Assumed — confirm",
                "versions": ", ".join(product_versions) if product_versions else "[PRODUCT VERSION REQUIRED]",
                "basis": ("token overlap with product description" if reported else "not described — confirmation required"),
            })
    else:
        product_rows = [{"claim": "—", "limitation": "Product input not supplied",
                         "product_component": "—", "implementation": "Not applicable to this chart type",
                         "versions": "—", "basis": "Provide product_desc / product_versions for a patent-to-product chart."}]

    licensing_note = ""
    if "licens" in chart_type.lower() or "pool" in chart_type.lower():
        licensing_note = ("Licensing / pool context: essentiality verdicts here are candidate positions for FRAND/pool "
                          "review; the final licensability call remains with the parties and their attorneys.")
    litigation_note = ""
    if "litigat" in chart_type.lower():
        litigation_note = ("Litigation preparation chart. It is NOT 'court-ready' — every mapping needs "
                           "attorney verification of the claim construction and the standard version relied on.")

    result["summary"] = (f"{chart_type}. {len(atoms)} atomic limitation(s) across {max(len(claims), 1)} claim(s); "
                         f"mapped against {len(clause_texts)} retrieved standard clause source(s); "
                         f"{status.split('—')[0].replace('STATUS:', '').strip()}.")
    result["note"] = "Chart-type classification → claim & standard gates → atomic limitations → clause classification → feature-match labels → five-level essentiality verdict → evidence-tiering → version management → export gate."

    result["findings"].append(_finding("cc-1", "Chart type", chart_type + ". " + type_note,
                                       "info" if chart_type.endswith("(confirm)") or chart_type.startswith("Not declared") else "info"))
    result["findings"].append(_finding("cc-2", "Input gates", status + ((" · Missing: " + "; ".join(missing)) if missing else ""),
                                       "error" if gates_blocked else "warning" if not version.strip() else "info"))
    result["findings"].append(_finding("cc-3", "Essentiality is not self-asserted",
                                       "Verdicts are five-level POSITIONS (potentially essential / conditional / not shown / not mapped / uncertain), never flat 'Essential/Non-essential'; the ETSI test stays open until attorney review.", "warning"))
    if not clause_sources:
        result["findings"].append(_finding("cc-4", "No standard clause text retrieved",
                                           "Corpus supplied regulatory/patent sources, not standard clauses. Those sources are context only and were NOT used as clause evidence.", "warning"))
    else:
        result["findings"].append(_finding("cc-4", "Clause evidence grounding",
                                           f"{len(clause_sources)} standard-body source(s) used for clause classification; all other passages tiered as context.", "info"))
    for c in cit[:4]:
        result["evidence"].append(_evidence("claim_chart", c.get("act_title"), c.get("authority") or "KB"))

    result["suggestions"] = [
        "Supply the claim text and the standard (name, number, version, effective date) to pass the input and version gates.",
        "Paste the exact clause text of the standard for each section you want mapped — clause-search against the corpus is not a substitute.",
        "Confirm which claims are DECLARED as essential (patent holder declaration) — the chart maps claims-to-standard, it does not infer declarations.",
        "For patent-to-product charts, provide product_desc and product_versions (hw/sw/fw) so versioned implementation rows are accurate.",
        "Before release: attorney review of claim construction, the standard version relied on, and the ETSI 'technical impossibility' test.",
    ]

    max(len(atoms), 1)
    result["sections"] += [
        _section("AICC input & gates", [
            {"item": "Chart ID / version", "value": f"{chart_id} (evidence freeze date {today}; supersedes earlier drafts, never overwritten)"},
            {"item": "Chart type", "value": chart_type},
            {"item": "Patent", "value": patent_no},
            {"item": "Status", "value": status},
            {"item": "Version gate", "value": version_status},
            {"item": "Export status", "value": export_status},
        ], ["item", "value"], "The chart is BLOCKED until claim text AND the standard are supplied; version gating blocks early export."),
        _section("Claims — atomic limitation breakdown", [
            {"claim": a["claim"], "limitation": a["limitation"], "type": a["type"], "foundation": a["foundation"]}
            for a in atoms
        ], ["claim", "limitation", "type", "foundation"],
           "Dependent claims inherit every limitation of their parent claim — inherited limitations are charted, not skipped."),
        _section("Standard identification & clause classification", [
            {"standard": standard or "[STANDARD NOT PROVIDED]", "version": version or "[VERSION NOT PROVIDED]",
             "obligation": r["obligation"], "source": r["source"], "body": r["standard_body"]}
            for r in clause_rows[:8]
        ], ["standard", "version", "obligation", "source", "body"],
           "Obligation classification: mandatory / conditional / optional / recommended / informative / example / deprecated / profile-specific / implementation-dependent / unclear. Only normative clauses can support a positive essentiality position."),
        _section("Limitation × claim-limitation chart (AICC rows)", [
            {"claim": r["claim"], "limitation": r["limitation"], "foundation": r["foundation"],
             "standard_section": r["standard_section"], "feature_match": r["feature_match"],
             "evidence_tier": r["evidence_tier"], "clause_obligation": r["obligation"], "verdict": r["verdict"]}
            for r in chart_rows
        ], ["claim", "limitation", "foundation", "standard_section", "feature_match", "evidence_tier", "clause_obligation", "verdict"],
           "Feature-match labels: Direct / Partial / Optional / Not found / Unclear — assigned from real clause text. Verdicts: Potentially essential / Conditional / Not shown to be essential / Not mapped / Uncertain."),
        _section("Essentiality test (ETSI-style open questions)", test_rows,
                 ["q", "status"], "The seven ETSI essentiality questions are recorded and left open for technical/legal confirmation — the agent never concludes essentiality, infringement or validity."),
        _section("Source-to-claim evidence tiers", evidence_rows,
                 ["source", "authority", "tier", "role"],
                 "Tier 1 official standard text (supports) → Tier 2 patent/declaration record → Tier 3 technical docs → Tier 4 regulatory/patent-office context → Tier 5 secondary. Regulatory and patent-office statements DO NOT evidence a standard clause."),
        _section("Product implementation mapping", [
            {"claim": r["claim"], "limitation": r["limitation"], "component": r["product_component"],
             "implementation": r["implementation"], "versions": r["versions"], "basis": r["basis"]}
            for r in product_rows[:12]
        ], ["claim", "limitation", "component", "implementation", "versions", "basis"],
           "Versioned hardware/software/firmware mapping — every product version the chart is claimed against must be listed."),
        _section("Licensing / litigation context", [
            {"item": "Licensing", "value": licensing_note or "Standard licensing call is not made by this tool."},
            {"item": "Litigation", "value": litigation_note or "Chart is for technical mapping; not 'court-ready'."},
            {"item": "Essentiality position counts", "value": "; ".join(f"{v}: {k}" for v, k in sorted(match_summary.items(), key=lambda kv: -kv[1])) or "no positions yet"},
        ], ["item", "value"], "Similarity and essentiality are distinct — a claim that looks similar is not 'essential' until the technical impossibility test is passed."),
        _section("Scope & limitations", [
            {"item": "Version management", "value": f"Chart {chart_id} freezes to the standard version named; a new standard release opens a NEW chart — prior charts are retained, never overwritten."},
            {"item": "Legal conclusion", "value": "This is technical claim-charting for attorney review — not an opinion of infringement, validity or essentiality."},
            {"item": "Evidence", "value": "Nothing is invented: pass the claim text, standard and version, and the actual clause/passage text for each row."},
        ], ["item", "value"]),
    ]
    return result
