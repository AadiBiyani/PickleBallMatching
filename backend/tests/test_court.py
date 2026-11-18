"""Court contract: same cases as the harness's tests/test_zones.py, plus backend projection."""

import json

import pytest

from app import clips, court, pipeline
from app.frames import Frame, synthetic_frames
from app.vision import HarnessAnalyzer, LocatedPoint
from app.vision.simulated import SimulatedModel

RECTANGLE = [(0.0, 0.0), (200.0, 0.0), (200.0, 440.0), (0.0, 440.0)]


def test_rectangle_point_lands_in_kitchen_left():
    # Harness test_zones.py: test_rectangle_point_lands_in_kitchen_left
    h = court.compute_homography(RECTANGLE)
    x_ft, y_ft = court.apply_homography(h, (50.0, 250.0))
    assert abs(x_ft - 5.0) < 1e-3
    assert abs(y_ft - 25.0) < 1e-3
    assert court.zone_from_feet(x_ft, y_ft) == "kitchen_left"


def test_zone_edges():
    # Harness test_zones.py: test_zone_edges (identical assertions)
    assert court.zone_from_feet(0.0, 22.0) == "kitchen_left"
    assert court.zone_from_feet(9.9, 28.9) == "kitchen_left"
    assert court.zone_from_feet(10.0, 25.0) == "kitchen_right"
    assert court.zone_from_feet(5.0, 29.0) == "transition_left"
    assert court.zone_from_feet(5.0, 36.5) == "backcourt_left"
    assert court.zone_from_feet(20.0, 44.0) == "backcourt_right"
    assert court.zone_from_feet(5.0, 21.9) == "out_of_court"
    assert court.zone_from_feet(-0.1, 30.0) == "out_of_court"
    assert court.zone_from_feet(5.0, 44.1) == "out_of_court"


def test_perspective_corners_map_to_court_corners():
    h = court.compute_homography(list(clips.SYNTHETIC_CORNERS))
    for px, ft in zip(clips.SYNTHETIC_CORNERS, court.COURT_CORNERS_FT):
        x, y = court.apply_homography(h, px)
        assert abs(x - ft[0]) < 1e-6 and abs(y - ft[1]) < 1e-6


@pytest.mark.parametrize(
    "corners, problem",
    [
        ([(0, 0), (5, 0), (200, 440), (0, 440)], "nearly identical"),
        ([(0, 0), (0, 440), (200, 440), (200, 0)], "reverse order"),
        ([(0, 0), (200, 440), (200, 0), (0, 440)], "non-convex"),
    ],
)
def test_validate_corners_rejects_bad_selections(corners, problem):
    assert any(problem in p for p in court.validate_corners(corners))


def test_project_points_keeps_missing_frames_and_derives_zones():
    frames = [Frame(i, i * 1.0, 200, 440, None) for i in range(3)]
    points = [LocatedPoint(0, 50.0, 250.0), LocatedPoint(1, None, None), LocatedPoint(2, 150.0, 400.0)]
    rows = pipeline.project_points(frames, points, RECTANGLE)
    assert [r.zone for r in rows] == ["kitchen_left", "not_visible", "backcourt_right"]
    assert rows[1].x_ft is None and rows[1].x_px is None
    assert rows[2].x_ft == pytest.approx(15.0) and rows[2].y_ft == pytest.approx(40.0)


def test_project_points_rejects_a_short_answer():
    frames = [Frame(i, float(i), 200, 440, None) for i in range(3)]
    with pytest.raises(ValueError, match="2 points for 3 frames"):
        pipeline.project_points(frames, [LocatedPoint(0, 1.0, 1.0), LocatedPoint(1, 1.0, 1.0)], RECTANGLE)


def test_feet_from_a_court_model_are_used_without_corners():
    frames = [Frame(i, float(i), 200, 440, None) for i in range(2)]
    points = [LocatedPoint(0, x_ft=15.0, y_ft=40.0), LocatedPoint(1)]
    rows = pipeline.project_points(frames, points, None)
    assert [r.zone for r in rows] == ["backcourt_right", "not_visible"]
    assert rows[0].x_px is None and rows[0].x_ft == 15.0


def test_feet_win_when_a_model_reports_both():
    frames = [Frame(0, 0.0, 200, 440, None)]
    rows = pipeline.project_points(frames, [LocatedPoint(0, 50.0, 250.0, 15.0, 40.0)], RECTANGLE)
    assert (rows[0].x_px, rows[0].x_ft, rows[0].zone) == (50.0, 15.0, "backcourt_right")


def test_image_points_without_corners_are_refused():
    frames = [Frame(0, 0.0, 200, 440, None)]
    with pytest.raises(court.CalibrationError, match="no saved corners"):
        pipeline.project_points(frames, [LocatedPoint(0, 50.0, 250.0)], None)


def test_simulated_points_land_in_the_backcourt():
    clip = synthetic_frames(9.0, 10.0, *clips.SYNTHETIC_SIZE)
    rows = pipeline.project_points(clip.frames, SimulatedModel().locate(clip.frames), list(clips.SYNTHETIC_CORNERS))
    seen = {r.zone for r in rows}
    assert seen <= {"backcourt_left", "backcourt_right", "not_visible"}
    assert {"backcourt_left", "backcourt_right"} <= seen


def test_harness_analyzer_registers_unchanged():
    class HarnessPoint:  # the harness's own LocatedPoint type, not ours
        def __init__(self, frame_index, x_px, y_px):
            self.frame_index, self.x_px, self.y_px = frame_index, x_px, y_px

    class FakeHarnessAnalyzer:  # shape of experiments/vlm-harness/harness/analyzers/fake.py
        kind = "fake"
        model_id = "fake"
        is_remote = False

        def locate(self, frames):
            return [HarnessPoint(f.index, f.width_px / 2.0, f.height_px / 2.0) for f in frames]

    model = HarnessAnalyzer(FakeHarnessAnalyzer(), name="Fake", owner="test", description="d")
    assert model.id == "fake:fake" and model.info().is_remote is False
    assert model.output_space == "image"  # harness analyzers report pixels until they declare feet
    rows = pipeline.project_points(
        [Frame(0, 0.0, 200, 440, None)], model.locate([Frame(0, 0.0, 200, 440, None)]), RECTANGLE
    )
    assert rows[0].zone == "kitchen_right"  # centre of the frame: x = 10 ft, y = 22 ft


def test_corner_registry_lookup(tmp_path, monkeypatch):
    registry = {
        "videos": {
            "clip.mp4": {
                "width": 1920,
                "height": 1080,
                "corner_order": list(court.CORNER_ORDER),
                "corners_px": [list(c) for c in clips.SYNTHETIC_CORNERS],
            }
        }
    }
    path = tmp_path / "corners.json"
    path.write_text(json.dumps(registry))
    monkeypatch.setattr(clips, "CORNERS_PATH", path)
    assert clips.corners_for("clip.mp4", 1920, 1080)[0] == (420.0, 180.0)
    with pytest.raises(court.CalibrationError, match="saved corners are for 1920x1080"):
        clips.corners_for("clip.mp4", 1280, 720)
    with pytest.raises(court.CalibrationError, match="No court corners saved"):
        clips.corners_for("other.mp4", 1920, 1080)
