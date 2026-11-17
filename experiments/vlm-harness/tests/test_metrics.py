"""Acceptance cases 6-7: self-agreement, foot spread, label matching, zone accuracy."""

from __future__ import annotations

import pytest

from harness.labels import Label, load_labels
from harness.metrics import (
    foot_spread_px,
    frame_agreement,
    match_labels,
    self_agreement,
    valid_rate,
    zone_accuracy,
)


def test_frame_agreement_cases():
    assert frame_agreement(["A", "A", "B"]) == pytest.approx(2 / 3)
    assert frame_agreement(["A", "A", "A"]) == 1.0
    assert frame_agreement(["A", None, "A"]) == pytest.approx(2 / 3)
    assert frame_agreement([None, None, None]) == 0.0


def test_self_agreement_clip_mean():
    zones = {0: ["A", "A", "B"], 1: ["A", "A", "A"], 2: ["A", None, "A"]}
    assert self_agreement(zones) == pytest.approx(0.778, abs=1e-3)


def test_self_agreement_unavailable_with_one_repeat():
    assert self_agreement({0: ["A"]}) is None
    assert self_agreement({}) is None


def test_valid_rate():
    assert valid_rate([True] * 4 + [False]) == pytest.approx(0.8)
    assert valid_rate([]) is None


def test_foot_spread():
    pts = {0: [(100, 100), (100, 100), (103, 104)], 1: [(10, 10), None]}
    # frame 0 median (100,100): distances 0, 0, 5 -> median 0; frame 1 has < 2 valid points
    assert foot_spread_px(pts) == 0.0
    assert foot_spread_px({0: [(0, 0), (6, 8)]}) == pytest.approx(5.0)
    assert foot_spread_px({0: [None, (1, 1)]}) is None


FRAME_TIMES = {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0}


def test_zone_accuracy_counts_invalid_as_wrong():
    labels = [Label(t, z) for t, z in zip([0, 1, 2, 3, 4], ["kitchen_left", "kitchen_left", "transition_right", "transition_right", "backcourt_left"])]
    m = match_labels(labels, FRAME_TIMES, fps=1.0)
    preds = [(0, "kitchen_left"), (1, "kitchen_right"), (2, "transition_right"), (3, None), (4, "backcourt_left")]
    acc, n = zone_accuracy(preds, m.by_frame)
    assert acc == pytest.approx(0.60) and n == 5


def test_label_matching_tolerance_and_unmatched():
    m = match_labels([Label(2.4, "kitchen_left"), Label(9.0, "kitchen_left")], FRAME_TIMES, fps=1.0)
    assert m.by_frame == {2: "kitchen_left"}
    assert m.unmatched == (Label(9.0, "kitchen_left"),)
    acc, n = zone_accuracy([(i, "kitchen_left") for i in FRAME_TIMES], m.by_frame)
    assert (acc, n) == (1.0, 1)


def test_two_labels_on_one_frame_nearer_wins():
    m = match_labels([Label(1.3, "kitchen_left"), Label(1.1, "kitchen_right")], FRAME_TIMES, fps=1.0)
    assert m.by_frame == {1: "kitchen_right"}
    assert m.unmatched == (Label(1.3, "kitchen_left"),)


def test_no_labels_gives_unavailable_accuracy():
    assert zone_accuracy([(0, "kitchen_left")], {}) == (None, 0)


def test_load_labels_validates(tmp_path):
    good = tmp_path / "good.csv"
    good.write_text("time_s,zone\n0.0,kitchen_left\n1.5,not_visible\n", encoding="utf-8")
    assert load_labels(good) == [Label(0.0, "kitchen_left"), Label(1.5, "not_visible")]
    bad_zone = tmp_path / "bad_zone.csv"
    bad_zone.write_text("time_s,zone\n0.0,kitchen_center\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r":2: zone"):
        load_labels(bad_zone)
    bad_header = tmp_path / "bad_header.csv"
    bad_header.write_text("t,zone\n0,kitchen_left\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing column"):
        load_labels(bad_header)
    bad_time = tmp_path / "bad_time.csv"
    bad_time.write_text("time_s,zone\nabc,kitchen_left\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a number"):
        load_labels(bad_time)
