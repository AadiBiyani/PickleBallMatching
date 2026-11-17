"""Shared test fixtures. All video here is SYNTHETIC, generated in a temp folder."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def make_synthetic_video(path: Path, seconds: float = 5.0, fps: float = 30.0, size: tuple[int, int] = (1920, 1080)) -> Path:
    """Write a SYNTHETIC MJPG .avi: a green 'court' with a moving dot and the frame number."""
    w, h = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    assert writer.isOpened(), "OpenCV could not open a VideoWriter for MJPG"
    n = int(round(seconds * fps))
    for i in range(n):
        img = np.full((h, w, 3), (60, 120, 40), dtype=np.uint8)
        cx = int(w * (0.2 + 0.6 * i / max(1, n - 1)))
        cv2.circle(img, (cx, int(h * 0.7)), max(4, h // 40), (255, 255, 255), -1)
        cv2.putText(img, f"SYNTHETIC {i}", (20, h // 8), cv2.FONT_HERSHEY_SIMPLEX, h / 600, (255, 255, 255), 2)
        writer.write(img)
    writer.release()
    return path


@pytest.fixture(scope="session")
def video_1080p(tmp_path_factory) -> Path:
    return make_synthetic_video(tmp_path_factory.mktemp("vid") / "synthetic_clip.avi")


@pytest.fixture(scope="session")
def video_small(tmp_path_factory) -> Path:
    """Small and fast: 5 s at 10 fps, 640x360 (SYNTHETIC)."""
    return make_synthetic_video(tmp_path_factory.mktemp("vids") / "synthetic_small.avi", fps=10.0, size=(640, 360))


class FakeClock:
    """Monotonic clock whose sleep advances time instantly."""

    def __init__(self) -> None:
        self.t = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()
