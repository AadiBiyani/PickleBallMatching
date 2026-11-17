"""Pure metrics for the zone harness: validity, self-agreement, foot spread, zone accuracy.

Missing or invalid predictions count against a metric (as disagreement or as wrong);
they are never dropped to improve a number. A metric with an empty denominator is
None ("unavailable"), never 0.

Deliberately does no I/O and knows nothing about providers.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .labels import Label


def valid_rate(statuses_ok: Sequence[bool]) -> float | None:
    """Share of rows that are valid. None when there are no rows."""
    if not statuses_ok:
        return None
    return sum(1 for s in statuses_ok if s) / len(statuses_ok)


def frame_agreement(zones: Sequence[str | None]) -> float:
    """Share of repeats that equal the most common valid zone. None entries are invalid
    responses: they never form the mode and count as disagreement (denominator = N)."""
    if not zones:
        raise ValueError("no repeats for frame")
    valid = [z for z in zones if z is not None]
    if not valid:
        return 0.0
    _, top = Counter(valid).most_common(1)[0]
    return top / len(zones)


def self_agreement(zones_by_frame: Mapping[int, Sequence[str | None]]) -> float | None:
    """Mean per-frame agreement across repeats. None with fewer than 2 repeats or no frames."""
    if not zones_by_frame:
        return None
    if any(len(z) < 2 for z in zones_by_frame.values()):
        return None
    return statistics.fmean(frame_agreement(z) for z in zones_by_frame.values())


def foot_spread_px(points_by_frame: Mapping[int, Sequence[tuple[int, int] | None]]) -> float | None:
    """Median distance (px) of each valid foot point from its frame's median point.
    Only frames with at least 2 valid points contribute. None if none do."""
    distances: list[float] = []
    for pts in points_by_frame.values():
        valid = [p for p in pts if p is not None]
        if len(valid) < 2:
            continue
        mx = statistics.median(p[0] for p in valid)
        my = statistics.median(p[1] for p in valid)
        distances.extend(math.hypot(x - mx, y - my) for x, y in valid)
    return statistics.median(distances) if distances else None


@dataclass(frozen=True)
class LabelMatch:
    by_frame: dict[int, str]          # frame index -> labeled zone
    unmatched: tuple[Label, ...]      # labels with no sampled frame within tolerance


def match_labels(labels: Sequence[Label], frame_times_s: Mapping[int, float], fps: float) -> LabelMatch:
    """Assign each label to the nearest sampled frame within half the sampling interval.
    If two labels reach the same frame, the nearer one wins and the other is unmatched."""
    tol = 0.5 / fps + 1e-9
    best: dict[int, tuple[float, Label]] = {}
    unmatched: list[Label] = []
    for lab in labels:
        if not frame_times_s:
            unmatched.append(lab)
            continue
        idx, t = min(frame_times_s.items(), key=lambda kv: (abs(kv[1] - lab.time_s), kv[0]))
        dt = abs(t - lab.time_s)
        if dt > tol:
            unmatched.append(lab)
            continue
        prev = best.get(idx)
        if prev is None or dt < prev[0]:
            if prev is not None:
                unmatched.append(prev[1])
            best[idx] = (dt, lab)
        else:
            unmatched.append(lab)
    return LabelMatch({i: lab.zone for i, (_, lab) in best.items()}, tuple(unmatched))


def zone_accuracy(
    predicted: Sequence[tuple[int, str | None]], labeled: Mapping[int, str]
) -> tuple[float | None, int]:
    """Accuracy over (frame_index, predicted zone or None) rows whose frame has a label.
    None (invalid or missing) counts as wrong. Returns (accuracy or None, rows scored)."""
    scored = [(i, z) for i, z in predicted if i in labeled]
    if not scored:
        return None, 0
    correct = sum(1 for i, z in scored if z is not None and z == labeled[i])
    return correct / len(scored), len(scored)
