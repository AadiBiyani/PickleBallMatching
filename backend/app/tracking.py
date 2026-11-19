"""Session orchestration for real tracking; simulation stays in pipeline.py."""

import uuid
from collections import Counter
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import HTTPException

from . import court
from .schemas import CourtPoint, TrackSummary
from .store import store
from .vision.workers import RUNTIME, invoke

SLOTS = BoundedSemaphore(4)
ARTIFACTS = {"track.json", "track.csv", "provenance.json", "positions.json", "positions.csv"}
STEPS = ["Queued for tracking", "Track players and map court positions", "Prepare tracking results"]


def validate_options(req, model):
    if not model.info().available:
        raise HTTPException(503, model.info().unavailable_reason)
    if req.analysis is None:
        raise HTTPException(422, "Preview the clip and supply four court corners before analysis.")
    options = req.analysis
    cal = options.calibration
    problems = court.validate_corners(cal.corners_px, cal.width, cal.height)
    if problems:
        raise HTTPException(422, "Invalid court corners: " + "; ".join(problems))
    if any(not (0 <= x <= cal.width and 0 <= y <= cal.height) for x, y in cal.corners_px):
        raise HTTPException(422, "Court corners must lie inside the original image.")
    if model.kind == "yolo" and not options.selections:
        raise HTTPException(422, "Select at least one player for YOLO.")
    if model.kind == "mediapipe" and options.selections:
        raise HTTPException(422, "MediaPipe does not support selected-player identity tracking.")
    boxes = [tuple(box.model_dump().values()) for box in options.selections]
    if len(set(boxes)) != len(boxes):
        raise HTTPException(422, "The same player box was selected more than once.")
    if any(box.x2 > cal.width or box.y2 > cal.height for box in options.selections):
        raise HTTPException(422, "Player boxes must lie inside the original image.")


def queue(session, req, model, clip, path, background):
    validate_options(req, model)
    if not SLOTS.acquire(blocking=False):
        raise HTTPException(429, "Tracking queue is full. Wait for a job to finish, then retry.")
    try:
        session = store.update(
            session.id,
            status="queued",
            step=0,
            progress=0,
            error=None,
            steps=list(STEPS),
            model_id=model.id,
            clip_id=clip.id,
            clip_size_mb=clip.size_mb,
            analysis=req.analysis,
            upload_attempts=session.upload_attempts + 1,
        )
        background.add_task(run, session.id, model.kind, path, req.analysis.model_dump(mode="json"))
    except Exception:
        SLOTS.release()
        raise
    return session


def validated_result(data, expected_kind=None):
    rows = [CourtPoint.model_validate(row) for row in data["rows"]]
    summary = TrackSummary.model_validate(data["summary"])
    if not rows or summary.data_source != "model":
        raise ValueError("Worker returned no real tracking observations.")
    if expected_kind is not None and summary.kind != expected_kind:
        raise ValueError("Worker result does not match the selected model.")
    seen = set()
    samples = {}
    for row in rows:
        key = (row.player_id, row.source_frame_index)
        if key in seen or row.source_frame_index is None or row.player_id not in summary.players:
            raise ValueError("Worker returned duplicate or unidentified player/frame observations.")
        seen.add(key)
        samples.setdefault(row.player_id, set()).add(row.source_frame_index)
        missing = row.zone == "not_visible"
        coords = (row.x_px, row.y_px, row.x_ft, row.y_ft)
        if (missing and any(c is not None for c in coords)) or (
            not missing and any(c is None for c in coords)
        ):
            raise ValueError("Worker coordinates do not match their visibility status.")
        if (row.status == "ok") == missing:
            raise ValueError("Worker tracking status does not match visibility.")
    if len(samples) != len(summary.players) or any(
        s != next(iter(samples.values())) for s in samples.values()
    ):
        raise ValueError("Worker must retain every sampled frame for every player.")
    if (
        summary.observations != len(rows)
        or summary.frames != len(next(iter(samples.values())))
        or summary.missing_frames != sum(r.zone == "not_visible" for r in rows)
        or summary.zone_counts != dict(Counter(r.zone for r in rows))
    ):
        raise ValueError("Worker summary does not match its observations.")
    return rows, summary


def run(session_id, kind, video, analysis):
    directory = RUNTIME / "sessions" / session_id / uuid.uuid4().hex
    try:
        with store.lock:
            if session_id not in store.sessions:
                return
            store.update(session_id, status="processing", step=1)
        data = invoke(
            kind, {"operation": "analyze", "kind": kind, "video": str(video), "analysis": analysis}, directory
        )
        rows, summary = validated_result(data, kind)
        with store.lock:
            if session_id not in store.sessions:
                return
            store.attempts[session_id] = []
            store.tracks[session_id] = summary
            store.track_points[session_id] = rows
            store.artifacts[session_id] = directory
            store.update(session_id, status="completed", step=len(STEPS), progress=1)
    except Exception as exc:
        with store.lock:
            if session_id in store.sessions:
                store.update(session_id, status="failed", error=f"Tracking failed: {exc}")
    finally:
        SLOTS.release()


def artifact(session_id: str, name: str) -> Path:
    root = store.artifacts.get(session_id)
    if name not in ARTIFACTS or root is None or not (root / name).is_file():
        raise HTTPException(404, "Tracking artifact not found.")
    return root / name
