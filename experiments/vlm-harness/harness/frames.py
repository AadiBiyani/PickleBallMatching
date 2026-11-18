"""Sample frames from a test video.

The default keeps the video's own resolution. Pass long_side_px only when every
model should see a smaller copy of the same frame. The corner registry is then
scaled to that copy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


DEFAULT_FPS = 1.0


@dataclass(frozen=True)
class Frame:
    index: int
    time_s: float
    width_px: int
    height_px: int
    image: np.ndarray


@dataclass(frozen=True)
class ClipFrames:
    native_width: int
    native_height: int
    frames: list[Frame]


def resize_long_side(image: np.ndarray, long_side_px: int) -> np.ndarray:
    height, width = image.shape[:2]
    scale = long_side_px / max(height, width)
    if abs(scale - 1.0) < 1e-9:
        return image
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    return cv2.resize(image, size, interpolation=interp)


def extract_frames(
    video_path: str | Path,
    fps: float = DEFAULT_FPS,
    long_side_px: int | None = None,
) -> ClipFrames:
    """Sample at `fps`, starting at the first frame. Raises ValueError on a bad clip."""
    if fps <= 0:
        raise ValueError(f"fps must be > 0, got {fps}")
    if long_side_px is not None and long_side_px < 64:
        raise ValueError(f"long side must be >= 64 px, got {long_side_px}")
    path = Path(video_path)
    if not path.is_file():
        raise ValueError(f"video not found: {path}")

    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError(f"OpenCV could not open video: {path}")
        src_fps = cap.get(cv2.CAP_PROP_FPS)
        if not src_fps or src_fps <= 0 or np.isnan(src_fps):
            raise ValueError(f"video reports no frame rate: {path}")

        frames: list[Frame] = []
        native_width = native_height = None
        k = 0
        target = 0
        index = 0
        while True:
            ok, image = cap.read()
            if not ok:
                break
            if native_width is None:
                native_height, native_width = image.shape[:2]
            if index == target:
                shown = image if long_side_px is None else resize_long_side(image, long_side_px)
                height, width = shown.shape[:2]
                frames.append(Frame(k, round(index / src_fps, 3), width, height, shown))
                k += 1
                target = round(k * src_fps / fps)
                while target <= index:
                    k += 1
                    target = round(k * src_fps / fps)
            index += 1
    finally:
        cap.release()

    if not frames or native_width is None or native_height is None:
        raise ValueError(f"no frames could be read from: {path}")
    return ClipFrames(native_width, native_height, frames)
