"""Re-pull the full HAU letters table from HCD's public dashboard API.

HCD's letter dashboard (hcd.ca.gov/hau/enforcement-letters) embeds a Power
BI publish-to-web report; this queries its public API and decodes the DSR
payload into corpus/hcd/hau-letters-raw.json. Pair with
build_hcd_letters.py to refresh the per-jurisdiction dataset.

Usage:
    python3 scripts/pull_hau_letters.py            # pull + overwrite raw
    python3 scripts/pull_hau_letters.py --check    # compare only; exit 3 on drift

`--check` exit codes follow the source-currency watcher's distinction: 0
unchanged, 3 the dashboard was read and its rows moved, 2 the dashboard could
not be read. A fetch that fails is evidence about the network, not about
HCD's letters, and must never be reported as a change.

A row count is not a letter count. HCD edits published rows in place, so a
run can add rows, remove rows and edit rows at once, and "1317 versus 1314"
does not mean three new letters. The check reports rows added, rows removed,
and which jurisdictions had rows on both sides.

If the resource key changes (HCD republishes the report), re-read the
embed URL from the dashboard page and update RESOURCE_KEY.
"""
import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "hcd" / "hau-letters-raw.json"
USER_AGENT = "permit-pathways-hau-letters-watch/0.1"
JURISDICTION_COLUMN = 0  # u_jurisdiction_1_display_value
MAX_LISTED = 12
RESOURCE_KEY = "049c27c4-70aa-45c0-8ebd-5a224d4b44ed"
HOST = "https://wabi-us-gov-iowa-api.analysis.usgovcloudapi.net"
MODEL_ID = 971938
DATASET_ID = "5b74754d-30f9-4464-b563-44ee27833da2"
COLS = ["u_jurisdiction_1_display_value", "U_DATE_completed_display_value",
        "u_type_display_value", "u_type_of_request_display_value",
        "u_hcd_authority_display_value", "u_statutory_references_display_value",
        "u_keywords_display_value", "u_letter_url_display_value",
        "u_executive_summary_display_value", "number_display_value"]


def query():
    select = [{"Column": {"Expression": {"SourceRef": {"Source": "s"}},
                          "Property": c}, "Name": f"c{i}"}
              for i, c in enumerate(COLS)]
    payload = {
        "version": "1.0.0",
        "queries": [{
            "Query": {"Commands": [{"SemanticQueryDataShapeCommand": {
                "Query": {"Version": 2,
                          "From": [{"Name": "s", "Entity": "Source", "Type": 0}],
                          "Select": select},
                "Binding": {
                    "Primary": {"Groupings": [{"Projections": list(range(len(COLS)))}]},
                    "DataReduction": {"DataVolume": 6,
                                      "Primary": {"Window": {"Count": 30000}}},
                    "Version": 1}}}]},
            "QueryId": "",
            "ApplicationContext": {"DatasetId": DATASET_ID}}],
        "cancelQueries": [], "modelId": MODEL_ID}
    req = urllib.request.Request(
        HOST + "/public/reports/querydata?synchronous=true",
        data=json.dumps(payload).encode(),
        headers={"X-PowerBI-ResourceKey": RESOURCE_KEY,
                 "Content-Type": "application/json",
                 "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
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
                v = c[ci]; ci += 1
                dn = col.get("DN")
                if dn is not None and isinstance(v, int):
                    v = dicts[dn][v]
                vals.append(v)
        prev = vals
        out.append(vals)
    return {"columns": [c["N"] for c in schema], "rows": out}


@dataclass(frozen=True)
class Drift:
    """What moved between the committed rows and the dashboard's rows.

    Rows, not letters: HCD publishes one row per letter/reference pairing and
    edits published rows in place, so an edit shows up as one removed row and
    one added row for the same jurisdiction. Counting the difference in row
    totals reports that edit as nothing at all, and reports an edit plus a new
    letter as one new letter.
    """

    dashboard_rows: int
    committed_rows: int
    added: list[list[object]] = field(default_factory=list)
    removed: list[list[object]] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed)

    def _jurisdictions(self, rows):
        return {
            str(row[JURISDICTION_COLUMN])
            for row in rows
            if len(row) > JURISDICTION_COLUMN
        }

    @property
    def edited_jurisdictions(self) -> list[str]:
        """Jurisdictions with rows on both sides: an edit, or an edit plus a
        new letter. Never simply a new letter."""
        return sorted(self._jurisdictions(self.added) & self._jurisdictions(self.removed))

    @property
    def added_only_jurisdictions(self) -> list[str]:
        return sorted(self._jurisdictions(self.added) - self._jurisdictions(self.removed))

    @property
    def removed_only_jurisdictions(self) -> list[str]:
        return sorted(self._jurisdictions(self.removed) - self._jurisdictions(self.added))


def _row_counter(rows):
    # Order-insensitive: the API's row order is not contractual. Counter, not
    # set, so a duplicated row is a difference rather than a silent match.
    return Counter(json.dumps(row, sort_keys=True) for row in rows)


def classify(fresh_rows, current_rows) -> Drift:
    fresh_counts = _row_counter(fresh_rows)
    current_counts = _row_counter(current_rows)
    added = [json.loads(row) for row in (fresh_counts - current_counts).elements()]
    removed = [json.loads(row) for row in (current_counts - fresh_counts).elements()]
    return Drift(
        dashboard_rows=len(fresh_rows),
        committed_rows=len(current_rows),
        added=added,
        removed=removed,
    )


def _listed(names):
    if len(names) <= MAX_LISTED:
        return ", ".join(names)
    return ", ".join(names[:MAX_LISTED]) + f", and {len(names) - MAX_LISTED} more"


def describe(drift: Drift) -> list[str]:
    lines = [
        f"dashboard rows: {drift.dashboard_rows}; "
        f"committed rows: {drift.committed_rows}; "
        f"{'CHANGED' if drift.changed else 'unchanged'}"
    ]
    if not drift.changed:
        return lines
    lines.append(
        f"rows added: {len(drift.added)}; rows removed: {len(drift.removed)}. "
        f"A row total is not a letter count: HCD edits published rows in place."
    )
    if drift.added_only_jurisdictions:
        lines.append(
            f"added rows only ({len(drift.added_only_jurisdictions)} "
            f"jurisdictions): {_listed(drift.added_only_jurisdictions)}"
        )
    if drift.edited_jurisdictions:
        lines.append(
            f"rows on both sides, so edited in place (and possibly also new) "
            f"({len(drift.edited_jurisdictions)} jurisdictions): "
            f"{_listed(drift.edited_jurisdictions)}"
        )
    if drift.removed_only_jurisdictions:
        lines.append(
            f"removed rows only ({len(drift.removed_only_jurisdictions)} "
            f"jurisdictions): {_listed(drift.removed_only_jurisdictions)}"
        )
    return lines


def committed_rows():
    if not RAW.exists():
        return []
    return json.loads(RAW.read_text()).get("rows", [])


def main(argv=None, fetch=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    fetch = fetch or (lambda: decode(query()))
    check_only = "--check" in argv
    try:
        fresh = fetch()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
        # Could not read the dashboard. That is evidence about the network,
        # not about HCD's letters: never report it as drift.
        print(f"HCD letters dashboard unverifiable: {type(exc).__name__}: {exc}")
        return 2
    drift = classify(fresh["rows"], committed_rows())
    for line in describe(drift):
        print(line)
    if check_only:
        return 3 if drift.changed else 0
    RAW.write_text(json.dumps(fresh))
    print(f"wrote {RAW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
