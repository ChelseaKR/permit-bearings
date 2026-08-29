import zipfile
from pathlib import Path

import pytest

from permit_pathways.transit import (
    StopService,
    _worst_peak_gap,
    determine,
    haversine_miles,
    load_feed,
)

# Synthetic feed: stop S1 served by route A every 10 min in both peaks
# (HQTC-quality) and route B every 30 min; stop S2 nearby (same corner)
# served by route C every 15 min — so the S1/S2 cluster has two routes
# with <=20-min peaks and is a major-stop candidate. Stop FAR is remote
# with sparse service.
FILES = {
    "stops.txt": (
        "stop_id,stop_name,stop_lat,stop_lon\n"
        "S1,Main & First,38.5450,-121.7400\n"
        "S2,Main & First (far side),38.5455,-121.7402\n"
        "FAR,Edge Rd,38.6200,-121.7400\n"
    ),
    "routes.txt": ("route_id,route_short_name,route_type\nA,A,3\nB,B,3\nC,C,3\n"),
    "calendar.txt": (
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        "start_date,end_date\n"
        "WK,1,1,1,1,1,0,0,20260101,20261231\n"
    ),
    "trips.txt": "route_id,service_id,trip_id,direction_id\n"
    + "".join(
        [f"A,WK,A{i},0\n" for i in range(38)]
        + [f"B,WK,B{i},0\n" for i in range(14)]
        + [f"C,WK,C{i},0\n" for i in range(26)]
        + ["B,WK,BFAR,0\n"]
    ),
    "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
    + "".join(
        # Route A at S1: every 10 min, 06:00-09:00 and 16:00-19:00
        [
            f"A{i},{6 + (i * 10) // 60:02d}:{(i * 10) % 60:02d}:00,"
            f"{6 + (i * 10) // 60:02d}:{(i * 10) % 60:02d}:00,S1,1\n"
            for i in range(19)
        ]
        + [
            f"A{19 + i},{16 + (i * 10) // 60:02d}:{(i * 10) % 60:02d}:00,"
            f"{16 + (i * 10) // 60:02d}:{(i * 10) % 60:02d}:00,S1,1\n"
            for i in range(19)
        ]
        # Route B at S1: every 30 min in both peaks
        + [
            f"B{i},{6 + (i * 30) // 60:02d}:{(i * 30) % 60:02d}:00,"
            f"{6 + (i * 30) // 60:02d}:{(i * 30) % 60:02d}:00,S1,1\n"
            for i in range(7)
        ]
        + [
            f"B{7 + i},{16 + (i * 30) // 60:02d}:{(i * 30) % 60:02d}:00,"
            f"{16 + (i * 30) // 60:02d}:{(i * 30) % 60:02d}:00,S1,1\n"
            for i in range(7)
        ]
        # Route C at S2: every 15 min in both peaks
        + [
            f"C{i},{6 + (i * 15) // 60:02d}:{(i * 15) % 60:02d}:00,"
            f"{6 + (i * 15) // 60:02d}:{(i * 15) % 60:02d}:00,S2,1\n"
            for i in range(13)
        ]
        + [
            f"C{13 + i},{16 + (i * 15) // 60:02d}:{(i * 15) % 60:02d}:00,"
            f"{16 + (i * 15) // 60:02d}:{(i * 15) % 60:02d}:00,S2,1\n"
            for i in range(13)
        ]
        # FAR: one bus all day
        + ["BFAR,07:00:00,07:00:00,FAR,1\n"]
    ),
}


@pytest.fixture()
def stops(tmp_path):
    path = tmp_path / "feed.zip"
    with zipfile.ZipFile(path, "w") as z:
        for name, content in FILES.items():
            z.writestr(name, content)
    return load_feed(path)


def test_headway_classification(stops):
    by_id = {s.stop_id: s for s in stops}
    assert by_id["S1"].route_max_gaps["A"] <= 15  # HQTC-quality
    assert by_id["S1"].route_max_gaps["B"] == 30  # not qualifying
    assert by_id["S2"].route_max_gaps["C"] <= 20  # major-stop-quality
    assert "B" not in by_id["FAR"].route_max_gaps  # <2 peak trips → no interval


def test_point_near_cluster_gets_both_candidates(stops):
    d = determine(38.5452, -121.7401, stops)
    assert d.parking_exemption == "candidate"
    assert d.height_18ft == "candidate"
    reasons = [reason for _, _, reason in d.qualifying_stops]
    assert any("major transit stop" in r or "high-quality" in r for r in reasons)


def test_remote_point_has_no_candidate_in_supplied_data(stops):
    # ~20+ miles from every supplied stop: no candidate is found in this feed.
    # This does not establish that the feed covers every relevant operator.
    d = determine(38.9000, -121.4000, stops)
    assert d.parking_exemption == "no"
    assert d.height_18ft == "no"
    assert "NO" in d.summary()


def test_haversine_sanity():
    # Davis to Sacramento is roughly 11 miles.
    assert 9 < haversine_miles(38.5449, -121.7405, 38.5816, -121.4944) < 14


def test_peak_window_edges_count_toward_the_worst_gap():
    # Each peak has two trips 15 minutes apart near its end. Consecutive-trip
    # math alone says 15 minutes; the uncovered window edge is 150 minutes.
    assert _worst_peak_gap([510, 525, 1110, 1125]) == 150


def test_ferry_requires_connecting_bus_or_rail_service():
    ferry = StopService(
        stop_id="F",
        name="Ferry terminal",
        lat=38.545,
        lon=-121.740,
        ferry=True,
    )
    unconnected = determine(38.545, -121.740, [ferry])
    assert unconnected.parking_exemption == "candidate"
    assert unconnected.height_18ft == "no"

    connecting_bus = StopService(
        stop_id="B",
        name="Connecting bus",
        lat=38.5451,
        lon=-121.740,
        bus_routes={"connector"},
    )
    connected = determine(38.545, -121.740, [ferry, connecting_bus])
    assert connected.height_18ft == "candidate"
    assert "major transit stop" in connected.qualifying_stops[0][2]


def test_hq_dataset_supplies_missing_rail_major_stop(stops):
    from permit_pathways.transit import HQStop, determine

    # A rail station absent from the local bus feed (the Davis Amtrak
    # problem): the Caltrans HQ dataset supplies it, flipping both
    # determinations near the depot.
    hq = [
        HQStop(
            lat=38.5436,
            lon=-121.7377,
            hqta_type="major_stop_rail",
            details="major_stop_rail_single_operator",
            agency="Amtrak",
        )
    ]
    d = determine(
        38.5449, -121.7405, [s for s in stops if s.stop_id == "FAR"], hq_stops=hq
    )
    assert d.parking_exemption == "candidate"
    assert d.height_18ft == "candidate"
    assert "Caltrans HQ Transit Stops dataset" in d.qualifying_stops[0][2]


def test_corpus_hq_dataset_loads_and_contains_davis_amtrak():
    from permit_pathways.transit import haversine_miles, load_hq_stops

    path = (
        Path(__file__).parent.parent / "corpus" / "transit" / "ca-hq-transit-stops.json"
    )
    hq = load_hq_stops(path)
    assert len(hq) > 10000
    depot = [
        s
        for s in hq
        if s.hqta_type == "major_stop_rail"
        and haversine_miles(s.lat, s.lon, 38.5436, -121.7377) < 0.2
    ]
    assert depot, "Davis Amtrak depot present as a major rail stop"


def _hq(details: str, lat: float = 38.5449, lon: float = -121.7405, **kw):
    from permit_pathways.transit import HQStop

    return HQStop(
        lat=lat,
        lon=lon,
        hqta_type=kw.get("hqta_type", "major_stop_bus"),
        details=details,
        agency=kw.get("agency", "Yolo TD"),
    )


def test_planned_rtp_stop_never_supports_an_affirmative_result():
    """hqta_details marks 3,125 major-stop rows as planned, not built.

    Screening on hqta_type alone stated in the present tense that a facility
    programmed in an MPO plan "is a major transit stop".
    """

    from permit_pathways.transit import determine

    planned = _hq("mpo_rtp_planned_major_stop")
    d = determine(38.5449, -121.7405, [], hq_stops=[planned])

    assert d.height_18ft == "planned_only"
    assert d.parking_exemption == "planned_only"
    reason = d.qualifying_stops[0][2]
    assert "PLANNED" in reason
    assert "mpo_rtp_planned_major_stop" in reason
    summary = d.summary()
    assert "NOT ESTABLISHED BY AN EXISTING STOP" in summary
    assert "NOT ESTABLISHED BY EXISTING TRANSIT" in summary


def test_an_existing_stop_outranks_a_nearer_planned_one():
    """The cited reason must name a facility that exists, when one qualifies."""

    from permit_pathways.transit import determine

    planned = _hq("mpo_rtp_planned_major_stop", lat=38.5449, lon=-121.7405)
    existing = _hq(
        "major_stop_rail_single_operator",
        lat=38.5436,
        lon=-121.7377,
        hqta_type="major_stop_rail",
        agency="Amtrak",
    )
    d = determine(38.5449, -121.7405, [], hq_stops=[planned, existing])

    assert d.height_18ft == "candidate"
    cited_stop, cited_miles, cited_reason = d.qualifying_stops[0]
    assert "Amtrak" in cited_stop.name
    assert "PLANNED" not in cited_reason
    # The planned entry is nearer and is still reported, never dropped.
    assert cited_miles > d.qualifying_stops[1][1]
    assert "PLANNED" in d.qualifying_stops[1][2]


def test_unrecorded_hqta_details_is_unknown_not_assumed_existing():
    from permit_pathways.transit import determine

    for details in ("", "some_value_added_after_this_was_written"):
        d = determine(38.5449, -121.7405, [], hq_stops=[_hq(details)])
        assert d.height_18ft == "planned_only", details
        assert "no recorded hqta_details" in d.qualifying_stops[0][2]
        assert "does not say whether this facility exists" in d.summary()


def test_planned_flag_reads_the_dataset_field_not_the_type():
    from permit_pathways.transit import HQStop

    planned = _hq("mpo_rtp_planned_major_stop")
    assert planned.is_major and planned.is_planned
    assert not planned.existence_is_recorded

    built = _hq("intersection_2_bus_routes_same_operator")
    assert built.is_major and not built.is_planned
    assert built.existence_is_recorded

    assert isinstance(HQStop.is_planned, property)


def test_corpus_actually_contains_planned_major_stops():
    """A guard against data that no longer exercises it is not a guard."""

    from permit_pathways.transit import load_hq_stops

    path = (
        Path(__file__).parent.parent / "corpus" / "transit" / "ca-hq-transit-stops.json"
    )
    hq = load_hq_stops(path)
    major = [s for s in hq if s.is_major]
    planned = [s for s in major if s.is_planned]
    assert planned, "corpus no longer exercises the planned-stop path"
    assert len(planned) < len(major), "corpus has no existing major stops left"


def test_documented_davis_command_cites_an_existing_stop():
    """The README's own example used to cite a planned Yolo TD entry.

    Seven planned rows sit between 0.118 and 0.296 mi of this coordinate; the
    existing rail major stops are at about 0.36 mi. Both are inside the half
    mile, so the verdict survives either way — but the stop named as the
    reason must be one that exists.
    """

    from permit_pathways.transit import determine, load_feed, load_hq_stops

    root = Path(__file__).parent.parent
    stops = load_feed(root / "corpus" / "gtfs" / "unitrans.zip")
    hq = load_hq_stops(root / "corpus" / "transit" / "ca-hq-transit-stops.json")
    d = determine(38.5449, -121.7442, stops, hq_stops=hq)

    assert d.height_18ft == "candidate"
    _, _, reason = d.qualifying_stops[0]
    assert "PLANNED" not in reason
    assert "mpo_rtp_planned_major_stop" not in reason
    assert "major_stop_rail" in reason
    planned_reasons = [r for _, _, r in d.qualifying_stops if "PLANNED" in r]
    assert planned_reasons, "planned entries must still be reported, not dropped"


def test_every_corpus_detail_value_is_classified():
    """A dataset refresh must not silently downgrade every stop to unknown.

    ``existence_is_recorded`` whitelists the values observed in the committed
    corpus. That fails safe, but only if a new value is noticed: this names
    it instead of letting the tool quietly stop finding candidates.
    """

    import json

    from permit_pathways.transit import EXISTING_DETAILS, PLANNED_DETAILS

    path = (
        Path(__file__).parent.parent / "corpus" / "transit" / "ca-hq-transit-stops.json"
    )
    observed = {row[3] for row in json.loads(path.read_text())["stops"]}
    unclassified = sorted(observed - EXISTING_DETAILS - PLANNED_DETAILS)
    assert not unclassified, (
        "unclassified hqta_details value(s) "
        f"{unclassified}: decide whether each describes an existing or a "
        "planned facility and add it to the matching set"
    )
