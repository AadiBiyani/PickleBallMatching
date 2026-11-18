"""Load ground-truth labels for one clip.

Required columns are time_s and zone. x_ft and y_ft are optional. A file that
omits them can still score zones. A malformed file raises ValueError with its
line number.
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
    x_ft: float | None = None
    y_ft: float | None = None


def default_labels_path(video_path: str | Path) -> Path:
    path = Path(video_path)
    return path.with_name(f"{path.stem}.labels.csv")


def _optional_feet(row: dict, column: str, path: Path, line_no: int) -> float | None:
    raw = (row.get(column) or "").strip()
    if raw == "":
        return None
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{path}:{line_no}: {column} {raw!r} is not a number") from None
    if not math.isfinite(value):
        raise ValueError(f"{path}:{line_no}: {column} must be finite")
    return value


def load_labels(path: str | Path) -> list[Label]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column(s) {missing}; expected header 'time_s,zone'")
        labels: list[Label] = []
        for line_no, row in enumerate(reader, start=2):
            raw_t = (row.get("time_s") or "").strip()
            zone = (row.get("zone") or "").strip()
            try:
                time_s = float(raw_t)
            except ValueError:
                raise ValueError(f"{path}:{line_no}: time_s {raw_t!r} is not a number") from None
            if not math.isfinite(time_s) or time_s < 0:
                raise ValueError(f"{path}:{line_no}: time_s must be a finite number >= 0")
            if zone not in ZONE_VALUES:
                raise ValueError(f"{path}:{line_no}: zone {zone!r} is not one of {list(ZONE_VALUES)}")
            x_ft = _optional_feet(row, "x_ft", path, line_no)
            y_ft = _optional_feet(row, "y_ft", path, line_no)
            if (x_ft is None) != (y_ft is None):
                raise ValueError(f"{path}:{line_no}: x_ft and y_ft must both be present or both be empty")
            labels.append(Label(time_s, zone, x_ft, y_ft))
    if not labels:
        raise ValueError(f"{path}: no label rows")
    return labels
