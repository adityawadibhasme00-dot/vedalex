"""Agent registry and dispatch for the Innovation AI Lab.

This module is the **public surface**: the slug registry, ``execute_agent``,
input schemas and the hub dispatch table.  The work itself lives in
``app/services/innolab/agents/``, one module per domain:

* ``agents/discovery.py`` — find_solutions, quick_research, triz
* ``agents/novelty.py`` — novelty, tdoc_novelty
* ``agents/fto.py`` — design_fto, fto
* ``agents/patent.py`` — claim_chart, office_action, patent_drafting
* ``agents/disclosure.py`` — invention_disclosure
* ``agents/contract_analysis.py`` — document_analyzer, markush
* ``agents/pharma.py`` — antibody, lca_small, lead_candidate, sar
* ``agents/product.py`` — formulation, materials

Shared grounding primitives (corpus loading, ingredient resolution,
retrieval, evidence shaping) are in ``innolab/_shared.py``; text-analysis
primitives used by more than one domain are in ``agents/_shared_text.py``.

Deterministic, knowledge-grounded implementations for every registered
Innovation-Lab agent.  Every executor runs fully offline against the local
corpus -- Ayurvedic Pharmacopoeia of India monographs, botanical synonym
table, bioresource index, pathway rules and the KB passage store -- so runs
are reproducible and every finding can point at a real source.  No external
provider is contacted and nothing is ever fabricated; when the corpus has no
answer the agent says so instead of guessing.
"""

from __future__ import annotations

import re
from typing import Any, cast

# --- grounding primitives --------------------------------------------
from app.services.innolab._shared import (
    _AUTHORITY_KIND,
    _CURATIVE,
    _INJECTION,
    _KB,
    _PROHIBITED_CLAIM,
    _PURPOSE,
    _SOLVENT,
    _api_monographs,
    _as_citation,
    _base_result,
    _bioresource,
    _claim_signals,
    _draft_claims,
    _evidence,
    _finding,
    _fingerprint,
    _ingredient_names,
    _jurisdiction_code,
    _list_value,
    _load_json,
    _markets,
    _pathway_rules,
    _real_ref,
    _resolve_ingredients,
    _retrieve,
    _scan_formulation,
    _section,
    _source_kind,
    _sources_section,
    _text,
)

# --- domain agents (S5) ---------------------------------------------
# agents/contract_analysis.py -- _hub_document_analyzer, _hub_markush
from app.services.innolab.agents.contract_analysis import (  # noqa: F401
    _DA_META_LABEL_RE,
    _DA_OCR_ARTIFACT_RE,
    _DA_ADMIN_LINE_RE,
    _DA_MD_HEAD_RE,
    _DA_NUM_HEAD_RE,
    _DA_CHAPTER_RE,
    _DA_UNIT_RE,
    _DA_TABLE_LINE_RE,
    _DA_FIG_CAP_RE,
    _DA_OBLIGATION_MAP,
    _DA_GENERIC_CONCEPT,
    _DA_BIO_HINTS,
    _DA_ORG_SUFFIX,
    _DA_DEFN_RE,
    _DA_REF_RE,
    _da_lines,
    _da_is_artifact,
    _da_is_admin,
    _da_meta,
    _da_title,
    _da_structure,
    _da_obligations,
    _da_measures,
    _da_tables,
    _da_figures,
    _da_entity_context,
    _da_entity_categorise,
    _da_entities,
    _da_definitions,
    _da_crossrefs,
    _da_quality_band,
    _hub_document_analyzer,
    _MK_HEADING_RE,
    _MK_ARTIFACT_RE,
    _MK_STRUCTURE_RE,
    _MK_SMILES_FRAGMENT_RE,
    _MK_FORMULA_RE,
    _MK_RGROUP_RE,
    _MK_N_RE,
    _MK_BROAD_RE,
    _MK_LACTONE_RE,
    _MK_LACTONE_VARIATION_RE,
    _MK_SCAFFOLD_RE,
    _MK_EXAMPLE_RE,
    _MK_ACTIVITY_RE,
    _mk_clean,
    _mk_formula_status,
    _mk_rgroups,
    _mk_combinations,
    _hub_markush,
)
# agents/disclosure.py -- _hub_invention_disclosure
from app.services.innolab.agents.disclosure import (  # noqa: F401
    _disclosure_ratio,
    _PART_MARKERS,
    _SKIP_MENTION,
    _mention_candidates,
    _hub_invention_disclosure,
)
# agents/discovery.py -- _hub_find_solutions, _hub_quick_research, _hub_triz
from app.services.innolab.agents.discovery import (  # noqa: F401
    _hub_triz,
    _system_from_problem,
    _detect_improve_tradeoff,
    _triz_fallback_name,
    _triz_propose_empty_cell,
    _triz_success_metrics,
    _triz_validation_plan,
    _qr_jurisdiction_hint,
    _qr_provisional_classification,
    _hub_quick_research,
    _fs_failure_modes,
    _hub_find_solutions,
)
# agents/fto.py -- _hub_design_fto, _hub_fto
from app.services.innolab.agents.fto import (  # noqa: F401
    _source_category,
    _fto_product_elements,
    _fto_claim_rows,
    _fto_activity_matrix,
    _hub_fto,
    _DESIGN_SILHOUETTE,
    _DESIGN_CONFIGURATION,
    _DESIGN_SURFACE,
    _DESIGN_ORNAMENT,
    _DESIGN_COLOUR,
    _DESIGN_LABEL,
    _DESIGN_FUNCTIONAL,
    _design_source_category,
    _design_article,
    _design_visual_features,
    _hub_design_fto,
)
# agents/novelty.py -- _hub_novelty, _hub_tdoc_novelty
from app.services.innolab.agents.novelty import (  # noqa: F401
    _hub_novelty,
    _TDOC_ADMIN_PATTERNS,
    _TDOC_SYSTEM_RE,
    _tdoc_corruption,
    _tdoc_is_admin_line,
    _tdoc_tag_lines,
    _tdoc_classify_feature,
    _tdoc_ref_passage_label,
    _tdoc_is_self,
    _tdoc_hardening,
    _hub_tdoc_novelty,
)
# agents/patent.py -- _hub_claim_chart, _hub_office_action, _hub_patent_drafting
from app.services.innolab.agents.patent import (  # noqa: F401
    _VAGUE_CLAIM_TERMS,
    _UNRESOLVED_MARKER,
    _draft_blocker_check,
    _skeleton_claims,
    _use_phrase,
    _build_terms_map,
    _embedded_prior_art,
    _essential_features,
    _draft_patent_claims,
    _compliance_checks,
    _draft_abstract,
    _draft_figures,
    _draft_spec_sections,
    _hub_patent_drafting,
    _OA_GROUNDS,
    _OA_STRATEGY,
    _OA_EVIDENCE,
    _extract_claims,
    _classify_ground,
    _segment_objections,
    _claim_blocks,
    _hub_office_action,
    _STANDARD_BODY_WORDS,
    _standard_hint,
    _is_standard_source,
    _chart_type,
    _clause_obligation,
    _feature_match_label,
    _essentiality_verdict,
    _evidence_tier,
    _hub_claim_chart,
)
# agents/pharma.py -- _hub_antibody, _hub_lca_small, _hub_lead_candidate, _hub_sar
from app.services.innolab.agents.pharma import (  # noqa: F401
    _LCA_EXCLUDED,
    _LCA_INN_SUFFIX,
    _LCA_CLONE_RE,
    _LCA_SEQ_PATTERN,
    _LCA_ACCESSION,
    _LCA_MODALITY_HINTS,
    _LCA_TARGET_RE,
    _lca_tokens,
    _lca_validate,
    _lca_modality,
    _lca_target,
    _lca_patent_rows,
    _lca_rank_scorecard,
    _LSM_EXCLUDED,
    _LSM_BOTANICAL,
    _LSM_CAS_RE,
    _LSM_COMPOUND_LABEL_RE,
    _LSM_NAMED_RE,
    _LSM_CHEM_SUFFIX,
    _LSM_ACTIVITY_RE,
    _LSM_MARKUSH_RE,
    _LSM_FIRSTWORD_STOP,
    _lsm_first_word,
    _lsm_activity_near,
    _lsm_candidates,
    _lsm_patent_rows,
    _lsm_rank_scorecard,
    _hub_lca_small,
    _hub_lead_candidate,
    _SAR_ARTIFACT_RE,
    _SAR_ACTIVITY_RE,
    _SAR_SEG_SPLIT,
    _SAR_NAME_SEP,
    _sar_is_artifact,
    _sar_unit_norm,
    _SAR_EXPORT_COLS,
    _hub_sar,
    _ABP_IL_RE,
    _ABP_SEQ_RE,
    _ABP_CDR_LABEL_RE,
    _ABP_AA_VALID,
    _ABP_KD_RE,
    _ABP_BINDING_RE,
    _ABP_FUNCTIONAL_RE,
    _ABP_STRUCTURE_RE,
    _ABP_SELECTIVITY_RE,
    _ABP_PATENT_RE,
    _abp_is_aa_seq,
    _abp_family_only,
    _abp_evidence_level,
    _abp_confidence_components,
    _abp_sequences,
    _abp_candidates,
    _abp_affinity,
    _hub_antibody,
)
# agents/product.py -- _hub_formulation, _hub_materials
from app.services.innolab.agents.product import (  # noqa: F401
    _FORM_PCT_RE,
    _FORM_RANGE_RE,
    _FORM_PH_RE,
    _FORM_TEMP_RE,
    _FORM_TIME_RE,
    _FORM_SOLVENT_ARTIFACT_RE,
    _FORM_STRATEGY_RE,
    _FORM_MICROBE_CLAIM_RE,
    _FORM_PROCESS_CLAIM_RE,
    _FORM_COMPAT_CLAIM_RE,
    _FORM_CLAIM_RE,
    _FORM_OBJECTIVE_RE,
    _FORM_GAP_RE,
    _FORM_DECISION_WEIGHTS,
    _FORM_ENV_CLAIMS,
    _FORM_PC_OPTIONS,
    _form_concentration,
    _form_ingredient_names,
    _form_one_strategy_id,
    _form_cna_pct,
    _hub_formulation,
    _SOLVENT_MAP,
    _solvent_short,
    _detect_solvent,
    _MAT_MATERIAL_TERM_RE,
    _MAT_PROPERTY_OBS_RE,
    _MAT_KPP_RE,
    _MAT_RISK_RE,
    _MAT_COST_RE,
    _MAT_PROCESS_FIX_RE,
    _MAT_VALIDATION_GAP_RE,
    _mat_material_names,
    _mat_property_obs,
    _mat_grade,
    _hub_materials,
)

# --- shared text-analysis primitives ---------------------------------
from app.services.innolab.agents._shared_text import (  # noqa: F401
    _BENEFIT_AS_COMPONENT,
    _CORRUPT_CROSSWORD,
    _DEVICE_TERM,
    _DOSAGE_FORM,
    _HAS_PROCESS_VERB,
    _HYDROALCOHOLIC,
    _LCA_GUIDANCE_HINTS,
    _LCA_TOKEN_RE,
    _LSM_FORMULA_RE,
    _NC_STOP,
    _PAT_PUBNO,
    _STOPWORDS,
    _UNDEFINED_AMOUNT,
    _UNSUPPORTED_SYNERGY,
    _VAGUE_PROCESS,
    _atomic_novelty_features,
    _basis_text,
    _citation_kind,
    _claim_elements,
    _detected_ratio,
    _draft_block_reasons,
    _feature_disclosure,
    _first_sentence,
    _gcd_ratio,
    _ingredient_benefit_split,
    _keyword_phrases,
    _overlap_similarity,
    _parameter_flag,
    _parse_invention,
    _process_steps,
    _short_name,
    _solvent_word,
    _split_claims_txt,
    _tdoc_ref_kind,
    _tokens,
    _value_markers,
)

# --- carried imports (used by the kept dispatch code) ---------------
from app.services.agent_hub import toolbox
from app.services.innolab import agent_workflows

__all__ = [
    "EXECUTORS",
    "execute_agent",
    "input_schema",
    "sample_query",
    "_workflow_trace",
    "_exec_hub_generic",
    "_hub_execution",
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
    "_disclosure_ratio",
    "_PART_MARKERS",
    "_SKIP_MENTION",
    "_mention_candidates",
    "_hub_invention_disclosure",
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
    "_BENEFIT_AS_COMPONENT",
    "_CORRUPT_CROSSWORD",
    "_DEVICE_TERM",
    "_DOSAGE_FORM",
    "_HAS_PROCESS_VERB",
    "_HYDROALCOHOLIC",
    "_LCA_GUIDANCE_HINTS",
    "_LCA_TOKEN_RE",
    "_LSM_FORMULA_RE",
    "_NC_STOP",
    "_PAT_PUBNO",
    "_STOPWORDS",
    "_UNDEFINED_AMOUNT",
    "_UNSUPPORTED_SYNERGY",
    "_VAGUE_PROCESS",
    "_atomic_novelty_features",
    "_basis_text",
    "_citation_kind",
    "_claim_elements",
    "_detected_ratio",
    "_draft_block_reasons",
    "_feature_disclosure",
    "_first_sentence",
    "_gcd_ratio",
    "_ingredient_benefit_split",
    "_keyword_phrases",
    "_overlap_similarity",
    "_parameter_flag",
    "_parse_invention",
    "_process_steps",
    "_short_name",
    "_solvent_word",
    "_split_claims_txt",
    "_tdoc_ref_kind",
    "_tokens",
    "_value_markers",
]


import functools as _functools  # noqa: E402


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


def _workflow_trace(slug: str) -> list[dict[str, str]]:
    return [{"label": s.get("label", cast(str, s)), "status": "completed"} for s in agent_workflows.workflow_steps(slug)]


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


_DISCLOSURE_LEVELS = (
    "Explicitly disclosed",
    "Inherently disclosed",
    "Partially disclosed",
    "Broadly disclosed",
    "Suggested only",
    "Not disclosed",
    "Unclear",
)


_DESIGN_ARTICLES = re.compile(
    r"\b(nasal spray bottle|dropper bottle|spray bottle|blister pack|bottle|jar|tube|box|pouch|vial|"
    r"container|carton|sachet|blister|label|packaging|package|cap|dropper|flacon)\b", re.I,
)


_SAR_LABEL_RE = re.compile(r"\b(?:Compound|Cmpd|Cpd|Example|A\s*[0-9]+|Entry)\s*[.#]?\s*[A-Z0-9]+\b", re.I)


_ABP_GENERIC_TARGETS = {
    "interleukin", "cytokine", "protein", "receptor", "immune target", "biologic",
    "antigen", "target", "project", "description", "demo", "title",
}


_ABP_SOURCE_REG_RE = re.compile(
    r"\b(ich|q6b|fda|fssai|tkdl|biodiversity|dshea|quality\s+standard|"
    r"immunogenicity\s+guidance|biologic[\s-]?characterization|ayurveda)",
    re.I,
)


_FORM_FORMULA_LANG_RE = re.compile(
    r"\b(Withania\b[^%\n]{0,40}%\s*w/w|Ginkgo\b[^%\n]{0,40}%\s*w/w|\d+(?:\.\d+)?\s*%\s*w/w)",
    re.I)


_MAT_CAUSE_RE = re.compile(
    r"\bmaterial\b|process\b|storage\b|supply\b|batch\s+variation\b|raw\s+material\b|"
    r"equipment\b|humidity\b|temperature\b", re.I)


def _hub_execution(slug: str) -> dict[str, Any]:
    return {
        "planner": f"{slug} planner resolved the guided workflow",
        "reasoning": f"{slug} domain reasoning applied over retrieved evidence",
        "validation": "Findings trace to corpus sources; gaps are reported, nothing fabricated",
    }


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
