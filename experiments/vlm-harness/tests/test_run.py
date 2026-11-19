"""End-to-end scoring with the fake analyzer. No model weights and no window."""

import csv
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "player-tracking"))

import perspective as court

from harness.analyzers.base import create_analyzer
from harness.analyzers.fake import FakeAnalyzer
from harness.run import RESULT_COLUMNS, run_harness

WIDTH = 640
HEIGHT = 480
CORNERS = [[80.0, 40.0], [560.0, 40.0], [560.0, 440.0], [80.0, 440.0]]


def _write_clip(path):
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (WIDTH, HEIGHT))
    assert writer.isOpened()
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for _ in range(2):
        writer.write(frame)
    writer.release()


def _registry(path):
    import mark_corners

    saved = mark_corners.upsert_clip(
        mark_corners.empty_registry(), "clip.mp4", WIDTH, HEIGHT, CORNERS,
    )
    mark_corners.save_registry(path, saved)


def _court_pixel():
    homography = court.compute_homography(CORNERS)
    return court.apply_homography(np.linalg.inv(homography), [[5.0, 25.0]])[0]


def test_null_point_stays_blank_and_the_next_frame_is_scored(tmp_path):
    video = tmp_path / "clip.mp4"
    _write_clip(str(video))
    corners = tmp_path / "corners.json"
    _registry(corners)
    labels = tmp_path / "clip.labels.csv"
    labels.write_text(
        "time_s,zone,x_ft,y_ft\n"
        "0.0,kitchen_left,5.0,25.0\n"
        "0.1,kitchen_left,5.0,25.0\n"
    )
    pixel = _court_pixel()
    analyzer = FakeAnalyzer(points={0: None, 1: (float(pixel[0]), float(pixel[1]))})

    outcome = run_harness(
        video, analyzer, corners, labels_path=labels, fps=10.0, output_root=tmp_path / "out",
    )

    assert [row["zone"] for row in outcome.rows] == ["not_visible", "kitchen_left"]
    assert outcome.rows[0]["x_ft"] is None
    assert outcome.rows[0]["y_ft"] is None
    assert abs(outcome.rows[1]["x_ft"] - 5.0) < 0.05
    assert abs(outcome.rows[1]["y_ft"] - 25.0) < 0.05
    assert outcome.score.zone_accuracy == 0.5
    assert outcome.score.n_zone_labeled == 2
    assert outcome.score.n_position_missing == 1
    assert outcome.score.n_position_scored == 1
    assert outcome.score.position_error_mean_ft < 0.05
    assert outcome.score.position_error_max_ft < 0.05

    with (outcome.run_dir / "results.csv").open(encoding="utf-8") as handle:
        written = list(csv.DictReader(handle))
    assert list(written[0].keys()) == RESULT_COLUMNS
    assert written[0]["x_ft"] == ""
    assert written[0]["zone"] == "not_visible"
    assert written[1]["zone"] == "kitchen_left"


def test_unknown_analyzer_is_refused():
    with pytest.raises(ValueError, match="unknown analyzer"):
        create_analyzer("unknown-model")
