"""
RAG groundedness evaluation + regression harness.

Runs the full copilot RAG pipeline over a fixed set of sample queries and
reports, per query: intent, verification badge, confidence, answer length,
whether the answer is backed by retrieved knowledge-base records, and the
hallucination-guard risk. Any critical hallucination risk on a grounded,
answerable query fails the run — this is the "no-hallucination" regression
check.

Usage (from backend/):
    python scripts/eval_rag.py            # LLM off (deterministic), 6 queries
    python scripts/eval_rag.py --live     # also enable live official-web fetch
    python scripts/eval_rag.py --provider mock --max 3
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main() -> int:
    ap = argparse.ArgumentParser(description="RAG groundedness evaluation")
    ap.add_argument("--provider", default="off", choices=["off", "mock", "auto"],
                    help="LLM provider for draft finalisation (default off)")
    ap.add_argument("--live", action="store_true", help="enable live official-web retrieval")
    ap.add_argument("--max", type=int, default=6, help="max queries to run")
    args = ap.parse_args()

    os.environ["IPSAKTI_LLM_PROVIDER"] = args.provider
    if not args.live:
        os.environ["IPSAKTI_LIVE_WEB"] = "0"

    from app.services.copilot_orchestrator import AICopilotOrchestrator

    queries = [
        "Can I patent a Neem-based hair oil formulation?",
        "Can I patent a Brahmi-based tablet for memory?",
        "How is resin content measured in IS 6375?",
        "एलोवेरा जेल को कैसे पेटेंट करें?",
        "What is the deadline for filing a patent in India?",
        "Does this formulation cure insomnia?",
    ][: args.max]

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "llm_provider": args.provider,
        "live_web": bool(args.live),
        "queries": [],
        "summary": {},
    }
    failures: list[str] = []
    confidences: list[float] = []

    for q in queries:
        t0 = time.time()
        try:
            r = AICopilotOrchestrator.run(q, context=None)
        except Exception as exc:  # noqa: BLE001
            report["queries"].append({
                "question": q, "error": str(exc)[:200],
            })
            failures.append(f"exception: {q}")
            continue
        elapsed = time.time() - t0

        card = r.get("analysis_card") or {}
        guard = (card.get("hallucination_check") or {}).get("risk_level", "unknown")
        badge = card.get("verification_badge", "")
        answer = r.get("answer", "")
        conf = float(r.get("confidence") or 0.0)
        confidences.append(conf)
        sources = r.get("sources") or []
        intent_id = (r.get("intent") or {}).get("id", "?")

        has_evidence = "retrieved official sources" in answer.lower() or "knowledge" in answer.lower()
        pass_q = guard != "critical" and len(answer) > 40
        if not pass_q:
            failures.append(f"{guard}/{len(answer)} chars: {q}")
        if guard == "critical":
            failures.append(f"CRITICAL hallucination risk: {q}")

        report["queries"].append({
            "question": q,
            "intent": intent_id,
            "confidence": conf,
            "badge": badge,
            "answer_len": len(answer),
            "sources": len(sources),
            "evidence_used_in_answer": has_evidence,
            "guard_risk": guard,
            "elapsed_s": round(elapsed, 1),
            "pass": pass_q,
        })
        print(f"[{intent_id:>18}] conf={conf:.2f} guard={guard:<8} "
              f"len={len(answer):>4} sources={len(sources)} badge={badge!r} : {q[:52]}"
              .encode("ascii", "replace").decode("ascii"))

    summary = {
        "total": len(report["queries"]),
        "passed": sum(1 for x in report["queries"] if x.get("pass")),
        "failed": len(failures),
        "failures": failures[:10],
        "avg_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
        "critical_risks": sum(1 for x in report["queries"] if x.get("guard_risk") == "critical"),
    }
    report["summary"] = summary

    out_path = os.path.join(os.path.dirname(__file__), "..", "exports", "rag_groundedness_report.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print("\n=== SUMMARY ===")
    print(f"passed {summary['passed']}/{summary['total']}  "
          f"avg_confidence {summary['avg_confidence']:.2f}  "
          f"critical_risks {summary['critical_risks']}")
    print(f"report -> {out_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())