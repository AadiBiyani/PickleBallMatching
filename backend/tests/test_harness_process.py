"""Harness-process models, run against a stand-in `harness.run` CLI.

The stand-in mimics the real CLI's contract (experiments/vlm-harness/harness/run.py):
it writes runs/<name>/results.csv and summary.json under --output, prints
"wrote <dir>", and on failure prints "error: <reason>" to stderr and exits 2.
No OpenCV, MediaPipe, or YOLO is needed.
"""

import json
import sys
import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import clips, pipeline
from app.main import app
from app.store import store
from app.vision import MODELS, harness_process
from app.vision.harness_process import HarnessError, HarnessProcessModel

FAKE_RUN = textwrap.dedent(
    """
    import argparse, csv, json, sys
    from pathlib import Path

    p = argparse.ArgumentParser()
    p.add_argument("clip"); p.add_argument("--analyzer"); p.add_argument("--corners")
    p.add_argument("--fps"); p.add_argument("--output"); p.add_argument("--positions")
    p.add_argument("--player-id"); p.add_argument("--start-frame"); p.add_argument("--stop-frame")
    a = p.parse_args()
    if "fail" in a.analyzer:
        print("error: no corners saved for clip.mp4", file=sys.stderr); sys.exit(2)
    run = Path(a.output) / "runs" / "20261118-000000_clip_fake_abcd1234"
    run.mkdir(parents=True)
    cols = ["clip","analyzer","model_id","frame_index","source_frame_index","time_s",
            "x_px","y_px","x_ft","y_ft","zone","label_zone","label_x_ft","label_y_ft","position_error_ft"]
    with (run / "results.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=cols); w.writeheader()
        w.writerow(dict.fromkeys(cols, "") | {"frame_index": "0", "source_frame_index": "0", "time_s": "0.000",
                   "x_px": "960.000", "y_px": "900.000", "x_ft": "15.000", "y_ft": "40.000", "zone": "backcourt_right"})
        w.writerow(dict.fromkeys(cols, "") | {"frame_index": "1", "source_frame_index": "15", "time_s": "0.500",
                   "zone": "not_visible"})
    (run / "summary.json").write_text(json.dumps({"frame_size_px": [1920, 1080], "argv": sys.argv[1:]}))
    print("zone accuracy n/a"); print(f"wrote {run}")
    """
)


@pytest.fixture()
def fake_harness(tmp_path, monkeypatch):
    harness_dir = tmp_path / "vlm-harness"
    (harness_dir / "harness").mkdir(parents=True)
    (harness_dir / "harness" / "__init__.py").write_text("")
    (harness_dir / "harness" / "run.py").write_text(FAKE_RUN)
    monkeypatch.setattr(harness_process, "HARNESS_DIR", harness_dir)
    monkeypatch.setattr(harness_process, "RUNS_DIR", tmp_path / "harness_runs")
    monkeypatch.setattr(pipeline, "RUNS_DIR", tmp_path / "harness_runs")
    return harness_dir


def _model(analyzer="fake", **kw):
    return HarnessProcessModel(
        id="fake-harness", analyzer=analyzer, name="Fake harness model", owner="test",
        description="d", python=Path(sys.executable), sample_fps=2.0, **kw,
    )  # fmt: skip


def test_reads_results_csv_into_feet_rows(fake_harness, tmp_path):
    run = _model().analyze_clip(tmp_path / "clip.mp4", tmp_path / "corners.json", "s1")
    assert [r.zone for r in run.rows] == ["backcourt_right", "not_visible"]
    assert (run.rows[0].x_ft, run.rows[0].y_ft, run.rows[0].x_px) == (15.0, 40.0, 960.0)
    assert run.rows[1].x_ft is None and run.rows[1].source_frame_index == 15
    assert run.frame_size_px == (1920, 1080)
    argv = json.loads((run.run_dir / "summary.json").read_text())["argv"]
    assert argv[argv.index("--analyzer") + 1] == "fake" and argv[argv.index("--fps") + 1] == "2"


def test_harness_error_message_is_surfaced(fake_harness, tmp_path):
    with pytest.raises(HarnessError, match="no corners saved for clip.mp4"):
        _model("fail").analyze_clip(tmp_path / "clip.mp4", tmp_path / "corners.json", "s2")


def test_missing_environment_makes_the_model_unavailable(fake_harness, tmp_path):
    model = HarnessProcessModel(
        id="m", analyzer="mediapipe", name="M", owner="o", description="d",
        python=tmp_path / "no-venv" / "python.exe", sample_fps=1.0,
    )  # fmt: skip
    assert "environment is not set up" in model.unavailable_reason()
    assert model.info().available is False


def test_export_backed_model_needs_a_registered_export(fake_harness, tmp_path):
    model = _model(clip_args=lambda clip_id: ["--positions", "p.json"] if clip_id == "has.mp4" else None)
    has = clips.Clip(id="has.mp4", name="has", has_corners=True)
    lacks = clips.Clip(id="lacks.mp4", name="lacks", has_corners=True)
    assert model.clip_problem(has, tmp_path / "has.mp4") is None
    assert "No precomputed" in model.clip_problem(lacks, tmp_path / "lacks.mp4")
    run = model.analyze_clip(tmp_path / "has.mp4", tmp_path / "corners.json", "s3")
    argv = json.loads((run.run_dir / "summary.json").read_text())["argv"]
    assert argv[-2:] == ["--positions", "p.json"]


def test_yolo_args_read_the_exports_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(clips, "CLIP_DIR", tmp_path)
    monkeypatch.setattr(clips, "EXPORTS_PATH", tmp_path / "exports.json")
    (tmp_path / "exports.json").write_text(json.dumps(
        {"yolo": {"clip.mp4": {"positions": "clip.positions.json", "player_id": "player_2",
                               "start_frame": 600, "stop_frame": 890}}}
    ))  # fmt: skip
    assert clips.yolo_args("clip.mp4") is None  # export file not present yet
    (tmp_path / "clip.positions.json").write_text("{}")
    args = clips.yolo_args("clip.mp4")
    assert args[args.index("--player-id") + 1] == "player_2"
    assert args[-4:] == ["--start-frame", "600", "--stop-frame", "890"]


def test_upload_runs_the_harness_end_to_end(fake_harness, tmp_path, monkeypatch):
    """Clip with corners + harness model -> completed session whose track is the harness rows."""
    monkeypatch.setattr(pipeline, "STEP_DELAY_S", 0)
    clip_dir = tmp_path / "clips"
    clip_dir.mkdir()
    (clip_dir / "clip.mp4").write_bytes(b"not decoded by the stand-in")
    (clip_dir / "corners.json").write_text(json.dumps({"videos": {"clip.mp4": {}}}))
    monkeypatch.setattr(clips, "CLIP_DIR", clip_dir)
    monkeypatch.setattr(clips, "CORNERS_PATH", clip_dir / "corners.json")
    monkeypatch.setitem(MODELS, "fake-harness", _model())
    store.reset()
    client = TestClient(app)
    now = "2026-11-18T10:00:00Z"
    sid = client.post("/api/sessions", json={
        "drill_id": "lateral-prescribed", "drill_version": "1.0", "feed_method": "human_feeder",
        "capture_started_at": now, "capture_ended_at": now,
    }).json()["id"]  # fmt: skip
    r = client.post(f"/api/sessions/{sid}/upload", json={"model_id": "fake-harness", "clip_id": "clip.mp4"})
    assert r.status_code == 200, r.text
    assert client.get(f"/api/sessions/{sid}").json()["status"] == "completed"
    track = client.get(f"/api/sessions/{sid}/results").json()["track"]
    assert track["frames"] == 2 and track["missing_frames"] == 1
    assert track["frame_size_px"] == [1920, 1080] and track["harness_run"].startswith("harness_runs/")
    assert track["processing_s"] is not None
    assert client.get(f"/api/sessions/{sid}/track").json()[0]["zone"] == "backcourt_right"


def test_simulated_model_never_decodes_a_real_clip(tmp_path, monkeypatch):
    """The simulated tracker reads no pixels, so a real clip must not reach the video decoder."""
    monkeypatch.setattr(pipeline, "extract_frames", lambda *a, **k: pytest.fail("decoded a real clip"))
    from app.drills import get_drill

    frames = pipeline.sample_clip(MODELS["simulated"], tmp_path / "real.mp4", get_drill("lateral-prescribed"))
    assert len(frames.frames) == 600


def test_unavailable_model_is_refused_at_upload():
    store.reset()
    client = TestClient(app)
    now = "2026-11-18T10:00:00Z"
    sid = client.post("/api/sessions", json={
        "drill_id": "lateral-prescribed", "drill_version": "1.0", "feed_method": "human_feeder",
        "capture_started_at": now, "capture_ended_at": now,
    }).json()["id"]  # fmt: skip
    model = MODELS["yolo"]
    if model.unavailable_reason() is None:
        pytest.skip("the YOLO environment exists on this machine")
    r = client.post(f"/api/sessions/{sid}/upload", json={"model_id": "yolo", "clip_id": "synthetic"})
    assert r.status_code == 400 and "unavailable" in r.json()["detail"]
