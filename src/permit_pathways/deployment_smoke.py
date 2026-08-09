"""Read-only smoke checks for a deployed static Permit Bearings build.

The check is intentionally narrow: it proves that the public routes and the
generated jurisdiction index are reachable and shaped like this repository's
artifact.  It does not prove source currency, legal accuracy, accessibility,
or a successful applicant workflow.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

DEFAULT_BASE_URL = "https://chelseakr.github.io/permit-pathways/"
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_EXPECTED_JURISDICTIONS = 541
DEFAULT_EXPECTED_STATEWIDE_RULES = 17

Fetcher = Callable[[str, float], tuple[int, bytes]]


@dataclass(frozen=True)
class RouteContract:
    path: str
    marker: bytes


@dataclass(frozen=True)
class SmokeResult:
    url: str
    status: int
    detail: str


HTML_ROUTES = (
    RouteContract("", b'id="home-boundary-heading"'),
    RouteContract("check.html", b'id="jurisdictionProfile"'),
    RouteContract("prepare.html", b'id="readinessOutput"'),
    RouteContract("review.html", b'id="scanResults"'),
    RouteContract("evidence.html", b'id="sourceSnapshotSummary"'),
)
INDEX_PATH = "data/jurisdictions/generated/coverage-index.json"


class SmokeFailure(ValueError):
    """The deployed artifact did not satisfy its bounded route contract."""


def _validated_base_url(value: str, *, allow_http: bool) -> str:
    parsed = urlsplit(value)
    allowed_schemes = {"https", "http"} if allow_http else {"https"}
    if (
        parsed.scheme not in allowed_schemes
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        expectation = "HTTP(S)" if allow_http else "HTTPS"
        raise SmokeFailure(
            f"base URL must be an {expectation} URL without credentials, query, or fragment"
        )
    return value.rstrip("/") + "/"


def _fetch(url: str, timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(  # noqa: S310
        url,
        headers={"User-Agent": "permit-bearings-deployment-smoke/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310  # noqa: S310
            return response.status, response.read()
    except (OSError, urllib.error.HTTPError, urllib.error.URLError) as error:
        raise SmokeFailure(f"{url}: request failed: {error}") from error


def _fetch_success(fetcher: Fetcher, url: str, timeout: float) -> bytes:
    status, body = fetcher(url, timeout)
    if status != 200:
        raise SmokeFailure(f"{url}: expected HTTP 200, received {status}")
    if not body:
        raise SmokeFailure(f"{url}: response body is empty")
    return body


def _validated_index(
    body: bytes,
    *,
    expected_jurisdictions: int,
    expected_statewide_rules: int,
) -> tuple[int, int, int]:
    try:
        payload: Any = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(f"{INDEX_PATH}: expected valid UTF-8 JSON") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise SmokeFailure(f"{INDEX_PATH}: expected schema_version 1")
    profiles = payload.get("profiles")
    statewide = payload.get("statewide_rule_ids")
    hcd = payload.get("hcd_dataset")
    if not isinstance(profiles, dict):
        raise SmokeFailure(f"{INDEX_PATH}: profiles must be an object")
    if not isinstance(statewide, list) or not all(
        isinstance(rule_id, str) and rule_id for rule_id in statewide
    ):
        raise SmokeFailure(
            f"{INDEX_PATH}: statewide_rule_ids must be non-blank strings"
        )
    if not isinstance(hcd, dict) or not isinstance(hcd.get("letter_count"), int):
        raise SmokeFailure(f"{INDEX_PATH}: HCD dataset metadata is missing")
    if len(profiles) != expected_jurisdictions:
        raise SmokeFailure(
            f"{INDEX_PATH}: expected {expected_jurisdictions} jurisdiction profiles, "
            f"received {len(profiles)}"
        )
    if len(statewide) != expected_statewide_rules:
        raise SmokeFailure(
            f"{INDEX_PATH}: expected {expected_statewide_rules} statewide candidate rules, "
            f"received {len(statewide)}"
        )
    return len(profiles), len(statewide), hcd["letter_count"]


def run_smoke(
    base_url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    expected_jurisdictions: int = DEFAULT_EXPECTED_JURISDICTIONS,
    expected_statewide_rules: int = DEFAULT_EXPECTED_STATEWIDE_RULES,
    allow_http: bool = False,
    fetcher: Fetcher = _fetch,
) -> tuple[SmokeResult, ...]:
    """Check deployed routes and return one immutable result per contract."""

    if timeout <= 0:
        raise SmokeFailure("timeout must be greater than zero")
    if expected_jurisdictions <= 0 or expected_statewide_rules <= 0:
        raise SmokeFailure("expected record counts must be greater than zero")
    base = _validated_base_url(base_url, allow_http=allow_http)
    results: list[SmokeResult] = []
    for route in HTML_ROUTES:
        url = base + route.path
        body = _fetch_success(fetcher, url, timeout)
        if route.marker not in body:
            marker = route.marker.decode("ascii")
            raise SmokeFailure(f"{url}: deployed page is missing marker {marker}")
        results.append(SmokeResult(url=url, status=200, detail="route marker present"))

    index_url = base + INDEX_PATH
    index_body = _fetch_success(fetcher, index_url, timeout)
    jurisdictions, statewide_rules, hcd_letters = _validated_index(
        index_body,
        expected_jurisdictions=expected_jurisdictions,
        expected_statewide_rules=expected_statewide_rules,
    )
    results.append(
        SmokeResult(
            url=index_url,
            status=200,
            detail=(
                f"schema 1; {jurisdictions} profiles; {statewide_rules} statewide "
                f"candidate rules; {hcd_letters} dated HCD records"
            ),
        )
    )
    return tuple(results)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check the deployed static routes and generated coverage index. "
            "This is an availability/artifact smoke check, not a beta, legal, "
            "source-currency, or accessibility finding."
        )
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--expected-jurisdictions",
        type=int,
        default=DEFAULT_EXPECTED_JURISDICTIONS,
    )
    parser.add_argument(
        "--expected-statewide-rules",
        type=int,
        default=DEFAULT_EXPECTED_STATEWIDE_RULES,
    )
    parser.add_argument(
        "--allow-http",
        action="store_true",
        help="allow an HTTP base URL for a local server; production should use HTTPS",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        results = run_smoke(
            args.base_url,
            timeout=args.timeout,
            expected_jurisdictions=args.expected_jurisdictions,
            expected_statewide_rules=args.expected_statewide_rules,
            allow_http=args.allow_http,
        )
    except SmokeFailure as error:
        print(f"deployment smoke: FAIL: {error}", file=sys.stderr)
        return 1
    print("deployment smoke: PASS")
    for result in results:
        print(f"  {result.status} {result.url} — {result.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
