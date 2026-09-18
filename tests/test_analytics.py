"""Google Analytics 4 on the public pages (ADR 0008).

`assets/analytics.js` is run under Node against a stubbed window, navigator,
document and localStorage, so these tests check what the loader does, not only
what its source says. The page tests check the six public pages load it once,
that their CSP admits exactly the GA origins, and that the footer control and
privacy page agree with the loader.

The negative controls at the end each break the loader in one place, assert the
break actually landed in the source they run, and then assert the harness sees
the difference. A sabotage that silently no-ops would otherwise read as a pass.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "assets" / "analytics.js"
PAGES = (
    "index.html",
    "check.html",
    "evidence.html",
    "prepare.html",
    "review.html",
    "privacy.html",
)
MEASUREMENT_ID = "G-9FJBLEN2ZJ"
ID_LINE = f'var GA4_ID = "{MEASUREMENT_ID}";'
OPT_OUT_KEY = "permit-bearings:analytics-opt-out"
PRODUCTION = "https://chelseakr.github.io/permit-bearings/check.html?sample=adu#results"
GA_ORIGINS = {
    "script-src": {"https://www.googletagmanager.com"},
    "connect-src": {
        "https://*.google-analytics.com",
        "https://*.analytics.google.com",
        "https://www.googletagmanager.com",
    },
    "img-src": {
        "https://*.google-analytics.com",
        "https://www.googletagmanager.com",
    },
}
CONSENT_REQUIRED = [
    *("AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR"),
    *("HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI"),
    *("SK", "IS", "LI", "NO", "GB", "CH"),
]

needs_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js unavailable"
)

HARNESS = r"""
import vm from "node:vm";
const { source, scenario: s } = JSON.parse(process.env.ANALYTICS_HARNESS_PAYLOAD);
const appended = [];
const documentListeners = {};
const data = new Map(Object.entries(s.storage || {}));
const storage = {
  getItem(key) { return data.has(key) ? data.get(key) : null; },
  setItem(key, value) { data.set(key, String(value)); },
  removeItem(key) { data.delete(key); },
};
const button = {
  textContent: "Opt out of analytics",
  hidden: false,
  listeners: {},
  addEventListener(type, handler) { this.listeners[type] = handler; },
};
const status = { textContent: "" };
const box = {
  hidden: true,
  querySelector(selector) {
    if (selector === "button") return button;
    if (selector === "[role=status]") return status;
    return null;
  },
};
const document = {
  readyState: s.readyState || "loading",
  referrer: s.referrer || "",
  head: { appendChild(element) { appended.push(element); } },
  documentElement: { appendChild(element) { appended.push(element); } },
  createElement(tag) { return { tagName: tag.toUpperCase() }; },
  querySelector(selector) {
    return selector === "[data-analytics-choice]" ? box : null;
  },
  addEventListener(type, handler) {
    (documentListeners[type] = documentListeners[type] || []).push(handler);
  },
};
const url = new URL(s.url);
const navigator = {
  globalPrivacyControl: s.gpc,
  doNotTrack: s.dnt,
  msDoNotTrack: s.msDnt,
};
const window = {
  navigator,
  doNotTrack: s.windowDnt,
  location: {
    protocol: url.protocol,
    hostname: url.hostname,
    pathname: url.pathname,
    origin: url.origin,
    href: url.href,
    search: url.search,
    hash: url.hash,
  },
};
Object.defineProperty(window, "localStorage", {
  get() {
    if (s.storageThrows) throw new Error("SecurityError");
    return storage;
  },
});
const context = vm.createContext({ window, navigator, document, URL, Date });
vm.runInContext(source, context);
for (const handler of documentListeners.DOMContentLoaded || []) handler();
for (let index = 0; index < (s.clicks || 0); index += 1) button.listeners.click();
const disableKeys = Object.keys(window).filter(key => key.startsWith("ga-disable-"));
console.log(JSON.stringify({
  dataLayer: window.dataLayer === undefined
    ? null
    : window.dataLayer.map(args => Array.from(args).map(
      value => value instanceof Date ? "<date>" : value,
    )),
  scripts: appended.map(element => ({
    tag: element.tagName, src: element.src, async: element.async,
  })),
  wired: Boolean(button.listeners.click),
  control: {
    boxHidden: box.hidden,
    buttonHidden: button.hidden,
    text: button.textContent,
    status: status.textContent,
  },
  storage: Object.fromEntries(data),
  gaDisable: Object.fromEntries(disableKeys.map(key => [key, window[key]])),
}));
"""


def run_loader(source: str | None = None, **scenario: Any) -> dict[str, Any]:
    """Run the loader once in Node and report what it did."""
    scenario.setdefault("url", PRODUCTION)
    payload = json.dumps(
        {
            "source": LOADER.read_text(encoding="utf-8") if source is None else source,
            "scenario": scenario,
        }
    )
    completed = subprocess.run(
        ["node", "--input-type=module"],
        input=HARNESS,
        env={**os.environ, "ANALYTICS_HARNESS_PAYLOAD": payload},
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    result: dict[str, Any] = json.loads(completed.stdout)
    return result


def loaded(result: dict[str, Any]) -> bool:
    return result["dataLayer"] is not None or bool(result["scripts"])


def sabotaged(old: str, new: str) -> str:
    """The loader with `old` replaced once, after asserting the edit landed."""
    source = LOADER.read_text(encoding="utf-8")
    assert source.count(old) == 1, f"sabotage marker not found exactly once: {old!r}"
    changed = source.replace(old, new)
    assert changed != source
    assert old not in changed or old in new
    return changed


# --- what the loader does ---------------------------------------------------


@needs_node
def test_production_loads_gtag_once_with_the_consent_defaults_and_config() -> None:
    result = run_loader(referrer="https://www.google.com/search?q=adu+permit+davis")

    assert result["scripts"] == [
        {
            "tag": "SCRIPT",
            "src": f"https://www.googletagmanager.com/gtag/js?id={MEASUREMENT_ID}",
            "async": True,
        }
    ]
    advertising_denied = {
        "ad_storage": "denied",
        "ad_user_data": "denied",
        "ad_personalization": "denied",
    }
    assert result["dataLayer"] == [
        [
            "consent",
            "default",
            {
                **advertising_denied,
                "analytics_storage": "denied",
                "region": CONSENT_REQUIRED,
            },
        ],
        ["consent", "default", {**advertising_denied, "analytics_storage": "granted"}],
        ["js", "<date>"],
        [
            "config",
            MEASUREMENT_ID,
            {
                "allow_google_signals": False,
                "allow_ad_personalization_signals": False,
                # Origin and path only: the query string and the fragment of
                # the address the visitor is on never reach Google.
                "page_location": "https://chelseakr.github.io/permit-bearings/check.html",
                # The referring site's origin only, never its search terms.
                "page_referrer": "https://www.google.com/",
            },
        ],
    ]
    assert len(CONSENT_REQUIRED) == len(set(CONSENT_REQUIRED)) == 32


@needs_node
def test_page_location_and_referrer_never_carry_a_query_or_fragment() -> None:
    result = run_loader(
        url="https://chelseakr.github.io/permit-bearings/prepare.html"
        "?journey=woodland-preapproved-detached-adu-synthetic&version=1.0.0#cover",
        referrer="https://example.org/some/path?secret=1#frag",
    )
    config = result["dataLayer"][3][2]
    assert config["page_location"] == (
        "https://chelseakr.github.io/permit-bearings/prepare.html"
    )
    assert config["page_referrer"] == "https://example.org/"
    serialized = json.dumps(result["dataLayer"])
    for leaked in ("journey=", "version=", "#cover", "secret", "/some/path"):
        assert leaked not in serialized


@needs_node
def test_no_referrer_is_sent_as_an_empty_referrer() -> None:
    result = run_loader(referrer="")
    assert result["dataLayer"][3][2]["page_referrer"] == ""


@needs_node
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:4174/index.html",
        "http://localhost:8000/check.html",
        "http://chelseakr.github.io/permit-bearings/",
        "https://chelseakr.github.io/another-project/",
        "https://chelseakr.github.io/permit-bearings-copy/",
        "https://chelseakr.github.io/",
        "https://permit-bearings.example.org/permit-bearings/",
    ],
)
def test_nothing_loads_off_the_production_host_and_path(url: str) -> None:
    result = run_loader(url=url)
    assert not loaded(result)
    assert result["dataLayer"] is None
    assert result["scripts"] == []


@needs_node
@pytest.mark.parametrize(
    "signal",
    [
        {"gpc": True},
        {"dnt": "1"},
        {"dnt": "yes"},
        {"windowDnt": "1"},
        {"msDnt": "1"},
        {"gpc": True, "dnt": "1"},
    ],
    ids=["gpc", "dnt", "dnt-yes", "window-dnt", "ms-dnt", "gpc-and-dnt"],
)
def test_gpc_or_dnt_stops_ga_before_anything_loads(signal: dict[str, Any]) -> None:
    result = run_loader(**signal)
    assert not loaded(result)
    # The footer control says why instead of offering a choice that does
    # nothing.
    assert result["control"]["boxHidden"] is False
    assert result["control"]["buttonHidden"] is True
    assert "Global Privacy Control or Do Not Track" in result["control"]["status"]


@needs_node
@pytest.mark.parametrize(
    "signal",
    [{"gpc": False}, {"dnt": "0"}, {"dnt": "unspecified"}, {"windowDnt": "0"}],
)
def test_signals_that_are_off_do_not_stop_ga(signal: dict[str, Any]) -> None:
    assert loaded(run_loader(**signal))


@needs_node
def test_the_opt_out_flag_stops_ga_from_loading() -> None:
    result = run_loader(storage={OPT_OUT_KEY: "1"})
    assert not loaded(result)
    assert result["control"]["text"] == "Opt back in"
    assert result["control"]["buttonHidden"] is False
    assert result["control"]["status"].startswith("You have opted out")


@needs_node
@pytest.mark.parametrize(
    "storage",
    [
        {OPT_OUT_KEY: "0"},
        {OPT_OUT_KEY: "true"},
        {"another-site:analytics-opt-out": "1"},
    ],
)
def test_only_the_exact_flag_opts_out(storage: dict[str, str]) -> None:
    assert loaded(run_loader(storage=storage))


@needs_node
def test_the_control_toggles_the_flag_both_ways() -> None:
    once = run_loader(clicks=1)
    assert once["storage"] == {OPT_OUT_KEY: "1"}
    assert once["gaDisable"] == {f"ga-disable-{MEASUREMENT_ID}": True}
    assert once["control"]["text"] == "Opt back in"
    assert once["control"]["status"].startswith("Opted out.")

    twice = run_loader(clicks=2)
    assert twice["storage"] == {}
    assert twice["gaDisable"] == {f"ga-disable-{MEASUREMENT_ID}": False}
    assert twice["control"]["text"] == "Opt out of analytics"
    assert twice["control"]["status"].startswith("Opted back in.")


@needs_node
def test_blocked_storage_hides_the_control_and_says_why() -> None:
    result = run_loader(storageThrows=True)
    assert result["control"]["buttonHidden"] is True
    assert "blocking site storage" in result["control"]["status"]
    # Nothing is opted out, and GPC/DNT still work, so GA itself still runs.
    assert loaded(result)


@needs_node
def test_the_control_is_wired_on_local_hosts_without_loading_ga() -> None:
    """The accessibility runs on 127.0.0.1 check the real, visible button."""
    result = run_loader(url="http://127.0.0.1:4174/index.html", clicks=1)
    assert result["wired"] is True
    assert result["control"]["boxHidden"] is False
    assert result["storage"] == {OPT_OUT_KEY: "1"}
    assert not loaded(result)


@needs_node
def test_a_deferred_run_after_parsing_still_wires_the_control() -> None:
    result = run_loader(readyState="interactive")
    assert result["wired"] is True
    assert result["control"]["boxHidden"] is False


@needs_node
@pytest.mark.parametrize(
    "value", ["", "UA-12345-1", 'G-ABC"+alert(1)+"', "g-9fjblen2zj"]
)
def test_no_or_malformed_id_loads_nothing_and_offers_no_control(value: str) -> None:
    source = sabotaged(ID_LINE, f"var GA4_ID = {json.dumps(value)};")
    result = run_loader(source)
    assert not loaded(result)
    assert result["wired"] is False
    assert result["control"]["boxHidden"] is True


# --- the pages ---------------------------------------------------------------


def _csp(html: str) -> dict[str, list[str]]:
    found = re.search(
        r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', html
    )
    assert found
    directives: dict[str, list[str]] = {}
    for part in found.group(1).split(";"):
        name, *values = part.split()
        directives[name] = values
    return directives


def test_every_public_page_loads_the_loader_once_in_its_head() -> None:
    versions = set()
    for page in PAGES:
        html = (ROOT / page).read_text(encoding="utf-8")
        tags = re.findall(
            r'<script src="assets/analytics\.js\?v=([a-zA-Z0-9]+)" defer></script>',
            html,
        )
        assert len(tags) == 1, page
        versions.add(tags[0])
        assert html.index("assets/analytics.js") < html.index("</head>"), page
        # The CSP forbids inline script, and nothing else may load Google.
        assert re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html) is None, page
        body = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]+>', "", html)
        assert "googletagmanager" not in body, page
        assert "google-analytics" not in body, page
    assert len(versions) == 1


def test_every_public_page_csp_admits_exactly_the_ga_origins() -> None:
    for page in PAGES:
        directives = _csp((ROOT / page).read_text(encoding="utf-8"))
        for directive, origins in GA_ORIGINS.items():
            values = set(directives[directive])
            assert origins <= values, (page, directive)
            google = {v for v in values if "google" in v}
            assert google == origins, (page, directive, google)
        assert directives["default-src"] == ["'self'"], page
        assert directives["script-src"] == [
            "'self'",
            "https://www.googletagmanager.com",
        ]


def test_only_the_loader_names_google_among_the_shipped_scripts() -> None:
    for path in [*(ROOT / "assets").glob("*.js"), *(ROOT / "data").glob("*.js")]:
        text = path.read_text(encoding="utf-8")
        if path == LOADER:
            assert text.count("googletagmanager.com/gtag/js") == 1
            continue
        assert "googletagmanager" not in text, path
        assert "gtag(" not in text, path


def test_every_public_page_has_one_hidden_footer_control_and_a_privacy_link() -> None:
    for page in PAGES:
        html = (ROOT / page).read_text(encoding="utf-8")
        footer = html[
            html.index('<footer class="site-footer">') : html.index("</footer>")
        ]
        assert html.count("data-analytics-choice") == 1, page
        assert (
            '<div class="analytics-choice" data-analytics-choice hidden>\n'
            '      <button type="button" class="link-button ca-button">'
            "Opt out of analytics</button>\n"
            '      <span role="status"></span>\n'
            "    </div>"
        ) in footer, page
        if page != "privacy.html":
            assert '<a href="privacy.html">Privacy and analytics</a>' in footer, page


def test_the_privacy_page_matches_the_loader() -> None:
    loader = LOADER.read_text(encoding="utf-8")
    privacy = (ROOT / "privacy.html").read_text(encoding="utf-8")
    text = re.sub(r"\s+", " ", privacy)

    assert ID_LINE in loader
    assert f'var OPT_OUT_KEY = "{OPT_OUT_KEY}";' in loader
    assert f"<code>{OPT_OUT_KEY}</code>" in text
    assert f"<code>_ga_{MEASUREMENT_ID.removeprefix('G-')}</code>" in text
    for claim in (
        "Google Analytics 4, a service of Google LLC in the United States",
        "with everything after a <code>?</code> or <code>#</code> removed",
        "Google Analytics never receives your project answers, pasted text",
        "Google signals and ad personalization are turned off.",
        "Google keeps this data for 14 months.",
        "the United Kingdom, and Switzerland, analytics storage is denied",
        "does not load if your browser sends Global Privacy Control or Do Not Track",
        "Opting out does not delete Google Analytics cookies that were already set.",
    ):
        assert claim in text, claim


def test_no_public_copy_still_says_the_site_does_not_track() -> None:
    public = [
        *(ROOT / page for page in PAGES),
        ROOT / "README.md",
        ROOT / "SECURITY.md",
    ]
    for path in public:
        text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8")).lower()
        for claim in ("no tracking", "no analytics", "no-telemetry", "no cookies"):
            assert claim not in text, (path.name, claim)


# --- negative controls -------------------------------------------------------


@needs_node
@pytest.mark.parametrize(
    ("old", "new", "scenario"),
    [
        ("  if (signal) return;\n", "", {"gpc": True}),
        ("  if (signal) return;\n", "", {"dnt": "1"}),
        ("  if (optedOut()) return;\n", "", {"storage": {OPT_OUT_KEY: "1"}}),
        (
            '  if (loc.protocol !== "https:" || loc.hostname !== PRODUCTION_HOST) return;\n',
            "",
            # The path matches, so only the host/scheme guard stands in the way.
            {"url": "http://127.0.0.1:4174/permit-bearings/index.html"},
        ),
        (
            "  if (loc.pathname.indexOf(PRODUCTION_PATH) !== 0) return;\n",
            "",
            {"url": "https://chelseakr.github.io/another-project/"},
        ),
    ],
    ids=["gpc-guard", "dnt-guard", "opt-out-guard", "host-guard", "path-guard"],
)
def test_negative_control_each_removed_guard_lets_ga_load(
    old: str, new: str, scenario: dict[str, Any]
) -> None:
    assert not loaded(run_loader(**scenario))
    assert loaded(run_loader(sabotaged(old, new), **scenario))


@needs_node
def test_negative_control_a_full_page_location_is_caught() -> None:
    source = sabotaged(
        "page_location: loc.origin + loc.pathname,", "page_location: loc.href,"
    )
    config = run_loader(source)["dataLayer"][3][2]
    assert config["page_location"].endswith("?sample=adu#results")


@needs_node
def test_negative_control_signals_turned_on_is_caught() -> None:
    source = sabotaged("allow_google_signals: false,", "allow_google_signals: true,")
    config = run_loader(source)["dataLayer"][3][2]
    assert config["allow_google_signals"] is True


@needs_node
def test_negative_control_a_dropped_set_item_is_caught() -> None:
    source = sabotaged('store.setItem(OPT_OUT_KEY, "1");', "")
    assert run_loader(source, clicks=1)["storage"] == {}
