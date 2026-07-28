from demo.app import ROOT, static_path
from scripts.build_demo_bundle import OUTPUT, build_bundle


def test_committed_demo_bundle_matches_canonical_json():
    assert OUTPUT.read_text(encoding="utf-8") == build_bundle()


def test_index_loads_offline_bundle_before_application_code():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    bundle_tag = '<script src="data/demo-data.js"></script>'
    application_start = "<script>\nconst STRINGS"

    assert bundle_tag in html
    assert application_start in html
    assert html.index(bundle_tag) < html.index(application_start)
    assert "globalThis.PERMIT_PATHWAYS_DEMO_DATA" in html


def test_demo_server_exposes_only_intended_static_files():
    assert static_path("/index.html") == ROOT / "index.html"
    assert static_path("/showcase") == ROOT / "index.html"
    assert static_path("/data/demo-data.js") == OUTPUT

    assert static_path("/README.md") is None
    assert static_path("/data/missing.json") is None
    assert static_path("/data/../README.md") is None
    assert static_path("/data/%2e%2e/README.md") is None
