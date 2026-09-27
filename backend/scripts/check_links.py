"""A5 — nightly dead-link checker CLI.

    python scripts/check_links.py            # offline report (skipped)
    python scripts/check_links.py --live     # real HTTP checks
    python scripts/check_links.py --live --fail-on-dead   # exit 1 if dead

Designed for cron: quiet output, deterministic exit codes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.link_checker import check_corpus_links  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IP-SAKTI dead-link checker")
    parser.add_argument("--live", action="store_true", help="perform real HTTP checks")
    parser.add_argument("--json", type=Path, help="write full report to path")
    parser.add_argument(
        "--fail-on-dead", action="store_true", help="exit 1 when dead links found"
    )
    args = parser.parse_args(argv)

    fetcher = None
    if args.live:
        from app.ingestion.fetchers import fetch_html

        fetcher = lambda url: fetch_html(url) is not None  # noqa: E731

    report = check_corpus_links(fetcher=fetcher)
    print(
        f"links: {report['urls_checked']} checked | ok={report['ok']} "
        f"dead={report['dead']} skipped={report['skipped']} "
        f"(live={report['live']})"
    )
    for item in report["results"]:
        if item["status"] == "dead":
            print(f"  DEAD {item['source_id']}: {item['url']} ({item['detail']})")

    if args.json:
        args.json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.fail_on_dead and report["dead"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
