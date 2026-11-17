"""Acceptance case 9 (unit level): pacing and backoff with an injected clock."""

from __future__ import annotations

import pytest

from harness.analyzers.base import RateLimited
from harness.throttle import QuotaExhausted, Throttle


def flaky(failures: int, **kw):
    state = {"calls": 0}

    def fn():
        state["calls"] += 1
        if state["calls"] <= failures:
            raise RateLimited("429", **kw)
        return "ok"

    return fn, state


def test_backs_off_15_then_30_then_succeeds(fake_clock):
    t = Throttle(clock=fake_clock, sleep=fake_clock.sleep, log=lambda m: None)
    fn, state = flaky(2)
    result, _ = t.call(fn)
    assert result == "ok" and state["calls"] == 3
    assert fake_clock.sleeps == [15.0, 30.0]


def test_server_retry_hint_extends_wait(fake_clock):
    t = Throttle(clock=fake_clock, sleep=fake_clock.sleep, log=lambda m: None)
    fn, _ = flaky(1, retry_after_s=42.0)
    t.call(fn)
    assert fake_clock.sleeps == [42.0]


def test_gives_up_after_schedule(fake_clock):
    t = Throttle(clock=fake_clock, sleep=fake_clock.sleep, log=lambda m: None)
    fn, state = flaky(99)
    with pytest.raises(RateLimited):
        t.call(fn)
    assert state["calls"] == 5
    assert fake_clock.sleeps == [15.0, 30.0, 60.0, 120.0]


def test_quota_exhausted_is_not_retried(fake_clock):
    t = Throttle(clock=fake_clock, sleep=fake_clock.sleep, log=lambda m: None)
    fn, state = flaky(99, quota_exhausted=True)
    with pytest.raises(QuotaExhausted):
        t.call(fn)
    assert state["calls"] == 1 and fake_clock.sleeps == []


def test_min_interval_between_calls(fake_clock):
    t = Throttle(min_interval_s=10.0, clock=fake_clock, sleep=fake_clock.sleep, log=lambda m: None)
    t.call(lambda: 1)
    fake_clock.t += 3.0
    t.call(lambda: 2)
    assert fake_clock.sleeps == [pytest.approx(7.0)]
