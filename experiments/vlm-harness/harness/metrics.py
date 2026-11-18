"""Score harness zones and court positions against labels.

The zone compared here is the zone from court feet, not a zone chosen by the
model. A frame with no player point is the wrong zone, and it is a missing
position when the label has court feet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .frames import Frame
from .labels import Label


@dataclass(frozen=True)
class LabelMatch:
    by_frame: dict[int, Label]
    unmatched: tuple[Label, ...]


@dataclass(frozen=True)
class Score:
    zone_accuracy: float | None
    n_zone_labeled: int
    position_error_mean_ft: float | None
    position_error_max_ft: float | None
    n_position_scored: int
    n_position_missing: int


def match_labels(labels: list[Label], frames: list[Frame], interval_s: float) -> LabelMatch:
    """Match each label to the nearest sampled frame within half the sample interval."""
    if interval_s <= 0:
        raise ValueError(f"interval must be > 0, got {interval_s}")
    tol = interval_s / 2.0
    best: dict[int, tuple[float, Label]] = {}
    unmatched: list[Label] = []
    for label in labels:
        nearest = None
        nearest_dt = None
        for frame in frames:
            dt = abs(frame.time_s - label.time_s)
            if nearest_dt is None or dt < nearest_dt:
                nearest = frame
                nearest_dt = dt
        if nearest is None or nearest_dt is None or nearest_dt > tol:
            unmatched.append(label)
            continue
        previous = best.get(nearest.index)
        if previous is None or nearest_dt < previous[0]:
            if previous is not None:
                unmatched.append(previous[1])
            best[nearest.index] = (nearest_dt, label)
        else:
            unmatched.append(label)
    return LabelMatch({index: label for index, (_, label) in best.items()}, tuple(unmatched))


def score_rows(rows: list[dict]) -> Score:
    """Score rows that already include zone, feet, and any matched label fields."""
    labeled = [row for row in rows if row.get("label_zone")]
    if not labeled:
        zone_accuracy = None
        n_zone = 0
    else:
        correct = sum(1 for row in labeled if row["zone"] == row["label_zone"])
        zone_accuracy = correct / len(labeled)
        n_zone = len(labeled)

    errors: list[float] = []
    missing = 0
    for row in rows:
        if row.get("label_x_ft") in (None, "") or row.get("label_y_ft") in (None, ""):
            continue
        if row.get("x_ft") in (None, "") or row.get("y_ft") in (None, ""):
            missing += 1
            continue
        dx = float(row["x_ft"]) - float(row["label_x_ft"])
        dy = float(row["y_ft"]) - float(row["label_y_ft"])
        errors.append(math.hypot(dx, dy))
    if errors:
        mean = sum(errors) / len(errors)
        maximum = max(errors)
    else:
        mean = maximum = None
    return Score(zone_accuracy, n_zone, mean, maximum, len(errors), missing)
