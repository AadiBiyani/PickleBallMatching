"""Adapt continuous YOLO/ByteTrack exports; geometry stays in the shared harness."""

from __future__ import annotations

import json
from pathlib import Path

from ..contract import LocatedPoint


class YoloAnalyzer:
    kind = "yolo"
    is_remote = False

    def __init__(self, *, positions_path=None, player_id=None, model_id=""):
        if positions_path is None or not player_id:
            raise ValueError(
                "yolo requires --positions <positions.json> and an explicit --player-id"
            )
        try:
            from player_tracking.contracts import FrameRecord
            from player_tracking.video import sha256_file
        except ModuleNotFoundError as exc:
            raise ValueError(
                "Use the player-tracking-yolo Python 3.12 environment; see the harness README."
            ) from exc

        self.positions_path = Path(positions_path)
        self.export_sha256 = sha256_file(self.positions_path)
        data = json.loads(self.positions_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != "1.1":
            raise ValueError("YOLO positions must use schema_version 1.1")
        metadata = data.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("complete") is not True:
            raise ValueError("YOLO evaluation requires a complete tracking run")
        if metadata.get("processing_stride") != 1:
            raise ValueError(
                "YOLO export must come from continuous tracking (processing_stride 1)"
            )
        if metadata.get("coordinate_system") != "original_image_pixels":
            raise ValueError("YOLO coordinates must be original_image_pixels")
        if metadata.get("point_source") != "ankle_midpoint":
            raise ValueError("YOLO export must declare point_source ankle_midpoint")
        self.model_id = metadata.get("model_name")
        if self.model_id != "yolo26n-pose.pt" or (
            model_id
            and model_id.removesuffix(".pt") != self.model_id.removesuffix(".pt")
        ):
            raise ValueError("YOLO model must match the export: yolo26n-pose.pt")
        source = metadata.get("source")
        if not isinstance(source, dict) or not isinstance(source.get("sha256"), str):
            raise ValueError("YOLO export requires source dimensions and SHA-256")  # noqa: TRY004 -- invalid file data
        for field in ("width", "height", "frame_count"):
            if type(source.get(field)) is not int or source[field] <= 0:
                raise ValueError(f"YOLO source {field} must be a positive integer")
        track_ids = metadata.get("selected_track_ids")
        if not isinstance(track_ids, dict) or player_id not in track_ids:
            raise ValueError(
                f"Unknown YOLO player_id {player_id!r}; choose from {track_ids}"
            )
        start = metadata.get("start_frame")
        count = metadata.get("processed_frame_count")
        if type(start) is not int or start < 0 or type(count) is not int or count < 1:
            raise ValueError("YOLO export requires a nonempty source frame window")
        if count != metadata.get("requested_frame_count"):
            raise ValueError("YOLO processed/requested frame counts differ")
        if start + count > source["frame_count"]:
            raise ValueError("YOLO window extends beyond the source frame count")
        raw_rows = data.get("frames")
        if not isinstance(raw_rows, list):
            raise ValueError("YOLO frames must be an array")  # noqa: TRY004 -- invalid file data
        rows = [FrameRecord.model_validate(row) for row in raw_rows]
        seen = set()
        for row in rows:
            key = (row.player_id, row.frame_index)
            if key in seen:
                raise ValueError(f"Duplicate YOLO observation {key}")
            seen.add(key)
            if (
                row.player_id not in track_ids
                or row.selected_track_id != track_ids[row.player_id]
            ):
                raise ValueError(
                    "YOLO observation does not match its selected player/track ID"
                )
            if not start <= row.frame_index < start + count:
                raise ValueError(
                    "YOLO observation lies outside its declared frame window"
                )
            coords = (row.image_x_px, row.image_y_px)
            if row.status == "ok":
                if any(value is None for value in coords):
                    raise ValueError("YOLO ok observations require both coordinates")
                if not (
                    0 <= coords[0] < source["width"]
                    and 0 <= coords[1] < source["height"]
                ):
                    raise ValueError("YOLO point lies outside the source image")
            elif coords != (None, None):
                raise ValueError(
                    "Missing YOLO observations require two null coordinates"
                )
        self.records = {
            row.frame_index: row for row in rows if row.player_id == player_id
        }
        if len(self.records) != count or set(self.records) != set(
            range(start, start + count)
        ):
            raise ValueError(
                "Selected YOLO player must have one observation per tracked source frame"
            )
        self.metadata = metadata
        self.player_id = player_id
        self.start_frame = start
        self.stop_frame = start + count
        self.sample_details = []

    def validate_video(self, video, width, height, start_frame, stop_frame):
        """Prevent filename collisions and accidental evaluation against another clip."""
        from player_tracking.video import sha256_file

        source = self.metadata["source"]
        if (width, height) != (source["width"], source["height"]):
            raise ValueError("YOLO export dimensions do not match the evaluation video")
        if sha256_file(Path(video)) != source["sha256"]:
            raise ValueError("YOLO source SHA-256 does not match the evaluation video")
        stop = source["frame_count"] if stop_frame is None else stop_frame
        if start_frame < self.start_frame or stop > self.stop_frame:
            raise ValueError(
                f"Evaluation window was not fully tracked; use --start-frame {self.start_frame} "
                f"--stop-frame {self.stop_frame} (exclusive), or generate a longer tracking run."
            )

    def locate(self, frames):
        """Select exact source frames AFTER tracking, then scale into harness pixels.

        Never infer from rounded timestamps or bridge a missing detection. The
        harness sample index is returned; it is not the source video frame index.
        """
        self.sample_details = []
        points = []
        source = self.metadata["source"]
        for frame in frames:
            if frame.source_frame_index is None:
                raise ValueError(
                    "YOLO evaluation requires source_frame_index on every sampled frame"
                )
            row = self.records.get(frame.source_frame_index)
            if row is None:
                raise ValueError(
                    f"Source frame {frame.source_frame_index} was not tracked; "
                    f"use --start-frame {self.start_frame} --stop-frame {self.stop_frame} "
                    "(exclusive), or generate a longer tracking run."
                )
            x = y = None
            if row.status == "ok":
                x = row.image_x_px * frame.width_px / source["width"]
                y = row.image_y_px * frame.height_px / source["height"]
            points.append(LocatedPoint(frame.index, x, y))
            self.sample_details.append(
                {
                    "sample_index": frame.index,
                    "sample_time_s": frame.time_s,
                    "observation": row.model_dump(),
                }
            )
        return points

    def provenance(self):
        """Preserve tracker status, reference point, software, settings and timing."""
        return {
            "adapter": "yolo-export-v1",
            "positions_file": self.positions_path.name,
            "positions_sha256": self.export_sha256,
            "player_id": self.player_id,
            "sampling": "exact source frame index after continuous tracking; no interpolation",
            "tracking_metadata": self.metadata,
            "samples": self.sample_details,
        }
