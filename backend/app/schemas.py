"""API and domain models shared by the routes, pipeline, and vision adapters."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# FR-06 status progression, plus the pre-upload state required by FR-07 retries.
SessionStatus = Literal["awaiting_upload", "uploaded", "queued", "processing", "completed", "failed"]

# FR-09 attempt classifications.
Outcome = Literal["success", "failure", "invalid_feed", "uncertain"]

FeedMethod = Literal["human_feeder", "ball_machine"]
DrillStage = Literal["prescribed", "reactive"]

# Prototype-only switch so every error/empty screen can be demonstrated on demand.
Scenario = Literal["normal", "upload_error", "processing_error", "insufficient_data"]


class Region(BaseModel):
    id: str
    label: str


class Drill(BaseModel):
    id: str
    version: str
    name: str
    summary: str
    purpose: str
    stage: DrillStage
    feed_count: int
    max_recording_s: int
    equipment: list[str]
    starting_position: str
    steps: list[str]
    target_area: str
    regions: list[Region]


class VisionModelInfo(BaseModel):
    id: str
    kind: str
    model_id: str
    name: str
    owner: str
    version: str
    description: str
    is_remote: bool  # frames leave this machine; needs participant consent (SYS-08)
    requires_clip_file: bool
    sample_fps: float
    # "court": the model reports court feet itself (expected default); "image": pixels
    # the backend projects with the clip's saved corners (court evaluation harness style).
    output_space: Literal["court", "image"]
    available: bool = True
    unavailable_reason: str | None = None
    selection_mode: Literal["none", "multiple", "first_pose"] = "none"
    requires_calibration: bool = False


class Clip(BaseModel):
    id: str
    name: str
    size_mb: float | None = None
    synthetic: bool = False
    has_corners: bool = False  # court corners saved in sample_clips/corners.json


# ---- Vision output (FR-08) -------------------------------------------------
# Rows match the team's court evaluation harness (results.csv columns). Feet are
# the project's unit: COURT FEET have origin at the far-left outside corner,
# x 0-20 toward the right sideline, y 0-44 toward the near baseline. A model
# reports either feet directly or an image point the pipeline projects with the
# clip's saved corners; the zone is always derived here. See app/court.py.

Zone = Literal[
    "kitchen_left",
    "kitchen_right",
    "transition_left",
    "transition_right",
    "backcourt_left",
    "backcourt_right",
    "out_of_court",
    "not_visible",
]


class CourtPoint(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    frame_index: int
    time_s: float
    x_px: float | None  # None when the player was not visible in this frame
    y_px: float | None
    x_ft: float | None
    y_ft: float | None
    zone: Zone
    source_frame_index: int | None = None
    player_id: str = "player_1"
    status: str = "ok"
    reason: str | None = None
    point_source: str = "simulated"


class TrackSummary(BaseModel):
    kind: str
    model_id: str
    model_version: str
    sample_fps: float
    frame_size_px: tuple[int, int]
    frames: int
    missing_frames: int  # frames with no player point (zone "not_visible")
    zone_counts: dict[str, int]
    data_source: Literal["simulated", "model"] = "simulated"
    observations: int = 0
    players: list[str] = Field(default_factory=lambda: ["player_1"])
    limitations: list[str] = Field(default_factory=list)


# ---- Attempts and results (FR-09 - FR-12) ---------------------------------


class Attempt(BaseModel):
    number: int
    region_id: str
    outcome: Outcome
    reason: str | None = None  # exclusion reason for invalid_feed / uncertain
    t_start_ms: int
    t_end_ms: int
    travel_time_s: float | None = None
    response_time_s: float | None = None
    lateral_ft: float | None = None
    flagged: bool = False
    flag_reason: str | None = None


class RegionResult(BaseModel):
    region_id: str
    label: str
    scored: int
    successes: int
    success_rate: float | None  # None when below the sample minimum
    ci_low: float | None
    ci_high: float | None
    avg_travel_time_s: float | None
    sufficient: bool


class Exclusions(BaseModel):
    invalid_feed: int
    uncertain: int
    flagged: int


class Results(BaseModel):
    session_id: str
    drill_id: str
    drill_name: str
    drill_version: str
    analysis_version: str
    feed_method: FeedMethod
    published: bool
    total_attempts: int
    scored: int
    successes: int
    success_rate: float | None
    ci_low: float | None
    ci_high: float | None
    avg_response_time_s: float | None
    min_scored_per_region: int
    sufficient: bool
    regions: list[RegionResult]
    exclusions: Exclusions
    limitations: list[str]
    attempts: list[Attempt]
    track: TrackSummary
    attempts_source: Literal["simulated", "unavailable"] = "simulated"


# ---- Sessions ---------------------------------------------------------------

PIPELINE_STEPS = [
    "Upload video securely",
    "Detect court boundaries",
    "Track player & ball",
    "Evaluate each attempt",
    "Calculate coverage metrics",
]


class Session(BaseModel):
    id: str
    player_id: str
    drill_id: str
    drill_version: str
    feed_method: FeedMethod
    capture_started_at: str
    capture_ended_at: str
    status: SessionStatus
    step: int = 0  # index into PIPELINE_STEPS of the step in progress
    progress: float = 0.0  # 0-1
    model_id: str | None = None
    clip_id: str | None = None
    clip_size_mb: float | None = None
    upload_attempts: int = 0
    error: str | None = None
    scenario: Scenario = "normal"
    steps: list[str] = Field(default_factory=lambda: list(PIPELINE_STEPS))
    analysis: "AnalysisOptions | None" = None


class CreateSessionRequest(BaseModel):
    drill_id: str
    drill_version: str
    feed_method: FeedMethod
    capture_started_at: str
    capture_ended_at: str
    scenario: Scenario = "normal"


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Calibration(StrictInput):
    width: int = Field(gt=0, strict=True)
    height: int = Field(gt=0, strict=True)
    corners_px: list[tuple[float, float]] = Field(min_length=4, max_length=4)


class PlayerBox(StrictInput):
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)
    x2: float = Field(gt=0)
    y2: float = Field(gt=0)

    @model_validator(mode="after")
    def positive_area(self):
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Player boxes must have positive width and height.")
        return self


class AnalysisOptions(StrictInput):
    start_frame: int = Field(default=0, ge=0, strict=True)
    max_frames: int = Field(default=300, ge=1, le=1800, strict=True)
    sample_fps: float = Field(default=1, gt=0, le=10)
    selections: list[PlayerBox] = Field(default_factory=list, max_length=8)
    calibration: Calibration


class UploadRequest(StrictInput):
    model_id: str
    clip_id: str
    analysis: AnalysisOptions | None = None


class FlagRequest(BaseModel):
    reason: str
    note: str | None = None


class PublishedProfile(BaseModel):
    player_id: str
    version: int
    session_id: str
    drill_id: str
    drill_name: str
    analysis_version: str
    published_at: str
    success_rate: float | None
    scored: int
    regions: list[RegionResult]


class DebugSessionRequest(BaseModel):
    """Prototype-only: create a session already in a given state."""

    state: Literal["awaiting_upload", "processing", "completed", "failed", "published"]
    scenario: Scenario = "normal"
    drill_id: str = "lateral-prescribed"
