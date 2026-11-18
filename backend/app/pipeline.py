"""Background analysis (stands in for the Celery worker in SDP D-02).

Tracking: frames are sampled from the clip and the selected model returns one
point per frame, in court feet (the expected default) or in image pixels, which
this module maps to feet with the clip's saved corners as the team's court
evaluation harness does. The zone is always derived here (see `project_points`). Attempt classification and scoring inputs are
still simulated until the ball tracker and attempt classifier exist.
"""

import random
import time
import zlib
from collections import Counter
from collections.abc import Sequence

from . import clips, court, scoring
from .drills import get_drill
from .frames import ClipFrames, Frame, extract_frames, synthetic_frames
from .schemas import Attempt, CourtPoint, Drill, Results, Scenario, TrackSummary
from .store import store
from .vision import LocatedPoint, VisionModel, get_model

ANALYSIS_VERSION = "proto-0.2"  # 0.2: harness court contract (image points -> feet -> zone)
STEP_DELAY_S = 1.5
INSUFFICIENT_FEEDS = 9  # recording "stopped early" in the insufficient_data scenario

_INVALID_REASONS = [
    "Feed landed outside the drill's feed area",
    "Feed arrived before the player recovered to the start mark",
]
_UNCERTAIN_REASONS = [
    "Ball hidden behind player at contact",
    "Player out of frame - tracking lost for 1.2 s",
    "Landing spot not visible",
]


def seed_for(session_id: str) -> int:
    return zlib.crc32(session_id.encode())


def _region_order(drill: Drill, n: int, rng: random.Random) -> list[str]:
    ids = [r.id for r in drill.regions]
    order = [ids[i % len(ids)] for i in range(n)]  # balanced across directions
    if drill.stage == "reactive":
        rng.shuffle(order)
    return order


def simulate_attempts(drill: Drill, seed: int, scenario: Scenario) -> list[Attempt]:
    rng = random.Random(seed)
    n = INSUFFICIENT_FEEDS if scenario == "insufficient_data" else drill.feed_count
    skill = {r.id: rng.uniform(0.55, 0.9) for r in drill.regions}
    order = _region_order(drill, n, rng)
    # Never exclude so many that a direction falls below the sample minimum,
    # except in the insufficient_data scenario, which demonstrates that case.
    excludable = {
        r.id: n if scenario == "insufficient_data" else max(0, order.count(r.id) - scoring.MIN_SCORED_PER_REGION)
        for r in drill.regions
    }
    attempts = []
    for i, region in enumerate(order):
        roll = rng.random()
        reason = None
        if roll < 0.13 and excludable[region] == 0:
            roll = 1.0  # treat as a scorable attempt
        if roll < 0.13:
            excludable[region] -= 1
        if roll < 0.06:
            outcome, reason = "invalid_feed", rng.choice(_INVALID_REASONS)
        elif roll < 0.13:
            outcome, reason = "uncertain", rng.choice(_UNCERTAIN_REASONS)
        else:
            outcome = "success" if rng.random() < skill[region] else "failure"
        wide = region in ("left", "right")
        t0 = i * 3000
        attempts.append(
            Attempt(
                number=i + 1,
                region_id=region,
                outcome=outcome,
                reason=reason,
                t_start_ms=t0,
                t_end_ms=t0 + 2600,
                travel_time_s=round(rng.uniform(0.7, 1.1) + (0.3 if wide else 0), 2),
                response_time_s=round(rng.uniform(0.22, 0.48), 2),
                lateral_ft=round(rng.uniform(6.5, 9.0) if wide else rng.uniform(0.7, 2.5), 1),
            )
        )
    return attempts


def project_points(
    frames: Sequence[Frame], points: Sequence[LocatedPoint], corners_px: list[court.Point] | None
) -> list[CourtPoint]:
    """Turn model points into court-feet rows with zones.

    Feet reported by the model are used as-is. Image points are projected with
    the saved corners, as the harness's project_rows does. Every sampled frame
    gets a row; a frame the model skipped, or reported with no point, is
    `not_visible` with empty coordinates and is never dropped.
    """
    if len(points) != len(frames):
        raise ValueError(f"model returned {len(points)} points for {len(frames)} frames")
    homography = court.compute_homography(corners_px) if corners_px is not None else None
    by_index = {p.frame_index: p for p in points}
    rows = []
    for frame in frames:
        point = by_index.get(frame.index)
        x_px = y_px = x_ft = y_ft = None
        zone = court.NOT_VISIBLE
        if point is not None and point.has_pixels:
            x_px, y_px = float(point.x_px), float(point.y_px)
        if point is not None and point.has_feet:
            x_ft, y_ft = float(point.x_ft), float(point.y_ft)
        elif x_px is not None:
            if homography is None:
                raise court.CalibrationError("the model returned image points, but this clip has no saved corners")
            x_ft, y_ft = court.apply_homography(homography, (x_px, y_px))
        if x_ft is not None:
            zone = court.zone_from_feet(x_ft, y_ft)
            x_ft, y_ft = round(x_ft, 3), round(y_ft, 3)
        rows.append(
            CourtPoint(
                frame_index=frame.index, time_s=frame.time_s, x_px=x_px, y_px=y_px, x_ft=x_ft, y_ft=y_ft, zone=zone
            )
        )
    return rows


def sample_clip(model: VisionModel, clip_path, drill: Drill) -> ClipFrames:
    """Frames at the model's sampling rate. The synthetic clip lasts one feed interval per feed."""
    if clip_path is None:
        width, height = clips.SYNTHETIC_SIZE
        return synthetic_frames(drill.feed_count * 3.0, model.sample_fps, width, height)
    return extract_frames(clip_path, model.sample_fps)


def run(session_id: str, step_delay_s: float | None = None) -> None:
    if step_delay_s is None:
        step_delay_s = STEP_DELAY_S
    with store.lock:
        s = store.sessions.get(session_id)
        # Idempotent: a duplicate delivery of the job does nothing (NFR-04).
        if s is None or s.status != "queued":
            return
        s = store.update(session_id, status="processing", step=1, progress=0.2)

    drill = get_drill(s.drill_id)
    model = get_model(s.model_id or "")
    resolved = clips.resolve(s.clip_id or "")
    if drill is None or model is None or resolved is None:
        store.update(session_id, status="failed", error="Session configuration is invalid.")
        return
    _, clip_path = resolved

    sampled: ClipFrames | None = None
    corners_px: list[court.Point] | None = None
    rows: list[CourtPoint] = []
    for step in range(1, len(s.steps)):
        store.update(session_id, step=step, progress=step / len(s.steps))
        time.sleep(step_delay_s)
        try:
            if step == 1:  # Detect court boundaries: sample frames; image models need saved corners
                sampled = sample_clip(model, clip_path, drill)
                if model.output_space == "image":
                    corners_px = clips.corners_for(s.clip_id or "", sampled.native_width, sampled.native_height)
                    first = sampled.frames[0]
                    corners_px = court.scale_corners(
                        corners_px, (sampled.native_width, sampled.native_height), (first.width_px, first.height_px)
                    )
            elif step == 2:  # Track player: feet from court models, projected pixels from image models
                if s.scenario == "processing_error":
                    raise _Unanalyzable(
                        "We lost track of the player for most of the recording, so no attempts "
                        "could be scored. Re-record with your whole body and the court lines in frame."
                    )
                points = list(model.locate(sampled.frames))
                rows = project_points(sampled.frames, points, corners_px)
        except _Unanalyzable as exc:
            store.update(session_id, status="failed", error=str(exc))
            return
        except court.CalibrationError as exc:
            store.update(session_id, status="failed", error=f"Court calibration problem: {exc}")
            return
        except Exception as exc:  # surface model or video errors as an explicit failed status (FR-06)
            store.update(session_id, status="failed", error=f"Tracking model error: {exc}")
            return

    attempts = simulate_attempts(drill, seed_for(session_id), s.scenario)
    first = sampled.frames[0]
    with store.lock:
        store.attempts[session_id] = attempts
        store.track_points[session_id] = rows
        store.tracks[session_id] = TrackSummary(
            kind=model.kind,
            model_id=model.model_id,
            model_version=model.version,
            sample_fps=model.sample_fps,
            frame_size_px=(first.width_px, first.height_px),
            frames=len(rows),
            missing_frames=sum(r.zone == court.NOT_VISIBLE for r in rows),
            zone_counts=dict(Counter(r.zone for r in rows)),
        )
        store.update(session_id, status="completed", step=len(s.steps), progress=1.0)


class _Unanalyzable(Exception):
    """A recording that cannot be analyzed for a reason the player can fix."""


def build_results(session_id: str) -> Results | None:
    with store.lock:
        s = store.sessions.get(session_id)
        attempts = store.attempts.get(session_id)
        track = store.tracks.get(session_id)
        profiles = store.profiles.get(s.player_id, []) if s else []
    if s is None or attempts is None or track is None:
        return None
    drill = get_drill(s.drill_id)
    regions = scoring.region_results(attempts, drill.regions)
    totals = scoring.overall(attempts)
    sufficient = all(r.sufficient for r in regions)
    limitations = [
        "Measured from an individual drill; it does not show how two partners move together.",
        f"Directions with fewer than {scoring.MIN_SCORED_PER_REGION} scored attempts are marked "
        "insufficient instead of being scored.",
        "Ranges are 95% Wilson intervals; with about 6 attempts per direction they are wide.",
    ]
    if track.model_id == "simulated":
        limitations.append("Prototype: tracking and attempt outcomes are simulated.")
    if len(attempts) < drill.feed_count:
        limitations.insert(0, f"Only {len(attempts)} of {drill.feed_count} feeds were recorded.")
    return Results(
        session_id=s.id,
        drill_id=drill.id,
        drill_name=drill.name,
        drill_version=s.drill_version,
        analysis_version=ANALYSIS_VERSION,
        feed_method=s.feed_method,
        published=any(p.session_id == s.id for p in profiles),
        total_attempts=len(attempts),
        min_scored_per_region=scoring.MIN_SCORED_PER_REGION,
        sufficient=sufficient,
        regions=regions,
        exclusions=scoring.exclusions(attempts),
        limitations=limitations,
        attempts=attempts,
        track=track,
        **totals,
    )
