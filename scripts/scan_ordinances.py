"""Batch-scan local ordinance texts through the conformance scanner.

Drop ordinance text files at corpus/ordinances/<registry-slug>.txt (PDFs:
extract with pdftotext first) and record provenance in
corpus/ordinances/SOURCES.json. Results land at
data/conformance/results/<slug>.json plus an index the demo site reads.

Usage: python3 scripts/scan_ordinances.py <scanned-on-ISO>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from permit_pathways.conformance import load_checks, scan  # noqa: E402


def main(scanned_on):
    checks = load_checks(ROOT / "data/conformance/checks.json")
    sources = json.loads((ROOT / "corpus/ordinances/SOURCES.json").read_text())
    registry_slugs = {j["slug"] for j in json.loads(
        (ROOT / "data/jurisdictions/registry.json").read_text())["jurisdictions"]}
    results_dir = ROOT / "data/conformance/results"
    results_dir.mkdir(parents=True, exist_ok=True)

    index = {}
    for path in sorted((ROOT / "corpus/ordinances").glob("*.txt")):
        slug = path.stem
        if slug not in registry_slugs:
            raise SystemExit(f"{slug}: not a registry slug")
        if slug not in sources:
            raise SystemExit(f"{slug}: missing provenance in SOURCES.json")
        findings = scan(path.read_text(), checks)
        out = {
            "slug": slug,
            "source": sources[slug],
            "scanned_on": scanned_on,
            "disclaimer": ("Presence-based screening for staff/counsel "
                           "review; not a certification of compliance and "
                           "silence is not a clean bill of health."),
            "findings": [{
                "check_id": f.check.check_id,
                "title": f.check.title,
                "severity": f.check.severity,
                "excerpt": f.excerpt,
                "state_law": f.check.state_law,
                "hcd_precedent": f.check.hcd_precedent,
            } for f in findings],
        }
        (results_dir / f"{slug}.json").write_text(
            json.dumps(out, indent=1) + "\n")
        by_sev = {}
        for f in findings:
            by_sev[f.check.severity] = by_sev.get(f.check.severity, 0) + 1
        index[slug] = {"scanned_on": scanned_on,
                       "findings": len(findings), "by_severity": by_sev,
                       "source_title": sources[slug]["title"]}
        print(f"{slug}: {len(findings)} flag(s) {by_sev}")

    (results_dir / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    print(f"wrote {len(index)} result file(s) + index")


if __name__ == "__main__":
    main(sys.argv[1])
