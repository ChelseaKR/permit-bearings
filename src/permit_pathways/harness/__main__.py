"""Run the verification harness from the command line.

    python -m permit_pathways.harness
    python -m permit_pathways.harness --assume-changed "ca-gov-66321"

--assume-changed marks one stable source ID as changed, e.g. to rehearse what
a legislative amendment does to the rule base: every explicitly dependent
rule flips to stale until re-verified.

Exit codes:

* ``0`` — nothing needs a person: no source changed, no rule is stale, and
  the golden set passes.
* ``1`` — review needed: a watched source's content changed, a rule aged
  out of its review window, or a golden case regressed.
* ``2`` — one or more watched sources could not be re-fetched. Nothing is
  known to be wrong with the rule base; the check simply could not confirm
  currency for those sources this run. Kept distinct from ``1`` so a
  blocked or rate-limited runner cannot masquerade as a legislative change.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from ..dates import resolve_today
from .runner import verify_rules

if TYPE_CHECKING:
    from .watch import UnverifiableSource

ROOT = Path(__file__).resolve().parents[3]

EXIT_OK = 0
EXIT_REVIEW_NEEDED = 1
EXIT_UNVERIFIABLE = 2


def main(*, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(prog="permit_pathways.harness")
    parser.add_argument("--rules", type=Path, default=ROOT / "data" / "rules")
    parser.add_argument(
        "--golden", type=Path, default=ROOT / "data" / "golden" / "example.json"
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="Run the report as of this ISO date",
    )
    parser.add_argument(
        "--assume-changed",
        action="append",
        default=[],
        metavar="SOURCE_ID",
        help="Treat this stable source ID as changed",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Re-fetch watched sources; a fetched source whose content hash "
        "moved counts as changed, while a source that could not be fetched "
        "is reported as unverifiable and marks nothing stale",
    )
    parser.add_argument("--sources", type=Path, default=ROOT / "data" / "sources.json")
    args = parser.parse_args()
    as_of = resolve_today(args.as_of or today)

    changed = list(args.assume_changed)
    source_changed = False
    unverifiable: dict[str, UnverifiableSource] = {}
    if args.fetch:
        from .watch import check_sources, load_sources

        watch = check_sources(args.sources, today=as_of)
        labels = {
            source_id: source.label
            for source_id, source in load_sources(args.sources, today=as_of).items()
        }
        print(watch.summary(labels), end="\n\n")
        # Only a *fetched* document whose hash moved is evidence of a change.
        # A source we could not download tells us nothing about its content:
        # its recorded hash and last verification date still stand, so its
        # dependent rules keep the status their own review dates give them.
        # Feeding fetch failures into `changed` here is what turned one
        # blocked host into "every statewide rule is stale".
        changed.extend(watch.changed)
        source_changed = bool(watch.changed)
        unverifiable = dict(watch.unverifiable)

    report = verify_rules(
        args.rules,
        args.golden,
        today=as_of,
        changed_source_ids=changed,
    )
    print(report.summary())

    registry_path = ROOT / "data" / "jurisdictions" / "registry.json"
    if registry_path.exists() and args.rules.is_dir():
        from ..jurisdictions import coverage, load_registry

        cov = coverage(
            load_registry(
                registry_path,
                args.rules,
                ROOT / "data" / "jurisdictions" / "hcd-letters.json",
            )
        )
        print("\n" + cov.summary())
    if args.assume_changed:
        print(f"\n(simulating changed sources: {', '.join(args.assume_changed)})")
        for rule_id in report.stale:
            print(f"  STALE until re-verified: {rule_id}")
    print(
        "\ntrustworthy:",
        "yes" if report.trustworthy else "NO — review queue is not empty",
    )
    if unverifiable:
        print(
            f"\n{len(unverifiable)} watched source(s) could not be re-fetched "
            "this run. Their recorded hashes and last verification dates "
            "stand, and no rule was marked stale on that account. If a source "
            "stays unreachable, its dependent rules still age out of the "
            "review window on their own dates."
        )
    # Exit nonzero only on NEW problems (changed sources, stale rules, or
    # golden regressions). Known-unverified rules are a standing backlog, not
    # a fresh alarm — a scheduled currency check should page on change, not on
    # every run. Unverifiable sources get their own code so that "we could not
    # check" is never escalated as "the law changed".
    if source_changed or report.stale or report.golden_failed:
        return EXIT_REVIEW_NEEDED
    if unverifiable:
        return EXIT_UNVERIFIABLE
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
