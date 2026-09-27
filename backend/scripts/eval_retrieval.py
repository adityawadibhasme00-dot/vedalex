"""
Run retrieval-quality benchmarks (Recall@5/10, Precision@5/10, MRR, citation accuracy).

Usage (from backend/):
    python scripts/eval_retrieval.py                # all benchmark questions
    python scripts/eval_retrieval.py --max 3
    IPSAKTI_LLM_PROVIDER=off python scripts/eval_retrieval.py
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.evals.retrieval_metrics import REPORT_PATH, run_evaluation


def main() -> int:
    ap = argparse.ArgumentParser(description="Retrieval-quality benchmark")
    ap.add_argument("--max", type=int, default=None, help="max benchmark questions to run")
    args = ap.parse_args()
    report = run_evaluation(limit=args.max)
    agg = report["aggregate"]
    print(json.dumps(agg, indent=2, ensure_ascii=False))
    print(f"\nReport -> {REPORT_PATH}")
    return 0 if agg.get("gates_pass") else 2


if __name__ == "__main__":
    sys.exit(main())