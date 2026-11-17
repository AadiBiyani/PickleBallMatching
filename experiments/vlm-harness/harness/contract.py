"""Output contract for the VLM zone harness: zones, the response schema, and validation.

Turns a model's raw response text into exactly one FrameResult per frame that was sent.
Invalid output is recorded as a failure with a reason; it is never repaired, retried,
or dropped here.

Deliberately does not do I/O, model calls, or court-coordinate (feet) geometry.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Zone(str, Enum):
    """Court zones on the player's (near) half, left/right as seen in the image."""

    KITCHEN_LEFT = "kitchen_left"
    KITCHEN_RIGHT = "kitchen_right"
    TRANSITION_LEFT = "transition_left"
    TRANSITION_RIGHT = "transition_right"
    BACKCOURT_LEFT = "backcourt_left"
    BACKCOURT_RIGHT = "backcourt_right"
    OUT_OF_COURT = "out_of_court"
    NOT_VISIBLE = "not_visible"


ZONE_VALUES: tuple[str, ...] = tuple(z.value for z in Zone)

# Zone extents in the court frame from docs/vlm-harness-notes.md (feet, origin at the
# far-left outside corner, x 0-20, y 0-44; near half is y 22-44). Reference only: the MVP
# does not compute feet. Transition/backcourt split is at 14.5 ft from the net (no painted line).
ZONE_EXTENTS_FT: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    "kitchen_left": ((0.0, 10.0), (22.0, 29.0)),
    "kitchen_right": ((10.0, 20.0), (22.0, 29.0)),
    "transition_left": ((0.0, 10.0), (29.0, 36.5)),
    "transition_right": ((10.0, 20.0), (29.0, 36.5)),
    "backcourt_left": ((0.0, 10.0), (36.5, 44.0)),
    "backcourt_right": ((10.0, 20.0), (36.5, 44.0)),
}

NORM_MAX = 1000  # model coordinates are integers 0..1000, normalized to the image

# Row status strings.
STATUS_OK = "ok"
STATUS_INVALID = "invalid_response"
STATUS_REQUEST_ERROR = "request_error"

# Reasons for a non-ok status.
REASON_JSON = "json_parse_error"
REASON_SCHEMA = "schema_error"
REASON_MISSING = "missing_frame"
REASON_RATE_LIMITED = "rate_limited"
REASON_QUOTA = "quota_exhausted"
REASON_REQUEST_FAILED = "request_failed"


class FramePrediction(BaseModel):
    """One frame's answer as the model must return it."""

    model_config = ConfigDict(extra="forbid")

    frame_index: int = Field(ge=0)
    zone: Literal[
        "kitchen_left",
        "kitchen_right",
        "transition_left",
        "transition_right",
        "backcourt_left",
        "backcourt_right",
        "out_of_court",
        "not_visible",
    ]
    foot_x: int | None = Field(ge=0, le=NORM_MAX)
    foot_y: int | None = Field(ge=0, le=NORM_MAX)


class ZoneResponse(BaseModel):
    """Top-level response: one entry per frame sent."""

    model_config = ConfigDict(extra="forbid")

    frames: list[dict]  # entries are validated one by one so one bad frame fails alone


def response_json_schema() -> dict:
    """JSON Schema sent to providers (Gemini response_format, Ollama format).

    Written by hand so it uses only keywords both providers document: type arrays for
    null, enum, minimum/maximum, required.
    """
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
                        "zone": {"type": "string", "enum": list(ZONE_VALUES)},
                        "foot_x": coord,
                        "foot_y": coord,
                    },
                    "required": ["frame_index", "zone", "foot_x", "foot_y"],
                },
            }
        },
        "required": ["frames"],
    }


@dataclass(frozen=True)
class FrameResult:
    """Validated outcome for one frame of one request."""

    frame_index: int
    status: str
    reason: str = ""
    zone: str | None = None
    foot_x_norm: int | None = None
    foot_y_norm: int | None = None

    @property
    def is_valid(self) -> bool:
        return self.status == STATUS_OK


def norm_to_px(value: int, size_px: int) -> int:
    """Map a 0..1000 normalized coordinate to a pixel index in 0..size_px-1."""
    return int(math.floor(value / NORM_MAX * (size_px - 1) + 0.5))


def _check_entry(entry: object) -> tuple[FramePrediction | None, str]:
    try:
        pred = FramePrediction.model_validate(entry)
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first.get("loc", ()))
        return None, f"{REASON_SCHEMA}: {loc} {first.get('msg', '')}".strip()
    if pred.zone == Zone.NOT_VISIBLE.value:
        if pred.foot_x is not None or pred.foot_y is not None:
            return None, f"{REASON_SCHEMA}: not_visible must have null foot point"
    elif pred.foot_x is None or pred.foot_y is None:
        return None, f"{REASON_SCHEMA}: visible zone requires foot_x and foot_y"
    return pred, ""


def validate_response(text: str, sent_indices: list[int]) -> list[FrameResult]:
    """Validate raw response text. Returns one FrameResult per sent index, in order."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        return [FrameResult(i, STATUS_INVALID, f"{REASON_JSON}: {exc}") for i in sent_indices]

    try:
        top = ZoneResponse.model_validate(data)
    except ValidationError as exc:
        msg = exc.errors()[0].get("msg", "")
        return [FrameResult(i, STATUS_INVALID, f"{REASON_SCHEMA}: top level: {msg}") for i in sent_indices]

    by_index: dict[int, list[object]] = {}
    for entry in top.frames:
        idx = entry.get("frame_index") if isinstance(entry, dict) else None
        if isinstance(idx, int) and not isinstance(idx, bool):
            by_index.setdefault(idx, []).append(entry)
        # Entries without a usable frame_index cannot be attributed to any frame; the
        # frame they were meant for is then reported as missing.

    results: list[FrameResult] = []
    for i in sent_indices:
        entries = by_index.get(i, [])
        if not entries:
            results.append(FrameResult(i, STATUS_INVALID, REASON_MISSING))
            continue
        if len(entries) > 1:
            results.append(FrameResult(i, STATUS_INVALID, f"{REASON_SCHEMA}: duplicate frame_index"))
            continue
        pred, err = _check_entry(entries[0])
        if pred is None:
            results.append(FrameResult(i, STATUS_INVALID, err))
        else:
            results.append(FrameResult(i, STATUS_OK, "", pred.zone, pred.foot_x, pred.foot_y))
    return results


def extra_indices(text: str, sent_indices: list[int]) -> list[int]:
    """Frame indices present in a response that were never sent (reported in run.json)."""
    try:
        frames = json.loads(text).get("frames", [])
    except (json.JSONDecodeError, AttributeError, TypeError):
        return []
    sent = set(sent_indices)
    out = []
    for entry in frames if isinstance(frames, list) else []:
        idx = entry.get("frame_index") if isinstance(entry, dict) else None
        if isinstance(idx, int) and not isinstance(idx, bool) and idx not in sent:
            out.append(idx)
    return sorted(out)


def request_error_results(sent_indices: list[int], reason: str) -> list[FrameResult]:
    """Rows for frames whose request never produced a response."""
    return [FrameResult(i, STATUS_REQUEST_ERROR, reason) for i in sent_indices]
