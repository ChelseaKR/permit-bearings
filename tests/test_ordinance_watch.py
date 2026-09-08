"""The ordinance watch: what it may conclude, and what it must refuse to.

Every published conformance result names a real California city and says its
ordinance carries specific defects. The scan behind those claims was taken once.
The whole risk this module carries is that a re-read is *misread*: a redirect
notice served with a 200 becomes a clean bill of health, a throttled runner
becomes an amended ordinance, a chapter that dropped four of five repealed
citations reads as unchanged because a set comparison cannot count.

So the tests below are organised by the wrong conclusion each guard exists to
prevent, not by function.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
from pathlib import Path

import pytest
from scripts import watch_ordinances

from permit_pathways import ordinance_watch
from permit_pathways.conformance import load_checks

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus/ordinances"
RESULTS = ROOT / "data/conformance/results"
CHECKS = ROOT / "data/conformance/checks.json"

# A paragraph the committed checks flag, taken from the shape the real corpus
# uses rather than invented: the repealed-section citation is the finding the
# published Capitola result leads with.
# Measured, not assumed: this paragraph fires `stale-statutory-citation` twice
# (once per repealed section it names), a current one fires it not at all, and
# two copies fire it four times. Every expected count below is written as a
# literal from those measurements rather than derived from a fresh scan, which
# would move with whatever the scanner did and assert nothing.
STALE = (
    "Chapter 17.74. This chapter establishes standards for the location and "
    "construction of "
    "accessory dwelling units (ADUs) consistent with Government Code Sections "
    "65852.2 through 65852.22. These standards are intended to allow accessory "
    "dwelling units as a form of affordable housing."
)
CURRENT = STALE.replace("65852.2 through 65852.22", "66310 through 66342")


@pytest.fixture(scope="module")
def checks():
    return load_checks(CHECKS)


def _page(body: str) -> bytes:
    return f"<html><body><p>{body}</p></body></html>".encode()


def _source(
    tmp_path: Path,
    *,
    text: str,
    identifier: str = "17.74",
    url: str = "https://example.invalid/CA/Capitola/html/Capitola1774.html",
):
    """A declared source whose committed text is `text`, written to disk."""
    (tmp_path / "capitola.txt").write_text(text, encoding="utf-8")
    sources = {
        "capitola": {
            "title": "Capitola Municipal Code, Ch. 17.74",
            "url": url,
            "retrieved": "2026-08-15",
            "note": "fixture",
            "watch": {
                "identifier": identifier,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            },
        }
    }
    (tmp_path / "SOURCES.json").write_text(json.dumps(sources), encoding="utf-8")
    return ordinance_watch.load_sources(tmp_path / "SOURCES.json")["capitola"]


class TestAFailedReadIsNeverAChange:
    """The distinction the statewide watcher exists to preserve, kept here."""

    @pytest.mark.parametrize(
        ("kind", "detail"),
        [("transport", "timed out"), ("not_found", "HTTP 404")],
    )
    def test_no_answer_is_unverifiable_and_carries_its_kind(
        self, tmp_path, checks, kind, detail
    ):
        source = _source(tmp_path, text=STALE)
        watch = ordinance_watch.watch_source(
            source,
            None,
            failure=(kind, detail),
            published={"stale-statutory-citation": 1},
            checks=checks,
        )
        assert watch.status == "unverifiable"
        assert watch.kind == kind
        assert detail in watch.detail
        # A source nobody could read has no diff, and printing an empty one
        # would read as "we looked and nothing moved".
        assert watch.newly_flagged == ()
        assert watch.no_longer_flagged == ()

    def test_bytes_no_extractor_can_read_are_unverifiable_not_empty(
        self, tmp_path, checks
    ):
        """A payload this project cannot read is not a document with no findings."""
        source = _source(tmp_path, text=STALE, url="https://x.invalid/ch.pdf")
        watch = ordinance_watch.watch_source(
            source,
            b"not a PDF, whatever the address said",
            failure=None,
            published={"stale-statutory-citation": 1},
            checks=checks,
        )
        assert (watch.status, watch.kind) == ("unverifiable", "not_extractable")


class TestATwoHundredIsNotEvidenceThatItIsTheDocument:
    """The Angels case, which is why `not_the_document` exists.

    On 2026-09-08 the recorded Angels URL answered 200 with a publisher
    migration notice. Scanning that page yields zero findings, so anything that
    treats a 200 as content publishes a clean bill of health for a city whose
    ordinance nobody read.
    """

    def test_a_migration_notice_is_not_a_repealed_ordinance(self, tmp_path, checks):
        source = _source(tmp_path, text=STALE, identifier="17.74")
        notice = _page(
            "Your municipal code is now hosted on General Code's eCode360 "
            "platform and can be viewed here: https://ecode360.com/AN4338"
        )

        watch = ordinance_watch.watch_source(
            source,
            notice,
            failure=None,
            published={"stale-statutory-citation": 1},
            checks=checks,
        )

        assert (watch.status, watch.kind) == ("unverifiable", "not_the_document")
        assert "17.74" in watch.detail
        # The trap this closes: the notice really does scan to nothing.
        assert watch.no_longer_flagged == ()

    def test_the_same_bytes_would_otherwise_read_as_every_finding_gone(
        self, tmp_path, checks
    ):
        """Proof the guard is load-bearing rather than decorative.

        With the identifier declared as something the notice happens to carry,
        the very same page is classified `changed` and reports the ordinance's
        every finding as resolved. That is the outcome; the identifier is the
        only thing standing between the watch and publishing it.
        """
        source = _source(tmp_path, text=STALE, identifier="ADU")
        notice = _page("Your municipal code has moved. ADU chapters are online.")

        watch = ordinance_watch.watch_source(
            source,
            notice,
            failure=None,
            published={"stale-statutory-citation": 1},
            checks=checks,
        )

        assert watch.status == "changed"
        assert watch.no_longer_flagged == (("stale-statutory-citation", 1),)


class TestTheDiffCountsRatherThanSets:
    def test_a_chapter_that_drops_four_of_five_citations_has_changed(
        self, tmp_path, checks
    ):
        """A set comparison calls this unchanged. It is not."""
        source = _source(tmp_path, text=STALE)

        watch = ordinance_watch.watch_source(
            source,
            _page(STALE),
            failure=None,
            published={"stale-statutory-citation": 6},
            checks=checks,
        )

        assert watch.status == "changed"
        assert watch.no_longer_flagged == (("stale-statutory-citation", 4),)
        assert watch.newly_flagged == ()

    def test_a_current_citation_stops_flagging_and_the_diff_names_it(
        self, tmp_path, checks
    ):
        source = _source(tmp_path, text=STALE)

        watch = ordinance_watch.watch_source(
            source,
            _page(CURRENT),
            failure=None,
            published={"stale-statutory-citation": 2},
            checks=checks,
        )

        assert watch.status == "changed"
        assert watch.no_longer_flagged == (("stale-statutory-citation", 2),)
        assert "stale-statutory-citation" in watch.describe()

    def test_an_unchanged_page_reports_the_offsets_it_read(self, tmp_path, checks):
        source = _source(tmp_path, text=STALE)

        watch = ordinance_watch.watch_source(
            source,
            _page(STALE),
            failure=None,
            published={"stale-statutory-citation": 2},
            checks=checks,
        )

        assert (watch.status, watch.kind) == ("unchanged", None)
        assert [check_id for check_id, _ in watch.offsets] == [
            "stale-statutory-citation",
            "stale-statutory-citation",
        ]


class TestASourceWithNoWatchMetadataIsRefusedRatherThanSkipped:
    """A silently unwatched source and a watched, unchanged one print the same."""

    def _write(self, tmp_path: Path, entry: dict) -> Path:
        path = tmp_path / "SOURCES.json"
        path.write_text(json.dumps({"capitola": entry}), encoding="utf-8")
        return path

    def test_a_missing_watch_block_is_an_error(self, tmp_path):
        path = self._write(
            tmp_path,
            {
                "title": "t",
                "url": "https://x.invalid/a.html",
                "retrieved": "2026-01-01",
            },
        )
        with pytest.raises(ValueError, match="watch"):
            ordinance_watch.load_sources(path)

    def test_a_truncated_digest_is_an_error(self, tmp_path):
        """The `note` prose records 16-hex-character page hashes. Those describe
        bytes this repository does not keep, and one pasted in here would look
        like an integrity anchor while anchoring nothing."""
        path = self._write(
            tmp_path,
            {
                "title": "t",
                "url": "https://x.invalid/a.html",
                "retrieved": "2026-01-01",
                "watch": {"identifier": "17.74", "text_sha256": "e18b9056472bfdf5"},
            },
        )
        with pytest.raises(ValueError, match="64 lowercase hex"):
            ordinance_watch.load_sources(path)

    def test_a_media_type_with_no_extractor_is_an_error(self, tmp_path):
        path = self._write(
            tmp_path,
            {
                "title": "t",
                "url": "https://x.invalid/chapter.docx",
                "retrieved": "2026-01-01",
                "watch": {"identifier": "17.74", "text_sha256": "0" * 64},
            },
        )
        with pytest.raises(ValueError, match="no text extractor"):
            ordinance_watch.load_sources(path)


class TestTheCorpusIsHeldToItsOwnProvenance:
    def test_an_edited_text_fails_even_when_no_check_notices(self, tmp_path, checks):
        source = _source(tmp_path, text=STALE)
        # An edit far from any match: the published findings do not move, so
        # `scan_ordinances.py --check` stays green over it.
        (tmp_path / "capitola.txt").write_text(
            STALE + "\n\nAmended by Ord. 1099, 2026.", encoding="utf-8"
        )

        problems = ordinance_watch.corpus_problems({"capitola": source}, tmp_path)

        assert [p.slug for p in problems] == ["capitola"]
        assert "hashes" in problems[0].detail

    def test_an_identifier_absent_from_its_own_text_fails(self, tmp_path):
        source = _source(tmp_path, text=STALE, identifier="17.99")
        problems = ordinance_watch.corpus_problems({"capitola": source}, tmp_path)
        assert any("declared identifier" in p.detail for p in problems)

    def test_a_text_with_no_entry_and_an_entry_with_no_text_both_fail(self, tmp_path):
        source = _source(tmp_path, text=STALE)
        (tmp_path / "orphan.txt").write_text("nobody declared this", encoding="utf-8")
        (tmp_path / "capitola.txt").unlink()

        problems = {
            p.slug: p.detail
            for p in ordinance_watch.corpus_problems({"capitola": source}, tmp_path)
        }

        assert "no entry in SOURCES.json" in problems["orphan"]
        assert "no text at" in problems["capitola"]


class TestTheCommittedCorpusItself:
    def test_every_committed_ordinance_matches_its_recorded_provenance(self):
        sources = ordinance_watch.load_sources(CORPUS / "SOURCES.json")
        problems = ordinance_watch.corpus_problems(sources, CORPUS)
        assert not problems, [p.describe() for p in problems]

    def test_every_published_result_has_a_declared_source(self):
        sources = ordinance_watch.load_sources(CORPUS / "SOURCES.json")
        published = {p.stem for p in RESULTS.glob("*.json")} - {"index"}
        assert published == set(sources)

    def test_every_published_result_yields_readable_finding_counts(self):
        for path in sorted(RESULTS.glob("*.json")):
            if path.stem == "index":
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            counts = ordinance_watch.published_finding_counts(payload)
            assert sum(counts.values()) == len(payload["findings"])

    def test_a_published_result_with_an_unreadable_finding_is_refused(self):
        with pytest.raises(ValueError, match="check_id"):
            ordinance_watch.published_finding_counts({"findings": [{"title": "x"}]})

    def test_a_published_result_with_no_findings_list_is_refused(self):
        with pytest.raises(ValueError, match="findings list"):
            ordinance_watch.published_finding_counts({})


class TestTheCommandLineHoldsTheSameLine:
    """The exit codes a scheduled run acts on, exercised without a network."""

    def test_a_directory_with_no_bytes_is_unverifiable_and_never_a_change(
        self, tmp_path
    ):
        """The most dangerous run: nothing was read about seven ordinances.

        Exit 2 says so. Exit 0 would say every published finding still holds,
        and exit 3 would report seven amendments that nobody observed.
        """
        code, reports = watch_ordinances.run(from_dir=tmp_path)

        assert code == 2
        assert {r.status for r in reports} == {"unverifiable"}
        assert {r.kind for r in reports} == {"transport"}
        assert len(reports) == 7

    def test_a_changed_source_outranks_an_unreadable_one(self, tmp_path):
        """Both fired; the code has to be the one that names a stale claim."""
        sources = ordinance_watch.load_sources(CORPUS / "SOURCES.json")
        # One slug gets a page that is plainly its chapter and flags nothing.
        capitola = sources["capitola"]
        (tmp_path / f"capitola{capitola.suffix}").write_bytes(
            _page(f"Chapter {capitola.identifier}. Nothing objectionable here.")
        )

        code, reports = watch_ordinances.run(from_dir=tmp_path)

        by_slug = {r.slug: r for r in reports}
        assert by_slug["capitola"].status == "changed"
        assert {r.status for r in reports if r.slug != "capitola"} == {"unverifiable"}
        assert code == 3

    def test_a_not_found_is_not_retried_and_a_transport_failure_is(self, monkeypatch):
        """Asking a server twice more what it already answered only slows a run."""
        attempts: list[str] = []
        slept: list[float] = []

        def refuse(url: str) -> bytes:
            attempts.append(url)
            raise urllib.error.HTTPError(url, 404, "gone", None, None)  # type: ignore[arg-type]

        monkeypatch.setattr(watch_ordinances, "_fetch_once", refuse)
        payload, failure = watch_ordinances.fetch(
            "https://x.invalid/a.html", sleep=slept.append
        )
        assert (payload, failure) == (None, ("not_found", "HTTP 404"))
        assert len(attempts) == 1
        assert slept == []

        attempts.clear()

        def blip(url: str) -> bytes:
            attempts.append(url)
            raise TimeoutError("timed out")

        monkeypatch.setattr(watch_ordinances, "_fetch_once", blip)
        payload, failure = watch_ordinances.fetch(
            "https://x.invalid/a.html", attempts=3, sleep=slept.append
        )
        assert payload is None
        assert failure is not None and failure[0] == "transport"
        assert len(attempts) == 3
        assert slept == [2.0, 4.0]
