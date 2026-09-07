"""Walking distance over an offline pedestrian network.

The fixtures are two hand-written OSM XML extracts that differ in exactly one
tag. In `barrier.osm` the only direct line between the site and the stop is a
freeway ramp (way 104, `highway=motorway_link`) beside a service road signed
`foot=no` (way 105), so the walk goes 550 m east, 300 m across and 550 m back:
1400 m for a 300 m straight line. In `no-barrier.osm` way 104 is a footbridge
and the two distances agree.

That one-tag difference is the point. If the graph rules ever let a motorway
or a `foot=no` street through, the barrier fixture measures 300 m and the
whole module reports the optimistic number it exists to stop reporting.

Way 104 carries `foot=yes` in both files, and that is deliberate. Without it,
`motorway_link` would be excluded merely by being absent from the walkable
set, the exclusion set would carry no weight in this fixture, and a control
that deleted a value from `EXCLUDED_HIGHWAY` would pass. With it, the
fixture exercises the rule the ADR actually states.
"""

from __future__ import annotations

import gzip
import json
import math
import subprocess  # nosec B404
import sys
from pathlib import Path

import pytest

from permit_pathways.pedestrian import (
    DEFAULT_SNAP_MAX_M,
    EARTH_RADIUS_M,
    EXCLUDED_HIGHWAY,
    STATUS_DISCONNECTED,
    STATUS_MEASURED,
    STATUS_NOT_IN_EXTRACT,
    STATUS_SNAP_TOO_FAR,
    WALKABLE_HIGHWAY,
    NetworkBounds,
    PedestrianNetworkError,
    haversine_meters,
    load_graph_json,
    load_network,
    load_osm_xml,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "pedestrian"
BARRIER = FIXTURES / "barrier.osm"
NO_BARRIER = FIXTURES / "no-barrier.osm"

# The fixtures were generated against this module's own earth radius, so a
# leg the fixture calls 300 m measures 300 m here.
LAT0, LON0 = 38.5400, -121.7400
_M_PER_DEG_LAT = math.pi * EARTH_RADIUS_M / 180.0
_M_PER_DEG_LON = _M_PER_DEG_LAT * math.cos(math.radians(LAT0))


def point(east_m: float, north_m: float) -> tuple[float, float]:
    return (LAT0 + north_m / _M_PER_DEG_LAT, LON0 + east_m / _M_PER_DEG_LON)


SITE = point(0, 0)
STOP = point(0, 300)
ORPHAN = point(320, 60)
OUTSIDE = point(4000, 4000)


def _osm(*ways: str, nodes: str = "") -> str:
    default_nodes = """
  <node id="1" lat="38.5400000" lon="-121.7400000"/>
  <node id="2" lat="38.5426947" lon="-121.7400000"/>
"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<osm version="0.6" generator="test">\n'
        + (nodes or default_nodes)
        + "\n".join(ways)
        + "\n</osm>\n"
    )


def _way(*tags: tuple[str, str], refs: tuple[int, int] = (1, 2)) -> str:
    rows = "".join(f'    <nd ref="{ref}"/>\n' for ref in refs)
    rows += "".join(f'    <tag k="{k}" v="{v}"/>\n' for k, v in tags)
    return f'  <way id="900">\n{rows}  </way>'


# --- The barrier case, which is the whole reason for the module -----------


def test_a_stop_across_a_barrier_is_300_m_away_and_1400_m_on_foot() -> None:
    network = load_network(BARRIER)
    result = network.walk(*SITE, *STOP)
    assert result.walking_status == STATUS_MEASURED
    assert round(result.straight_line_m) == 300
    assert round(result.walking_m or 0) == 1400
    # The straight line is not merely different; it is optimistic by 4.7x.
    assert (result.walking_m or 0) > result.straight_line_m * 4


def test_removing_the_barrier_makes_the_two_distances_agree() -> None:
    """One tag differs between the fixtures: way 104's `highway` value."""
    result = load_network(NO_BARRIER).walk(*SITE, *STOP)
    assert result.walking_status == STATUS_MEASURED
    assert round(result.straight_line_m) == 300
    # Within snap tolerance: both endpoints are on the network, so both snaps
    # are zero and the walk is the footbridge itself.
    assert abs((result.walking_m or 0) - result.straight_line_m) <= DEFAULT_SNAP_MAX_M
    assert round(result.walking_m or 0) == 300


def test_the_two_fixtures_differ_only_in_that_one_tag() -> None:
    """Non-vacuity: if they differed elsewhere, the comparison proves nothing."""
    barrier = BARRIER.read_text(encoding="utf-8").splitlines()
    no_barrier = NO_BARRIER.read_text(encoding="utf-8").splitlines()
    differing = [
        (left, right)
        for left, right in zip(barrier, no_barrier, strict=True)
        # The leading comment describes each file and is expected to differ.
        if left != right and not left.lstrip().startswith("<!--")
    ]
    assert [left.strip() for left, _ in differing] == [
        '<tag k="highway" v="motorway_link"/>',
        '<tag k="name" v="Freeway ramp"/>',
    ]
    assert [right.strip() for _, right in differing] == [
        '<tag k="highway" v="footway"/>',
        '<tag k="name" v="Footbridge"/>',
    ]


# --- The three states that carry no number --------------------------------


def test_a_stop_outside_the_extract_yields_no_walking_figure() -> None:
    result = load_network(BARRIER).walk(*SITE, *OUTSIDE)
    assert result.walking_status == STATUS_NOT_IN_EXTRACT
    assert result.walking_m is None
    # The straight line is still reported; it is the walk that is withheld.
    assert result.straight_line_m > 5000


def test_a_site_outside_the_extract_withholds_every_walk() -> None:
    results = load_network(BARRIER).walk_many(*OUTSIDE, [STOP, SITE])
    assert [r.walking_status for r in results] == [
        STATUS_NOT_IN_EXTRACT,
        STATUS_NOT_IN_EXTRACT,
    ]
    assert all(r.walking_m is None for r in results)


def test_a_stop_too_far_from_any_path_is_not_attached_to_one() -> None:
    result = load_network(BARRIER).walk(*SITE, *point(275, 150), snap_max_m=10.0)
    assert result.walking_status == STATUS_SNAP_TOO_FAR
    assert result.walking_m is None
    assert (result.destination_snap_m or 0) > 10.0


def test_a_stop_on_an_unreachable_fragment_is_disconnected_not_unreachable() -> None:
    result = load_network(BARRIER).walk(*SITE, *ORPHAN)
    assert result.walking_status == STATUS_DISCONNECTED
    assert result.walking_m is None
    # Both ends snapped: this is a statement about the extract's coverage.
    assert result.site_snap_m == pytest.approx(0.0, abs=1.0)
    assert (result.destination_snap_m or 0) < DEFAULT_SNAP_MAX_M


def test_no_status_but_measured_ever_carries_a_distance() -> None:
    network = load_network(BARRIER)
    for result in network.walk_many(*SITE, [STOP, OUTSIDE, ORPHAN, point(275, 150)]):
        assert (result.walking_m is None) is (
            result.walking_status != STATUS_MEASURED
        ), result
        # And a withheld walk never quietly equals the straight line.
        if result.walking_m is None:
            assert result.to_dict()["walking_m"] is None


# --- Graph rules (ADR 0007) -----------------------------------------------


#: Written out rather than taken from `EXCLUDED_HIGHWAY`, because a fixture
#: derived from the constant it tests can never catch a wrong constant:
#: deleting a value from the set would delete its own test case with it. This
#: list has to be edited deliberately, and ADR 0007 is where the argument for
#: each entry lives.
NEVER_WALKABLE = (
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "construction",
    "proposed",
    "raceway",
    "bus_guideway",
)


def test_the_excluded_set_is_exactly_the_one_adr_0007_records() -> None:
    assert sorted(EXCLUDED_HIGHWAY) == sorted(NEVER_WALKABLE)


@pytest.mark.parametrize("highway", NEVER_WALKABLE)
def test_an_excluded_way_is_not_walkable_even_when_tagged_foot_yes(
    tmp_path: Path, highway: str
) -> None:
    """A mapped shoulder is not a footpath, and reading it as one is the
    optimistic answer this module exists to stop.

    `foot=yes` is the case that matters: without it these values are already
    outside the walkable set, so the exclusion set would carry no weight and
    a control that removed a value from it would pass.
    """
    path = tmp_path / "x.osm"
    path.write_text(_osm(_way(("highway", highway), ("foot", "yes"))), encoding="utf-8")
    with pytest.raises(PedestrianNetworkError, match="no walkable way"):
        load_osm_xml(path)


def test_foot_no_removes_an_otherwise_walkable_street(tmp_path: Path) -> None:
    path = tmp_path / "x.osm"
    path.write_text(
        _osm(_way(("highway", "residential"), ("foot", "no"))), encoding="utf-8"
    )
    with pytest.raises(PedestrianNetworkError, match="no walkable way"):
        load_osm_xml(path)


def test_foot_yes_adds_a_way_whose_highway_value_is_not_in_the_walkable_set(
    tmp_path: Path,
) -> None:
    path = tmp_path / "x.osm"
    path.write_text(
        _osm(_way(("highway", "cycleway"), ("foot", "designated"))), encoding="utf-8"
    )
    network = load_osm_xml(path)
    assert len(network.nodes) == 2
    assert "cycleway" not in WALKABLE_HIGHWAY


def test_access_private_is_removed_unless_foot_says_otherwise(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked.osm"
    blocked.write_text(
        _osm(_way(("highway", "service"), ("access", "private"))), encoding="utf-8"
    )
    with pytest.raises(PedestrianNetworkError, match="no walkable way"):
        load_osm_xml(blocked)
    allowed = tmp_path / "allowed.osm"
    allowed.write_text(
        _osm(_way(("highway", "service"), ("access", "private"), ("foot", "yes"))),
        encoding="utf-8",
    )
    assert len(load_osm_xml(allowed).nodes) == 2


def test_edges_are_undirected_because_oneway_restricts_vehicles(
    tmp_path: Path,
) -> None:
    path = tmp_path / "x.osm"
    path.write_text(
        _osm(_way(("highway", "residential"), ("oneway", "yes"))), encoding="utf-8"
    )
    network = load_osm_xml(path)
    assert network.shortest_path_meters(1, 2) == pytest.approx(300, abs=1)
    assert network.shortest_path_meters(2, 1) == pytest.approx(300, abs=1)


# --- Reading the file -----------------------------------------------------


def test_provenance_names_the_file_its_digest_and_its_bounds() -> None:
    network = load_network(BARRIER)
    provenance = network.provenance()
    assert provenance["source"] == "barrier.osm"
    assert provenance["sha256"].startswith("sha256:")
    assert len(provenance["sha256"]) == len("sha256:") + 64
    assert provenance["nodes"] == 6
    # Ways 104 and 105 are excluded, so four of the six are read.
    assert provenance["ways"] == 4
    bounds = provenance["bounds"]
    assert bounds["min_lat"] < LAT0 < bounds["max_lat"]
    assert network.describe().startswith("Pedestrian network: barrier.osm")


def test_the_declared_bounds_are_used_rather_than_the_node_extent() -> None:
    """A clipped extract's `<bounds>` is wider than its nodes, and that
    difference is exactly the strip where a stop is inside the extract but has
    nothing near to snap to."""
    network = load_network(BARRIER)
    lats = [lat for lat, _ in network.nodes.values()]
    assert network.bounds.min_lat < min(lats)
    assert network.bounds.max_lat > max(lats)


def test_a_gzipped_extract_reads_to_the_same_graph(tmp_path: Path) -> None:
    compressed = tmp_path / "barrier.osm.gz"
    compressed.write_bytes(gzip.compress(BARRIER.read_bytes()))
    plain = load_network(BARRIER)
    zipped = load_network(compressed)
    assert zipped.nodes == plain.nodes
    assert zipped.edges == plain.edges
    # The digest is of the file, so it differs — which is right: a different
    # file is a different provenance record even for the same graph.
    assert zipped.source_sha256 != plain.source_sha256


def test_a_way_referencing_a_node_outside_the_clip_drops_the_reference(
    tmp_path: Path,
) -> None:
    path = tmp_path / "x.osm"
    path.write_text(
        _osm(_way(("highway", "footway"), refs=(1, 999, 2))), encoding="utf-8"
    )
    network = load_osm_xml(path)
    # 1 and 2 are joined directly rather than through a node that is not here;
    # joining across the gap would invent an edge of unknown length.
    assert set(network.nodes) == {1, 2}
    assert network.shortest_path_meters(1, 2) == pytest.approx(300, abs=1)


def test_a_file_with_no_walkable_way_and_no_bounds_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "x.osm"
    path.write_text(_osm(_way(("highway", "motorway"))), encoding="utf-8")
    with pytest.raises(PedestrianNetworkError, match="coverage is unknown"):
        load_osm_xml(path)


def test_pbf_is_named_rather_than_tried(tmp_path: Path) -> None:
    path = tmp_path / "area.osm.pbf"
    path.write_bytes(b"\x00\x00\x00\rnot xml")
    with pytest.raises(PedestrianNetworkError, match="osmium cat"):
        load_network(path)


# --- The pre-built graph --------------------------------------------------


def test_a_prebuilt_graph_reads_and_its_lengths_come_from_its_geometry(
    tmp_path: Path,
) -> None:
    path = tmp_path / "graph.json"
    path.write_text(
        json.dumps(
            {
                "nodes": {"1": [LAT0, LON0], "2": list(point(0, 300))},
                # A caller cannot assert a shorter walk than the geometry
                # supports, because no length is read from the file.
                "edges": [[1, 2]],
                "length_m": 5,
            }
        ),
        encoding="utf-8",
    )
    network = load_graph_json(path)
    assert network.shortest_path_meters(1, 2) == pytest.approx(300, abs=1)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("[]", "expected a JSON object"),
        ('{"nodes": {}}', "expected 'nodes'"),
        ('{"nodes": {"1": [1]}, "edges": []}', "is not \\[lat, lon\\]"),
        ('{"nodes": {"1": [1, 2]}, "edges": [[1]]}', "is not \\[a, b\\]"),
        ('{"nodes": {"1": [1, 2]}, "edges": [[1, 9]]}', "does not define"),
    ],
)
def test_a_malformed_graph_is_refused_rather_than_partly_read(
    tmp_path: Path, payload: str, message: str
) -> None:
    path = tmp_path / "graph.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(PedestrianNetworkError, match=message):
        load_graph_json(path)


def test_an_unreadable_graph_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "graph.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(PedestrianNetworkError, match="not readable as JSON"):
        load_graph_json(path)


# --- Determinism ----------------------------------------------------------


def test_a_snap_tie_breaks_on_the_lower_node_id(tmp_path: Path) -> None:
    """Two nodes exactly equidistant is where a nearest-node search stops
    being deterministic unless the tie is decided explicitly."""
    north, south = point(0, 300), point(0, -300)
    path = tmp_path / "graph.json"
    path.write_text(
        json.dumps(
            {
                # 7 is written before 3, so file order and id order disagree.
                "nodes": {"7": list(north), "3": list(south), "8": list(north)},
                "edges": [[7, 3], [3, 8]],
            }
        ),
        encoding="utf-8",
    )
    network = load_graph_json(path)
    snapped = network.snap(*north)
    assert snapped is not None and snapped[0] == 7
    assert network.snap(LAT0, LON0) == (3, pytest.approx(300, abs=1))


def test_the_same_extract_measures_the_same_metres_in_separate_processes() -> None:
    """Across processes, not twice in one: a determinism claim tested inside
    one interpreter proves only that the code is not random."""
    script = (
        "import sys; sys.path.insert(0, 'src');"
        "from pathlib import Path;"
        "from permit_pathways.pedestrian import load_network;"
        "n = load_network(Path('tests/fixtures/pedestrian/barrier.osm'));"
        f"r = n.walk_many({SITE[0]!r}, {SITE[1]!r}, "
        f"[{STOP!r}, {ORPHAN!r}, {OUTSIDE!r}]);"
        "print([(x.walking_status, None if x.walking_m is None else round(x.walking_m, 6)) for x in r])"
    )
    outputs = set()
    for seed in ("0", "1", "12345"):
        completed = subprocess.run(  # nosec B603
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"},
        )
        outputs.add(completed.stdout.strip())
    assert len(outputs) == 1, outputs
    assert "1399.98" in outputs.pop()


# --- Geometry -------------------------------------------------------------


def test_bounds_contain_their_own_corners() -> None:
    bounds = NetworkBounds(1.0, 2.0, 3.0, 4.0)
    assert bounds.contains(1.0, 2.0) and bounds.contains(3.0, 4.0)
    assert not bounds.contains(0.999, 3.0) and not bounds.contains(2.0, 4.001)


def test_haversine_is_symmetric_and_zero_on_a_point() -> None:
    assert haversine_meters(LAT0, LON0, LAT0, LON0) == 0.0
    assert haversine_meters(*SITE, *STOP) == pytest.approx(
        haversine_meters(*STOP, *SITE)
    )
