"""Exercise the actual worker-to-harness path with fabricated detections."""

import json

import pytest
import worker

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")


@pytest.fixture
def worker_request(tmp_path):
    video = tmp_path / "fixture.avi"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (200, 440))
    assert writer.isOpened()
    for _ in range(4):
        writer.write(np.zeros((440, 200, 3), dtype=np.uint8))
    writer.release()
    return {
        "operation": "analyze",
        "kind": "mediapipe",
        "video": str(video),
        "analysis": {
            "start_frame": 1,
            "max_frames": 3,
            "sample_fps": 10,
            "selections": [],
            "calibration": {
                "width": 200,
                "height": 440,
                "corners_px": [[0, 0], [200, 0], [200, 440], [0, 440]],
            },
        },
    }


def test_worker_uses_shared_geometry_and_retains_missing_samples(worker_request, tmp_path, monkeypatch):
    from harness.analyzers import base
    from harness.contract import LocatedPoint

    class Analyzer:
        kind, model_id = "mediapipe", "fabricated-test-points"
        closed = False

        def locate(self, frames):
            return [
                LocatedPoint(frame.index, None, None)
                if frame.source_frame_index == 2
                else LocatedPoint(frame.index, 50, 250)
                for frame in frames
            ]

        def close(self):
            self.closed = True

    analyzer = Analyzer()
    monkeypatch.setattr(base, "create_analyzer", lambda *a, **kw: analyzer)
    monkeypatch.setattr(worker.importlib.metadata, "version", lambda _: "fixture")
    result = worker.analyze(worker_request, tmp_path)
    assert analyzer.closed
    assert [r["source_frame_index"] for r in result["rows"]] == [1, 2, 3]
    assert [r["time_s"] for r in result["rows"]] == [0.1, 0.2, 0.3]
    assert result["rows"][0]["x_ft"] == pytest.approx(5)
    assert result["rows"][0]["y_ft"] == pytest.approx(25)
    assert result["rows"][0]["zone"] == "kitchen_left"
    assert result["rows"][1]["zone"] == "not_visible" and result["rows"][1]["x_ft"] is None
    assert result["summary"]["missing_frames"] == 1
    provenance = json.loads((tmp_path / "provenance.json").read_text())
    assert not provenance["accuracy_evaluated"] and provenance["attempts_source"] == "unavailable"
    assert provenance["analysis"]["calibration"] == worker_request["analysis"]["calibration"]


def test_worker_refuses_dimensions_for_another_clip(worker_request):
    worker_request["analysis"]["calibration"]["width"] = 300
    with pytest.raises(ValueError, match="dimensions"):
        worker.validate(worker_request, {"width": 200, "height": 440, "frame_count": 4})
