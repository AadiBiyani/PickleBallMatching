"""Gemini analyzer with a stub client: no network, no API key, no real clip.

Covers the request shape, the response contract, pixel conversion, caching,
rate-limit handling, the consent gate, and one end-to-end harness run.
"""

import base64
import json
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "player-tracking"))

import perspective as court

from harness import run as run_module
from harness.analyzers import foot_response as contract
from harness.analyzers.base import AnalyzerRequestError, RateLimited, create_analyzer
from harness.analyzers.gemini import GeminiAnalyzer, _classify
from harness.frames import Frame
from harness.run import run_harness
from harness.throttle import QuotaExhausted

SCHEMA = contract.response_json_schema()


class StubInteractions:
    """Stands in for client.interactions. Replies in order; an Exception reply is raised."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return type("Interaction", (), {"output_text": reply})()


class APIError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _frames(n=3, width=1920, height=1080):
    frames = []
    for i in range(n):
        image = np.full((height, width, 3), 40 * i, dtype=np.uint8)
        frames.append(Frame(i, float(i), width, height, image, i * 30))
    return frames


def _reply(points):
    return json.dumps(
        {"frames": [{"frame_index": i, "foot_x": x, "foot_y": y} for i, (x, y) in points.items()]}
    )


def _analyzer(tmp_path, stub, **options):
    client = type("Client", (), {"interactions": stub})()
    options.setdefault("min_interval_s", 0.0)
    options.setdefault("sleep", lambda s: None)
    options.setdefault("log", lambda message: None)
    return GeminiAnalyzer("gemini-3.8-flash", client=client, cache_dir=tmp_path / "cache", **options)


def test_request_shape_sends_captioned_inline_jpegs_with_schema(tmp_path):
    stub = StubInteractions(_reply({0: (1, 2), 1: (3, 4), 2: (5, 6)}))
    _analyzer(tmp_path, stub).locate(_frames())

    sent = stub.calls[0]
    assert sent["model"] == "gemini-3.8-flash"
    assert sent["store"] is False
    assert sent["response_format"] == {"type": "text", "mime_type": "application/json", "schema": SCHEMA}
    assert "generation_config" not in sent
    parts = sent["input"]
    assert parts[0]["type"] == "text" and "foot_x" in parts[0]["text"]
    assert [p["text"] for p in parts[1::2]] == [f"Frame {i} (t={i:.1f} s):" for i in range(3)]
    images = parts[2::2]
    assert {p["type"] for p in images} == {"image"} and {p["mime_type"] for p in images} == {"image/jpeg"}
    decoded = cv2.imdecode(np.frombuffer(base64.b64decode(images[0]["data"]), np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[:2] == (540, 960)  # 1080p frames are sent at a 960 px long side


def test_temperature_is_sent_only_when_set(tmp_path):
    stub = StubInteractions(_reply({0: (1, 2)}))
    _analyzer(tmp_path, stub, temperature=0.2).locate(_frames(1))
    assert stub.calls[0]["generation_config"] == {"temperature": 0.2}


def test_normalized_point_maps_to_pixels_of_the_frame_given(tmp_path):
    stub = StubInteractions(_reply({0: (500, 1000), 1: (None, None), 2: (0, 250)}))
    analyzer = _analyzer(tmp_path, stub)
    points = analyzer.locate(_frames())

    # Sent at 960x540, but the point refers to the 1920x1080 frame the harness holds.
    assert (points[0].x_px, points[0].y_px) == (960.0, 1080.0)
    assert not points[1].visible
    assert (points[2].x_px, points[2].y_px) == (0.0, 270.0)
    statuses = [row["status"] for row in analyzer.provenance()["frames"]]
    assert statuses == ["ok", "not_visible", "ok"]


def test_non_json_reply_leaves_every_frame_without_a_point_and_keeps_the_reason(tmp_path):
    stub = StubInteractions("sorry, I cannot help")
    analyzer = _analyzer(tmp_path, stub)
    points = analyzer.locate(_frames())

    assert [p.visible for p in points] == [False, False, False]
    record = analyzer.provenance()
    assert record["status_counts"] == {"invalid_response": 3}
    assert all(row["reason"].startswith("json_parse_error") for row in record["frames"])
    cached = json.loads(open(record["requests"][0]["raw_response_path"], encoding="utf-8").read())
    assert cached["raw_text"] == "sorry, I cannot help"


@pytest.mark.parametrize(
    "entry, reason",
    [
        ({"frame_index": 1, "foot_x": 1200, "foot_y": 5}, "schema_error: foot_x=1200 is outside 0-1000"),
        ({"frame_index": 1, "foot_x": 5, "foot_y": None}, "schema_error: foot_x and foot_y must both be set"),
        (
            {"frame_index": 1, "foot_x": 5, "foot_y": 5, "zone": "kitchen_left"},
            "schema_error: unexpected keys",
        ),
        ({"frame_index": 1, "foot_x": 5.5, "foot_y": 5}, "schema_error: foot_x must be an integer"),
        ({"frame_index": 1, "foot_x": True, "foot_y": 5}, "schema_error: foot_x must be an integer"),
    ],
)
def test_a_bad_entry_invalidates_only_its_own_frame(entry, reason):
    text = json.dumps(
        {
            "frames": [
                {"frame_index": 0, "foot_x": 10, "foot_y": 20},
                entry,
                {"frame_index": 2, "foot_x": 30, "foot_y": 40},
            ]
        }
    )
    results = contract.parse_foot_response(text, [0, 1, 2])
    assert [r.status for r in results] == ["ok", "invalid_response", "ok"]
    assert results[1].reason.startswith(reason)


def test_missing_duplicate_and_extra_indices():
    text = json.dumps(
        {
            "frames": [
                {"frame_index": 0, "foot_x": 1, "foot_y": 1},
                {"frame_index": 0, "foot_x": 2, "foot_y": 2},
                {"frame_index": 9, "foot_x": 3, "foot_y": 3},
            ]
        }
    )
    results = contract.parse_foot_response(text, [0, 1])
    assert [r.reason for r in results] == ["schema_error: duplicate frame_index", "missing_frame"]
    assert contract.extra_indices(text, [0, 1]) == [9]


def test_integral_floats_are_accepted():
    results = contract.parse_foot_response(
        '{"frames": [{"frame_index": 0, "foot_x": 512.0, "foot_y": 3}]}', [0]
    )
    assert (results[0].status, results[0].foot_x_norm) == ("ok", 512)


def test_wrong_top_level_invalidates_every_frame():
    results = contract.parse_foot_response('{"frames": [], "note": "x"}', [0, 1])
    assert {r.status for r in results} == {"invalid_response"}


def test_rerun_uses_the_cache_and_needs_no_client_or_key(tmp_path, monkeypatch):
    frames = _frames()
    stub = StubInteractions(_reply({0: (1, 2), 1: (3, 4), 2: (5, 6)}))
    first = _analyzer(tmp_path, stub).locate(frames)

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    offline = GeminiAnalyzer(
        "gemini-3.8-flash", cache_dir=tmp_path / "cache", min_interval_s=0, log=lambda m: None
    )
    second = offline.locate(frames)
    assert second == first
    assert len(stub.calls) == 1
    assert [r["cache_hit"] for r in offline.provenance()["requests"]] == [True]


def test_changing_the_prompt_misses_the_cache(tmp_path):
    frames = _frames(1)
    stub = StubInteractions(_reply({0: (1, 2)}))
    _analyzer(tmp_path, stub).locate(frames)
    other = tmp_path / "foot_other.txt"
    other.write_text("a different prompt", encoding="utf-8")
    _analyzer(tmp_path, stub, prompt_path=other).locate(frames)
    assert len(stub.calls) == 2


def test_batches_are_paced_by_the_minimum_interval(tmp_path):
    now = [0.0]
    waits = []
    stub = StubInteractions(
        _reply({0: (1, 1), 1: (1, 1)}), _reply({2: (1, 1), 3: (1, 1)}), _reply({4: (1, 1)})
    )
    analyzer = _analyzer(
        tmp_path,
        stub,
        batch_size=2,
        min_interval_s=10.0,
        clock=lambda: now[0],
        sleep=waits.append,
    )
    points = analyzer.locate(_frames(5))
    assert len(stub.calls) == 3
    assert [len(call["input"]) for call in stub.calls] == [5, 5, 3]
    assert waits == [10.0, 10.0]
    assert all(p.visible for p in points)


def test_rate_limit_backs_off_then_succeeds(tmp_path):
    waits = []
    stub = StubInteractions(
        APIError(429, "RESOURCE_EXHAUSTED"), APIError(429, "RESOURCE_EXHAUSTED"), _reply({0: (1, 2)})
    )
    analyzer = _analyzer(tmp_path, stub, sleep=waits.append)
    points = analyzer.locate(_frames(1))
    assert len(stub.calls) == 3
    assert waits == [15.0, 30.0]
    assert points[0].visible


def test_persistent_rate_limit_stops_the_run_and_caches_nothing(tmp_path):
    stub = StubInteractions(APIError(429, "RESOURCE_EXHAUSTED"))
    with pytest.raises(RateLimited):
        _analyzer(tmp_path, stub).locate(_frames(1))
    assert len(stub.calls) == 5
    assert not (tmp_path / "cache").exists()


def test_daily_quota_is_not_retried(tmp_path):
    stub = StubInteractions(APIError(429, "quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier"))
    with pytest.raises(QuotaExhausted):
        _analyzer(tmp_path, stub).locate(_frames(1))
    assert len(stub.calls) == 1


def test_failure_in_a_later_batch_keeps_earlier_batches_cached(tmp_path):
    frames = _frames(2)
    stub = StubInteractions(_reply({0: (1, 1)}), APIError(500, "internal"))
    with pytest.raises(AnalyzerRequestError, match="a rerun resumes at frame 1"):
        _analyzer(tmp_path, stub, batch_size=1).locate(frames)
    stub.replies = [_reply({1: (2, 2)})]
    analyzer = _analyzer(tmp_path, stub, batch_size=1)
    assert all(p.visible for p in analyzer.locate(frames))
    assert [r["cache_hit"] for r in analyzer.provenance()["requests"]] == [True, False]


def test_error_classification_reads_the_retry_hint():
    hinted = _classify(APIError(429, "RESOURCE_EXHAUSTED ... 'retryDelay': '37s'"))
    assert isinstance(hinted, RateLimited) and hinted.retry_after_s == 37.0 and not hinted.quota_exhausted
    failed = _classify(APIError(500, "internal"))
    assert isinstance(failed, AnalyzerRequestError) and not isinstance(failed, RateLimited)


def test_missing_key_is_a_readable_error(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    analyzer = GeminiAnalyzer(
        "gemini-3.8-flash", cache_dir=tmp_path / "cache", min_interval_s=0, log=lambda m: None
    )
    with pytest.raises(AnalyzerRequestError, match="GEMINI_API_KEY is not set"):
        analyzer.locate(_frames(1))


def test_registry_builds_gemini_with_default_model_and_prompt(tmp_path):
    analyzer = create_analyzer("gemini")
    assert (analyzer.kind, analyzer.model_id, analyzer.is_remote) == ("gemini", "gemini-3.8-flash", True)
    assert analyzer.prompt_version == "foot_gemini_v1"
    right = create_analyzer("gemini:gemini-4-hydrogen", prompt_path="prompts/foot_gemini_v1_right.txt")
    assert (right.model_id, right.prompt_version) == ("gemini-4-hydrogen", "foot_gemini_v1_right")


def test_prompt_option_is_rejected_for_other_analyzers_and_missing_prompts():
    with pytest.raises(ValueError, match="only to the gemini"):
        create_analyzer("fake", prompt_path="prompts/foot_gemini_v1.txt")
    with pytest.raises(ValueError, match="only to the yolo"):
        create_analyzer("gemini", player_id="player_1")
    with pytest.raises(ValueError, match="prompt file not found"):
        create_analyzer("gemini", prompt_path="prompts/does_not_exist.txt")


# --- through the harness runner -------------------------------------------------------------

WIDTH, HEIGHT = 640, 480
CORNERS = [[80.0, 40.0], [560.0, 40.0], [560.0, 440.0], [80.0, 440.0]]


def _clip_and_corners(tmp_path):
    import mark_corners

    video = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (WIDTH, HEIGHT))
    assert writer.isOpened()
    for _ in range(2):
        writer.write(np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8))
    writer.release()
    corners = tmp_path / "corners.json"
    saved = mark_corners.upsert_clip(mark_corners.empty_registry(), "clip.mp4", WIDTH, HEIGHT, CORNERS)
    mark_corners.save_registry(corners, saved)
    return video, corners


def test_harness_refuses_gemini_without_consent_before_any_request(tmp_path):
    video, corners = _clip_and_corners(tmp_path)
    stub = StubInteractions(_reply({0: (1, 1)}))
    with pytest.raises(ValueError, match="--consent-confirmed"):
        run_harness(video, _analyzer(tmp_path, stub), corners, fps=10.0, output_root=tmp_path / "out")
    assert stub.calls == []


def test_cli_refuses_gemini_without_consent(tmp_path, capsys):
    video, corners = _clip_and_corners(tmp_path)
    code = run_module.main([str(video), "--analyzer", "gemini", "--corners", str(corners)])
    assert code == 2
    assert "--consent-confirmed" in capsys.readouterr().err


def test_end_to_end_points_become_feet_and_zones_with_provenance(tmp_path):
    video, corners = _clip_and_corners(tmp_path)
    homography = court.compute_homography(CORNERS)
    x_px, y_px = court.apply_homography(np.linalg.inv(homography), [[5.0, 25.0]])[0]
    norm = (round(x_px / WIDTH * 1000), round(y_px / HEIGHT * 1000))
    stub = StubInteractions(_reply({0: norm, 1: (None, None)}))

    outcome = run_harness(
        video,
        _analyzer(tmp_path, stub),
        corners,
        fps=10.0,
        output_root=tmp_path / "out",
        consent_confirmed=True,
    )

    assert [row["zone"] for row in outcome.rows] == ["kitchen_left", "not_visible"]
    assert abs(outcome.rows[0]["x_ft"] - 5.0) < 0.1 and abs(outcome.rows[0]["y_ft"] - 25.0) < 0.1
    assert outcome.rows[1]["x_ft"] is None
    provenance = json.loads((outcome.run_dir / "analyzer.json").read_text(encoding="utf-8"))
    assert provenance["status_counts"] == {"ok": 1, "not_visible": 1}
    assert provenance["prompt_version"] == "foot_gemini_v1"
    summary = json.loads((outcome.run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["analyzer"] == "gemini" and summary["analyzer_provenance_file"] == "analyzer.json"
