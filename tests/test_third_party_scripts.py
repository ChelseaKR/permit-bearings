"""Every third-party script the site may load is listed (SEC-43).

`third-party-scripts.json` at the repository root is the list. These tests hold
the public pages and the GA loader to it:

- the list itself is well formed: each entry names a vendor, a position and an
  absolute `src`, and its `sha256` is the digest of its `text`;
- the privacy page names every listed vendor;
- no public page loads a `<script src>` from a host that is not listed or
  first-party;
- the one script `assets/analytics.js` injects at runtime is the listed one, and
  the CSP `script-src` on every public page admits no host beyond the list.

The archived source copies under `corpus/` are not pages of this site: they are
the publishers' HTML kept byte for byte so citations can be re-verified, and
the site never links to them. They are out of scope here.

The negative controls at the end break one thing each and assert the check
sees it, so a check that silently matches nothing cannot read as a pass.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "third-party-scripts.json"
LOADER = ROOT / "assets" / "analytics.js"
PAGES = (
    "index.html",
    "check.html",
    "evidence.html",
    "prepare.html",
    "review.html",
    "privacy.html",
)
SCRIPT_SRC = re.compile(r"<script\b[^>]*?\bsrc\s*=\s*[\"']?([^\"'\s>]+)", re.IGNORECASE)
CSP = re.compile(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)"')


def _allowlist() -> dict[str, Any]:
    return json.loads(ALLOWLIST.read_text(encoding="utf-8"))


def _host(url: str) -> str | None:
    if url.startswith("//"):
        url = "https:" + url
    return (urlsplit(url).hostname or "").lower() or None


def _allowed_hosts(doc: dict[str, Any]) -> set[str]:
    hosts = {h.lower() for h in doc.get("first_party_hosts", [])}
    hosts |= {_host(s["src"]) for s in doc["scripts"] if s.get("src")} - {None}
    return hosts


def _stray_hosts(html: str, allowed: set[str]) -> set[str]:
    """Hosts a page loads script from that are neither listed nor relative."""
    stray = set()
    for src in SCRIPT_SRC.findall(html):
        host = _host(src) if re.match(r"(?:https?:)?//", src, re.IGNORECASE) else None
        if host is not None and host not in allowed:
            stray.add(host)
    return stray


def _injected_src(loader: str) -> str:
    """The URL assets/analytics.js builds for the script it appends."""
    base = re.search(r'var LOADER = "([^"]+)";', loader)
    ident = re.search(r'var GA4_ID = "([^"]*)";', loader)
    assert base and ident, "the loader no longer declares LOADER and GA4_ID"
    return base.group(1) + ident.group(1)


def test_every_entry_is_well_formed_and_its_digest_matches_its_text() -> None:
    doc = _allowlist()
    assert doc["scripts"], "the list is empty, but the GA loader injects a script"
    for script in doc["scripts"]:
        assert script["vendor"].strip()
        assert script["position"] in {"head", "body"}
        assert _host(script["src"]), script["src"]
        assert (
            hashlib.sha256(script["text"].encode("utf-8")).hexdigest()
            == script["sha256"]
        )
        assert f'src="{script["src"]}"' in script["text"]


def test_the_privacy_page_names_every_listed_vendor() -> None:
    doc = _allowlist()
    page = (ROOT / doc["privacy_page"]).read_text(encoding="utf-8").casefold()
    for script in doc["scripts"]:
        assert script["vendor"].casefold() in page, script["vendor"]


def test_no_public_page_loads_script_from_an_unlisted_host() -> None:
    allowed = _allowed_hosts(_allowlist())
    for page in PAGES:
        html = (ROOT / page).read_text(encoding="utf-8")
        assert SCRIPT_SRC.search(html), f"{page} has no <script src> to check"
        assert not _stray_hosts(html, allowed), page


def test_the_script_the_loader_injects_is_the_listed_one() -> None:
    listed = {s["src"] for s in _allowlist()["scripts"]}
    assert _injected_src(LOADER.read_text(encoding="utf-8")) in listed


def test_every_public_page_csp_admits_script_only_from_listed_hosts() -> None:
    allowed = _allowed_hosts(_allowlist())
    for page in PAGES:
        found = CSP.search((ROOT / page).read_text(encoding="utf-8"))
        assert found, f"{page} has no CSP"
        directive = next(
            (
                d.split()[1:]
                for d in found.group(1).split(";")
                if d.split()[:1] == ["script-src"]
            ),
            None,
        )
        assert directive is not None, f"{page} CSP has no script-src"
        for source in directive:
            if source.startswith("'"):
                assert source == "'self'", (page, source)
                continue
            assert _host(source) in allowed, (page, source)


# --- negative controls -----------------------------------------------------


def test_negative_control_an_unlisted_host_on_a_page_is_caught() -> None:
    allowed = _allowed_hosts(_allowlist())
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    tampered = html.replace(
        "</head>", '<script src="https://cdn.example.net/x.js"></script></head>', 1
    )
    assert tampered != html
    assert _stray_hosts(tampered, allowed) == {"cdn.example.net"}


def test_negative_control_a_changed_measurement_id_is_caught() -> None:
    loader = LOADER.read_text(encoding="utf-8")
    tampered = re.sub(r'var GA4_ID = "[^"]*";', 'var GA4_ID = "G-ZZZZZZZZ";', loader)
    assert tampered != loader
    listed = {s["src"] for s in _allowlist()["scripts"]}
    assert _injected_src(tampered) not in listed
