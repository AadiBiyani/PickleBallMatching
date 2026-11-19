import hashlib
import math
from pathlib import Path

import cv2

from .contracts import InputError, VideoInfo

MAX_UPLOAD_BYTES = 600 * 1024 * 1024
MAX_VIDEO_DURATION_S = 300
MAX_PIXELS = 3840 * 2160


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_video(path: Path, *, enforce_demo_limits: bool = False) -> VideoInfo:
    if not path.is_file() or path.stat().st_size == 0:
        raise InputError("Video is missing or empty.")
    if enforce_demo_limits and path.stat().st_size > MAX_UPLOAD_BYTES:
        raise InputError("Video exceeds the 600 MiB local-demo upload limit.")
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise InputError("Cannot decode this video. Try an MP4 with H.264 video.")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not math.isfinite(fps) or fps <= 0 or fps > 240:
            raise InputError("Video has invalid or unsupported FPS metadata (expected 0 < FPS <= 240).")
        if not math.isfinite(count) or count < 1:
            raise InputError("Video must report a positive frame count.")
        ok, frame = capture.read()
        if not ok or frame is None:
            raise InputError("Video contains no decodable first frame.")
        height, width = frame.shape[:2]
        if width * height > MAX_PIXELS:
            raise InputError("Video resolution exceeds the 3840 × 2160 pixel budget.")
        duration = count / fps
        if enforce_demo_limits and duration > MAX_VIDEO_DURATION_S:
            raise InputError("Video exceeds the 300-second demo limit. Export a shorter segment first.")
        return VideoInfo(width=width, height=height, fps=fps, frame_count=int(count), duration_s=duration)
    finally:
        capture.release()


def open_at_frame(path: Path, frame_index: int):
    """Decode forward to the exact requested frame; avoid imprecise keyframe seeking."""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise InputError("Cannot open the video.")
    for _ in range(frame_index):
        if not capture.grab():
            capture.release()
            raise InputError("Selection frame is beyond the decodable video.")
    return capture
