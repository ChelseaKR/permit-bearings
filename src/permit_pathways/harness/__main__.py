"""Run the verification harness from the command line.

    python -m permit_pathways.harness
    python -m permit_pathways.harness --assume-changed "66321"

--assume-changed marks a source (matched by substring against each rule's
citation source/URL) as changed, e.g. to rehearse what a legislative
amendment does to the rule base: affected rules flip to stale until
re-verified.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from .runner import verify_rules

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(prog="permit_pathways.harness")
    parser.add_argument("--rules", type=Path,
                        default=ROOT / "data" / "rules")
    parser.add_argument("--golden", type=Path,
                        default=ROOT / "data" / "golden" / "example.json")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None,
                        help="Run the report as of this ISO date")
    parser.add_argument("--assume-changed", action="append", default=[],
                        metavar="SOURCE_SUBSTRING",
                        help="Treat sources matching this substring as changed")
    parser.add_argument("--fetch", action="store_true",
                        help="Re-fetch watched sources and treat any whose "
                             "content hash changed as changed")
    parser.add_argument("--sources", type=Path,
                        default=ROOT / "data" / "sources.json")
    args = parser.parse_args()

    changed = list(args.assume_changed)
    if args.fetch:
        from .watch import check_sources, load_sources
        watch = check_sources(args.sources)
        labels = {u: m["label"] for u, m in load_sources(args.sources).items()}
        print(watch.summary(labels), end="\n\n")
        changed.extend(watch.changed)
        # A source we can't reach can't be verified as current either.
        changed.extend(watch.errors)

    report = verify_rules(
        args.rules, args.golden,
        today=args.as_of or date.today(),
        changed_sources=changed,
    )
    print(report.summary())
    if args.assume_changed:
        print(f"\n(simulating changed sources: {', '.join(args.assume_changed)})")
        for rule_id in report.stale:
            print(f"  STALE until re-verified: {rule_id}")
    print("\ntrustworthy:", "yes" if report.trustworthy else "NO — review queue is not empty")
    return 0 if report.trustworthy else 1


if __name__ == "__main__":
    sys.exit(main())
