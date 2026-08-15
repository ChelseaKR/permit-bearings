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

CORPUS_HQ_PATH = (
    Path(__file__).parent.parent / "corpus" / "transit" / "ca-hq-transit-stops.json"
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

    hq = load_hq_stops(CORPUS_HQ_PATH)
    assert len(hq) > 10000
    near_depot = [
        s
        for s in hq
        if s.hqta_type == "major_stop_rail"
        and haversine_miles(s.lat, s.lon, 38.5436, -121.7377) < 0.2
    ]
    assert near_depot, "Davis Amtrak depot present as a major rail stop"
    # The depot claim is only worth anything if the rows backing it are
    # existing facilities. One of the rail rows within 0.2 mi of the depot
    # is itself an mpo_rtp_planned_major_stop, so "a major_stop_rail row is
    # nearby" does not establish it.
    existing = [s for s in near_depot if s.is_existing_major]
    assert existing, "the depot rows relied on are existing, not planned"


# --- planned RTP stops are not existing major transit stops (issue #44) ---


def _planned(**overrides):
    from permit_pathways.transit import PLANNED_HQTA_DETAIL, HQStop

    fields = {
        "lat": 38.5449,
        "lon": -121.7442,
        "hqta_type": "major_stop_bus",
        "details": PLANNED_HQTA_DETAIL,
        "agency": "Yolo TD",
    }
    fields.update(overrides)
    return HQStop(**fields)


def test_planned_row_is_not_classified_as_an_existing_major_stop():
    planned = _planned()
    assert planned.is_major_type
    assert planned.is_planned
    assert not planned.is_existing_major


def test_planned_only_stop_produces_no_candidate_and_no_present_tense_claim():
    from permit_pathways.transit import determine

    d = determine(38.5449, -121.7442, [], hq_stops=[_planned()])

    # The wrong answer is an eligibility candidate resting on a stop that
    # does not exist yet. Assert its absence, not merely that some planned
    # reporting happened.
    assert d.height_18ft == "no"
    assert d.parking_exemption == "no"
    assert d.qualifying_stops == []
    summary = d.summary()
    assert "is a major transit stop" not in summary
    assert "CANDIDATE" not in summary.replace("NO CANDIDATE", "")

    # It is reported rather than dropped, and the report says the question
    # is open rather than answering it either way.
    assert len(d.planned_stops) == 1
    assert "PLANNED, NOT COUNTED" in summary
    assert "mpo_rtp_planned_major_stop" in summary
    assert "not decided here" in summary


def test_a_planned_stop_never_reaches_the_qualifying_set():
    from permit_pathways.transit import PLANNED_HQTA_DETAIL, determine

    existing = _planned(
        lat=38.5436,
        lon=-121.7377,
        hqta_type="major_stop_rail",
        details="major_stop_rail_single_operator",
        agency="Amtrak",
    )
    d = determine(38.5449, -121.7442, [], hq_stops=[_planned(), existing])

    assert d.height_18ft == "candidate"
    # The nearer stop is the planned one. The cited stop must still be the
    # existing rail row, and no qualifying entry may name a planned row.
    named = d.qualifying_stops[0][0].name
    assert "Amtrak" in named
    assert all(
        PLANNED_HQTA_DETAIL not in stop.name and PLANNED_HQTA_DETAIL not in reason
        for stop, _miles, reason in d.qualifying_stops
    )
    assert d.summary().index("CANDIDATE") < d.summary().index("PLANNED, NOT COUNTED")


def test_planned_cluster_alone_does_not_carry_the_committed_corpus():
    """The README's own coordinate, against the committed statewide corpus.

    Seven Yolo TD rows sit closer to this point than any existing major
    stop, and every one of them is planned-only. Before the fix the screen
    cited one of them in the present tense.
    """
    from permit_pathways.transit import PLANNED_HQTA_DETAIL, determine, load_hq_stops

    hq = load_hq_stops(CORPUS_HQ_PATH)
    assert sum(1 for s in hq if s.is_planned) > 0, "corpus has planned rows to exclude"

    d = determine(38.5449, -121.7442, [], hq_stops=hq)
    assert d.planned_stops, "the planned rows near this point are still reported"
    assert d.planned_stops[0][1] < d.qualifying_stops[0][1], (
        "the nearest planned row is closer than the cited existing stop, "
        "so this coordinate exercises the ordering the fix depends on"
    )
    for stop, _miles, reason in d.qualifying_stops:
        assert PLANNED_HQTA_DETAIL not in stop.name
        assert PLANNED_HQTA_DETAIL not in reason
    assert "major_stop_rail" in d.qualifying_stops[0][0].name


def test_planned_only_neighbourhood_reports_no_height_candidate():
    """A point whose only nearby major-stop rows are planned.

    38.5449/-121.7442 keeps its candidate because existing rail is 0.36 mi
    away. Move north-west and the existing rows fall outside the half mile
    while the planned Yolo TD cluster does not.
    """
    from permit_pathways.transit import determine, load_hq_stops

    hq = load_hq_stops(CORPUS_HQ_PATH)
    d = determine(38.5510, -121.7520, [], hq_stops=hq)

    assert d.planned_stops, "planned rows are within a half mile of this point"
    assert d.height_18ft == "no"
    assert d.qualifying_stops == []
    assert "NO CANDIDATE" in d.summary()
