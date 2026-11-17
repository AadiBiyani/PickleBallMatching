"""Acceptance cases 2-5: response validation and coordinate conversion."""

from __future__ import annotations

import json

from harness.contract import (
    STATUS_INVALID,
    STATUS_OK,
    ZONE_VALUES,
    extra_indices,
    norm_to_px,
    response_json_schema,
    validate_response,
)

SENT = [0, 1, 2, 3, 4]


def entry(i, zone="kitchen_left", x=500, y=700):
    return {"frame_index": i, "zone": zone, "foot_x": x, "foot_y": y}


def as_text(entries):
    return json.dumps({"frames": entries})


def test_valid_response_gives_one_ok_row_per_frame():
    res = validate_response(as_text([entry(i) for i in SENT]), SENT)
    assert [r.frame_index for r in res] == SENT
    assert all(r.status == STATUS_OK for r in res)
    assert res[0].zone == "kitchen_left" and res[0].foot_x_norm == 500


def test_norm_to_px():
    assert norm_to_px(500, 960) == 480
    assert norm_to_px(1000, 540) == 539
    assert norm_to_px(0, 960) == 0


def test_missing_frame_is_recorded_not_dropped():
    res = validate_response(as_text([entry(i) for i in SENT if i != 3]), SENT)
    assert len(res) == 5
    assert [r.status for r in res].count(STATUS_OK) == 4
    assert res[3].status == STATUS_INVALID and res[3].reason == "missing_frame"


def test_not_json_marks_every_frame_invalid():
    res = validate_response("The player is in the kitchen.", SENT)
    assert len(res) == 5
    assert all(r.status == STATUS_INVALID and r.reason.startswith("json_parse_error") for r in res)


def test_wrong_top_level_shape_is_schema_error():
    res = validate_response(json.dumps([entry(0)]), [0])
    assert res[0].status == STATUS_INVALID and res[0].reason.startswith("schema_error")


def test_bad_entries_fail_only_their_frame():
    entries = [
        entry(0, zone="kitchen_center"),
        entry(1, x=1200),
        entry(2, zone="not_visible", x=10, y=10),
        entry(3, zone="backcourt_left", x=None, y=None),
        {"frame_index": 4, "zone": "not_visible", "foot_x": None, "foot_y": None},
    ]
    res = validate_response(as_text(entries), SENT)
    assert [r.status for r in res] == [STATUS_INVALID] * 4 + [STATUS_OK]
    assert all(r.reason.startswith("schema_error") for r in res[:4])
    assert res[4].zone == "not_visible" and res[4].foot_x_norm is None


def test_duplicate_and_extra_indices():
    text = as_text([entry(0), entry(0, zone="kitchen_right"), entry(1), entry(7)])
    res = validate_response(text, [0, 1])
    assert res[0].status == STATUS_INVALID and "duplicate" in res[0].reason
    assert res[1].status == STATUS_OK
    assert extra_indices(text, [0, 1]) == [7]


def test_extra_keys_rejected():
    e = entry(0)
    e["confidence"] = "high"
    res = validate_response(as_text([e]), [0])
    assert res[0].status == STATUS_INVALID


def test_schema_lists_all_eight_zones():
    schema = response_json_schema()
    item = schema["properties"]["frames"]["items"]
    assert item["properties"]["zone"]["enum"] == list(ZONE_VALUES)
    assert len(ZONE_VALUES) == 8
    assert item["properties"]["foot_x"] == {"type": ["integer", "null"], "minimum": 0, "maximum": 1000}
