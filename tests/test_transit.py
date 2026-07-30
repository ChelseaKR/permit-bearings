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
