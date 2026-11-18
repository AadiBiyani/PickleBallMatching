"""Stand-in model that fabricates a plausible track without reading video."""

import math
import random
from pathlib import Path

from ..schemas import Drill, TrackPoint, TrackResult
from .base import VisionModel

COURT_WIDTH_M = 6.10
FEED_INTERVAL_MS = 3000
SAMPLE_HZ = 10


class SimulatedModel(VisionModel):
    id = "simulated"
    name = "Simulated tracker"
    owner = "UI prototype"
    version = "0.1.0"
    description = "Generates a synthetic track so the flow works before a real model is chosen."
    requires_clip_file = False

    def track(self, clip_path: Path | None, drill: Drill, seed: int) -> TrackResult:
        rng = random.Random(seed)
        duration_ms = drill.feed_count * FEED_INTERVAL_MS
        n_regions = len(drill.regions)
        points: list[TrackPoint] = []
        for t in range(0, duration_ms, 1000 // SAMPLE_HZ):
            feed = t // FEED_INTERVAL_MS
            phase = (t % FEED_INTERVAL_MS) / FEED_INTERVAL_MS
            # Move from the center mark toward the feed's side, then recover.
            target = (feed % n_regions + 0.5) / n_regions * COURT_WIDTH_M
            centre = COURT_WIDTH_M / 2
            x = centre + (target - centre) * math.sin(math.pi * phase)
            if rng.random() < 0.03:
                points.append(TrackPoint(t_ms=t, x_m=None, y_m=None, confidence=0.0))
                continue
            points.append(
                TrackPoint(
                    t_ms=t,
                    x_m=round(x + rng.gauss(0, 0.05), 3),
                    y_m=round(-0.5 + rng.gauss(0, 0.05), 3),
                    confidence=round(rng.uniform(0.75, 0.98), 2),
                )
            )
        return TrackResult(model_id=self.id, model_version=self.version, points=points)
