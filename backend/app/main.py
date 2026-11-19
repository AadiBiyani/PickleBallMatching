"""Prototype API for the record -> upload -> analysis flow.

Run:  uvicorn app.main:app --reload --port 8000   (from the backend/ folder)
Docs: http://localhost:8000/docs
"""

import threading
import uuid
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import clips, pipeline
from .drills import DRILLS, get_drill
from .schemas import (
    Clip,
    CourtPoint,
    CreateSessionRequest,
    DebugSessionRequest,
    Drill,
    FlagRequest,
    PublishedProfile,
    Results,
    Session,
    UploadRequest,
    VisionModelInfo,
)
from .store import DEMO_PLAYER_ID, store
from .vision import MODELS, get_model

app = FastAPI(title="PickleBall Matching - prototype API", version=pipeline.ANALYSIS_VERSION)

# Local prototype only: the Expo web dev server runs on a different port.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_or_404(session_id: str) -> Session:
    s = store.sessions.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found.")
    return s


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "analysis_version": pipeline.ANALYSIS_VERSION}


@app.get("/api/drills")
def list_drills() -> list[Drill]:
    return DRILLS


@app.get("/api/models")
def list_models() -> list[VisionModelInfo]:
    return [m.info() for m in MODELS.values()]


@app.get("/api/clips")
def list_clips() -> list[Clip]:
    return clips.list_clips()


@app.post("/api/sessions", status_code=201)
def create_session(req: CreateSessionRequest) -> Session:
    """FR-05: a finished recording becomes a session with its metadata."""
    drill = get_drill(req.drill_id)
    if drill is None or drill.version != req.drill_version:
        raise HTTPException(400, "Unknown drill or drill version.")
    s = Session(
        id=uuid.uuid4().hex[:12],
        player_id=DEMO_PLAYER_ID,
        status="awaiting_upload",
        **req.model_dump(),
    )
    with store.lock:
        store.sessions[s.id] = s
    return s


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> Session:
    return _session_or_404(session_id)


@app.post("/api/sessions/{session_id}/upload")
def upload(session_id: str, req: UploadRequest, background: BackgroundTasks) -> Session:
    """Dummy upload: sends a pre-recorded clip to the selected model.

    Retrying uses the same session ID (FR-07). A retry after a successful upload
    returns the current state instead of queueing a second analysis (NFR-04).
    """
    with store.lock:
        s = _session_or_404(session_id)
        if s.status != "awaiting_upload":
            return s
        model = get_model(req.model_id)
        if model is None:
            raise HTTPException(400, "Unknown vision model.")
        resolved = clips.resolve(req.clip_id)
        if resolved is None:
            raise HTTPException(400, "Unknown clip.")
        clip, path = resolved
        if model.requires_clip_file and path is None:
            raise HTTPException(400, f"{model.name} needs a real video clip, not the synthetic one.")
        if model.output_space == "image" and not clip.has_corners:
            raise HTTPException(
                400, f"No court corners are saved for {clip.name}. Add them to sample_clips/corners.json."
            )
        s = store.update(session_id, upload_attempts=s.upload_attempts + 1)
        if s.scenario == "upload_error" and s.upload_attempts == 1:
            raise HTTPException(
                503, "The connection dropped during upload. Your recording is still saved on this device."
            )
        store.update(session_id, status="uploaded", model_id=model.id, clip_id=clip.id, clip_size_mb=clip.size_mb)
        s = store.update(session_id, status="queued", step=1, progress=0.2, error=None)
    background.add_task(pipeline.run, session_id)
    return s


@app.get("/api/sessions/{session_id}/results")
def get_results(session_id: str) -> Results:
    s = _session_or_404(session_id)
    if s.status != "completed":
        raise HTTPException(409, f"Results are not ready (status: {s.status}).")
    return pipeline.build_results(session_id)


@app.get("/api/sessions/{session_id}/track")
def get_track(session_id: str) -> list[CourtPoint]:
    """Per-frame player points in the court evaluation harness's results.csv shape (FR-08)."""
    s = _session_or_404(session_id)
    if s.status != "completed":
        raise HTTPException(409, f"Tracking is not ready (status: {s.status}).")
    return store.track_points.get(session_id, [])


@app.post("/api/sessions/{session_id}/attempts/{number}/flag")
def flag_attempt(session_id: str, number: int, req: FlagRequest) -> Results:
    """SR-9: flagged attempts keep their prediction but leave the scored counts."""
    _session_or_404(session_id)
    with store.lock:
        attempts = store.attempts.get(session_id)
        if attempts is None:
            raise HTTPException(409, "Results are not ready.")
        for i, a in enumerate(attempts):
            if a.number == number:
                attempts[i] = a.model_copy(update={"flagged": True, "flag_reason": req.reason})
                break
        else:
            raise HTTPException(404, "Attempt not found.")
    return pipeline.build_results(session_id)


@app.post("/api/sessions/{session_id}/publish")
def publish(session_id: str) -> PublishedProfile:
    """FR-15: sufficient results become a new profile version; insufficient ones never replace it."""
    s = _session_or_404(session_id)
    results = pipeline.build_results(session_id)
    if results is None:
        raise HTTPException(409, "Results are not ready.")
    if not results.sufficient:
        raise HTTPException(409, "Not enough valid attempts to publish this assessment.")
    with store.lock:
        versions = store.profiles.setdefault(s.player_id, [])
        existing = next((p for p in versions if p.session_id == session_id), None)
        if existing:
            return existing
        profile = PublishedProfile(
            player_id=s.player_id,
            version=len(versions) + 1,
            session_id=s.id,
            drill_id=results.drill_id,
            drill_name=results.drill_name,
            analysis_version=results.analysis_version,
            published_at=_now(),
            success_rate=results.success_rate,
            scored=results.scored,
            regions=results.regions,
        )
        versions.append(profile)
        return profile


@app.get("/api/profile")
def get_profile() -> PublishedProfile | None:
    versions = store.profiles.get(DEMO_PLAYER_ID, [])
    return versions[-1] if versions else None


# ---- Prototype-only debug endpoints (power the in-app debug toggle) --------


@app.post("/api/debug/sessions", status_code=201)
def debug_session(req: DebugSessionRequest) -> Session:
    drill = get_drill(req.drill_id)
    if drill is None:
        raise HTTPException(400, "Unknown drill.")
    now = _now()
    scenario = "processing_error" if req.state == "failed" else req.scenario
    s = create_session(
        CreateSessionRequest(
            drill_id=drill.id,
            drill_version=drill.version,
            feed_method="human_feeder",
            capture_started_at=now,
            capture_ended_at=now,
            scenario=scenario,
        )
    )
    if req.state == "awaiting_upload":
        if scenario == "upload_error":
            # Opening the upload-error screen directly: the first (failing) attempt already happened.
            return store.update(s.id, upload_attempts=1)
        return s
    store.update(s.id, status="queued", model_id="simulated", clip_id="synthetic", upload_attempts=1)
    if req.state == "processing":
        threading.Thread(target=pipeline.run, args=(s.id,), daemon=True).start()
        return store.sessions[s.id]
    pipeline.run(s.id, step_delay_s=0)
    if req.state == "published":
        publish(s.id)
    return store.sessions[s.id]


@app.post("/api/debug/reset", status_code=204)
def debug_reset() -> None:
    store.reset()
