"""Demo clip and browser-playable previews (the camera screens' playback)."""

import pytest
from fastapi.testclient import TestClient

from app import clips
from app.main import app

client = TestClient(app)


@pytest.fixture()
def clip_dir(tmp_path, monkeypatch):
    (tmp_path / "demo.mp4").write_bytes(b"analysis clip bytes")
    (tmp_path / "demo.preview.mp4").write_bytes(bytes(range(256)) * 4)  # 1024 bytes
    (tmp_path / "other.mp4").write_bytes(b"no preview")
    monkeypatch.setattr(clips, "CLIP_DIR", tmp_path)
    monkeypatch.setattr(clips, "CORNERS_PATH", tmp_path / "corners.json")
    monkeypatch.setattr(clips, "EXPORTS_PATH", tmp_path / "exports.json")
    monkeypatch.setattr(clips, "DEMO_CLIP", "demo.mp4")
    return tmp_path


def test_previews_are_not_analysis_clips(clip_dir):
    listed = {c["id"]: c for c in client.get("/api/clips").json()}
    assert "demo.preview.mp4" not in listed
    assert listed["demo.mp4"]["preview_url"] == "/api/clips/demo.mp4/preview"
    assert listed["other.mp4"]["preview_url"] is None


def test_demo_clip(clip_dir, monkeypatch):
    assert client.get("/api/demo-clip").json()["id"] == "demo.mp4"
    monkeypatch.setattr(clips, "DEMO_CLIP", "missing.mp4")
    assert client.get("/api/demo-clip").json() is None


def test_preview_streams_with_range_requests(clip_dir):
    full = client.get("/api/clips/demo.mp4/preview")
    assert full.status_code == 200 and full.headers["content-type"] == "video/mp4"
    assert len(full.content) == 1024
    part = client.get("/api/clips/demo.mp4/preview", headers={"Range": "bytes=100-199"})
    assert part.status_code == 206 and part.content == full.content[100:200]


@pytest.mark.parametrize("clip_id", ["other.mp4", "nope.mp4", "..%2Fsecret.mp4", "demo.preview.mp4"])
def test_preview_404s(clip_dir, clip_id):
    assert client.get(f"/api/clips/{clip_id}/preview").status_code == 404
