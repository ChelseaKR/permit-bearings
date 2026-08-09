"""Contracts for the California Design System component-alignment layer.

These checks deliberately distinguish component alignment from State branding.
Permit Bearings can reuse the published design primitives without presenting the
independent prototype as an official State of California service.
"""

import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar

from demo.app import intake_form

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PAGES = (
    "index.html",
    "check.html",
    "prepare.html",
    "review.html",
    "evidence.html",
)


class _MarkupInventory(HTMLParser):
    """Collect the small amount of structural information these tests need."""

    _VOID_ELEMENTS: ClassVar[set[str]] = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.tags: Counter[str] = Counter()
        self.ids: dict[str, tuple[str, dict[str, str]]] = {}
        self.controls: list[tuple[str, str | None, bool]] = []
        self.buttons: list[tuple[str, str | None, set[str]]] = []
        self.tables: list[set[str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        classes = set(attributes.get("class", "").split())
        element_id = attributes.get("id") or None

        self.tags[tag] += 1
        if element_id:
            self.ids[element_id] = (tag, attributes)

        if tag in {"input", "select", "textarea"}:
            input_type = attributes.get("type", "").lower()
            if input_type != "hidden":
                self.controls.append((tag, element_id, "ca-field" in self.stack))

        if tag == "button" or (tag == "a" and "button" in classes):
            self.buttons.append((tag, element_id, classes))

        if tag == "table":
            self.tables.append(classes)

        if tag not in self._VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self._VOID_ELEMENTS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag not in self.stack:
            return
        reverse_index = self.stack[::-1].index(tag)
        del self.stack[len(self.stack) - reverse_index - 1 :]


def _page(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _inventory(name: str) -> _MarkupInventory:
    inventory = _MarkupInventory()
    inventory.feed(_page(name))
    return inventory


def test_every_public_page_loads_the_local_california_component_layer_first():
    component_asset = ROOT / "assets" / "california-design-system.css"
    assert component_asset.is_file()

    for page_name in PUBLIC_PAGES:
        markup = _page(page_name)
        component_link = re.search(
            r'<link rel="stylesheet" '
            r'href="assets/california-design-system\.css(?:\?v=[a-zA-Z0-9]+)?">',
            markup,
        )
        product_link = re.search(
            r'<link rel="stylesheet" '
            r'href="assets/site\.css(?:\?v=[a-zA-Z0-9]+)?">',
            markup,
        )
        assert component_link, page_name
        assert product_link, page_name
        assert component_link.start() < product_link.start(), page_name


def test_local_component_layer_exposes_the_adopted_california_primitives():
    css = (ROOT / "assets" / "california-design-system.css").read_text(encoding="utf-8")

    for selector in (
        ".ca-button",
        "ca-field",
        ".ca-field",
        "ca-shout",
        ".ca-shout",
        "ca-box",
        ".ca-box",
        "ca-mesh",
        "ca-card",
        ".ca-card",
        "table.ca-inner-border",
        "table.ca-outer-border",
        "table.ca-stripes",
    ):
        assert re.search(rf"{re.escape(selector)}[^{{]*\{{", css), selector


def test_skip_link_keeps_the_california_component_id_and_main_target():
    for page_name in PUBLIC_PAGES:
        markup = _page(page_name)
        inventory = _inventory(page_name)
        assert "skip-to-content" in inventory.ids, page_name
        tag, _ = inventory.ids["skip-to-content"]
        assert tag == "div", page_name
        assert re.search(
            r'<div[^>]*\bid="skip-to-content"[^>]*>\s*'
            r'<a[^>]*\bhref="#mainContent"',
            markup,
        ), page_name
        assert "mainContent" in inventory.ids, page_name


def test_static_form_controls_are_inside_ca_field_components():
    controls_seen = 0
    for page_name in PUBLIC_PAGES:
        inventory = _inventory(page_name)
        controls_seen += len(inventory.controls)
        for tag, element_id, inside_ca_field in inventory.controls:
            assert inside_ca_field, (page_name, tag, element_id)
    assert controls_seen > 0


def test_static_button_patterns_add_ca_button_without_losing_product_hooks():
    buttons_seen = 0
    for page_name in PUBLIC_PAGES:
        inventory = _inventory(page_name)
        buttons_seen += len(inventory.buttons)
        for tag, element_id, classes in inventory.buttons:
            assert "ca-button" in classes, (page_name, tag, element_id)

    assert buttons_seen > 0

    expected_legacy_classes = {
        ("check.html", "langToggle"): {"nav-button", "ghost"},
        ("prepare.html", "printJourneySummary"): {"button"},
        ("review.html", "loadSample"): {"link-button"},
        ("evidence.html", "simBtn"): {"ghost"},
        ("evidence.html", "resetBtn"): {"ghost", "hidden"},
    }
    for (page_name, element_id), expected in expected_legacy_classes.items():
        inventory = _inventory(page_name)
        matching = [
            classes
            for _, candidate_id, classes in inventory.buttons
            if candidate_id == element_id
        ]
        assert len(matching) == 1, (page_name, element_id)
        assert expected <= matching[0], (page_name, element_id)
        assert "ca-button" in matching[0], (page_name, element_id)


def test_home_page_uses_california_layout_components_for_bounded_content():
    inventory = _inventory("index.html")
    assert inventory.tags["ca-mesh"] >= 1
    assert inventory.tags["ca-card"] >= 1


def test_evidence_tables_use_current_california_table_utilities():
    inventory = _inventory("evidence.html")
    assert len(inventory.tables) == 2
    required = {"ca-inner-border", "ca-outer-border", "ca-stripes"}
    for classes in inventory.tables:
        assert required <= classes


def test_static_pages_use_shout_or_box_components_for_notices():
    inventories = [_inventory(name) for name in PUBLIC_PAGES]
    assert sum(item.tags["ca-shout"] for item in inventories) >= 1
    assert sum(item.tags["ca-box"] for item in inventories) >= 1


def test_dynamic_markup_emits_additive_california_component_hooks():
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")

    for component_class in (
        "ca-field",
        "ca-button",
        "ca-shout",
        "ca-box",
        "ca-card",
    ):
        assert re.search(
            rf'class="[^"]*\b{re.escape(component_class)}\b[^"]*"',
            application,
        ), component_class

    # The migration adds styling hooks without replacing resilient native
    # disclosure and grouping semantics with JavaScript-dependent widgets.
    assert '<details class="rule-details"' in application
    assert "<ca-accordion" not in application


def test_product_typography_no_longer_uses_a_separate_serif_display_stack():
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    display = re.search(r"--display\s*:\s*([^;]+);", css)
    assert display
    display_value = display.group(1).lower().replace("sans-serif", "")
    assert "serif" not in display_value
    for legacy_face in ("Iowan Old Style", "Palatino Linotype", "Georgia"):
        assert legacy_face not in css


def test_component_alignment_does_not_add_state_branding_or_endorsement():
    disallowed_claims = (
        "State of California",
        "Official website of",
        "An official California government website",
    )
    disallowed_header_patterns = (
        "CA.gov",
        "<ca-site-header",
        "<cagov-site-header",
    )
    for page_name in PUBLIC_PAGES:
        markup = _page(page_name)
        header = markup[markup.index("<header") : markup.index("</header>")]
        assert "Permit Bearings" in header, page_name
        assert "Prototype" in header, page_name
        for claim in disallowed_claims:
            assert claim not in markup, (page_name, claim)
        for pattern in disallowed_header_patterns:
            assert pattern not in header, (page_name, pattern)


def test_python_reference_surface_uses_the_same_local_component_layer():
    markup = intake_form("en")
    component_link = markup.index("/assets/california-design-system.css")
    product_link = markup.index("/assets/site.css")
    assert component_link < product_link
    assert 'id="skip-to-content"' in markup
    assert 'class="ca-button"' in markup
    assert 'class="ca-field"' in markup
    assert 'class="site-header"' in markup
    assert "State of California" not in markup
