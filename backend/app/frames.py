"""Frames handed to vision models, mirroring the harness's `harness/frames.py`.

A `Frame` has the same fields as the harness frame, so harness analyzers can be
registered here unchanged. `image` is a BGR NumPy array for real clips and
None for the synthetic clip (only models that do not read pixels accept it).

OpenCV is imported lazily so the API runs without it; install
`requirements-vision.txt` to analyze real video.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Frame:
    index: int
    time_s: float
    width_px: int
    height_px: int
    image: Any  # numpy.ndarray (BGR) for real clips; None for synthetic frames


@dataclass(frozen=True)
class ClipFrames:
    native_width: int
    native_height: int
    frames: list[Frame]


def synthetic_frames(duration_s: float, fps: float, width: int, height: int) -> ClipFrames:
    count = max(1, int(duration_s * fps))
    return ClipFrames(width, height, [Frame(k, round(k / fps, 3), width, height, None) for k in range(count)])


def extract_frames(video_path: str | Path, fps: float) -> ClipFrames:
    """Sample at `fps` from the first frame at native size (same rule as the harness)."""
    try:
        import cv2  # noqa: PLC0415 - optional dependency
    except ImportError as exc:
        raise ValueError(
            "Analyzing real video needs OpenCV: pip install -r requirements-vision.txt"
        ) from exc
    if fps <= 0:
        raise ValueError(f"fps must be > 0, got {fps}")
    path = Path(video_path)
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError(f"OpenCV could not open video: {path.name}")
        src_fps = cap.get(cv2.CAP_PROP_FPS)
        if not src_fps or src_fps <= 0 or src_fps != src_fps:
            raise ValueError(f"video reports no frame rate: {path.name}")
        frames: list[Frame] = []
        native = None
        k = target = index = 0
        while True:
            ok, image = cap.read()
            if not ok:
                break
            if native is None:
                native = (image.shape[1], image.shape[0])
            if index == target:
                frames.append(Frame(k, round(index / src_fps, 3), image.shape[1], image.shape[0], image))
                k += 1
                target = round(k * src_fps / fps)
                while target <= index:
                    k += 1
                    target = round(k * src_fps / fps)
            index += 1
    finally:
        cap.release()
    if not frames or native is None:
        raise ValueError(f"no frames could be read from: {path.name}")
    return ClipFrames(native[0], native[1], frames)
