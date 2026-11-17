"""Load a clip's zone labels CSV and validate it at the boundary.

Format (UTF-8, header required):

    time_s,zone
    0.0,backcourt_left
    1.0,transition_left

`zone` must be one of the eight contract zones. Malformed files raise ValueError with the
line number; a partial label set is never returned.

Deliberately does not match labels to frames (see metrics.match_labels).
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from .contract import ZONE_VALUES

REQUIRED_COLUMNS = ("time_s", "zone")


@dataclass(frozen=True)
class Label:
    time_s: float
    zone: str


def default_labels_path(video_path: str | Path) -> Path:
    p = Path(video_path)
    return p.with_name(f"{p.stem}.labels.csv")


def load_labels(path: str | Path) -> list[Label]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column(s) {missing}; expected header 'time_s,zone'")
        labels: list[Label] = []
        for line_no, row in enumerate(reader, start=2):
            raw_t = (row.get("time_s") or "").strip()
            zone = (row.get("zone") or "").strip()
            try:
                t = float(raw_t)
            except ValueError:
                raise ValueError(f"{path}:{line_no}: time_s {raw_t!r} is not a number") from None
            if not math.isfinite(t) or t < 0:
                raise ValueError(f"{path}:{line_no}: time_s must be a finite number >= 0")
            if zone not in ZONE_VALUES:
                raise ValueError(f"{path}:{line_no}: zone {zone!r} is not one of {list(ZONE_VALUES)}")
            labels.append(Label(t, zone))
    if not labels:
        raise ValueError(f"{path}: no label rows")
    return labels
