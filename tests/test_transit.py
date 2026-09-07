import zipfile
from datetime import date
from pathlib import Path

import pytest

from permit_pathways.transit import (
    HQStop,
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


#: A Monday inside the fixture calendar's 20260101-20261231 weekday range.
FIXTURE_SERVICE_DATE = date(2026, 6, 15)


def _write_feed(path, files):
    with zipfile.ZipFile(path, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    return path


@pytest.fixture()
def feed_path(tmp_path):
    return _write_feed(tmp_path / "feed.zip", FILES)


@pytest.fixture()
def stops(feed_path):
    return load_feed(feed_path, as_of=FIXTURE_SERVICE_DATE).stops


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


# --- Planned regional-transportation-plan stops -------------------------
#
# Caltrans publishes `hqta_details` for every row in the statewide dataset.
# `mpo_rtp_planned_major_stop` marks a location an MPO submitted as planned in
# its adopted regional transportation plan, which Caltrans documents as future
# service that it "does not validate or further process". Those rows carry the
# same `major_stop_*` type as an operating rail platform, so a screen that
# reads only `hqta_type` reports a facility that does not exist yet as the
# reason a standard applies.

PLANNED_BUS_STOP = HQStop(
    lat=38.5455,
    lon=-121.7442,
    hqta_type="major_stop_bus",
    details="mpo_rtp_planned_major_stop",
    agency="Yolo TD",
)

EXISTING_RAIL_STOP = HQStop(
    lat=38.5400,
    lon=-121.7400,
    hqta_type="major_stop_rail",
    details="major_stop_rail_single_operator",
    agency="Amtrak",
)

DAVIS_README_POINT = (38.5449, -121.7442)


def test_planned_rtp_stop_does_not_qualify_as_a_major_transit_stop():
    # The only dataset row within a half mile is one an MPO submitted as
    # planned. PRC § 21064.3 is not satisfied by a facility that does not
    # exist, so the screen must not report a candidate on this row alone.
    determination = determine(*DAVIS_README_POINT, [], hq_stops=[PLANNED_BUS_STOP])
    assert determination.height_18ft == "no"
    assert determination.qualifying_stops == []


def test_planned_rtp_stop_alone_does_not_establish_public_transit():
    # § 66322(a)(1) turns on public transit near the site. A planned stop is
    # not service the applicant can walk to today.
    determination = determine(*DAVIS_README_POINT, [], hq_stops=[PLANNED_BUS_STOP])
    assert determination.parking_exemption == "no"


def test_planned_stops_within_the_radius_are_reported_not_discarded():
    # Withholding the candidate is only half the fix: the reader still has to
    # be told the row exists, so they can ask whether it was built.
    determination = determine(*DAVIS_README_POINT, [], hq_stops=[PLANNED_BUS_STOP])
    assert len(determination.planned_major_stops) == 1
    planned_stop, planned_miles = determination.planned_major_stops[0]
    assert planned_stop.agency == "Yolo TD"
    assert planned_miles < 0.5


def test_summary_names_a_planned_stop_and_sends_it_to_staff():
    determination = determine(*DAVIS_README_POINT, [], hq_stops=[PLANNED_BUS_STOP])
    summary = determination.summary()
    assert "regional transportation plan" in summary
    assert "Yolo TD" in summary
    assert "does not validate" in summary
    assert "§ 21064.3" in summary
    assert "in service" in summary


def test_an_existing_stop_is_cited_even_when_a_planned_one_is_nearer():
    # Both are inside the half mile, so the verdict survives either way. The
    # defect is which stop the screen names as the reason.
    determination = determine(
        *DAVIS_README_POINT,
        [],
        hq_stops=[PLANNED_BUS_STOP, EXISTING_RAIL_STOP],
    )
    assert determination.height_18ft == "candidate"
    cited_stop, _miles, reason = determination.qualifying_stops[0]
    assert "Amtrak" in cited_stop.name
    assert "major_stop_rail" in reason
    assert "mpo_rtp_planned_major_stop" not in reason
    assert len(determination.planned_major_stops) == 1


def test_corpus_davis_example_does_not_cite_a_planned_stop():
    # The exact coordinate the README documents. Seven planned Yolo TD rows
    # sit between it and the two operating rail platforms at ~0.36 mi.
    from permit_pathways.transit import load_hq_stops

    path = (
        Path(__file__).parent.parent / "corpus" / "transit" / "ca-hq-transit-stops.json"
    )
    determination = determine(*DAVIS_README_POINT, [], hq_stops=load_hq_stops(path))
    assert determination.height_18ft == "candidate"
    _cited_stop, miles, reason = determination.qualifying_stops[0]
    assert "major_stop_rail" in reason
    assert "mpo_rtp_planned_major_stop" not in reason
    assert 0.3 < miles < 0.4
    assert determination.planned_major_stops


def test_unreadable_hqta_details_is_rejected_rather_than_read_as_existing():
    # `details` now decides whether a row can support a candidate, so a value
    # that is not text must fail the load instead of defaulting to "" and
    # being treated as an operating facility.
    import json

    from permit_pathways.transit import load_hq_stops

    payload = {
        "source": "test",
        "retrieved_on": "2026-08-27",
        "stops": [[38.5, -121.7, "major_stop_bus", 5, "Yolo TD", 4.0]],
    }
    path = Path(__file__).parent / "_hq_details_not_text.json"
    path.write_text(json.dumps(payload))
    try:
        with pytest.raises(ValueError):
            load_hq_stops(path)
    finally:
        path.unlink()


def test_a_planned_and_an_existing_row_at_one_point_both_survive_loading():
    # The de-duplication key has to include `details`, or a planned row and an
    # operating row sharing a coordinate collapse into whichever came first.
    import json

    from permit_pathways.transit import load_hq_stops

    payload = {
        "source": "test",
        "retrieved_on": "2026-08-27",
        "stops": [
            [38.5, -121.7, "major_stop_rail", "mpo_rtp_planned_major_stop", "A", 4.0],
            [
                38.5,
                -121.7,
                "major_stop_rail",
                "major_stop_rail_single_operator",
                "A",
                4.0,
            ],
        ],
    }
    path = Path(__file__).parent / "_hq_same_point_two_details.json"
    path.write_text(json.dumps(payload))
    try:
        loaded = load_hq_stops(path)
    finally:
        path.unlink()
    assert len(loaded) == 2
    assert sorted(stop.details for stop in loaded) == [
        "major_stop_rail_single_operator",
        "mpo_rtp_planned_major_stop",
    ]


# --- Service dates (issue #132) -----------------------------------------
#
# Both screens turn on service that operates on a day, so a headway is a fact
# about a date. The previous implementation read `calendar.txt` alone, kept
# whichever service_id had the most trips, and never opened `feed_info.txt` or
# `calendar_dates.txt` -- so a summer session, a holiday, and a feed that
# expired years ago all produced a number, and which number depended on which
# service period happened to be larger. These tests pin the four states in
# which no number is produced, and the two in which one is.

CALENDAR_TWO_SEASONS = (
    "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
    "start_date,end_date\n"
    # A big spring weekday service that ended, and a small summer one that
    # runs on the date under test. "Busiest" picks the wrong one.
    "SPRING,1,1,1,1,1,0,0,20260101,20260531\n"
    "SUMMER,1,1,1,1,1,0,0,20260601,20260831\n"
    "WEEKEND,0,0,0,0,0,1,1,20260101,20261231\n"
)


def _peak_times(count, step):
    """`count` trips every `step` minutes from 06:00 and again from 16:00."""
    rows = []
    for index in range(count):
        for base in (6, 16):
            minute = index * step
            rows.append(f"{base + minute // 60:02d}:{minute % 60:02d}:00")
    return rows


def _seasonal_feed(files_extra=None):
    trips = []
    stop_times = []
    for service, step, count in (
        ("SPRING", 10, 19),
        ("SUMMER", 15, 13),
        ("WEEKEND", 60, 4),
    ):
        for index, hms in enumerate(_peak_times(count, step)):
            trip_id = f"{service}{index}"
            trips.append(f"R1,{service},{trip_id},0\n")
            stop_times.append(f"{trip_id},{hms},{hms},S1,1\n")
    files = {
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nS1,Depot,38.5450,-121.7400\n",
        "routes.txt": "route_id,route_short_name,route_type\nR1,1,3\n",
        "calendar.txt": CALENDAR_TWO_SEASONS,
        "trips.txt": "route_id,service_id,trip_id,direction_id\n" + "".join(trips),
        "stop_times.txt": (
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            + "".join(stop_times)
        ),
    }
    files.update(files_extra or {})
    return files


def test_without_a_service_date_no_headway_is_produced(feed_path):
    # The defect in its plainest form: asked nothing about a day, the loader
    # used to answer with the busiest service's headways anyway.
    screen = load_feed(feed_path)
    assert screen.calendar.status == "no_as_of"
    assert all(stop.route_max_gaps == {} for stop in screen.stops)
    assert not screen.calendar.headways_measurable


def test_without_a_service_date_the_screen_is_unknown_not_no(feed_path):
    screen = load_feed(feed_path)
    determination = determine(
        38.5452, -121.7401, screen.stops, calendar=screen.calendar
    )
    assert determination.height_18ft == "unknown"
    assert determination.parking_exemption == "unknown"
    summary = determination.summary()
    assert "UNKNOWN" in summary
    assert "no service date was supplied" in summary


def test_a_stated_date_still_produces_the_candidates_it_always_did(stops):
    # The complement of the four withholding tests. If the only thing this
    # change did were report `unknown` everywhere, every test above would pass
    # and the module would be useless. On a date the feed covers, the answer is
    # the same one the module gave before.
    determination = determine(38.5452, -121.7401, stops)
    assert determination.parking_exemption == "candidate"
    assert determination.height_18ft == "candidate"
    assert any(stop.route_max_gaps for stop in stops)


def test_a_date_outside_the_feeds_own_validity_window_is_unknown(tmp_path):
    files = _seasonal_feed(
        {
            "feed_info.txt": (
                "feed_publisher_name,feed_publisher_url,feed_lang,"
                "feed_start_date,feed_end_date\n"
                "Test,http://example.invalid,en,20260601,20260831\n"
            )
        }
    )
    path = _write_feed(tmp_path / "expired.zip", files)
    # Inside `calendar.txt`'s WEEKEND range, outside what the feed publishes
    # about itself. An expired feed used to screen exactly like a current one.
    screen = load_feed(path, as_of=date(2026, 12, 5))
    assert screen.calendar.status == "outside_feed_window"
    assert screen.calendar.feed_valid_from == "2026-06-01"
    assert screen.calendar.feed_valid_to == "2026-08-31"
    assert all(stop.route_max_gaps == {} for stop in screen.stops)
    determination = determine(
        38.5450, -121.7400, screen.stops, calendar=screen.calendar
    )
    assert determination.parking_exemption == "unknown"
    assert determination.height_18ft == "unknown"
    summary = determination.summary()
    assert "2026-06-01 to 2026-08-31" in summary
    assert "CANDIDATE" not in summary


def test_a_feed_with_no_calendar_files_is_unknown_rather_than_a_negative(tmp_path):
    files = _seasonal_feed()
    del files["calendar.txt"]
    path = _write_feed(tmp_path / "nocal.zip", files)
    screen = load_feed(path, as_of=date(2026, 6, 15))
    assert screen.calendar.status == "no_calendar"
    assert screen.calendar.calendar_source == "none"
    determination = determine(
        38.5450, -121.7400, screen.stops, calendar=screen.calendar
    )
    assert determination.height_18ft == "unknown"
    assert "neither calendar.txt nor calendar_dates.txt" in determination.summary()


def test_a_feed_defined_only_by_calendar_dates_still_resolves(tmp_path):
    files = _seasonal_feed()
    del files["calendar.txt"]
    files["calendar_dates.txt"] = "service_id,date,exception_type\nSUMMER,20260615,1\n"
    path = _write_feed(tmp_path / "datesonly.zip", files)
    screen = load_feed(path, as_of=date(2026, 6, 15))
    assert screen.calendar.status == "resolved"
    assert screen.calendar.calendar_source == "calendar_dates"
    assert screen.calendar.service_ids_active == ("SUMMER",)
    assert screen.stops[0].route_max_gaps["R1"] <= 15


def test_weekday_and_weekend_dates_give_different_headways(tmp_path):
    path = _write_feed(tmp_path / "seasonal.zip", _seasonal_feed())
    weekday = load_feed(path, as_of=date(2026, 6, 15))  # a Monday
    weekend = load_feed(path, as_of=date(2026, 6, 20))  # the Saturday after
    assert weekday.calendar.service_ids_active == ("SUMMER",)
    assert weekend.calendar.service_ids_active == ("WEEKEND",)
    assert weekday.stops[0].route_max_gaps != weekend.stops[0].route_max_gaps
    assert weekday.stops[0].hqtc_routes() == ["R1"]
    assert weekend.stops[0].hqtc_routes() == []


def test_an_expired_service_period_is_not_measured_because_it_is_bigger(tmp_path):
    # SPRING has the most trips and the best headways, and ended on 2026-05-31.
    # Selecting the busiest service picked it for every date in the feed.
    path = _write_feed(tmp_path / "seasonal.zip", _seasonal_feed())
    screen = load_feed(path, as_of=date(2026, 6, 15))
    assert "SPRING" not in screen.calendar.service_ids_active
    assert screen.stops[0].route_max_gaps["R1"] == 15  # SUMMER's, not SPRING's


def test_every_service_active_on_the_date_is_measured(tmp_path):
    # A supplemental service sharing a weekday with the base schedule used to
    # be dropped whole, because only the single busiest service_id was kept.
    files = _seasonal_feed()
    files["calendar.txt"] += "SUPPLEMENT,1,1,1,1,1,0,0,20260601,20260831\n"
    files["trips.txt"] += "R2,SUPPLEMENT,SUP0,0\nR2,SUPPLEMENT,SUP1,0\n"
    files["routes.txt"] += "R2,2,3\n"
    files["stop_times.txt"] += (
        "SUP0,07:00:00,07:00:00,S1,1\nSUP1,17:00:00,17:00:00,S1,1\n"
    )
    path = _write_feed(tmp_path / "supplement.zip", files)
    screen = load_feed(path, as_of=date(2026, 6, 15))
    assert screen.calendar.service_ids_active == ("SUMMER", "SUPPLEMENT")
    assert set(screen.stops[0].bus_routes) == {"R1", "R2"}


def test_an_exception_removing_every_service_states_itself_and_finds_nothing(tmp_path):
    files = _seasonal_feed(
        {"calendar_dates.txt": "service_id,date,exception_type\nSUMMER,20260615,2\n"}
    )
    path = _write_feed(tmp_path / "holiday.zip", files)
    screen = load_feed(path, as_of=date(2026, 6, 15))
    assert screen.calendar.status == "no_service_on_date"
    assert screen.calendar.service_ids_removed_by_exception == ("SUMMER",)
    determination = determine(
        38.5450, -121.7400, screen.stops, calendar=screen.calendar
    )
    # The feed answered, so this is a negative it supports -- not `unknown`.
    assert determination.height_18ft == "no"
    assert determination.qualifying_stops == []
    summary = determination.summary()
    assert "no service runs on 2026-06-15" in summary
    assert "removes service SUMMER" in summary


def test_an_exception_adding_service_on_an_excluded_day_is_honoured(tmp_path):
    files = _seasonal_feed(
        {"calendar_dates.txt": "service_id,date,exception_type\nSUMMER,20260620,1\n"}
    )
    path = _write_feed(tmp_path / "added.zip", files)
    saturday = load_feed(path, as_of=date(2026, 6, 20))
    assert saturday.calendar.service_ids_active == ("SUMMER", "WEEKEND")
    assert saturday.calendar.service_ids_added_by_exception == ("SUMMER",)


def test_the_statewide_dataset_still_answers_when_the_feed_calendar_does_not(tmp_path):
    # The statewide dataset carries its own currency and is not scoped by this
    # feed's calendar, so an unreadable feed must not suppress a candidate that
    # never depended on it.
    path = _write_feed(tmp_path / "seasonal.zip", _seasonal_feed())
    screen = load_feed(path)  # no as-of
    determination = determine(
        38.5449,
        -121.7405,
        screen.stops,
        hq_stops=[EXISTING_RAIL_STOP],
        calendar=screen.calendar,
    )
    assert determination.height_18ft == "candidate"
    assert determination.parking_exemption == "candidate"
    assert "Caltrans HQ Transit Stops dataset" in determination.qualifying_stops[0][2]


# --- The committed Unitrans feed ---------------------------------------

UNITRANS = Path(__file__).parent.parent / "corpus" / "gtfs" / "unitrans.zip"
DAVIS_SITE = (38.5449, -121.7442)


def test_unitrans_summer_weekday_and_sunday_name_different_service():
    weekday = load_feed(UNITRANS, as_of=date(2026, 8, 4))  # a Tuesday
    sunday = load_feed(UNITRANS, as_of=date(2026, 8, 9))
    assert weekday.calendar.status == "resolved"
    assert sunday.calendar.status == "resolved"
    assert weekday.calendar.service_ids_active != sunday.calendar.service_ids_active
    weekday_gaps = {
        s.stop_id: s.route_max_gaps for s in weekday.stops if s.route_max_gaps
    }
    sunday_gaps = {
        s.stop_id: s.route_max_gaps for s in sunday.stops if s.route_max_gaps
    }
    assert weekday_gaps != sunday_gaps


def test_unitrans_measures_real_service_on_a_date_inside_its_window():
    # The complement over the real corpus: a change that only ever reported
    # `unknown` would satisfy every withholding test above. It does not.
    screen = load_feed(UNITRANS, as_of=date(2026, 8, 4))
    assert screen.calendar.service_ids_active == ("71",)
    assert screen.calendar.feed_valid_from == "2026-07-20"
    assert screen.calendar.feed_valid_to == "2026-09-22"
    measured = {r for stop in screen.stops for r in stop.route_max_gaps}
    assert len(measured) > 10


def test_unitrans_finding_is_unchanged_once_the_date_is_stated():
    # The README's finding is that no *local bus* stop meets the encoded peak
    # screens and the statewide dataset supplies the Amtrak candidate. Naming a
    # date must not quietly change what the repository claims.
    from permit_pathways.transit import load_hq_stops

    screen = load_feed(UNITRANS, as_of=date(2026, 8, 4))
    assert not [s for s in screen.stops if s.hqtc_routes()]
    assert not [s for s in screen.stops if s.major_candidate_routes()]
    hq = load_hq_stops(
        Path(__file__).parent.parent / "corpus" / "transit" / "ca-hq-transit-stops.json"
    )
    determination = determine(
        *DAVIS_SITE, screen.stops, hq_stops=hq, calendar=screen.calendar
    )
    assert determination.height_18ft == "candidate"
    assert "major_stop_rail" in determination.qualifying_stops[0][2]


def test_unitrans_labor_day_monday_runs_the_sunday_service_the_exception_names():
    # 2026-09-07 is a Monday. `calendar.txt` puts service 71 on Mondays;
    # `calendar_dates.txt` removes 71 and adds 79, the weekend service. A
    # reader of `calendar.txt` alone measures a schedule that does not run.
    holiday = load_feed(UNITRANS, as_of=date(2026, 9, 7))
    ordinary_monday = load_feed(UNITRANS, as_of=date(2026, 8, 31))
    assert ordinary_monday.calendar.service_ids_active == ("71",)
    assert holiday.calendar.service_ids_active == ("79",)
    assert holiday.calendar.service_ids_removed_by_exception == ("71",)
    assert holiday.calendar.service_ids_added_by_exception == ("79",)


def test_unitrans_outside_its_published_window_is_unknown_not_a_negative():
    screen = load_feed(UNITRANS, as_of=date(2026, 10, 1))
    assert screen.calendar.status == "outside_feed_window"
    determination = determine(*DAVIS_SITE, screen.stops, calendar=screen.calendar)
    assert determination.height_18ft == "unknown"
    assert determination.parking_exemption == "unknown"
    assert "outside the validity window" in determination.summary()


@pytest.mark.parametrize(
    ("as_of", "files", "expected_status"),
    [
        (None, _seasonal_feed(), "no_as_of"),
        (date(2026, 12, 5), None, "outside_feed_window"),
        (date(2026, 6, 15), "no-calendar", "no_calendar"),
    ],
)
def test_an_unresolved_calendar_names_no_active_service(
    tmp_path, as_of, files, expected_status
):
    # The real invariant behind the headway skip in `load_feed`: a state that
    # is not `resolved` must never carry service ids. If it did, a caller that
    # measures over `service_ids_active` -- or a future refactor that drops the
    # skip as redundant -- would measure a schedule nobody vouched for.
    if files is None:
        files = _seasonal_feed(
            {
                "feed_info.txt": (
                    "feed_publisher_name,feed_publisher_url,feed_lang,"
                    "feed_start_date,feed_end_date\n"
                    "Test,http://example.invalid,en,20260601,20260831\n"
                )
            }
        )
    elif files == "no-calendar":
        files = _seasonal_feed()
        del files["calendar.txt"]
    path = _write_feed(tmp_path / f"{expected_status}.zip", files)
    screen = load_feed(path, as_of=as_of)
    assert screen.calendar.status == expected_status
    assert screen.calendar.service_ids_active == ()
    assert not screen.calendar.headways_measurable


def test_a_feed_without_frequencies_does_not_claim_headway_defined_trips(tmp_path):
    # `frequencies.txt` is not expanded, so its presence is disclosed rather
    # than silently measured around. A missing file and an empty one are
    # different facts and must not collapse into "present".
    plain = _write_feed(tmp_path / "plain.zip", _seasonal_feed())
    assert (
        load_feed(plain, as_of=date(2026, 6, 15)).calendar.frequency_based_trips
        is False
    )

    with_frequencies = _write_feed(
        tmp_path / "freq.zip",
        _seasonal_feed(
            {
                "frequencies.txt": (
                    "trip_id,start_time,end_time,headway_secs\n"
                    "SUMMER0,06:00:00,09:00:00,600\n"
                )
            }
        ),
    )
    resolved = load_feed(with_frequencies, as_of=date(2026, 6, 15)).calendar
    assert resolved.frequency_based_trips is True
    assert "frequencies.txt" in resolved.reason()


# --- Several operators, and what a negative is bounded to (issue #133) ---
#
# A site is served by whoever serves it, not by whoever published the feed
# someone happened to supply. Near the Davis depot that is Unitrans, Yolobus,
# Capitol Corridor and Amtrak thruway buses; the committed corpus screens one
# of them. These tests pin three things: several feeds screen as one set with
# their ids kept apart, a run says which operators it covered, and a negative
# is withheld when it cannot say that.

from permit_pathways.transit import (  # noqa: E402
    COVERAGE_BOUNDED,
    COVERAGE_COMPLETE,
    COVERAGE_UNKNOWN,
    FeedCoverage,
    _normalise_operator,
    assess_coverage,
    feed_agencies,
    load_feeds,
)

AGENCY_ALPHA = (
    "agency_id,agency_name,agency_url,agency_timezone\n"
    "alpha,Alpha Transit,http://alpha.invalid,America/Los_Angeles\n"
)
AGENCY_BETA = (
    "agency_id,agency_name,agency_url,agency_timezone\n"
    "beta,Beta Transit,http://beta.invalid,America/Los_Angeles\n"
)


def _rows(block):
    """Header line plus the remaining non-empty lines of a fixture CSV."""
    lines = [line for line in block.splitlines() if line.strip()]
    return lines[0], lines[1:]


def _subset_feed(stop_ids, route_ids, agency):
    """The slice of ``FILES`` covering these stops and routes, as its own feed.

    Derived from the single-feed fixture rather than retyped, so the split and
    merged feeds cannot drift apart and make the equivalence test vacuous.
    """
    stops_header, stops_rows = _rows(FILES["stops.txt"])
    routes_header, routes_rows = _rows(FILES["routes.txt"])
    trips_header, trips_rows = _rows(FILES["trips.txt"])
    times_header, times_rows = _rows(FILES["stop_times.txt"])

    kept_trips = [r for r in trips_rows if r.split(",")[0] in route_ids]
    kept_trip_ids = {r.split(",")[2] for r in kept_trips}
    kept_times = [
        r
        for r in times_rows
        if r.split(",")[0] in kept_trip_ids and r.split(",")[3] in stop_ids
    ]
    return {
        "agency.txt": agency,
        "stops.txt": stops_header
        + "\n"
        + "\n".join(r for r in stops_rows if r.split(",")[0] in stop_ids)
        + "\n",
        "routes.txt": routes_header
        + "\n"
        + "\n".join(r for r in routes_rows if r.split(",")[0] in route_ids)
        + "\n",
        "calendar.txt": FILES["calendar.txt"],
        "trips.txt": trips_header + "\n" + "\n".join(kept_trips) + "\n",
        "stop_times.txt": times_header + "\n" + "\n".join(kept_times) + "\n",
    }


@pytest.fixture()
def split_feeds(tmp_path):
    """The one-feed fixture cut in two along the corner it clusters at.

    S1 (routes A and B) goes to one operator, S2 (route C) to the other. The
    § 21064.3 bus branch needs two qualifying routes at one intersection, and
    after the split neither feed has two on its own.
    """
    alpha = _write_feed(
        tmp_path / "alpha.zip", _subset_feed({"S1", "FAR"}, {"A", "B"}, AGENCY_ALPHA)
    )
    beta = _write_feed(tmp_path / "beta.zip", _subset_feed({"S2"}, {"C"}, AGENCY_BETA))
    return [alpha, beta]


def test_two_feeds_at_one_corner_answer_as_the_merged_feed_does(split_feeds, feed_path):
    # Done-when 1. Splitting one operator's stops across two feeds must not
    # change the answer, and the corner rule has to reach across feeds for
    # that to hold: each feed alone has one qualifying route at the corner.
    merged = load_feed(feed_path, as_of=FIXTURE_SERVICE_DATE)
    several = load_feeds(split_feeds, as_of=FIXTURE_SERVICE_DATE)

    from_merged = determine(38.5452, -121.7401, merged.stops, calendar=merged.calendar)
    from_several = determine(
        38.5452, -121.7401, several.stops, calendar=several.calendar
    )
    assert (
        from_merged.parking_exemption == from_several.parking_exemption == "candidate"
    )
    assert from_merged.height_18ft == from_several.height_18ft == "candidate"
    assert [reason for _s, _m, reason in from_merged.qualifying_stops] == [
        reason for _s, _m, reason in from_several.qualifying_stops
    ]
    assert [stop.name for stop, _m, _r in from_merged.qualifying_stops] == [
        stop.name for stop, _m, _r in from_several.qualifying_stops
    ]


def test_one_feed_of_the_split_pair_cannot_reach_the_two_route_threshold(
    split_feeds,
):
    # The control for the test above. Written first as "each half alone
    # returns no candidate", which failed: each half has one route at
    # <=15-minute peaks, so each half alone is already a § 21155(b)
    # high-quality-corridor candidate on its own. The half the split actually
    # destroys is the § 21064.3 *major transit stop*, which needs two
    # qualifying routes at one intersection — so that is what the control
    # asserts, and what crossing feeds has to restore.
    for single in split_feeds:
        alone = load_feeds([single], as_of=FIXTURE_SERVICE_DATE)
        determination = determine(
            38.5452, -121.7401, alone.stops, calendar=alone.calendar
        )
        reasons = [reason for _s, _m, reason in determination.qualifying_stops]
        assert reasons, "each half alone still has a corridor-quality route"
        assert all("high-quality transit corridor" in r for r in reasons)
        assert not any("major transit stop" in r for r in reasons)

    several = load_feeds(split_feeds, as_of=FIXTURE_SERVICE_DATE)
    together = determine(38.5452, -121.7401, several.stops, calendar=several.calendar)
    assert all(
        "major transit stop" in reason for _s, _m, reason in together.qualifying_stops
    )


def test_two_operators_route_1_are_two_routes_not_one(tmp_path):
    # PRC § 21064.3's bus branch counts two or more qualifying routes at one
    # intersection. Two operators both numbering a route "1" is the ordinary
    # case, and merging their ids would collapse them into one route and deny
    # a candidate that exists.
    def one_route_feed(stop_id, lat, lon, agency):
        times = _peak_times(13, 15)
        return {
            "agency.txt": agency,
            "stops.txt": (
                f"stop_id,stop_name,stop_lat,stop_lon\n{stop_id},Corner,{lat},{lon}\n"
            ),
            "routes.txt": "route_id,route_short_name,route_type\n1,1,3\n",
            "calendar.txt": FILES["calendar.txt"],
            "trips.txt": "route_id,service_id,trip_id,direction_id\n"
            + "".join(f"1,WK,T{i},0\n" for i in range(len(times))),
            "stop_times.txt": (
                "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                + "".join(
                    f"T{i},{hms},{hms},{stop_id},1\n" for i, hms in enumerate(times)
                )
            ),
        }

    north = _write_feed(
        tmp_path / "north.zip", one_route_feed("1", 38.5450, -121.7400, AGENCY_ALPHA)
    )
    south = _write_feed(
        tmp_path / "south.zip", one_route_feed("1", 38.5455, -121.7402, AGENCY_BETA)
    )
    several = load_feeds([north, south], as_of=FIXTURE_SERVICE_DATE)
    assert sorted(s.stop_id for s in several.stops) == ["north:1", "south:1"]
    assert sorted(r for s in several.stops for r in s.route_max_gaps) == [
        "north:1",
        "south:1",
    ]
    determination = determine(
        38.5452, -121.7401, several.stops, calendar=several.calendar
    )
    assert determination.height_18ft == "candidate"
    assert "major transit stop" in determination.qualifying_stops[0][2]


def test_two_feeds_with_the_same_filename_do_not_share_a_namespace(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = _write_feed(
        tmp_path / "a" / "gtfs.zip",
        _subset_feed({"S1", "FAR"}, {"A", "B"}, AGENCY_ALPHA),
    )
    second = _write_feed(
        tmp_path / "b" / "gtfs.zip", _subset_feed({"S2"}, {"C"}, AGENCY_BETA)
    )
    several = load_feeds([first, second], as_of=FIXTURE_SERVICE_DATE)
    assert [feed.key for feed in several.feeds] == ["gtfs", "gtfs-2"]
    assert len({s.stop_id for s in several.stops}) == len(several.stops)


def test_feed_agency_names_are_read_verbatim():
    assert feed_agencies(UNITRANS) == ("Unitrans",)


def test_a_feed_that_names_no_agency_reports_none_rather_than_guessing(tmp_path):
    files = _subset_feed({"S2"}, {"C"}, AGENCY_BETA)
    del files["agency.txt"]
    path = _write_feed(tmp_path / "anonymous.zip", files)
    assert feed_agencies(path) == ()
    several = load_feeds([path], as_of=FIXTURE_SERVICE_DATE)
    assert several.operators_supplied == ()
    assert several.feeds_without_declared_agency == ("anonymous",)


# --- Operator coverage --------------------------------------------------


def test_unitrans_alone_near_davis_is_bounded_and_names_who_is_missing():
    # Done-when 2, over the committed corpus rather than a fixture. The
    # statewide dataset lists Amtrak and Capitol Corridor as serving operating
    # stops within a half mile of the README site; neither feed was supplied.
    from permit_pathways.transit import load_hq_stops

    several = load_feeds([UNITRANS], as_of=date(2026, 8, 4))
    hq = load_hq_stops(
        Path(__file__).parent.parent / "corpus" / "transit" / "ca-hq-transit-stops.json"
    )
    coverage = several.coverage(*DAVIS_SITE, hq)
    assert coverage.operators_supplied == ("Unitrans",)
    assert coverage.operators_listed_not_supplied == (
        "Amtrak",
        "Capitol Corridor Joint Powers Authority",
    )
    assert coverage.completeness == COVERAGE_BOUNDED
    assert "Capitol Corridor Joint Powers Authority" in coverage.reason()


def test_a_planned_operator_is_not_counted_as_a_missing_one():
    # Every Yolo TD row within a half mile of the README site is one an MPO
    # submitted as planned. A facility that does not exist yet cannot show
    # that its agency serves this location today, so not having Yolo TD's feed
    # does not make the screen more bounded than it is.
    from permit_pathways.transit import load_hq_stops

    several = load_feeds([UNITRANS], as_of=date(2026, 8, 4))
    hq = load_hq_stops(
        Path(__file__).parent.parent / "corpus" / "transit" / "ca-hq-transit-stops.json"
    )
    coverage = several.coverage(*DAVIS_SITE, hq)
    assert "Yolo TD" not in coverage.operators_listed_not_supplied
    planned_nearby = [
        s
        for s in hq
        if s.is_planned
        and s.agency == "Yolo TD"
        and haversine_miles(s.lat, s.lon, *DAVIS_SITE) <= 0.5
    ]
    assert planned_nearby, "the fixture premise: Yolo TD is listed here, as planned"


def test_a_bounded_run_still_reports_the_candidate_the_state_dataset_supplies():
    # Withholding a negative is not the same as withholding an answer. The
    # Davis finding the README states must survive the coverage disclosure.
    from permit_pathways.transit import load_hq_stops

    several = load_feeds([UNITRANS], as_of=date(2026, 8, 4))
    hq = load_hq_stops(
        Path(__file__).parent.parent / "corpus" / "transit" / "ca-hq-transit-stops.json"
    )
    determination = determine(
        *DAVIS_SITE,
        several.stops,
        hq_stops=hq,
        calendar=several.calendar,
        coverage=several.coverage(*DAVIS_SITE, hq),
    )
    assert determination.height_18ft == "candidate"
    assert "major_stop_rail" in determination.qualifying_stops[0][2]
    assert "BOUNDED" in determination.summary()


def test_no_feed_at_all_is_unknown_not_complete():
    # Done-when 3. Nothing was supplied, so nothing was covered; the screen
    # rests on the statewide dataset alone and says so.
    coverage = assess_coverage(*DAVIS_SITE, [EXISTING_RAIL_STOP], feeds_supplied=0)
    assert coverage.completeness == COVERAGE_UNKNOWN
    assert coverage.operators_supplied == ()
    assert "no transit feed was supplied" in coverage.reason().lower()


def test_no_feed_at_all_yields_only_statewide_candidates_and_no_negative():
    several = load_feeds([], as_of=date(2026, 8, 4))
    assert several.stops == []
    coverage = several.coverage(*DAVIS_SITE, [EXISTING_RAIL_STOP])
    assert coverage.completeness == COVERAGE_UNKNOWN

    found = determine(
        *DAVIS_SITE,
        several.stops,
        hq_stops=[EXISTING_RAIL_STOP],
        calendar=several.calendar,
        coverage=coverage,
    )
    assert found.height_18ft == "candidate"
    assert all("Caltrans" in reason for _s, _m, reason in found.qualifying_stops)

    # Far from the one dataset row: nothing was found, and with no operator
    # feed nothing supports calling that an absence.
    nothing = determine(
        38.9000,
        -121.4000,
        several.stops,
        hq_stops=[EXISTING_RAIL_STOP],
        calendar=several.calendar,
        coverage=several.coverage(38.9000, -121.4000, [EXISTING_RAIL_STOP]),
    )
    assert nothing.height_18ft == "unknown"
    assert nothing.parking_exemption == "unknown"
    assert "no transit feed was supplied" in nothing.summary()


def test_a_complete_run_still_reports_a_negative(split_feeds):
    # The complement, and the point of running it. A change that only ever
    # reported `unknown` would satisfy every withholding test above and make
    # the screen useless. Both operators the dataset lists near this point
    # were supplied, so "no qualifying stop" is a finding the run can make.
    several = load_feeds(split_feeds, as_of=FIXTURE_SERVICE_DATE)
    remote = (38.9000, -121.4000)
    hq = [EXISTING_RAIL_STOP]  # 30+ miles away: listed, but not near this site
    coverage = several.coverage(*remote, hq)
    assert coverage.completeness == COVERAGE_COMPLETE
    assert coverage.operators_supplied == ("Alpha Transit", "Beta Transit")
    determination = determine(
        *remote,
        several.stops,
        hq_stops=hq,
        calendar=several.calendar,
        coverage=coverage,
    )
    assert determination.parking_exemption == "no"
    assert determination.height_18ft == "no"
    assert "complete against the statewide Caltrans list" in determination.summary()


def test_without_a_statewide_dataset_nothing_cross_checks_the_operator_list(
    split_feeds,
):
    # An absent check is not a passed one. With no dataset to compare against,
    # "no agency is missing" is vacuous, and reading it as complete would let
    # a one-operator run report a site-wide negative.
    several = load_feeds(split_feeds, as_of=FIXTURE_SERVICE_DATE)
    coverage = several.coverage(38.9000, -121.4000, None)
    assert coverage.cross_checked is False
    assert coverage.completeness == COVERAGE_BOUNDED
    assert coverage.operators_listed_not_supplied == ()
    assert "No statewide dataset was supplied" in coverage.reason()
    determination = determine(
        38.9000,
        -121.4000,
        several.stops,
        calendar=several.calendar,
        coverage=coverage,
    )
    assert determination.parking_exemption == "unknown"
    assert determination.height_18ft == "unknown"


def test_a_feed_that_cannot_name_itself_bounds_the_screen(tmp_path):
    files = _subset_feed({"S1", "FAR"}, {"A", "B"}, AGENCY_ALPHA)
    del files["agency.txt"]
    path = _write_feed(tmp_path / "anonymous.zip", files)
    several = load_feeds([path], as_of=FIXTURE_SERVICE_DATE)
    coverage = several.coverage(38.9000, -121.4000, [EXISTING_RAIL_STOP])
    assert coverage.completeness == COVERAGE_BOUNDED
    assert coverage.feeds_without_declared_agency == ("anonymous",)
    assert "declare no agency name" in coverage.reason()


def test_an_operating_row_with_no_agency_name_bounds_the_screen():
    # The statewide snapshot leaves `agency` blank on 2,283 rows. Every one of
    # them is currently a planned row, so this case is unreachable from the
    # committed corpus today — which is exactly why it is pinned on a fixture:
    # a later snapshot that blanks an operating row must not have that blank
    # counted as an operator who was supplied.
    unnamed = HQStop(
        lat=38.5450,
        lon=-121.7440,
        hqta_type="major_stop_bus",
        details="major_stop_bus_intersection",
        agency=" ",
    )
    coverage = assess_coverage(
        *DAVIS_SITE,
        [unnamed],
        operators_supplied=("Unitrans",),
        feeds_supplied=1,
    )
    assert coverage.unnamed_listed_stops == 1
    assert coverage.operators_listed_not_supplied == ()
    assert coverage.completeness == COVERAGE_BOUNDED
    assert "name no agency" in coverage.reason()


def test_the_committed_snapshot_blanks_an_agency_only_on_planned_rows():
    # The premise of the test above, measured rather than assumed. If a future
    # snapshot breaks it, the fixture case has become reachable and this test
    # is where that shows up.
    from permit_pathways.transit import load_hq_stops

    hq = load_hq_stops(
        Path(__file__).parent.parent / "corpus" / "transit" / "ca-hq-transit-stops.json"
    )
    unnamed = [s for s in hq if not s.agency.strip()]
    assert unnamed
    assert all(s.is_planned for s in unnamed)


def test_operator_names_match_across_punctuation_but_never_fuzzily():
    # A false match invents coverage the run does not have; a false miss only
    # over-reports incompleteness. The comparison is aimed away from the first.
    assert _normalise_operator(
        "Capitol Corridor Joint-Powers Authority"
    ) == _normalise_operator("capitol corridor joint powers authority")
    assert _normalise_operator("Yolo  County  Transportation") == (
        "yolo county transportation"
    )
    # An abbreviation does not fold into its expansion. That is the safe
    # direction: it can only report the screen as more bounded than it is.
    assert _normalise_operator("Capitol Corridor J.P.A.") == "capitol corridor j p a"
    assert _normalise_operator("Capitol Corridor J.P.A.") != _normalise_operator(
        "Capitol Corridor JPA"
    )
    assert _normalise_operator("AC Transit") != _normalise_operator(
        "Alameda-Contra Costa Transit District"
    )

    near_miss = assess_coverage(
        *DAVIS_SITE,
        [
            HQStop(
                lat=38.5450,
                lon=-121.7440,
                hqta_type="major_stop_bus",
                details="major_stop_bus_intersection",
                agency="Unitrans Davis",
            )
        ],
        operators_supplied=("Unitrans",),
        feeds_supplied=1,
    )
    assert near_miss.operators_listed_not_supplied == ("Unitrans Davis",)
    assert near_miss.completeness == COVERAGE_BOUNDED


def test_the_three_coverage_states_are_the_published_strings():
    # These strings are the screen's own vocabulary and reach a reader. A
    # property test over the state machine would not notice one of them being
    # renamed or, worse, a fourth being introduced that nothing reads.
    assert COVERAGE_COMPLETE == "complete"
    assert COVERAGE_BOUNDED == "bounded"
    assert COVERAGE_UNKNOWN == "unknown"
    assert (
        FeedCoverage(
            operators_supplied=(),
            operators_listed_not_supplied=(),
            feeds_without_declared_agency=(),
            unnamed_listed_stops=0,
            listed_operating_stops=0,
            feeds_supplied=1,
            cross_checked=True,
            completeness=COVERAGE_COMPLETE,
        ).supports_a_negative
        is True
    )
    for state in (COVERAGE_BOUNDED, COVERAGE_UNKNOWN):
        assert (
            FeedCoverage(
                operators_supplied=(),
                operators_listed_not_supplied=(),
                feeds_without_declared_agency=(),
                unnamed_listed_stops=0,
                listed_operating_stops=0,
                feeds_supplied=1,
                cross_checked=True,
                completeness=state,
            ).supports_a_negative
            is False
        )


# --- Feeds that disagree about the date ---------------------------------


def test_one_unreadable_feed_does_not_erase_another_feeds_measurement(
    split_feeds, tmp_path
):
    # Alpha resolves for the date; Beta ships no calendar at all. The old
    # single-calendar gate was global, so one unreadable feed would have
    # discarded every stop including the ones that were measured.
    beta_files = _subset_feed({"S2"}, {"C"}, AGENCY_BETA)
    del beta_files["calendar.txt"]
    broken_beta = _write_feed(tmp_path / "beta-nocal.zip", beta_files)
    several = load_feeds([split_feeds[0], broken_beta], as_of=FIXTURE_SERVICE_DATE)

    by_feed = {s.feed: s for s in several.stops}
    assert by_feed["alpha"].headways_measured is True
    assert by_feed["beta-nocal"].headways_measured is False
    assert several.calendar.headways_measurable is True
    assert several.calendar.supports_a_negative is False
    assert several.calendar.status == "mixed"

    # Alpha's route A is still measured at ~10-minute peaks, so the corridor
    # candidate it establishes survives.
    determination = determine(
        38.5452, -121.7401, several.stops, calendar=several.calendar
    )
    assert determination.height_18ft == "candidate"
    assert "high-quality transit corridor" in determination.qualifying_stops[0][2]


def test_an_unreadable_feeds_stops_are_not_read_as_absent_service(
    split_feeds, tmp_path
):
    # The other half: Beta's stop is present and has no headways, and that
    # blank must not be counted as "this corner has no qualifying service".
    beta_files = _subset_feed({"S2"}, {"C"}, AGENCY_BETA)
    del beta_files["calendar.txt"]
    broken_beta = _write_feed(tmp_path / "beta-nocal.zip", beta_files)
    only_beta = load_feeds([broken_beta], as_of=FIXTURE_SERVICE_DATE)
    determination = determine(
        38.5452, -121.7401, only_beta.stops, calendar=only_beta.calendar
    )
    assert determination.height_18ft == "unknown"
    assert determination.parking_exemption == "unknown"
    assert "beta-nocal: " in determination.summary()
    assert "neither calendar.txt nor calendar_dates.txt" in determination.summary()


def test_a_multi_feed_screen_names_each_feeds_service_ids_apart(split_feeds):
    several = load_feeds(split_feeds, as_of=FIXTURE_SERVICE_DATE)
    assert several.calendar.service_ids_active == ("alpha:WK", "beta:WK")
    assert several.calendar.service_date == "2026-06-15"
    assert several.calendar.status == "resolved"
