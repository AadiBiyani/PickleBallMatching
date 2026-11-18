import json
import threading
import time

import pytest
from conftest import BOX, FakeBackend
from fastapi.testclient import TestClient

from player_tracking.api import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "api", FakeBackend)) as instance:
        yield instance


def upload(client, tiny_video):
    response = client.post(
        "/api/videos", files={"file": ("clip.avi", tiny_video.read_bytes(), "video/x-msvideo")}
    )
    assert response.status_code == 201, response.text
    return response.json()["video_id"]


def start(client, video_id, **changes):
    if "selection" in changes:
        changes["selections"] = [changes.pop("selection")]
    body = {
        "video_id": video_id,
        "selections": [{"frame_index": 0, "bbox": BOX.model_dump()}],
        "config": {"max_frames": 3},
    }
    body.update(changes)
    return client.post("/api/jobs", json=body)


def terminal(client, job_id):
    for _ in range(200):
        result = client.get(f"/api/jobs/{job_id}").json()
        if result["status"] in {"completed", "failed"}:
            return result
        time.sleep(0.01)
    pytest.fail("Fake job did not finish within two seconds.")


def test_upload_preview_tracking_downloads(client, tiny_video):
    video_id = upload(client, tiny_video)
    preview = client.get(f"/api/videos/{video_id}/preview").json()
    assert preview["source"]["width"] == 64
    assert preview["candidates"][0]["bbox"] == BOX.model_dump()
    image = client.get(preview["image_url"])
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"
    response = start(client, video_id)
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    job = terminal(client, job_id)
    assert job["status"] == "completed" and job["metadata"]["complete"]
    assert job["metadata"]["usable_position_count"] == 3
    base = f"/api/jobs/{job_id}/artifacts/"
    positions = client.get(base + "positions.json").json()
    assert [row["timestamp_s"] for row in positions["frames"]] == pytest.approx([0, 0.1, 0.2])
    assert positions["frames"][0]["image_x_px"] == 16
    assert "ankle_midpoint" in client.get(base + "positions.csv").text
    manifest = client.get(base + "manifest.json").json()
    assert len(manifest["frames"]) == 3
    frame = client.get(f"/api/jobs/{job_id}/frames/00000002.jpg")
    assert frame.status_code == 200
    assert client.get(base + "secrets.txt").status_code == 404
    assert client.get(f"/api/jobs/{job_id}/frames/00000003.jpg").status_code == 404
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_invalid_upload_and_identifiers(client):
    response = client.post("/api/videos", files={"file": ("broken.mp4", b"not a video")})
    assert response.status_code == 422 and "decode" in response.text.lower()
    assert client.post("/api/videos", files={"file": ("text.txt", b"text")}).status_code == 422
    assert client.get("/api/jobs/no-such-job").status_code == 404
    assert client.get("/api/jobs/" + "0" * 32).status_code == 404
    assert client.get("/api/videos/" + "0" * 32 + "/preview").status_code == 404
    assert start(client, "../../outside").status_code == 422


def test_invalid_selection_and_config(client, tiny_video):
    video_id = upload(client, tiny_video)
    for selection in [
        {"frame_index": 6, "bbox": BOX.model_dump()},
        {"frame_index": 0, "bbox": {"x1": 0, "y1": 0, "x2": 100, "y2": 100}},
        {"frame_index": -1, "bbox": BOX.model_dump()},
        {"frame_index": True, "bbox": BOX.model_dump()},
        {"frame_index": 0, "bbox": {"x1": "4", "y1": 4, "x2": 40, "y2": 44}},
    ]:
        assert start(client, video_id, selection=selection).status_code == 422
    assert start(client, video_id, config={"max_frames": 0}).status_code == 422
    assert start(client, video_id, config={"device": "unknown"}).status_code == 422
    assert client.get(f"/api/videos/{video_id}/preview?frame_index=6").status_code == 422


def test_failed_job_exposes_incomplete_artifacts(tmp_path, tiny_video):
    class BrokenBackend(FakeBackend):
        def detect(self, frame, track):
            if self.calls == 1:
                raise RuntimeError("Simulated inference failure")
            return super().detect(frame, track=track)

    with TestClient(create_app(tmp_path / "broken", BrokenBackend)) as client:
        job_id = start(client, upload(client, tiny_video)).json()["job_id"]
        job = terminal(client, job_id)
        assert job["status"] == "failed" and "Simulated" in job["error"]
        assert job["processed_frames"] == 1
        assert job["metadata"]["complete"] is False
        assert client.get(f"/api/jobs/{job_id}/artifacts/manifest.json").json()["complete"] is False


def test_broken_export_still_reports_failed_job(client, tiny_video, monkeypatch):
    from player_tracking import api

    def broken_export(video, selections, config, output_root, *, run_id, **kwargs):
        directory = output_root / run_id
        directory.mkdir(parents=True)
        (directory / "run.json").write_text('{"unfinished":')
        raise OSError("Simulated export write failure")

    monkeypatch.setattr(api, "run_tracking", broken_export)
    job_id = start(client, upload(client, tiny_video)).json()["job_id"]
    job = terminal(client, job_id)
    assert job["status"] == "failed" and "export write" in job["error"]
    assert not job["artifacts_available"]


def test_worker_serializes_jobs_and_preview(tmp_path, tiny_video):
    entered, release = threading.Event(), threading.Event()

    class WaitingBackend(FakeBackend):
        def detect(self, frame, track):
            entered.set()
            assert release.wait(3), "Test did not release worker"
            return super().detect(frame, track=track)

    app = create_app(tmp_path / "serial", WaitingBackend)
    with TestClient(app) as client:
        video_id = upload(client, tiny_video)
        first = start(client, video_id).json()["job_id"]
        try:
            assert entered.wait(1)
            second = start(client, video_id).json()["job_id"]
            preview_future = app.state.service.submit(lambda: "preview work")
            assert client.get(f"/api/jobs/{first}").json()["status"] == "running"
            assert client.get(f"/api/jobs/{second}").json()["status"] == "queued"
            assert not preview_future.done()
        finally:
            release.set()
        assert terminal(client, first)["status"] == "completed"
        assert terminal(client, second)["status"] == "completed"
        assert preview_future.result(timeout=1) == "preview work"
        one = client.get(f"/api/jobs/{first}/artifacts/positions.json").json()["frames"]
        two = client.get(f"/api/jobs/{second}/artifacts/positions.json").json()["frames"]
        assert one == two


def test_limits_and_unambiguous_selection(client, tiny_video, monkeypatch):
    from player_tracking import api

    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 5)
    assert client.post("/api/videos", files={"file": ("large.mp4", b"123456")}).status_code == 413
    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 600 * 1024 * 1024)
    video_id = upload(client, tiny_video)
    bad = {"frame_index": 0, "bbox": {"x1": 50, "y1": 2, "x2": 60, "y2": 10}}
    job_id = start(client, video_id, selection=bad).json()["job_id"]
    job = terminal(client, job_id)
    assert job["status"] == "failed" and "overlap" in job["error"].lower()
    assert job["processed_frames"] == 0


def test_cli_and_api_share_same_export_values(client, tiny_video, tmp_path):
    from player_tracking.contracts import Selection, TrackingConfig
    from player_tracking.tracking import run_tracking

    result = run_tracking(
        tiny_video,
        Selection(bbox=BOX),
        TrackingConfig(max_frames=3),
        tmp_path / "cli-core",
        backend_factory=FakeBackend,
    )
    from pathlib import Path

    expected = json.loads((Path(result["output_dir"]) / "positions.json").read_text())["frames"]
    job_id = start(client, upload(client, tiny_video)).json()["job_id"]
    terminal(client, job_id)
    actual = client.get(f"/api/jobs/{job_id}/artifacts/positions.json").json()["frames"]
    assert actual == expected
