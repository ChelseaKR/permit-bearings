"""Corpus text index, passage splitting, and the citation verifier."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from permit_pathways.ai import corpus as corpus_module
from permit_pathways.ai.corpus import (
    MIN_QUOTE_CHARS,
    CorpusError,
    CorpusIndex,
    extract_text,
    html_to_text,
    normalize_for_match,
    split_passages,
)
from permit_pathways.ai.retrieval import rank_passages, tokenize

ROOT = Path(__file__).resolve().parents[1]

STATUTE = """
<html><head><title>ignored title</title><style>p{}</style></head><body>
<script>var token = "per-request";</script>
<div><p>66317. (a) A permit application for an accessory dwelling unit shall be
considered and approved ministerially without discretionary review.</p>
<p>(b) The permitting agency shall act within 60 days.</p></div>
</body></html>
"""


def _write_corpus(
    tmp_path: Path, *, extra: dict[str, dict[str, object]] | None = None
) -> Path:
    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus" / "statute.html").write_text(STATUTE, encoding="utf-8")
    (tmp_path / "corpus" / "handout.txt").write_text(
        "First paragraph about accessory dwelling units and parking.\n\n"
        "Second paragraph: height limits of 16 feet apply to detached units.\n\n"
        + "\n\n".join(
            f"Filler paragraph number {i} about nothing in particular."
            for i in range(40)
        ),
        encoding="utf-8",
    )
    (tmp_path / "corpus" / "layer.json").write_text("{}", encoding="utf-8")
    sources = {
        "https://example.test/statute": {
            "source_id": "statute",
            "label": "Statute",
            "local_copy": "corpus/statute.html",
            "sha256": "0" * 64,
            "fetched_on": "2026-01-01",
            "normalize": "html-text",
        },
        "https://example.test/handout": {
            "source_id": "handout",
            "label": "Handout",
            "local_copy": "corpus/handout.txt",
            "sha256": "0" * 64,
            "fetched_on": "2026-01-01",
        },
        "https://example.test/absent": {
            "source_id": "absent",
            "label": "No copy",
            "local_copy": None,
            "sha256": "0" * 64,
            "fetched_on": "2026-01-01",
        },
        "https://example.test/layer": {
            "source_id": "layer",
            "label": "Parcel layer",
            "local_copy": "corpus/layer.json",
            "sha256": "0" * 64,
            "fetched_on": "2026-01-01",
        },
    }
    sources.update(extra or {})
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "sources.json").write_text(
        json.dumps(sources), encoding="utf-8"
    )
    return tmp_path


def test_html_to_text_drops_scripts_styles_and_title_but_keeps_blocks() -> None:
    text = html_to_text(STATUTE)
    assert "per-request" not in text
    assert "ignored title" not in text
    assert "p{}" not in text
    assert text.startswith("66317. (a) A permit application")
    assert "\n(b) The permitting agency" in text


def test_normalize_for_match_folds_typography_case_and_whitespace() -> None:
    left = normalize_for_match("“Accessory—dwelling”  UNIT,\nsection § 66317")
    right = normalize_for_match('"accessory-dwelling" unit, section §66317')
    assert left == right
    assert "§" in left


def test_split_passages_bounds_size_and_numbers_in_order() -> None:
    paragraphs = "\n\n".join(f"Paragraph {i}. " + ("word " * 120) for i in range(6))
    passages = split_passages("doc", paragraphs)
    assert [p.index for p in passages] == list(range(len(passages)))
    assert all(p.passage_id == f"doc#{p.index}" for p in passages)
    assert all(len(p.text) <= corpus_module.PASSAGE_MAX_CHARS for p in passages)
    long_paragraph = "Sentence one is here. " * 120
    long_passages = split_passages("long", long_paragraph)
    assert len(long_passages) > 1
    assert all(len(p.text) <= corpus_module.PASSAGE_MAX_CHARS for p in long_passages)


def test_index_loads_text_documents_and_reports_skips(tmp_path: Path) -> None:
    index = CorpusIndex.load(_write_corpus(tmp_path))
    assert set(index.documents) == {"statute", "handout"}
    assert index.skipped == {
        "absent": "no local copy",
        "layer": "not a text document (.json)",
    }
    summary = index.summary()
    assert summary["documents"]["statute"]["passages"] >= 1
    assert summary["skipped"]["absent"] == "no local copy"
    assert index.documents["statute"].url == "https://example.test/statute"


def test_verify_quote_accepts_verbatim_text_across_line_breaks(tmp_path: Path) -> None:
    index = CorpusIndex.load(_write_corpus(tmp_path))
    match = index.verify_quote(
        "statute",
        "shall be considered and approved ministerially without discretionary review",
    )
    assert match is not None
    assert match.passage_id == "statute#0"
    assert match.offset >= 0


def test_verify_quote_rejects_altered_short_or_foreign_text(tmp_path: Path) -> None:
    index = CorpusIndex.load(_write_corpus(tmp_path))
    assert (
        index.verify_quote(
            "statute", "shall be considered and DENIED ministerially without review"
        )
        is None
    )
    assert index.verify_quote("statute", "approved ministerially") is None  # too short
    assert len(normalize_for_match("approved ministerially")) < MIN_QUOTE_CHARS
    assert (
        index.verify_quote(
            "handout",
            "shall be considered and approved ministerially without discretionary review",
        )
        is None
    )
    assert (
        index.verify_quote(
            "missing",
            "shall be considered and approved ministerially without discretionary review",
        )
        is None
    )


def test_locate_excerpt_tolerates_bracketed_elisions_in_order(tmp_path: Path) -> None:
    index = CorpusIndex.load(_write_corpus(tmp_path))
    located = index.locate_excerpt(
        "statute",
        "A permit application for an accessory dwelling unit [...] approved ministerially [must] without discretionary review",
    )
    assert located is not None and located.passage_id == "statute#0"
    assert (
        index.locate_excerpt(
            "statute",
            "without discretionary review [...] A permit application for an accessory",
        )
        is None
    )
    assert index.locate_excerpt("statute", "[short]") is None
    assert (
        index.locate_excerpt(
            "nope", "A permit application for an accessory dwelling unit"
        )
        is None
    )


def test_passage_lookup_and_scoped_passages(tmp_path: Path) -> None:
    index = CorpusIndex.load(_write_corpus(tmp_path))
    assert index.passage("statute#0") is not None
    assert index.passage("statute#99") is None
    assert index.passage("statute#x") is None
    assert index.passage("unknown#0") is None
    scoped = index.passages_for(["handout", "absent"])
    assert scoped and all(p.source_id == "handout" for p in scoped)


def test_index_fails_closed_on_missing_copy_or_bad_registry(tmp_path: Path) -> None:
    root = _write_corpus(
        tmp_path,
        extra={
            "https://example.test/ghost": {
                "source_id": "ghost",
                "label": "Ghost",
                "local_copy": "corpus/ghost.txt",
                "sha256": "0" * 64,
                "fetched_on": "2026-01-01",
            }
        },
    )
    with pytest.raises(CorpusError, match="ghost"):
        CorpusIndex.load(root)
    with pytest.raises(CorpusError, match="cannot read"):
        CorpusIndex.load(tmp_path, sources_path=tmp_path / "nope.json")
    (tmp_path / "data" / "sources.json").write_text(
        json.dumps({"https://x": {"local_copy": "corpus/statute.html"}}),
        encoding="utf-8",
    )
    with pytest.raises(CorpusError, match="no source_id"):
        CorpusIndex.load(tmp_path)


def test_extract_text_rejects_unknown_suffix(tmp_path: Path) -> None:
    path = tmp_path / "thing.zip"
    path.write_bytes(b"")
    with pytest.raises(CorpusError, match="not an indexable"):
        extract_text(path)


def test_committed_corpus_indexes_every_text_source() -> None:
    index = CorpusIndex.load(ROOT)
    registry = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    expected = {
        entry["source_id"]
        for entry in registry.values()
        if entry.get("local_copy")
        and Path(entry["local_copy"]).suffix in {".html", ".txt", ".pdf"}
    }
    assert set(index.documents) == expected
    assert all(doc.character_count > 500 for doc in index.documents.values())
    assert index.documents["hcd-adu-handbook-2026-03"].character_count > 100_000


def test_retrieval_ranks_matching_passages_first(tmp_path: Path) -> None:
    index = CorpusIndex.load(_write_corpus(tmp_path))
    passages = index.passages_for(["handout", "statute"])
    ranked = rank_passages("height limits for detached units of 16 feet", passages, 3)
    assert ranked and ranked[0].passage.source_id == "handout"
    assert "16 feet" in ranked[0].passage.text
    assert rank_passages("", passages, 3) == []
    assert rank_passages("height", passages, 0) == []
    assert rank_passages("zzzz qqqq", passages, 3) == []
    assert tokenize("The § 66317(a) deadline is 60 days") == [
        "§",
        "66317",
        "deadline",
        "60",
        "days",
    ]
