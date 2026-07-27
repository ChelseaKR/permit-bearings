"""Source currency watcher.

Re-fetches every watched source document and compares its content hash to
the hash recorded when rules were last verified. A changed hash means the
source has been revised — every rule citing it must be treated as stale
until a person re-verifies the rule against the new text. Fetch failures
are reported, never swallowed: an unwatchable source is a currency problem
in itself.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

FETCH_TIMEOUT_SECONDS = 30
USER_AGENT = "permit-pathways-currency-watch/0.1"


@dataclass
class WatchResult:
    unchanged: list[str] = field(default_factory=list)   # source URLs
    changed: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)  # url -> reason

    def summary(self, labels: dict[str, str]) -> str:
        lines = ["Source currency check"]
        for url in self.unchanged:
            lines.append(f"  unchanged: {labels.get(url, url)}")
        for url in self.changed:
            lines.append(f"  CHANGED:   {labels.get(url, url)} — re-verify dependent rules")
        for url, reason in self.errors.items():
            lines.append(f"  ERROR:     {labels.get(url, url)} — {reason}")
        return "\n".join(lines)


def load_sources(path: Path) -> dict:
    return json.loads(path.read_text())


def check_sources(sources_path: Path) -> WatchResult:
    sources = load_sources(sources_path)
    result = WatchResult()
    for url, meta in sources.items():
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as resp:
                digest = hashlib.sha256(resp.read()).hexdigest()
        except Exception as exc:  # noqa: BLE001 — any fetch failure is reportable
            result.errors[url] = str(exc)
            continue
        if digest == meta["sha256"]:
            result.unchanged.append(url)
        else:
            result.changed.append(url)
    return result
