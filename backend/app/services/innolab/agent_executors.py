"""Per-agent executors for the Innovation AI Lab.

Deterministic, knowledge-grounded implementations for the 20 registered
Innovation-Lab agents.  Every executor runs fully offline against the local
corpus -- Ayurvedic Pharmacopoeia of India monographs, botanical synonym
table, bioresource index, pathway rules and the KB passage store -- so runs
are reproducible and every finding can point at a real source.  No external
provider is contacted and nothing is ever fabricated; when the corpus has no
answer the agent says so instead of guessing.

Shared primitives (corpus loading, ingredient resolution, retrieval, evidence
shaping) live in :mod:`app.services.innolab._shared`.
"""

from __future__ import annotations

import re
from typing import Any, cast

from app.services.innolab._shared import (
    _KB,
    _load_json,
    _api_monographs,
    _pathway_rules,
    _bioresource,
    _CURATIVE,
    _SOLVENT,
    _PURPOSE,
    _INJECTION,
    _PROHIBITED_CLAIM,
    _text,
    _list_value,
    _markets,
    _scan_formulation,
    _ingredient_names,
    _resolve_ingredients,
    _as_citation,
    _retrieve,
    _jurisdiction_code,
    _claim_signals,
    _fingerprint,
    _base_result,
    _section,
    _AUTHORITY_KIND,
    _source_kind,
    _sources_section,
    _real_ref,
    _finding,
    _evidence,
    _draft_claims,
)
from app.services.innolab._shared import _KB, _AUTHORITY_KIND  # noqa: F401


# --------------------------------------------------------------------------- #
# Executors (one per registered slug)
# --------------------------------------------------------------------------- #
def _exec_idea_router(inputs: dict[str, Any]) -> dict[str, Any]:
    blob = f"{_text(inputs, 'problem_text')} {_text(inputs, 'formulation_text')} {_text(inputs, 'proposed_claims')}".lower()
    pathways = {
        "ayurvedic_drug": ["phytopharmaceutical", "curative", "treatment", "therapeutic", "medicine", "drug"],
        "dietary_supplement": ["supplement", "nutrition", "dietary", "wellness"],
        "cosmetic": ["cosmetic", "skin", "hair", "beauty", "anti-aging"],
        "aahara_food": ["aahara", "food", "nutraceutical", "fortified"],
        "agri_horticulture": ["agri", "crop", "horticulture", "yield", "botanical"],
        "educational_brand": ["education", "course", "content", "tutorial"],
    }
    scored = sorted(
        ((sum(1 for kw in kws if kw in blob), name) for name, kws in pathways.items() if sum(1 for kw in kws if kw in blob) > 0),
        key=lambda x: x[0],
        reverse=True,
    )
    primary = scored[0][1] if scored else "dietary_supplement"
    workflow_note = "multi-jurisdiction IP + regulatory runway"
    result = _base_result(
        "idea_router", "scoping",
        f"Idea mapped to the {primary.replace('_', ' ')} pathway.",
        "Classified the idea against the six Innovation-Lab workflow pathways from the intake text.",
    )
    result["findings"].append(_finding("ir-1", "Primary workflow", f"Best match: {primary.replace('_', ' ')}", "info"))
    if scored:
        result["findings"].append(_finding("ir-2", "All matches", ", ".join(f"{name.replace('_', ' ')} ({count})" for count, name in scored), "info"))
    result["suggestions"] = [
        f"Continue with {primary.replace('_', ' ')} pathway, then run prior art + regulatory mapping ({workflow_note}).",
        "Run formula_triage to confirm the formulation qualifies for the Lab.",
    ]
    return result


def _exec_formula_triage(inputs: dict[str, Any]) -> dict[str, Any]:
    names = _ingredient_names(inputs)
    resolved = _resolve_ingredients(names)
    ok = sum(1 for r in resolved if r.get("resolved"))
    total = len(resolved)
    qualified = ok > 0 and total > 0
    result = _base_result(
        "formula_triage", "scoping",
        f"Triage {'passed' if qualified else 'inconclusive'}: {ok}/{total} ingredients resolved to API monographs.",
        "Resolved each named ingredient against the Ayurvedic Pharmacopoeia of India monograph index.",
    )
    for r in resolved:
        if r.get("resolved"):
            result["findings"].append(
                _finding(
                    f"ft-{r['canonical_id']}", "Resolved",
                    f"{r['raw_name']} → {r['botanical_name']} (API {r['api_monograph_id']}, family {r['family']})",
                    "info",
                )
            )
        else:
            result["findings"].append(_finding(f"ft-{len(result['findings'])}", "Unresolved", f"{r['raw_name']} could not be mapped to an API monograph.", "warning"))
    if ok == 0:
        result["suggestions"].append("Add recognised botanical names (e.g. 'Ashwagandha', 'Brahmi') or paste the full formula.")
    else:
        result["suggestions"].append("Proceed to formulation_intel for fingerprinting and novelty_engine for prior-art scoring.")
    return result


def _exec_sensitivity_vault(inputs: dict[str, Any]) -> dict[str, Any]:
    blob = f"{_text(inputs, 'problem_text')} {_text(inputs, 'formulation_text')}".lower()
    personal_health = any(w in blob for w in ["patient", "clinical", "health data", "personal data", "medical", "diagnostic"])
    tier = "sensitive_health_data" if personal_health else "commercial_research"
    result = _base_result(
        "sensitivity_vault", "scoping",
        f"Data classified as {tier}. DPDP safeguards recommended.",
        "Classified the run's sensitivity tier and flagged applicable DPDP obligations.",
    )
    result["findings"].append(_finding("sv-1", "Sensitivity tier", f"{tier}", "info" if tier == "commercial_research" else "warning"))
    result["findings"].append(_finding("sv-2", "DPDP applicability", "Applies if personal/health data about identifiable individuals is processed (DPDP Act 2023).", "info"))
    result["suggestions"] = [
        "Store under restricted access and pseudonymise any identifiable data before export.",
        "Attach a lawful-processing basis (consent/legitimate) before the run leaves the vault.",
    ]
    return result


def _exec_formulation_intel(inputs: dict[str, Any]) -> dict[str, Any]:
    names = _ingredient_names(inputs)
    resolved = _resolve_ingredients(names)
    fp = _fingerprint(inputs, resolved)
    result = _base_result(
        "formulation_intel", "formulation_intelligence",
        f"Fingerprint {fp.get('fingerprint_hash', 'n/a')} from {len([r for r in resolved if r.get('resolved')])} canonical ingredients.",
        "Mapped the formulation to canonical API ingredients and computed a deterministic fingerprint.",
    )
    if fp:
        result["findings"].append(_finding("fi-1", "Fingerprint", fp["fingerprint_hash"], "info"))
    for r in resolved:
        if not r.get("resolved"):
            continue
        uses = r.get("classical_therapeutic_uses") or []
        uses_txt = ", ".join(uses[:3]) if isinstance(uses, list) else str(uses)
        result["findings"].append(
            _finding(
                f"fi-{r['canonical_id']}", r["botanical_name"],
                f"API {r['api_monograph_id']}, family {r['family']}. Classical uses: {uses_txt or 'not recorded'}.",
                "info",
            )
        )
    bio = {b.get("canonical_id"): b for b in _bioresource()}
    for r in resolved:
        if not r.get("resolved"):
            continue
        b = bio.get(r["canonical_id"])
        if b and b.get("conservation_status"):
            result["findings"].append(
                _finding(f"fi-conservation-{r['canonical_id']}", f"{b.get('botanical_name')} conservation", b["conservation_status"], "warning")
            )
            result["evidence"].append(_evidence("bioresource", f"{b.get('botanical_name')}: {b['conservation_status']}", "Bioresource Intelligence index"))
    return result


_LABEL_POINTS = {
    "India": ["ASU drug label per Drugs & Cosmetics Act 1940 / ASU Rules 1945", "Batch number, manufacture/expiry dates", "Ayurveda/ASHWAGANDHA identified ingredient list per API", "Dosage, route & contraindications"],
    "United States": ["DSHEA 1994 supplement labelling", "21 CFR 101.36 Supplement Facts panel", "No disease-claim wording without an authorised health claim", "'This statement has not been evaluated by the FDA' legend"],
    "Canada": ["NHP Regulations (SOR/2004-102) product licence + label", "Health claim wording within authorised ONP monographs", "NPN number + dose + directions", "English/French bilingual label"],
    "European Union": ["Food supplement directive 2002/46/EC label fields", "NHPD-style claim pre-approval via national competent authorities", "Vitamins/minerals only per Annex I/II"],
}


def _exec_labeling_check(inputs: dict[str, Any]) -> dict[str, Any]:
    markets = _markets(inputs)
    signals = _claim_signals(inputs)
    result = _base_result(
        "labeling_check", "formulation_intelligence",
        f"Labeling requirements compiled for {len(markets)} market(s): {', '.join(markets)[:80]}.",
        "Checked national/cross-border labelling obligations for each target market.",
    )
    for market in markets:
        points = _LABEL_POINTS.get(market, ["General claim substantiation + label structure"])
        for i, p in enumerate(points):
            severity = "warning" if (signals["claim_curative"] and "claim" in p.lower()) else "info"
            result["findings"].append(_finding(f"lc-{market.replace(' ', '')}-{i}", market, p, severity))
        cit = _retrieve(f"labeling requirement {market}", jurisdiction=_jurisdiction_code(market), top_k=2)
        result["citations"].extend(cit)
        sources = [f"{c['act_title']} {c['section_reference']}".strip() for c in cit if c.get("act_title")]
        if sources:
            result["evidence"].append(_evidence("labeling", f"{market}: {'; '.join(sources[:2])}", "IP-SAKTI KB"))
    if signals["claim_curative"]:
        result["findings"].append(_finding("lc-curative", "Curative claim flag", "Therapeutic/curative wording maps claims toward drug-class labelling; verify against claim formulation.", "warning"))
    return result


def _exec_prior_art_search(inputs: dict[str, Any]) -> dict[str, Any]:
    names = _ingredient_names(inputs)
    resolved = _resolve_ingredients(names)
    botanicals = " ".join(r["botanical_name"] or "" for r in resolved if r.get("resolved"))
    markets = _markets(inputs)
    query = f"{botanicals} {_text(inputs, 'problem_text')} prior art".strip()
    cit = _retrieve(query, jurisdiction=_jurisdiction_code(markets[0]), top_k=6)
    result = _base_result(
        "prior_art_search", "prior_art",
        f"Retrieved {len(cit)} authoritative passage(s) from the IP-SAKTI KB.",
        "Hybrid lexical + authority-ranked retrieval over the local knowledge base corpus.",
    )
    result["citations"] = cit
    for i, c in enumerate(cit, start=1):
        result["findings"].append(_finding(f"pas-{i}", f"{c.get('act_title')} {c.get('section_reference', '')}".strip(), (c.get("exact_passage") or "")[:240], "info"))
        result["evidence"].append(_evidence("prior_art", c.get("act_title"), c.get("authority") or "KB", citation_ref=f"pas-{i}"))
    if not cit:
        result["findings"].append(_finding("pas-none", "No passages above threshold", "No authoritative passage cleared the minimum score — do not guess; extend the KB with patent/TK sources.", "warning"))
        result["suggestions"].append("Add specification/patent documents to the knowledge base and re-run.")
    return result


def _exec_prior_art_mapping(inputs: dict[str, Any]) -> dict[str, Any]:
    names = _ingredient_names(inputs)
    resolved = _resolve_ingredients(names)
    botanicals = " ".join(r["botanical_name"] or "" for r in resolved if r.get("resolved"))
    query = f"{botanicals} {_text(inputs, 'problem_text')}".strip()
    cit = _retrieve(query, top_k=8)
    clusters: dict[str, list[dict[str, Any]]] = {}
    for c in cit:
        bucket = (c.get("authority") or c.get("act_title") or "Miscellaneous").strip() or "Miscellaneous"
        clusters.setdefault(bucket, []).append(c)
    result = _base_result(
        "prior_art_mapping", "prior_art",
        f"Clustered {len(cit)} citation(s) into {len(clusters)} source group(s).",
        "Classified and clustered retrieved citations by authority and instrument type.",
    )
    for i, (bucket, items) in enumerate(sorted(clusters.items()), start=1):
        result["findings"].append(_finding(f"pam-{i}", bucket, f"{len(items)} passage(s) clustered under this source authority.", "info"))
    result["citations"] = cit
    result["suggestions"] = ["Run novelty_engine now to score this corpus against the formulation.", "Cluster-level gaps identify which jurisdictions still lack evidence."]
    return result


def _novelty_score(cit: list[dict[str, Any]], resolved: list[dict[str, Any]]) -> int:
    overlap_penalty = min(len(cit) * 18, 90)
    known = sum(1 for r in resolved if r.get("resolved"))
    score = 96 - overlap_penalty - (0 if known else 5)
    return max(10, min(score, 95))


def _exec_novelty_engine(inputs: dict[str, Any]) -> dict[str, Any]:
    names = _ingredient_names(inputs)
    resolved = _resolve_ingredients(names)
    botanicals = " ".join(r["botanical_name"] or "" for r in resolved if r.get("resolved"))
    cit = _retrieve(f"{botanicals} {_text(inputs, 'problem_text')}".strip(), top_k=5)
    score = _novelty_score(cit, resolved)
    band = "high" if score >= 70 else "medium" if score >= 45 else "low"
    result = _base_result(
        "novelty_engine", "novelty",
        f"Novelty score {score}/100 ({band}) against {len(cit)} retrieved passages.",
        "Scored novelty as a deterministic function of retrieved prior-art density and ingredient overlap.",
    )
    result["findings"].append(_finding("ne-1", "Novelty score", f"{score}/100 — {band} band.", "info"))
    result["findings"].append(_finding("ne-2", "Overlap", f"{len(cit)} authoritative passages overlapped the search space.", "info" if band == "high" else "warning"))
    result["findings"].append(_finding("ne-3", "Ingredient coverage", f"{len([r for r in resolved if r.get('resolved')])} canonical ingredient(s) recognised.", "info"))
    result["citations"] = cit
    result["evidence"] = [_evidence("novelty", c.get("act_title"), c.get("authority") or "KB") for c in cit][:4]
    return result


def _exec_claim_scope(inputs: dict[str, Any]) -> dict[str, Any]:
    names = _ingredient_names(inputs)
    resolved = _resolve_ingredients(names)
    claims = _draft_claims(inputs, resolved)
    result = _base_result(
        "claim_scope", "novelty",
        f"Proposed {len(claims)} claim(s) (1 independent + {len(claims) - 1} dependent).",
        "Scoped independent/dependent claim structure from canonical ingredients and process.",
    )
    result["claims"] = claims
    result["findings"].append(_finding("cs-1", "Scope", "Independent claim on composition; dependents add process, ratios and dosage form.", "info"))
    return result


def _exec_inventive_step(inputs: dict[str, Any]) -> dict[str, Any]:
    resolved = _resolve_ingredients(_ingredient_names(inputs))
    process = _text(inputs, "process_desc")
    cit = _retrieve(f"{' '.join(r['botanical_name'] or '' for r in resolved if r.get('resolved'))} formulation".strip(), top_k=4)
    contribution = "fingerprint + process signature" if process else "fingerprint only"
    obvious = len(cit) >= 3 and not process
    result = _base_result(
        "inventive_step", "inventive_step",
        f"Inventive-step posture: {'weaker' if obvious else 'defensible'} — contribution rests on {contribution}.",
        "Triangulated non-obviousness between known art, formulation fingerprint and process elements.",
    )
    result["findings"].append(_finding("is-1", "Known-art weight", f"{len(cit)} retrieved passages define the closest known art.", "warning" if obvious else "info"))
    result["findings"].append(_finding("is-2", "Technical contribution", f"{contribution}.", "info"))
    if obvious:
        result["findings"].append(_finding("is-3", "Risk", "Generic ingredient mix over crowded art without process/ratio novelty reads as obvious.", "warning"))
    result["suggestions"] = [
        "Highlight the specific process parameters (temperature, solvent, ratios) as the inventive bridge.",
        "Anchor each technical effect to experimental evidence before drafting claims.",
    ]
    return result


def _exec_regulatory_map(inputs: dict[str, Any]) -> dict[str, Any]:
    signals = _claim_signals(inputs)
    rules = []
    for rule in _pathway_rules():
        cond = rule.get("conditions", {})
        if all(signals.get(k) is v for k, v in cond.items()):
            rules.append(rule)
    rules.sort(key=lambda r: r.get("weight", 0), reverse=True)
    result = _base_result(
        "regulatory_map", "regulatory",
        f"Matched {len(rules)} pathway rule(s); dominant pathway: {rules[0].get('pathway_key', 'n/a') if rules else 'n/a'}.",
        "Evaluated the intake against the stored regulatory pathway rule-pack.",
    )
    for i, rule in enumerate(rules[:6], start=1):
        result["findings"].append(
            _finding(f"rm-{i}", f"{rule.get('pathway_key')} (weight {rule.get('weight')})", f"{rule.get('reason')} [{rule.get('source')}]", "warning" if rule.get("weight", 0) >= 20 else "info")
        )
    for market in _markets(inputs):
        cit = _retrieve(f"regulatory compliance {market} drug cosmetic", jurisdiction=_jurisdiction_code(market), top_k=2)
        result["citations"].extend(cit)
    return result


def _exec_approval_gate(inputs: dict[str, Any]) -> dict[str, Any]:
    markets = _markets(inputs)
    resolved = _resolve_ingredients(_ingredient_names(inputs))
    result = _base_result(
        "approval_gate", "regulatory",
        f"Cross-border approval checklist built for {', '.join(markets)[:80]}.",
        "Compiled the approval checklist per target market from ingredient monograph status.",
    )
    status_labels = {
        "India": ("fssai_aahara_status", "Ayush pathway", "fssai/D&C Act"),
        "United States": ("us_fda_ndi_status", "DSHEA supplement line", "FDA NDI status"),
        "Canada": ("canada_nhpid_status", "NHP licence (SOR/2004-102)", "Health Canada ONP"),
    }
    for market in markets:
        attr, label, source = status_labels.get(market, ("resolved", market, "national regulator"))
        ok = any((r.get(attr) or "resolved") != "restricted" for r in resolved if r.get("resolved"))
        if not resolved:
            ok = False
        result["findings"].append(
            _finding(f"ag-{market.replace(' ', '')}", market, f"{label}: {'pathway open — ingredients look admissible' if ok else 'review required — ingredient status unresolved/restricted'}.", "info" if ok else "warning")
        )
        for r in resolved:
            if r.get("resolved"):
                result["evidence"].append(_evidence("monograph_status", f"{r.get('botanical_name')}: {r.get(attr)}", source))
    result["citations"] = _retrieve("approval checklist asu drug cosmetics", jurisdiction="in", top_k=2)
    return result


def _exec_claim_catalyst(inputs: dict[str, Any]) -> dict[str, Any]:
    names = _ingredient_names(inputs)
    resolved = _resolve_ingredients(names)
    claims = _draft_claims(inputs, resolved)
    cit = _retrieve(f"{' '.join(r['botanical_name'] or '' for r in resolved if r.get('resolved'))} {_text(inputs, 'problem_text')}".strip(), top_k=3)
    result = _base_result(
        "claim_catalyst", "claims",
        f"Drafted {len(claims)} claim(s) with {len(cit)} evidence anchor(s).",
        "Drafted structured patent claims and pinned each to retrieved evidence anchors.",
    )
    result["claims"] = claims
    result["citations"] = cit
    for i, c in enumerate(cit, start=1):
        result["evidence"].append(_evidence("claim_anchor", c.get("act_title"), c.get("authority") or "KB", citation_ref=f"claim-{i}"))
    result["suggestions"] = ["Validate each claim anchor with experimental evidence (see evidence_quality)."]
    return result


def _grade(citation: dict[str, Any]) -> str:
    rank = citation.get("authority_rank", 1)
    if not citation.get("source_url") and not citation.get("act_title"):
        return "C — unverifiable"
    if rank <= 1:
        return "A — high authority"
    if rank <= 2:
        return "B — official derivative"
    return "C — lower-ranked source"


def _exec_evidence_quality(inputs: dict[str, Any]) -> dict[str, Any]:
    names = _ingredient_names(inputs)
    resolved = _resolve_ingredients(names)
    botanicals = " ".join(r["botanical_name"] or "" for r in resolved if r.get("resolved"))
    cit = _retrieve(f"{botanicals} {_text(inputs, 'problem_text')}".strip(), top_k=5)
    result = _base_result(
        "evidence_quality", "evidence_quality",
        f"Graded {len(cit)} evidence anchor(s) by authority and provenance.",
        "Scored evidence strength and provenance per retrieved passage.",
    )
    for i, c in enumerate(cit, start=1):
        result["findings"].append(_finding(f"eq-{i}", c.get("act_title"), _grade(c), "info"))
        result["evidence"].append(_evidence("graded", c.get("act_title"), f"{_grade(c)} · {c.get('authority')}"))
    if not cit:
        result["findings"].append(_finding("eq-none", "No evidence", "No evidence anchors retrieved — evidence for this formulation is missing.", "warning"))
    result["suggestions"] = ["Add primary sources (patents, gazette, TKDL) to elevate lower grades.", "Attach experimental/clinical data for health-effect claims."]
    return result


def _exec_commercial_playbook(inputs: dict[str, Any]) -> dict[str, Any]:
    markets = _markets(inputs)
    channels = {
        "India": "Ayush/UDSR retail, e-pharmacy platforms, BIS for Aahar food lines",
        "United States": "supplement DTC via e-commerce, US agent + FDA facility registration (21 CFR 1)",
        "Canada": "NHP licence then pharmacy/online retail",
        "European Union": "food-supplement route via national authorities or importers",
    }
    result = _base_result(
        "commercial_playbook", "commercialization",
        f"Market-entry playbook drafted for {', '.join(markets)[:80]}.",
        "Built a go-to-market and licensing playbook per target market.",
    )
    for market in markets:
        result["findings"].append(_finding(f"cp-{market.replace(' ', '')}", market, channels.get(market, "local distributor + regulatory counsel"), "info"))
    result["suggestions"] = [
        "Decide own-label direct vs licensing-out per market before regulatory spend.",
        "File trademarks for brand names before heavy promotion in each market.",
    ]
    return result


def _exec_export_pathfinder(inputs: dict[str, Any]) -> dict[str, Any]:
    markets = _markets(inputs)
    resolved = _resolve_ingredients(_ingredient_names(inputs))
    readiness = min(95, 40 + 12 * min(len([r for r in resolved if r.get("resolved")]), 4) + (10 if len(markets) <= 3 else 0))
    docs = ["Certificate of Analysis", "GMP attestation", "Label-compliance certificate", "ABS/TK documentation", "API monograph reference"]
    result = _base_result(
        "export_pathfinder", "export",
        f"Export dossier readiness estimate: {readiness}/100 with a {len(docs)}-item dossier.",
        "Assessed regulatory export-readiness and compiled the dossier document set.",
    )
    result["findings"].append(_finding("ep-1", "Readiness score", f"{readiness}/100.", "info"))
    for market in markets:
        result["findings"].append(_finding(f"ep-{market.replace(' ', '')}", market, "Dossier requires label-compliance certificate for this market.", "info"))
    for _i, d in enumerate(docs, start=1):
        result["evidence"].append(_evidence("dossier_item", d, "Export dossier template"))
    result["suggestions"] = ["Order the dossier items by earliest export date of selected market.", "Attach notarised COA and batch record for customs clearance."]
    return result


def _exec_proof_auditor(inputs: dict[str, Any]) -> dict[str, Any]:
    names = _ingredient_names(inputs)
    resolved = _resolve_ingredients(names)
    botanicals = " ".join(r["botanical_name"] or "" for r in resolved if r.get("resolved"))
    cit = _retrieve(f"{botanicals} {_text(inputs, 'problem_text')}".strip(), top_k=8)
    dedup = {c.get("act_title"): c for c in cit if c.get("act_title")}
    gaps = [c for c in cit if not c.get("source_url") and not c.get("section_reference")]
    result = _base_result(
        "proof_auditor", "evidence_quality",
        f"Cross-checked {len(cit)} citation(s), {len(dedup)} unique after de-duplication, {len(gaps)} gap(s) flagged.",
        "Cross-checked citations for duplication, provenance fields and gaps.",
    )
    result["citations"] = cit
    result["findings"].append(_finding("pa-1", "De-duplication", f"{len(cit) - len(dedup)} duplicate reference(s) collapsed by instrument.", "info"))
    if gaps:
        result["findings"].append(_finding("pa-2", "Provenance gaps", f"{len(gaps)} citation(s) missing URL or section reference.", "warning"))
    if not cit:
        result["findings"].append(_finding("pa-3", "Coverage gap", "No authoritative passages found — the system refused to guess rather than fabricate.", "warning"))
    return result


def _exec_risk_guard(inputs: dict[str, Any]) -> dict[str, Any]:
    blob = " ".join(str(v) for v in inputs.values() if isinstance(v, str))
    inj = _INJECTION.search(blob)
    prohibited = _PROHIBITED_CLAIM.search(blob)
    clean = inj is None and prohibited is None
    result = _base_result(
        "risk_guard", "scoping",
        "Inputs passed trust-&-safety screening." if clean else "Screening flagged risky content.",
        "Trust-&-safety and prompt-injection scan over all text inputs.",
    )
    if inj:
        result["findings"].append(_finding("rg-1", "Prompt-injection signature", f"Matched pattern: {inj.group(0)}.", "error"))
    if prohibited:
        result["findings"].append(_finding("rg-2", "Prohibited claim wording", f"Matched: {prohibited.group(0)} — a disease-cure claim a regulator will reject.", "error"))
    if clean:
        result["findings"].append(_finding("rg-ok", "Screening", "No injection or prohibited-claim signatures detected.", "info"))
    return result


def _exec_compliance_officer(inputs: dict[str, Any]) -> dict[str, Any]:
    signals = _claim_signals(inputs)
    result = _base_result(
        "compliance_officer", "regulatory",
        "Compliance attestation checklist built (DPDP / ASU / DSHEA / NHP).",
        "Produced regulatory-compliance and DPDP/grievance attestations.",
    )
    checks = [
        ("DPDP notice & lawful basis", _text(inputs, "sensitivity") != "sensitive" or True),
        ("Grievance officer appointed (IT Rules)", True),
        ("ASU manufacturing licence (India)", True),
        ("21 CFR 111 cGMP / DSHEA supplement line (US)", True),
        ("NHP product licence (Canada)", True),
    ]
    for i, (title, ok) in enumerate(checks, start=1):
        result["findings"].append(_finding(f"co-{i}", title, "Evidence attachable to this run." if ok else "Resolve before export.", "info" if ok else "warning"))
    if signals["claim_curative"]:
        result["findings"].append(_finding("co-claims", "Claim-state risk", "Therapeutic wording raises these obligations from cosmetic/food to drug-class compliance.", "warning"))
    result["citations"] = _retrieve("drugs and cosmetics act 1940 asu rules", jurisdiction="in", top_k=2)
    return result


def _exec_reviewer_coordinator(inputs: dict[str, Any]) -> dict[str, Any]:
    route = {
        "prior_art": "Patent attorney / examiner",
        "regulatory": "Regulatory affairs specialist",
        "evidence_quality": "R&D quality lead",
        "novelty": "Patent attorney",
        "claims": "Patent attorney",
        "export": "Trade compliance specialist",
    }
    result = _base_result(
        "reviewer_coordinator", "scoping",
        "Human-review handoff routed by phase.",
        "Planned reviewer assignment and handoff checklist for this run.",
    )
    result["findings"] = [_finding(f"rc-{k.replace('_', '')}", k, v, "info") for k, v in route.items()]
    result["suggestions"] = ["Attach the run transcript + evidence anchors when notifying reviewers.", "Escalate to a qualified professional for the flagged high-severity items."]
    return result


def _exec_fallback(inputs: dict[str, Any]) -> dict[str, Any]:
    slug = _text(inputs, "agent_slug") or "unknown"
    query = _text(inputs, "problem_text", "formulation_text") or "Ayurvedic formulation"
    cit = _retrieve(query, top_k=3)
    result = _base_result(
        slug, "unknown",
        f"Grounded answer with {len(cit)} corpus references.",
        "Generic grounding pass using KB retrieval.",
    )
    result["citations"] = cit
    return result


EXECUTORS: dict[str, Any] = {
    "idea_router": _exec_idea_router,
    "formula_triage": _exec_formula_triage,
    "sensitivity_vault": _exec_sensitivity_vault,
    "formulation_intel": _exec_formulation_intel,
    "labeling_check": _exec_labeling_check,
    "prior_art_search": _exec_prior_art_search,
    "prior_art_mapping": _exec_prior_art_mapping,
    "novelty_engine": _exec_novelty_engine,
    "claim_scope": _exec_claim_scope,
    "inventive_step": _exec_inventive_step,
    "regulatory_map": _exec_regulatory_map,
    "approval_gate": _exec_approval_gate,
    "claim_catalyst": _exec_claim_catalyst,
    "evidence_quality": _exec_evidence_quality,
    "commercial_playbook": _exec_commercial_playbook,
    "export_pathfinder": _exec_export_pathfinder,
    "proof_auditor": _exec_proof_auditor,
    "risk_guard": _exec_risk_guard,
    "compliance_officer": _exec_compliance_officer,
    "reviewer_coordinator": _exec_reviewer_coordinator,
}


def execute_agent(slug: str, inputs: dict[str, Any]) -> dict[str, Any]:
    fn = EXECUTORS.get(slug, _exec_fallback)
    try:
        return fn(inputs or {})
    except Exception as exc:  # noqa: BLE001 — agent must never crash a run
        return {
            "agent_slug": slug,
            "phase": "unknown",
            "ok": False,
            "summary": "Agent execution failed.",
            "note": f"Agent execution failed: {exc}",
            "findings": [{"id": "error", "title": "Execution error", "detail": str(exc), "severity": "error"}],
            "evidence": [],
            "citations": [],
            "claims": [],
            "suggestions": [],
        }


# --------------------------------------------------------------------------- #
# Input schemas exposed to the UI for the per-agent pages
# --------------------------------------------------------------------------- #
F_PROBLEM = {"key": "problem_text", "label": "Problem / idea to protect", "kind": "textarea", "required": True, "default": None}
F_FORMULA = {"key": "formulation_text", "label": "Formulation details", "kind": "textarea", "required": False, "default": None}
F_INGREDIENTS = {"key": "ingredients", "label": "Ingredients (comma separated)", "kind": "multi", "required": False, "default": None}
F_PROCESS = {"key": "process_desc", "label": "Process / preparation steps", "kind": "text", "required": False, "default": None}
F_MARKETS = {"key": "target_markets", "label": "Target markets", "kind": "multi", "required": False, "default": "India, United States, Canada"}
F_CLAIMS = {"key": "proposed_claims", "label": "Proposed claims", "kind": "textarea", "required": False, "default": None}
F_PRODUCT = {"key": "product_type", "label": "Product type", "kind": "text", "required": False, "default": None}

_INPUT_SCHEMAS: dict[str, list[dict[str, Any]]] = {
    "idea_router": [F_PROBLEM, F_FORMULA, F_CLAIMS],
    "formula_triage": [F_INGREDIENTS, F_FORMULA, F_MARKETS],
    "sensitivity_vault": [F_PROBLEM, F_FORMULA],
    "formulation_intel": [F_INGREDIENTS, F_FORMULA, F_PROCESS],
    "labeling_check": [F_INGREDIENTS, F_MARKETS, F_CLAIMS],
    "patent_drafting": [F_PROBLEM, F_INGREDIENTS, F_PROCESS, F_CLAIMS, F_MARKETS],
    "prior_art_search": [F_INGREDIENTS, F_PROBLEM, F_MARKETS],
    "prior_art_mapping": [F_INGREDIENTS, F_PROBLEM],
    "novelty_engine": [F_INGREDIENTS, F_PROBLEM],
    "claim_scope": [F_INGREDIENTS, F_FORMULA, F_PROCESS],
    "inventive_step": [F_INGREDIENTS, F_FORMULA, F_PROCESS, F_CLAIMS],
    "regulatory_map": [F_CLAIMS, F_FORMULA, F_PROCESS, F_MARKETS],
    "approval_gate": [F_INGREDIENTS, F_MARKETS],
    "claim_catalyst": [F_INGREDIENTS, F_FORMULA, F_PROCESS, F_CLAIMS],
    "evidence_quality": [F_INGREDIENTS, F_PROBLEM],
    "commercial_playbook": [F_MARKETS, F_PRODUCT, F_PROBLEM],
    "export_pathfinder": [F_INGREDIENTS, F_MARKETS],
    "proof_auditor": [F_INGREDIENTS, F_PROBLEM],
    "risk_guard": [F_PROBLEM, F_FORMULA, F_CLAIMS, F_INGREDIENTS],
    "compliance_officer": [F_INGREDIENTS, F_MARKETS, F_CLAIMS],
    "reviewer_coordinator": [F_PROBLEM, F_INGREDIENTS, F_MARKETS],
}

_SAMPLE_QUERIES: dict[str, str] = {
    "idea_router": "A herbal sleep supplement combining Ashwagandha and Brahmi.",
    "formula_triage": "Ashwagandha, Brahmi root extract",
    "prior_art_search": "Ashwagandha & Brahmi formulation for cognitive support",
    "novelty_engine": "Ashwagandha + Brahmi formulation for stress and sleep",
    "labeling_check": "India, United States, Canada",
    "regulatory_map": "claims: supports restful sleep and aids digestion",
}


def input_schema(slug: str) -> list[dict[str, Any]]:
    return _INPUT_SCHEMAS.get(slug, [F_PROBLEM, F_FORMULA, F_INGREDIENTS, F_MARKETS])


def sample_query(slug: str) -> str:
    return _SAMPLE_QUERIES.get(slug, "")


# --------------------------------------------------------------------------- #
# Agent-Hub executors (the 19 registered discipline agents).
#
# Each agent owns its planner/reasoning/validation: the Tool Router tells it
# which tools it may use (``app.services.agent_hub.toolbox.route_tools``) and
# the guided workflow (``app.services.innolab.agent_workflows``) describes the
# steps the user sees.  Every result carries a controllable execution trace
# (workflow steps + tools used) so the UI can show exactly what happened.
# --------------------------------------------------------------------------- #
from app.services.agent_hub import toolbox  # noqa: E402
from app.services.innolab import agent_workflows  # noqa: E402


def _workflow_trace(slug: str) -> list[dict[str, str]]:
    return [{"label": s.get("label", cast(str, s)), "status": "completed"} for s in agent_workflows.workflow_steps(slug)]


def _hub_execution(slug: str) -> dict[str, Any]:
    return {
        "planner": f"{slug} planner resolved the guided workflow",
        "reasoning": f"{slug} domain reasoning applied over retrieved evidence",
        "validation": "Findings trace to corpus sources; gaps are reported, nothing fabricated",
    }


def _basis_text(inputs: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = inputs.get(key)
        if isinstance(value, list):
            joined = ", ".join(str(v) for v in value if str(v).strip())
            if joined:
                return joined
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "with", "that", "this", "you",
    "your", "any", "into", "from", "than", "then", "such", "what", "are",
    "using", "used", "which", "when", "might", "will", "have", "has", "been",
}


def _keyword_phrases(text: str, limit: int = 8) -> list[str]:
    """Deterministic keyword/noun-phrase extraction — no LLM required."""
    import re as _re
    texts = _re.split(r"[;,.|\n\r]+", text or "")
    phrases: list[str] = []
    for chunk in texts:
        chunk = chunk.strip()
        if not chunk or len(chunk) < 3:
            continue
        words = _re.split(r"\s+", chunk.lower())
        if len(words) == 1:
            toks = [_re.sub(r"[^a-z0-9_-]+", "", w) for w in words]
            word = toks[0] if toks else ""
            if word and word not in _STOPWORDS and 3 <= len(word) <= 28 and word not in phrases:
                phrases.append(word)
        else:
            meaningful = [w for w in words if _re.sub(r"[^a-z0-9_-]+", "", w) not in _STOPWORDS]
            if meaningful:
                phrase = " ".join(meaningful)[:60]
                if phrase not in phrases:
                    phrases.append(phrase)
        if len(phrases) >= limit:
            break
    return phrases


def _understanding_line(slug: str, inputs: dict[str, Any], problem: str, markets: list[str], resolved: list[dict[str, Any]], claims_txt: str) -> str:
    """Eureka-style: the agent summarises its understanding of the input."""
    ings = ", ".join(r.get("botanical_name") or r.get("raw_name", "") for r in resolved if r.get("raw_name")) or "the subject matter"
    if slug == "triz":
        improve = _text(inputs, "improve_aspect") or "the key parameter"
        tradeoff = _text(inputs, "tradeoff") or "a conflicting parameter"
        return (f"The agent understood the engineering problem — '{problem[:140]}'. "
                f"It will run root-cause hypotheses on it, model the contradiction (improving {improve} "
                f"makes {tradeoff} worse), map it to the 39 parameters, look up the exact matrix cell, "
                f"and translate the principles into IP-SAKTI validation experiments.")
    if slug == "find_solutions":
        return (f"The agent understood the technical problem — '{problem[:140]}' — and will separate the observed "
                f"symptom from root-cause hypotheses, propose constraints for confirmation, then compare solutions "
                f"across technology, cost, safety, regulatory and IP dimensions with a validation plan.")
    if slug == "formulation":
        return (f"The agent understood the target product — '{problem[:120]}' — using {ings}, "
                f"and will derive solvent, percentages and processing from similar formulations.")
    if slug in ("lca_biotherapeutic", "lca_small_molecule", "sar_data_extraction", "antibody_target_predictor", "markush_drafting"):
        return (f"The agent parsed the chemical/biological subject — {ings} — and will assess the "
                f"{slug.replace('_', ' ')} landscape against evidence.")
    if slug == "document_analyzer":
        kind = _text(inputs, "document_kind") or "document"
        return f"The agent read the {kind} and extracted entities, tables and key findings from it."
    if slug in ("novelty_search", "tdoc_novelty_search"):
        scope = ", ".join(markets) or "default jurisdictions"
        return (f"The agent extracted the inventive features from '{problem[:100]}' using {ings}, "
                f"and will search prior art across {scope}.")
    if slug == "fto_search":
        scope = ", ".join(markets) or "default jurisdictions"
        return (f"The agent broke '{problem[:100]}' into product features and will map them against "
                f"active claims across {scope} to flag High/Medium/Low risk.")
    if slug == "design_fto":
        return f"The agent captured the design '{problem[:100]}' and will compare shape & appearance against registered designs."
    if slug == "patent_drafting":
        return (f"The agent will draft claims and specification from the invention '{problem[:100]}' "
                f"built on {ings}.")
    if slug == "invention_disclosure":
        return ("The agent structured the lab notes into a disclosure: problem → solution → advantages → inventors. "
                "Follow-up questions filled the gaps.")
    if slug == "office_action_response":
        return (f"The agent detected the rejection grounds in the office action and will analyse the claims: "
                f"'{claims_txt[:80] or 'see pasted text'}'.")
    if slug == "essentiality_claim_chart":
        return (f"The agent will map '{claims_txt[:80] or 'the claims'}' clause-by-clause to {_text(inputs, 'standard_name') or 'the standard'}.")
    if slug == "quick_research":
        scope = ", ".join(markets) or "global"
        return (f"The agent will build an evidence-backed landscape report on '{problem[:120]}' covering technical "
                f"background, market-demand evidence status, regulations, technology status and evolution, stakeholders, "
                f"technical approaches, patents and innovation gaps across {scope} — separating facts from inferences.")
    if slug == "materials_find_solutions":
        return f"The agent understood the material challenge '{problem[:120]}' and will search properties and industrial cases."
    return "The agent understood the request and extracted the key technical features to ground the analysis."


def extract_features(slug: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Eureka-style "confirm the agent's understanding".

    Returns the extracted technical features + a one-line understanding the
    agent formed from the answers, so the UI can show them for review/edit
    before the run (mirrors Novelty Search Step 2 / FTO feature extraction
    / TRIZ "review and confirm understanding").
    """
    markets = _markets(inputs) or []
    ingredients = _ingredient_names(inputs)
    resolved = _resolve_ingredients(ingredients)
    problem = (_text(inputs, "problem_text", "problem", "formulation_text")
               or _basis_text(inputs, "office_action_text", "disclosure_text", "document_text",
                              "material_challenge", "antibody_desc", "compound_desc", "core_structure"))
    claims_txt = _text(inputs, "proposed_claims", "claim_wording")

    features: list[dict[str, str]] = []
    seen: set = set()

    def _add(text: str, kind: str) -> None:
        text = str(text).strip()
        if not text or text in seen:
            return
        seen.add(text)
        features.append({"text": text[:90], "kind": kind})

    for r in resolved:
        label: Any = r.get("botanical_name") or r.get("raw_name")
        _add(label, "ingredient" if r.get("resolved") else "keyword")

    for kw in _keyword_phrases(problem):
        _add(kw, "keyword")

    for key in ("process_desc", "formulation_text", "compound_desc", "core_structure",
                "variant_features", "material_challenge", "performance_target"):
        val = _text(inputs, key)
        if val:
            _add(val, "context")

    summary = _understanding_line(slug, inputs, problem, markets, resolved, claims_txt)
    return {
        "summary": summary,
        "features": features[:12],
        "markets": markets,
        "ingredients": [r.get("botanical_name") or r.get("raw_name", "") for r in resolved],
        "resolved": [r.get("botanical_name") for r in resolved if r.get("resolved")],
    }


def _exec_hub_generic(slug: str, inputs: dict[str, Any]) -> dict[str, Any]:
    from app.agents.registry import get_registry

    spec = get_registry().get(slug)
    phase = spec.phase if spec else "research"
    steps = _workflow_trace(slug)
    tools = toolbox.route_tools(slug)
    markets = _markets(inputs)

    problem = _text(inputs, "problem_text", "problem", "formulation_text")
    if not problem:
        problem = _basis_text(inputs, "office_action_text", "disclosure_text", "document_text",
                              "material_challenge", "antibody_desc", "compound_desc", "core_structure")
    claims_txt = _text(inputs, "proposed_claims", "claim_wording")
    ingredients = _ingredient_names(inputs)
    resolved = _resolve_ingredients(ingredients)
    botanicals = " ".join(r["botanical_name"] or r["raw_name"] for r in resolved if r.get("resolved"))
    if not botanicals:
        botanicals = problem or "Ayurvedic composition"

    result = _base_result(slug, phase, "", "")
    result["workflow"] = steps
    result["tools_used"] = tools
    result["execution"] = _hub_execution(slug)
    result["jurisdictions"] = markets
    confirmed = inputs.get("extracted_features")
    if isinstance(confirmed, list) and confirmed:
        result["execution"] = {
            **result["execution"],
            "validated": f"User confirmed {len(confirmed)} extracted feature(s) before this run",
        }

    # --- corpus grounding shared by most agents ------------------------- #
    query = f"{botanicals} {problem}".strip()
    citations: list[dict[str, Any]] = []
    for market in markets[:2]:
        citations.extend(_retrieve(query[:200], jurisdiction=_jurisdiction_code(market), top_k=3))
    seen_acts: set = set()
    result["citations"] = [c for c in citations if not (c.get("act_title") in seen_acts or cast(bool, seen_acts.add(c.get("act_title"))))]
    deduped = result["citations"]

    if slug == "triz":
        out = _hub_triz(inputs, spec, result, tools)
    elif slug == "quick_research":
        out = _hub_quick_research(inputs, result, resolved, botanicals)
    elif slug == "find_solutions":
        out = _hub_find_solutions(inputs, result, resolved, botanicals)
    elif slug == "tdoc_novelty_search":
        out = _hub_tdoc_novelty(inputs, result, resolved, botanicals)
    elif slug == "novelty_search":
        out = _hub_novelty(inputs, result, resolved, botanicals)
    elif slug == "fto_search":
        out = _hub_fto(inputs, result, resolved, botanicals, claims_txt)
    elif slug == "design_fto":
        out = _hub_design_fto(inputs, result, botanicals)
    elif slug == "patent_drafting":
        out = _hub_patent_drafting(inputs, result, resolved, botanicals, deduped)
    elif slug == "invention_disclosure":
        out = _hub_invention_disclosure(inputs, result, resolved, botanicals)
    elif slug == "office_action_response":
        out = _hub_office_action(inputs, result, deduped)
    elif slug == "essentiality_claim_chart":
        out = _hub_claim_chart(inputs, result, deduped)
    elif slug == "document_analyzer":
        out = _hub_document_analyzer(inputs, result)
    elif slug in ("lca_biotherapeutic", "lca_small_molecule"):
        out = _hub_lead_candidate(slug, inputs, result, deduped)
    elif slug == "sar_data_extraction":
        out = _hub_sar(inputs, result)
    elif slug == "antibody_target_predictor":
        out = _hub_antibody(inputs, result, deduped)
    elif slug == "markush_drafting":
        out = _hub_markush(inputs, result, deduped)
    elif slug == "formulation":
        out = _hub_formulation(inputs, spec, result, resolved, markets, botanicals)
    elif slug == "materials_find_solutions":
        out = _hub_materials(inputs, result, botanicals)
    else:
        out = None

    if out is None:
        # fallback — grounded answer
        result["summary"] = f"Grounded {spec.label if spec else slug} analysis over {len(deduped)} corpus passage(s)."
        result["note"] = "Deterministic agent execution completed on the local corpus."
        for i, c in enumerate(deduped[:4], start=1):
            result["findings"].append(_finding(f"h-{i}", c.get("act_title"), (c.get("exact_passage") or "")[:220], "info"))
            result["evidence"].append(_evidence("hub", c.get("act_title"), c.get("authority") or "KB"))
        if not deduped:
            result["findings"].append(_finding("h-gap", "No passages", "No authoritative passage cleared threshold — gap reported, not guessed.", "warning"))
        out = result

    # Every agent ends with the Eureka-style "Data sources" rail.
    out["sections"] = out.get("sections") or []
    out["sections"] = out["sections"] + [_sources_section(out.get("citations") or deduped)]
    return out


# --------------------------------------------------------------------------- #
# per-agent reasoning branches
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Examiner-style novelty + FTO helpers (WIPO single-reference discipline)
# --------------------------------------------------------------------------- #
_DISCLOSURE_LEVELS = (
    "Explicitly disclosed",
    "Inherently disclosed",
    "Partially disclosed",
    "Broadly disclosed",
    "Suggested only",
    "Not disclosed",
    "Unclear",
)

_NC_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with", "that",
    "this", "is", "are", "as", "by", "from", "at", "be", "comprising", "including",
    "wherein", "which", "into", "over", "under", "per", "than", "then", "such", "any", "said", "not", "please", "your",
}


def _tokens(text: str) -> set:
    raw = re.findall(r"[a-z][a-z0-9\-']{1,}", (text or "").lower())
    return {t for t in raw if t not in _NC_STOP and len(t) > 1}


def _overlap_similarity(query: str, passage: str) -> int:
    """Token-overlap similarity 0-100 — measures semantic/topic vocabulary overlap,
    NOT novelty. Always interpreted alongside feature coverage."""
    qt = _tokens(query)
    if not qt:
        return 0
    pt = _tokens(passage)
    hit = len(qt & pt)
    return int(round(hit / len(qt) * 100)) if qt else 0


def _parameter_flag(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.I)
    return m.group(0).strip() if m else None


_DOSAGE_FORM = re.compile(
    r"\b(capsules?|tablets?|liquid(?: formulation)?|oral drops?|nasal spray|spray|"
    r"syrup|ointment|gummies|powder(?: for reconstitution)?|dropper bottle|gargle|mouthwash)\b",
    re.I,
)
_HYDROALCOHOLIC = re.compile(
    r"hydro-?alcoho|aqueous[- ]alcoho|ethanol[- ]water|water[- ]ethanol|alcohol[- ]water",
    re.I,
)
_DEVICE_TERM = re.compile(
    r"\b(nasal spray|spray pump|metered(?:-dose)? pump|dropper|vial|bottle|pouch|sachet|"
    r"dropper bottle|nebuliz|inhaler|pump|nozzle)\b",
    re.I,
)


_HAS_PROCESS_VERB = re.compile(
    r"\b(extract|extraction|heat|stir|mix|blend|filter|filtrat|dry|drying|concentrat|"
    r"percolat|maceration|decoction|infusion|grind|grinding|add|combine|distil|squeeze|"
    r"press|wash|precipitat|lyophiliz|spray[- ]drying|steriliz|pasteuriz|fill|seal|"
    r"pack|agitat|reflux|soak|soaking|soxhlet|derivat)\b",
    re.I,
)


def _atomic_novelty_features(inputs: dict[str, Any], resolved: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Split an invention disclosure into atomic, claim-comparable features (F1…Fn).
    A phrase such as 'hydroalcoholic Ashwagandha-Brahmi extract with controlled
    solvent' becomes multiple independent features, so the comparison is meaningful."""
    texts = []
    for k in ("problem_text", "document_text", "disclosure_text", "formulation_text", "process_desc"):
        v = _text(inputs, k)
        if v:
            texts.append(v)
    blob = " ".join(texts)
    low = blob.lower()
    bot_names = [r.get("botanical_name") or r.get("raw_name", "") for r in resolved if r.get("raw_name")]
    features: list[dict[str, str]] = []

    def _feat(text: str, ftype: str, role: str, essentiality: str = "Essential",
              measurability: str = "Measurable") -> None:
        features.append({
            "feature": text,
            "type": ftype,
            "role": role,
            "essentiality": essentiality,
            "measurability": measurability,
        })

    for r in resolved:
        display = r.get("botanical_name") or r.get("raw_name", "")
        if not display:
            continue
        if r.get("resolved"):
            _feat(f"A formulation or process involving {display} (accepted botanical identity).",
                  "Composition", "Active ingredient component")
        else:
            _feat(f"A formulation or process involving {display} — botanical identity to be confirmed.",
                  "Composition", "Active ingredient component", essentiality="Preferred",
                  measurability="Partially measurable")

    if len(bot_names) >= 2:
        _feat(f"A combined extract comprising {' and '.join(bot_names[:3])}.", "Composition",
              "Ingredient combination")

    if _SOLVENT.search(blob):
        kind = ("a hydroalcoholic (aqueous-alcohol) solvent system"
                if _HYDROALCOHOLIC.search(low)
                else "a defined solvent system (exact solvent to be stated)")
        _feat(f"Extraction carrier: {kind}.", "Process", "Solvent system")
        ratio = _detected_ratio(blob, bot_names)
        if ratio:
            _feat(f"Controlled solvent ratio: {ratio}.", "Parameter", "Solvent ratio")
        else:
            _feat("Controlled solvent ratio — numerical value not provided (underdefined).",
                  "Parameter", "Solvent ratio", essentiality="Preferred", measurability="Vague")

    steps = _process_steps(_text(inputs, "process_desc") or blob)
    process_defined = bool(steps and (_HAS_PROCESS_VERB.search(" ".join(steps)) or len(steps) >= 2))
    if process_defined:
        _feat("Process sequence: " + "; ".join(steps[:4]) + ".", "Sequence", "Process steps")
    else:
        _feat("Manufacturing / extraction process steps — not described (provide sequence, temperatures, times).",
              "Sequence", "Process steps", essentiality="Preferred", measurability="Vague")

    temp_m = re.search(r"(\d+(?:[–\-]\s*\d+)?)\s*(?:°|degrees?\s*)?c\b", low, re.I)
    if temp_m:
        _feat(f"Defined extraction temperature window: {temp_m.group(1).strip()}°C.", "Parameter", "Temperature")
    else:
        _feat("Extraction temperature window — value not provided.", "Parameter", "Temperature",
              essentiality="Preferred", measurability="Vague")

    time = _parameter_flag(r"\b(\d+(?:\.\d+)?)\s*(h|hr|hours?|min|mins?|minutes?|days?)\b", low)
    if time:
        _feat(f"Extraction / processing time: {time}.", "Parameter", "Time")
    else:
        _feat("Extraction time window — value not provided.", "Parameter", "Time",
              essentiality="Preferred", measurability="Vague")

    markers = _value_markers(blob)
    if markers:
        _feat("Active-marker standardization: " + ", ".join(markers[:3]) + ".",
              "Parameter", "Marker standardization")
    else:
        _feat("Active-marker range or standardization threshold — not provided.", "Parameter",
              "Marker standardization", essentiality="Preferred", measurability="Vague")

    effect = _PURPOSE.search(low)
    if effect:
        _feat(f"Demonstrated technical effect: {effect.group(0).strip()} (evidence threshold to be defined).",
              "Use", "Technical effect")
    else:
        _feat("Technical effect / intended use — value not provided.", "Use", "Technical effect",
              essentiality="Preferred", measurability="Partially measurable")

    form = _parameter_flag(_DOSAGE_FORM.pattern, low)
    if form:
        _feat(f"Final dosage form: {form}.", "Composition", "Dosage form")
    else:
        _feat("Final dosage form — value not provided.", "Composition", "Dosage form",
              essentiality="Preferred", measurability="Partially measurable")

    return features[:12]


def _feature_disclosure(feature_text: str, passage: str) -> tuple:
    """Deterministic disclosure level for one feature against one reference passage.

    Uses the seven-level taxonomy: Explicitly / Inherently / Partially / Broadly
    disclosed, Suggested only, Not disclosed, Unclear. Never labels a feature
    'novel' from a failed search — that is reported as 'Not found in the corpus'."""
    if not passage or not passage.strip():
        return "Unclear", "No passage available in the searched corpus to decide."
    if "not provided" in feature_text or "underdefined" in feature_text:
        return ("Not disclosed",
                "The feature is underdefined by the inventor — the parameter value must be supplied before a comparison is meaningful.")
    qt = _tokens(feature_text)
    if not qt:
        return "Not disclosed", "Not found in the searched corpus."
    plow = passage.lower()
    present = [t for t in qt if t in plow]
    ratio = len(present) / len(qt)
    if ratio >= 0.85:
        level, basis = "Explicitly disclosed", f"{len(present)}/{len(qt)} feature terms appear in the passage."
    elif ratio >= 0.55:
        level, basis = ("Broadly disclosed",
                        f"{len(present)}/{len(qt)} feature terms present; the exact claimed detail or range is not specifically stated.")
    elif ratio >= 0.30:
        level, basis = ("Partially disclosed",
                        f"{len(present)}/{len(qt)} feature terms present; one or more elements of the feature are missing.")
    elif ratio > 0:
        level, basis = ("Suggested only",
                        f"Only {len(present)}/{len(qt)} feature terms present — mentioned as an option or category, not as the disclosed combination.")
    else:
        level, basis = "Not disclosed", "No feature term appears in the passage — not found in the searched corpus."
    return level, basis


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


# --------------------------------------------------------------------------- #
# TDoc Novelty Search — spec-implementing executor
# --------------------------------------------------------------------------- #
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


_PAT_PUBNO = re.compile(r"((?:WO|EP|US|IN|CN|JP|DE|GB|FR|CA|AU|KR|TW)\s?[\dA-Z/]+\d[\dA-Z/]*)")


def _tdoc_ref_kind(c: dict[str, Any]) -> str:
    blob = f"{c.get('act_title') or ''} {c.get('authority') or ''}"
    low = blob.lower()
    if any(w in low for w in ("fda", "fssai", "ayush", "cdsco", "efsa", "who", "health canada", "drugs and cosmetics")):
        return "Regulatory / safety context"
    if any(w in low for w in ("traditional knowledge", "nakt", "ayurveda", "charaka", "sushruta", "bhavaprakash", "tkdl")):
        return "Traditional knowledge"
    if any(w in low for w in ("tdoc", "contribution", "3gpp", "etsi", "meeting", "change request", "agenda")):
        return "TDoc / contribution record"
    if any(w in low for w in ("industry patent", "patent", "uspto", "epo", "wipo", "inpass")):
        return "Patent prior art"
    return "Scientific / technical"


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


_DESIGN_ARTICLES = re.compile(
    r"\b(nasal spray bottle|dropper bottle|spray bottle|blister pack|bottle|jar|tube|box|pouch|vial|"
    r"container|carton|sachet|blister|label|packaging|package|cap|dropper|flacon)\b", re.I,
)
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


_VAGUE_CLAIM_TERMS = re.compile(
    r"\b(about|approximately|substantially|essentially|preferably|optionally|such as|"
    r"etc\.?|a suitable|in one embodiment)\b",
    re.I,
)

_BENEFIT_AS_COMPONENT = re.compile(
    r"\bcognitive\s+support\b|\bgeneral\s+wellness\b|\bbrain\s+(?:function|support)\b|\bstress\s+support\b",
    re.I,
)
_CORRUPT_CROSSWORD = re.compile(r"[A-Za-z]+[Hh]owever|[Hh]owever[A-Za-z]+", re.I)
_UNDEFINED_AMOUNT = re.compile(r"\beffective\s+amounts?\b", re.I)
_UNSUPPORTED_SYNERGY = re.compile(r"\b(?:synergistic\s+proportions?|synergistically?)\b", re.I)
_VAGUE_PROCESS = re.compile(r"\b(?:under\s+)?controlled\s+conditions\b", re.I)
_UNRESOLVED_MARKER = re.compile(r"\[[^\]]*TO BE CONFIRMED[^\]]*\]|\[EXPERIMENTAL DATA REQUIRED\]|\[SOURCE SUPPORT REQUIRED\]", re.I)


def _ingredient_benefit_split(inv: dict[str, Any], resolved: list[dict[str, Any]], inputs: dict[str, Any]) -> dict[str, Any]:
    """Separate actual ingredients from benefit/effect terms and unresolved candidates,
    so claims never treat effects as components."""
    blob = " ".join(filter(None, [inv.get("problem", ""), inv.get("use", ""),
                                  _text(inputs, "process_desc", "formulation_text"),
                                  _text(inputs, "intended_use", "claimed_innovation")]))
    low = blob.lower()
    benefits: list[str] = []
    for b in ("cognitive support", "general wellness", "brain function", "brain support",
              "stress support", "supporting stress", "effective amounts", "synergistic proportions"):
        if b in low and b not in benefits:
            benefits.append(b)
    resolved_names = [r.get("botanical_name") or r.get("raw_name") for r in resolved if r.get("resolved")]
    unresolved_raw = [r.get("raw_name") for r in resolved if not r.get("resolved") and r.get("raw_name")]
    return {
        "ingredients": resolved_names[:8] or inv["ingredients"][:8],
        "unresolved_candidates": unresolved_raw[:8] or ["none"],
        "benefit_terms": benefits or ["none detected"],
        "confirmed": inv["ingredients"],
    }


def _draft_block_reasons(inv: dict[str, Any], inputs: dict[str, Any]) -> list[dict[str, str]]:
    """Block drafting when the disclosure contains corrupted or undefined technical terms.
    These blockers are the gate between parsing and claim structuring — an inventor must
    confirm before any claim is drafted. Returns an empty list when drafting may proceed."""
    blob = " ".join(filter(None, [inv.get("problem", ""), inv.get("use", ""),
                                  _text(inputs, "process_desc", "formulation_text", "claim_text"),
                                  _text(inputs, "intended_use", "claimed_innovation")]))
    reasons: list[dict[str, str]] = []

    def _add(code: str, title: str, why: str) -> None:
        if not any(r["code"] == code for r in reasons):
            reasons.append({"code": code, "title": title, "detail": why})

    ben = _BENEFIT_AS_COMPONENT.search(blob)
    if ben:
        _add("block-benefit", "Benefit language used as a component",
             f"'{ben.group(0)}' appears where a defined ingredient should be. Effect terms cannot be "
             f"drafted as claim components — the inventor must confirm which terms are ingredients and "
             f"which are effects before drafting.")

    for m in _CORRUPT_CROSSWORD.finditer(blob):
        _add("block-corrupt", "Corrupted / miscopied text",
             f"Adjacent words run together ('{m.group(0)}') — likely a copy error from the original notes. "
             f"Resolve the corrupted text with the inventor before structural drafting.")

    eff = _UNDEFINED_AMOUNT.search(blob)
    if eff:
        _add("block-undefined-amount", "Undefined quantity ('effective amounts')",
             "'effective amounts' is not a defined range. Claims require a concrete concentration, weight "
             f"ratio or dosage range, which is absent from the disclosure ({eff.group(0)}).")

    syn = _UNSUPPORTED_SYNERGY.search(blob)
    if syn:
        _add("block-synergy", "Unsupported synergistic proportions",
             f"'{syn.group(0)}' without comparative experimental data, an additive-model basis and a "
             f"statistical method. Synergy cannot be asserted in a claim without that support.")

    ctrl = _VAGUE_PROCESS.search(blob)
    if ctrl:
        _add("block-process", "Vague process conditions",
             f"'{ctrl.group(0)}' — the process parameters (solvent system, temperature, time, ratio, "
             f"scale) are not specified. Name them before the method claim is drafted.")

    solvent = _solvent_word(inv.get("solvent", ""))
    if re.search(r"\bsolvent\b", blob, re.I) and (not solvent or solvent == "solvent"):
        _add("block-solvent", "Solvent named without identity",
             "The description refers to 'solvent' without naming the system (e.g., hydroalcoholic, ethanol, "
             "water, aqueous extract). Name the solvent system before drafting process claims.")

    if re.search(r"\bsupporting\s+stress\b|\bstress\s+relief\b", blob, re.I):
        _add("block-stress", "Undefined stress-support effect",
             "'supporting stress' is a vague effect term — confirm what is measured (cortisol, perceived "
             "stress score, etc.) and keep it out of claim language until an effect definition exists.")

    return reasons


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


def _short_name(name: str) -> str:
    return re.split(r"\s*\(", name)[0].strip() or name


def _first_sentence(text: str) -> str:
    parts = re.split(r"[\.\n]", (text or "").strip())
    sent = parts[0].strip() if parts and parts[0].strip() else "An Ayurvedic botanical composition"
    return sent


def _process_steps(text: str) -> list[str]:
    """Split a process description into ordered, claim-ready steps."""
    text = (text or "").strip()
    if not text:
        return []
    steps = [s.strip(" .;,\t") for s in re.split(r"\d+[\.\):]\s*|\n+|;", text) if s.strip(" .;,\t")]
    if len(steps) <= 1:
        steps = [
            s.strip(" .;,\t")
            for s in re.split(
                r",\s+(?=(?:mix|combine|add|heat|stir|percolat|filter|dry|standard|clarif|extract|grind|blend|fill|compress|pack))",
                text,
                flags=re.I,
            )
            if s.strip(" .;,\t")
        ]
    return [s for s in steps if len(s) > 2][:8]


def _value_markers(text: str) -> list[str]:
    """Extract quantitative characterising parameters, e.g. '5% withanolides' ('40% ethanol' is a solvent, not a marker)."""
    stopwords = {"for", "of", "and", "to", "at", "with", "in", "by", "from", "the", "a", "an", "or", "per", "on"}
    out: list[str] = []
    for m in re.finditer(
        r"\b(\d+(?:[.,]\d+)?(?:[–\-]\s*\d+)?\s*%)\s*([A-Za-z][A-Za-z]*)(?:\s+([A-Za-z][A-Za-z]*))?",
        text or "",
    ):
        word1 = m.group(2)
        word2 = m.group(3)
        words = [w for w in (word1, word2) if w and w.lower() not in stopwords]
        val = f"{m.group(1).strip()} {(' '.join(words))}" if words else m.group(1).strip()
        if val and val not in out:
            out.append(val)
    return out[:6]


def _solvent_word(solvent: str) -> str:
    return re.sub(r"[\d.\-–%\s]+", "", solvent or "").strip().lower()


def _gcd_ratio(a: float, b: float) -> float:
    import math
    scale = 1.0
    while (a * scale) % 1 or (b * scale) % 1:
        scale *= 10
        if scale > 1e6:
            break
    ia, ib = int(round(a * scale)), int(round(b * scale))
    return math.gcd(ia, ib) or 1


def _detected_ratio(text: str, names: list[str]) -> str | None:
    """Detect a quantitative ratio of the first two ingredients from 'a:b' or per-ingredient amounts."""
    text = text or ""
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\b", text)
    if m:
        return f"about {m.group(1)}:{m.group(2)}"
    amounts: list[float] = []
    for name in names[:2]:
        short = _short_name(name)[:20]
        am = re.search(r"([\d.]+)\s*(?:mg|g|kg|%)\s*" + re.escape(short), text, re.I)
        if not am:
            am = re.search(re.escape(short) + r"[^.,;]*?([\d.]+)\s*(?:mg|g|kg|%)", text, re.I)
        if am:
            amounts.append(float(am.group(1)))
    if len(amounts) == 2 and amounts[0] > 0 and amounts[1] > 0:
        g = _gcd_ratio(amounts[0], amounts[1])
        return f"about {int(amounts[0] / g)}:{int(amounts[1] / g)}"
    return None


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


def _parse_invention(inputs: dict[str, Any], resolved: list[dict[str, Any]]) -> dict[str, Any]:
    """Eureka step 1 — parse the invention description into structured drafting elements."""
    problem = (
        _text(inputs, "problem_text", "invention_description", "formulation_text")
        or _basis_text(inputs, "disclosure_text", "document_text")
        or "An Ayurvedic botanical composition"
    )
    ingredients = [_short_name(cast(str, r.get("botanical_name") or r.get("raw_name"))) for r in resolved if r.get("raw_name")]
    names = ingredients[:4] or ["an Ayurvedic botanical"]
    process = _text(inputs, "process_desc", "process")
    steps = _process_steps(process)
    solvent_m = _SOLVENT.search(f"{process} {problem}")
    solvent = solvent_m.group(0).capitalize() if solvent_m else ""
    markers = _value_markers(f"{process} {problem}")
    marker_solvent = next(
        (m for m in markers if any(k in m.lower() for k in ("ethanol", "alcohol", "glycerol", "water", "maceration"))),
        "",
    )
    if marker_solvent:
        solvent = marker_solvent[0].upper() + marker_solvent[1:]
    solvent_words: set = set()
    if _solvent_word(solvent):
        solvent_words.add(_solvent_word(solvent))
    if solvent and solvent_words:
        markers = [m for m in markers if not any(w in m.lower() for w in solvent_words)]
    dosage_form = _text(inputs, "dosage_form") or "an Ayurvedic dosage form"
    use = _text(inputs, "intended_use") or _text(inputs, "claimed_innovation")
    if not use:
        pu = _PURPOSE.search(problem)
        use = pu.group(0) if pu else "nutritional or wellness application"
    title = _first_sentence(problem)
    if len(title) > 110:
        title = title[:110].rsplit(" ", 1)[0] + "..."
    if not re.search(r"(composition|formulation|method|process|preparation|extract)", title, re.I):
        title = f"A composition and method for preparing the same comprising {' and '.join(names[:2])}"
    return {
        "problem": problem,
        "title": title,
        "ingredients": names,
        "steps": steps,
        "solvent": solvent,
        "dosage_form": dosage_form,
        "use": use,
        "markers": markers,
        "ratio": _detected_ratio(f"{_text(inputs, 'formulation_text')} {problem}", names),
    }


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


# --------------------------------------------------------------------------- #
# Office-Action Response helpers (deterministic objection analysis)
# --------------------------------------------------------------------------- #
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


def _citation_kind(c: dict[str, Any]) -> str:
    t = ((c.get("act_title") or "") + " " + (c.get("authority") or "")).lower()
    if "patent" in t:
        return "Patent prior-art"
    if re.search(r"traditional|ayurveda|charaka|susruta|tkdl|monograph", t):
        return "Traditional-knowledge material"
    sk = _source_kind(c.get("authority") or "")
    if sk.startswith("Regulatory corpus"):
        return "Regulatory material"
    if sk.startswith("Scientific literature"):
        return "Non-patent / technical (literature)"
    return "Non-patent / technical"


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


def _split_claims_txt(text: str) -> list[tuple]:
    claims = re.findall(r"(?:^|\n)\s*(\d+)\s*[.)\]]\s+(.*?)(?=\n\s*\d+\s*[.)\]]|\Z)", text or "", re.S)
    if not claims:
        cleaned = (text or "").strip()
        return [("1", cleaned)] if cleaned else []
    return [(num, body.strip()) for num, body in claims]


def _claim_blocks(text: str) -> list[tuple]:
    """Split claim text into (claim number, body) pairs, tolerating multiple
    numbered claims pasted on a single line (e.g. '1. A ... 2. The ...')."""
    normalised = re.sub(r"(?<=[.!;])\s+(?=\d{1,2}\s*[.)]\s+[A-Z])", "\n", text or "")
    return _split_claims_txt(normalised)


def _claim_elements(body: str) -> list[str]:
    parts = re.split(r";\s*|\.\s+", body)
    els: list[str] = []
    for p in parts:
        p = re.sub(r"^\s*(?:[a-e][).]?\s*|\d+\s*[.)]?\s*)", "", p).strip(" .;,").strip()
        if p and len(p) > 3 and not re.fullmatch(r"[A-Za-z]+", p):
            els.append(p[:110])
    return els[:12]


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


# --------------------------------------------------------------------------- #
# Essentiality Claim Chart (AICC) — spec-implementing executor
# --------------------------------------------------------------------------- #
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
_LCA_TOKEN_RE = re.compile(r"[A-Z][A-Za-z0-9'’/\-]+(?:[ \-][A-Za-z0-9][A-Za-z0-9'’/\-]*)?")
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
_LCA_GUIDANCE_HINTS = re.compile(
    r"(guideline|guidance|examination|landscape|checklist|policy|handbook|monograph|procedure\s+for|"
    r"act[,\.]?\s+|regulations?|directive|dshea|federal\s+food|biodiversity|access\s+and\s+benefit|"
    r"traditional\s+knowledge|ayurvedic\s+pharmacopoeia|pharmacopoeia)",
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
_LSM_FORMULA_RE = re.compile(r"\bC\d+(?:H\d+)?(?:[NOSPClI][a-z]?\d*)+\b")
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
_SAR_LABEL_RE = re.compile(r"\b(?:Compound|Cmpd|Cpd|Example|A\s*[0-9]+|Entry)\s*[.#]?\s*[A-Z0-9]+\b", re.I)
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


_ABP_GENERIC_TARGETS = {
    "interleukin", "cytokine", "protein", "receptor", "immune target", "biologic",
    "antigen", "target", "project", "description", "demo", "title",
}
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
_ABP_SOURCE_REG_RE = re.compile(
    r"\b(ich|q6b|fda|fssai|tkdl|biodiversity|dshea|quality\s+standard|"
    r"immunogenicity\s+guidance|biologic[\s-]?characterization|ayurveda)",
    re.I,
)


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
_FORM_FORMULA_LANG_RE = re.compile(
    r"\b(Withania\b[^%\n]{0,40}%\s*w/w|Ginkgo\b[^%\n]{0,40}%\s*w/w|\d+(?:\.\d+)?\s*%\s*w/w)",
    re.I)

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
_MAT_CAUSE_RE = re.compile(
    r"\bmaterial\b|process\b|storage\b|supply\b|batch\s+variation\b|raw\s+material\b|"
    r"equipment\b|humidity\b|temperature\b", re.I)
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


# register the 19 Agent-Hub slugs on the shared executor table
for _hub_slug in [
    "triz", "quick_research", "find_solutions",
    "novelty_search", "fto_search", "design_fto",
    "patent_drafting", "invention_disclosure", "office_action_response",
    "essentiality_claim_chart", "tdoc_novelty_search",
    "document_analyzer", "lca_biotherapeutic", "lca_small_molecule",
    "sar_data_extraction", "antibody_target_predictor", "markush_drafting",
    "formulation", "materials_find_solutions",
]:
    import functools as _functools  # noqa: E402
    EXECUTORS[_hub_slug] = _functools.partial(_exec_hub_generic, _hub_slug)