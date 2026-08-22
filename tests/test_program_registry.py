import json
from pathlib import Path

import pytest

from permit_pathways import program_registry as pr

ROOT = Path(__file__).parent.parent
REGISTRY_PATH = ROOT / "program-pages.json"


def _page(**overrides):
    page = {
        "page_id": "city-preapproved-plans",
        "label": "City preapproved plan list",
        "url": "https://example.org/plans",
        "excerpt": "No plans are listed on this prototype page.",
        "excerpt_fingerprint": None,
    }
    import hashlib

    normalized = pr.normalize_excerpt(page["excerpt"])
    page["excerpt_fingerprint"] = (
        "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    )
    page.update(overrides)
    return page


def _write(tmp_path, pages):
    path = tmp_path / "program-pages.json"
    path.write_text(json.dumps({"schema_version": 1, "pages": pages}), encoding="utf-8")
    return path


def _load(tmp_path, pages):
    return pr.load_program_registry(_write(tmp_path, pages))


# ---------------------------------------------------------------------------
# The committed registry


def test_committed_registry_loads_and_matches_the_availability_record():
    pages = pr.load_program_registry(REGISTRY_PATH)
    assert [page.page_id for page in pages] == ["woodland-preapproved-adu-program"]
    assert pages[0].url.endswith("/Preapproved-ADU-Plan-Program")
    assert pages[0].excerpt_fingerprint.startswith("sha256:")


# ---------------------------------------------------------------------------
# Schema validation


def test_fingerprint_must_match_its_own_excerpt(tmp_path):
    with pytest.raises(ValueError, match="does not match the recorded excerpt"):
        _load(tmp_path, [_page(excerpt_fingerprint="sha256:" + "0" * 64)])


def test_schema_errors_are_rejected(tmp_path):
    cases = [
        ([_page(page_id="Bad ID")], "stable identifier"),
        ([_page(url="http://example.org/plans")], "canonical HTTPS URL"),
        ([_page(label="  ")], "non-blank text"),
        ([_page(), _page()], "duplicate page ID"),
        ([_page(excerpt_fingerprint="deadbeef")], "normalized SHA-256"),
    ]
    for pages, match in cases:
        with pytest.raises(ValueError, match=match):
            _load(tmp_path, pages)

    extra = _page()
    extra["note"] = "unexpected"
    with pytest.raises(ValueError, match="unknown fields"):
        _load(tmp_path, [extra])

    missing = _page()
    del missing["label"]
    with pytest.raises(ValueError, match="missing fields"):
        _load(tmp_path, [missing])


# ---------------------------------------------------------------------------
# Classification


def _fetcher(responses):
    def fetch(url):
        result = responses[url]
        if isinstance(result, Exception):
            raise result
        return result

    return fetch


def test_pages_classify_as_changed_unverifiable_or_unchanged(tmp_path):
    pages = _load(
        tmp_path,
        [
            _page(page_id="a-still-there"),
            _page(page_id="b-moved", url="https://example.org/moved"),
            _page(page_id="c-unreachable", url="https://example.org/unreachable"),
            _page(page_id="d-whitespace", url="https://example.org/spacey"),
        ],
    )
    body = "<html><body>No plans are listed on this prototype page.</body></html>"
    # A real U+00A0 and messy spacing normalize away; a literal HTML entity
    # does not decode at this text level and would count as absence.
    spacey = "<p>No\u00a0plans   are listed\n on this prototype page.</p>"
    result = pr.check_program_pages(
        pages,
        fetch=_fetcher(
            {
                "https://example.org/plans": body,
                "https://example.org/moved": "<html>Coming soon!</html>",
                "https://example.org/unreachable": RuntimeError("offline"),
                "https://example.org/spacey": spacey,
            }
        ),
    )
    by_id = {item.page_id: item.status for item in result.observations}
    assert by_id == {
        "a-still-there": "unchanged",
        "b-moved": "changed",
        "c-unreachable": "unverifiable",
        # Presentation-only churn normalizes away and is never a change.
        "d-whitespace": "unchanged",
    }
    assert result.changed_page_ids == ("b-moved",)
    assert "1 changed" in result.summary()


def test_changed_pages_propose_the_pre_written_issue_only(tmp_path):
    pages = _load(tmp_path, [_page()])
    result = pr.check_program_pages(
        pages, fetch=_fetcher({"https://example.org/plans": "<html>new content</html>"})
    )
    proposal = pr.issue_proposal(pages[0], result)
    assert proposal["title"] == "Program page changed: City preapproved plan list"
    assert "candidate change, not" in proposal["body"]
    assert pages[0].excerpt_fingerprint in proposal["body"]
    assert "never marks anything stale" in proposal["body"]


def test_report_is_stable_machine_readable_json(tmp_path):
    pages = _load(tmp_path, [_page()])
    result = pr.check_program_pages(
        pages, fetch=_fetcher({"https://example.org/plans": "<html>x</html>"})
    )
    payload = json.loads(pr.encoded_report(result))
    assert payload["schema_version"] == 1
    assert payload["changed_page_ids"] == ["city-preapproved-plans"]
    assert set(payload["observations"][0]) == {"page_id", "url", "status", "detail"}


def test_cli_exit_codes_mirror_the_watcher_contract(tmp_path, monkeypatch):
    entries = [
        {
            "page_id": page_id,
            "label": label,
            "url": url,
            "excerpt": "No plans are listed on this prototype page.",
            "excerpt_fingerprint": None,
        }
        for page_id, label, url in [
            ("moved", "M", "https://example.org/plans"),
            ("dark", "D", "https://example.org/dark"),
            ("calm", "C", "https://example.org/calm"),
        ]
    ]
    import hashlib

    for entry in entries:
        normalized = pr.normalize_excerpt(entry["excerpt"])
        entry["excerpt_fingerprint"] = (
            "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        )
    registry = _write(tmp_path, entries)

    monkeypatch.setattr(
        pr,
        "_default_fetch",
        _fetcher(
            {
                "https://example.org/calm": "No plans are listed on this prototype page.",
                "https://example.org/dark": RuntimeError("offline"),
                "https://example.org/plans": "<html>renovated</html>",
            }
        ),
    )
    issues_dir = tmp_path / "issues"
    code = pr.main(["--registry", str(registry), "--issues-out", str(issues_dir)])
    assert code == 1
    proposal_files = sorted(p.name for p in issues_dir.iterdir())
    assert proposal_files == ["moved.md"]

    monkeypatch.setattr(
        pr,
        "_default_fetch",
        _fetcher(
            {
                "https://example.org/calm": RuntimeError("offline"),
                "https://example.org/dark": RuntimeError("offline"),
                "https://example.org/plans": RuntimeError("offline"),
            }
        ),
    )
    assert pr.main(["--registry", str(registry)]) == 2
