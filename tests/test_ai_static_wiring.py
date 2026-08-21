"""The project-check page wires the optional AI service without touching the
static path: one meta tag names the service, the CSP allows exactly that
origin, and the browser module loads after the application it extends."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_check_page_names_the_service_once_and_allows_only_its_origin() -> None:
    html = (ROOT / "check.html").read_text(encoding="utf-8")
    meta = re.findall(r'<meta name="permit-ai-service" content="([^"]+)">', html)
    assert len(meta) == 1
    candidates = [c.strip() for c in meta[0].split(",")]
    assert candidates[0] == "http://127.0.0.1:8787"
    assert all(
        c.startswith(("http://127.0.0.1:8787", "http://localhost:8787", "https://"))
        for c in candidates
    )
    csp = re.search(r'content="(default-src [^"]+)"', html)
    assert csp is not None
    connect = re.search(r"connect-src ([^;]+);", csp.group(1))
    assert connect is not None
    allowed = connect.group(1).split()
    assert allowed[:3] == ["'self'", "http://127.0.0.1:8787", "http://localhost:8787"]
    # Every hosted candidate in the meta tag must be allowed by the CSP, and
    # the CSP must not allow an origin the page does not name.
    hosted = {c for c in candidates if c.startswith("https://")}
    assert set(allowed[3:]) == hosted
    server = (ROOT / "demo" / "app.py").read_text(encoding="utf-8")
    assert "connect-src 'self' http://127.0.0.1:8787 http://localhost:8787" in server
    for other in ("index.html", "prepare.html", "review.html", "evidence.html"):
        assert "permit-ai-service" not in (ROOT / other).read_text(encoding="utf-8")


def test_ai_module_loads_after_the_application_with_the_same_version() -> None:
    html = (ROOT / "check.html").read_text(encoding="utf-8")
    application = re.search(
        r'<script src="assets/demo\.js\?v=([a-zA-Z0-9]+)" defer></script>', html
    )
    ai_module = re.search(
        r'<script src="assets/ai\.js\?v=([a-zA-Z0-9]+)" defer></script>', html
    )
    assert application and ai_module
    assert application.group(1) == ai_module.group(1)
    assert application.start() < ai_module.start()
    assert html.index('<div id="aiAssist"') < html.index('<form id="intake"')


def test_static_application_makes_no_service_call_itself() -> None:
    application = (ROOT / "assets" / "demo.js").read_text(encoding="utf-8")
    ai_module = (ROOT / "assets" / "ai.js").read_text(encoding="utf-8")
    assert "permit-ai-service" not in application
    assert "8787" not in application
    assert "document.querySelector('meta[name=\"permit-ai-service\"]')" in ai_module
    assert ai_module.count("fetch(") == 1
    assert "SERVICE_CANDIDATES" in ai_module and '.split(",")' in ai_module
    assert "#:~:text=" in ai_module
    assert "localStorage" not in ai_module and "sessionStorage" not in ai_module
    assert 'credentials: "omit"' in ai_module
    for key in (
        "panelHeading",
        "unavailable",
        "explain",
        "withheld",
        "questionsHeading",
    ):
        assert application.count(f"      {key}:") == 2, key
