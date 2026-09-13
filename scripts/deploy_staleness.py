#!/usr/bin/env python3
"""Is the site a visitor gets at chelseakr.github.io/permit-bearings the site
this repository has?

Nothing in this repository was asking. `ci.yml`, `codeql.yml`, `currency.yml`,
`scorecard.yml`, `security.yml`, `standards.yml` and
`accessibility-performance.yml` all describe the *source*. The live pages are
published by GitHub itself, outside every one of them, and a liveness check that
confirms the site serves the dataset it names answers correctly every day of a
three-week freeze. Elsewhere in this portfolio a site served a two-month-old
build for 63 days with every gate green; the gates were not lying, they were
not asked.

This module deploys nothing, holds no credential that could, and answers one
question: how far behind `main` are the bytes a visitor receives.

The publishing model: a committed tree GitHub builds
----------------------------------------------------
`GET /repos/ChelseaKR/permit-bearings/pages` reports, as of 2026-09-13::

    "build_type": "legacy", "source": {"branch": "main", "path": "/"}

No workflow in `.github/workflows/` publishes this site. GitHub's own legacy
Jekyll build runs on a push to `main`, serving the repository *root*, and files
a `github-pages` deployment naming the commit it built. That is the model
assumed throughout this file, and it is why the deployment record -- not a run
list -- is the source of truth: there is no publisher run to list.

What that build actually serves, and how that was verified
----------------------------------------------------------
There is no `_config.yml`, no `_config.yaml` and no `.nojekyll` anywhere in the
tree (`git ls-tree -r origin/main` finds none), so the build runs on Jekyll's
defaults: every tracked file under the root is copied to the site verbatim
*except* entries whose name begins with `.` or `_`.

Assumed, then checked against the live site on 2026-09-13 rather than taken on
faith -- `curl -o /dev/null -w '%{http_code}' -L`::

    /                                  200      /.github/workflows/ci.yml     404
    /index.html                        200      /src/permit_pathways/__init__.py 404
    /assets/site.css                   200      /src/permit_pathways/ai/budget.py 200
    /data/conformance/checks.json      200      /evals/                       404
    /corpus/leginfo/gov-66314.html     200      /assets/                      404
    /README.md                         200      /pyproject.toml               200
    /Makefile                          200      /uv.lock                      200
    /conftest.py                       200      /tests/accessibility.spec.js  200
    /scripts/readability_gate.py       200      /demo/app.py                  200

The two 404s that are not directory listings confirm the rule exactly:
`.github/` is skipped because the directory name starts with a dot, and
`src/permit_pathways/__init__.py` because the *file* name starts with an
underscore, while `src/permit_pathways/ai/budget.py` beside it is served.

Why the literal published-subtree comparison is not the honest measure here
---------------------------------------------------------------------------
For a committed-tree publisher the right comparison is normally the published
subtree: `git rev-parse <deployed>:<path>` against `git rev-parse <head>:<path>`,
because equal tree ids mean the visitor has exactly the bytes `main` has however
far apart the two commits are. That is the correct instrument, and the probe
above is what makes it inapplicable *as written* to this repository: the
published path is `/`, so the published subtree is the whole root, and the whole
root's tree id changes on every commit that changes any tracked file. A commit
that only edits `tests/test_transit.py` moves it. Comparing the published root
would therefore be deployed-SHA-versus-head wearing a tree id, and it would
report drift on a test-only commit -- the cry-wolf failure the subtree rule
exists to avoid.

So the instrument is kept and its subject is narrowed. Jekyll mirroring
`tests/` and `pyproject.toml` into the site is an artefact of the default
build, not a surface anyone reaches: no page links them, no script fetches them,
and no visitor arrives at `/uv.lock`. `VISITOR_SURFACE` below is the set of
paths a visitor actually receives, and the comparison is a per-path object-id
comparison across exactly that set. Equal object ids across all of it means the
visitor has, byte for byte, what `main` has -- and, unlike counting commits, a
change that was reverted or regenerated identically correctly reports as no
drift.

The alternative -- deployed SHA versus head with an exclusion list -- was
rejected because the list would have to enumerate everything the repository
might ever add that is not the site, an open set that silently fails toward
false alarms. An inclusion list fails toward silence, which is the direction
this module has to guard against, so the companion test
`test_every_local_reference_the_shipped_pages_make_is_inside_the_surface`
re-derives the references out of the committed HTML and JavaScript and fails
when one escapes the declared surface. The list is checked against the pages,
not asserted about them.

The failure mode GitHub-built Pages adds
-----------------------------------------
Because GitHub does the build, a push can land on `main` and the *build* can
fail. `main` moves, the deployed commit does not, and no workflow anywhere goes
red -- the Pages build is not one. A deployment row is a request to publish; its
statuses say whether bytes landed. So a deployment whose newest status is not
`success` is never treated as the live commit, and any such deployment newer
than the live one is named in the report: that is a site whose republish is
actively broken, which reads from the outside exactly like a site nobody pushed
to.

A detector that cannot tell must refuse rather than report a comfortable zero.
Every unmeasurable case below raises `StalenessUnknown` and exits non-zero: no
deployment, none that succeeded, a deployed commit this clone does not contain,
a history that has diverged, or a declared visitor path that `main` no longer
has -- the last one meaning this file's own surface list has gone stale and is
measuring something the site no longer serves.

Standard library only, and it imports nothing from the rest of this repository,
so the sentinel runs on a bare interpreter with no dependency resolution and
cannot be broken by one.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_REPO = "ChelseaKR/permit-bearings"

#: The environment a deployment has to belong to. `build_type: legacy` files
#: these under the same name a workflow-built Pages site uses.
PAGES_ENVIRONMENT = "github-pages"

#: How long a visitor-visible change may sit unpublished before this reports.
#: GitHub rebuilds on every push to `main`, so ordinary drift here is hours, not
#: days; fourteen is the threshold for the abnormal case this exists to catch --
#: a broken build, a disabled Pages source, a branch that stopped being served.
DEFAULT_MAX_AGE_DAYS = 14

#: The paths a visitor actually receives. Not "what Jekyll copies": the default
#: build mirrors nearly the whole repository (see the module docstring), and
#: `tests/`, `scripts/`, `src/`, `schemas/`, `docs/`, `evals/`, `deploy/`,
#: `demo/` and the root metadata files are reachable only by typing their
#: source path into the address bar. Nothing on the site routes anyone to them.
#:
#: What is here, and why each one:
#:
#: * the five HTML pages -- every rendered page the site has. `prepare.html` is
#:   on the list although no other page links to it: it is published, it is
#:   reachable, and leaving it off would make a change to it invisible.
#: * `assets/` -- the stylesheets, `demo.js`, `ai.js`, the fonts and the
#:   illustrations every page loads.
#: * `data/` -- the datasets the pages fetch at runtime, including
#:   `data/demo-data.js`, which `scripts/build_demo_bundle.py` generates from
#:   the canonical JSON beside it and `make bundle-check` holds in sync. A
#:   change to any input dataset reaches the visitor through that bundle.
#: * `corpus/` -- the retained source copies. `evidence.html` names them by
#:   path and SHA-256 as the proof behind every citation, and GitHub serves
#:   them at exactly those paths (`/corpus/leginfo/gov-66314.html` -> 200), so a
#:   visitor who follows a named path has to receive the bytes the published
#:   evidence attests to.
VISITOR_SURFACE = (
    "index.html",
    "check.html",
    "evidence.html",
    "prepare.html",
    "review.html",
    "assets",
    "corpus",
    "data",
)

_SHA = re.compile(r"^[0-9a-f]{40}$")


class StalenessUnknown(Exception):
    """The comparison could not be made, so no number is reported.

    Raised in preference to returning zero anywhere the inputs do not support a
    measurement. The caller turns this into a red run: a sentinel that cannot
    tell is a broken sentinel and has to look broken.
    """


@dataclass(frozen=True)
class DeployRecord:
    """A published build: which commit it came from, and when it went out."""

    deployment_id: int
    sha: str
    created_at: datetime


@dataclass(frozen=True)
class UnpublishedAttempt:
    """A deployment newer than the live one that never reported success.

    GitHub builds this site, so this is the shape of "the push landed and the
    build broke": `main` moved, the served commit did not, and nothing in
    `.github/workflows/` is red because none of them publishes anything.
    """

    sha: str
    created_at: datetime
    state: str


@dataclass(frozen=True)
class LiveBuild:
    """The commit a visitor is being served, and what failed after it."""

    record: DeployRecord
    unpublished: tuple[UnpublishedAttempt, ...]


@dataclass(frozen=True)
class Drift:
    """How far the bytes a visitor receives are behind `main`."""

    live: LiveBuild
    head: str
    days: int
    commits: int
    visitor_commits: int
    changed_paths: tuple[str, ...]
    max_age_days: int

    @property
    def deployed(self) -> DeployRecord:
        return self.live.record

    @property
    def overdue(self) -> bool:
        """Report only when the visitor's bytes differ *and* have waited.

        Age alone is never the verdict. A site nobody republished because
        nothing it publishes changed is correct, not stale, and a sentinel that
        fires on that is one nobody reads. The first clause is the object-id
        comparison, not a commit count: a change made and reverted since the
        deploy leaves the visitor with exactly `main`'s bytes and is not drift.
        """
        return bool(self.changed_paths) and self.days > self.max_age_days


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def resolve_live_build(
    deployments: Iterable[Mapping[str, Any]],
    statuses_for: Callable[[Any], Sequence[Mapping[str, Any]]],
) -> LiveBuild:
    """The newest `github-pages` deployment that actually published.

    `statuses_for` is called with a deployment id and returns that deployment's
    statuses, newest first. A deployment row is a *request* to publish; its
    statuses are what say whether bytes landed. A deployment whose newest status
    is `failure`, `error`, `queued` or `in_progress` never became a site, and
    treating its commit as the live one would report the site as fresher than it
    is -- the precise direction of error this whole file exists to prevent.

    Everything newer than the winner that did not succeed is carried along, not
    discarded. On a GitHub-built site those rows are the difference between "the
    owner published nothing" and "the build is broken", and the report has to be
    able to say which.
    """
    candidates = [
        d
        for d in deployments
        if d.get("environment") in (None, PAGES_ENVIRONMENT)
        and _SHA.match(str(d.get("sha", "")))
    ]
    if not candidates:
        raise StalenessUnknown(
            "no github-pages deployment in this repository's history: there is no "
            "published build to compare main against"
        )
    candidates.sort(key=lambda d: _parse_timestamp(str(d["created_at"])), reverse=True)

    failed: list[UnpublishedAttempt] = []
    for deployment in candidates:
        states = [str(s.get("state", "")) for s in statuses_for(deployment["id"])]
        if states and states[0] == "success":
            return LiveBuild(
                record=DeployRecord(
                    deployment_id=int(deployment["id"]),
                    sha=str(deployment["sha"]),
                    created_at=_parse_timestamp(str(deployment["created_at"])),
                ),
                unpublished=tuple(failed),
            )
        failed.append(
            UnpublishedAttempt(
                sha=str(deployment["sha"]),
                created_at=_parse_timestamp(str(deployment["created_at"])),
                state=states[0] if states else "no status",
            )
        )

    raise StalenessUnknown(
        f"none of the {len(candidates)} github-pages deployment(s) reports a "
        "successful status: nothing here proves any build was ever published"
    )


def ships_to_visitors(path: str) -> bool:
    """Does changing this file change what a visitor of the site receives?

    A path is inside the surface when it *is* a declared entry or lies under
    one. `index.html` matches itself; `assets/site.css` matches `assets`;
    `tests/accessibility.spec.js` matches nothing, although GitHub does serve
    it.
    """
    return any(
        path == entry or path.startswith(f"{entry}/") for entry in VISITOR_SURFACE
    )


def _git_executable() -> str:
    git = shutil.which("git")
    if git is None:
        raise StalenessUnknown(
            "git is not on PATH: the comparison walks this clone's history and "
            "cannot be made without it"
        )
    return git


def _run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # nosec B603
        [_git_executable(), "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _git(*args: str) -> str:
    result = _run_git(*args)
    if result.returncode != 0:
        raise StalenessUnknown(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _has_commit(sha: str) -> bool:
    """Whether this clone contains the commit, without raising on absence.

    `git cat-file` exits non-zero for a commit that is simply not here, which is
    the ordinary shallow-clone case and not a git failure. Routing it through
    `_git` would report it as one, and the refusal the caller raises -- the one
    that names the shallow checkout and says why a zero would be wrong -- would
    never be reached.
    """
    return _run_git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def object_id(commit: str, path: str) -> str | None:
    """The git object id of `path` at `commit`, or `None` if it is not there.

    A tree id for a directory, a blob id for a file. Equal ids mean identical
    bytes: this is what lets the comparison say the visitor has exactly what
    `main` has without re-reading a single file.
    """
    result = _run_git("rev-parse", "--verify", "--quiet", f"{commit}:{path}")
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def require_comparable(deployed_sha: str, head: str) -> None:
    """Refuse unless this clone can actually place the deployed commit on `main`.

    Both failures below report zero drift if they are not caught, and both are
    ordinary. A shallow checkout does not contain a commit from a month ago, so
    `git log <deployed>..HEAD` lists nothing and the site reads as up to date --
    which is why the sentinel workflow checks out with `fetch-depth: 0` and why
    this refuses rather than trusting that it did. A force-push or a rebase
    leaves the deployed commit off `main` entirely, where "commits since" is not
    a question with an answer.
    """
    if not _SHA.match(deployed_sha):
        raise StalenessUnknown(f"deployed commit {deployed_sha!r} is not a commit id")
    if not _has_commit(deployed_sha):
        raise StalenessUnknown(
            f"deployed commit {deployed_sha[:9]} is not in this clone: the checkout "
            "is shallow, and a comparison against a history that does not reach the "
            "published build would report no drift at all"
        )
    merge_base = _git("merge-base", deployed_sha, head)
    if merge_base != _git("rev-parse", deployed_sha):
        raise StalenessUnknown(
            f"deployed commit {deployed_sha[:9]} is not an ancestor of {head}: the "
            "history has diverged and 'commits since the deploy' has no answer"
        )


def changed_surface(deployed_sha: str, head: str) -> tuple[str, ...]:
    """The declared visitor paths whose bytes differ between the two commits.

    An entry `main` no longer carries is a refusal, not an absence. It means
    `VISITOR_SURFACE` has gone stale -- the page was renamed or the directory
    moved -- and a stale surface list quietly measures a site that no longer
    exists, reporting no drift because it is looking at nothing.
    """
    changed: list[str] = []
    for entry in VISITOR_SURFACE:
        current = object_id(head, entry)
        if current is None:
            raise StalenessUnknown(
                f"{entry!r} is declared visitor-visible but is not in {head}: this "
                "sentinel's surface list no longer describes the published site, so "
                "it is measuring a page that is not there"
            )
        if object_id(deployed_sha, entry) != current:
            changed.append(entry)
    return tuple(changed)


def commits_between(deployed_sha: str, head: str) -> list[tuple[str, list[str]]]:
    """Each commit after the deployed one, with the paths it touched."""
    raw = _git("log", "--format=%x00%H", "--name-only", f"{deployed_sha}..{head}")
    commits: list[tuple[str, list[str]]] = []
    for block in raw.split("\x00"):
        stripped = block.strip("\n")
        if not stripped:
            continue
        lines = [line for line in stripped.splitlines() if line.strip()]
        commits.append((lines[0], lines[1:]))
    return commits


def measure(
    live: LiveBuild,
    head: str,
    now: datetime,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> Drift:
    """Place the published build against `main`, or refuse."""
    head_sha = _git("rev-parse", head)
    require_comparable(live.record.sha, head_sha)
    commits = commits_between(live.record.sha, head_sha)
    visitor = [c for c in commits if any(ships_to_visitors(p) for p in c[1])]
    return Drift(
        live=live,
        head=head_sha,
        days=(now - live.record.created_at).days,
        commits=len(commits),
        visitor_commits=len(visitor),
        changed_paths=changed_surface(live.record.sha, head_sha),
        max_age_days=max_age_days,
    )


def render(drift: Drift) -> str:
    """The report. States the measurement before its verdict, always."""
    lines = [
        f"Published build:  {drift.deployed.sha[:9]}  "
        f"({drift.deployed.created_at.date().isoformat()}, "
        f"deployment {drift.deployed.deployment_id})",
        f"main:             {drift.head[:9]}",
        f"Behind by:        {drift.days} days, {drift.commits} commits, "
        f"{drift.visitor_commits} of them touching the visitor surface",
        "Differing bytes:  "
        + (", ".join(drift.changed_paths) if drift.changed_paths else "none"),
    ]
    for attempt in drift.live.unpublished:
        lines.append(
            f"Build did NOT publish: {attempt.sha[:9]} "
            f"({attempt.created_at.date().isoformat()}, {attempt.state}). "
            "GitHub builds this site; a failed build leaves the older commit "
            "serving with nothing in this repository red."
        )
    if drift.overdue:
        lines.append(
            f"\nOVERDUE: {len(drift.changed_paths)} visitor-visible path(s) have "
            f"differed for {drift.days} days, past the {drift.max_age_days}-day "
            "threshold. The live site is not what this repository says it is."
        )
    elif drift.changed_paths:
        lines.append(
            f"\nWaiting: {len(drift.changed_paths)} visitor-visible path(s) differ, "
            f"{drift.days} days, within the {drift.max_age_days}-day threshold."
        )
    else:
        lines.append(
            "\nUp to date: every visitor-visible path is byte-identical to main."
        )
    return "\n".join(lines)


def as_json(drift: Drift) -> dict[str, Any]:
    return {
        "deployed_sha": drift.deployed.sha,
        "deployed_at": drift.deployed.created_at.isoformat(),
        "deployment_id": drift.deployed.deployment_id,
        "head": drift.head,
        "days": drift.days,
        "commits": drift.commits,
        "visitor_commits": drift.visitor_commits,
        "changed_paths": list(drift.changed_paths),
        "unpublished_builds": [
            {
                "sha": attempt.sha,
                "created_at": attempt.created_at.isoformat(),
                "state": attempt.state,
            }
            for attempt in drift.live.unpublished
        ],
        "overdue": drift.overdue,
    }


def _gh(path: str) -> Any:
    """Read the API through `gh`, which the runner already authenticates."""
    gh = shutil.which("gh")
    if gh is None:
        raise StalenessUnknown(
            "gh is not on PATH: the deployment record is the only place the live "
            "commit is written down, and it cannot be read without it"
        )
    result = subprocess.run(  # noqa: S603  # nosec B603
        [gh, "api", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise StalenessUnknown(f"gh api {path} failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def main(argv: Sequence[str] | None = None) -> int:
    doc = __doc__ or ""
    parser = argparse.ArgumentParser(description=doc.splitlines()[0])
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--head", default="origin/main")
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    parser.add_argument(
        "--json", action="store_true", help="emit the measurement as JSON"
    )
    parser.add_argument(
        "--deployments-json",
        type=Path,
        help="read deployments from a file instead of the API (offline use and tests)",
    )
    args = parser.parse_args(argv)

    try:
        if args.deployments_json:
            payload = json.loads(args.deployments_json.read_text(encoding="utf-8"))
            deployments = payload["deployments"]
            statuses = payload["statuses"]

            def statuses_for(deployment_id: Any) -> Sequence[Mapping[str, Any]]:
                recorded: Sequence[Mapping[str, Any]] = statuses.get(
                    str(deployment_id), []
                )
                return recorded
        else:
            deployments = _gh(
                f"repos/{args.repo}/deployments"
                f"?environment={PAGES_ENVIRONMENT}&per_page=20"
            )

            def statuses_for(deployment_id: Any) -> Sequence[Mapping[str, Any]]:
                fetched: Sequence[Mapping[str, Any]] = _gh(
                    f"repos/{args.repo}/deployments/{deployment_id}/statuses"
                    "?per_page=10"
                )
                return fetched

        live = resolve_live_build(deployments, statuses_for)
        drift = measure(live, args.head, datetime.now(UTC), args.max_age_days)
    except StalenessUnknown as exc:
        print(f"cannot measure deploy staleness: {exc}", file=sys.stderr)
        _write_github_output(None, str(exc))
        return 2

    print(json.dumps(as_json(drift), indent=2) if args.json else render(drift))
    _write_github_output(drift, None)
    return 0


def _write_github_output(drift: Drift | None, error: str | None) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        if drift is None:
            handle.write("measured=false\n")
            handle.write(f"error={error or 'unknown'}\n")
        else:
            handle.write("measured=true\n")
            handle.write(f"overdue={str(drift.overdue).lower()}\n")
            handle.write(f"days={drift.days}\n")
            handle.write(f"commits={drift.commits}\n")
            handle.write(f"visitor_commits={drift.visitor_commits}\n")
            handle.write(f"changed_paths={' '.join(drift.changed_paths)}\n")
            handle.write(f"unpublished_builds={len(drift.live.unpublished)}\n")
            handle.write(f"deployed_sha={drift.deployed.sha}\n")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
