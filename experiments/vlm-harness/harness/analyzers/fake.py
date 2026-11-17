"""Fake analyzer with canned responses, for tests and offline smoke runs. SYNTHETIC output.

Scenarios (the part after 'fake:'):
  valid                 well-formed answers, zone cycles with frame index
  noisy                 like valid, but every third call changes zones (self-agreement < 1)
  invalid_json          returns text that is not JSON
  missing_frame         omits the middle frame of each batch
  bad_zone              first frame gets an unknown zone 'kitchen_center'
  rate_limit_then_ok    two rate-limit errors, then valid answers
  always_rate_limited   every call is rate limited
  quota_exhausted       daily quota exhausted
  request_failed        every call fails with a non-rate-limit error

Deliberately makes no network calls and looks at no pixels.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from ..frames import Frame
from .base import RateLimited, RequestFailed

COURT_ZONES = (
    "backcourt_left",
    "backcourt_right",
    "transition_left",
    "transition_right",
    "kitchen_left",
    "kitchen_right",
)
SCENARIOS = (
    "valid",
    "noisy",
    "invalid_json",
    "missing_frame",
    "bad_zone",
    "rate_limit_then_ok",
    "always_rate_limited",
    "quota_exhausted",
    "request_failed",
)


def canned_entry(index: int, shift: int = 0) -> dict:
    return {
        "frame_index": index,
        "zone": COURT_ZONES[(index + shift) % len(COURT_ZONES)],
        "foot_x": 300 + 50 * (index % 8),
        "foot_y": 600 + 40 * (index % 8),
    }


class FakeAnalyzer:
    kind = "fake"
    is_remote = False
    default_batch_size: int | None = None
    default_min_interval_s = 0.0
    notice = "Fake analyzer: canned SYNTHETIC responses, not a model."

    def __init__(self, scenario: str = "valid", responses: Sequence[str] | None = None) -> None:
        if responses is None and scenario not in SCENARIOS:
            raise ValueError(f"unknown fake scenario {scenario!r}; choose from {list(SCENARIOS)}")
        self.scenario = scenario
        self.model_id = f"fake-{scenario}"
        self._scripted = list(responses) if responses is not None else None
        self.calls = 0
        self.requests: list[list[int]] = []   # frame indices of each call, for tests

    @property
    def name(self) -> str:
        return f"fake:{self.scenario}"

    def request(self, frames: Sequence[Frame], prompt: str, schema: dict, temperature: float | None) -> str:
        self.calls += 1
        indices = [f.index for f in frames]
        self.requests.append(indices)
        if self._scripted is not None:
            return self._scripted.pop(0)
        s = self.scenario
        if s == "always_rate_limited" or (s == "rate_limit_then_ok" and self.calls <= 2):
            raise RateLimited("fake 429 RESOURCE_EXHAUSTED")
        if s == "quota_exhausted":
            raise RateLimited("fake daily quota", quota_exhausted=True)
        if s == "request_failed":
            raise RequestFailed("fake connection error")
        if s == "invalid_json":
            return "Sure! The player is in the kitchen."
        entries = [canned_entry(i, shift=1 if (s == "noisy" and self.calls % 3 == 0) else 0) for i in indices]
        if s == "missing_frame" and entries:
            entries.pop(len(entries) // 2)
        if s == "bad_zone" and entries:
            entries[0]["zone"] = "kitchen_center"
        return json.dumps({"frames": entries})
