"""Freedom-to-operate analysis, including registered design rights.

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
    _DEVICE_TERM,
    _DOSAGE_FORM,
    _detected_ratio,
    _keyword_phrases,
    _parameter_flag,
    _process_steps,
    _value_markers,
)
from app.services.innolab._shared import (
    _PURPOSE,
    _SOLVENT,
    _evidence,
    _finding,
    _markets,
    _retrieve,
    _section,
    _source_kind,
    _text,
)

__all__ = [
    "_source_category",
    "_fto_product_elements",
    "_fto_claim_rows",
    "_fto_activity_matrix",
    "_hub_fto",
    "_DESIGN_SILHOUETTE",
    "_DESIGN_CONFIGURATION",
    "_DESIGN_SURFACE",
    "_DESIGN_ORNAMENT",
    "_DESIGN_COLOUR",
    "_DESIGN_LABEL",
    "_DESIGN_FUNCTIONAL",
    "_design_source_category",
    "_design_article",
    "_design_visual_features",
    "_hub_design_fto",
]

def _source_category(authority: str) -> str:
    """Patent vs regulatory vs technical classification for FTO candidate screening."""
    kind = _source_kind(authority or "")
    if kind.startswith("Patent"):
        return "patent"
    if kind.startswith("Regulatory"):
        return "regulatory"
    if kind.startswith("Scientific"):
        return "technical"
    low = (authority or "").lower()
    if any(k in low for k in ("patent", "uspto", "epo", "wipo", "inpass", "ipo", "office action")):
        return "patent"
    if any(k in low for k in ("fda", "fssai", "fss", "ayush", "health canada", "efsa", "who",
                              "cdsco", "pharmacopoeia", "pharmacopeia", "monograph", "regulation",
                              "drugs and cosmetics", "drugs & cosmetics", "act 1940", "rules 1945")):
        return "regulatory"
    return "technical"


def _fto_product_elements(inputs: dict[str, Any], resolved: list[dict[str, Any]], claims_txt: str) -> list[dict[str, str]]:
    """Decompose a product into claim-relevant elements with confirmed/assumed/missing status.

    A generic product name (e.g. 'Ashwagandha nasal spray') is not a complete
    technical description — every element needed for claim mapping is listed and
    labelled."""
    texts = []
    for k in ("problem_text", "document_text", "disclosure_text", "formulation_text", "process_desc"):
        v = _text(inputs, k)
        if v:
            texts.append(v)
    blob = " ".join(texts)
    low = blob.lower()
    bot_names = [r.get("botanical_name") or r.get("raw_name", "") for r in resolved if r.get("raw_name")]
    markers = _value_markers(blob)
    solv = _SOLVENT.search(blob)
    ratio = _detected_ratio(blob, bot_names)
    device = _parameter_flag(_DEVICE_TERM.pattern, low)
    form = _parameter_flag(_DOSAGE_FORM.pattern, low)
    steps = _process_steps(_text(inputs, "process_desc") or blob)
    uses = claims_txt.strip() or cast("re.Match[str]", _PURPOSE.search(low)).group(0).strip() if _PURPOSE.search(low) else ""

    els: list[dict[str, str]] = []

    def _el(feature_id: str, feature: str, ftype: str, status: str, evidence: str, clarification: str) -> None:
        els.append({
            "feature_id": feature_id,
            "feature": feature,
            "type": ftype,
            "status": status,
            "evidence": evidence,
            "clarification": clarification,
        })

    active = ", ".join(bot_names[:3]) or "not stated"
    _el("F1", f"Active ingredient(s): {active}.", "Active ingredient",
        "Confirmed" if bot_names else "Missing",
        "User disclosure / resolved botanical name" if bot_names else "Not provided",
        "Plant part, extract type and identity of each botanical")
    _el("F2", "Extract standardization / active-marker concentration.",
        "Formulation",
        "Confirmed" if markers else "Missing",
        "; ".join(markers[:3]) if markers else "Not provided",
        "Marker name(s) and target range")
    _el("F3", "Solvent system (aqueous / hydroalcoholic / other).", "Formulation",
        "Confirmed" if solv else "Missing",
        "Solvent term stated in disclosure" if solv else "Not provided",
        "Exact solvent and water/alcohol ratio")
    _el("F4", "Controlled solvent ratio.", "Formulation",
        "Confirmed" if ratio else "Missing",
        ratio or "Not provided",
        "Numerical solvent ratio")
    _el("F5", "Excipients / carrier / vehicle.", "Formulation",
        "Missing", "Not provided", "Excipient names and concentrations")
    _el("F6", "Preservative and stabilizer.", "Formulation",
        "Missing", "Not provided", "Name and concentration / system")
    _el("F7", "pH and osmolality window.", "Formulation",
        "Missing", "Not provided", "Target pH / osmolality and buffers")
    _el("F8", "Delivery device / metering system.", "Device",
        "Confirmed" if device else "Missing",
        device or "Not provided",
        "Pump type, dose per actuation, droplet-size range")
    _el("F9", "Dosage form.", "Formulation",
        "Confirmed" if form else "Missing",
        form or "Not provided",
        "Final dosage form and container/closure")
    _el("P1", "Manufacturing / extraction process.", "Process",
        "Confirmed" if steps else "Missing",
        "; ".join(steps[:4]) if steps else "Not provided",
        "Full process sequence, temperatures and times")
    _el("U1", "Intended use / claim wording.", "Use",
        "Confirmed" if uses else "Missing",
        uses[:90] if uses else "Not provided",
        "Therapeutic vs structure/function vs wellness claim")
    return els


def _fto_claim_rows(elements: list[dict[str, str]]) -> list[dict[str, str]]:
    """Element-wise claim chart rows — Identified / Not identified / Uncertain.

    Mapping depends on product-data status: a missing product element cannot be
    marked 'Identified', and a claim is never called blocking without verified
    legal status and claim construction."""
    rows: list[dict[str, str]] = []
    for i, el in enumerate(elements, start=1):
        fea = el["feature"]
        status = el["status"]
        if status == "Confirmed":
            mapping, rationale = "Identified", "Product disclosure supports this element; live-claim and claim-construction review still required."
            q = "Does the element survive claim construction in the target market?"
        elif status in ("Missing", "Requires confirmation"):
            mapping, rationale = ("Uncertain",
                                  "The product feature is not specified in the disclosure — presence or absence cannot be concluded.")
            q = f"What is the exact value / composition? ({el['clarification']})"
        else:
            mapping, rationale = "Not identified", "No product documentation maps to this element."
            q = "Is this element required by the independent claim?"
        rows.append({
            "claim_element": f"Independent claim element {i} reciting the {el['type'].lower()}",
            "claim_language": f"reciting: {fea}",
            "product_evidence": f"Product data: {el['evidence']}",
            "preliminary_mapping": mapping,
            "rationale": rationale,
            "reviewer_question": q,
        })
    return rows


def _fto_activity_matrix(markets: list[str]) -> list[dict[str, str]]:
    acts = ("Manufacture", "Use", "Sale", "Offer for sale", "Import", "Export")
    return [
        {"jurisdiction": m, "activity": a, "status": "To confirm with user", "assessed": "Yes"}
        for m in (markets or []) for a in acts
    ]


def _hub_fto(inputs: dict[str, Any], result: dict[str, Any], resolved: list[dict[str, Any]], botanicals: str, claims_txt: str) -> dict[str, Any]:
    product = _text(inputs, "problem_text", "document_text", "disclosure_text", "formulation_text")
    markets = result.get("jurisdictions") or _markets(inputs)

    # 1) product decomposition: every claim-relevant element labelled Confirmed/Missing
    elements = _fto_product_elements(inputs, resolved, claims_txt)
    confirmed_el = [e for e in elements if e["status"] == "Confirmed"]
    missing_el = [e for e in elements if e["status"] == "Missing"]

    # 2) retrieval across target jurisdictions
    product_blob = f"{botanicals} {product} {_text(inputs, 'process_desc')} {claims_txt}".strip()
    cit = result["citations"] or _retrieve(product_blob, top_k=5)

    # 3) candidate screening — source category first, then screen label + reason
    screened: list[dict[str, Any]] = []
    for idx, c in enumerate(cit, start=1):
        cat = _source_category(c.get("authority") or "")
        title_low = (c.get("act_title") or "").lower()
        # A statute/rule/guideline/landscape is NEVER a claim-bearing patent,
        # even when its publisher authority name contains 'patent office'.
        if cat == "patent" and any(k in title_low for k in (
                " act", "rules", "guideline", "guidance", "notification", "landscape",
                " report", "manual", "standard operating", " comments", "draft for",
                "compendium", " directory", "handbook", "white paper", "schedule")):
            cat = "regulatory"
        if cat == "patent":
            label = "Include for claim review — status uncertain"
            reason = ("Patent-family document. Legal status at the national register, live independent claims and "
                      "expiry are NOT verified offline — official-register verification is required before any risk conclusion.")
        elif cat == "regulatory":
            label = "Background only (regulatory / technical context)"
            reason = ("Regulatory or pharmacopoeial document — supports product classification, ingredient identity and "
                      "compliance context, but is NOT a patent right and cannot by itself block the product.")
        else:
            label = "Status uncertain — verify legal status"
            reason = "General technical evidence; no verified patent claim or legal-status data."
        screened.append({
            "ref_id": f"C{idx}",
            "reference": c.get("act_title") or "passage",
            "authority": c.get("authority") or "KB",
            "source_category": cat,
            "screen_label": label,
            "reason": reason,
            "citation": c,
        })

    patent_candidates = [s for s in screened if s["source_category"] == "patent"]
    background_pool = [s for s in screened if s["source_category"] != "patent"]

    # 4) element-wise claim chart (mapping driven by product-data status, never random)
    claim_rows = _fto_claim_rows(elements)
    identified = sum(1 for r in claim_rows if r["preliminary_mapping"] == "Identified")
    sum(1 for r in claim_rows if r["preliminary_mapping"] == "Uncertain")

    # 5) risk classification — relevant jurisdiction + live right + mapped claim
    #    elements + covered commercial activity. Offline, legal status is never
    #    verified, so High cannot be certified; Medium is the ceiling for a
    #    patent-candidate screening, and regulations are never a risk.
    if not cit:
        risk, risk_reason = ("Unknown",
                             "No candidate passage was retrieved from the local corpus. Absence of a corpus hit is not clearance — extend the patent search and repeat the screening.")
    elif not patent_candidates:
        risk, risk_reason = ("Low",
                             "No patent-family candidate was found in the searched corpus. Retrieved items are regulatory/technical background and do not constitute a blocking right. This is a screening result, not clearance — official-register checks are still recommended.")
    else:
        risk, risk_reason = ("Medium",
                             f"{len(patent_candidates)} patent-family candidate(s) found; {identified}/{len(claim_rows)} product elements are identified. Legal status, live independent claims and claim construction are not verified offline, so risk cannot yet be certified as High.")

    result["summary"] = (f"FTO screening: {risk} risk — {identified}/{len(claim_rows)} product element(s) identified; "
                         f"{len(patent_candidates)} patent candidate(s) to verify at national registers.")
    result["note"] = "Product/process decomposition → confirm → jurisdiction+activity matrix → multi-strategy search → candidate screening → element-wise claim chart → risk classification with reasons."
    result["findings"].append(_finding("fto-1", "Confirmed product elements",
                                       f"{len(confirmed_el)} of {len(elements)} claim-relevant elements are confirmed; {len(missing_el)} are missing and must be supplied before a final FTO conclusion.",
                                       "warning" if missing_el else "info"))
    result["findings"].append(_finding("fto-2", "Candidate screening",
                                       f"{len(patent_candidates)} patent candidate(s); {len(background_pool)} regulatory/technical item(s) kept as background only.",
                                       "warning" if patent_candidates else "info"))
    result["findings"].append(_finding("fto-3", "Risk basis",
                                       risk_reason, "error" if risk == "High" else "warning" if risk == "Medium" else "info"))
    result["findings"].append(_finding("fto-4", "Legal-status verification",
                                       "Status must be confirmed on the official national register (granted/pending/expired/lapsed/abandoned) — never inferred from publication alone.", "warning"))
    for market in markets:
        result["findings"].append(_finding(f"fto-m-{re.sub(r'[^A-Za-z]', '', market)[:12]}", market,
                                           "Verify claims in force + legal status at the national register for manufacture, use, sale, import and export activities.", "info"))
    for c in cit[:3]:
        result["evidence"].append(_evidence("fto", c.get("act_title"), c.get("authority") or "KB"))
    result["suggestions"] = [
        "Confirm the missing product features (solvent ratio, excipients, preservative, pH, device, process, claim wording) — the Medium risk is driven as much by missing data as by found patents.",
        "Verify legal status of every patent candidate at the official national register (granted/pending/expired/lapsed).",
        "Obtain the full independent claims of each patent candidate and re-run the element-wise mapping.",
        "Regulations and monographs were kept as background — they cannot block the product by themselves.",
        "Run a formal FTO opinion with a patent professional before launch; designate owners for redesign / licence / monitor / timing options.",
    ]

    activity_rows = _fto_activity_matrix(markets)
    screening_rows = [
        {"ref_id": s["ref_id"], "reference": s["reference"], "authority": s["authority"],
         "source_category": s["source_category"], "screen_label": s["screen_label"], "reason": s["reason"]}
        for s in screened
    ]
    if not screening_rows:
        screening_rows = [{"ref_id": "—", "reference": "no candidate retrieved",
                           "authority": "—", "source_category": "—",
                           "screen_label": "extend the patent search", "reason": "low corpus coverage"}]

    risk_rows = [
        {"risk_level": risk, "references": " · ".join(f"{p['ref_id']} {p['reference']}" for p in patent_candidates[:4]) or "—",
         "basis": risk_reason},
        {"risk_level": "Background only", "references": " · ".join(f"{b['ref_id']} {b['reference']}" for b in background_pool[:4]) or "—",
         "basis": "Regulatory/technical documents support product classification and context; they are NOT patent-blocking rights."},
    ]

    movers = []
    if patent_candidates:
        movers.append({"direction": "Risk may move to HIGH if", "condition": "a live enforceable claim in a target jurisdiction maps to every essential product element and the commercial activity is covered."})
    movers.append({"direction": "Risk may move to LOW if", "condition": "one or more required claim elements are absent from the product, or the right is expired/lapsed/abandoned or not present in the target jurisdiction."})
    if missing_el:
        movers.append({"direction": "Risk resolution requires", "condition": "completing " + ", ".join(e["feature_id"] for e in missing_el) + " before the mapping below is reliable."})

    result["sections"] += [
        _section("Structured product features (confirm & edit)", [
            {"feature_id": e["feature_id"], "feature": e["feature"], "type": e["type"],
             "status": e["status"], "evidence": e["evidence"], "clarification": e["clarification"]}
            for e in elements
        ], ["feature_id", "feature", "type", "status", "evidence", "clarification"],
           "A generic product name is not a complete technical description. Every element needed for claim mapping is listed with Confirmed/Missing status; missing elements are flagged as 'Required before a final FTO conclusion'."),
        _section("Jurisdiction & commercial-activity matrix", activity_rows,
                 ["jurisdiction", "activity", "status", "assessed"],
                 "FTO is assessed per jurisdiction and per activity (manufacture/use/sale/offer for sale/import/export). One global FTO conclusion is never given."),
        _section("Keyword & terminology expansion", [
            {"feature": e["feature"][:60], "synonyms": "botanical / common / chemical variants", "broader/narrower": "broader + narrower concept", "patent_language_variants": "technical alternatives · patent-language variation"}
            for e in elements[:6]
        ], ["feature", "synonyms", "broader/narrower", "patent_language_variants"], "Each feature expands into related terminology so the search finds patents beyond matching titles."),
        _section("Build FTO search strategy (trace)", [
            {"strategy": "Semantic retrieval", "route": "features as natural-language query", "markets": ", ".join(markets) or "specified markets"},
            {"strategy": "Keyword & Boolean queries", "route": " · ".join(_keyword_phrases(product_blob, limit=6)) or "feature terms combined", "markets": ", ".join(markets) or "specified markets"},
            {"strategy": "Classification codes", "route": "IPC/CPC classes from the feature context", "markets": ", ".join(markets) or "specified markets"},
            {"strategy": "Citations & families", "route": "citation signals + family tracing (deduplicated)", "markets": ", ".join(markets) or "specified markets"},
            {"strategy": "Legal-status route", "route": "official national registers for each candidate family", "markets": ", ".join(markets) or "specified markets"},
        ], ["strategy", "route", "markets"], "A transparent search path showing how candidates were retrieved, refined and added to the review scope."),
        _section("Candidate screening (status labels)", screening_rows,
                 ["ref_id", "reference", "authority", "source_category", "screen_label", "reason"],
                 "Screening keeps uncertainty visible. Regulations, monographs and technical papers are labelled 'Background only' — they are never placed in a patent-risk bucket unless an actual enforceable patent claim is involved."),
        _section("Element-wise claim chart (independent claims first)", [
            {"claim_element": r["claim_element"], "claim_language": r["claim_language"],
             "product_evidence": r["product_evidence"], "preliminary_mapping": r["preliminary_mapping"],
             "rationale": r["rationale"], "reviewer_question": r["reviewer_question"]}
            for r in claim_rows
        ], ["claim_element", "claim_language", "product_evidence", "preliminary_mapping", "rationale", "reviewer_question"],
           "Maps each claim element to product evidence — Identified / Not identified / Uncertain, with rationale and the reviewer question that still needs resolution. A claim is never marked blocking if a required element is missing or legal status is unverified."),
        _section("FTO risk classification (High / Medium / Low)", risk_rows,
                 ["risk_level", "references", "basis"], "Risk is based on claim mapping + legal status + jurisdiction + activity, never on a similarity score or source authority."),
        _section("Risk movers", movers, ["direction", "condition"], "What would change the preliminary classification."),
        _section("Regulatory context (SEPARATE — not a patent right)", [
            {"item": "Classification questions", "value": "Whether the product is a food, dietary supplement, drug or other regulated category depends on intended use, claims, route and ingredients — per jurisdiction."},
            {"item": "Cited regulatory sources", "value": " · ".join(f"{b['reference']} ({b['authority']})" for b in background_pool[:5]) or "none retrieved in this run"},
            {"item": "FTO status of these sources", "value": "Not a patent right and not a patent-blocking reference."},
        ], ["item", "value"], "Regulatory analysis is kept separate from patent FTO analysis."),
        _section("Design-around options (only if a blocking claim is confirmed)", [
            {"direction": "Change the formulation element", "detail": "Solvent system / ratio, excipients, preservative, pH, marker standardization"},
            {"direction": "Change the delivery device", "detail": "Pump type, metering, droplet-size range, container/closure"},
            {"direction": "Change the process", "detail": "Extraction sequence, temperature/time windows, purification, filling"},
            {"direction": "Change activity / jurisdiction / timing", "detail": "Align with design-around re-mapping; verify each option against the FULL claim scope"},
        ], ["direction", "detail"], "Any design-around must be re-checked against the full independent claim scope — changing one label or ingredient is not proof of avoiding infringement."),
        _section("Options & accountable review", [
            {"option": "Redesign / design-around", "trigger": "potentially blocking claim or high technical overlap", "owner": "product engineering + IP team"},
            {"option": "Seek a licence", "trigger": "live claim maps to all required product elements", "owner": "legal / business"},
            {"option": "Monitor pending application", "trigger": "relevant application pending or status uncertain", "owner": "IP team (set review date + claim-change alerts)"},
            {"option": "Change market or timing", "trigger": "jurisdiction- or time-specific risk", "owner": "commercial + IP team"},
            {"option": "Obtain a formal legal opinion", "trigger": "High or uncertain risk before launch", "owner": "qualified patent professional"},
        ], ["option", "trigger", "owner"], "Each next step has an accountable owner."),
        _section("FTO search scope & strategy appendix", [
            {"item": "Jurisdictions", "value": ", ".join(markets) or "specified markets"},
            {"item": "Review date", "value": "current corpus snapshot — legal status must be re-verified at the office"},
            {"item": "Search routes", "value": "technical/functional terms · classifications · semantic · citations · families · legal-status"},
            {"item": "Screening labels", "value": "include for claim review · background only · status uncertain"},
            {"item": "Excluded / uncertain", "value": "see screening section; no hidden exclusions"},
        ], ["item", "value"], "Appendix with keywords, Boolean queries and source selection — traceable back to the sources."),
    ]
    return result


_DESIGN_SILHOUETTE = re.compile(
    r"\b(tall|short|wide|slim|narrow|cylindrical|hexagonal|hex|square|rectangular|oval|round|rounded|"
    r"tapered|taper|conical|prismatic|faceted|asymmetric|asymmetrical|curved|bulbous|elongated|"
    r"shouldered|flat)\b", re.I,
)


_DESIGN_CONFIGURATION = re.compile(
    r"\b(shoulder|neck|cap|closure|base|body|panel|sidewall|rim|lip|transition|opening|aperture)\b", re.I,
)


_DESIGN_SURFACE = re.compile(
    r"\b(grip|ridge|ridges|rib|ribs|ribbed|emboss|embossing|groove|grooved|texture|textured|matte|"
    r"gloss|glossy|satin|polished|brushed|finish|recess|deboss|engrav|stipple)\b", re.I,
)


_DESIGN_ORNAMENT = re.compile(
    r"\b(leaf|leaves|botanical|floral|ornament|ornamentation|motif|pattern|swirl|wave|geometric|"
    r"decorat|symbol|logo|mark|graphic|illustration|herb|vine|flower)\b", re.I,
)


_DESIGN_COLOUR = re.compile(
    r"\b(amber|green|brown|black|white|clear|transparent|opaque|blue|red|gold|golden|silver|ivory|"
    r"cream|colour|color|shade|tint)\b", re.I,
)


_DESIGN_LABEL = re.compile(r"\b(label|labelled|labeled|wrapper|band|tag|typography|font)\b", re.I)


_DESIGN_FUNCTIONAL = re.compile(
    r"\b(pump|sprayer|spray|dropper|tamper|seal|airtight|dose|dosing|meter|metering|valve|actuator|"
    r"actuat|nozzle|mechanism|thread|screw|hinge|fitment|child[- ]?resistant|insert|orifice)\b", re.I,
)


def _design_source_category(authority: str) -> str:
    """Design-register vs patent vs regulatory vs technical screening label.

    A source only counts as a design-right record if it comes from an official
    national design register / design-patent database or the Hague system.
    Patent families, regulations and technical papers are never treated as
    design-right evidence."""
    low = (authority or "").lower()
    if "design" in low and any(k in low for k in (
        "register", "database", "db", "search", "hague", "industrial design", "design act",
        "designs act", "e-register", "cgpdiy", "design patent", "d-quest",
    )):
        return "design_register"
    kind = _source_kind(authority or "")
    if kind.startswith("Patent"):
        return "patent"
    if kind.startswith("Regulatory"):
        return "regulatory"
    if any(k in low for k in ("patent", "uspto", "epo", "wipo", "ipo", "inpass", "office action")):
        return "patent"
    if any(k in low for k in ("fda", "fssai", "fss", "ayush", "health canada", "efsa", "who",
                              "cdsco", "pharmacopoeia", "pharmacopeia", "dshea")):
        return "regulatory"
    return "technical"


def _design_article(text: str) -> str:
    low = (text or "").lower()
    for art in ("nasal spray bottle", "dropper bottle", "spray bottle", "blister pack", "bottle",
                "jar", "tube", "box", "pouch", "vial", "container", "carton", "sachet", "label",
                "packaging package", "packaging", "package", "cap", "dropper"):
        if art in low:
            return art.title()
    return "Article to be confirmed (photograph / CAD drawing / line drawing / 3D model required)"


def _design_visual_features(text: str) -> list[dict[str, str]]:
    """Decompose a described design into atomic visual features (V1…Vn).

    Each feature carries a category (Silhouette / Configuration / Surface /
    Ornamentation / Colour / Label / Functional) and a functional-relevance
    classification (Functional / Ornamental / Mixed / Unknown). A generic
    phrase such as 'herbal bottle design' is never emitted as one feature —
    visual features are separated from functional features, and anything that
    cannot be read from the text is flagged 'not described'."""
    low = (text or "").lower()
    feats: list[dict[str, str]] = []
    seen: set = set()

    def _add(desc: str, cat: str, func: str) -> None:
        key = desc.lower().strip()
        if len(key) < 4 or key in seen:
            return
        seen.add(key)
        feats.append({
            "feature": desc[:100],
            "category": cat,
            "functional_relevance": func,
            "evidence": "Described in the submitted text only",
            "confirmation": "Pending",
        })

    sil = sorted({m for m in _DESIGN_SILHOUETTE.findall(low)})
    cfg = sorted({m for m in _DESIGN_CONFIGURATION.findall(low)})
    surf = sorted({m for m in _DESIGN_SURFACE.findall(low)})
    orn = sorted({m for m in _DESIGN_ORNAMENT.findall(low)})
    cols = sorted({m for m in _DESIGN_COLOUR.findall(low)})
    labs = sorted({m for m in _DESIGN_LABEL.findall(low)})
    func = sorted({m for m in _DESIGN_FUNCTIONAL.findall(low)})

    if sil:
        _add("Overall " + " ".join(sil) + " silhouette.", "Silhouette",
             "Mixed" if any(w in sil for w in ("tapered", "shouldered", "rounded", "curved", "flat")) else "Ornamental")
    else:
        _add("Overall silhouette — not described; extract from front / side / rear / top / bottom views.",
             "Silhouette", "Ornamental")

    if cfg:
        for w in cfg[:4]:
            rel = "Mixed" if w in ("cap", "closure", "rim", "lip", "opening", "aperture") else "Ornamental"
            _add(f"{w.capitalize()} configuration as described.", "Configuration", rel)
    else:
        _add("Container / closure configuration — not described.", "Configuration", "Ornamental")

    if surf:
        mixed = any(w in surf for w in ("grip", "ridge", "ridges", "rib", "ribs", "ribbed"))
        _add("Surface treatment: " + ", ".join(surf) + ".", "Surface",
             "Mixed" if mixed else "Ornamental")
    else:
        _add("Surface treatment (texture, finish, grip ridges, embossing) — not described.", "Surface", "Ornamental")

    if orn:
        _add("Ornamentation: " + ", ".join(orn) + ".", "Ornamentation", "Ornamental")
    else:
        _add("Ornamentation / decorative marks — not described.", "Ornamentation", "Ornamental")

    if cols:
        _add("Colour arrangement: " + ", ".join(cols) + ".", "Colour", "Ornamental")
    else:
        _add("Colour arrangement — not described.", "Colour", "Ornamental")

    if labs:
        _add("Label layout: " + ", ".join(labs) + ".", "Label", "Ornamental")
    else:
        _add("Label layout — not described.", "Label", "Ornamental")

    if func:
        _add("Functional feature(s): " + ", ".join(func) + ".", "Functional", "Functional")
    else:
        _add("Functional features (opening, spraying, dosing, tamper, grip geometry) — not described.",
             "Functional", "Functional")

    return feats[:12]


def _hub_design_fto(inputs: dict[str, Any], result: dict[str, Any], botanicals: str) -> dict[str, Any]:
    design = _text(inputs, "problem_text", "document_text", "disclosure_text") or "described design"
    markets = result.get("jurisdictions") or _markets(inputs) or ["specified market"]
    image_input = inputs.get("images") or inputs.get("image_ids") or inputs.get("design_images") or inputs.get("views")
    has_images = bool(
        (isinstance(image_input, list) and image_input)
        or (isinstance(image_input, str) and image_input.strip())
    )

    article = _design_article(design)
    features = _design_visual_features(design)

    # register connection — deterministic: no national design register is
    # reachable in this offline build, so NOTHING is verified below.

    # candidate screening — only official design-register records are candidates;
    # patents, regulations and papers are background/excluded.
    screened: list[dict[str, Any]] = []
    for idx, c in enumerate(result.get("citations") or [], start=1):
        cat = _design_source_category(c.get("authority") or "")
        if cat == "design_register":
            label, reason = ("Status uncertain — official register verification required",
                             "Design-right record type. Registration number, representations, status and term "
                             "are NOT verified offline; verify each field on the national register.")
        elif cat == "patent":
            label, reason = ("Exclude — utility-patent record, not a design right",
                             "Utility patent / patent-family document covers functional matter, not the ornamental "
                             "appearance of the article.")
        elif cat == "regulatory":
            label, reason = ("Background only (regulatory / technical context)",
                             "Regulatory or pharmacopoeial document — describes practice and classification, not a "
                             "design right.")
        else:
            label, reason = ("Exclude — technical background, no design representation",
                             "General technical paper or content without a registered design representation to compare.")
        screened.append({
            "candidate": f"C{idx}",
            "reference": c.get("act_title") or "passage",
            "authority": c.get("authority") or "KB",
            "source_category": cat,
            "screen_label": label,
            "reason": reason,
        })

    design_candidates = [s for s in screened if s["source_category"] == "design_register"]
    background = [s for s in screened if s["source_category"] != "design_register"]

    # per-jurisdiction register & legal-status rows — all UNVERIFIED by design.
    status_rows = [
        {"jurisdiction": m, "record": "Not retrieved", "registration_number": "None",
         "article_classification": "To be confirmed against the national schedule",
         "legal_status": "Not verified", "last_verified": "— (offline build, no register connection)",
         "fto_implication": "No risk classification can be finalised until status and representations are "
                            "verified on the official register."}
        for m in markets
    ]

    # risk classification: register-gated. Not connected -> Unknown, never Medium.
    risk = "Unknown / Not determinable"

    # visual comparison framework — no reference representations -> not comparable.
    vis_dims = ["Silhouette", "Proportion and scale", "Configuration", "Shoulder and neck profile",
                "Cap / closure appearance", "Surface treatment", "Ornamentation", "Colour arrangement",
                "Label arrangement", "Decorative mark placement", "Visible functional features",
                "Overall consumer impression"]
    comp_rows = [
        {"visual_dimension": d, "proposed_design": "From described features only (text)",
         "reference_design": "None retrieved", "similarity": "Not comparable — no verified reference representation",
         "importance": "High", "note": "Compare after acquiring the reference design's official representations."}
        for d in vis_dims
    ]

    # IP-risk separation
    ip_rows = [
        {"ip_category": "Registered design / design patent", "relevant_future": "Ornamental appearance of the article (shape, configuration, pattern, ornamentation, colour)",
         "preliminary_risk": "Unknown — no verified register match", "next_action": "Search India (IP India design e-register), USPTO design patents, Canadian industrial-design register"},
        {"ip_category": "Trademark / trade dress", "relevant_future": "Logo, brand name, symbol, colour scheme, overall trade dress",
         "preliminary_risk": "Separate review required", "next_action": "Trademark + trade-dress clearance per jurisdiction"},
        {"ip_category": "Copyright", "relevant_future": "Label artwork, illustration, graphic design",
         "preliminary_risk": "Separate review required", "next_action": "Copyright clearance for decorative artwork"},
        {"ip_category": "Passing-off / unfair competition", "relevant_future": "Overall packaging presentation, colour scheme, layout",
         "preliminary_risk": "Separate review required", "next_action": "Market-confusion assessment"},
        {"ip_category": "Utility patent", "relevant_future": "Functional mechanism, formulation, process, technical effect",
         "preliminary_risk": "Separate, out of Design-FTO scope", "next_action": "Run the FTO Search agent separately"},
    ]

    result["summary"] = (f"Design-FTO screening (text-based) for {article}: design-register status NOT verified; "
                         f"preliminary risk {risk.lower()}. No registration number, official representation or "
                         f"jurisdiction-specific comparison was retrieved.")
    result["note"] = "Design article identification → visual/functional separation → atomic visual features → design-register search (not connected) → candidate screening → register & legal-status table → visual comparison → separated IP risk → design-arounds."
    result["findings"].append(_finding("dfto-1", "Design-register status",
                                       "Not verified — no national design-register record or registration number was "
                                       "retrieved in this build. Status must be confirmed on the official register.",
                                       "warning"))
    result["findings"].append(_finding("dfto-2", "Risk classification",
                                       f"{risk} — because there is no verified reference design in a relevant "
                                       f"jurisdiction. 'Medium' is NOT assigned without a register search, verified "
                                       f"registration and a visual comparison.", "warning"))
    result["findings"].append(_finding("dfto-3", "Image evidence",
                                       "No product image or design-register image was compared. Text-based preliminary "
                                       "assessment only; image-to-register comparison required (front, rear, side, top, "
                                       "bottom, perspective views).", "warning" if not has_images else "info"))
    result["findings"].append(_finding("dfto-4", "Visual/functional separation",
                                       f"{len(features)} atomic visual feature(s) extracted; functional features "
                                       f"(pump, dosing, tamper, grip geometry) are reported separately and never "
                                       f"counted as ornamental risk by themselves.", "info"))
    result["findings"].append(_finding("dfto-5", "Source screening",
                                       f"{len(design_candidates)} design-right candidate(s); "
                                       f"{len(background)} patent/regulatory/technical item(s) kept as background or "
                                       f"excluded — they are not design-right evidence.", "info"))
    result["findings"].append(_finding("dfto-6", "Separate IP risks",
                                       "Design, trademark, copyright, passing-off and utility-patent risks are reported "
                                       "in separate lines — one design-FTO score is never produced.", "info"))

    result["suggestions"] = [
        "Upload complete multi-view design drawings (front, rear, side, top, bottom, perspective) and confirm the extracted visual features.",
        "Search the official design registers of each target market (India: IP India Design Search + e-register; US: USPTO design patents; Canada: industrial-design register) and record registration/application numbers.",
        "Verify legal status with a date (registered & active / pending / expired / lapsed / refused / not found) — never infer from publication alone.",
        "Compare the overall visual impression of the proposed article with each active/pending relevant registration.",
        "Run separate trademark, copyright and passing-off (trade-dress) checks; run the utility-patent FTO agent for functional features.",
        "Obtain professional design clearance before final artwork or launch.",
    ]

    feature_rows = [
        {"feature_num": f"V{i + 1}", "feature": f["feature"], "category": f["category"],
         "functional_relevance": f["functional_relevance"], "evidence": f["evidence"],
         "confirmation": f["confirmation"]}
        for i, f in enumerate(features)
    ]
    separation_rows = [
        {"feature": f["feature"], "functional_role": "Operating mechanism / grip / ergonomics"
         if f["functional_relevance"] == "Functional" else "None (visual only)" if f["functional_relevance"] == "Ornamental"
         else "Functionally relevant AND visually distinctive",
         "visual_role": "Overall impression / layout / ornamentation",
         "design_fto_relevance": "Not counted as ornamental risk alone"
         if f["functional_relevance"] == "Functional" else "Relevant to the visual impression"
         if f["functional_relevance"] == "Ornamental" else "Mixed functional + visual relevance — legal review required",
         "review_note": "Do not recommend changing a purely functional feature as a design-around unless the product "
                        "function can be preserved and utility-patent / regulatory implications are reviewed."}
        for f in features
    ]
    screening_rows = screened or [
        {"candidate": "—", "reference": "no candidate retrieved", "authority": "—",
         "source_category": "—", "screen_label": "extend to official design registers", "reason": "local corpus has no design-register records"}
    ]
    da_rows = [
        {"direction": "Change the silhouette", "detail": "Alter overall height-to-width ratio, body cross-section, shoulder transition or base geometry.",
         "function_preserved": "Yes — appearance-only change", "validation": "Re-compare the overall visual impression with each candidate after change"},
        {"direction": "Differentiate surface treatment", "detail": "Remove/reposition grip ridges, change embossing, texture or matte/gloss distribution.",
         "function_preserved": "Verify grip/sealing/dispensing still works", "validation": "Check whether ridges are functional before altering them"},
        {"direction": "Replace the label & marks", "detail": "Change label shape, text layout, logo position or typography; use independently created artwork.",
         "function_preserved": "Yes — artwork-only change", "validation": "Run separate trademark and copyright checks on the new label"},
        {"direction": "Change the colour arrangement", "detail": "Change dominant colour, cap/body contrast or label background.",
         "function_preserved": "Yes", "validation": "A colour change alone may not avoid design or trade-dress conflict — reassess overall impression"},
        {"direction": "Change the configuration", "detail": "Cap geometry, cap-to-body ratio, panel arrangement, visible transitions.",
         "function_preserved": "Verify sealing/closing still works", "validation": "Mixed cap geometry needs functional review before a design-around"},
    ]

    result["sections"] += [
        _section("Design FTO scope", [
            {"item": "Design article", "value": article},
            {"item": "Design scope", "value": "Container / cap / label / packaging / surface ornamentation — to be confirmed against the proposed commercial article"},
            {"item": "Visual features included", "value": "V1–V" + str(len(features)) + " (below)"},
            {"item": "Functional features excluded", "value": "Opening / spray / pump / dropper / tamper / dose-measuring / ergonomic grip geometry"},
            {"item": "Jurisdictions", "value": ", ".join(markets)},
            {"item": "Commercial activities", "value": "Manufacture · use · sale · offer for sale · import · export (to confirm with user)"},
            {"item": "Review date", "value": "current build — legal status must be re-verified at the official register with a date"},
            {"item": "Design-register connection", "value": "Not connected — register verification pending"},
            {"item": "Article classification", "value": "To be confirmed against the national design-classification schedule"},
        ], ["item", "value"], "One global 'design FTO verdict' is not given — the assessment is per article, per jurisdiction and per commercial activity."),
        _section("Image and drawing inventory", [
            {"item": "Images / drawings supplied", "value": ("Yes — " + str(len(image_input)) + " view(s) attached")
             if isinstance(image_input, list) else "Yes — single image" if has_images else "None"},
            {"item": "Views available", "value": ", ".join(str(v) for v in (isinstance(image_input, list) and image_input) or [])
             if isinstance(image_input, list) else str(image_input) if isinstance(image_input, str) else "None supplied"},
            {"item": "Hidden / unclear features", "value": "Cannot be inferred from text alone — rear, side, top, bottom and perspective views required"},
            {"item": "Image-based comparison", "value": "Not performed — no design-register image retrieved for the reference side of the comparison"},
            {"item": "Text-only limitation", "value": "Text-based preliminary assessment only; visual similarity cannot be scored reliably without images."},
        ], ["item", "value"], "The image gate decides what the visual comparison is allowed to conclude."),
        _section("Structured visual features (confirm & edit)", feature_rows,
                 ["feature_num", "feature", "category", "functional_relevance", "evidence", "confirmation"],
                 "Features are split into atomic visual units (never one combined phrase like 'herbal bottle design'). Each feature is classified Functional / Ornamental / Mixed — functional features (pump, dosing, tamper, grip geometry) are never counted as ornamental risk by themselves. Confirm, edit, remove or mark each feature as essential / functional / optional before the register search."),
        _section("Functional vs ornamental separation", separation_rows,
                 ["feature", "functional_role", "visual_role", "design_fto_relevance", "review_note"],
                 "A feature may be both functional and visually relevant — such features are marked 'Mixed functional + visual relevance — legal review required'."),
        _section("Image-to-register search strategy (planned routes)", [
            {"route": "Product-category search", "input": "article category (bottle / nasal spray container / cosmetic container / pharmaceutical or herbal packaging / pump dispenser / dropper bottle / packaging box)"},
            {"route": "Visual-feature search", "input": "silhouette · surface treatment · ornamentation · colour · label terms as search aids, not legal conclusions"},
            {"route": "Classification search", "input": "relevant design-classification codes per national schedule (to be recorded per jurisdiction)"},
            {"route": "Image-similarity search", "input": "image embeddings, silhouette / proportion / surface / ornamentation / colour comparison — candidate ranking only, not infringement determination"},
            {"route": "Owner / competitor search", "input": "competitor names, brand owners, packaging companies, design registrants"},
            {"route": "Registration-number search", "input": "official record, all views, classification, owner, dates, status, disclaimers"},
            {"route": "Family & related-design search", "input": "priority filings, national registrations, continuations, same-owner design families"},
        ], ["route", "input"], "The search is executed against official design registers; registrations must carry numbers, views, classification and verified status."),
        _section("Candidate screening (status labels)", screening_rows,
                 ["candidate", "reference", "authority", "source_category", "screen_label", "reason"],
                 "Candidates are screened by record type. Utility patents, regulations (FDA / FSSAI / AYUSH / pharmacopoeia) and technical papers are NOT design-right evidence — they are background or excluded. A candidate is never labelled 'high risk' merely because it is an official source."),
        _section("Official design-register & legal-status table", status_rows,
                 ["jurisdiction", "record", "registration_number", "article_classification", "legal_status", "last_verified", "fto_implication"],
                 "Register not connected in this build — every row is UNVERIFIED. No risk classification can be finalised until status and representations are verified on the official register."),
        _section("Visual comparison framework (overall impression)", comp_rows,
                 ["visual_dimension", "proposed_design", "reference_design", "similarity", "importance", "note"],
                 "Comparison is by overall visual impression — silhouette, proportion, configuration, surface treatment, ornamentation, colour and label arrangement — never by product name, ingredient or function alone. 'Not comparable' is recorded because no verified reference representation was retrieved."),
        _section("Visual similarity score", [
            {"item": "Visual similarity score", "value": "Not calculated"},
            {"item": "Reason", "value": "No product image and no design-register image were available. Text descriptions are insufficient for reliable image-to-register comparison."},
            {"item": "Score semantics", "value": "If a numeric score is ever produced it measures VISUAL RESEMBLANCE ONLY — never probability of infringement, a legal-risk percentage, or a chance of losing a case."},
        ], ["item", "value"], "Never assign a final risk level 'after image match' without the image match."),
        _section("Design-right vs other IP risks (separate)", ip_rows,
                 ["ip_category", "relevant_future", "preliminary_risk", "next_action"],
                 "Design, trademark, copyright, passing-off and utility-patent risks are kept separate — changing a leaf mark reduces one design/trademark issue but may not resolve overall trade-dress or copyright risk."),
        _section("Design-around suggestions (function-preserving)", da_rows,
                 ["direction", "detail", "function_preserved", "validation"],
                 "Every design-around must preserve the required product function and be validated by re-comparing the overall visual impression — a colour change alone does not avoid design or trade-dress conflict."),
        _section("Limitations & required next steps", [
            {"item": "Register connection", "value": "Not connected — official national design registers of India, the US and Canada must be searched"},
            {"item": "Text-only analysis", "value": "Complete image-to-register comparison requires front, rear, side, top, bottom and perspective views"},
            {"item": "Unverified status", "value": "Registration number, legal status, term and representations require official-register verification"},
            {"item": "Confirmed rule", "value": "Register search not done, reference registration number not retrieved and visual representations not compared ⇒ final design-FTO risk is 'Unknown / Not determinable', never 'Medium'"},
            {"item": "Legal opinion", "value": "This is a preliminary design-risk screening, not a legal opinion and not a guarantee of non-infringement"},
        ], ["item", "value"], "Final artwork and launch decisions require register verification and professional design clearance."),
    ]
    return result
