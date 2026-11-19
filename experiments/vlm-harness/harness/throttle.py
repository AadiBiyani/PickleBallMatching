"""Request pacing and rate-limit backoff for free-tier model APIs.

Waits a minimum interval between real requests and, on a rate limit, backs off
on a fixed schedule (or longer if the server asks). Only rate limits are
retried: an invalid response is a result and is never retried here. Clock and
sleep are injectable so tests never really wait.

Copied from liam-test-harness (harness/throttle.py), unchanged apart from the
error import and an exception type for the exhausted daily quota.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

from .analyzers.base import AnalyzerRequestError, RateLimited

T = TypeVar("T")

DEFAULT_BACKOFF_S: tuple[float, ...] = (15.0, 30.0, 60.0, 120.0)


class QuotaExhausted(AnalyzerRequestError):
    """The provider reported a quota that will not recover within this run."""


@dataclass
class Throttle:
    min_interval_s: float = 0.0
    backoff_s: tuple[float, ...] = DEFAULT_BACKOFF_S
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    log: Callable[[str], None] = print
    waits_s: list[float] = field(default_factory=list)  # every pause taken, kept for provenance
    _last_start: float | None = None

    def _pace(self) -> None:
        if self._last_start is None or self.min_interval_s <= 0:
            return
        remaining = self.min_interval_s - (self.clock() - self._last_start)
        if remaining > 0:
            self.waits_s.append(remaining)
            self.sleep(remaining)

    def call(self, fn: Callable[[], T]) -> tuple[T, float]:
        """Run fn with pacing and backoff. Returns (result, latency of the successful call in s).

        Raises QuotaExhausted at once, or the last RateLimited when the schedule is used up.
        """
        attempt = 0
        while True:
            self._pace()
            self._last_start = self.clock()
            start = self._last_start
            try:
                result = fn()
            except RateLimited as exc:
                if exc.quota_exhausted:
                    raise QuotaExhausted(str(exc)) from exc
                if attempt >= len(self.backoff_s):
                    raise
                delay = max(self.backoff_s[attempt], exc.retry_after_s or 0.0)
                attempt += 1
                self.log(f"  rate limited; waiting {delay:.0f} s (retry {attempt}/{len(self.backoff_s)})")
                self.waits_s.append(delay)
                self.sleep(delay)
                continue
            return result, self.clock() - start
