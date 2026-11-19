import csv
import json
from collections import deque

import numpy as np
import pytest
from conftest import BOX, FakeBackend
from pydantic import ValidationError

from player_tracking.contracts import (
    BoundingBox,
    Detection,
    FrameRecord,
    InputError,
    Selection,
    TrackingConfig,
)
from player_tracking.exports import sample_validation_rows
from player_tracking.selection import position_record, select_track
from player_tracking.tracking import annotate_frame, assign_timestamps, preview_video, run_tracking
from player_tracking.video import inspect_video


def person(track_id=7, left=(100, 200, 0.9), right=(140, 200, 0.9), confidence=0.8):
    return Detection(BoundingBox(x1=50, y1=30, x2=180, y2=220), confidence, track_id, left, right)


def test_midpoint_reference():
    row = position_record(0, 7, [person()], 640, 480, 0.5)
    assert (row.image_x_px, row.image_y_px) == (120, 200)
    assert row.status == "ok"
    assert row.point_source == "ankle_midpoint"


@pytest.mark.parametrize(
    "ankle",
    [None, (100, 200, 0.49), (640, 200, 1), (-1, 200, 1), (100, float("nan"), 1), (100, 200, float("nan"))],
)
def test_bad_ankles_preserve_row_with_null(ankle):
    row = position_record(12, 7, [person(left=ankle)], 640, 480, 0.5)
    assert row.frame_index == 12
    assert row.status == "keypoints_unreliable"
    assert row.reason
    assert row.bbox is not None
    assert row.image_x_px is None and row.image_y_px is None
    json.dumps(row.model_dump(), allow_nan=False)


def test_nonselected_high_confidence_person_does_not_replace_target():
    row = position_record(0, 7, [person(9, confidence=0.99), person(7, confidence=0.6)], 640, 480, 0.5)
    assert row.selected_track_id == 7 and row.status == "ok"
    lost = position_record(1, 7, [person(9, confidence=0.99)], 640, 480, 0.5)
    assert lost.status == "target_not_detected" and lost.bbox is None
    assert lost.image_x_px is None


def test_new_id_is_not_automatically_reidentified():
    row = position_record(1, 7, [person(8)], 640, 480, 0.5)
    assert row.status == "target_not_detected"


def test_loss_and_unreliable_positions_break_trail():
    trail = deque(maxlen=60)
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    ok = position_record(0, 7, [person()], 640, 480, 0.5)
    for missing in (
        position_record(1, 7, [], 640, 480, 0.5),
        position_record(1, 7, [person(left=None)], 640, 480, 0.5),
    ):
        annotate_frame(image, [person()], [ok], {"player_1": trail})
        assert len(trail) == 1
        annotate_frame(image, [], [missing], {"player_1": trail})
        assert len(trail) == 0
        annotate_frame(image, [person()], [ok], {"player_1": trail})
        assert len(trail) == 1
        trail.clear()


def test_selection_requires_unambiguous_overlap():
    assert select_track(person().bbox, [person()], TrackingConfig()) == 7
    with pytest.raises(InputError, match="ambiguously"):
        select_track(person().bbox, [person(7), person(8)], TrackingConfig())
    with pytest.raises(InputError, match="overlaps"):
        select_track(BOX, [person()], TrackingConfig())


@pytest.mark.parametrize(
    "values",
    [
        {"x1": 10, "y1": 0, "x2": 5, "y2": 30},
        {"x1": -1, "y1": 0, "x2": 5, "y2": 30},
        {"x1": float("nan"), "y1": 0, "x2": 5, "y2": 30},
    ],
)
def test_invalid_boxes(values):
    with pytest.raises(ValidationError):
        BoundingBox(**values)


@pytest.mark.parametrize("fps", [0, -1, float("nan"), float("inf")])
def test_invalid_fps_rejected(tiny_video, monkeypatch, fps):
    from player_tracking import video

    class InvalidMetadataCapture:
        def isOpened(self):
            return True

        def get(self, key):
            return fps if key == video.cv2.CAP_PROP_FPS else 6

        def release(self):
            pass

    monkeypatch.setattr(video.cv2, "VideoCapture", lambda _: InvalidMetadataCapture())
    with pytest.raises(InputError, match="FPS"):
        inspect_video(tiny_video)


def test_timestamps_use_decoder_or_documented_cfr_fallback():
    rows = [
        FrameRecord(frame_index=i, timestamp_s=0, selected_track_id=7, status="target_not_detected")
        for i in range(3)
    ]
    source, reason = assign_timestamps(rows, [0.0, 0.05, 0.12], 30)
    assert source == "opencv_pos_msec" and reason is None
    assert [r.timestamp_s for r in rows] == [0.0, 0.05, 0.12]
    source, reason = assign_timestamps(rows, [0, 0, 0], 30)
    assert source == "frame_index_over_fps" and reason
    assert [r.timestamp_s for r in rows] == [0, 1 / 30, 2 / 30]


def test_independent_runs_create_fresh_tracker_and_preserve_all_rows(tiny_video, tmp_path):
    FakeBackend.instances.clear()
    selection = Selection(bbox=BOX)
    for _ in range(2):
        result = run_tracking(
            tiny_video,
            selection,
            TrackingConfig(max_frames=3),
            tmp_path / "runs",
            backend_factory=FakeBackend,
        )
        output = result["output_dir"]
        from pathlib import Path

        data = json.loads((Path(output) / "positions.json").read_text())
        assert data["metadata"]["complete"] is True
        assert data["metadata"]["processing_stride"] == 1
        assert len(data["frames"]) == 3
        assert data["frames"][0]["image_x_px"] == 16
    assert len(FakeBackend.instances) == 2
    assert [item.calls for item in FakeBackend.instances] == [3, 3]


def test_exports_keep_missing_rows_and_reference_metadata(tiny_video, tmp_path):
    class GappyBackend(FakeBackend):
        def detect(self, frame, *, track):
            detections = super().detect(frame, track=track)
            return detections if self.calls != 2 else []

    result = run_tracking(
        tiny_video,
        Selection(bbox=BOX),
        TrackingConfig(max_frames=3),
        tmp_path / "runs",
        backend_factory=GappyBackend,
    )
    from pathlib import Path

    output = Path(result["output_dir"])
    data = json.loads((output / "positions.json").read_text())
    csv_rows = list(csv.DictReader((output / "positions.csv").open()))
    assert len(csv_rows) == len(data["frames"]) == 3
    assert data["frames"][1]["image_x_px"] is None
    assert csv_rows[1]["image_x_px"] == "" and csv_rows[1]["bbox_x1"] == ""
    assert csv_rows[1]["point_source"] == "ankle_midpoint"
    assert float(csv_rows[1]["timestamp_s"]) == data["frames"][1]["timestamp_s"]
    assert result["metadata"]["missing_counts"]["target_not_detected"] == 1
    assert len(list((output / "frames").glob("*.jpg"))) == 3


def test_processing_failure_exports_explicit_partial_run(tiny_video, tmp_path):
    class FailingBackend(FakeBackend):
        def detect(self, frame, *, track):
            if self.calls == 1:
                raise RuntimeError("Deliberate processing failure")
            return super().detect(frame, track=track)

    with pytest.raises(RuntimeError, match="Deliberate"):
        run_tracking(
            tiny_video,
            Selection(bbox=BOX),
            TrackingConfig(max_frames=3),
            tmp_path / "runs",
            run_id="partial",
            backend_factory=FailingBackend,
        )
    data = json.loads((tmp_path / "runs/partial/positions.json").read_text())
    assert data["metadata"]["complete"] is False
    assert len(data["frames"]) == 1
    assert "Deliberate" in data["metadata"]["error"]


def test_preview_uses_original_decoded_coordinates(tiny_video, tmp_path):
    data = preview_video(tiny_video, tmp_path / "preview", backend_factory=FakeBackend)
    assert data["source"]["width"] == 64 and data["source"]["height"] == 48
    assert data["candidates"][0]["bbox"] == BOX.model_dump()
    # Preview rendering may scale the image; its data contract never changes coordinate units.
    assert data["coordinate_system"] == "original_image_pixels"


def test_invalid_video_and_out_of_image_selection(tiny_video, tmp_path):
    path = tmp_path / "invalid.mp4"
    path.write_bytes(b"not a video")
    with pytest.raises(InputError, match="decode"):
        inspect_video(path)
    with pytest.raises(InputError, match="inside"):
        run_tracking(
            tiny_video,
            Selection(bbox=person().bbox),
            TrackingConfig(),
            tmp_path / "runs",
            backend_factory=FakeBackend,
        )


def test_adapter_retains_missing_predictions_and_unmatched_requests():
    rows = [FrameRecord(frame_index=0, timestamp_s=0, selected_track_id=7, status="target_not_detected")]
    result = sample_validation_rows(rows, [0, 10], 0.01)
    assert result[0]["record"]["image_x_px"] is None
    assert result[1] == {"requested_timestamp_s": 10, "matched": False, "record": None}
