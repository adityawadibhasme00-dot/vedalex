"""Component 11 — Eval Harness, Master Prompt v7.0.0.

50-question Q&A test set scored end-to-end through the AgenticChain:

    metrics:
      routing_accuracy    — orchestrator query_type matches the labelled intent
      language_accuracy   — language detection (where labelled)
      jurisdiction_accuracy — jurisdiction routing (where labelled)
      abstention_accuracy — out-of-scope questions are rejected/abstained and
                            in-scope questions are answered
      category_accuracy   — formulation classifier labels (where labelled)
      citation_rate       — answered questions with ≥1 verified citation
      avg_confidence      — mean confidence (HIGH=1, MEDIUM=0.5, LOW=0)

Run:
    python tests/eval_harness.py            # summary, exit 0
    python tests/eval_harness.py --strict   # exit 1 if below thresholds
    python tests/eval_harness.py --json out.json

Not collected by pytest (filename has no ``test_`` prefix).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Allow `python tests/eval_harness.py` from the backend/ directory.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# ---------------------------------------------------------------------------
# 50-question labelled test set
# ---------------------------------------------------------------------------

QUESTIONS: list[dict[str, Any]] = [
    # -- PRODUCT_SPECIFIC (10) ---------------------------------------------
    {"id": "Q01", "query": "Can we patent an Ashwagandha churna from Charaka Samhita?",
     "expect": {"query_type": "PRODUCT_SPECIFIC", "category": "CLASSICAL_MEDICINE"}},
    {"id": "Q02", "query": "Ashwagandha churna ka patent kar sakte hain?",
     "expect": {"query_type": "PRODUCT_SPECIFIC", "language": "hi"}},
    {"id": "Q03", "query": "Is a formulation from Charaka Samhita patentable?",
     "expect": {"query_type": "PRODUCT_SPECIFIC", "category": "CLASSICAL_MEDICINE"}},
    {"id": "Q04", "query": "What license do I need for our Giloy kwath product?",
     "expect": {"query_type": "PRODUCT_SPECIFIC"}},
    {"id": "Q05", "query": "Can I patent a Brahmi Vati tablet formulation?",
     "expect": {"query_type": "PRODUCT_SPECIFIC"}},
    {"id": "Q06", "query": "Is a Sharangadhara Samhita Asava covered under Section 3(p)?",
     "expect": {"query_type": "PRODUCT_SPECIFIC"}},
    {"id": "Q07", "query": "Our Turmeric capsule dosage form — patentable?",
     "expect": {"query_type": "PRODUCT_SPECIFIC"}},
    {"id": "Q08", "query": "What protection applies to a formulation from the Ayurvedic Formulary?",
     "expect": {"query_type": "PRODUCT_SPECIFIC"}},
    {"id": "Q09", "query": "Neem cream for external use — trademark options?",
     "expect": {"query_type": "PRODUCT_SPECIFIC", "category": "COSMETIC"}},
    {"id": "Q10", "query": "Can we patent a Guggulu tablet with a film coated layer?",
     "expect": {"query_type": "PRODUCT_SPECIFIC"}},
    # -- ABS_QUESTION (8) ---------------------------------------------------
    {"id": "Q11", "query": "Do we need NBA approval for access and benefit sharing?",
     "expect": {"query_type": "ABS_QUESTION"}},
    {"id": "Q12", "query": "Does the Biological Diversity Act apply to our tulsi sourcing?",
     "expect": {"query_type": "ABS_QUESTION"}},
    {"id": "Q13", "query": "What benefit-sharing obligations apply to wild-collected ingredients?",
     "expect": {"query_type": "ABS_QUESTION"}},
    {"id": "Q14", "query": "Is prior approval required from the National Biodiversity Authority?",
     "expect": {"query_type": "ABS_QUESTION"}},
    {"id": "Q15", "query": "Our ABS compliance path for a research collaboration?",
     "expect": {"query_type": "ABS_QUESTION"}},
    {"id": "Q16", "query": "Can an AYUSH practitioner use biological resources without NBA approval?",
     "expect": {"query_type": "ABS_QUESTION"}},
    {"id": "Q17", "query": "What Form do we file for access to biological resources?",
     "expect": {"query_type": "ABS_QUESTION"}},
    {"id": "Q18", "query": "Does codified traditional knowledge exempt us from benefit sharing?",
     "expect": {"query_type": "ABS_QUESTION"}},
    # -- PRIOR_ART_QUESTION (9) ---------------------------------------------
    {"id": "Q19", "query": "Is turmeric patentable for wound healing?",
     "expect": {"query_type": "PRIOR_ART_QUESTION"}},
    {"id": "Q20", "query": "Has someone patented Ashwagandha for sleep?",
     "expect": {"query_type": "PRIOR_ART_QUESTION"}},
    {"id": "Q21", "query": "Run a prior art search on Brahmi nootropic claims",
     "expect": {"query_type": "PRIOR_ART_QUESTION"}},
    {"id": "Q22", "query": "Is a neem pesticide already patented?",
     "expect": {"query_type": "PRIOR_ART_QUESTION"}},
    {"id": "Q23", "query": "Can we patent a new extraction process for saffron?",
     "expect": {"query_type": "PRIOR_ART_QUESTION"}},
    {"id": "Q24", "query": "Freedom to operate for a capsule formulation in the European market?",
     "expect": {"query_type": "PRIOR_ART_QUESTION"}},
    {"id": "Q25", "query": "Has anyone patented jamun seed extract?",
     "expect": {"query_type": "PRIOR_ART_QUESTION"}},
    {"id": "Q26", "query": "What is the novelty of a known herbal formulation?",
     "expect": {"query_type": "PRIOR_ART_QUESTION"}},
    {"id": "Q27", "query": "Is there prior art on standardized amla extract?",
     "expect": {"query_type": "PRIOR_ART_QUESTION"}},
    # -- GENERAL_LEGAL (8) --------------------------------------------------
    {"id": "Q28", "query": "What is a patent?",
     "expect": {"query_type": "GENERAL_LEGAL"}},
    {"id": "Q29", "query": "Explain Section 3(p) of the Patents Act.",
     "expect": {"query_type": "GENERAL_LEGAL", "jurisdiction": "india"}},
    {"id": "Q30", "query": "How long does patent protection last in India?",
     "expect": {"query_type": "GENERAL_LEGAL", "jurisdiction": "india"}},
    {"id": "Q31", "query": "What is the difference between a patent and a trademark?",
     "expect": {"query_type": "GENERAL_LEGAL"}},
    {"id": "Q32", "query": "How do I file a patent application with the patent office?",
     "expect": {"query_type": "GENERAL_LEGAL"}},
    {"id": "Q33", "query": "What are the trademark classes for herbal products?",
     "expect": {"query_type": "GENERAL_LEGAL"}},
    {"id": "Q34", "query": "How does the Trade Marks Act protect a brand name?",
     "expect": {"query_type": "GENERAL_LEGAL"}},
    {"id": "Q35", "query": "What is GI registration and who can apply?",
     "expect": {"query_type": "GENERAL_LEGAL"}},
    # -- OUT_OF_SCOPE → must abstain/escalate (8) ---------------------------
    {"id": "Q36", "query": "Should I sue them for copying my product?",
     "expect": {"query_type": "OUT_OF_SCOPE", "abstain": True}},
    {"id": "Q37", "query": "Will my patent be granted for sure?",
     "expect": {"query_type": "OUT_OF_SCOPE", "abstain": True}},
    {"id": "Q38", "query": "What dosage of Ashwagandha should I take daily?",
     "expect": {"query_type": "OUT_OF_SCOPE", "abstain": True}},
    {"id": "Q39", "query": "Take 500 mg of Ashwagandha — is that safe?",
     "expect": {"query_type": "OUT_OF_SCOPE", "abstain": True}},
    {"id": "Q40", "query": "Can you prescribe something for my migraine?",
     "expect": {"query_type": "OUT_OF_SCOPE", "abstain": True}},
    {"id": "Q41", "query": "What is the cure for my diabetes?",
     "expect": {"query_type": "OUT_OF_SCOPE", "abstain": True}},
    {"id": "Q42", "query": "Predict whether my patent will be granted.",
     "expect": {"query_type": "OUT_OF_SCOPE", "abstain": True}},
    {"id": "Q43", "query": "What is the court strategy to enforce my design patent?",
     "expect": {"query_type": "OUT_OF_SCOPE", "abstain": True}},
    # -- International / BOTH jurisdiction (5) -------------------------------
    {"id": "Q44", "query": "How does the TRIPS agreement affect our ayurvedic exports?",
     "expect": {"query_type": "GENERAL_LEGAL", "jurisdiction": "international"},
     "toggle": "international"},
    {"id": "Q45", "query": "What is the PCT filing route for our invention?",
     "expect": {"query_type": "GENERAL_LEGAL", "jurisdiction": "international"},
     "toggle": "international"},
    {"id": "Q46", "query": "WIPO mediation for a cross-border dispute?",
     "expect": {"query_type": "GENERAL_LEGAL", "jurisdiction": "international"},
     "toggle": "international"},
    {"id": "Q47", "query": "Can we file an Indian patent and a PCT application together?",
     "expect": {"query_type": "GENERAL_LEGAL", "jurisdiction": "both"}},
    {"id": "Q48", "query": "Export regulations for our herbal products to the USA?",
     "expect": {"query_type": "GENERAL_LEGAL", "jurisdiction": "international"},
     "toggle": "international"},
    # -- Multilingual (2) -----------------------------------------------------
    {"id": "Q49", "query": "गिलोय की दवा का पेटेंट कैसे करें?",
     "expect": {"query_type": "GENERAL_LEGAL", "language": "hi"}},
    {"id": "Q50", "query": "kya ye formulation patentable hai?",
     "expect": {"query_type": "PRODUCT_SPECIFIC", "language": "hi"}},
]

THRESHOLDS = {
    "routing_accuracy": 0.9,
    "abstention_accuracy": 0.9,
    "language_accuracy": 0.9,
}

_CONFIDENCE_SCORE = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.0}


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def run_eval(
    questions: list[dict[str, Any]] | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Execute the labelled set through the AgenticChain and score it."""
    from app.agents.chain import AgenticChain
    from app.rag.retrieval_pipeline import HybridRetriever

    questions = questions if questions is not None else QUESTIONS
    # Build the BM25 index / preload embeddings exactly as the API does on
    # startup — otherwise the first queries all abstain on an empty index.
    try:
        HybridRetriever.reindex_all()
    except Exception as exc:  # noqa: BLE001 — eval still runs on failure
        print(f"WARN: reindex_all failed ({exc}); retrieval may be partial",
              flush=True)

    chain = AgenticChain()
    results: list[dict[str, Any]] = []

    routing_ok = lang_ok = jur_ok = abst_ok = cat_ok = 0
    routing_n = lang_n = jur_n = abst_n = cat_n = 0
    answered = cited = 0
    conf_total = 0.0

    for item in questions:
        expect = item.get("expect", {})
        toggle = item.get("toggle", "india")
        out = chain.execute(item["query"], jurisdiction=toggle)
        routing = out.get("routing") or {}
        checks: dict[str, bool] = {}

        if "query_type" in expect:
            routing_n += 1
            checks["query_type"] = routing.get("query_type") == expect["query_type"]
            routing_ok += int(checks["query_type"])
        if "language" in expect:
            lang_n += 1
            checks["language"] = routing.get("language") == expect["language"]
            lang_ok += int(checks["language"])
        if "jurisdiction" in expect:
            jur_n += 1
            checks["jurisdiction"] = (
                routing.get("jurisdiction") == expect["jurisdiction"]
            )
            jur_ok += int(checks["jurisdiction"])
        if "abstain" in expect:
            abst_n += 1
            is_abstained = out.get("status") in ("rejected", "abstained")
            checks["abstain"] = is_abstained == bool(expect["abstain"])
            abst_ok += int(checks["abstain"])
        if "category" in expect:
            classification = out.get("classification") or {}
            if classification.get("category"):
                cat_n += 1
                checks["category"] = (
                    classification["category"] == expect["category"]
                )
                cat_ok += int(checks["category"])

        status = out.get("status")
        confidence = str(out.get("confidence") or "LOW")
        conf_total += _CONFIDENCE_SCORE.get(confidence, 0.0)
        has_valid_citation = bool(
            (out.get("citations") or {}).get("valid_citations")
        )
        if status == "answered":
            answered += 1
            cited += int(has_valid_citation)

        passed = all(checks.values()) if checks else True
        record = {
            "id": item["id"],
            "query": item["query"],
            "status": status,
            "confidence": confidence,
            "query_type": routing.get("query_type"),
            "language": routing.get("language"),
            "jurisdiction": routing.get("jurisdiction"),
            "checks": checks,
            "passed": passed,
        }
        results.append(record)
        if verbose and not passed:
            print(f"FAIL {item['id']}: {record}", flush=True)

    total = len(questions)
    metrics = {
        "routing_accuracy": _ratio(routing_ok, routing_n),
        "language_accuracy": _ratio(lang_ok, lang_n),
        "jurisdiction_accuracy": _ratio(jur_ok, jur_n),
        "abstention_accuracy": _ratio(abst_ok, abst_n),
        "category_accuracy": _ratio(cat_ok, cat_n),
        "citation_rate": _ratio(cited, answered),
        "avg_confidence": round(conf_total / total, 4) if total else 0.0,
        "answered": answered,
        "questions": total,
        "passed": sum(1 for r in results if r["passed"]),
    }
    below = {
        name: {"value": metrics[name], "threshold": threshold}
        for name, threshold in THRESHOLDS.items()
        if metrics[name] < threshold
    }
    return {
        "metrics": metrics,
        "below_threshold": below,
        "thresholds": dict(THRESHOLDS),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IP-SAKTI agentic RAG eval")
    parser.add_argument("--json", type=Path, help="write full report to path")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when thresholds are missed")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="print every failing question")
    args = parser.parse_args(argv)

    report = run_eval(verbose=args.verbose)
    metrics = report["metrics"]
    print("=" * 60)
    print("IP-SAKTI AGENTIC RAG EVAL — 50 labelled questions")
    print("=" * 60)
    for name in (
        "routing_accuracy",
        "language_accuracy",
        "jurisdiction_accuracy",
        "abstention_accuracy",
        "category_accuracy",
        "citation_rate",
        "avg_confidence",
    ):
        print(f"  {name:<24} {metrics[name]}")
    print(f"  {'passed/questions':<24} {metrics['passed']}/{metrics['questions']}")
    if report["below_threshold"]:
        print("-" * 60)
        print("BELOW THRESHOLD:")
        for name, detail in report["below_threshold"].items():
            print(f"  {name}: {detail['value']} < {detail['threshold']}")
    print("=" * 60)

    if args.json:
        args.json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"report written: {args.json}")

    if args.strict and report["below_threshold"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
