# Backend (prototype API)

FastAPI service for the record → upload → analysis flow. Recording, upload, and attempt scoring are simulated. The vision-model call is real: the selected model receives the chosen pre-recorded clip.

## Run (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

Tests: `.\.venv\Scripts\python.exe -m pytest -q`. They include the SDP's FR-10 fixture, FR-07 retry under the same session ID, and FR-15 publish rules.

## Add your vision model

1. Create `app/vision/<your_model>.py` with a class that subclasses `VisionModel` (see `app/vision/base.py`).
2. Implement `track(clip_path, drill, seed)`. It returns `TrackResult` points `{t_ms, x_m, y_m, confidence}` in court metres.
   - Frames with no detection must be returned with `x_m = y_m = None`, not dropped (NFR-06).
   - Coordinate convention (provisional, please confirm): origin at the assessed player's baseline, left sideline as seen from behind the baseline. x runs along the baseline (0–6.10 m); y runs toward the net (0–6.71 m).
3. Register an instance in `app/vision/__init__.py`. The app's model selector lists it automatically.
4. Put test clips in `sample_clips/` (they're gitignored).

Heavy dependencies (PyTorch, OpenCV, MediaPipe) may not have wheels for Python 3.15 yet. If install fails, create the venv with Python 3.12 or 3.13 instead (for example, `uv venv --python 3.13`).

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/drills` | Versioned drill definitions (FR-03) |
| GET | `/api/models` | Registered vision models (prototype selector) |
| GET | `/api/clips` | Pre-recorded clips + synthetic clip |
| POST | `/api/sessions` | Create a session when a recording stops (FR-05) |
| POST | `/api/sessions/{id}/upload` | "Upload": send clip to model and queue analysis; safe to retry (FR-07, NFR-04) |
| GET | `/api/sessions/{id}` | Status: awaiting_upload → uploaded → queued → processing → completed / failed (FR-06) |
| GET | `/api/sessions/{id}/results` | Coverage results with exclusions and 95% Wilson ranges (FR-09–FR-12) |
| POST | `/api/sessions/{id}/attempts/{n}/flag` | Flag a misclassified attempt (SR-9) |
| POST | `/api/sessions/{id}/publish` | Publish as a new profile version if sufficient (FR-15) |
| GET | `/api/profile` | Latest published profile |
| POST | `/api/debug/sessions`, `/api/debug/reset` | Prototype-only, used by the in-app debug panel |

Data is in memory and resets when the server restarts. There is no auth: one demo player owns everything.
