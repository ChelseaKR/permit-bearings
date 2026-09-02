# Committed ruleset

`main.json` is the reviewable source for the live `protect-main` ruleset on
`ChelseaKR/permit-bearings` (id `20017370`, `enforcement: active`,
`target: branch`). It is committed so the branch-protection posture can be read
in a diff instead of only in a settings page, and so a reader can see what the
eight required contexts are without admin rights.

Read from `GET /repos/ChelseaKR/permit-bearings/rulesets/20017370` on
**2026-08-28**. `id` and `updated_at` are server-assigned and are left out of
the committed copy; everything else is reproduced as the API returns it.

## Why the owner can bypass

`bypass_actors` holds exactly the repository owner's standing bypass
(`RepositoryRole` 5, `bypass_mode: always`), deliberately and permanently: an
agent once applied a ruleset with no bypass and locked the owner out of their
own repository, and restoring access took a sweep across eighteen repositories.
An empty list here is not a stricter gate, it is the lockout.

This file recorded `"bypass_actors": []` until 2026-08-28 while the live ruleset
had the owner's bypass the whole time (`"current_user_can_bypass": "always"`).
That mattered because this file is a thing somebody re-applies. Re-applying it
as it stood, after a repository transfer or a misclick or an agent tidying up,
would have reproduced the lockout, and the empty list would have looked like the
careful choice while doing it. The committed file is what changed; **no live
ruleset or repository setting was touched.**

A standing admin bypass is a recovery path, not a merge policy. Every change to
`main` still goes through a pull request with the eight required contexts green,
signed commits, linear history, and no force-push or deletion. What the bypass
buys is a way back in when the ruleset itself is the thing that is wrong, which
a solo maintainer has no other route to: there is no second admin to let them
in.

What is worth checking, then, is not "is the list empty" but "is it exactly the
owner's own". `tests/test_repository_ruleset.py` holds the committed file and
the live ruleset against that actor **independently**, rather than comparing the
two to each other, because a comparison would report conformance on the day both
were emptied together — the incident recurring with a green tick on it. A second
actor, whether a team, a GitHub App, or another repository role, is a finding on
either side.

If you are reading this because the empty list looked more secure and you are
about to restore it: re-applying a ruleset file that omits the owner's bypass is
how the lockout happens. Do not.

## Re-applying it

Needs admin on the repository. Either route produces the same ruleset.

**In the browser.** Settings → Rules → Rulesets → New ruleset → *Import a
ruleset*, and upload `main.json`.

**From the command line.**

```sh
gh api --method POST repos/ChelseaKR/permit-bearings/rulesets \
  --input .github/rulesets/main.json
```

Check what took effect rather than assuming, and check the bypass list
specifically:

```sh
gh api repos/ChelseaKR/permit-bearings/rulesets \
  --jq '.[] | "\(.id)  \(.name)  \(.enforcement)"'
gh api repos/ChelseaKR/permit-bearings/rulesets/20017370 \
  --jq '{bypass_actors, current_user_can_bypass}'
```

`current_user_can_bypass` should read `"always"`. If it reads `"never"`, the
owner is locked out and the ruleset needs the bypass restored, not the file
"corrected" to match.
