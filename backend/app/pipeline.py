"""Simulated background analysis (stands in for the Celery worker in SDP D-02).

The vision model call is real: the selected adapter receives the chosen clip.
Attempt classification and scoring inputs are simulated until the ball tracker
and attempt classifier exist.
"""

import random
import time
import zlib

from . import clips, scoring
from .drills import get_drill
from .schemas import Attempt, Drill, Results, Scenario, TrackSummary
from .store import store
from .vision import get_model

ANALYSIS_VERSION = "proto-0.1"
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
                lateral_m=round(rng.uniform(2.0, 2.8) if wide else rng.uniform(0.2, 0.8), 1),
            )
        )
    return attempts


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

    track = None
    for step in range(1, len(s.steps)):
        store.update(session_id, step=step, progress=step / len(s.steps))
        time.sleep(step_delay_s)
        if step == 2:
            if s.scenario == "processing_error":
                store.update(
                    session_id,
                    status="failed",
                    error=(
                        "We lost track of the player for most of the recording, so no attempts "
                        "could be scored. Re-record with your whole body and the court lines in frame."
                    ),
                )
                return
            try:
                track = model.track(clip_path, drill, seed_for(session_id))
            except Exception as exc:  # surface model crashes as an explicit failed status (FR-06)
                store.update(session_id, status="failed", error=f"Tracking model error: {exc}")
                return

    attempts = simulate_attempts(drill, seed_for(session_id), s.scenario)
    with store.lock:
        store.attempts[session_id] = attempts
        store.tracks[session_id] = TrackSummary(
            model_id=track.model_id,
            model_version=track.model_version,
            frames=len(track.points),
            missing_frames=sum(p.x_m is None for p in track.points),
        )
        store.update(session_id, status="completed", step=len(s.steps), progress=1.0)


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
