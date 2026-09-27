"""Compare the four RAG architectures side by side.

Runs a fixed query set through hybrid / production / graph / agentic and
reports p50 / p95 / mean latency plus source richness for each one. Results
are written to ``evals/rag_benchmarks.json`` (and echoed to the console).

Usage:
    python scripts/benchmark_rag.py            # full run
    python scripts/benchmark_rag.py --quick    # 4 queries, 1 repeat
    python scripts/benchmark_rag.py --types hybrid,graph
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag import get_rag  # noqa: E402
from app.services.rag.config import reset_runtime  # noqa: E402

BENCH_QUERIES = [
    "Can I patent an ashwagandha formulation?",
    "What regulatory approvals do I need to sell a nutraceutical in India?",
    "Does my formulation need FSSAI compliance before export?",
    "Is prior art relevant if the ingredient is classical Ayurveda?",
    "How do I register my product for ABS benefits sharing?",
    "What is the patentability of a turmeric-based pain relief balm?",
    "Which schedule applies to my ayurvedic Aahara product?",
    "Can I use a trademark for my herbal brand in Canada?",
]

TYPES = ["hybrid", "production", "graph", "agentic"]


def _pctl(values, p):
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round((p / 100.0) * (len(ordered) - 1))))
    return ordered[idx]


def run(types, queries, repeats):
    reset_runtime()
    results = {}
    for t in types:
        rag = get_rag(t)
        print(f"\n=== {t.upper()} ===")
        # Warm-up: model / index load is excluded from statistics.
        try:
            rag.search(BENCH_QUERIES[0], top_k=5, user_key="bench")  # cold load
        except Exception as exc:  # noqa: BLE001
            print(f"  warm-up failed: {exc}")
        latencies = []
        source_counts = []
        errors = 0
        refusals = 0
        for _ in range(repeats):
            for q in queries:
                start = time.perf_counter()
                try:
                    r = rag.search(q, top_k=5, user_key=f"bench-{t}")
                    lat = (time.perf_counter() - start) * 1000.0
                    if r.should_refuse or not r.sources:
                        refusals += 1
                    else:
                        latencies.append(lat)
                        source_counts.append(len(r.sources))
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    print(f"  ERROR [{q[:40]}...]: {type(exc).__name__}: {exc}")
        n = len(latencies)
        agg = {
            "architecture": t,
            "samples": repeats * len(queries),
            "answered": n,
            "refusals": refusals,
            "errors": errors,
            "latency_ms": {
                "mean": round(statistics.mean(latencies), 1) if latencies else 0.0,
                "p50": round(_pctl(latencies, 50), 1),
                "p95": round(_pctl(latencies, 95), 1),
            },
            "sources": {
                "avg": round(statistics.mean(source_counts), 2) if source_counts else 0.0,
                "max": max(source_counts) if source_counts else 0,
            },
        }
        results[t] = agg
        print(f"  answered={n}/{agg['samples']} refusals={refusals} errors={errors} "
              f"p50={agg['latency_ms']['p50']}ms p95={agg['latency_ms']['p95']}ms "
              f"mean={agg['latency_ms']['mean']}ms avg_sources={agg['sources']['avg']}")

    out = Path(__file__).resolve().parent.parent / "evals" / "rag_benchmarks.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "queries": queries,
        "repeats": repeats,
        "architectures": results,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nBenchmark written to {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="4 queries, 1 repeat")
    parser.add_argument("--types", default=",".join(TYPES), help="comma-separated RAG types")
    args = parser.parse_args()

    queries = BENCH_QUERIES[:4] if args.quick else BENCH_QUERIES
    types = [t.strip() for t in args.types.split(",") if t.strip() in TYPES]
    repeats = 1 if args.quick else 2
    if not types:
        print("No valid RAG types requested", file=sys.stderr)
        return 1
    run(types, queries, repeats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())