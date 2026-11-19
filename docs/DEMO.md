# Running the prototype demo

This guide builds and runs the **record → upload → analysis** prototype on a fresh clone, including the real vision models on real footage. Developers and agents should start here.

There are two ways to run it:

| | What you get | What you need |
| --- | --- | --- |
| **Simulated demo** | Every screen; the simulated tracker; a static court in place of the camera; a clip picker with a synthetic clip | Only this repo (steps 1 and 4) |
| **Full demo** | The demo clip playing in the camera screens, plus MediaPipe and YOLO analyzing it, with results in the Movement card | The **demo kit** from the team drive (steps 1–4) |

The footage is **not in git**. It shows identifiable players, so it is gitignored and shared as a demo kit through the team drive (SDP SYS-08). Without the kit, the app falls back to the simulated demo automatically; nothing breaks.

All commands run from the **repository root**. They were verified on Windows 10 with PowerShell 5.1, Node 24, Python 3.15 (backend), and `uv` 0.11. The macOS/Linux variants are given but **not yet verified**.

> **PowerShell:** start relative program paths with `.\`. Without it, `backend\.venv\…\python.exe` can be read as a module-qualified command name, and fails with "The module '…' could not be loaded".

## 1. Install the app (once per clone)

Requirements: Python 3.12 or newer for the backend, Node 24, and `uv` (https://docs.astral.sh/uv/) for the model environments.

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm install --prefix frontend
```

macOS/Linux (unverified): `python3 -m venv backend/.venv && backend/.venv/bin/python -m pip install -r backend/requirements.txt && npm install --prefix frontend`

## 2. Get the demo kit

Download **`pickleball-demo-kit-test-60s.zip`** (about 59 MB) from the team drive: **[team drive link: add when uploaded]**. Save it anywhere outside the repo, or in `demo-kit/`, which is gitignored.

The kit is one flat zip:

| File | What it is |
| --- | --- |
| `test-60s.mp4` | The demo "recording": the first 60 s of the team's NCPA men's doubles clip (Purdue 1 vs WashU 1). 2560×1600, 30 fps, 1,800 frames, fixed camera behind the near baseline |
| `corners.json` | That clip's four court corners (harness registry format), clicked with `experiments/player-tracking/mark_corners.py` |
| `test-60s.positions.json` | YOLO26n-pose + ByteTrack run on the near-right player in black (`player_1`), all 1,800 frames; replayed by the YOLO model |
| `exports.json` | Registers that YOLO run for the clip |
| `kit.json` | Manifest: SHA-256 and size of each file, provenance, the clip's corner note, and YOLO run details |
| `README.txt` | Short install note and privacy reminder |

The browser preview (`test-60s.preview.mp4`) is not in the kit; step 3 regenerates it.

## 3. Install the kit

```powershell
.\backend\.venv\Scripts\python.exe backend\scripts\setup_demo.py PATH\TO\pickleball-demo-kit-test-60s.zip --models
```

macOS/Linux (unverified): `backend/.venv/bin/python backend/scripts/setup_demo.py path/to/pickleball-demo-kit-test-60s.zip --models`

The script prints numbered steps:

1. Verifies every file against the SHA-256 in `kit.json`.
2. Copies the clip and YOLO run into `backend/sample_clips/`, and merges the clip's entries into `corners.json` and `exports.json`. It refuses to overwrite a different file or entry unless you pass `--force`.
3. Makes `test-60s.preview.mp4`, the H.264 copy the browser plays. Browsers cannot play the clip itself, which is MPEG-4 Part 2. If `imageio-ffmpeg` is missing, the script installs it into the backend's Python.
4. With `--models`, builds the two model environments. They must be separate, because each pins a different OpenCV build and YOLO needs Python 3.12:
   - **MediaPipe:** `experiments/vlm-harness/.venv`, created with Python 3.13 from `uv` (or pass `--mediapipe-python PATH`).
   - **YOLO:** `experiments/player-tracking-yolo/.venv`, via `uv sync --frozen --python 3.12`; about 0.94 GB.
5. Asks the backend what's ready, and should end with `Demo is ready.`

It is safe to re-run. Everything it writes is gitignored. Without `--models`, the app still runs, but MediaPipe and YOLO show as unavailable.

## 4. Run

**By hand:** two terminals, then open **http://localhost:8081** in a desktop browser. A wide window shows the phone frame with the debug panel beside it.

```powershell
# terminal 1: API on :8000
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# terminal 2: app on :8081
cd frontend
npx expo start --web
```

**Agents:** use the run skill, `.claude/skills/run-pickleball-matching/SKILL.md`. It has verified start/stop commands and a headless-browser driver (`driver.mjs smoke | flow | shot`).

## 5. What to show (demo walkthrough)

1. **Record New Drill** → choose a drill → **Continue** → tick the four checklist items → **Start Camera Setup**.
2. **Camera check:** the demo clip loops as the live preview. The checks are simulated; tap **Player visible** to turn the status green, then **Start Recording**.
3. **Countdown:** the clip holds its first frame. **Recording:** the clip plays from 0:00. Recording stops when the clip ends at 60 s, or press **Stop Recording**.
4. **Analysis model:** the clip is shown as the fixed recording. Pick **MediaPipe** or **YOLO**, or the Simulated tracker, then press **Upload & Analyze**. The real models take about 20–25 s.
5. **Results:** scroll to the **Movement** card. It shows the model's track on the near half of the court and the share of frames in each zone.
6. Use the **debug panel** to show the error and empty states (upload error, processing error, not enough data).

**What is real and what is simulated.** Real: the demo clip and the MediaPipe/YOLO positions, projected to court feet and zones by the shared court harness. Simulated: recording, upload, the camera checks, and the attempt outcomes and coverage percentages ("Return success by direction").

Reference results on this kit, from the issue #7 work:

| Model | Frames | Not visible | Tracking time |
| --- | --- | --- | --- |
| MediaPipe | 120 at 2 fps | 23 | 16.2 s |
| YOLO (replay) | 120 at 2 fps | 4 | 13.7 s |

Where both found the player, they differed by a median of 0.45 ft (ankle midpoint vs heel). MediaPipe follows any one pose, so it sometimes jumps between the four players. Lens distortion is not corrected, so positions near the middle of the near baseline are off by about 2 ft.

## Making a new kit

After saving a new clip, its corners, and optionally a YOLO run in `backend/sample_clips/` (see "Real models" and "Demo clip and camera playback" in `backend/README.md`):

```powershell
.\backend\.venv\Scripts\python.exe backend\scripts\make_demo_kit.py --clip test-60s.mp4 --out demo-kit --note "where the clip came from"
```

The script refuses to pack a YOLO run that was tracked on a different file than the clip. To use a clip other than `test-60s.mp4` as the app's demo clip, start the API with `PBM_DEMO_CLIP=<file>`.

## Where things live (all gitignored)

| Path | Contents | Made by |
| --- | --- | --- |
| `backend/sample_clips/` | Clips, `*.preview.mp4`, `corners.json`, `exports.json`, YOLO positions | `setup_demo.py` |
| `experiments/vlm-harness/.venv` | MediaPipe environment | `setup_demo.py --models` |
| `experiments/player-tracking-yolo/.venv` | YOLO environment | `setup_demo.py --models` |
| `experiments/player-tracking/models/` | MediaPipe pose model (5.5 MB), downloaded on first run | the harness |
| `backend/harness_runs/` | Each real-model run's `results.csv` and `summary.json` | the API |
| `demo-kit/` | Kits you build | `make_demo_kit.py` |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `The module 'backend' could not be loaded` (or `'experiments'`) | Prefix the path with `.\` (PowerShell). |
| Camera screens show a drawn court, not video | No `*.preview.mp4` for the demo clip. Re-run `setup_demo.py`, or `backend/scripts/make_preview.py`. |
| MediaPipe/YOLO greyed out: "Python environment is not set up" | Run `setup_demo.py … --models`. |
| `setup_demo.py`: "already has a different entry" or "exists with different contents" | You have your own corners or clip under the same name. Keep yours, or re-run with `--force` to take the kit's. |
| YOLO fails: "source SHA-256 does not match" | The clip in `sample_clips` is not the exact file YOLO tracked. Reinstall it from the kit. |
| Code changes don't show up | The run skill starts servers without reload; restart them. |
| Port 8000 in use | Something else is running on it; Aadi's standalone YOLO demo also defaults to 8000. Stop it first. |

## Privacy

The clip shows identifiable people. Share the kit only within the team, never commit it, and don't send it to remote models (e.g. a Gemini analyzer) unless everyone in it has agreed to third-party processing.
