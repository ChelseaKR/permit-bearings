"""Comparable-jurisdiction precedent over the committed HCD letter snapshot.

The risk in this module is not that it computes the wrong count. It is that a
reader takes a list of letters for a compliance finding, or takes an absent
row for evidence of compliance. `docs/PRODUCT-CONTEXT.md` names both, so the
boundary language is tested as behaviour rather than left to prose.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from permit_pathways.precedent import (
    BOUNDARY,
    EXIT_INVALID,
    EXIT_OK,
    comparable,
    comparable_totals,
    kind_counts,
    load_letters,
    load_names,
    main,
    render_comparable,
    render_kind_listing,
    render_kinds,
    with_kind,
)

ROOT = Path(__file__).resolve().parents[1]
REPEAL_REQUEST = "Technical Assistance Letter - Repeal Request"
ADU_LAW = "Accessory Dwelling Unit Law"


@pytest.fixture(scope="module")
def letters():
    return load_letters()


@pytest.fixture(scope="module")
def names():
    return load_names()


def _snapshot(**overrides):
    payload = {
        "source": "test snapshot",
        "retrieved_on": "2026-08-03",
        "letters": {
            "davis": [
                {
                    "date": "2025-10-08",
                    "kind": REPEAL_REQUEST,
                    "authority": ADU_LAW,
                    "statutes": "66316",
                    "subject": "Repeal the outdated ADU ordinance.",
                    "url": "https://example.invalid/davis.pdf",
                    "hau_number": "ADU1",
                }
            ],
            "woodland": [
                {
                    "date": "2025-11-08",
                    "kind": REPEAL_REQUEST,
                    "authority": ADU_LAW,
                    "statutes": "66316",
                    "subject": "Repeal the outdated ADU ordinance.",
                    "url": "https://example.invalid/woodland.pdf",
                    "hau_number": "ADU2",
                }
            ],
            "capitola": [
                {
                    "date": "2025-09-08",
                    "kind": "Letter of Inquiry",
                    "authority": "Housing Element Law",
                    "statutes": "65585",
                    "subject": "Other",
                    "url": "https://example.invalid/capitola.pdf",
                    "hau_number": "HE1",
                }
            ],
        },
    }
    payload.update(overrides)
    return payload


def _write(tmp_path: Path, payload) -> Path:
    path = tmp_path / "letters.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --- The loader refuses a shape it cannot describe ------------------------


def test_loader_reads_the_committed_snapshot(letters):
    assert letters.retrieved_on == "2026-08-03"
    assert len(letters.letters) == 1312
    assert len(letters.jurisdictions()) == 470


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda p: p.pop("retrieved_on"), "retrieved_on"),
        (lambda p: p.pop("letters"), "letters"),
        (lambda p: p.update(letters=[]), "keyed by jurisdiction"),
        (lambda p: p["letters"].update(davis="not a list"), "must be a list"),
        (lambda p: p["letters"].update(davis=["not an object"]), "must be an object"),
        (lambda p: p["letters"]["davis"][0].pop("url"), "missing 'url'"),
        (lambda p: p["letters"]["davis"][0].update(kind="  "), "cannot be blank"),
        (lambda p: p["letters"]["davis"][0].update(kind=7), "expected text"),
    ],
)
def test_loader_rejects_a_malformed_snapshot(tmp_path, mutate, message):
    payload = _snapshot()
    mutate(payload)
    with pytest.raises(ValueError, match=message):
        load_letters(_write(tmp_path, payload))


def test_a_null_date_or_authority_is_carried_rather_than_dropped(tmp_path):
    # HCD publishes rows with an empty date. Silently discarding one would
    # understate a jurisdiction's correspondence.
    payload = _snapshot()
    payload["letters"]["davis"][0]["date"] = None
    payload["letters"]["davis"][0]["authority"] = None
    loaded = load_letters(_write(tmp_path, payload))
    row = next(item for item in loaded.letters if item.jurisdiction == "davis")
    assert row.date is None
    assert row.authority is None


# --- Grouping is what makes this precedent rather than a directory --------


def test_kind_counts_match_the_committed_data(letters):
    counts = dict((kind, (n, j)) for kind, n, j in kind_counts(letters))
    # 205 jurisdictions with a repeal request is the priority list the scan
    # findings note said was already sitting in committed data.
    assert counts[REPEAL_REQUEST] == (211, 205)
    assert counts["Letter of Inquiry"][1] == 282


def test_with_kind_can_narrow_to_one_authority(letters):
    all_repeals = with_kind(letters, REPEAL_REQUEST)
    adu_repeals = with_kind(letters, REPEAL_REQUEST, ADU_LAW)
    assert adu_repeals
    assert len(adu_repeals) <= len(all_repeals)
    assert all(letter.authority == ADU_LAW for letter in adu_repeals)


def test_comparable_groups_by_kind_and_authority_and_excludes_the_subject(tmp_path):
    loaded = load_letters(_write(tmp_path, _snapshot()))
    groups = comparable(loaded, "davis")
    assert set(groups) == {(REPEAL_REQUEST, ADU_LAW)}
    matched = groups[(REPEAL_REQUEST, ADU_LAW)]
    assert [letter.jurisdiction for letter in matched] == ["woodland"]
    # Capitola shares neither the kind nor the authority, so it is not
    # comparable. A directory would have listed it.
    assert all(letter.jurisdiction != "capitola" for letter in matched)


def test_a_capped_listing_still_reports_the_full_group_size(letters):
    capped = comparable(letters, "davis", limit=3)
    totals = comparable_totals(letters, "davis")
    key = (REPEAL_REQUEST, ADU_LAW)
    assert len(capped[key]) == 3
    assert totals[key] > 3
    rendered = render_comparable(letters, load_names(), "davis", limit=3)
    assert f"{totals[key]} other jurisdiction letter(s); showing the 3 most recent" in (
        rendered
    )


def test_comparable_is_empty_for_a_jurisdiction_with_no_letters(letters, names):
    without = sorted(set(names) - letters.jurisdictions())
    assert without, "expected some registry entry with no linked letter"
    assert comparable(letters, without[0]) == {}


# --- The boundary travels with every rendering ---------------------------


def test_every_rendering_carries_the_precedent_boundary(letters, names):
    renderings = [
        render_kinds(letters),
        render_kind_listing(letters, names, REPEAL_REQUEST, ADU_LAW),
        render_comparable(letters, names, "davis", limit=2),
    ]
    for rendering in renderings:
        assert BOUNDARY in rendering
        assert letters.retrieved_on in rendering


def test_an_absent_letter_is_never_rendered_as_compliance(letters, names):
    without = sorted(set(names) - letters.jurisdictions())[0]
    rendering = render_comparable(letters, names, without, limit=5)
    assert "links no letter" in rendering
    assert "not evidence of compliance" in rendering
    assert BOUNDARY in rendering


def test_an_unmatched_kind_says_so_rather_than_printing_an_empty_list(letters, names):
    rendering = render_kind_listing(letters, names, "Letter That Does Not Exist")
    assert "No letter in the committed snapshot has kind" in rendering
    assert BOUNDARY in rendering


# --- The CLI -------------------------------------------------------------


def test_cli_kinds_and_list_and_for_all_succeed(capsys):
    assert main(["kinds"]) == EXIT_OK
    assert BOUNDARY in capsys.readouterr().out
    assert main(["list", "--kind", REPEAL_REQUEST, "--authority", ADU_LAW]) == EXIT_OK
    assert BOUNDARY in capsys.readouterr().out
    assert main(["for", "davis", "--limit", "2"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "Comparable HCD precedent for Davis (davis)" in out
    assert BOUNDARY in out


def test_cli_rejects_a_slug_the_registry_does_not_hold(capsys):
    assert main(["for", "not-a-city"]) == EXIT_INVALID
    assert "is not a registry slug" in capsys.readouterr().out


def test_cli_rejects_a_nonsense_limit(capsys):
    assert main(["for", "davis", "--limit", "0"]) == EXIT_INVALID
    assert "--limit must be at least 1" in capsys.readouterr().out


def test_cli_reports_an_unreadable_dataset_rather_than_crashing(tmp_path, capsys):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert main(["--letters", str(broken), "kinds"]) == EXIT_INVALID
    assert "cannot read the committed dataset" in capsys.readouterr().out


def test_the_cli_writes_nothing(tmp_path, monkeypatch, capsys):
    # Read-only is a property worth asserting, not just documenting.
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    assert main(["for", "davis"]) == EXIT_OK
    capsys.readouterr()
    assert set(tmp_path.iterdir()) == before


def test_the_cli_makes_no_network_call(monkeypatch, capsys):
    import socket

    def refuse(*args, **kwargs):
        raise AssertionError("precedent discovery must not reach the network")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    assert main(["for", "davis"]) == EXIT_OK
    capsys.readouterr()
