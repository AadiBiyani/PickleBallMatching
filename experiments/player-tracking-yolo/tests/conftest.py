from pathlib import Path

import cv2
import numpy as np
import pytest

from player_tracking.contracts import BoundingBox, Detection


@pytest.fixture
def tiny_video(tmp_path: Path):
    """Blank encoded frames for software tests only, never model-accuracy evidence."""
    path = tmp_path / "software-test.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    assert writer.isOpened()
    for value in range(6):
        writer.write(np.full((48, 64, 3), value * 20, dtype=np.uint8))
    writer.release()
    return path


BOX = BoundingBox(x1=4, y1=4, x2=40, y2=44)


class FakeBackend:
    instances: list = []  # noqa: RUF012 -- shared test-only construction log
    load_seconds = 0.0

    def __init__(self, config):
        self.config = config
        self.calls = 0
        self.instances.append(self)

    def detect(self, frame, *, track):
        assert frame.shape[:2] == (48, 64)
        self.calls += 1
        return [Detection(BOX, 0.8, 7 if track else None, (12, 40, 0.9), (20, 40, 0.9))]
