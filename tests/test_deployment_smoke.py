from __future__ import annotations

import json
import urllib.error

import pytest

from permit_pathways import deployment_smoke


def _responses(
    *,
    profiles: int = 541,
    statewide_rules: int = 17,
) -> dict[str, bytes]:
    base = "https://example.gov/permit/"
    responses = {
        base + route.path: b"<html>" + route.marker + b"</html>"
        for route in deployment_smoke.HTML_ROUTES
    }
    responses[base + deployment_smoke.INDEX_PATH] = json.dumps(
        {
            "schema_version": 1,
            "hcd_dataset": {"letter_count": 1314},
            "profiles": {f"jurisdiction-{index}": {} for index in range(profiles)},
            "statewide_rule_ids": [
                f"candidate-rule-{index}" for index in range(statewide_rules)
            ],
        }
    ).encode()
    return responses


def _fetcher(responses: dict[str, bytes], *, status: int = 200):
    def fetch(url: str, timeout: float) -> tuple[int, bytes]:
        assert timeout == 3
        return status, responses[url]

    return fetch


def test_network_fetch_sets_user_agent_and_reads_response(monkeypatch) -> None:
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return b"deployed"

    def urlopen(request, *, timeout):
        assert request.full_url == "https://example.gov/permit/"
        assert request.get_header("User-agent") == (
            "permit-bearings-deployment-smoke/1"
        )
        assert timeout == 3
        return Response()

    monkeypatch.setattr(deployment_smoke.urllib.request, "urlopen", urlopen)
    assert deployment_smoke._fetch("https://example.gov/permit/", 3) == (
        200,
        b"deployed",
    )


def test_network_fetch_wraps_transport_failures(monkeypatch) -> None:
    def urlopen(request, *, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(deployment_smoke.urllib.request, "urlopen", urlopen)
    with pytest.raises(deployment_smoke.SmokeFailure, match="request failed"):
        deployment_smoke._fetch("https://example.gov/permit/", 3)


def test_run_smoke_checks_every_public_route_and_index() -> None:
    results = deployment_smoke.run_smoke(
        "https://example.gov/permit",
        timeout=3,
        fetcher=_fetcher(_responses()),
    )

    assert len(results) == 6
    assert all(result.status == 200 for result in results)
    assert results[-1].detail == (
        "schema 1; 541 profiles; 17 statewide candidate rules; 1314 dated HCD records"
    )


@pytest.mark.parametrize(
    ("base_url", "allow_http", "message"),
    [
        ("http://example.gov/permit", False, "must be an HTTPS URL"),
        ("https://user@example.gov/permit", False, "without credentials"),
        ("https://example.gov/permit?q=1", False, "query"),
        ("not-a-url", False, "HTTPS URL"),
    ],
)
def test_run_smoke_rejects_unsafe_or_ambiguous_base_urls(
    base_url: str,
    allow_http: bool,
    message: str,
) -> None:
    with pytest.raises(deployment_smoke.SmokeFailure, match=message):
        deployment_smoke.run_smoke(base_url, allow_http=allow_http)


def test_run_smoke_can_target_an_explicit_local_http_server() -> None:
    responses = {
        url.replace("https://", "http://"): body for url, body in _responses().items()
    }
    results = deployment_smoke.run_smoke(
        "http://example.gov/permit/",
        timeout=3,
        allow_http=True,
        fetcher=_fetcher(responses),
    )
    assert results[0].url == "http://example.gov/permit/"


@pytest.mark.parametrize("timeout", [0, -1])
def test_run_smoke_rejects_nonpositive_timeout(timeout: float) -> None:
    with pytest.raises(deployment_smoke.SmokeFailure, match="timeout"):
        deployment_smoke.run_smoke("https://example.gov", timeout=timeout)


@pytest.mark.parametrize(
    ("jurisdictions", "rules"),
    [(0, 17), (541, 0)],
)
def test_run_smoke_rejects_nonpositive_expected_counts(
    jurisdictions: int,
    rules: int,
) -> None:
    with pytest.raises(deployment_smoke.SmokeFailure, match="record counts"):
        deployment_smoke.run_smoke(
            "https://example.gov",
            expected_jurisdictions=jurisdictions,
            expected_statewide_rules=rules,
        )


def test_run_smoke_fails_on_non_200_response() -> None:
    with pytest.raises(deployment_smoke.SmokeFailure, match="received 503"):
        deployment_smoke.run_smoke(
            "https://example.gov/permit/",
            timeout=3,
            fetcher=_fetcher(_responses(), status=503),
        )


def test_run_smoke_fails_on_empty_response() -> None:
    responses = _responses()
    responses["https://example.gov/permit/"] = b""
    with pytest.raises(deployment_smoke.SmokeFailure, match="body is empty"):
        deployment_smoke.run_smoke(
            "https://example.gov/permit/",
            timeout=3,
            fetcher=_fetcher(responses),
        )


def test_run_smoke_fails_when_page_marker_is_missing() -> None:
    responses = _responses()
    responses["https://example.gov/permit/check.html"] = b"<html></html>"
    with pytest.raises(deployment_smoke.SmokeFailure, match="missing marker"):
        deployment_smoke.run_smoke(
            "https://example.gov/permit/",
            timeout=3,
            fetcher=_fetcher(responses),
        )


@pytest.mark.parametrize(
    ("index_payload", "message"),
    [
        (b"not-json", "valid UTF-8 JSON"),
        (json.dumps([]).encode(), "schema_version 1"),
        (json.dumps({"schema_version": 2}).encode(), "schema_version 1"),
        (
            json.dumps(
                {
                    "schema_version": 1,
                    "profiles": [],
                    "statewide_rule_ids": ["rule"],
                    "hcd_dataset": {"letter_count": 1},
                }
            ).encode(),
            "profiles must be an object",
        ),
        (
            json.dumps(
                {
                    "schema_version": 1,
                    "profiles": {},
                    "statewide_rule_ids": [""],
                    "hcd_dataset": {"letter_count": 1},
                }
            ).encode(),
            "statewide_rule_ids",
        ),
        (
            json.dumps(
                {
                    "schema_version": 1,
                    "profiles": {},
                    "statewide_rule_ids": ["rule"],
                    "hcd_dataset": {},
                }
            ).encode(),
            "HCD dataset metadata",
        ),
    ],
)
def test_run_smoke_rejects_malformed_index(
    index_payload: bytes,
    message: str,
) -> None:
    responses = _responses()
    responses["https://example.gov/permit/" + deployment_smoke.INDEX_PATH] = (
        index_payload
    )
    with pytest.raises(deployment_smoke.SmokeFailure, match=message):
        deployment_smoke.run_smoke(
            "https://example.gov/permit/",
            timeout=3,
            fetcher=_fetcher(responses),
        )


@pytest.mark.parametrize(
    ("profiles", "rules", "message"),
    [
        (540, 17, "expected 541 jurisdiction profiles"),
        (541, 16, "expected 17 statewide candidate rules"),
    ],
)
def test_run_smoke_rejects_unexpected_index_counts(
    profiles: int,
    rules: int,
    message: str,
) -> None:
    responses = _responses(profiles=profiles, statewide_rules=rules)
    with pytest.raises(deployment_smoke.SmokeFailure, match=message):
        deployment_smoke.run_smoke(
            "https://example.gov/permit/",
            timeout=3,
            fetcher=_fetcher(responses),
        )


def test_main_reports_pass(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(
        deployment_smoke,
        "run_smoke",
        lambda *args, **kwargs: (
            deployment_smoke.SmokeResult(
                url="https://example.gov/",
                status=200,
                detail="route marker present",
            ),
        ),
    )
    assert deployment_smoke.main(["--base-url", "https://example.gov/"]) == 0
    assert "deployment smoke: PASS" in capsys.readouterr().out


def test_main_reports_failure(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    def fail(*args, **kwargs):
        raise deployment_smoke.SmokeFailure("broken deployment")

    monkeypatch.setattr(deployment_smoke, "run_smoke", fail)
    assert deployment_smoke.main([]) == 1
    assert "deployment smoke: FAIL: broken deployment" in capsys.readouterr().err
