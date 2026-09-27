"""Eureka-parity validation runner — run from repo root:
    backend\\venv\\Scripts\\python.exe scripts\\verify_eureka_parity.py
Prints PASS/FAIL for every Innovation-Lab agent against the Eureka parity checklist
(EUREKA_PARITY_CHECKLIST.md). Any FAIL must be fixed before claiming parity."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.services.innolab.agent_executors import execute_agent

BASE_INP = {
    "problem_text": "A restful-sleep liquid formulation with Ashwagandha and Brahmi for Canada",
    "ingredients": ["Ashwagandha", "Brahmi"],
    "target_markets": ["Canada", "United States"],
}

INPUTS = {
    "triz": {"problem_text": "Potency of the extract degrades during hot-water processing", "improve_aspect": "Yield", "tradeoff": "Stability"},
    "quick_research": {"problem_text": "Adaptogens for cognitive health - Ashwagandha vs Brahmi evidence base", "target_markets": ["Canada"]},
    "find_solutions": {"problem_text": "Product clumps and settles during storage"},
    "novelty_search": BASE_INP,
    "tdoc_novelty_search": {"disclosure_text": "Two-stage hydroalcoholic extraction achieving >90% withanolide recovery", "problem_text": "Two-stage recovery process"},
    "fto_search": BASE_INP,
    "design_fto": BASE_INP,
    "patent_drafting": {"problem_text": "A stable hydroalcoholic Ashwagandha-Brahmi composition", "ingredients": ["Ashwagandha", "Brahmi"], "target_markets": ["Canada"]},
    "invention_disclosure": {"problem_text": "Mixed 3 parts ashwagandha root with 1 part brahmi, 40% alcohol, 70C", "formulation_text": "hydroalcoholic extraction 4h", "improve_aspect": "36-month stability"},
    "office_action_response": {"office_action_text": "Claims 1-10 rejected under 35 U.S.C. 103 as obvious", "target_markets": ["United States"]},
    "essentiality_claim_chart": {"patent_number": "US10,123,456", "standard_name": "TS 38.214"},
    "document_analyzer": {"document_text": "Certificate of Analysis: Ashwagandha root extract, Withanolides 5.2%"},
    "lca_biotherapeutic": {"problem_text": "Anti-inflammatory monoclonal antibodies using plant-derived glycoprotein scaffolds"},
    "lca_small_molecule": {"compound_desc": "Withaferin A (C28H38O6), Withanolide D", "target_markets": ["Canada"]},
    "sar_data_extraction": {"compound_desc": "Withaferin A - IC50 0.8 uM; Withanolide D - IC50 2.1 uM", "activity_metric": "IC50"},
    "antibody_target_predictor": {"antibody_desc": "Humanised IgG1 against a plant-derived lectin with anti-inflammatory activity"},
    "markush_drafting": {"core_structure": "withanolide lactone scaffold with 5b-6b-epoxy", "variant_features": ["R1 = H, OH, OCH3", "R2 = alkyl, aryl"]},
    "formulation": BASE_INP,
    "materials_find_solutions": {"material_challenge": "Extract absorbs moisture and cakes; need better anti-caking", "current_material": "magnesium stearate", "performance_target": "Moisture resistance"},
}


def main() -> int:
    archived = []
    for slug, inp in INPUTS.items():
        result = execute_agent(slug, inp)
        sections = result.get("sections", [])
        sources = any("Data sources" in s.get("title", "") for s in sections)
        checks = {
            "ok": bool(result.get("ok")),
            "sections (>0)": bool(sections),
            "data sources rail": sources,
            "workflow steps (>0)": bool(result.get("workflow")),
        }
        bad = [name for name, ok in checks.items() if not ok]
        state = "PASS" if not bad else "FAIL"
        reason = "" if not bad else f" <- missing: {', '.join(bad)}"
        archived.append((state, slug, len(sections), reason))
        print(f"{state}  {slug:<26} sections={len(sections):<2} wf={len(result.get('workflow', [])):<2} data_sources={sources}{reason}")
    failed = [row for row in archived if row[0] == "FAIL"]
    print(f"\nResult: {len(archived) - len(failed)}/{len(archived)} PASS" + (" — parity holds." if not failed else " — failures to fix."))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())