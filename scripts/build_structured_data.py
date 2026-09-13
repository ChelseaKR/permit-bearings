"""Write each static page's schema.org JSON-LD block from that page's own head.

The five public pages already carry a canonical URL, a title, a description, a
language and a social card, and `tests/test_static_demo.py` already holds them
to being self-consistent. A search engine could not read any of it as a typed
entity, so the site published no structured data at all.

This script does not introduce a second copy of those facts. It reads each
page's own `<html lang>`, `<title>`, `<meta name="description">`,
`<link rel="canonical">`, `<meta property="og:site_name">`,
`<meta property="og:image">` and the header's prototype label, and writes the
JSON-LD block from them. A value with no source in the page is omitted rather
than invented: there is no `applicationCategory`, no `offers`, no
`aggregateRating`, no author or publisher, because the repository holds no
reviewed source for any of them.

    python scripts/build_structured_data.py            # write
    python scripts/build_structured_data.py --check    # fail if a page is stale

`--check` is what `make bundle-check` runs;
`tests/test_static_demo.py::test_every_static_page_carries_its_own_structured_data`
parses the committed HTML and asserts the same agreement, so a page whose head
and whose JSON-LD have drifted apart fails in two places rather than none.

What is deliberately not emitted: nothing here describes `corpus/`, the
mirrored statute and CEQA text, or the rules derived from them. A `Dataset` or
`DataDownload` descriptor would invite dataset crawlers and open-data catalogues
to index an unofficial mirror of a government agency's documents as though it
were a published dataset, and a catalogue listing is far harder to withdraw than
a page. The nodes below describe the pages and the browser tool, and claim
nothing about official status, approval, or eligibility.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The schema.org type for each public page. `WebApplication` is claimed only by
# the three pages that run the browser tool; the other two are plain pages.
# Nothing here is a `GovernmentService`, a `LegalService`, or a `Dataset`: the
# prototype is not an eligibility determination and must not read as one.
PAGE_TYPES: dict[str, str] = {
    "index.html": "WebPage",
    "check.html": "WebApplication",
    "prepare.html": "WebApplication",
    "review.html": "WebApplication",
    "evidence.html": "WebPage",
}

# The page whose canonical URL is the site root, used for the `isPartOf` stub.
SITE_ROOT_PAGE = "index.html"

BLOCK_OPEN = '<script type="application/ld+json">'
BLOCK_CLOSE = "</script>"
HEAD_CLOSE = "</head>"


@dataclass(frozen=True)
class PageHead:
    """The facts a page already states about itself, read from its own head."""

    language: str
    title: str
    description: str
    canonical: str
    site_name: str
    image: str
    status: str


class _HeadReader(HTMLParser):
    """Collect the head facts with a real parser rather than a pattern match."""

    def __init__(self) -> None:
        super().__init__()
        self.language = ""
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.site_name = ""
        self.image = ""
        self.status = ""
        self._in_title = False
        self._in_status = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        if tag == "html":
            self.language = values.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self._read_meta(values)
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href", "")
        elif tag == "span" and "prototype-label" in values.get("class", "").split():
            self._in_status = True

    def _read_meta(self, values: dict[str, str]) -> None:
        if values.get("name") == "description":
            self.description = values.get("content", "")
        elif values.get("property") == "og:site_name":
            self.site_name = values.get("content", "")
        elif values.get("property") == "og:image":
            self.image = values.get("content", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "span":
            self._in_status = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_status:
            self.status += data


def read_head(html: str) -> PageHead:
    """Read one page's self-description out of its markup."""
    reader = _HeadReader()
    reader.feed(html)
    reader.close()
    head = PageHead(
        language=reader.language.strip(),
        title=reader.title.strip(),
        description=reader.description.strip(),
        canonical=reader.canonical.strip(),
        site_name=reader.site_name.strip(),
        image=reader.image.strip(),
        status=reader.status.strip(),
    )
    missing = [name for name, value in vars(head).items() if not value]
    if missing:
        raise ValueError(f"page states no {', '.join(missing)}")
    return head


def site_root_url() -> str:
    """The site's own root URL, taken from the landing page's canonical."""
    landing = (ROOT / SITE_ROOT_PAGE).read_text(encoding="utf-8")
    return read_head(landing).canonical


def build_node(name: str, head: PageHead, root_url: str) -> dict[str, object]:
    """Build the JSON-LD node for one page out of that page's own head."""
    node: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": PAGE_TYPES[name],
        "name": head.title,
        "description": head.description,
        "url": head.canonical,
        "inLanguage": head.language,
        "image": head.image,
        # The header labels every page a prototype; the markup says the same
        # rather than presenting the tool as finished work.
        "creativeWorkStatus": head.status,
        "isPartOf": {
            "@type": "WebSite",
            "name": head.site_name,
            "url": root_url,
        },
    }
    return node


def render_block(node: dict[str, object]) -> str:
    """Serialise a node as an embeddable JSON-LD block.

    `<` is escaped so no value can ever close the script element early; today no
    value contains one, which is exactly when the guard is cheap to add.
    """
    body = json.dumps(node, indent=2, ensure_ascii=False).replace("<", "\\u003c")
    return f"{BLOCK_OPEN}\n{body}\n{BLOCK_CLOSE}\n"


def strip_block(html: str) -> str:
    """Remove the generated block so regeneration is idempotent."""
    start = html.find(BLOCK_OPEN)
    if start == -1:
        return html
    end = html.index(BLOCK_CLOSE, start) + len(BLOCK_CLOSE)
    if html[end : end + 1] == "\n":
        end += 1
    return html[:start] + html[end:]


def render_page(name: str, root_url: str) -> str:
    """Return the full page with its JSON-LD block written from its own head."""
    path = ROOT / name
    original = path.read_text(encoding="utf-8")
    base = strip_block(original)
    head = read_head(base)
    block = render_block(build_node(name, head, root_url))
    cut = base.index(HEAD_CLOSE)
    return base[:cut] + block + base[cut:]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare instead of writing; exit 1 when a committed page is stale",
    )
    args = parser.parse_args(argv)

    root_url = site_root_url()
    stale: list[str] = []
    for name in sorted(PAGE_TYPES):
        rendered = render_page(name, root_url)
        path = ROOT / name
        if args.check:
            if path.read_text(encoding="utf-8") != rendered:
                stale.append(name)
            continue
        path.write_text(rendered, encoding="utf-8")
        print(f"wrote {name}")

    if args.check:
        if stale:
            print(
                "stale structured data: " + ", ".join(stale) + "\n"
                "regenerate with `python scripts/build_structured_data.py`",
                file=sys.stderr,
            )
            return 1
        print(f"structured data current ({len(PAGE_TYPES)} pages checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
