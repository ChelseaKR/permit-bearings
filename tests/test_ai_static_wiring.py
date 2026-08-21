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
    assert meta == ["http://127.0.0.1:8787"]
    csp = re.search(r'content="(default-src [^"]+)"', html)
    assert csp is not None
    connect = re.search(r"connect-src ([^;]+);", csp.group(1))
    assert connect is not None
    assert connect.group(1).split() == [
        "'self'",
        "http://127.0.0.1:8787",
        "http://localhost:8787",
    ]
    assert "https://" not in connect.group(1)
    server = (ROOT / "demo" / "app.py").read_text(encoding="utf-8")
    assert "connect-src 'self' http://127.0.0.1:8787 http://localhost:8787; " in server
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
