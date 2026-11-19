"""MediaPipe Pose Landmarker as a harness analyzer.

Still-image mode, one pose. The result is the heel contact pixel in the frame
that was shown, or no point. The harness applies the homography after this.
"""

from __future__ import annotations

import os
import sys
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path

import cv2
import numpy as np

from ..contract import LocatedPoint
from ..frames import Frame

PLAYER_TRACKING = Path(__file__).resolve().parents[3] / "player-tracking"
if str(PLAYER_TRACKING) not in sys.path:
    sys.path.insert(0, str(PLAYER_TRACKING))

import contact  # noqa: E402

MODEL_ID = "pose_landmarker_lite"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
MODEL_PATH = PLAYER_TRACKING / "models" / "pose_landmarker_lite.task"
USABLE = {contact.BOTH_HEELS, contact.SINGLE_HEEL}

Detector = Callable[[np.ndarray], contact.ContactSample]


def ensure_model(path: Path = MODEL_PATH) -> Path:
    """Download the lite pose model once. The file is gitignored."""
    if path.is_file() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    try:
        urllib.request.urlretrieve(MODEL_URL, temporary)
        os.replace(temporary, path)
    except OSError:
        if temporary.exists():
            temporary.unlink()
        raise
    return path


class PoseLandmarkerAnalyzer:
    """Heel point for each frame. MediaPipe is imported on the first real locate()."""

    kind = "mediapipe"
    is_remote = False

    def __init__(self, model: str = "", detect: Detector | None = None) -> None:
        model = (model or MODEL_ID).strip().replace("-", "_")
        if model != MODEL_ID:
            raise ValueError(f"unsupported pose model {model!r}; use {MODEL_ID}")
        self.model_id = model
        self._detect = detect
        self._landmarker = None
        self._mp = None

    def locate(self, frames: Sequence[Frame]) -> list[LocatedPoint]:
        detect = self._detect or self._detect_with_model
        located = []
        for frame in frames:
            sample = detect(frame.image)
            pixel = sample.pixel if sample.status in USABLE else None
            if pixel is None:
                located.append(LocatedPoint(frame.index, None, None))
            else:
                located.append(LocatedPoint(frame.index, float(pixel[0]), float(pixel[1])))
        return located

    def close(self) -> None:
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None

    def _detect_with_model(self, image_bgr: np.ndarray) -> contact.ContactSample:
        self._ensure_landmarker()
        rgb = np.ascontiguousarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)
        if not result.pose_landmarks:
            return contact.ContactSample(None, contact.OUT_OF_FRAME)
        height, width = image_bgr.shape[:2]
        return contact.classify_from_landmarks(result.pose_landmarks[0], width, height)

    def _ensure_landmarker(self) -> None:
        if self._landmarker is not None:
            return
        import mediapipe as mp

        model_path = ensure_model()
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_poses=1,
        )
        self._mp = mp
        self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
