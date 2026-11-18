import importlib.metadata
import math
import platform
import time
import uuid
from collections import Counter, deque
from itertools import pairwise
from pathlib import Path

import cv2
import numpy as np

from .backend import TRACKER_CONFIG, WEIGHTS, YoloBackend
from .contracts import InputError, Selection, TrackingConfig
from .exports import export_run, write_json
from .selection import position_record, select_track
from .video import inspect_video, open_at_frame, sha256_file


def preview_video(video: Path, output: Path, frame_index=0, config=None, backend_factory=YoloBackend):
    config = config or TrackingConfig()
    info = inspect_video(video)
    if frame_index < 0 or frame_index >= info.frame_count:
        raise InputError("Preview frame is outside the video.")
    capture = open_at_frame(video, frame_index)
    try:
        ok, frame = capture.read()
        if not ok:
            raise InputError("Cannot decode the preview frame.")
    finally:
        capture.release()
    backend = backend_factory(config)
    start = time.perf_counter()
    detections = backend.detect(frame, track=False)
    output.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output / "preview.jpg"), frame):
        raise RuntimeError("Could not write preview image.")
    candidates = [
        {"candidate_id": index, "bbox": item.bbox.model_dump(), "confidence": item.confidence}
        for index, item in enumerate(detections)
    ]
    data = {
        "source": info.model_dump(),
        "frame_index": frame_index,
        "candidates": candidates,
        "coordinate_system": "original_image_pixels",
        "model_load_s": backend.load_seconds,
        "detection_s": time.perf_counter() - start,
    }
    write_json(output / "preview.json", data)
    return data


def annotate_frame(frame, detections, records, trails):
    image = frame.copy()
    selected_ids = {row.selected_track_id: row.player_id for row in records}
    for item in detections:
        selected = item.track_id in selected_ids
        color = (80, 220, 80) if selected else (150, 150, 150)
        x1, y1, x2, y2 = map(round, (item.bbox.x1, item.bbox.y1, item.bbox.x2, item.bbox.y2))
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 3 if selected else 1)
        label = f"{selected_ids[item.track_id]} / ID {item.track_id}" if selected else f"ID {item.track_id}"
        cv2.putText(image, label, (x1, max(16, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    for record in records:
        trail = trails[record.player_id]
        if record.status == "ok":
            point = (round(record.image_x_px), round(record.image_y_px))
            trail.append(point)
            if len(trail) > 1:
                cv2.polylines(image, [np.array(trail, dtype=np.int32)], False, (0, 230, 255), 3)
            cv2.circle(image, point, 7, (0, 230, 255), -1)
        else:
            trail.clear()  # Each player's trail breaks independently across missing observations.
    cv2.rectangle(image, (0, 0), (image.shape[1], 36), (24, 24, 24), -1)
    cv2.putText(
        image,
        f"Frame {records[0].frame_index} | ankle_midpoint proxy (not foot-floor contact)",
        (15, 27),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (240, 240, 240),
        1,
    )
    footer_top = image.shape[0] - 15 - 25 * len(records)
    cv2.rectangle(image, (0, footer_top), (image.shape[1], image.shape[0]), (24, 24, 24), -1)
    for index, record in enumerate(records):
        color = (80, 220, 80) if record.status == "ok" else (100, 180, 255)
        label = f"{record.player_id} / ID {record.selected_track_id}: {record.status}"
        if record.reason:
            label += f" | {record.reason}"
        cv2.putText(image, label, (15, footer_top + 25 + 25 * index), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
    return image


def assign_timestamps(records, timestamps, fps):
    valid = (
        bool(timestamps)
        and all(math.isfinite(t) and t >= 0 for t in timestamps)
        and all(b > a for a, b in pairwise(timestamps))
    )
    # A zero timestamp on a later selection frame indicates an unusable decoder clock.
    if records and records[0].frame_index > 0 and timestamps[0] == 0:
        valid = False
    for row, timestamp in zip(records, timestamps, strict=True):
        row.timestamp_s = timestamp if valid else row.frame_index / fps
    return (
        "opencv_pos_msec" if valid else "frame_index_over_fps",
        None if valid else "Decoder timestamps were missing/nonmonotonic; constant-frame-rate fallback.",
    )


def run_tracking(
    video: Path,
    selection: Selection | list[Selection],
    config: TrackingConfig,
    output_root: Path,
    *,
    run_id: str | None = None,
    backend_factory=YoloBackend,
    progress=None,
):
    start = time.perf_counter()
    selections = [selection] if isinstance(selection, Selection) else selection
    if not 1 <= len(selections) <= 8:
        raise InputError("Select between one and eight players.")
    selection = selections[0]
    if any(item.frame_index != selection.frame_index for item in selections):
        raise InputError("All players must be selected on the same preview frame.")
    info = inspect_video(video)
    if any(not item.bbox.in_image(info.width, info.height) for item in selections):
        raise InputError("Selection coordinates must lie inside the original image.")
    if selection.frame_index >= info.frame_count:
        raise InputError("Selection frame is outside the video.")
    run_id = run_id or uuid.uuid4().hex
    output = output_root / run_id
    output.mkdir(parents=True, exist_ok=False)
    frames_dir = output / "frames"
    frames_dir.mkdir()
    count = min(config.max_frames, info.frame_count - selection.frame_index)
    real_model = backend_factory is YoloBackend
    metadata = {
        "schema_version": "1.1",
        "run_id": run_id,
        "complete": False,
        "source": {"identifier": video.name, "sha256": sha256_file(video), **info.model_dump()},
        "model_name": "yolo26n-pose.pt" if real_model else "test-double",
        "weights_sha256": sha256_file(WEIGHTS) if real_model and WEIGHTS.is_file() else None,
        "tracker": {
            "file": "bytetrack.yaml",
            "sha256": sha256_file(TRACKER_CONFIG),
            "configuration": TRACKER_CONFIG.read_text(),
        },
        "software": {
            name: importlib.metadata.version(name)
            for name in ("ultralytics", "torch", "opencv-python", "numpy", "fastapi", "pydantic")
        },
        "os": platform.platform(),
        "machine": platform.machine(),
        "device": config.device,
        "selections": [
            {"player_id": f"player_{i + 1}", **item.model_dump()} for i, item in enumerate(selections)
        ],
        "settings": config.model_dump(),
        "selected_player_count": len(selections),
        "coordinate_system": "original_image_pixels",
        "point_source": "ankle_midpoint",
        "reference_point_limit": "Ankle midpoint is above the floor; not a foot-floor contact measurement.",
        "processing_stride": 1,
        "start_frame": selection.frame_index,
        "requested_frame_count": count,
        "scope": "continuous window beginning at selected preview frame; no implicit pre-window predictions",
        "model_load_s": None,
        "tracking_processing_s": 0,
        "error": None,
        "weights_download": "separate prepare-model command; not included in inference timing",
    }
    records, timestamps = [], []
    capture = None
    processing_start = None
    failure = None
    try:
        backend = backend_factory(config)
        metadata["model_load_s"] = backend.load_seconds
        capture = open_at_frame(video, selection.frame_index)
        processing_start = time.perf_counter()
        track_ids = None
        trails = {f"player_{i + 1}": deque(maxlen=60) for i in range(len(selections))}
        for offset in range(count):
            ok, frame = capture.read()
            if not ok or frame is None:
                raise InputError("Video decoding ended before the requested window; this run is incomplete.")
            if frame.shape[:2] != (info.height, info.width):
                raise InputError("Video dimensions changed within the run.")
            timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            detections = backend.detect(frame, track=True)
            if track_ids is None:
                track_ids = [select_track(item.bbox, detections, config) for item in selections]
                if len(set(track_ids)) != len(track_ids):
                    raise InputError("Two selections matched the same person. Select each player only once.")
                metadata["selected_track_ids"] = dict(zip(trails, track_ids, strict=True))
            frame_index = selection.frame_index + offset
            frame_records = []
            for player_id, track_id in zip(trails, track_ids, strict=True):
                record = position_record(
                    frame_index, track_id, detections, info.width, info.height, config.ankle_confidence
                )
                record.player_id = player_id
                frame_records.append(record)
            annotated = annotate_frame(frame, detections, frame_records, trails)
            if not cv2.imwrite(
                str(frames_dir / f"{frame_index:08d}.jpg"), annotated, [cv2.IMWRITE_JPEG_QUALITY, 80]
            ):
                raise RuntimeError("Failed to save an annotated frame.")
            records.extend(frame_records)
            timestamps.append(timestamp)
            if progress:
                progress(offset + 1, count)
        metadata["complete"] = True
    except Exception as error:  # noqa: BLE001 -- preserve an explicitly incomplete run before re-raising
        failure = error
        metadata["error"] = str(error)
    finally:
        if capture is not None:
            capture.release()
        if processing_start is not None:
            metadata["tracking_processing_s"] = time.perf_counter() - processing_start
    first_player_rows = records[:: len(selections)]
    source, assumption = assign_timestamps(first_player_rows, timestamps, info.fps)
    for index, row in enumerate(records):
        row.timestamp_s = first_player_rows[index // len(selections)].timestamp_s
    counts = Counter(row.status for row in records)
    per_player = {}
    for index in range(len(selections)):
        player_id = f"player_{index + 1}"
        player_counts = Counter(row.status for row in records if row.player_id == player_id)
        per_player[player_id] = {
            status: player_counts[status] for status in ("ok", "target_not_detected", "keypoints_unreliable")
        }
    metadata.update(
        timestamp_source=source,
        timestamp_assumption=assumption,
        processed_frame_count=len(timestamps),
        observation_count=len(records),
        per_player_counts=per_player,
        usable_position_count=counts["ok"],
        missing_counts={name: counts[name] for name in ("target_not_detected", "keypoints_unreliable")},
        total_elapsed_s=time.perf_counter() - start,
        timing_scope="Total ends before final JSON/CSV serialization; processing includes decoding, inference and JPEG writes.",
    )
    export_run(output, metadata, records)
    if failure is not None:
        raise failure
    return {"output_dir": str(output), "metadata": metadata}
