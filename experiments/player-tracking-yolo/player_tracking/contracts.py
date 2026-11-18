"""Proposed internal contract; not yet Liam's validation-framework contract."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class BoundingBox(StrictModel):
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)
    x2: float = Field(gt=0)
    y2: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Bounding box must have positive width and height.")
        return self

    def in_image(self, width: int, height: int) -> bool:
        return self.x2 <= width and self.y2 <= height


class Selection(StrictModel):
    frame_index: int = Field(default=0, ge=0, strict=True)
    bbox: BoundingBox


class TrackingConfig(StrictModel):
    device: Literal["cpu", "mps"] = "cpu"
    image_size: int = Field(default=640, ge=160, le=1280, multiple_of=32)
    detection_confidence: float = Field(default=0.1, gt=0, lt=1)
    ankle_confidence: float = Field(default=0.5, gt=0, le=1)
    selection_iou: float = Field(default=0.5, gt=0, le=1)
    ambiguity_margin: float = Field(default=0.1, ge=0, le=1)
    max_frames: int = Field(default=300, ge=1, le=1800, strict=True)


class VideoInfo(StrictModel):
    width: int
    height: int
    fps: float
    frame_count: int
    duration_s: float


class FrameRecord(StrictModel):
    player_id: str = "player_1"
    frame_index: int
    timestamp_s: float
    selected_track_id: int
    status: Literal["ok", "target_not_detected", "keypoints_unreliable"]
    reason: str | None = None
    bbox: BoundingBox | None = None
    image_x_px: float | None = None
    image_y_px: float | None = None
    point_source: Literal["ankle_midpoint"] = "ankle_midpoint"
    left_ankle_confidence: float | None = None
    right_ankle_confidence: float | None = None


@dataclass(frozen=True)
class Detection:
    bbox: BoundingBox
    confidence: float
    track_id: int | None = None
    left_ankle: tuple[float, float, float] | None = None
    right_ankle: tuple[float, float, float] | None = None


class InputError(ValueError):
    """An actionable video/selection error, safe to display to the local user."""
