"""Pose landmarker points, with a stub in place of MediaPipe."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "player-tracking"))

import contact
from harness.analyzers.base import create_analyzer
from harness.analyzers.mediapipe_pose import PoseLandmarkerAnalyzer
from harness.frames import Frame


def _frame():
    return Frame(0, 0.0, 100, 80, np.zeros((80, 100, 3), dtype=np.uint8))


def _analyzer(left, right):
    def detect(image):
        height, width = image.shape[:2]
        return contact.classify_contact(left, right, width, height)

    return PoseLandmarkerAnalyzer(detect=detect)


def test_both_visible_heels_return_the_midpoint():
    point = _analyzer((10.0, 20.0, 0.9), (30.0, 40.0, 0.9)).locate([_frame()])[0]
    assert point.x_px == 20.0
    assert point.y_px == 30.0


def test_one_usable_heel_returns_that_heel():
    point = _analyzer((5.0, 6.0, 0.2), (15.0, 26.0, 0.8)).locate([_frame()])[0]
    assert (point.x_px, point.y_px) == (15.0, 26.0)


def test_both_heels_outside_the_image_have_no_point():
    point = _analyzer((-1.0, 10.0, 0.9), (120.0, 10.0, 0.9)).locate([_frame()])[0]
    assert point.x_px is None
    assert point.y_px is None


def test_no_pose_has_no_point():
    def detect(image):
        return contact.ContactSample(None, contact.OUT_OF_FRAME)

    point = PoseLandmarkerAnalyzer(detect=detect).locate([_frame()])[0]
    assert point.x_px is None
    assert point.y_px is None


def test_factory_does_not_load_mediapipe():
    sys.modules.pop("mediapipe", None)
    analyzer = create_analyzer("mediapipe")
    assert analyzer.kind == "mediapipe"
    assert analyzer.model_id == "pose_landmarker_lite"
    assert analyzer._landmarker is None
    assert "mediapipe" not in sys.modules
    named = create_analyzer("mediapipe:pose-landmarker-lite")
    assert named.model_id == "pose_landmarker_lite"
