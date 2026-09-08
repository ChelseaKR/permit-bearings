"""Re-read the seven scanned ordinances and say whether the published results still hold.

Every published conformance result carries the date its ordinance text was
retrieved and says, in its own disclaimer, that no watch monitors that text for
later amendment. This is that watch. It proposes; it never adopts.

Usage:
    python3 scripts/watch_ordinances.py            # fetch and report
    python3 scripts/watch_ordinances.py --from-dir DIR   # read bytes off disk

Exit codes follow `pull_hau_letters.py` and the source-currency watcher, for the
same reason: 0 every source was read and flags what its published result says it
flags, 3 a source was read and no longer does, 2 a source could not be read at
all. A failed read is evidence about the network or about a publisher's URL, and
is never reported as a change to the law.

`--from-dir` expects `<slug>.html` / `<slug>.pdf` and does no network I/O, so a
proposal can be reviewed, re-run and argued about without re-downloading a
moving target -- and so the whole path is exercised by the test suite.

Adoption is deliberate and belongs to a person: re-retrieve the text into
`corpus/ordinances/<slug>.txt`, re-record `watch.text_sha256`, re-run
`scripts/scan_ordinances.py <date>`, and say in the changelog what moved. A
watch that rewrote published findings about a named city on a cron would be the
opposite of what this repository is for.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from permit_pathways import ordinance_watch  # noqa: E402
from permit_pathways.conformance import load_checks  # noqa: E402

CORPUS = ROOT / "corpus/ordinances"
RESULTS = ROOT / "data/conformance/results"
CHECKS = ROOT / "data/conformance/checks.json"
USER_AGENT = "permit-bearings-ordinance-watch/0.1"
FETCH_TIMEOUT_SECONDS = 60
FETCH_ATTEMPTS = 3
FETCH_BACKOFF_SECONDS = 2.0
# The server answered about this exact address and said nothing is there.
# A 403 is a refusal to say, a 5xx is the server failing, a 429 is throttling:
# those are transport outcomes and retrying them is worth the wait.
NOT_FOUND_HTTP_STATUSES = frozenset({404, 410})


def _fetch_once(url: str) -> bytes:
    request = urllib.request.Request(  # noqa: S310  # nosec B310
        url, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(  # noqa: S310  # nosec B310
        request, timeout=FETCH_TIMEOUT_SECONDS
    ) as resp:
        status = getattr(resp, "status", None)
        if status is not None and not 200 <= int(status) < 300:
            raise urllib.error.HTTPError(
                url, int(status), "non-2xx", resp.headers, None
            )
        payload: bytes = resp.read()
        return payload


def fetch(
    url: str,
    *,
    attempts: int = FETCH_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[bytes | None, tuple[ordinance_watch.UnverifiableKind, str] | None]:
    """Download one ordinance page, or say which kind of nothing came back.

    Returns ``(payload, None)`` or ``(None, (kind, detail))``. It never raises
    and never returns a partial read as content: one dead publisher must not end
    a run over seven jurisdictions, and no fetch outcome maps to "changed".
    """
    kind: ordinance_watch.UnverifiableKind = "transport"
    detail = "no attempt was made"
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return _fetch_once(url), None
        except urllib.error.HTTPError as error:
            code = int(error.code)
            kind = "not_found" if code in NOT_FOUND_HTTP_STATUSES else "transport"
            detail = f"HTTP {code}"
        except Exception as error:
            # Deliberately broad: one dead publisher must not end a run over
            # seven jurisdictions, and no fetch outcome ever maps to "changed".
            text = str(error).strip()
            kind = "transport"
            detail = f"{type(error).__name__}: {text}" if text else type(error).__name__
        if kind == "not_found":
            # The server already answered about this address. Asking twice more
            # cannot change the answer and makes a dead citation look flaky.
            break
        if attempt < max(1, attempts):
            sleep(FETCH_BACKOFF_SECONDS * (2 ** (attempt - 1)))
    return None, (kind, detail)


def _published(slug: str, results_dir: Path) -> dict[str, int]:
    path = results_dir / f"{slug}.json"
    if not path.is_file():
        raise SystemExit(f"{slug}: no published result at {path}")
    return ordinance_watch.published_finding_counts(
        json.loads(path.read_text(encoding="utf-8"))
    )


def run(
    *, from_dir: Path | None, results_dir: Path = RESULTS, corpus_dir: Path = CORPUS
) -> tuple[int, list[ordinance_watch.SourceWatch]]:
    """Watch every declared source and return an exit code with the reports."""
    sources = ordinance_watch.load_sources(corpus_dir / "SOURCES.json")
    checks = load_checks(CHECKS)
    reports: list[ordinance_watch.SourceWatch] = []
    for slug, source in sorted(sources.items()):
        if from_dir is None:
            payload, failure = fetch(source.url)
        else:
            path = from_dir / f"{slug}{source.suffix}"
            if path.is_file():
                payload, failure = path.read_bytes(), None
            else:
                payload, failure = None, ("transport", f"no bytes at {path}")
        reports.append(
            ordinance_watch.watch_source(
                source,
                payload,
                failure=failure,
                published=_published(slug, results_dir),
                checks=checks,
            )
        )
    changed = [r for r in reports if r.status == "changed"]
    unverifiable = [r for r in reports if r.status == "unverifiable"]
    # A source that changed outranks one that could not be read: the first is a
    # published claim that no longer holds, the second is a fact about a server.
    # Reporting the weaker code when both fired would hide the stronger.
    code = 3 if changed else (2 if unverifiable else 0)
    return code, reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Re-read the scanned ordinances and diff their findings "
        "against the published results. Proposes; never adopts."
    )
    parser.add_argument(
        "--from-dir",
        type=Path,
        default=None,
        help="read <slug>.html/<slug>.pdf from this directory instead of "
        "fetching, so a proposal can be reviewed without a second download",
    )
    args = parser.parse_args(argv)

    code, reports = run(from_dir=args.from_dir)
    for report in reports:
        print(report.describe())
    unchanged = sum(1 for r in reports if r.status == "unchanged")
    changed = sum(1 for r in reports if r.status == "changed")
    unverifiable = sum(1 for r in reports if r.status == "unverifiable")
    print(
        f"ordinance watch: unchanged={unchanged} changed={changed} "
        f"unverifiable={unverifiable}"
    )
    if changed:
        print(
            "A changed source is a proposal, not an adoption. Re-retrieve the "
            "text, re-record watch.text_sha256, re-run "
            "scripts/scan_ordinances.py <date>, and say what moved."
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
