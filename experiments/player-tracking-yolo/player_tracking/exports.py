"""Full tracking exports consumed by the browser and shared harness adapter."""

import csv
import json
from itertools import groupby
from pathlib import Path

from .contracts import FrameRecord


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def export_run(output: Path, metadata: dict, records: list[FrameRecord]) -> None:
    write_json(
        output / "positions.json",
        {
            "schema_version": "1.1",
            "metadata": metadata,
            "frames": [record.model_dump() for record in records],
        },
    )
    write_json(output / "run.json", metadata)
    columns = [
        "player_id",
        "frame_index",
        "timestamp_s",
        "selected_track_id",
        "status",
        "reason",
        "image_x_px",
        "image_y_px",
        "point_source",
        "left_ankle_confidence",
        "right_ankle_confidence",
        "bbox_x1",
        "bbox_y1",
        "bbox_x2",
        "bbox_y2",
    ]
    with (output / "positions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for record in records:
            row = record.model_dump(exclude={"bbox"})
            for name in ("x1", "y1", "x2", "y2"):
                row[f"bbox_{name}"] = getattr(record.bbox, name) if record.bbox else None
            writer.writerow(row)  # None is an empty CSV field, never a numerical zero.
    frames = []
    for index, group in groupby(records, key=lambda row: row.frame_index):
        rows = list(group)
        frames.append(
            {
                "frame_index": index,
                "timestamp_s": rows[0].timestamp_s,
                "file": f"{index:08d}.jpg",
                "statuses": {row.player_id: row.status for row in rows},
            }
        )
    write_json(
        output / "manifest.json",
        {
            "schema_version": "1.1",
            "complete": metadata["complete"],
            "width": metadata["source"]["width"],
            "height": metadata["source"]["height"],
            "frames": frames,
        },
    )


def sample_validation_rows(
    records: list[FrameRecord], timestamps_s: list[float], tolerance_s: float, *, player_id: str | None = None
):
    """Sample only AFTER continuous tracking; keep missing rows and unmatched requests.

    This utility serves timestamp consumers; the shared harness uses exact frame indices.
    Ties resolve to the earlier timestamp. Rows are never interpolated.
    """
    import math

    if player_id is not None:
        records = [row for row in records if row.player_id == player_id]
    if len({row.player_id for row in records}) > 1:
        raise ValueError("Choose a player_id when sampling a multi-player run.")
    if not math.isfinite(tolerance_s) or tolerance_s < 0:
        raise ValueError("Tolerance must be finite and nonnegative.")
    output = []
    for timestamp in timestamps_s:
        if not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError("Validation timestamps must be finite and nonnegative.")
        nearest = min(
            records, key=lambda row: (abs(row.timestamp_s - timestamp), row.timestamp_s), default=None
        )
        matched = nearest is not None and abs(nearest.timestamp_s - timestamp) <= tolerance_s
        output.append(
            {
                "requested_timestamp_s": timestamp,
                "matched": matched,
                "record": nearest.model_dump() if matched else None,
            }
        )
    return output
