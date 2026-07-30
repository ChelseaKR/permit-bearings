"""Transit-proximity determinations from GTFS data.

Two State ADU Law standards turn on transit proximity, and both are
computable from a jurisdiction's own GTFS feed instead of applicant
self-attestation:

- Parking exemption — Gov. Code § 66322(a)(1): no parking may be required
  for an ADU "located within one-half mile walking distance of public
  transit"; § 66313(m) defines public transit broadly (any bus stop or
  train station with fixed-route, set-fare public service).
- 18-foot height allowance — Gov. Code § 66321(b)(4)(B): applies within a
  half-mile walking distance of a "major transit stop" (Pub. Res. Code
  § 21064.3: rail/BRT station, ferry with bus or rail service, or the
  intersection of two or more major bus routes with ≤20-minute peak
  service) or a "high-quality transit corridor" (Pub. Res. Code
  § 21155(b): fixed-route bus service with ≤15-minute peak intervals).

Honesty model. Distances here are straight-line (haversine). Walking
distance is never shorter than straight-line, so a supplied stop farther than
the threshold can be eliminated. That does not prove every relevant operator,
stop, planned/current facility, or service record is present. A stop within
the threshold is a CANDIDATE "yes" pending a walking-network check
(production deployments should confirm with a router). Headways are measured
from the busiest weekday service in the feed within the peak windows 6-9 AM
and 4-7 PM, using the maximum gap between consecutive trips - a screening
approximation of the statutes' "service interval" language, and only as
current and complete as the supplied feed.
"""

from __future__ import annotations

import csv
import io
import itertools
import json
import math
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

HALF_MILE = 0.5
HQTC_MAX_GAP_MIN = 15  # PRC § 21155(b)
MAJOR_STOP_MAX_GAP_MIN = 20  # PRC § 21064.3(c)
PEAKS = ((6 * 60, 9 * 60), (16 * 60, 19 * 60))
STOP_CLUSTER_MILES = 0.1  # stops this close count as one "intersection"
RAIL_ROUTE_TYPES = {"0", "1", "2"}  # tram, metro, rail
FERRY_ROUTE_TYPES = {"4"}
BUS_ROUTE_TYPES = {"3", "11"}  # bus and trolleybus


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class StopService:
    stop_id: str
    name: str
    lat: float
    lon: float
    route_max_gaps: dict[str, float] = field(default_factory=dict)
    bus_routes: set[str] = field(default_factory=set)
    rail: bool = False
    ferry: bool = False

    def hqtc_routes(self) -> list[str]:
        return [r for r, g in self.route_max_gaps.items() if g <= HQTC_MAX_GAP_MIN]

    def major_candidate_routes(self) -> list[str]:
        return [
            r for r, g in self.route_max_gaps.items() if g <= MAJOR_STOP_MAX_GAP_MIN
        ]


def _read(z: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    with z.open(name) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, "utf-8-sig")))


def _minutes(hms: str) -> int | None:
    parts = hms.strip().split(":")
    if len(parts) < 2:
        return None
    return int(parts[0]) * 60 + int(parts[1])


def _worst_peak_gap(times: list[int]) -> float | None:
    """Worst max-gap across the peak windows; None if any peak window has
    fewer than 2 trips (can't establish an interval at all).

    Window-edge gaps count. Otherwise service at 6:15 and every 15 minutes
    through 8:45 would be mislabeled as continuous 15-minute service across
    the full 6-9 AM window.
    """
    worst = 0.0
    for start, end in PEAKS:
        window = sorted(t for t in times if start <= t <= end)
        if len(window) < 2:
            return None
        gaps = [
            window[0] - start,
            *(b - a for a, b in itertools.pairwise(window)),
            end - window[-1],
        ]
        worst = max(worst, max(gaps))
    return worst


def _route_mode(route_type: str) -> str:
    if route_type in RAIL_ROUTE_TYPES:
        return "rail"
    if route_type in FERRY_ROUTE_TYPES:
        return "ferry"
    if route_type in BUS_ROUTE_TYPES:
        return "bus"
    # GTFS extended route types 700-799 are bus services.
    try:
        numeric = int(route_type)
    except (TypeError, ValueError):
        return "other"
    return "bus" if 700 <= numeric <= 799 else "other"


def load_feed(gtfs_zip: Path) -> list[StopService]:
    z = zipfile.ZipFile(gtfs_zip)
    stops = {
        s["stop_id"]: StopService(
            stop_id=s["stop_id"],
            name=s["stop_name"],
            lat=float(s["stop_lat"]),
            lon=float(s["stop_lon"]),
        )
        for s in _read(z, "stops.txt")
        if s.get("stop_lat")
    }
    route_types = {
        r["route_id"]: r.get("route_type", "3") for r in _read(z, "routes.txt")
    }

    weekday_services = {
        c["service_id"] for c in _read(z, "calendar.txt") if c.get("monday") == "1"
    }
    trips = {
        t["trip_id"]: t
        for t in _read(z, "trips.txt")
        if t["service_id"] in weekday_services
    }
    # Busiest weekday service = the service_id with the most trips.
    by_service: dict[str, int] = defaultdict(int)
    for t in trips.values():
        by_service[t["service_id"]] += 1
    if by_service:
        busiest = max(by_service, key=lambda s: by_service[s])
        trips = {tid: t for tid, t in trips.items() if t["service_id"] == busiest}

    # arrivals[(stop_id, route_id, direction)] = [minutes, ...]
    arrivals: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for st in _read(z, "stop_times.txt"):
        trip = trips.get(st["trip_id"])
        if not trip:
            continue
        minutes = _minutes(st.get("arrival_time") or st.get("departure_time") or "")
        if minutes is None:
            continue
        key = (st["stop_id"], trip["route_id"], trip.get("direction_id", ""))
        arrivals[key].append(minutes)

    for (stop_id, route_id, _direction), times in arrivals.items():
        stop = stops.get(stop_id)
        if not stop:
            continue
        mode = _route_mode(route_types.get(route_id, "3"))
        if mode == "rail":
            stop.rail = True
            continue
        if mode == "ferry":
            stop.ferry = True
            continue
        if mode != "bus":
            continue
        stop.bus_routes.add(route_id)
        gap = _worst_peak_gap(times)
        if gap is None:
            continue
        best = stop.route_max_gaps.get(route_id)
        if best is None or gap < best:
            stop.route_max_gaps[route_id] = gap
    return list(stops.values())


def _is_major_stop(stop: StopService, all_stops: list[StopService]) -> bool:
    """PRC § 21064.3 transit-mode and service conditions.

    Rail is independently qualifying. A ferry terminal qualifies only when
    the same clustered stop is served by bus or rail transit. Bus stops need
    two major routes with qualifying peak service.
    """
    if stop.rail:
        return True
    cluster = [stop]
    cluster.extend(
        other
        for other in all_stops
        if other.stop_id != stop.stop_id
        and haversine_miles(
            stop.lat,
            stop.lon,
            other.lat,
            other.lon,
        )
        <= STOP_CLUSTER_MILES
    )
    if stop.ferry and any(member.rail or member.bus_routes for member in cluster):
        return True
    routes = set(stop.major_candidate_routes())
    for other in cluster[1:]:
        routes |= set(other.major_candidate_routes())
    return len(routes) >= 2


@dataclass(frozen=True)
class HQStop:
    """A stop from the Caltrans/Cal-ITP statewide High Quality Transit
    Stops dataset — the state's own PRC § 21064.3 / § 21155 analysis,
    covering every agency (including rail and ferry the local feed may
    lack). Used alongside, not instead of, live-feed headway analysis:
    the two sources cross-check each other."""

    lat: float
    lon: float
    hqta_type: str  # major_stop_rail | major_stop_brt | major_stop_ferry
    # | major_stop_bus | hq_corridor_bus
    details: str
    agency: str

    @property
    def is_major(self) -> bool:
        return self.hqta_type.startswith("major_stop")


def load_hq_stops(path: Path) -> list[HQStop]:
    data: dict[str, list[list[object]]] = json.loads(Path(path).read_text())
    seen: set[tuple[float, float, str]] = set()
    out: list[HQStop] = []
    for lat, lon, hqta_type, details, agency, _peak in data["stops"]:
        if not (
            isinstance(lat, (int, float))
            and isinstance(lon, (int, float))
            and isinstance(hqta_type, str)
        ):
            raise ValueError("invalid high-quality transit stop record")
        key = (lat, lon, hqta_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            HQStop(
                lat=float(lat),
                lon=float(lon),
                hqta_type=hqta_type,
                details=details if isinstance(details, str) else "",
                agency=agency if isinstance(agency, str) else "",
            )
        )
    return out


@dataclass(frozen=True)
class Determination:
    nearest_stop: StopService | None
    nearest_miles: float | None
    parking_exemption: str  # "candidate" | "no"
    height_18ft: str  # "candidate" | "no"
    qualifying_stops: list[tuple[StopService, float, str]]

    def summary(self) -> str:
        lines = []
        if self.nearest_stop:
            lines.append(
                f"Nearest transit stop: {self.nearest_stop.name} "
                f"({self.nearest_miles:.2f} mi straight-line)"
            )
        if self.parking_exemption == "candidate":
            lines.append(
                "Parking exemption (Gov. Code § 66322(a)(1)): CANDIDATE — public "
                "transit within a half mile straight-line; confirm walking distance."
            )
        else:
            lines.append(
                "Parking exemption (Gov. Code § 66322(a)(1)): NO CANDIDATE FOUND "
                "IN SUPPLIED DATA — confirm operator/feed coverage before relying "
                "on this result."
            )
        if self.height_18ft == "candidate":
            stop, miles, reason = self.qualifying_stops[0]
            lines.append(
                f"18-ft height allowance (Gov. Code § 66321(b)(4)(B)): CANDIDATE — "
                f"{stop.name} ({miles:.2f} mi) is a {reason}; confirm walking distance."
            )
        else:
            lines.append(
                "18-ft height allowance (Gov. Code § 66321(b)(4)(B)): NO CANDIDATE "
                "FOUND IN SUPPLIED DATA — no encoded qualifying stop was found "
                "within a half mile; confirm source coverage."
            )
        lines.append(
            "Screening result from GTFS peak headways (busiest weekday service "
            "in the feed); straight-line distance can eliminate a supplied stop "
            "but cannot prove dataset completeness. Not a legal determination."
        )
        return "\n".join(lines)


def determine(
    lat: float,
    lon: float,
    stops: list[StopService],
    hq_stops: list[HQStop] | None = None,
) -> Determination:
    if not stops and not hq_stops:
        return Determination(None, None, "no", "no", [])
    with_dist = sorted(
        ((s, haversine_miles(lat, lon, s.lat, s.lon)) for s in stops),
        key=lambda x: x[1],
    )
    nearest, nearest_miles = with_dist[0] if with_dist else (None, None)

    qualifying: list[tuple[StopService, float, str]] = []
    for stop, miles in with_dist:
        if miles > HALF_MILE:
            break
        if _is_major_stop(stop, stops):
            qualifying.append(
                (stop, miles, "major transit stop (PRC § 21064.3, from feed headways)")
            )
        elif stop.hqtc_routes():
            qualifying.append(
                (
                    stop,
                    miles,
                    "high-quality transit corridor stop (PRC § 21155(b), from feed headways)",
                )
            )

    hq_within = []
    for hq in hq_stops or []:
        miles = haversine_miles(lat, lon, hq.lat, hq.lon)
        if miles > HALF_MILE:
            continue
        hq_within.append((hq, miles))
        label = (
            "major transit stop"
            if hq.is_major
            else "high-quality transit corridor stop"
        )
        stop_view = StopService(
            stop_id=f"hq:{hq.hqta_type}",
            name=f"{hq.agency} ({hq.hqta_type})",
            lat=hq.lat,
            lon=hq.lon,
        )
        qualifying.append(
            (
                stop_view,
                miles,
                f"{label} (Caltrans HQ Transit Stops dataset: {hq.hqta_type})",
            )
        )

    qualifying.sort(key=lambda x: x[1])
    parking = (
        "candidate"
        if ((nearest_miles is not None and nearest_miles <= HALF_MILE) or hq_within)
        else "no"
    )
    return Determination(
        nearest_stop=nearest,
        nearest_miles=nearest_miles,
        parking_exemption=parking,
        height_18ft="candidate" if qualifying else "no",
        qualifying_stops=qualifying,
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="permit_pathways.transit",
        description="Transit-proximity screening for ADU parking/height standards.",
    )
    parser.add_argument("--gtfs", type=Path, required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    default_hq = (
        Path(__file__).resolve().parents[2]
        / "corpus"
        / "transit"
        / "ca-hq-transit-stops.json"
    )
    parser.add_argument(
        "--hq-stops", type=Path, default=default_hq if default_hq.exists() else None
    )
    args = parser.parse_args()

    stops = load_feed(args.gtfs)
    hq = load_hq_stops(args.hq_stops) if args.hq_stops else []
    print(
        f"Loaded {len(stops)} feed stops; "
        f"{sum(1 for s in stops if s.hqtc_routes())} with ≤15-min peak routes, "
        f"{sum(1 for s in stops if len(s.major_candidate_routes()) >= 1)} with "
        f"≤20-min peak routes; {len(hq)} Caltrans HQ dataset stops.\n"
    )
    print(determine(args.lat, args.lon, stops, hq_stops=hq).summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
