"""Rebuild data/jurisdictions/hcd-letters.json from the raw HAU letters pull.

Source: HCD's public "HAU letter dashboard" (Power BI publish-to-web report
embedded at hcd.ca.gov/hau/enforcement-letters), queried via the public
report API. Raw rows are preserved at corpus/hcd/hau-letters-raw.json.
Usage: python3 scripts/build_hcd_letters.py <retrieved-on-ISO>
"""

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def slugify(name):
    import unicodedata

    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main(retrieved_on):
    raw = json.loads((ROOT / "corpus/hcd/hau-letters-raw.json").read_text())
    registry = json.loads((ROOT / "data/jurisdictions/registry.json").read_text())[
        "jurisdictions"
    ]
    known = {j["slug"] for j in registry}
    aliases = {
        "carmel": "carmel-by-the-sea",
        "saint-helena": "st-helena",
        "angels-camp": "angels",
        "la-ca-ada-flintridge": "la-canada-flintridge",
    }
    for j in registry:
        if j["kind"] == "county":
            aliases[slugify(j["name"].replace(" County", ""))] = j["slug"]

    cols = raw["columns"]
    idx = {c: i for i, c in enumerate(cols)}
    letters, unmatched, statewide = {}, {}, []
    for row in raw["rows"]:
        name = (row[idx["G0"]] or "").strip()
        ms = row[idx["G1"]]
        date = (
            datetime.fromtimestamp(ms / 1000, tz=UTC).date().isoformat() if ms else None
        )
        rec = {
            "date": date,
            "kind": row[idx["G2"]] or "letter",
            "authority": row[idx["G4"]],
            "statutes": row[idx["G5"]],
            "subject": (row[idx["G8"]] or row[idx["G3"]] or "").strip()[:280],
            "url": row[idx["G7"]],
            "hau_number": row[idx["G9"]],
        }
        if name.startswith("-") or not name:
            statewide.append(rec)
            continue
        slug = slugify(name)
        slug = slug if slug in known else aliases.get(slug, slug)
        bucket = letters if slug in known else unmatched
        bucket.setdefault(slug, []).append(rec)

    for recs in letters.values():
        recs.sort(key=lambda r: r["date"] or "", reverse=True)

    out = {
        "source": (
            "HCD Housing Accountability Unit letter dashboard "
            "(hcd.ca.gov/hau/enforcement-letters), full public dataset "
            f"retrieved {retrieved_on}; raw rows preserved at "
            "corpus/hcd/hau-letters-raw.json. Letters addressed to no "
            "single jurisdiction are under _statewide; rows whose "
            "jurisdiction could not be matched to the Census registry "
            "are under _unmatched."
        ),
        "retrieved_on": retrieved_on,
        "letter_count": len(raw["rows"]),
        "letters": letters,
        "_statewide": statewide,
        "_unmatched": unmatched,
    }
    dest = ROOT / "data/jurisdictions/hcd-letters.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    n_matched = sum(len(v) for v in letters.values())
    n_unmatched = sum(len(v) for v in unmatched.values())
    print(
        f"total {len(raw['rows'])}: {n_matched} matched to "
        f"{len(letters)} jurisdictions, {len(statewide)} statewide, "
        f"{n_unmatched} unmatched ({sorted(unmatched)[:10]}...)"
    )
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    main(sys.argv[1])
