"""Re-pull the full HAU letters table from HCD's public dashboard API.

HCD's letter dashboard (hcd.ca.gov/hau/enforcement-letters) embeds a Power
BI publish-to-web report; this queries its public API and decodes the DSR
payload into corpus/hcd/hau-letters-raw.json. Pair with
build_hcd_letters.py to refresh the per-jurisdiction dataset.

Usage:
    python3 scripts/pull_hau_letters.py            # pull + overwrite raw
    python3 scripts/pull_hau_letters.py --check    # compare only; exit 3 on drift

If the resource key changes (HCD republishes the report), re-read the
embed URL from the dashboard page and update RESOURCE_KEY.
"""

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "hcd" / "hau-letters-raw.json"
RESOURCE_KEY = "049c27c4-70aa-45c0-8ebd-5a224d4b44ed"
HOST = "https://wabi-us-gov-iowa-api.analysis.usgovcloudapi.net"
MODEL_ID = 971938
DATASET_ID = "5b74754d-30f9-4464-b563-44ee27833da2"
COLS = [
    "u_jurisdiction_1_display_value",
    "U_DATE_completed_display_value",
    "u_type_display_value",
    "u_type_of_request_display_value",
    "u_hcd_authority_display_value",
    "u_statutory_references_display_value",
    "u_keywords_display_value",
    "u_letter_url_display_value",
    "u_executive_summary_display_value",
    "number_display_value",
]


def query():
    select = [
        {
            "Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": c},
            "Name": f"c{i}",
        }
        for i, c in enumerate(COLS)
    ]
    payload = {
        "version": "1.0.0",
        "queries": [
            {
                "Query": {
                    "Commands": [
                        {
                            "SemanticQueryDataShapeCommand": {
                                "Query": {
                                    "Version": 2,
                                    "From": [
                                        {"Name": "s", "Entity": "Source", "Type": 0}
                                    ],
                                    "Select": select,
                                },
                                "Binding": {
                                    "Primary": {
                                        "Groupings": [
                                            {"Projections": list(range(len(COLS)))}
                                        ]
                                    },
                                    "DataReduction": {
                                        "DataVolume": 6,
                                        "Primary": {"Window": {"Count": 30000}},
                                    },
                                    "Version": 1,
                                },
                            }
                        }
                    ]
                },
                "QueryId": "",
                "ApplicationContext": {"DatasetId": DATASET_ID},
            }
        ],
        "cancelQueries": [],
        "modelId": MODEL_ID,
    }
    req = urllib.request.Request(
        HOST + "/public/reports/querydata?synchronous=true",
        data=json.dumps(payload).encode(),
        headers={
            "X-PowerBI-ResourceKey": RESOURCE_KEY,
            "Content-Type": "application/json",
        },
    )
    # HOST is a module constant naming HCD's published Power BI endpoint over
    # https. No caller-supplied value reaches the scheme, so the file:/custom
    # scheme risk B310 warns about cannot arise here. Same decision, and the
    # same reasoning, as the waiver on harness/watch.py.
    with urllib.request.urlopen(req, timeout=120) as resp:  # nosec B310
        return json.load(resp)


def decode(data):
    dsr = data["results"][0]["result"]["data"]["dsr"]
    ds = dsr["DS"][0]
    dicts = ds.get("ValueDicts", {})
    rows_raw = ds["PH"][0]["DM0"]
    schema = rows_raw[0]["S"]
    n = len(schema)
    prev, out = [None] * n, []
    for row in rows_raw:
        c = row.get("C", [])
        rbits, nbits = row.get("R", 0), row.get("Ø", 0)
        vals, ci = [], 0
        for i, col in enumerate(schema):
            if nbits >> i & 1:
                vals.append(None)
            elif rbits >> i & 1:
                vals.append(prev[i])
            else:
                v = c[ci]
                ci += 1
                dn = col.get("DN")
                if dn is not None and isinstance(v, int):
                    v = dicts[dn][v]
                vals.append(v)
        prev = vals
        out.append(vals)
    return {"columns": [c["N"] for c in schema], "rows": out}


def main() -> int:
    check_only = "--check" in sys.argv
    fresh = decode(query())
    current = json.loads(RAW.read_text()) if RAW.exists() else {"rows": []}

    def key(rows):  # order-insensitive: the API's row order is not contractual
        return sorted(json.dumps(r, sort_keys=True) for r in rows)

    same = key(fresh["rows"]) == key(current.get("rows", []))
    print(
        f"dashboard rows: {len(fresh['rows'])}; "
        f"committed rows: {len(current.get('rows', []))}; "
        f"{'unchanged' if same else 'CHANGED'}"
    )
    if check_only:
        return 3 if not same else 0
    RAW.write_text(json.dumps(fresh))
    print(f"wrote {RAW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
