import json
from pathlib import Path

import pytest
from conftest import BOX, FakeBackend
from fastapi.testclient import TestClient

from player_tracking.api import create_app
from player_tracking.contracts import BoundingBox, Detection, InputError, Selection, TrackingConfig
from player_tracking.exports import sample_validation_rows
from player_tracking.tracking import run_tracking

SECOND_BOX = BoundingBox(x1=42, y1=2, x2=62, y2=46)


class TwoPlayers(FakeBackend):
    def detect(self, frame, *, track):
        first = super().detect(frame, track=track)
        second = Detection(
            bbox=SECOND_BOX,
            confidence=0.99,
            track_id=8 if track else None,
            left_ankle=(48, 40, 0.9),
            right_ankle=(56, 40, 0.9),
        )
        return first if self.calls == 2 else [*first, second]


def test_multiple_players_keep_independent_missing_rows(tiny_video, tmp_path):
    result = run_tracking(
        tiny_video,
        [Selection(bbox=BOX), Selection(bbox=SECOND_BOX)],
        TrackingConfig(max_frames=3),
        tmp_path / "multi",
        backend_factory=TwoPlayers,
    )
    meta = result["metadata"]
    assert meta["processed_frame_count"] == 3 and meta["observation_count"] == 6
    assert meta["selected_track_ids"] == {"player_1": 7, "player_2": 8}
    assert meta["per_player_counts"]["player_1"]["ok"] == 3
    assert meta["per_player_counts"]["player_2"] == {
        "ok": 2,
        "target_not_detected": 1,
        "keypoints_unreliable": 0,
    }
    path = Path(result["output_dir"])
    rows = json.loads((path / "positions.json").read_text())["frames"]
    assert [row["timestamp_s"] for row in rows] == pytest.approx([0, 0, 0.1, 0.1, 0.2, 0.2])
    assert rows[3]["player_id"] == "player_2" and rows[3]["image_x_px"] is None
    assert rows[2]["image_x_px"] == 16 and rows[5]["image_x_px"] == 52
    manifest = json.loads((path / "manifest.json").read_text())
    assert len(manifest["frames"]) == 3
    assert manifest["frames"][1]["statuses"] == {"player_1": "ok", "player_2": "target_not_detected"}
    from player_tracking.contracts import FrameRecord

    records = [FrameRecord.model_validate(row) for row in rows]
    with pytest.raises(ValueError, match="player_id"):
        sample_validation_rows(records, [0.1], 0.01)
    sampled = sample_validation_rows(records, [0.1], 0.01, player_id="player_2")
    assert sampled[0]["record"]["status"] == "target_not_detected"


def test_duplicate_player_selection_rejected(tiny_video, tmp_path):
    with pytest.raises(InputError, match="same person"):
        run_tracking(
            tiny_video,
            [Selection(bbox=BOX), Selection(bbox=BOX)],
            TrackingConfig(),
            tmp_path / "duplicate",
            backend_factory=TwoPlayers,
        )


def test_multiple_selections_require_same_frame(tiny_video, tmp_path):
    with pytest.raises(InputError, match="same preview"):
        run_tracking(
            tiny_video,
            [Selection(bbox=BOX), Selection(frame_index=1, bbox=SECOND_BOX)],
            TrackingConfig(),
            tmp_path / "different",
            backend_factory=TwoPlayers,
        )


def test_api_rejects_empty_or_different_frame_selections(tiny_video, tmp_path):
    with TestClient(create_app(tmp_path / "api", TwoPlayers)) as client:
        video_id = client.post("/api/videos", files={"file": ("clip.avi", tiny_video.read_bytes())}).json()[
            "video_id"
        ]
        assert client.post("/api/jobs", json={"video_id": video_id, "selections": []}).status_code == 422
        selections = [
            Selection(bbox=BOX).model_dump(),
            Selection(frame_index=1, bbox=SECOND_BOX).model_dump(),
        ]
        assert (
            client.post("/api/jobs", json={"video_id": video_id, "selections": selections}).status_code == 422
        )
