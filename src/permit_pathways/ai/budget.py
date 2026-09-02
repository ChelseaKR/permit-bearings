"""Request budget: a per-client rate limit and a hard daily cap.

The service has no accounts, so the only levers against runaway cost or
abuse are these two. The per-client limit is a sliding window keyed by the
caller's address; the daily cap is a single counter that refuses every
model-backed request once the day's allowance is spent. In one process the
counter lives in memory; on a stateless host it can live in a DynamoDB
table so every instance shares the same ceiling. Neither stores anything
about the request beyond a count.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import os
import threading
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

DEFAULT_DAILY_CAP = 300
DEFAULT_PER_CLIENT_PER_MINUTE = 8


class BudgetExhausted(RuntimeError):
    """The daily cap or the per-client limit refused the request."""


def _today() -> str:
    return dt.datetime.now(dt.UTC).date().isoformat()


class DailyCounter(Protocol):
    def increment(self, day: str, cap: int) -> int:
        """Add one to the day's count and return it, or raise BudgetExhausted
        without counting when the cap is already reached."""


class MemoryCounter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = ""
        self._count = 0

    def increment(self, day: str, cap: int) -> int:
        with self._lock:
            if day != self._day:
                self._day, self._count = day, 0
            if self._count >= cap:
                raise BudgetExhausted("daily request cap reached")
            self._count += 1
            return self._count


class DynamoCounter:
    """One item per UTC day in a DynamoDB table; the conditional update is the
    atomic cap. Requires boto3 (present on AWS Lambda) and a table whose key
    is the string attribute ``day``."""

    def __init__(self, table_name: str, *, client: Any | None = None) -> None:
        self._table = table_name
        if client is None:  # pragma: no cover - exercised only on AWS
            import boto3  # type: ignore[import-untyped]

            client = boto3.client("dynamodb")
        self._client = client

    def increment(self, day: str, cap: int) -> int:
        try:
            response = self._client.update_item(
                TableName=self._table,
                Key={"day": {"S": day}},
                UpdateExpression="ADD #c :one SET #e = if_not_exists(#e, :expires)",
                ConditionExpression="attribute_not_exists(#c) OR #c < :cap",
                ExpressionAttributeNames={"#c": "count", "#e": "expires_at"},
                ExpressionAttributeValues={
                    ":one": {"N": "1"},
                    ":cap": {"N": str(cap)},
                    ":expires": {
                        "N": str(int(dt.datetime.now(dt.UTC).timestamp()) + 3 * 86400)
                    },
                },
                ReturnValues="UPDATED_NEW",
            )
        except (
            Exception
        ) as exc:  # boto3 surfaces the condition failure as a client error
            if (
                "ConditionalCheckFailed" in exc.__class__.__name__
                or "ConditionalCheckFailed" in str(exc)
            ):
                raise BudgetExhausted("daily request cap reached") from exc
            raise
        return int(response["Attributes"]["count"]["N"])


@dataclass
class Budget:
    daily_cap: int
    per_client_per_minute: int
    counter: DailyCounter

    def __post_init__(self) -> None:
        self._windows: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def charge(self, client_id: str, *, now: float | None = None) -> dict[str, int]:
        """Consume one request for ``client_id`` or raise BudgetExhausted."""
        import time

        moment = time.monotonic() if now is None else now
        with self._lock:
            window = self._windows.setdefault(client_id, deque())
            while window and moment - window[0] >= 60:
                window.popleft()
            if len(window) >= self.per_client_per_minute:
                raise BudgetExhausted(
                    "too many requests from this client; wait a minute"
                )
            # Reserve the slot now, while still holding the lock. Releasing
            # the lock before counter.increment (an I/O call, potentially
            # slow) and only appending afterward would reopen the per-minute
            # check to concurrent callers: any number of them could pass
            # "is the window under cap" before any one of them has committed
            # to it, and the cap would enforce nothing for the duration of
            # that call. Reserve first under the same lock acquisition as
            # the check, and roll the reservation back below if the daily
            # cap (rather than the per-minute one) is what rejects.
            window.append(moment)
            if len(self._windows) > 10_000:
                self._windows = {
                    k: v for k, v in self._windows.items() if v and moment - v[-1] < 60
                }
        try:
            used = self.counter.increment(_today(), self.daily_cap)
        except BudgetExhausted:
            with self._lock:
                reserved = self._windows.get(client_id)
                if reserved is not None:
                    with contextlib.suppress(ValueError):
                        # Already pruned by a concurrent charge for the same
                        # client: nothing left to roll back.
                        reserved.remove(moment)
            raise
        return {"daily_used": used, "daily_cap": self.daily_cap}


def budget_from_env(environ: Mapping[str, str] | None = None) -> Budget:
    env = os.environ if environ is None else environ
    cap = int(env.get("PERMIT_AI_DAILY_CAP", "").strip() or DEFAULT_DAILY_CAP)
    per_client = int(
        env.get("PERMIT_AI_PER_CLIENT_PER_MINUTE", "").strip()
        or DEFAULT_PER_CLIENT_PER_MINUTE
    )
    table = env.get("PERMIT_AI_BUDGET_TABLE", "").strip()
    counter: DailyCounter = DynamoCounter(table) if table else MemoryCounter()
    return Budget(cap, per_client, counter)
