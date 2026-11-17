"""Acceptance cases 3, 4, 7-10, 12 end to end with the fake analyzer (SYNTHETIC video, no network)."""

from __future__ import annotations

import csv
import json

import pytest

from harness.analyzers.base import create_analyzer
from harness.analyzers.fake import FakeAnalyzer
from harness.analyzers.gemini import FREE_TIER_NOTICE, GeminiAnalyzer
from harness.run import RESULT_COLUMNS, ConsentRequired, main, run_harness


def run(video, analyzers, tmp_path, fake_clock, logs=None, **kw):
    out = logs if logs is not None else []
    return run_harness(
        video, analyzers, output_root=tmp_path / "out", clock=fake_clock, sleep=fake_clock.sleep,
        log=out.append, **kw,
    )


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_valid_run_writes_rows_frames_annotations_and_summary(video_small, tmp_path, fake_clock):
    logs: list[str] = []
    res = run(video_small, [FakeAnalyzer("valid")], tmp_path, fake_clock, logs)
    rows = read_csv(res.run_dir / "results.csv")
    assert list(rows[0].keys()) == RESULT_COLUMNS
    assert len(rows) == 5 and all(r["status"] == "ok" for r in rows)
    assert rows[0]["zone"] == "backcourt_left"
    # canned foot (300, 600) on 960x540 -> (288, 323)
    assert (rows[0]["foot_x_px"], rows[0]["foot_y_px"]) == ("288", "323")
    assert len(list((res.run_dir / "frames").glob("*.jpg"))) == 5
    assert len(list((res.run_dir / "annotated" / "fake_valid" / "r0").glob("*.jpg"))) == 5
    s = res.summaries[0]
    assert s.valid_rate == 1.0 and s.self_agreement is None and s.zone_accuracy is None
    assert (res.run_dir / "summary.csv").is_file() and (res.run_dir / "run.json").is_file()
    assert any("Labels: none" in m for m in logs)
    assert any("SYNTHETIC" in m for m in logs)


def test_missing_frame_valid_rate(video_small, tmp_path, fake_clock):
    res = run(video_small, [FakeAnalyzer("missing_frame")], tmp_path, fake_clock)
    assert res.summaries[0].valid_rate == pytest.approx(0.8)
    missing = [r for r in res.rows if r["reason"] == "missing_frame"]
    assert [r["frame_index"] for r in missing] == [2]


def test_invalid_json_is_cached_and_recorded(video_small, tmp_path, fake_clock):
    res = run(video_small, [FakeAnalyzer("invalid_json")], tmp_path, fake_clock)
    assert all(r["status"] == "invalid_response" for r in res.rows)
    raw = {r["raw_response_path"] for r in res.rows}
    assert len(raw) == 1
    cached = json.loads(open(raw.pop(), encoding="utf-8").read())
    assert cached["raw_text"].startswith("Sure!")


def test_rerun_hits_cache_and_makes_no_calls(video_small, tmp_path, fake_clock):
    first = FakeAnalyzer("valid")
    a = run(video_small, [first], tmp_path, fake_clock, repeats=2)
    assert first.calls == 2
    second = FakeAnalyzer("valid")
    b = run(video_small, [second], tmp_path, fake_clock, repeats=2)
    assert second.calls == 0
    assert a.run_dir != b.run_dir
    strip = lambda rows: [{k: v for k, v in r.items() if k != "cache_hit"} for r in rows]  # noqa: E731
    ra, rb = read_csv(a.run_dir / "results.csv"), read_csv(b.run_dir / "results.csv")
    assert strip(ra) == strip(rb)
    assert {r["cache_hit"] for r in rb} == {"True"}


def test_repeats_and_self_agreement(video_small, tmp_path, fake_clock):
    res = run(video_small, [FakeAnalyzer("noisy")], tmp_path, fake_clock, repeats=3)
    s = res.summaries[0]
    # third call shifts every zone: each frame [z, z, z'] -> 2/3
    assert s.self_agreement == pytest.approx(2 / 3)
    assert s.foot_spread_px == 0.0
    assert len(res.rows) == 15


def test_batch_size_splits_requests(video_small, tmp_path, fake_clock):
    fake = FakeAnalyzer("valid")
    run(video_small, [fake], tmp_path, fake_clock, batch_size=2)
    assert fake.requests == [[0, 1], [2, 3], [4]]


def test_rate_limit_then_ok(video_small, tmp_path, fake_clock):
    fake = FakeAnalyzer("rate_limit_then_ok")
    res = run(video_small, [fake], tmp_path, fake_clock)
    assert fake.calls == 3
    assert fake_clock.sleeps == [15.0, 30.0]
    assert all(r["status"] == "ok" for r in res.rows)


def test_always_rate_limited_is_recorded_and_not_cached(video_small, tmp_path, fake_clock):
    fake = FakeAnalyzer("always_rate_limited")
    res = run(video_small, [fake], tmp_path, fake_clock)
    assert {(r["status"], r["reason"]) for r in res.rows} == {("request_error", "rate_limited")}
    assert res.summaries[0].s_per_clip is None
    assert not list((tmp_path / "out" / "cache").rglob("*.json"))
    again = FakeAnalyzer("always_rate_limited")
    run(video_small, [again], tmp_path, fake_clock)
    assert again.calls == 5  # tried again: nothing was cached


def test_quota_exhausted_stops_further_calls(video_small, tmp_path, fake_clock):
    fake = FakeAnalyzer("quota_exhausted")
    res = run(video_small, [fake], tmp_path, fake_clock, batch_size=1, repeats=2)
    assert fake.calls == 1
    assert {r["reason"] for r in res.rows} == {"quota_exhausted"}
    assert len(res.rows) == 10


def test_request_failure_rows(video_small, tmp_path, fake_clock):
    res = run(video_small, [FakeAnalyzer("request_failed")], tmp_path, fake_clock)
    assert all(r["status"] == "request_error" and r["reason"].startswith("request_failed") for r in res.rows)


def test_labels_give_zone_accuracy(video_small, tmp_path, fake_clock):
    labels = tmp_path / "labels.csv"
    # fake zones by frame: backcourt_left, backcourt_right, transition_left, transition_right, kitchen_left
    labels.write_text(
        "time_s,zone\n0,backcourt_left\n1,backcourt_left\n2.4,transition_left\n3,transition_right\n4,kitchen_left\n9,kitchen_left\n",
        encoding="utf-8",
    )
    res = run(video_small, [FakeAnalyzer("valid")], tmp_path, fake_clock, labels_path=labels)
    s = res.summaries[0]
    assert s.zone_accuracy == pytest.approx(0.8) and s.n_labeled_frames == 5
    assert res.unmatched_labels == [{"time_s": 9.0, "zone": "kitchen_left"}]


def test_labels_found_beside_clip(video_small, tmp_path, fake_clock):
    beside = video_small.with_name(f"{video_small.stem}.labels.csv")
    beside.write_text("time_s,zone\n0,backcourt_left\n", encoding="utf-8")
    try:
        res = run(video_small, [FakeAnalyzer("valid")], tmp_path, fake_clock)
        assert res.summaries[0].zone_accuracy == 1.0 and res.summaries[0].n_labeled_frames == 1
    finally:
        beside.unlink()


def test_comparison_table_has_one_row_per_analyzer(video_small, tmp_path, fake_clock):
    logs: list[str] = []
    res = run(video_small, [FakeAnalyzer("valid"), FakeAnalyzer("missing_frame")], tmp_path, fake_clock, logs, repeats=2)
    table = next(m for m in logs if m.startswith("analyzer"))
    lines = table.splitlines()
    assert len(lines) == 4  # header, rule, two analyzers
    assert "valid_rate" in lines[0] and "self_agree" in lines[0] and "s_per_clip" in lines[0]
    assert lines[2].startswith("fake:valid") and "1.000 (10/10)" in lines[2]
    assert lines[3].startswith("fake:missing_frame") and "0.800 (8/10)" in lines[3]
    assert len(res.summaries) == 2


class StubInteractions:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def create(self, **kw):
        self.calls.append(kw)
        idx = [int(p["text"].split()[1]) for p in kw["input"] if p["type"] == "text" and p["text"].startswith("Frame ")]
        return type("I", (), {"output_text": self.reply(idx)})()


class StubClient:
    def __init__(self, reply):
        self.interactions = StubInteractions(reply)


def test_gemini_requires_consent(video_small, tmp_path, fake_clock):
    gem = GeminiAnalyzer("gemini-3.8-flash", client=StubClient(lambda idx: "{}"))
    with pytest.raises(ConsentRequired, match="consent-confirmed"):
        run(video_small, [gem], tmp_path, fake_clock)
    assert gem._client.interactions.calls == []


def test_gemini_run_prints_notice_and_sends_one_request(video_small, tmp_path, fake_clock):
    from harness.analyzers.fake import canned_entry

    stub = StubClient(lambda idx: json.dumps({"frames": [canned_entry(i) for i in idx]}))
    gem = GeminiAnalyzer("gemini-3.8-flash", client=stub)
    logs: list[str] = []
    res = run(video_small, [gem], tmp_path, fake_clock, logs, consent_confirmed=True)
    assert FREE_TIER_NOTICE in logs
    assert len(stub.interactions.calls) == 1
    assert res.summaries[0].valid_rate == 1.0


def test_cli_rejects_gemini_without_consent(video_small, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    code = main([str(video_small), "--analyzer", "gemini", "--output", str(tmp_path / "o")])
    assert code == 2
    err = capsys.readouterr().err
    assert "consent-confirmed" in err and "test-key-not-real" not in err


def test_cli_fake_end_to_end(video_small, tmp_path, capsys):
    code = main([str(video_small), "--analyzer", "fake:valid", "--analyzer", "fake:noisy", "--repeats", "3",
                 "--output", str(tmp_path / "o")])
    assert code == 0
    out = capsys.readouterr().out
    assert "fake:valid" in out and "fake:noisy" in out and "Wrote" in out


def test_unknown_analyzer_is_readable():
    with pytest.raises(ValueError, match="unknown analyzer"):
        create_analyzer("openai:gpt")
    with pytest.raises(ValueError, match="unknown fake scenario"):
        create_analyzer("fake:nope")
    assert create_analyzer("gemini").model_id == "gemini-3.8-flash"
    assert create_analyzer("ollama:qwen3-vl:8b").model_id == "qwen3-vl:8b"
