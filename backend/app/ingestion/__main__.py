"""CLI entry point: ``python -m app.ingestion``"""

import argparse
import json

from app.ingestion import sources as src
from app.ingestion.pipeline import get_ingestion_status, run_ingestion


def main() -> int:
    ap = argparse.ArgumentParser(description="IP-SAKTI corpus ingestion")
    ap.add_argument("--sources", nargs="*", default=None,
                    help="Source ids, or selectors: P0 P1 P2 P3 all daily weekly monthly")
    ap.add_argument("--mode", default="update", choices=["update", "full"],
                    help="update = hash-change aware; full = force re-embed")
    ap.add_argument("--query", default=None,
                    help="Optional search query used to discover pages on public sources")
    ap.add_argument("--limit", type=int, default=None,
                    help="Max chunks captured per URL")
    ap.add_argument("--no-local", action="store_true", help="Skip curated local corpus")
    ap.add_argument("--no-seeds", action="store_true", help="Skip canonical knowledge seeds")
    ap.add_argument("--list", action="store_true", help="List the corpus registry and exit")
    ap.add_argument("--status", action="store_true", help="Show ingestion state and exit")
    args = ap.parse_args()

    if args.list:
        for s in src.list_sources():
            print(f"{s['priority']}  {s['id']:<18} {s['name']}  [{s['schedule']}]  {s['access_mode']}")
        return 0

    if args.status:
        print(json.dumps(get_ingestion_status(), indent=2, ensure_ascii=False))
        return 0

    include_local = not args.no_local
    include_seeds = not args.no_seeds
    summary = run_ingestion(
        source_ids=args.sources,
        mode=args.mode,
        include_local=include_local,
        include_seeds=include_seeds,
        query=args.query,
        limit_per_source=args.limit,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())