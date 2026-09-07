"""Walking distance over an offline pedestrian network.

Both transit standards this project screens are written in *walking*
distance — Gov. Code § 66322(a)(1), "one-half mile walking distance of public
transit" — and `transit.py` measures a straight line. Walking distance is
never shorter than straight-line, so the straight line can eliminate a stop
and cannot establish one. The gap is not academic and it is not symmetric: a
stop across a freeway or a creek is a quarter mile as the crow flies and a
mile and a half on foot, so the straight-line answer is *systematically
optimistic* about the one direction that matters.

This module measures the other number, offline and deterministically, from a
pedestrian network the operator supplies as a file. There is no router, no
service, and nothing is fetched.

What it will not do
-------------------

It will never return a straight-line number wearing a walking label. Four
statuses come back per stop, and only the first carries a distance:

``measured``          a path was found; ``walking_m`` is its length.
``not_in_extract``    the site or the stop lies outside the extract's bounds.
                      The extract cannot say anything about a point it does
                      not contain, including that the walk is long.
``snap_too_far``      the nearest walkable node is farther than the snap
                      limit. Attaching the point anyway would invent a
                      footpath that is not in the data.
``disconnected``      both points snapped, and no walkable route joins them
                      *in this extract*. That is a fact about the extract's
                      coverage, not a proof that no route exists, which is
                      why it is a withheld state rather than "unreachable".

A clipped extract makes the third and fourth states common near its edge, so
neither is treated as evidence against a stop.

Graph rules
-----------

Recorded in ADR 0007 and enforced here, not inferred at read time:

* a way is walkable when its ``highway`` tag is in :data:`WALKABLE_HIGHWAY`;
* ``highway`` values in :data:`EXCLUDED_HIGHWAY` are never walkable, however
  they are otherwise tagged — a freeway is the barrier, not a shortcut;
* ``foot=no`` or ``access=no``/``private`` removes an otherwise walkable way;
* ``foot=yes``/``designated`` adds a way whose ``highway`` value is not in
  the walkable set, but never one in the excluded set;
* every edge is undirected. ``oneway`` restricts vehicles; this graph is for
  people on foot, and a one-way street is walkable in both directions.

Determinism
-----------

Node ids, way order and edge order are read in file order and the search is
a plain Dijkstra over integer-keyed adjacency, so the same extract yields the
same metre count on every run and on every machine. The extract's SHA-256 and
its bounds travel with the result, so a number can always be traced to the
file it came from.

No third-party dependency, and therefore no optional extra: OSM XML is read
with the standard library's ``iterparse``, one element at a time, so a large
clipped extract does not have to fit in memory as a tree. `.osm.gz` and
`.osm.bz2` are read directly. **PBF is deliberately not supported.** Reading
it needs a compiled library, and taking that dependency for an optional
offline mode would cost every deployment that never uses it; ``osmium cat -o
area.osm area.osm.pbf`` converts in one command. A pre-built graph in JSON is
the other accepted input, for an operator who would rather build the graph
once.
"""

from __future__ import annotations

import bz2
import gzip
import hashlib
import heapq
import json
import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import IO, Any, cast
from xml.etree.ElementTree import iterparse  # nosec B405

EARTH_RADIUS_M = 6_371_008.8
#: Default limit on how far a point may be from the nearest walkable node
#: before the measurement is withheld. 100 m is roughly a city block: far
#: enough to attach a stop set back from the kerb, near enough that attaching
#: it does not silently invent a path across a parcel.
DEFAULT_SNAP_MAX_M = 100.0

STATUS_MEASURED = "measured"
STATUS_NOT_IN_EXTRACT = "not_in_extract"
STATUS_SNAP_TOO_FAR = "snap_too_far"
STATUS_DISCONNECTED = "disconnected"

#: Ways a person on foot may use. See ADR 0007 for why each is here.
WALKABLE_HIGHWAY = frozenset(
    {
        "footway",
        "path",
        "pedestrian",
        "steps",
        "living_street",
        "residential",
        "unclassified",
        "service",
        "track",
        "tertiary",
        "tertiary_link",
        "secondary",
        "secondary_link",
        "primary",
        "primary_link",
        "corridor",
        "crossing",
    }
)

#: Ways a person on foot may not use, whatever else the way says. A
#: `foot=yes` tag on a motorway is a tagging error or a mapped shoulder, and
#: reading it as a footpath is exactly the optimistic answer this module
#: exists to stop.
EXCLUDED_HIGHWAY = frozenset(
    {
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "construction",
        "proposed",
        "raceway",
        "bus_guideway",
    }
)

_FOOT_ALLOWS = frozenset({"yes", "designated", "permissive", "destination"})
_FOOT_DENIES = frozenset({"no", "private"})


class PedestrianNetworkError(ValueError):
    """The supplied network file could not be read as a pedestrian network."""


@dataclass(frozen=True)
class NetworkBounds:
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    def contains(self, lat: float, lon: float) -> bool:
        return (
            self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "min_lat": self.min_lat,
            "min_lon": self.min_lon,
            "max_lat": self.max_lat,
            "max_lon": self.max_lon,
        }


@dataclass(frozen=True)
class WalkResult:
    """One measurement, or one stated reason there is none."""

    straight_line_m: float
    walking_m: float | None
    walking_status: str
    #: How far the site and the destination sat from the network, when both
    #: snapped. ``None`` where a snap did not happen.
    site_snap_m: float | None = None
    destination_snap_m: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "straight_line_m": round(self.straight_line_m, 1),
            "walking_m": None if self.walking_m is None else round(self.walking_m, 1),
            "walking_status": self.walking_status,
            "site_snap_m": (
                None if self.site_snap_m is None else round(self.site_snap_m, 1)
            ),
            "destination_snap_m": (
                None
                if self.destination_snap_m is None
                else round(self.destination_snap_m, 1)
            ),
        }


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class PedestrianNetwork:
    """An undirected walkable graph, with the provenance of the file it came from."""

    #: Node id -> (lat, lon), in file order.
    nodes: dict[int, tuple[float, float]]
    #: Node id -> ((neighbour, metres), ...), in file order.
    edges: dict[int, tuple[tuple[int, float], ...]]
    bounds: NetworkBounds
    source_path: str
    source_sha256: str
    way_count: int

    def provenance(self) -> dict[str, Any]:
        return {
            "source": self.source_path,
            "sha256": f"sha256:{self.source_sha256}",
            "bounds": self.bounds.to_dict(),
            "nodes": len(self.nodes),
            "ways": self.way_count,
        }

    def describe(self) -> str:
        return (
            f"Pedestrian network: {self.source_path} "
            f"(sha256:{self.source_sha256[:12]}…, {len(self.nodes)} walkable "
            f"nodes from {self.way_count} way(s), bounds "
            f"{self.bounds.min_lat:.5f},{self.bounds.min_lon:.5f} to "
            f"{self.bounds.max_lat:.5f},{self.bounds.max_lon:.5f})"
        )

    def snap(self, lat: float, lon: float) -> tuple[int, float] | None:
        """Nearest node and its distance, or ``None`` for an empty graph.

        Ties break on the lower node id so the same extract always snaps the
        same way; a nearest-node tie is otherwise resolved by dict order,
        which is file order, which is not something a reader can check.
        """
        candidates = (
            (haversine_meters(lat, lon, node_lat, node_lon), node_id)
            for node_id, (node_lat, node_lon) in self.nodes.items()
        )
        best = min(candidates, default=None)
        return None if best is None else (best[1], best[0])

    def shortest_path_meters(self, start: int, goal: int) -> float | None:
        """Plain Dijkstra. ``None`` when no walkable route joins the two."""
        if start == goal:
            return 0.0
        best: dict[int, float] = {start: 0.0}
        queue: list[tuple[float, int]] = [(0.0, start)]
        seen: set[int] = set()
        while queue:
            cost, node = heapq.heappop(queue)
            if node in seen:
                continue
            seen.add(node)
            if node == goal:
                return cost
            for neighbour, length in self.edges.get(node, ()):
                if neighbour in seen:
                    continue
                candidate = cost + length
                if candidate < best.get(neighbour, math.inf):
                    best[neighbour] = candidate
                    heapq.heappush(queue, (candidate, neighbour))
        return None

    def distances_from(self, start: int) -> dict[int, float]:
        """Every node's walking distance from ``start``. One Dijkstra.

        Screening a site asks the same question of many stops, so the search
        runs once from the site rather than once per stop; a node absent from
        the result is one no walkable route in this extract reaches.
        """
        best: dict[int, float] = {start: 0.0}
        queue: list[tuple[float, int]] = [(0.0, start)]
        seen: set[int] = set()
        while queue:
            cost, node = heapq.heappop(queue)
            if node in seen:
                continue
            seen.add(node)
            for neighbour, length in self.edges.get(node, ()):
                if neighbour in seen:
                    continue
                candidate = cost + length
                if candidate < best.get(neighbour, math.inf):
                    best[neighbour] = candidate
                    heapq.heappush(queue, (candidate, neighbour))
        return {node: cost for node, cost in best.items() if node in seen}

    def walk(
        self,
        site_lat: float,
        site_lon: float,
        destination_lat: float,
        destination_lon: float,
        *,
        snap_max_m: float = DEFAULT_SNAP_MAX_M,
    ) -> WalkResult:
        """Measure one walk, or state why it was not measured."""
        return self.walk_many(
            site_lat,
            site_lon,
            [(destination_lat, destination_lon)],
            snap_max_m=snap_max_m,
        )[0]

    def walk_many(
        self,
        site_lat: float,
        site_lon: float,
        destinations: Sequence[tuple[float, float]],
        *,
        snap_max_m: float = DEFAULT_SNAP_MAX_M,
    ) -> list[WalkResult]:
        """Measure several walks from one site, in the order given."""
        straights = [
            haversine_meters(site_lat, site_lon, lat, lon) for lat, lon in destinations
        ]
        site_in_bounds = self.bounds.contains(site_lat, site_lon)
        site = self.snap(site_lat, site_lon) if site_in_bounds else None
        # A file with bounds but no walkable node snaps nothing; inside the
        # bounds with nothing to attach to is a snap failure, not a missing
        # extract.
        site_snapped = site is not None and site[1] <= snap_max_m
        reachable = (
            self.distances_from(site[0]) if site is not None and site_snapped else {}
        )

        results: list[WalkResult] = []
        for straight, (lat, lon) in zip(straights, destinations, strict=True):
            if not site_in_bounds or not self.bounds.contains(lat, lon):
                results.append(WalkResult(straight, None, STATUS_NOT_IN_EXTRACT))
                continue
            destination = self.snap(lat, lon)
            if site is None or destination is None:
                results.append(WalkResult(straight, None, STATUS_SNAP_TOO_FAR))
                continue
            if not site_snapped or destination[1] > snap_max_m:
                results.append(
                    WalkResult(
                        straight, None, STATUS_SNAP_TOO_FAR, site[1], destination[1]
                    )
                )
                continue
            metres = reachable.get(destination[0])
            if metres is None:
                results.append(
                    WalkResult(
                        straight, None, STATUS_DISCONNECTED, site[1], destination[1]
                    )
                )
                continue
            # The two snap legs are part of the walk. Leaving them out would
            # report the distance between two nodes as the distance between
            # two places, which is the same category of error as the straight
            # line.
            results.append(
                WalkResult(
                    straight,
                    site[1] + metres + destination[1],
                    STATUS_MEASURED,
                    site[1],
                    destination[1],
                )
            )
        return results


def _is_walkable(tags: dict[str, str]) -> bool:
    highway = tags.get("highway", "")
    if highway in EXCLUDED_HIGHWAY:
        return False
    foot = tags.get("foot", "")
    if foot in _FOOT_DENIES:
        return False
    if tags.get("access", "") in _FOOT_DENIES and foot not in _FOOT_ALLOWS:
        return False
    if highway in WALKABLE_HIGHWAY:
        return True
    return foot in _FOOT_ALLOWS


def _open_maybe_compressed(path: Path) -> IO[bytes]:
    name = path.name.lower()
    if name.endswith(".gz"):
        return cast("IO[bytes]", gzip.open(path, "rb"))
    if name.endswith(".bz2"):
        return cast("IO[bytes]", bz2.open(path, "rb"))
    return path.open("rb")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _osm_elements(handle: IO[bytes]) -> Iterator[tuple[str, Any]]:
    # `iterparse` on a local operator-supplied file. No network entities are
    # resolved, and the parser is never handed a URL.
    yield from iterparse(handle, events=("end",))  # noqa: S314  # nosec B314


def load_osm_xml(path: Path) -> PedestrianNetwork:
    """Build a walkable graph from an OSM XML extract.

    Two passes over one file: nodes are collected first because a way names
    node ids that may appear before or after it, and a single pass would have
    to keep every way's node list alive anyway.
    """
    coordinates, declared = _read_osm_nodes(path)
    nodes, adjacency, way_count = _read_osm_ways(path, coordinates)
    return PedestrianNetwork(
        nodes=nodes,
        edges={node: tuple(pairs) for node, pairs in adjacency.items()},
        bounds=declared if declared is not None else _bounds_of(nodes, path),
        source_path=path.name,
        source_sha256=_sha256(path),
        way_count=way_count,
    )


def _read_osm_nodes(
    path: Path,
) -> tuple[dict[int, tuple[float, float]], NetworkBounds | None]:
    coordinates: dict[int, tuple[float, float]] = {}
    declared: NetworkBounds | None = None
    with _open_maybe_compressed(path) as handle:
        for _, element in _osm_elements(handle):
            if element.tag == "bounds":
                try:
                    declared = NetworkBounds(
                        float(element.attrib["minlat"]),
                        float(element.attrib["minlon"]),
                        float(element.attrib["maxlat"]),
                        float(element.attrib["maxlon"]),
                    )
                except (KeyError, ValueError) as exc:
                    raise PedestrianNetworkError(
                        f"{path}: <bounds> is malformed"
                    ) from exc
                element.clear()
            elif element.tag == "node":
                try:
                    coordinates[int(element.attrib["id"])] = (
                        float(element.attrib["lat"]),
                        float(element.attrib["lon"]),
                    )
                except (KeyError, ValueError) as exc:
                    raise PedestrianNetworkError(
                        f"{path}: a <node> lacks a usable id/lat/lon"
                    ) from exc
                element.clear()
    return coordinates, declared


def _read_osm_ways(
    path: Path, coordinates: dict[int, tuple[float, float]]
) -> tuple[dict[int, tuple[float, float]], dict[int, list[tuple[int, float]]], int]:
    nodes: dict[int, tuple[float, float]] = {}
    adjacency: dict[int, list[tuple[int, float]]] = {}
    way_count = 0
    with _open_maybe_compressed(path) as handle:
        for _, element in _osm_elements(handle):
            if element.tag != "way":
                if element.tag == "node":
                    element.clear()
                continue
            tags = {
                child.attrib.get("k", ""): child.attrib.get("v", "")
                for child in element.findall("tag")
            }
            if _is_walkable(tags):
                refs = _way_refs(path, element, coordinates)
                if len(refs) >= 2:
                    way_count += 1
                    for first, second in pairwise(refs):
                        _add_edge(nodes, adjacency, coordinates, first, second)
            element.clear()
    return nodes, adjacency, way_count


def _way_refs(
    path: Path, element: Any, coordinates: dict[int, tuple[float, float]]
) -> list[int]:
    refs: list[int] = []
    for child in element.findall("nd"):
        try:
            ref = int(child.attrib["ref"])
        except (KeyError, ValueError) as exc:
            raise PedestrianNetworkError(f"{path}: a <nd> lacks a usable ref") from exc
        # A way in a clipped extract can reference a node outside the clip.
        # Dropping the reference keeps the rest of the way usable; joining
        # across the gap would invent an edge.
        if ref in coordinates:
            refs.append(ref)
    return refs


def _add_edge(
    nodes: dict[int, tuple[float, float]],
    adjacency: dict[int, list[tuple[int, float]]],
    coordinates: dict[int, tuple[float, float]],
    first: int,
    second: int,
) -> None:
    if first == second:
        return
    first_point = coordinates[first]
    second_point = coordinates[second]
    nodes.setdefault(first, first_point)
    nodes.setdefault(second, second_point)
    length = haversine_meters(*first_point, *second_point)
    adjacency.setdefault(first, []).append((second, length))
    adjacency.setdefault(second, []).append((first, length))


def _bounds_of(nodes: dict[int, tuple[float, float]], path: Path) -> NetworkBounds:
    if not nodes:
        raise PedestrianNetworkError(
            f"{path}: no walkable way was found, and the file declares no <bounds>, "
            "so the extract's coverage is unknown"
        )
    lats = [lat for lat, _ in nodes.values()]
    lons = [lon for _, lon in nodes.values()]
    return NetworkBounds(min(lats), min(lons), max(lats), max(lons))


def load_graph_json(path: Path) -> PedestrianNetwork:
    """Read a pre-built graph, for an operator who builds it once.

    ``{"nodes": {"1": [lat, lon], ...}, "edges": [[a, b], ...]}``; edge
    lengths are computed from the coordinates rather than trusted, so a graph
    file cannot assert a shorter walk than its own geometry supports.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PedestrianNetworkError(f"{path}: not readable as JSON") from exc
    if not isinstance(payload, dict):
        raise PedestrianNetworkError(f"{path}: expected a JSON object")
    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges")
    if not isinstance(raw_nodes, dict) or not isinstance(raw_edges, list):
        raise PedestrianNetworkError(
            f"{path}: expected 'nodes' (object) and 'edges' (array)"
        )
    coordinates: dict[int, tuple[float, float]] = {}
    for key, value in raw_nodes.items():
        try:
            point = (float(value[0]), float(value[1]))
            coordinates[int(key)] = point
        except (TypeError, ValueError, IndexError, KeyError) as exc:
            raise PedestrianNetworkError(
                f"{path}: node {key!r} is not [lat, lon]"
            ) from exc
    nodes: dict[int, tuple[float, float]] = {}
    adjacency: dict[int, list[tuple[int, float]]] = {}
    for edge in raw_edges:
        try:
            first, second = int(edge[0]), int(edge[1])
        except (TypeError, ValueError, IndexError) as exc:
            raise PedestrianNetworkError(
                f"{path}: edge {edge!r} is not [a, b]"
            ) from exc
        if first not in coordinates or second not in coordinates:
            raise PedestrianNetworkError(
                f"{path}: edge {edge!r} names a node the file does not define"
            )
        _add_edge(nodes, adjacency, coordinates, first, second)
    return PedestrianNetwork(
        nodes=nodes,
        edges={node: tuple(pairs) for node, pairs in adjacency.items()},
        bounds=_bounds_of(nodes, path),
        source_path=path.name,
        source_sha256=_sha256(path),
        way_count=len(raw_edges),
    )


def load_network(path: Path) -> PedestrianNetwork:
    """Read either accepted input, chosen by suffix rather than by sniffing.

    A `.pbf` is named rather than tried, so an operator who has one is told
    what to do instead of watching the XML parser fail on binary.
    """
    name = path.name.lower()
    if name.endswith(".pbf"):
        raise PedestrianNetworkError(
            f"{path}: PBF is not supported. Reading it needs a compiled library "
            "this project does not depend on; convert it first with "
            f"`osmium cat -o area.osm {path.name}` and pass the .osm file."
        )
    if name.endswith(".json"):
        return load_graph_json(path)
    return load_osm_xml(path)
