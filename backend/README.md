# Backend (prototype API)

> **Running the demo on a new machine?** Start with [`docs/DEMO.md`](../docs/DEMO.md). It covers installing the app, the demo kit (footage, corners, and YOLO run, which aren't in git), and setting up the model environments with `scripts/setup_demo.py`.

FastAPI service for the record → upload → analysis flow. Recording, upload, and attempt scoring are simulated. Player tracking follows the team's **court evaluation harness** (`experiments/vlm-harness/` on `nishaant/experiment/no-issue-court-eval-harness`). Frames are sampled from the chosen pre-recorded clip, and the selected model returns one image point per frame. The backend then maps each point to court feet and a zone exactly as the harness does.

## Run (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

Tests: `.\.venv\Scripts\python.exe -m pytest -q`. They include the SDP's FR-10 fixture, FR-07 retry under the same session ID, FR-15 publish rules, and the court evaluation harness's zone and homography cases.

## Tracking contract

Feet are the project's unit for positions and distances. **Court feet:** the origin is the far-left outside corner, `x` runs 0–20 ft toward the right sideline, `y` runs 0–44 ft toward the near baseline, and the net is at `y = 22`. This is the court evaluation harness's frame. Metres appear only when checking NFR-06 (0.30 m ≈ 0.98 ft).

1. **The model returns one point per frame:** `locate(frames) -> [LocatedPoint(frame_index, x_px, y_px, x_ft, y_ft)]`, in one of two forms, declared by the model's `output_space`:
   - **`"court"` (the expected default):** the model reports `x_ft`/`y_ft` itself. No corners are needed in the backend.
   - **`"image"` (court evaluation harness style):** the model reports `x_px`/`y_px` in the pixels of the frame it was shown, with the origin at the top-left. It never sees the court corners. The backend maps the point to feet using the clip's four saved corners, clicked in the order far-left, far-right, near-right, near-left.
   - When the player isn't visible, return the frame with every coordinate `None`. Don't drop it (NFR-06).
   - If a model reports both feet and pixels, the feet are used and the pixels are kept for reference.
2. **The model never picks the zone.** The backend derives it from the feet.
3. **The zone comes from the feet** (`app/court.py`, the same rules as the harness's `contract.py`):
   - On the near half: `kitchen_*` covers `y` 22–29, `transition_*` 29–36.5, and `backcourt_*` 36.5–44. Left and right are split at `x = 10`, as seen in the image.
   - Anything outside the near half is `out_of_court`.
   - A frame with no point is `not_visible`.
4. **Output:** `GET /api/sessions/{id}/track` returns one row per sampled frame (`frame_index, time_s, x_px, y_px, x_ft, y_ft, zone`), the same columns as the harness's `results.csv` minus the label fields.

`app/court.py` solves the homography in pure Python, so the API doesn't need OpenCV. `tests/test_court.py` repeats the harness's zone and homography test cases. A one-off comparison against the harness's OpenCV `perspective.py` gave identical results for points on the court (within 1e-5 ft).

## Real models (MediaPipe, YOLO) through the court harness

MediaPipe and YOLO each need their own Python environment: they pin different OpenCV distributions, and YOLO is locked to Python 3.12. So the backend never imports them. For these models it runs the court evaluation harness as a subprocess with that model's interpreter, from `experiments/vlm-harness/`:

```
<model python> -m harness.run <clip> --analyzer <spec> --corners sample_clips/corners.json --fps <n> --output harness_runs/<session> [model args]
```

It then reads the run's `results.csv`, which is already in court feet with the harness's zones. The run folder is kept under `backend/harness_runs/`, which is gitignored, and is listed in the results as `track.harness_run`. A model whose environment is missing shows as unavailable in the app, with the reason.

| Model | Environment the backend looks for | Notes |
| --- | --- | --- |
| `mediapipe` | `experiments/vlm-harness/.venv` | Runs live. Samples 2 fps; heel point, one pose per frame |
| `yolo` | `experiments/player-tracking-yolo/.venv` | Replays a completed tracking export registered in `sample_clips/exports.json` |

Set `PBM_MEDIAPIPE_PYTHON` or `PBM_YOLO_PYTHON` to use an interpreter elsewhere.

**MediaPipe setup.** This was verified on Windows with Python 3.13.12; the harness README asks for Python 3.9 or newer. Run it from the repository root. The first line uses `uv` to find an installed Python 3.13; run `uv python install 3.13` first if you don't have one.

```powershell
& (uv python find 3.13) -m venv experiments\vlm-harness\.venv
.\experiments\vlm-harness\.venv\Scripts\python.exe -m pip install -r experiments\vlm-harness\requirements.txt
```

In PowerShell, start a relative program path with `.\`. Without it, `experiments\…\python.exe` is read as a module-qualified command, and PowerShell fails with "The module 'experiments' could not be loaded".

The first MediaPipe run downloads `pose_landmarker_lite.task` (5.5 MB) into `experiments/player-tracking/models/`, which is gitignored.

**YOLO setup.** Verified on Windows with `uv` 0.11.2, which fetched Python 3.12.13. The environment is about 0.94 GB. See also `experiments/player-tracking-yolo/README.md`. From the repository root:

```powershell
cd experiments\player-tracking-yolo
uv sync --frozen --python 3.12
.\.venv\Scripts\player-tracker.exe prepare-model
.\.venv\Scripts\player-tracker.exe preview ..\..\backend\sample_clips\YOUR_CLIP.mp4 --frame 0 --output runtime\preview
```

1. In `runtime\preview\preview.json`, choose the candidate box of the player to follow. `preview.jpg` doesn't draw the boxes, so match them by their pixel coordinates.
2. Track that player, passing the box's x1 y1 x2 y2:

   ```powershell
   .\.venv\Scripts\player-tracker.exe run ..\..\backend\sample_clips\YOUR_CLIP.mp4 --frame 0 --max-frames 1800 --bbox X1 Y1 X2 Y2 --output runtime\YOUR_RUN
   ```

3. Copy the run's `positions.json` (under `runtime\YOUR_RUN\<id>\`) into `backend/sample_clips/`.
4. Register it in `backend/sample_clips/exports.json`. See `exports.example.json` for the shape: the file, `player_id` (`player_1` for the first selected box), and the tracked `start_frame`/`stop_frame` window.

The harness checks that the export's SHA-256 matches the clip, so register the export against the exact file that was tracked.

**Clips.** Every clip analyzed by a harness model needs its corners in `sample_clips/corners.json`. You can create them with the harness's corner tool, which opens an OpenCV window:

```powershell
.\experiments\vlm-harness\.venv\Scripts\python.exe experiments\player-tracking\mark_corners.py backend\sample_clips\YOUR_CLIP.mp4 --registry backend\sample_clips\corners.json
```

## Demo clip and camera playback

The prototype uses one fixed demo clip as its "recording": `sample_clips/test-60s.mp4`. Set `PBM_DEMO_CLIP` to use a different file.

- **Camera screens:** the app plays the clip in place of a live camera. The camera check loops it, the countdown holds the first frame, and recording plays it from the start; when the clip ends, recording stops.
- **Model screen:** the clip is shown as the recording instead of a clip picker.
- **Fallback:** if the file is missing, the app falls back to the clip picker and the static court illustration.

Clips written by OpenCV (such as a trimmed copy) use MPEG-4 Part 2 (`mp4v`), which browsers don't play. Make a browser-playable copy once per clip:

```powershell
python -m pip install imageio-ffmpeg
python backend\scripts\make_preview.py backend\sample_clips\test-60s.mp4
```

This writes `test-60s.preview.mp4`: H.264, 1280 px wide, with no audio. The result for `test-60s.mp4` was 3.7 MB, made in 6 s. Preview files are served at `/api/clips/{id}/preview` and are never listed or analyzed as clips. The original is untouched, so its corners and the YOLO export stay valid.

## Add your vision model

- **You already wrote a harness analyzer** (an object with `kind`, `model_id`, `is_remote`, and `locate(frames)`): wrap it in `app/vision/__init__.py`. Nothing else is needed. It is treated as a pixel model (`"image"`) unless you pass `output_space="court"` once it reports feet.

  ```python
  HarnessAnalyzer(YourAnalyzer(...), name="YOLO pose + ByteTrack", owner="Aadi", description="...", sample_fps=10)
  ```

- **Otherwise:** subclass `VisionModel` (`app/vision/base.py`), implement `locate()`, and register it.

Frames have the harness frame fields (`index`, `time_s`, `width_px`, `height_px`, `image`). For real clips, `image` is a BGR NumPy array. Each model sets `sample_fps`, the number of frames per second it is given (10 by default; 1 suits slow remote models). Set `is_remote = True` if frames leave the machine, and the app will show a consent warning (SYS-08).

## Clips and court corners

- Put pre-recorded clips (`.mp4` or `.mov`) in `sample_clips/`. They're gitignored.
- Clips analyzed by a pixel (`"image"`) model need their corners in `sample_clips/corners.json`, which is gitignored.
  - The format is the harness's corner registry (see `corners.example.json`), so a registry made with the harness's `mark_corners.py` can be copied over unchanged.
  - Without corners, such a clip can't be uploaded with a pixel model. Court models report feet themselves and don't need corners.
  - Corners for a different video size are refused, as in the harness.
- The built-in synthetic clip uses the example corners.
- Real clips need OpenCV for frame extraction: `pip install -r requirements-vision.txt`.
  - Vision dependencies (PyTorch, OpenCV, MediaPipe) may not have wheels for Python 3.15 yet.
  - The harnesses were tested on Python 3.12, and both harness test suites also pass on 3.13. If installation fails, create the venv with one of those, for example `uv venv --python 3.13`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/drills` | Versioned drill definitions (FR-03) |
| GET | `/api/models` | Registered vision models, with availability and clip requirements (prototype selector) |
| GET | `/api/clips` | Pre-recorded clips + synthetic clip, with saved corners and registered exports |
| GET | `/api/demo-clip` | The fixed demo clip (the prototype's "recording"), or null |
| GET | `/api/clips/{id}/preview` | Browser-playable copy of a clip for the camera screens (supports Range requests) |
| POST | `/api/sessions` | Create a session when a recording stops (FR-05) |
| POST | `/api/sessions/{id}/upload` | "Upload": send clip to model and queue analysis; safe to retry (FR-07, NFR-04) |
| GET | `/api/sessions/{id}` | Status: awaiting_upload → uploaded → queued → processing → completed / failed (FR-06) |
| GET | `/api/sessions/{id}/results` | Coverage results with exclusions and 95% Wilson ranges (FR-09–FR-12) |
| GET | `/api/sessions/{id}/track` | Per-frame court points in the harness's results.csv shape (FR-08) |
| POST | `/api/sessions/{id}/attempts/{n}/flag` | Flag a misclassified attempt (SR-9) |
| POST | `/api/sessions/{id}/publish` | Publish as a new profile version if sufficient (FR-15) |
| GET | `/api/profile` | Latest published profile |
| POST | `/api/debug/sessions`, `/api/debug/reset` | Prototype-only, used by the in-app debug panel |

Data is in memory and resets when the server restarts. There is no auth: one demo player owns everything.
