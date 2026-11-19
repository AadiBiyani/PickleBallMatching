"""A stand-in analyzer that returns scripted image points.

Used by tests and by an offline smoke run. It does not look at the pixels.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..contract import LocatedPoint
from ..frames import Frame


class FakeAnalyzer:
    kind = "fake"
    is_remote = False

    def __init__(self, model: str = "", points: dict[int, tuple[float, float] | None] | None = None) -> None:
        self.model_id = model or "fake"
        self._points = {} if points is None else points

    def locate(self, frames: Sequence[Frame]) -> list[LocatedPoint]:
        located = []
        for frame in frames:
            if frame.index in self._points:
                chosen = self._points[frame.index]
            else:
                chosen = (frame.width_px / 2.0, frame.height_px / 2.0)
            if chosen is None:
                located.append(LocatedPoint(frame.index, None, None))
            else:
                located.append(LocatedPoint(frame.index, float(chosen[0]), float(chosen[1])))
        return located
