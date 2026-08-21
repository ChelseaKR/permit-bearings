"""Text index over the committed corpus, and the citation verifier.

The corpus is the evidence; the model is the narrator. This module turns the
documents that ``data/sources.json`` binds to ``corpus/`` into passages the
explanation prompt can offer, and — more importantly — verifies that a quote
the model claims to have taken from a source actually occurs in that source's
extracted text. Verification is a pure function over committed files; it does
not consult the model, the retrieval ranking, or the prompt.

Matching is deliberately tolerant of the ways extracted text differs from
what a model will reproduce (line breaks inside a PDF sentence, curly versus
straight quotes, section signs, soft hyphens, case) and deliberately strict
about content: after normalization the quote must occur verbatim and must be
long enough that a trivial phrase cannot pass as a citation.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

MIN_QUOTE_CHARS = 24
PASSAGE_TARGET_CHARS = 900
PASSAGE_MAX_CHARS = 1600
INDEXABLE_SUFFIXES = frozenset({".html", ".htm", ".txt", ".pdf"})

_BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "br",
        "li",
        "ul",
        "ol",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "tr",
        "td",
        "th",
        "table",
        "section",
        "article",
        "header",
        "footer",
        "blockquote",
        "pre",
    }
)
_SKIP_TAGS = frozenset({"script", "style", "noscript", "head", "title"})


class CorpusError(ValueError):
    """The corpus could not be indexed as committed."""


class _TextExtractor(HTMLParser):
    """Collect visible text, breaking lines at block-level tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    parser = _TextExtractor()
    parser.feed(markup)
    parser.close()
    return _tidy("".join(parser.parts))


def pdf_to_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise CorpusError(
            "PDF corpus documents need the `ai` extra (pypdf); "
            "install with `uv sync --extra ai`"
        ) from exc
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return _tidy("\n\n".join(pages))


def _tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return html_to_text(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".txt":
        return _tidy(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".pdf":
        return pdf_to_text(path)
    raise CorpusError(f"not an indexable text document: {path}")


_QUOTE_MAP = str.maketrans(
    {
        "\u2018": "'",  # left single quotation mark
        "\u2019": "'",  # right single quotation mark
        "\u201c": '"',  # left double quotation mark
        "\u201d": '"',  # right double quotation mark
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u00a0": " ",  # no-break space
        "\u00ad": "",  # soft hyphen
    }
)


def normalize_for_match(text: str) -> str:
    """Collapse text to the characters that carry meaning for a match.

    Unicode is NFKC-folded, typographic quotes and dashes become ASCII, case
    is folded, and every character that is not a letter, digit, or section
    sign is dropped. A quote that survives this and still occurs verbatim in
    a document said the same words in the same order.
    """
    text = unicodedata.normalize("NFKC", text).translate(_QUOTE_MAP).casefold()
    return "".join(ch for ch in text if ch.isalnum() or ch == "§")


@dataclass(frozen=True)
class Passage:
    passage_id: str
    source_id: str
    index: int
    text: str


@dataclass(frozen=True)
class CorpusDocument:
    source_id: str
    label: str
    url: str
    path: str
    text: str
    passages: tuple[Passage, ...]
    normalized: str

    @property
    def character_count(self) -> int:
        return len(self.text)


@dataclass(frozen=True)
class QuoteMatch:
    source_id: str
    quote: str
    passage_id: str | None
    offset: int


def split_passages(source_id: str, text: str) -> tuple[Passage, ...]:
    """Split document text into paragraph-bounded passages of bounded size."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > PASSAGE_MAX_CHARS:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long(paragraph))
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > PASSAGE_TARGET_CHARS and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return tuple(
        Passage(f"{source_id}#{index}", source_id, index, chunk)
        for index, chunk in enumerate(chunks)
    )


def _split_long(paragraph: str) -> list[str]:
    sentences = re.split(r"(?<=[.;:])\s+", paragraph)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > PASSAGE_TARGET_CHARS and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


class CorpusIndex:
    """Documents keyed by source ID, with a verifier for quoted text."""

    def __init__(self, documents: dict[str, CorpusDocument], skipped: dict[str, str]):
        self.documents = documents
        self.skipped = skipped

    @classmethod
    def load(cls, root: Path, *, sources_path: Path | None = None) -> CorpusIndex:
        sources_file = sources_path or root / "data" / "sources.json"
        try:
            registry: dict[str, dict[str, Any]] = json.loads(
                sources_file.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            raise CorpusError(
                f"cannot read source registry {sources_file}: {exc}"
            ) from exc
        documents: dict[str, CorpusDocument] = {}
        skipped: dict[str, str] = {}
        for url, entry in registry.items():
            source_id = str(entry.get("source_id", ""))
            local_copy = entry.get("local_copy")
            if not source_id:
                raise CorpusError(f"source registry entry for {url} has no source_id")
            if not local_copy:
                skipped[source_id] = "no local copy"
                continue
            path = root / str(local_copy)
            if path.suffix.lower() not in INDEXABLE_SUFFIXES:
                skipped[source_id] = f"not a text document ({path.suffix})"
                continue
            if not path.is_file():
                raise CorpusError(f"{source_id}: local copy missing at {path}")
            text = extract_text(path)
            documents[source_id] = CorpusDocument(
                source_id=source_id,
                label=str(entry.get("label", source_id)),
                url=url,
                path=str(local_copy),
                text=text,
                passages=split_passages(source_id, text),
                normalized=normalize_for_match(text),
            )
        return cls(documents, skipped)

    def passages_for(self, source_ids: list[str] | tuple[str, ...]) -> list[Passage]:
        passages: list[Passage] = []
        for source_id in source_ids:
            document = self.documents.get(source_id)
            if document:
                passages.extend(document.passages)
        return passages

    def passage(self, passage_id: str) -> Passage | None:
        source_id, _, index = passage_id.partition("#")
        document = self.documents.get(source_id)
        if not document or not index.isdigit():
            return None
        position = int(index)
        if position >= len(document.passages):
            return None
        return document.passages[position]

    def verify_quote(self, source_id: str, quote: str) -> QuoteMatch | None:
        """Return where ``quote`` occurs in the named source, or ``None``.

        The check runs against the whole extracted document, not against the
        passage the model was shown, so a quote that straddles a passage
        boundary still verifies and a passage ID alone can never vouch for
        text.
        """
        document = self.documents.get(source_id)
        if document is None:
            return None
        needle = normalize_for_match(quote)
        if len(needle) < MIN_QUOTE_CHARS:
            return None
        offset = document.normalized.find(needle)
        if offset < 0:
            return None
        passage_id = None
        for passage in document.passages:
            if needle in normalize_for_match(passage.text):
                passage_id = passage.passage_id
                break
        return QuoteMatch(source_id, quote, passage_id, offset)

    def locate_excerpt(self, source_id: str, excerpt: str) -> QuoteMatch | None:
        """Locate an editorially elided excerpt such as a rule's recorded
        citation text, which may contain ``[...]`` or bracketed insertions.

        Each fragment between brackets must occur verbatim, in order, in the
        document; the match reports where the first fragment occurs. This is
        used only to choose grounding passages from a rule's own excerpt; a
        model-produced quote is never matched this way.
        """
        document = self.documents.get(source_id)
        if document is None:
            return None
        fragments = [
            normalize_for_match(part)
            for part in re.split(r"\[[^\]]*\]", excerpt)
            if normalize_for_match(part)
        ]
        fragments = [f for f in fragments if len(f) >= 12]
        if not fragments:
            return None
        cursor = 0
        first = -1
        for fragment in fragments:
            offset = document.normalized.find(fragment, cursor)
            if offset < 0:
                return None
            if first < 0:
                first = offset
            cursor = offset + len(fragment)
        passage_id = None
        for passage in document.passages:
            if fragments[0] in normalize_for_match(passage.text):
                passage_id = passage.passage_id
                break
        return QuoteMatch(source_id, excerpt, passage_id, first)

    def summary(self) -> dict[str, Any]:
        return {
            "documents": {
                source_id: {
                    "label": doc.label,
                    "path": doc.path,
                    "characters": doc.character_count,
                    "passages": len(doc.passages),
                }
                for source_id, doc in sorted(self.documents.items())
            },
            "skipped": dict(sorted(self.skipped.items())),
        }
