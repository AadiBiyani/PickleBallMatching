"""Deterministic API/worker contracts. These fixtures do not exercise inference."""

import copy
import json
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from app import clips, tracking
from app.main import app
from app.schemas import Clip
from app.store import store
from app.vision import get_model

client = TestClient(app)


@pytest.fixture
def request_body():
    return {
        "model_id": "yolo:yolo26n-pose",
        "clip_id": "fixture.mp4",
        "analysis": {
            "start_frame": 30,
            "max_frames": 31,
            "sample_fps": 1,
            "selections": [{"x1": 20, "y1": 30, "x2": 40, "y2": 80}],
            "calibration": {
                "width": 200,
                "height": 440,
                "corners_px": [[0, 0], [200, 0], [200, 440], [0, 440]],
            },
        },
    }


@pytest.fixture
def worker_data():
    rows = []
    for sample, source in enumerate((30, 60)):
        for player in ("player_1", "player_2"):
            missing = sample == 1 and player == "player_2"
            rows.append(
                dict(
                    frame_index=sample,
                    source_frame_index=source,
                    time_s=source / 30,
                    player_id=player,
                    x_px=None if missing else 50,
                    y_px=None if missing else 250,
                    x_ft=None if missing else 5,
                    y_ft=None if missing else 25,
                    zone="not_visible" if missing else "kitchen_left",
                    status="target_not_detected" if missing else "ok",
                    reason="Selected track ID lost" if missing else None,
                    point_source="ankle_midpoint",
                )
            )
    return {
        "rows": rows,
        "summary": dict(
            kind="yolo",
            model_id="yolo26n-pose.pt",
            model_version="fixture",
            sample_fps=1,
            frame_size_px=[200, 440],
            frames=2,
            observations=4,
            missing_frames=1,
            players=["player_1", "player_2"],
            data_source="model",
            limitations=["Fabricated test observations"],
            zone_counts=dict(Counter(r["zone"] for r in rows)),
        ),
    }


@pytest.fixture
def session(monkeypatch, tmp_path):
    store.reset()
    monkeypatch.setattr(tracking, "RUNTIME", tmp_path)
    monkeypatch.setattr(
        clips, "resolve", lambda _: (Clip(id="fixture.mp4", name="Fixture"), tmp_path / "fixture.mp4")
    )
    # Availability is configuration, not model execution, in these tests.
    from app.vision import workers

    monkeypatch.setattr(workers, "interpreter", lambda _: __import__("pathlib").Path(__file__))
    response = client.post(
        "/api/sessions",
        json={
            "drill_id": "lateral-prescribed",
            "drill_version": "1.0",
            "feed_method": "human_feeder",
            "capture_started_at": "2026-11-18T10:00:00Z",
            "capture_ended_at": "2026-11-18T10:00:01Z",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_real_tracking_is_not_attempt_scoring(session, request_body, worker_data, monkeypatch):
    calls = []

    def invoke(kind, request, directory):
        calls.append((kind, request))
        directory.mkdir(parents=True)
        (directory / "track.json").write_text(json.dumps(worker_data["rows"]))
        return worker_data

    monkeypatch.setattr(tracking, "invoke", invoke)
    path = f"/api/sessions/{session}"
    assert client.post(path + "/upload", json=request_body).status_code == 200
    assert client.get(path).json()["status"] == "completed"
    results = client.get(path + "/results").json()
    assert results["attempts"] == [] and results["attempts_source"] == "unavailable"
    assert results["success_rate"] is None and not results["sufficient"]
    assert client.post(path + "/publish").status_code == 409
    rows = client.get(path + "/track").json()
    assert rows[-1]["source_frame_index"] == 60 and rows[-1]["reason"] == "Selected track ID lost"
    assert rows[-1]["x_ft"] is None
    assert client.get(path + "/artifacts/track.json").json() == worker_data["rows"]
    assert client.get(path + "/artifacts/request.json").status_code == 404
    assert client.post(path + "/upload", json=request_body).json()["status"] == "completed"
    assert len(calls) == 1  # duplicate delivery must not re-run inference
    assert calls[0][0] == "yolo" and calls[0][1]["analysis"]["start_frame"] == 30


def test_failure_retries_same_session(session, request_body, worker_data, monkeypatch):
    def fail(*args):
        raise ValueError("Unable to match selected player")

    monkeypatch.setattr(tracking, "invoke", fail)
    path = f"/api/sessions/{session}"
    client.post(path + "/upload", json=request_body)
    assert client.get(path).json()["status"] == "failed"
    assert "selected player" in client.get(path).json()["error"]
    assert client.get(path + "/track").status_code == 409
    monkeypatch.setattr(tracking, "invoke", lambda *args: worker_data)
    client.post(path + "/upload", json=request_body)
    assert client.get(path).json()["status"] == "completed"
    assert len(store.sessions) == 1


def test_mediapipe_dispatch_has_no_selected_identity(session, request_body, worker_data, monkeypatch):
    request_body["model_id"] = "mediapipe:pose-landmarker-lite"
    request_body["analysis"]["selections"] = []
    worker_data["summary"]["kind"] = "mediapipe"
    worker_data["summary"]["model_id"] = "pose_landmarker_lite"
    calls = []

    def invoke(kind, request, directory):
        calls.append((kind, request))
        return worker_data

    monkeypatch.setattr(tracking, "invoke", invoke)
    assert client.post(f"/api/sessions/{session}/upload", json=request_body).status_code == 200
    assert calls[0][0] == "mediapipe" and calls[0][1]["analysis"]["selections"] == []
    assert get_model(request_body["model_id"]).info().selection_mode == "first_pose"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.pop("analysis"),
        lambda r: r["analysis"].update(selections=[]),
        lambda r: r["analysis"].update(start_frame="30"),
        lambda r: r["analysis"].update(max_frames=1801),
        lambda r: r["analysis"].update(sample_fps=0),
        lambda r: r["analysis"]["calibration"].update(corners_px=[[0, 0]] * 4),
        lambda r: r["analysis"]["calibration"]["corners_px"].reverse(),
        lambda r: r["analysis"]["calibration"]["corners_px"].__setitem__(0, [-1, 0]),
        lambda r: r["analysis"]["selections"].append(copy.deepcopy(r["analysis"]["selections"][0])),
        lambda r: r["analysis"]["selections"][0].update(x2=1000),
        lambda r: r["analysis"]["selections"][0].update(x2=1),
        lambda r: r.update(model_id="mediapipe:pose-landmarker-lite"),
    ],
)
def test_invalid_requests_never_start_worker(session, request_body, mutate, monkeypatch):
    monkeypatch.setattr(tracking, "invoke", lambda *args: pytest.fail("invalid request reached inference"))
    mutate(request_body)
    assert client.post(f"/api/sessions/{session}/upload", json=request_body).status_code == 422
    assert client.get(f"/api/sessions/{session}").json()["status"] == "awaiting_upload"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["rows"].append(d["rows"][0]),
        lambda d: d["rows"].pop(),
        lambda d: d["rows"][0].update(source_frame_index=None),
        lambda d: d["rows"][0].update(x_ft=float("nan")),
        lambda d: d["rows"][-1].update(x_px=1),
        lambda d: d["rows"][-1].update(status="ok"),
        lambda d: d["summary"].update(observations=99),
    ],
)
def test_malformed_worker_results_are_rejected(worker_data, mutate):
    mutate(worker_data)
    with pytest.raises(ValueError):
        tracking.validated_result(worker_data)


def test_result_must_match_selected_model(worker_data):
    with pytest.raises(ValueError, match="selected model"):
        tracking.validated_result(worker_data, "mediapipe")


def test_missing_model_and_queue_capacity(session, request_body, monkeypatch):
    from app.vision import workers

    monkeypatch.setattr(workers, "interpreter", lambda _: workers.ROOT / "missing-python")
    assert not get_model(request_body["model_id"]).info().available
    assert client.post(f"/api/sessions/{session}/upload", json=request_body).status_code == 503
    monkeypatch.setattr(workers, "interpreter", lambda _: __import__("pathlib").Path(__file__))
    from threading import BoundedSemaphore

    monkeypatch.setattr(tracking, "SLOTS", BoundedSemaphore(0))
    assert client.post(f"/api/sessions/{session}/upload", json=request_body).status_code == 429
