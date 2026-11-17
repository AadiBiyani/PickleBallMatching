"""Shared frame extraction: sample a video at a fixed rate and resize to one resolution.

Every analyzer receives the same JPEG bytes, so differences in how providers handle raw
video stay out of the comparison. Frames are read sequentially (no seeking), which is
reliable across codecs. OpenCV applies the container's rotation metadata (iPhone
portrait video) by default.

Deliberately does not detect players, the court, or anything else in the image.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

DEFAULT_FPS = 1.0
DEFAULT_LONG_SIDE_PX = 960
JPEG_QUALITY = 90


@dataclass(frozen=True)
class Frame:
    index: int
    time_s: float
    width_px: int
    height_px: int
    jpeg: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.jpeg).hexdigest()

    def decode(self) -> np.ndarray:
        return cv2.imdecode(np.frombuffer(self.jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)


def resize_long_side(image: np.ndarray, long_side_px: int) -> np.ndarray:
    h, w = image.shape[:2]
    scale = long_side_px / max(h, w)
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
    return cv2.resize(image, size, interpolation=interp)


def extract_frames(
    video_path: str | Path,
    fps: float = DEFAULT_FPS,
    long_side_px: int = DEFAULT_LONG_SIDE_PX,
) -> list[Frame]:
    """Sample frames at `fps` (k / fps seconds, k = 0, 1, ...), resized so the long side is
    `long_side_px`. Raises ValueError for an unreadable video or bad settings."""
    if fps <= 0:
        raise ValueError(f"fps must be > 0, got {fps}")
    if long_side_px < 64:
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
        k = 0
        target = 0  # source frame index of the k-th sample
        i = 0
        while True:
            ok, image = cap.read()
            if not ok:
                break
            if i == target:
                small = resize_long_side(image, long_side_px)
                ok_enc, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                if not ok_enc:
                    raise ValueError(f"JPEG encoding failed at frame {i}")
                h, w = small.shape[:2]
                frames.append(Frame(k, round(i / src_fps, 3), w, h, buf.tobytes()))
                k += 1
                target = round(k * src_fps / fps)
                # Sampling faster than the source rate would repeat frames; skip ahead.
                while target <= i:
                    k += 1
                    target = round(k * src_fps / fps)
            i += 1
    finally:
        cap.release()

    if not frames:
        raise ValueError(f"no frames could be read from: {path}")
    # Re-number sequentially in case sampling skipped duplicate source frames.
    return [Frame(n, f.time_s, f.width_px, f.height_px, f.jpeg) for n, f in enumerate(frames)]
