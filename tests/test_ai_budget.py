"""Request budget: per-client sliding window and the daily cap."""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from permit_pathways.ai.budget import (
    DEFAULT_DAILY_CAP,
    Budget,
    BudgetExhausted,
    DailyCounter,
    DynamoCounter,
    MemoryCounter,
    budget_from_env,
)


def test_memory_counter_caps_per_day_and_resets_on_a_new_day() -> None:
    counter = MemoryCounter()
    assert [counter.increment("2026-08-21", 2) for _ in range(2)] == [1, 2]
    with pytest.raises(BudgetExhausted):
        counter.increment("2026-08-21", 2)
    assert counter.increment("2026-08-22", 2) == 1


def test_budget_sliding_window_per_client() -> None:
    budget = Budget(daily_cap=100, per_client_per_minute=2, counter=MemoryCounter())
    assert budget.charge("a", now=0.0)["daily_used"] == 1
    budget.charge("a", now=10.0)
    with pytest.raises(BudgetExhausted, match="too many"):
        budget.charge("a", now=20.0)
    budget.charge("b", now=20.0)
    assert budget.charge("a", now=61.0)["daily_used"] == 4
    budget.charge("c")


def test_budget_daily_cap_exhaustion_does_not_burn_client_window() -> None:
    budget = Budget(daily_cap=1, per_client_per_minute=2, counter=MemoryCounter())
    # First charge consumes the daily cap of 1
    assert budget.charge("client-1", now=0.0)["daily_used"] == 1

    # Client-1 retries 5 times while daily cap is exhausted
    for t in [1.0, 2.0, 3.0, 4.0, 5.0]:
        with pytest.raises(BudgetExhausted, match="daily request cap reached"):
            budget.charge("client-1", now=t)

    # If daily cap is now increased/replenished, client-1 should still have quota left
    # and should NOT be rejected with "too many requests from this client"
    budget.daily_cap = 10
    res = budget.charge("client-1", now=6.0)
    assert res["daily_used"] == 2


class _SlowCounter(DailyCounter):
    """A counter whose I/O takes long enough to widen the race window between
    the per-minute check and the daily-cap increment, if one exists."""

    def __init__(self, delay: float = 0.05) -> None:
        self._delay = delay
        self._inner = MemoryCounter()

    def increment(self, day: str, cap: int) -> int:
        time.sleep(self._delay)
        return self._inner.increment(day, cap)


def test_budget_concurrent_charges_never_exceed_the_per_client_cap() -> None:
    """Regression test for the TOCTOU race caught in review on #98: releasing
    the lock between the per-minute check and the daily-cap increment let any
    number of concurrent callers pass the check before any of them committed
    to the window, so the per-client cap enforced nothing for the duration of
    the (slow) daily-cap call. The cap must hold even when counter.increment
    is slow and many callers race it at once."""
    budget = Budget(daily_cap=1_000, per_client_per_minute=3, counter=_SlowCounter())
    admitted: list[bool] = []
    lock = threading.Lock()

    def attempt() -> None:
        try:
            budget.charge("client-x")
            ok = True
        except BudgetExhausted:
            ok = False
        with lock:
            admitted.append(ok)

    threads = [threading.Thread(target=attempt) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert admitted.count(True) == 3


def test_budget_from_env_defaults_and_table() -> None:
    default = budget_from_env({})
    assert default.daily_cap == DEFAULT_DAILY_CAP and isinstance(
        default.counter, MemoryCounter
    )
    custom = budget_from_env(
        {"PERMIT_AI_DAILY_CAP": "7", "PERMIT_AI_PER_CLIENT_PER_MINUTE": "3"}
    )
    assert (custom.daily_cap, custom.per_client_per_minute) == (7, 3)


class _FakeDynamo:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def update_item(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("ConditionalCheckFailedException: cap")
        return {"Attributes": {"count": {"N": "5"}}}


def test_dynamo_counter_uses_a_conditional_update() -> None:
    fake = _FakeDynamo()
    counter = DynamoCounter("permit-ai-budget", client=fake)
    assert counter.increment("2026-08-21", 10) == 5
    call = fake.calls[0]
    assert call["TableName"] == "permit-ai-budget"
    assert call["Key"] == {"day": {"S": "2026-08-21"}}
    assert call["ExpressionAttributeValues"][":cap"] == {"N": "10"}
    with pytest.raises(BudgetExhausted):
        DynamoCounter("t", client=_FakeDynamo(fail=True)).increment("2026-08-21", 10)

    class _Broken:
        def update_item(self, **kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("network")

    with pytest.raises(RuntimeError, match="network"):
        DynamoCounter("t", client=_Broken()).increment("2026-08-21", 10)
