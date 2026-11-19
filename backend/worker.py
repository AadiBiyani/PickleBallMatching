"""Local prototype subprocess. Heavy dependencies stay in the model environment.

The API supplies a server-owned JSON request path. Both real pipelines use the
same harness projection; this bridge can be retired when experiments graduate
to a versioned models package. Nothing here classifies drill attempts.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "vlm-harness"))
sys.path.insert(0, str(ROOT / "experiments" / "player-tracking"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def video_info(video):
    import cv2

    capture = cv2.VideoCapture(str(video))
    try:
        if not capture.isOpened():
            raise ValueError("Could not open the video.")
        width, height = (
            int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        fps, count = capture.get(cv2.CAP_PROP_FPS), int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not math.isfinite(fps) or not 0 < fps <= 240 or count < 1 or width <= 0 or height <= 0:
            raise ValueError("Video dimensions, frame count or frame rate are invalid.")
        if width * height > 3840 * 2160 or count / fps > 300:
            raise ValueError("Use a clip up to 4K and five minutes for this local demo.")
        return dict(width=width, height=height, fps=fps, frame_count=count, duration_s=count / fps)
    finally:
        capture.release()


def preview(request, output):
    import cv2

    video = Path(request["video"])
    info = video_info(video)
    index = request["frame_index"]
    if not 0 <= index < info["frame_count"]:
        raise ValueError("Preview frame is outside the video.")
    if request["kind"] == "yolo":
        from player_tracking.tracking import preview_video

        return preview_video(video, output, frame_index=index)
    capture = cv2.VideoCapture(str(video))
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = capture.read()
        if not ok or not cv2.imwrite(str(output / "preview.jpg"), frame):
            raise ValueError("Could not decode the preview frame.")
    finally:
        capture.release()
    return {"source": info, "frame_index": index, "candidates": []}


def validate(request, info):
    import perspective

    options = request["analysis"]
    calibration = options["calibration"]
    if (calibration["width"], calibration["height"]) != (info["width"], info["height"]):
        raise ValueError("Calibration dimensions do not match this video.")
    corners = calibration["corners_px"]
    problems = perspective.validate_corners(corners, (info["height"], info["width"]))
    if problems:
        raise ValueError("Invalid court corners: " + "; ".join(problems))
    if any(not (0 <= x <= info["width"] and 0 <= y <= info["height"]) for x, y in corners):
        raise ValueError("Court corners must lie inside the original image.")
    if options["start_frame"] >= info["frame_count"]:
        raise ValueError("Starting frame is outside the video.")


def analyze(request, output):
    from harness.analyzers.base import create_analyzer
    from harness.run import run_harness

    video = Path(request["video"])
    info = video_info(video)
    validate(request, info)
    options, kind = request["analysis"], request["kind"]
    start = options["start_frame"]
    stop = min(start + options["max_frames"], info["frame_count"])
    corners = {
        "videos": {
            video.name: {
                **options["calibration"],
                "corner_order": ["far-left", "far-right", "near-right", "near-left"],
                "note": "User-supplied prototype calibration; accuracy is not established.",
            }
        }
    }
    corner_file = output / "corners.json"
    write(corner_file, corners)
    positions = None
    if kind == "yolo":
        from player_tracking.contracts import Selection, TrackingConfig
        from player_tracking.tracking import run_tracking

        selections = [
            Selection.model_validate({"frame_index": start, "bbox": box}) for box in options["selections"]
        ]
        tracked = run_tracking(
            video, selections, TrackingConfig(max_frames=options["max_frames"]), output / "native"
        )
        native = Path(tracked["output_dir"])
        positions = native / "positions.json"
        for name in ("positions.json", "positions.csv"):
            shutil.copyfile(native / name, output / name)
        players = list(tracked["metadata"]["selected_track_ids"])
        reference = "ankle_midpoint"
    elif kind == "mediapipe":
        if options["selections"]:
            raise ValueError("MediaPipe does not support selected-player identity tracking.")
        players, reference = ["detected_pose"], "heel_midpoint_or_single_heel"
    else:
        raise ValueError("Unknown real tracking model.")
    rows, audits = [], {}
    for player in players:
        analyzer = create_analyzer(
            "yolo:yolo26n-pose" if kind == "yolo" else "mediapipe:pose-landmarker-lite",
            **({"positions_path": positions, "player_id": player} if positions else {}),
        )
        try:
            outcome = run_harness(
                video,
                analyzer,
                corner_file,
                fps=options["sample_fps"],
                output_root=output / "evaluations",
                start_frame=start,
                stop_frame=stop,
            )
            for row in outcome.rows:
                observation = analyzer.records[row["source_frame_index"]] if kind == "yolo" else None
                rows.append(
                    {
                        **{
                            key: row[key]
                            for key in (
                                "frame_index",
                                "source_frame_index",
                                "time_s",
                                "x_px",
                                "y_px",
                                "x_ft",
                                "y_ft",
                                "zone",
                            )
                        },
                        "player_id": player,
                        "point_source": reference,
                        "status": observation.status
                        if observation
                        else ("ok" if row["x_px"] is not None else "not_visible"),
                        "reason": observation.reason
                        if observation
                        else (
                            None if row["x_px"] is not None else "No usable heel point in the sampled frame."
                        ),
                    }
                )
            audits[player] = json.loads((outcome.run_dir / "summary.json").read_text())
            if kind == "yolo":
                audits[player]["analyzer"] = analyzer.provenance()
        finally:
            if hasattr(analyzer, "close"):
                analyzer.close()
    rows.sort(key=lambda row: (row["source_frame_index"], row["player_id"]))
    write(output / "track.json", rows)
    with (output / "track.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with video.open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    write(
        output / "provenance.json",
        {
            "schema_version": "tracking-ui-1",
            "source_sha256": source_hash,
            "source": info,
            "kind": kind,
            "analysis": options,
            "players": audits,
            "software": {
                name: importlib.metadata.version(name)
                for name in (
                    ("ultralytics", "numpy", "opencv-python")
                    if kind == "yolo"
                    else ("mediapipe", "numpy", "opencv-contrib-python")
                )
            },
            "attempts_source": "unavailable",
            "accuracy_evaluated": False,
        },
    )
    limitations = [
        "Position estimates only. Ball tracking, attempt outcomes and coverage scores are unavailable.",
        "Court calibration is manually supplied; no labeled accuracy evaluation was performed.",
        "Zones cover the near half only. A visible far-half point is labeled out of court.",
        "Positions are foot-point proxies, not measured ground contact. Missing points are not interpolated.",
        "Sampling uses source frame indices and nominal FPS; variable-frame-rate alignment is unvalidated.",
    ]
    if kind == "mediapipe":
        limitations.append(
            "MediaPipe returns the first pose at each sample. It can switch people; identity is not locked."
        )
    return {
        "rows": rows,
        "summary": {
            "kind": kind,
            "model_id": "yolo26n-pose.pt" if kind == "yolo" else "pose_landmarker_lite",
            "model_version": "integration-1",
            "sample_fps": options["sample_fps"],
            "frame_size_px": [info["width"], info["height"]],
            "frames": len({r["frame_index"] for r in rows}),
            "observations": len(rows),
            "missing_frames": sum(r["zone"] == "not_visible" for r in rows),
            "zone_counts": dict(Counter(r["zone"] for r in rows)),
            "players": players,
            "data_source": "model",
            "limitations": limitations,
        },
    }


def main():
    path = Path(sys.argv[1])
    request = json.loads(path.read_text(encoding="utf-8"))
    try:
        result = (
            preview(request, path.parent)
            if request["operation"] == "preview"
            else analyze(request, path.parent)
        )
        write(path.parent / "response.json", result)
    except Exception as exc:
        write(path.parent / "response.json", {"error": str(exc)})
        raise


if __name__ == "__main__":
    main()
