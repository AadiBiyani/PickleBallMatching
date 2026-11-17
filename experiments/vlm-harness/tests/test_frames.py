"""Acceptance case 1: shared frame extraction (SYNTHETIC video)."""

from __future__ import annotations

import pytest

from harness.frames import extract_frames
from tests.conftest import make_synthetic_video


def test_one_fps_gives_five_frames_at_960x540(video_1080p):
    frames = extract_frames(video_1080p, fps=1.0, long_side_px=960)
    assert [f.time_s for f in frames] == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert [f.index for f in frames] == [0, 1, 2, 3, 4]
    assert {(f.width_px, f.height_px) for f in frames} == {(960, 540)}
    decoded = frames[0].decode()
    assert decoded.shape == (540, 960, 3)


def test_two_fps_gives_ten_frames(video_1080p):
    frames = extract_frames(video_1080p, fps=2.0)
    assert len(frames) == 10
    assert frames[1].time_s == 0.5


def test_portrait_video_keeps_orientation(tmp_path):
    video = make_synthetic_video(tmp_path / "portrait.avi", seconds=2.0, fps=10.0, size=(1080, 1920))
    frames = extract_frames(video, fps=1.0)
    assert {(f.width_px, f.height_px) for f in frames} == {(540, 960)}


def test_frames_are_identical_across_calls(video_small):
    a = extract_frames(video_small)
    b = extract_frames(video_small)
    assert [f.sha256 for f in a] == [f.sha256 for f in b]


def test_bad_inputs_raise_readable_errors(tmp_path, video_small):
    with pytest.raises(ValueError, match="not found"):
        extract_frames(tmp_path / "nope.mp4")
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"not a video")
    with pytest.raises(ValueError):
        extract_frames(junk)
    with pytest.raises(ValueError, match="fps"):
        extract_frames(video_small, fps=0)
