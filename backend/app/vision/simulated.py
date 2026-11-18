"""Stand-in model that reports plausible court positions in feet without reading pixels.

It follows the expected default (`output_space = "court"`): positions come back
in court feet, so the pipeline only derives the zone. The image-pixel path used
by harness analyzers is covered by tests/test_court.py.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from .. import court
from ..frames import Frame
from .base import LocatedPoint, VisionModel

FEED_INTERVAL_S = 3.0
BASELINE_Y_FT = 42.5  # just inside the near baseline, so zones read "backcourt"
LATERAL_TARGETS_FT = (3.5, 10.0, 16.5)  # wide left, center, wide right


class SimulatedModel(VisionModel):
    id = "simulated"
    kind = "simulated"
    model_id = "simulated"
    name = "Simulated tracker"
    owner = "UI prototype"
    version = "0.3.0"
    description = "Generates synthetic court positions in feet so the flow works before a real model is chosen."
    output_space = "court"
    is_remote = False
    requires_clip_file = False
    sample_fps = 10.0

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed

    def locate(self, frames: Sequence[Frame]) -> list[LocatedPoint]:
        rng = random.Random(self._seed)
        points: list[LocatedPoint] = []
        for frame in frames:
            if rng.random() < 0.03:  # occasional dropout, reported as "not visible"
                points.append(LocatedPoint(frame.index))
                continue
            feed = int(frame.time_s // FEED_INTERVAL_S)
            phase = (frame.time_s % FEED_INTERVAL_S) / FEED_INTERVAL_S
            target = LATERAL_TARGETS_FT[feed % len(LATERAL_TARGETS_FT)]
            x_ft = court.CENTER_X_FT + (target - court.CENTER_X_FT) * math.sin(math.pi * phase) + rng.gauss(0, 0.15)
            y_ft = BASELINE_Y_FT + rng.gauss(0, 0.15)
            points.append(LocatedPoint(frame.index, x_ft=round(x_ft, 3), y_ft=round(y_ft, 3)))
        return points
