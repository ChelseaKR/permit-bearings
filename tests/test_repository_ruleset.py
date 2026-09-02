"""The committed `protect-main` ruleset, and the one bit of it that reads backwards.

`.github/rulesets/main.json` is a file somebody re-applies. That is what makes its
`bypass_actors` list dangerous rather than merely stale: the file said `[]` until
2026-08-28 while live ruleset `20017370` had the repository owner's standing bypass
the whole time, and re-applying the file as it stood would have locked the owner out
of their own repository. That has already happened once, and restoring access took a
sweep across eighteen repositories.

So the check here is not "is the bypass list empty" and it is not "do the two lists
match". It is "does each side, on its own, hold exactly the owner's bypass and
nothing else" — see :func:`bypass_findings` for why the distinction is the whole
point.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
RULESET = REPO_ROOT / ".github" / "rulesets" / "main.json"
RULESET_DOC = REPO_ROOT / ".github" / "rulesets" / "README.md"

# The repository owner's standing bypass, exactly as GitHub returns it for live
# ruleset 20017370. Read 2026-08-28 alongside `"current_user_can_bypass": "always"`.
# Deliberate and permanent: an empty `bypass_actors` list is not a stricter gate, it
# is the lockout. See `.github/rulesets/README.md`, "Why the owner can bypass".
OWNER_BYPASS: dict[str, Any] = {
    "actor_id": 5,
    "actor_type": "RepositoryRole",
    "bypass_mode": "always",
}

# The live ruleset as `gh api repos/ChelseaKR/permit-bearings/rulesets/20017370`
# returns it, reproduced rather than fetched so this test makes no network request.
LIVE: dict[str, Any] = {
    "id": 20017370,
    "name": "protect-main",
    "target": "branch",
    "enforcement": "active",
    "bypass_actors": [dict(OWNER_BYPASS)],
    "current_user_can_bypass": "always",
}


def committed() -> dict[str, Any]:
    """The committed ruleset as it stands on disk, not a fixture of it."""
    data: dict[str, Any] = json.loads(RULESET.read_text(encoding="utf-8"))
    return data


def _side_findings(actors: list[Any], side: str) -> list[str]:
    """One bypass list held against the owner's bypass, on its own terms."""
    if OWNER_BYPASS in actors:
        return []
    return [
        f"{side} does not record the repository owner's standing bypass "
        f"({OWNER_BYPASS}). An empty or owner-less list is the lockout, not a "
        f"stricter gate."
    ]


def bypass_findings(live: dict[str, Any], commit: dict[str, Any]) -> list[str]:
    """Every way the bypass lists are wrong, each side judged separately.

    Deliberately not `live["bypass_actors"] == commit["bypass_actors"]`. If a future
    edit put the empty list back into the committed file on a day the owner had also
    been locked out of the repository, the two sides would agree and an equality check
    would report conformance on precisely the incident this exists to catch. So the
    owner's bypass is asserted against each side absolutely, and only *other* actors
    are compared between them.
    """
    live_actors = list(live.get("bypass_actors") or [])
    committed_actors = list(commit.get("bypass_actors") or [])

    findings = _side_findings(live_actors, "the live protect-main ruleset")
    findings += _side_findings(committed_actors, ".github/rulesets/main.json")

    other_live = [actor for actor in live_actors if actor != OWNER_BYPASS]
    other_committed = [actor for actor in committed_actors if actor != OWNER_BYPASS]
    findings += [
        f"unreviewed bypass actor enforced and not committed: {actor}. Only the "
        f"owner's own bypass is expected; a team, an app, or a second role is not."
        for actor in other_live
        if actor not in other_committed
    ]
    findings += [
        f"bypass actor committed and not enforced: {actor}"
        for actor in other_committed
        if actor not in other_live
    ]
    return findings


def test_the_committed_file_records_exactly_the_owner_bypass():
    """Not a fixture: the actual `.github/rulesets/main.json`.

    Re-applying a ruleset file that omits the owner's bypass is one way the lockout
    happens, so the file has to be right and not only the comparison.
    """
    assert committed()["bypass_actors"] == [OWNER_BYPASS]


def test_the_real_live_configuration_reads_as_conformance():
    """The configuration the repository is actually in must pass.

    A check that fails forever against a correct repository is not a stricter check,
    it is a broken one — which is what asserting an empty list would now be.
    """
    assert bypass_findings(LIVE, committed()) == []


def test_a_second_bypass_actor_is_reported_on_either_side():
    """The threat actually worth guarding: someone other than the owner able to
    skip the merge gate."""
    for extra in (
        {"actor_id": 4242, "actor_type": "Team", "bypass_mode": "pull_request"},
        {"actor_id": 99, "actor_type": "Integration", "bypass_mode": "always"},
        {"actor_id": 2, "actor_type": "RepositoryRole", "bypass_mode": "always"},
    ):
        live = dict(LIVE, bypass_actors=[dict(OWNER_BYPASS), extra])
        found = bypass_findings(live, committed())
        assert len(found) == 1, found
        assert "unreviewed bypass actor" in found[0]

        planted = dict(committed(), bypass_actors=[dict(OWNER_BYPASS), extra])
        found = bypass_findings(LIVE, planted)
        assert len(found) == 1, found
        assert "committed and not enforced" in found[0]


def test_the_owner_losing_their_live_bypass_is_reported():
    """The incident the rule exists for. An empty list coming back from the API is
    the owner locked out of their own repository."""
    found = bypass_findings(dict(LIVE, bypass_actors=[]), committed())
    assert len(found) == 1, found
    assert "the live protect-main ruleset" in found[0]
    assert "lockout" in found[0]


def test_both_sides_emptied_together_is_two_findings_not_zero():
    """The case a plain equality check would pass with a green tick on it: a tidy
    revert of the committed file on a day the owner had also been locked out."""
    found = bypass_findings(
        dict(LIVE, bypass_actors=[]),
        dict(committed(), bypass_actors=[]),
    )
    assert len(found) == 2, found
    assert any("the live protect-main ruleset" in line for line in found), found
    assert any(".github/rulesets/main.json" in line for line in found), found


def test_the_ruleset_still_gates_what_the_readme_says_it_gates():
    """A bypass for the owner is a recovery path, not a relaxed merge policy. If
    these rules ever go away, the bypass sentence above stops being true."""
    ruleset = committed()
    assert ruleset["name"] == "protect-main"
    assert ruleset["target"] == "branch"
    assert ruleset["enforcement"] == "active"
    assert ruleset["conditions"]["ref_name"] == {
        "include": ["refs/heads/main"],
        "exclude": [],
    }
    rules = {rule["type"]: rule for rule in ruleset["rules"]}
    assert {
        "pull_request",
        "required_status_checks",
        "required_signatures",
        "required_linear_history",
        "non_fast_forward",
        "deletion",
    } <= rules.keys()
    parameters = rules["required_status_checks"]["parameters"]
    assert parameters["strict_required_status_checks_policy"] is True
    assert parameters["required_status_checks"]


def test_the_reason_is_written_down_where_somebody_would_reapply_the_file():
    """The file is the hazard, so the warning has to live beside the file. A test
    that only checked JSON would let the explanation be deleted."""
    doc = RULESET_DOC.read_text(encoding="utf-8")
    assert "Why the owner can bypass" in doc
    assert "lockout" in doc
    assert "eighteen repositories" in doc
