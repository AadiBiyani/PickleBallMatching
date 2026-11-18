"""Run one analyzer on one clip and score the shared court projection.

The analyzer returns image points. This module loads the saved corners, maps
every point into court feet, assigns the zone, and writes results.csv.

    python -m harness.run clip.mp4 --analyzer fake --corners data/corners.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PLAYER_TRACKING = EXPERIMENT_DIR.parent / "player-tracking"
if str(PLAYER_TRACKING) not in sys.path:
    sys.path.insert(0, str(PLAYER_TRACKING))

import perspective as court

from .analyzers import create_analyzer
from .contract import NOT_VISIBLE, zone_from_feet
from .corners import entry_for, load_registry, scale_corners
from .frames import DEFAULT_FPS, extract_frames
from .labels import default_labels_path, load_labels
from .metrics import match_labels, score_rows

RESULT_COLUMNS = [
    "clip",
    "analyzer",
    "model_id",
    "frame_index",
    "source_frame_index",
    "time_s",
    "x_px",
    "y_px",
    "x_ft",
    "y_ft",
    "zone",
    "label_zone",
    "label_x_ft",
    "label_y_ft",
    "position_error_ft",
]


@dataclass(frozen=True)
class RunOutcome:
    run_dir: Path
    rows: list[dict]
    score: object


def _blank(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def project_rows(video_name, analyzer, frames, points, corners_px, labeled):
    homography = court.compute_homography(corners_px)
    by_index = {point.frame_index: point for point in points}
    rows = []
    for frame in frames:
        point = by_index.get(frame.index)
        label = labeled.get(frame.index)
        x_px = y_px = x_ft = y_ft = None
        zone = NOT_VISIBLE
        if point is not None and point.visible:
            x_px = float(point.x_px)
            y_px = float(point.y_px)
            mapped = court.apply_homography(homography, [[x_px, y_px]])[0]
            x_ft = float(mapped[0])
            y_ft = float(mapped[1])
            zone = zone_from_feet(x_ft, y_ft)
        error = None
        if (
            label is not None
            and label.x_ft is not None
            and label.y_ft is not None
            and x_ft is not None
        ):
            error = ((x_ft - label.x_ft) ** 2 + (y_ft - label.y_ft) ** 2) ** 0.5
        rows.append(
            {
                "clip": video_name,
                "analyzer": analyzer.kind,
                "model_id": analyzer.model_id,
                "frame_index": frame.index,
                "source_frame_index": frame.source_frame_index,
                "time_s": frame.time_s,
                "x_px": x_px,
                "y_px": y_px,
                "x_ft": x_ft,
                "y_ft": y_ft,
                "zone": zone,
                "label_zone": "" if label is None else label.zone,
                "label_x_ft": None if label is None else label.x_ft,
                "label_y_ft": None if label is None else label.y_ft,
                "position_error_ft": error,
            }
        )
    return rows


def run_harness(
    video,
    analyzer,
    corners_path,
    labels_path=None,
    fps=DEFAULT_FPS,
    long_side_px=None,
    output_root=None,
    start_frame=0,
    stop_frame=None,
) -> RunOutcome:
    video = Path(video)
    clip = extract_frames(
        video,
        fps=fps,
        long_side_px=long_side_px,
        start_frame=start_frame,
        stop_frame=stop_frame,
    )
    validate_video = getattr(analyzer, "validate_video", None)
    if validate_video is not None:
        validate_video(
            video, clip.native_width, clip.native_height, start_frame, stop_frame
        )
    registry = load_registry(corners_path)
    entry = entry_for(registry, video.name, clip.native_width, clip.native_height)
    frame = clip.frames[0]
    corners_px = scale_corners(entry, frame.width_px, frame.height_px)
    points = list(analyzer.locate(clip.frames))
    if len(points) != len(clip.frames):
        raise ValueError(
            f"{analyzer.kind} returned {len(points)} points for {len(clip.frames)} frames"
        )

    labels = []
    label_file = None
    if labels_path is not None:
        label_file = Path(labels_path)
    else:
        guessed = default_labels_path(video)
        if guessed.is_file():
            label_file = guessed
    if label_file is not None:
        labels = load_labels(label_file)
    matched = match_labels(labels, clip.frames, 1.0 / fps) if labels else None
    labeled = {} if matched is None else matched.by_frame

    rows = project_rows(video.name, analyzer, clip.frames, points, corners_px, labeled)
    score = score_rows(rows)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = Path(output_root) if output_root is not None else EXPERIMENT_DIR / "output"
    run_dir = (
        root / "runs" / f"{stamp}_{video.stem}_{analyzer.kind}_{uuid.uuid4().hex[:8]}"
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    with (run_dir / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _blank(row[column]) for column in RESULT_COLUMNS})
    summary = {
        "clip": video.name,
        "analyzer": analyzer.kind,
        "model_id": analyzer.model_id,
        "frames": len(clip.frames),
        "native_size_px": [clip.native_width, clip.native_height],
        "frame_size_px": [frame.width_px, frame.height_px],
        "sampling": {
            "fps": fps,
            "start_frame": start_frame,
            "stop_frame_exclusive": stop_frame,
        },
        "corners_px": corners_px,
        "corner_registry_entry": registry["videos"][video.name],
        "zone_accuracy": score.zone_accuracy,
        "n_zone_labeled": score.n_zone_labeled,
        "position_error_mean_ft": score.position_error_mean_ft,
        "position_error_max_ft": score.position_error_max_ft,
        "n_position_scored": score.n_position_scored,
        "n_position_missing": score.n_position_missing,
        "unmatched_labels": []
        if matched is None
        else [label.time_s for label in matched.unmatched],
    }
    provenance = getattr(analyzer, "provenance", None)
    if provenance is not None:
        summary["analyzer_provenance_file"] = "analyzer.json"
        (run_dir / "analyzer.json").write_text(
            json.dumps(provenance(), indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return RunOutcome(run_dir, rows, score)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Project one model's player points onto the court and score them."
    )
    parser.add_argument("clip", help="path to the test video")
    parser.add_argument("--analyzer", required=True, help="fake or yolo[:yolo26n-pose]")
    parser.add_argument(
        "--positions", type=Path, help="completed YOLO positions.json export"
    )
    parser.add_argument("--player-id", help="explicit YOLO player, e.g. player_1")
    parser.add_argument(
        "--start-frame", type=int, default=0, help="first source frame to evaluate"
    )
    parser.add_argument(
        "--stop-frame", type=int, default=None, help="exclusive source frame limit"
    )
    parser.add_argument("--corners", required=True, help="corner registry JSON")
    parser.add_argument(
        "--labels",
        default=None,
        help="labels CSV; default is <clip>.labels.csv beside the clip when that file exists",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=DEFAULT_FPS,
        help="frames sampled per second (default 1)",
    )
    parser.add_argument(
        "--long-side",
        type=int,
        default=None,
        help="resize the long side to this many pixels; default keeps the video size",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="output root (default experiments/vlm-harness/output)",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        analyzer = create_analyzer(
            args.analyzer, positions_path=args.positions, player_id=args.player_id
        )
        outcome = run_harness(
            args.clip,
            analyzer,
            args.corners,
            labels_path=args.labels,
            fps=args.fps,
            long_side_px=args.long_side,
            output_root=args.output,
            start_frame=args.start_frame,
            stop_frame=args.stop_frame,
        )
    except (ValueError, OSError, court.CalibrationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    score = outcome.score
    zone = (
        "n/a"
        if score.zone_accuracy is None
        else f"{score.zone_accuracy:.3f} ({score.n_zone_labeled})"
    )
    mean = (
        "n/a"
        if score.position_error_mean_ft is None
        else f"{score.position_error_mean_ft:.3f} ft"
    )
    print(f"zone accuracy {zone}")
    print(f"position error mean {mean}; missing {score.n_position_missing}")
    print(f"wrote {outcome.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
