"""The detector that answers "is the live site the site this repository has?".

Written from both directions, because the failure it replaces was a green gate.
A detector that cannot fire is noise and gets deleted; a detector that reports a
number it did not really measure is worse than none, because the number reads as
a measurement and nobody re-derives it.

So the cases below cover the drift it must report AND every way the comparison
can be meaningless -- no deployment at all, a deployment that never succeeded, a
commit this clone does not contain, a history that has diverged, a declared
visitor path `main` no longer has. Each of those ends in a refusal. None of them
ends in a comfortable zero.

Two cases are specific to this repository's publishing model, which is GitHub's
own legacy Jekyll build serving the committed root of `main`:

* `test_a_commit_that_only_touched_the_repository_is_not_drift`. That build
  mirrors nearly the whole repository into the site -- `/tests/accessibility.spec.js`
  and `/uv.lock` both answer 200 -- so comparing the published *root* would report
  drift on a commit that only edited a test. The surface list is what stops it.
* `test_a_build_that_failed_is_not_the_live_commit`. GitHub does the building, so
  a push can land and the build can break, leaving an older commit serving while
  nothing in `.github/workflows/` goes red. The status check is the only thing
  between that and a report claiming the site is fresher than it is.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def _script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Registered before execution, not after: `@dataclass` resolves annotations
    # through `sys.modules[cls.__module__]`, so a module that is not there yet
    # raises on the decorator rather than on anything to do with this repository.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


staleness = _script("deploy_staleness")

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
AUGUST = "2026-08-01T07:29:54Z"


def _deployment(**over: Any) -> dict[str, Any]:
    row = {
        "id": 6413320723,
        "sha": "c" * 40,
        "environment": "github-pages",
        "created_at": AUGUST,
    }
    row.update(over)
    return row


def _succeeded(_id: Any) -> Sequence[Mapping[str, Any]]:
    return [{"state": "success"}]


def _never_succeeded(_id: Any) -> Sequence[Mapping[str, Any]]:
    return [{"state": "failure"}, {"state": "in_progress"}]


# --- what the deployment record is allowed to mean --------------------------


def test_the_newest_successful_deployment_is_the_live_build() -> None:
    live = staleness.resolve_live_build([_deployment()], _succeeded)
    assert live.record.sha == "c" * 40
    assert live.record.created_at.date().isoformat() == "2026-08-01"
    assert live.record.deployment_id == 6413320723
    assert live.unpublished == ()


def test_the_newest_deployment_wins_over_an_older_one() -> None:
    newer = _deployment(id=2, sha="d" * 40, created_at="2026-09-12T19:06:37Z")
    live = staleness.resolve_live_build([_deployment(), newer], _succeeded)
    assert live.record.sha == "d" * 40


def test_no_deployment_at_all_is_a_refusal_not_a_zero() -> None:
    with pytest.raises(staleness.StalenessUnknown, match="no github-pages deployment"):
        staleness.resolve_live_build([], _succeeded)


def test_a_deployment_that_never_succeeded_is_a_refusal() -> None:
    with pytest.raises(staleness.StalenessUnknown, match="successful status"):
        staleness.resolve_live_build([_deployment()], _never_succeeded)


def test_a_row_without_a_commit_id_is_not_a_deployment() -> None:
    with pytest.raises(staleness.StalenessUnknown, match="no github-pages deployment"):
        staleness.resolve_live_build([_deployment(sha="not-a-sha")], _succeeded)


def test_a_build_that_failed_is_not_the_live_commit() -> None:
    """The failure mode a GitHub-built site adds.

    Nothing in `.github/workflows/` publishes this site, so when GitHub's own
    build breaks there is no red run anywhere: `main` moves, the served commit
    does not. Reading the newest deployment row would report the newest commit
    as live and the site as perfectly fresh, which is the exact direction of
    error this sentinel exists to prevent.
    """
    broken = _deployment(id=9, sha="e" * 40, created_at="2026-09-12T19:06:37Z")

    def statuses(deployment_id: Any) -> Sequence[Mapping[str, Any]]:
        return [{"state": "failure"}] if deployment_id == 9 else [{"state": "success"}]

    live = staleness.resolve_live_build([_deployment(), broken], statuses)

    assert live.record.sha == "c" * 40
    assert [a.sha for a in live.unpublished] == ["e" * 40]
    assert live.unpublished[0].state == "failure"


def test_a_build_still_running_is_not_the_live_commit_either() -> None:
    """`in_progress` is not `success`. Bytes have not landed yet."""
    running = _deployment(id=9, sha="e" * 40, created_at="2026-09-12T19:06:37Z")

    def statuses(deployment_id: Any) -> Sequence[Mapping[str, Any]]:
        return (
            [{"state": "in_progress"}, {"state": "queued"}]
            if deployment_id == 9
            else [{"state": "success"}]
        )

    live = staleness.resolve_live_build([_deployment(), running], statuses)

    assert live.record.sha == "c" * 40
    assert live.unpublished[0].state == "in_progress"


def test_a_deployment_with_no_statuses_at_all_is_not_the_live_commit() -> None:
    stateless = _deployment(id=9, sha="e" * 40, created_at="2026-09-12T19:06:37Z")

    def statuses(deployment_id: Any) -> Sequence[Mapping[str, Any]]:
        return [] if deployment_id == 9 else [{"state": "success"}]

    live = staleness.resolve_live_build([_deployment(), stateless], statuses)

    assert live.record.sha == "c" * 40
    assert live.unpublished[0].state == "no status"


# --- which paths a visitor actually receives --------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "index.html",
        "check.html",
        "evidence.html",
        "prepare.html",
        "review.html",
        "privacy.html",
        "assets/site.css",
        "assets/demo.js",
        "assets/analytics.js",
        "assets/illustrations/permit-pathway-hero.webp",
        "data/demo-data.js",
        "data/rules/statewide.json",
        "corpus/leginfo/gov-66314.html",
    ],
)
def test_the_published_pages_and_what_they_load_ship_to_visitors(path: str) -> None:
    assert staleness.ships_to_visitors(path)


@pytest.mark.parametrize(
    "path",
    [
        "tests/accessibility.spec.js",
        "tests/test_deploy_staleness.py",
        "src/permit_pathways/screening.py",
        "scripts/build_demo_bundle.py",
        "schemas/screening-result.schema.json",
        "docs/DESIGN.md",
        "evals/ai/ask-cases.json",
        "deploy/ai-service/main.tf",
        "demo/app.py",
        "pyproject.toml",
        "uv.lock",
        "README.md",
        ".github/workflows/ci.yml",
    ],
)
def test_the_rest_of_the_repository_does_not(path: str) -> None:
    """GitHub serves most of these; no visitor receives them.

    The legacy Jekyll build copies everything whose name does not start with
    `.` or `_`, so `/tests/accessibility.spec.js`, `/uv.lock` and
    `/scripts/build_demo_bundle.py` all answer 200. That mirror is an artifact
    of the default build, not a surface: no page links them and nothing fetches
    them. Counting them is what would make this sentinel report drift on a
    commit that only touched a test, and a sentinel that fires on every commit
    is one nobody reads.
    """
    assert not staleness.ships_to_visitors(path)


def test_every_local_reference_the_shipped_pages_make_is_inside_the_surface() -> None:
    """The surface list is checked against the pages, not asserted about them.

    A hand-maintained inclusion list fails toward silence: add a page, or move
    an asset into a new top-level directory, and the sentinel keeps reporting
    "up to date" about a surface that no longer covers the site. So the
    references are re-derived here out of the committed HTML and the committed
    JavaScript, and any site-relative path that escapes `VISITOR_SURFACE` fails
    this test rather than disappearing from the measurement.
    """
    pages = [
        "index.html",
        "check.html",
        "evidence.html",
        "prepare.html",
        "review.html",
        "privacy.html",
    ]
    scripts = [
        "assets/demo.js",
        "assets/ai.js",
        "assets/analytics.js",
        "data/demo-data.js",
    ]

    referenced: set[str] = set()
    for page in pages:
        text = (REPO_ROOT / page).read_text(encoding="utf-8")
        referenced.update(
            m.group(1) for m in re.finditer(r'(?:src|href)="([^"]+)"', text)
        )
    for script in scripts:
        text = (REPO_ROOT / script).read_text(encoding="utf-8")
        referenced.update(
            m.group(1)
            for m in re.finditer(
                r'"((?:assets|corpus|data|docs|evals|schemas)/[^"]+)"', text
            )
        )

    escaped = sorted(
        reference
        for reference in (r.split("?")[0].split("#")[0] for r in referenced)
        if reference
        and not reference.startswith(("http://", "https://", "mailto:", "/"))
        and not staleness.ships_to_visitors(reference.rstrip("/"))
    )

    assert escaped == [], (
        "these paths are loaded by the published pages but are outside "
        f"VISITOR_SURFACE, so a change to them would not be measured: {escaped}"
    )


def test_every_declared_surface_entry_exists_in_this_checkout() -> None:
    """A surface list that names a path the repository does not have measures

    nothing, and reports "up to date" while doing it.
    """
    missing = [e for e in staleness.VISITOR_SURFACE if not (REPO_ROOT / e).exists()]
    assert missing == []


# --- the comparison against main, and every way it can be meaningless -------


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    _git(root, "add", path)


def _commit(root: Path, path: str, body: str = "x") -> str:
    _write(root, path, body)
    _git(root, "commit", "-m", f"touch {path}")
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture
def clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository carrying one file for every declared visitor-surface entry.

    Seeded so the surface comparison has something real to compare; the missing
    entry is introduced deliberately, by one test, rather than being the
    fixture's accidental default.
    """
    root = tmp_path / "clone"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "sentinel@example.test")
    _git(root, "config", "user.name", "sentinel")
    for page in ("index", "check", "evidence", "prepare", "review", "privacy"):
        _write(root, f"{page}.html", f"<!doctype html><title>{page}</title>")
    _write(root, "assets/site.css", "body{color:#000}")
    _write(root, "corpus/leginfo/gov-66314.html", "<p>statute</p>")
    _write(root, "data/demo-data.js", "window.DEMO={};")
    _git(root, "commit", "-m", "seed the published site")
    monkeypatch.setattr(staleness, "REPO_ROOT", root)
    return root


def _live(sha: str, created_at: datetime, unpublished: tuple[Any, ...] = ()) -> Any:
    return staleness.LiveBuild(
        record=staleness.DeployRecord(deployment_id=1, sha=sha, created_at=created_at),
        unpublished=unpublished,
    )


def test_it_counts_the_commits_and_names_the_paths_whose_bytes_moved(
    clone: Path,
) -> None:
    deployed = _git(clone, "rev-parse", "HEAD")
    _commit(clone, "tests/test_x.py")
    _commit(clone, "assets/site.css", "body{color:#111}")
    _commit(clone, "data/rules/statewide.json", "{}")

    drift = staleness.measure(_live(deployed, NOW - timedelta(days=40)), "HEAD", NOW)

    assert drift.commits == 3
    assert drift.visitor_commits == 2
    assert drift.changed_paths == ("assets", "data")
    assert drift.days == 40
    assert drift.overdue


def test_a_commit_that_only_touched_the_repository_is_not_drift(clone: Path) -> None:
    """The cry-wolf case the whole-root comparison would produce.

    GitHub serves `/tests/accessibility.spec.js` and `/pyproject.toml`, so the
    published root's tree id moves on a commit that changed nothing anyone sees.
    Comparing the surface instead of the root is what keeps that from reading as
    a stale site.
    """
    deployed = _git(clone, "rev-parse", "HEAD")
    _commit(clone, "tests/test_x.py")
    _commit(clone, "pyproject.toml", "[project]\n")
    _commit(clone, "src/permit_pathways/screening.py", "pass\n")

    drift = staleness.measure(_live(deployed, NOW - timedelta(days=200)), "HEAD", NOW)

    assert drift.commits == 3
    assert drift.visitor_commits == 0
    assert drift.changed_paths == ()
    assert not drift.overdue
    assert "Up to date" in staleness.render(drift)


def test_a_visitor_change_that_was_reverted_is_not_drift(clone: Path) -> None:
    """Object ids, not commit counts.

    Two commits touched the visitor surface and the visitor still has exactly
    `main`'s bytes. Counting commits would call this a stale site for as long as
    nobody pushed again; comparing what is served says the true thing.
    """
    deployed = _git(clone, "rev-parse", "HEAD")
    _commit(clone, "assets/site.css", "body{color:#111}")
    _commit(clone, "assets/site.css", "body{color:#000}")

    drift = staleness.measure(_live(deployed, NOW - timedelta(days=200)), "HEAD", NOW)

    assert drift.commits == 2
    assert drift.visitor_commits == 2
    assert drift.changed_paths == ()
    assert not drift.overdue


def test_age_alone_is_not_overdue(clone: Path) -> None:
    """A site nobody republished because nothing it publishes changed is

    correct, not stale. Reporting on age alone would make this fire on every
    repository that is simply finished.
    """
    deployed = _git(clone, "rev-parse", "HEAD")
    _commit(clone, "src/permit_pathways/screening.py")

    drift = staleness.measure(_live(deployed, NOW - timedelta(days=365)), "HEAD", NOW)

    assert drift.commits == 1
    assert drift.changed_paths == ()
    assert not drift.overdue


def test_inside_the_threshold_is_not_overdue(clone: Path) -> None:
    deployed = _git(clone, "rev-parse", "HEAD")
    _commit(clone, "index.html", "<!doctype html><title>new</title>")

    drift = staleness.measure(_live(deployed, NOW - timedelta(days=3)), "HEAD", NOW)

    assert drift.changed_paths == ("index.html",)
    assert not drift.overdue
    assert "Waiting" in staleness.render(drift)


def test_nothing_since_the_deploy_is_up_to_date(clone: Path) -> None:
    deployed = _git(clone, "rev-parse", "HEAD")

    drift = staleness.measure(_live(deployed, NOW - timedelta(days=1)), "HEAD", NOW)

    assert drift.commits == 0
    assert drift.changed_paths == ()
    assert not drift.overdue


def test_a_commit_this_clone_does_not_have_is_a_refusal(clone: Path) -> None:
    """The shallow-checkout case, which is the one that reports zero silently.

    `git log <absent>..HEAD` on a shallow clone lists nothing, so the site reads
    as current. This is why the sentinel checks out with `fetch-depth: 0`, and
    why the refusal exists rather than trusting that it did.
    """
    with pytest.raises(staleness.StalenessUnknown, match="not in this clone"):
        staleness.measure(_live("a" * 40, NOW - timedelta(days=40)), "HEAD", NOW)


def test_a_diverged_history_is_a_refusal(clone: Path) -> None:
    _git(clone, "checkout", "-b", "other")
    orphan = _commit(clone, "orphan.txt")
    _git(clone, "checkout", "main")

    with pytest.raises(staleness.StalenessUnknown, match="not an ancestor"):
        staleness.measure(_live(orphan, NOW - timedelta(days=40)), "HEAD", NOW)


def test_a_malformed_deployed_sha_is_a_refusal(clone: Path) -> None:
    with pytest.raises(staleness.StalenessUnknown, match="not a commit id"):
        staleness.measure(_live("nope", NOW), "HEAD", NOW)


def test_a_surface_entry_main_no_longer_has_is_a_refusal(clone: Path) -> None:
    """A stale surface list measures a page that is not there and calls it clean.

    Renaming `prepare.html` without updating `VISITOR_SURFACE` would otherwise
    leave one published page permanently unwatched, silently.
    """
    deployed = _git(clone, "rev-parse", "HEAD")
    _git(clone, "rm", "prepare.html")
    _git(clone, "commit", "-m", "retire prepare.html")

    with pytest.raises(staleness.StalenessUnknown, match="no longer describes"):
        staleness.measure(_live(deployed, NOW - timedelta(days=1)), "HEAD", NOW)


def test_object_id_is_none_for_a_path_that_is_not_there(clone: Path) -> None:
    head = _git(clone, "rev-parse", "HEAD")
    assert staleness.object_id(head, "index.html") is not None
    assert staleness.object_id(head, "not-a-file.html") is None


# --- the report, and the exit code --------------------------------------------


def test_the_report_states_the_measurement_before_its_verdict(clone: Path) -> None:
    deployed = _git(clone, "rev-parse", "HEAD")
    _commit(clone, "assets/site.css", "body{color:#111}")
    drift = staleness.measure(_live(deployed, NOW - timedelta(days=40)), "HEAD", NOW)

    report = staleness.render(drift)

    assert deployed[:9] in report
    assert "40 days" in report
    assert "OVERDUE" in report
    assert report.index("Behind by") < report.index("OVERDUE")
    assert report.index("Differing bytes") < report.index("OVERDUE")


def test_the_report_names_a_build_that_did_not_publish(clone: Path) -> None:
    """Otherwise "the owner published nothing" and "the build is broken" read

    identically from outside, and only one of them is anybody's to fix.
    """
    deployed = _git(clone, "rev-parse", "HEAD")
    _commit(clone, "index.html", "<!doctype html><title>new</title>")
    broken = staleness.UnpublishedAttempt(
        sha="e" * 40, created_at=NOW - timedelta(days=1), state="failure"
    )
    live = _live(deployed, NOW - timedelta(days=40), (broken,))

    report = staleness.render(staleness.measure(live, "HEAD", NOW))

    assert "did NOT publish" in report
    assert "eeeeeeeee" in report
    assert "failure" in report


def test_the_json_carries_every_number_the_report_states(clone: Path) -> None:
    deployed = _git(clone, "rev-parse", "HEAD")
    _commit(clone, "data/rules/statewide.json", "{}")
    drift = staleness.measure(_live(deployed, NOW - timedelta(days=40)), "HEAD", NOW)

    payload = staleness.as_json(drift)

    assert payload["deployed_sha"] == deployed
    assert payload["days"] == 40
    assert payload["commits"] == 1
    assert payload["visitor_commits"] == 1
    assert payload["changed_paths"] == ["data"]
    assert payload["unpublished_builds"] == []
    assert payload["overdue"] is True


def test_the_cli_refuses_with_a_nonzero_exit_when_it_cannot_measure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 2, not 0 with a reassuring report. The sentinel workflow turns a

    measurement into an issue and a refusal into a red run, so this exit code is
    the whole difference between "the site is fine" and "nobody can tell".
    """
    payload = tmp_path / "deployments.json"
    payload.write_text('{"deployments": [], "statuses": {}}', encoding="utf-8")

    code = staleness.main(["--deployments-json", str(payload)])

    assert code == 2
    assert "cannot measure" in capsys.readouterr().err


def test_the_cli_reports_and_exits_zero_when_it_can_measure(
    clone: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    deployed = _git(clone, "rev-parse", "HEAD")
    payload = tmp_path / "deployments.json"
    payload.write_text(
        f'{{"deployments": [{{"id": 1, "sha": "{deployed}", '
        f'"environment": "github-pages", "created_at": "{AUGUST}"}}], '
        '"statuses": {"1": [{"state": "success"}]}}',
        encoding="utf-8",
    )

    code = staleness.main(
        ["--deployments-json", str(payload), "--head", "HEAD", "--json"]
    )

    assert code == 0
    assert '"overdue": false' in capsys.readouterr().out


def test_the_github_output_records_a_refusal_as_unmeasured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The workflow reads `measured`; if a refusal wrote nothing, the reporting

    step would see an empty value and take the not-overdue branch, closing the
    open issue on a run that measured nothing at all.
    """
    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    payload = tmp_path / "deployments.json"
    payload.write_text('{"deployments": [], "statuses": {}}', encoding="utf-8")

    assert staleness.main(["--deployments-json", str(payload)]) == 2
    assert "measured=false" in output.read_text(encoding="utf-8")
