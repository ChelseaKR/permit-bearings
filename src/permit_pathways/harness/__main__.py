"""Run the verification harness from the command line.

    python -m permit_pathways.harness
    python -m permit_pathways.harness --assume-changed "ca-gov-66321"

--assume-changed marks one stable source ID as changed, e.g. to rehearse what
a legislative amendment does to the rule base: every explicitly dependent
rule flips to stale until re-verified.

Exit codes:

* ``0`` — the bounded automated source-age and structured-regression checks
  pass. This is not a human-review or legal-accuracy result.
* ``1`` — review needed: a watched source's content changed, a rule aged
  out of its review window, or a golden case regressed.
* ``2`` — one or more watched sources could not be re-fetched. Nothing is
  known to be wrong with the rule base; the check simply could not confirm
  currency for those sources this run. Kept distinct from ``1`` so a
  blocked or rate-limited runner cannot masquerade as a legislative change.

An unverifiable source is reported by kind. A ``transport`` failure got no
answer and is a fact about this run. A ``not_found`` failure means the
server answered that no document is published at that address, so a rule
citing it prints a link that resolves to nothing. Neither stales a rule and
neither changes the exit code: a withdrawn link is a publication fact the
maintainer may not be able to fix in the same run, so it is reported
loudly rather than used to break the build.

The machine-readable ``currency signals:`` line reports ``changed_sources``
and ``unverifiable_sources`` as ``not_checked`` unless ``--fetch`` was given.
Both are answers only a download can produce, and a run that downloaded
nothing has not earned the number ``0`` for either.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from ..dates import resolve_today
from .availability import WATCH_WORKFLOW_PATH, availability_note, watch_availability
from .availability import signal_values as availability_signal_values
from .runner import verify_rules

if TYPE_CHECKING:
    from .runner import VerificationReport
    from .watch import UnverifiableSource, WatchResult

ROOT = Path(__file__).resolve().parents[3]

EXIT_OK = 0
EXIT_REVIEW_NEEDED = 1
EXIT_UNVERIFIABLE = 2

# Printed in the signal line for the two counts only a fetch can answer, on a
# run that did no fetching. `0` there would be indistinguishable from the
# clean result of a watch that actually ran.
NOT_CHECKED = "not_checked"


def _validate_snapshot_args(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    metadata = (
        args.snapshot_id,
        args.checked_at,
        args.receipt_method,
        args.run_url,
        args.commit_sha,
    )
    if args.snapshot_out is not None and (not args.fetch or not all(metadata)):
        parser.error(
            "--snapshot-out requires --fetch, --snapshot-id, --checked-at, "
            "--receipt-method, --run-url, and --commit-sha"
        )
    if args.snapshot_out is None and any(metadata):
        parser.error("snapshot metadata requires --snapshot-out")


def _write_snapshot(args: argparse.Namespace, watch: object) -> None:
    from ..source_state import build_source_state_snapshot, encoded_source_state
    from .watch import WatchResult

    if not isinstance(watch, WatchResult):
        raise AssertionError("snapshot output requires a completed source watch")
    snapshot = build_source_state_snapshot(
        watch,
        args.sources,
        args.rules,
        args.golden,
        snapshot_id=args.snapshot_id,
        checked_at=args.checked_at,
        receipt_status=args.receipt_status,
        method=args.receipt_method,
        run_url=args.run_url,
        commit_sha=args.commit_sha,
    )
    args.snapshot_out.parent.mkdir(parents=True, exist_ok=True)
    args.snapshot_out.write_text(encoded_source_state(snapshot), encoding="utf-8")
    print(f"\nwrote source-state snapshot: {args.snapshot_out}")


DEFAULT_RULES = ROOT / "data" / "rules"
DEFAULT_SOURCES = ROOT / "data" / "sources.json"
ADOPTED_SOURCE_STATE = ROOT / "data" / "source-status" / "current.json"


def _unverifiable_note(unverifiable: dict[str, UnverifiableSource]) -> str:
    """Report the two unverifiable kinds separately.

    Collapsing them is how a local certificate-store failure and a city
    handout that has been taken down read as the same line.
    """

    not_found = sorted(
        source_id for source_id, failure in unverifiable.items() if failure.is_not_found
    )
    unreachable = len(unverifiable) - len(not_found)
    lines = []
    if unreachable:
        lines.append(
            f"\n{unreachable} watched source(s) could not be re-fetched "
            "this run. Their recorded hashes and last verification dates "
            "stand, and no rule was marked stale on that account. If a source "
            "stays unreachable, its dependent rules still age out of the "
            "review window on their own dates."
        )
    if not_found:
        lines.append(
            f"\n{len(not_found)} watched source address(es) answered "
            '"not found": '
            + ", ".join(not_found)
            + ". The server replied, so this is not a network problem: the "
            "document is no longer published at the address this project "
            "prints. Recorded hashes and retained copies still stand and no "
            "rule was marked stale, but any citation pointing there resolves "
            "to nothing for a reader."
        )
    return "\n".join(lines)


def _adopted_withdrawn_citation_report(args: argparse.Namespace) -> str | None:
    """Report citations the adopted receipt already records as not found.

    Only for a run over the committed corpus. Pointing --rules or --sources
    at a fixture makes the committed receipt meaningless, and skipping
    there is honest; skipping on the real corpus would be a check that
    cannot fail.
    """

    if (
        args.rules != DEFAULT_RULES
        or args.sources != DEFAULT_SOURCES
        or not ADOPTED_SOURCE_STATE.exists()
    ):
        return None
    from ..source_state import load_source_state_snapshot, withdrawn_citations

    snapshot = load_source_state_snapshot(
        ADOPTED_SOURCE_STATE,
        args.sources,
        args.rules,
        args.golden,
    )
    findings = withdrawn_citations(snapshot, args.sources, args.rules)
    if not findings:
        return (
            "published citation links: the adopted receipt "
            f"({snapshot.snapshot_id}) records no cited source whose published "
            'address answered "not found".'
        )
    lines = [
        f"published citation links: {len(findings)} cited source address(es) "
        'answered "not found" in the adopted receipt. The excerpts and '
        "retained copies still stand and no rule was marked stale; the links "
        "printed beside those rules do not resolve."
    ]
    lines.extend(f"  LINK NOT FOUND: {item.describe()}" for item in findings)
    return "\n".join(lines)


def _print_excerpt_survival(watch: WatchResult) -> None:
    """Per changed source, whether each dependent rule's quoted text survived.

    Printed under the watch summary and above the rule report, because it is
    the first question a maintainer asks after "which sources moved". It
    reorders that work; it never removes any of it — every dependent rule is
    stale either way until a person re-verifies it.
    """

    if not watch.excerpt_survival:
        return
    from ..excerpt_survival import summarize

    print(
        "\nquoted text after the change (stales nothing on its own):\n"
        + "\n".join(
            summarize(source_id, watch.excerpt_survival[source_id])
            for source_id in sorted(watch.excerpt_survival)
        )
    )


def _print_adopted_withdrawn_citations(args: argparse.Namespace) -> None:
    report = _adopted_withdrawn_citation_report(args)
    if report is not None:
        print("\n" + report)


def _print_currency_signals(
    report: VerificationReport,
    *,
    watch: WatchResult | None,
    unverifiable: dict[str, UnverifiableSource],
    as_of: date,
) -> None:
    """One machine-readable line, printed on every run including a clean one.

    Exit 1 covers three conditions with different owners and different urgency,
    and the scheduled workflow could previously only say that one of them
    happened. A signal that appeared only on failure could not be used to detect
    recovery either, so it is unconditional. See issue #70.

    ``changed_sources`` and ``unverifiable_sources`` are answers only a fetch can
    give. Without ``--fetch`` nothing was downloaded, so printing ``0`` for them
    would publish "we checked and found none" for a check that never ran --
    byte-identical to what a genuinely clean watch prints, and, since the
    committed receipt can itself record a withdrawn address, flatly contradicted
    by the report printed above it. They say ``not_checked`` instead.
    ``stale_rules`` and ``golden_regressions`` come from the committed rule and
    Golden records and are measured on every run, fetch or not.

    ``data/availability/`` holds the one cadence in this repository shorter than
    ``SOURCE_REVIEW_WINDOW_DAYS``, and until issue #164 nothing in this harness
    read it: the run 33 hours before its first expiry exited 0 in 21 seconds.
    Two numbers, always both -- a count of readings about to lapse says nothing
    without the count of readings this run could examine, and a directory that
    could not be read prints ``not_checked`` rather than ``0`` for both.
    """

    changed_signal = str(len(watch.changed)) if watch is not None else NOT_CHECKED
    unverifiable_signal = str(len(unverifiable)) if watch is not None else NOT_CHECKED
    availability = watch_availability(
        ROOT / "data" / "availability",
        today=as_of,
        workflow_path=ROOT / WATCH_WORKFLOW_PATH,
    )
    availability_due, availability_records = availability_signal_values(
        availability, not_checked=NOT_CHECKED
    )
    print(
        "\ncurrency signals:"
        f" changed_sources={changed_signal}"
        f" stale_rules={len(report.stale)}"
        f" golden_regressions={len(report.golden_failed)}"
        f" unverifiable_sources={unverifiable_signal}"
        f" program_availability_due={availability_due}"
        f" program_availability_records={availability_records}"
    )
    availability_lines = availability_note(availability, today=as_of, root=ROOT)
    if availability_lines:
        print(availability_lines)


def main(argv: list[str] | None = None, *, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(prog="permit_pathways.harness")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
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
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument(
        "--snapshot-out",
        type=Path,
        default=None,
        help="Write a machine-readable proposed or reviewed source-state receipt",
    )
    parser.add_argument("--snapshot-id", default=None)
    parser.add_argument("--checked-at", default=None)
    parser.add_argument(
        "--receipt-status",
        choices=("proposed", "reviewed"),
        default="proposed",
    )
    parser.add_argument("--receipt-method", default=None)
    parser.add_argument("--run-url", default=None)
    parser.add_argument("--commit-sha", default=None)
    args = parser.parse_args(argv)
    _validate_snapshot_args(parser, args)
    as_of = resolve_today(args.as_of or today)

    changed = list(args.assume_changed)
    source_changed = False
    unverifiable: dict[str, UnverifiableSource] = {}
    watch = None
    if args.fetch:
        from ..screening import load_rules
        from .watch import check_sources, load_sources

        # The rules are handed to the watch so a source whose bytes moved can
        # be asked, in the same read, whether the text each dependent rule
        # quotes is still in it. It stales nothing extra: excerpt survival
        # orders the re-verification worklist, it does not shorten it.
        watch = check_sources(
            args.sources,
            today=as_of,
            rules=load_rules(args.rules, today=as_of),
        )
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
        _print_excerpt_survival(watch)

    report = verify_rules(
        args.rules,
        args.golden,
        today=as_of,
        changed_source_ids=changed,
    )
    print(report.summary())

    if args.snapshot_out is not None:
        _write_snapshot(args, watch)

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

    verification_path = ROOT / "data" / "validation" / "rule-verification.json"
    if verification_path.exists() and args.rules.is_dir():
        from ..rule_verification import level_coverage, load_rule_verifications
        from ..screening import load_rules

        verification_rules = load_rules(args.rules, today=as_of)
        # Display tooling loads tolerantly: --rules may point at a fixture
        # the committed ledger was never meant to cover (e.g. in tests), and
        # a rule with no valid entry simply reports as machine_linked, same
        # as effective_status's own default.
        ledger = load_rule_verifications(
            verification_path,
            verification_rules,
            require_complete=False,
            strict=False,
            today=as_of,
        )
        print(
            "\n"
            + level_coverage(
                verification_rules,
                ledger,
                today=as_of,
                changed_source_ids=changed,
            ).summary()
        )
    _print_adopted_withdrawn_citations(args)

    if args.assume_changed:
        print(f"\n(simulating changed sources: {', '.join(args.assume_changed)})")
        for rule_id in report.stale:
            print(f"  STALE until re-verified: {rule_id}")
    print(
        "\nautomated source/regression checks:",
        "pass"
        if report.automated_checks_pass
        else "REVIEW NEEDED — the automated queue is not empty",
    )
    _print_currency_signals(
        report,
        watch=watch,
        unverifiable=unverifiable,
        as_of=as_of,
    )
    if unverifiable:
        print(_unverifiable_note(unverifiable))
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
