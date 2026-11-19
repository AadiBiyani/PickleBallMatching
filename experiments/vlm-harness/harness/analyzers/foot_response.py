"""Response contract for vision-language analyzers that report a foot point.

The model returns, per frame, the ground point midway between the tracked
player's feet as integers 0-1000 normalized to the image, or null for both when
the feet are not visible. This module turns the raw text into one outcome per
frame that was sent. It never repairs, retries, or drops an answer, and it does
no I/O, model calls, homography, or zone assignment.

Ported from the zone harness on liam-test-harness (harness/contract.py) with the
model-chosen zone removed: the harness derives zones from court feet.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

NORM_MAX = 1000

STATUS_OK = "ok"
STATUS_NOT_VISIBLE = "not_visible"
STATUS_INVALID = "invalid_response"

REASON_JSON = "json_parse_error"
REASON_SCHEMA = "schema_error"
REASON_MISSING = "missing_frame"

_ENTRY_KEYS = {"frame_index", "foot_x", "foot_y"}


def response_json_schema() -> dict:
    """JSON Schema sent to the provider. Uses only widely supported keywords."""
    coord = {"type": ["integer", "null"], "minimum": 0, "maximum": NORM_MAX}
    return {
        "type": "object",
        "properties": {
            "frames": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "frame_index": {"type": "integer", "minimum": 0},
                        "foot_x": coord,
                        "foot_y": coord,
                    },
                    "required": ["frame_index", "foot_x", "foot_y"],
                },
            }
        },
        "required": ["frames"],
    }


@dataclass(frozen=True)
class FootResult:
    """Validated outcome for one sent frame. Coordinates are set only when status is ok."""

    frame_index: int
    status: str
    reason: str = ""
    foot_x_norm: int | None = None
    foot_y_norm: int | None = None


def norm_to_px(value: int, size_px: int) -> float:
    """Map a 0-1000 normalized coordinate to a continuous pixel coordinate in [0, size_px]."""
    return value / NORM_MAX * size_px


def _as_int(value: object) -> int | None:
    """Accept an int, or a float with an integral value; reject bool and everything else."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _check_coord(name: str, value: object) -> tuple[int | None, str]:
    if value is None:
        return None, ""
    number = _as_int(value)
    if number is None:
        return None, f"{REASON_SCHEMA}: {name} must be an integer or null"
    if not 0 <= number <= NORM_MAX:
        return None, f"{REASON_SCHEMA}: {name}={number} is outside 0-{NORM_MAX}"
    return number, ""


def _check_entry(index: int, entry: dict) -> FootResult:
    extra = sorted(set(entry) - _ENTRY_KEYS)
    if extra:
        return FootResult(index, STATUS_INVALID, f"{REASON_SCHEMA}: unexpected keys {extra}")
    missing = sorted(_ENTRY_KEYS - set(entry))
    if missing:
        return FootResult(index, STATUS_INVALID, f"{REASON_SCHEMA}: missing keys {missing}")
    x, x_error = _check_coord("foot_x", entry["foot_x"])
    if x_error:
        return FootResult(index, STATUS_INVALID, x_error)
    y, y_error = _check_coord("foot_y", entry["foot_y"])
    if y_error:
        return FootResult(index, STATUS_INVALID, y_error)
    if x is None and y is None:
        return FootResult(index, STATUS_NOT_VISIBLE)
    if x is None or y is None:
        return FootResult(
            index, STATUS_INVALID, f"{REASON_SCHEMA}: foot_x and foot_y must both be set or both null"
        )
    return FootResult(index, STATUS_OK, "", x, y)


def _entry_index(entry: object) -> int | None:
    if not isinstance(entry, dict):
        return None
    index = entry.get("frame_index")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        return None
    return index


def parse_foot_response(text: str, sent_indices: list[int]) -> list[FootResult]:
    """One FootResult per sent index, in order. A bad entry invalidates only its own frame."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        return [FootResult(i, STATUS_INVALID, f"{REASON_JSON}: {exc}") for i in sent_indices]
    if not isinstance(data, dict) or set(data) != {"frames"} or not isinstance(data["frames"], list):
        reason = f"{REASON_SCHEMA}: top level must be an object with only a 'frames' list"
        return [FootResult(i, STATUS_INVALID, reason) for i in sent_indices]

    by_index: dict[int, list[dict]] = {}
    for entry in data["frames"]:
        index = _entry_index(entry)
        # An entry without a usable frame_index cannot be attributed; its frame shows as missing.
        if index is not None:
            by_index.setdefault(index, []).append(entry)

    results = []
    for i in sent_indices:
        entries = by_index.get(i, [])
        if not entries:
            results.append(FootResult(i, STATUS_INVALID, REASON_MISSING))
        elif len(entries) > 1:
            results.append(FootResult(i, STATUS_INVALID, f"{REASON_SCHEMA}: duplicate frame_index"))
        else:
            results.append(_check_entry(i, entries[0]))
    return results


def extra_indices(text: str, sent_indices: list[int]) -> list[int]:
    """Frame indices in a response that were never sent. Recorded, not scored."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    frames = data.get("frames") if isinstance(data, dict) else None
    if not isinstance(frames, list):
        return []
    sent = set(sent_indices)
    return sorted({i for i in map(_entry_index, frames) if i is not None and i not in sent})
