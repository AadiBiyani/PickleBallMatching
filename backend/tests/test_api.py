import pytest
from fastapi.testclient import TestClient

from app import pipeline
from app.main import app
from app.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def fast_pipeline(monkeypatch):
    monkeypatch.setattr(pipeline, "STEP_DELAY_S", 0)
    store.reset()


def _create(scenario="normal", drill_id="lateral-prescribed"):
    r = client.post(
        "/api/sessions",
        json={
            "drill_id": drill_id,
            "drill_version": "1.0",
            "feed_method": "ball_machine",
            "capture_started_at": "2026-11-18T10:00:00Z",
            "capture_ended_at": "2026-11-18T10:01:00Z",
            "scenario": scenario,
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


def _upload(sid):
    return client.post(f"/api/sessions/{sid}/upload", json={"model_id": "simulated", "clip_id": "synthetic"})


@pytest.mark.parametrize("drill_id", ["lateral-prescribed", "lateral-reactive", "fh-bh-targets"])
def test_happy_path_completes_and_publishes(drill_id):
    sid = _create(drill_id=drill_id)
    assert _upload(sid).status_code == 200
    assert client.get(f"/api/sessions/{sid}").json()["status"] == "completed"
    results = client.get(f"/api/sessions/{sid}/results").json()
    assert results["sufficient"] is True
    assert results["track"]["model_id"] == "simulated"
    profile = client.post(f"/api/sessions/{sid}/publish").json()
    assert profile["version"] == 1
    assert client.post(f"/api/sessions/{sid}/publish").json()["version"] == 1  # idempotent


@pytest.mark.parametrize("scenario", ["normal", "upload_error"])
@pytest.mark.parametrize("drill_id", ["lateral-prescribed", "lateral-reactive", "fh-bh-targets"])
def test_only_insufficient_scenario_can_be_insufficient(scenario, drill_id):
    # Seeds vary per session ID, so run many sessions to catch unlucky draws.
    for _ in range(40):
        sid = _create(scenario, drill_id)
        _upload(sid)
        if scenario == "upload_error":
            _upload(sid)
        assert client.get(f"/api/sessions/{sid}/results").json()["sufficient"] is True


def test_upload_error_then_retry_uses_same_session():
    sid = _create("upload_error")
    assert _upload(sid).status_code == 503
    assert client.get(f"/api/sessions/{sid}").json()["status"] == "awaiting_upload"
    assert _upload(sid).status_code == 200
    assert len(store.sessions) == 1
    # A duplicate upload after success does not queue a second analysis (NFR-04).
    assert _upload(sid).json()["status"] == "completed"


def test_processing_error_is_explicit_failure():
    sid = _create("processing_error")
    _upload(sid)
    s = client.get(f"/api/sessions/{sid}").json()
    assert s["status"] == "failed" and s["error"]


def test_insufficient_data_cannot_publish():
    sid = _create("insufficient_data")
    _upload(sid)
    results = client.get(f"/api/sessions/{sid}/results").json()
    assert results["sufficient"] is False
    assert client.post(f"/api/sessions/{sid}/publish").status_code == 409
    assert client.get("/api/profile").json() is None


def test_debug_states():
    for state in ["awaiting_upload", "completed", "failed", "published"]:
        assert client.post("/api/debug/sessions", json={"state": state}).status_code == 201
    assert client.get("/api/profile").json()["version"] == 1
