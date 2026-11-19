# Tracking UI integration

Branch: `aadi/feature/no-issue-tracking-ui-integration`, based on `main`
`b701a99` (YOLO PR #5) with Logan's UI at `f0b1754` merged separately.
No issue was created; this is the team's agreed prototype integration.

## Agreed stages and acceptance criteria

1. Connect Logan's session/model API to isolated YOLO and MediaPipe workers.
   Demonstrate a real YOLO run before expanding the interface.
2. Both real workers use the existing court harness for projection and zones.
   Preserve exact source indices, original pixels, player IDs, null observations,
   reasons and model/calibration provenance. YOLO tracks continuously first.
3. Add frame preview, four-corner calibration and multiple-player YOLO selection.
   MediaPipe remains explicitly a single detected pose without identity locking.
4. Show actual court-position playback and downloads. Real tracking does not
   generate attempts, return success, coverage ratings or publishable profiles.
   Keep Logan's simulated flow available and visibly labeled.
5. Test dispatch, geometry, validation, missing points, failure/retry/idempotency,
   multiple players and browser controls, then run both actual models locally.

## Implementation choices

- Preserve Logan's Expo 58/React Native components, navigation and palette:
  background `#F4F4F0`, cards `#FFFFFF`, text `#16181D`, primary `#1D4ED8`,
  court `#2C5E8C`, selection `#D6EF3C`. Use existing system typography and spacing.
  The frame/court is the main visual; labels and numeric coordinate inputs make
  calibration usable without a pointer. Keep controls stacked at phone widths.
- One frontend and session API. Child processes run under configured model
  interpreters; the API never imports PyTorch or MediaPipe. These are temporary
  prototype bridges to experiments, not the final production packaging.
- Start with the existing server clip picker; real phone recording and file
  upload are outside this integration. Neither simulated recording nor tracking
  establishes that an individual drill was performed.
- Each real job snapshots its clip, frame window, selections and calibration.
  The shared harness returns court feet and zones; models still return pixels.
- Preserve model-specific references: YOLO ankle midpoint versus MediaPipe heel
  point. Missing observations are never interpolated. Near-half zone scope stays
  unchanged; a far-half position is visible but classified `out_of_court`.
- MediaPipe's current first-pose behavior is not selected-player tracking.
  Reliable target association remains model work; the interface must state this.

## Validation record

- Before integration: Logan's backend suite, 34 passed using the existing YOLO
  interpreter; one existing Starlette TestClient deprecation warning.
- Foundation merge: resolved `.gitignore` and decision-log add/add conflicts by
  preserving both branches' entries. No raw clips or model artifacts committed.
- Checkpoint before synchronizing with main: 60 backend tests passed; Python
  lint passed; frontend type-check and two coordinate/trail tests passed.
  Expo lint completed with three baseline effect warnings (recording, attempt
  review and the existing data hook); web export completed. The latest small
  selection-control/label changes still need the final web-export rerun.
- Both actual model workers completed frames 600–889 of the supplied local
  short clip, using the previously approved approximate corners. YOLO produced
  40 sampled observations across four players (18 missing); MediaPipe produced
  ten pose observations (none missing). These are integration checks, not
  accuracy or identity-consistency evidence.
- Browser flows passed for both models: real inference, original-pixel player
  selection, playback, filtering, download controls, no horizontal overflow at
  390px, and no JavaScript page errors. Browser evidence is local under
  `backend/runtime/browser-evidence/`. The subsequent pointer-calibration test
  extension has not yet been run.
- Corrections during implementation: updated an old exact-fields API assertion
  for the extended tracking contract; fixed new React effect lint findings;
  installed the already-locked optional Playwright group after a missing-import
  failure; replaced web selection controls with native HTML button activation
  after Space did not toggle React Native Web checkboxes; renamed a pytest
  fixture that used the reserved name `request` and fixed its import ordering.
- npm reported three moderate dependency advisories during lint-tool setup;
  dependency-audit follow-up remains. No forced dependency upgrades were made.

## Teammate checkpoint

The user paused implementation to synchronize with the newly merged UI PR #6
and publish the current branch for team review. This is a working prototype
checkpoint, not a claim that every planned validation or documentation task is
finished. The existing backend README still describes Logan's original adapter
path; the real pipelines use `backend/worker.py` and the shared harness instead.

From the repository root, set up YOLO with its existing README, then create the
separate MediaPipe environment:

```sh
uv venv --python 3.12 experiments/vlm-harness/.venv
uv pip install --python experiments/vlm-harness/.venv/bin/python -r experiments/vlm-harness/requirements.txt
```

Place a local `.mp4` or `.mov` in `backend/sample_clips/` (ignored by Git). The
UI can mark corners interactively; saved registries are optional. Model weights
and clips are not included in the branch. MediaPipe downloads its model on
first inference; YOLO weights must be prepared using the YOLO README.

```sh
# Terminal 1, from backend/
../experiments/player-tracking-yolo/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
# Terminal 2, from frontend/
npm ci
EXPO_PUBLIC_API_URL=http://127.0.0.1:8001 npm run web
```

On Windows use each environment's `Scripts/python.exe` and set
`$env:EXPO_PUBLIC_API_URL='http://127.0.0.1:8001'` before `npm run web`.
`YOLO_PYTHON` and `MEDIAPIPE_PYTHON` can override worker interpreter paths.
Open the app, choose **Analyze a test clip**, select a model/clip, load a frame,
mark the four corners, and select YOLO players. MediaPipe has no identity lock.
Sessions are in memory and disappear when the API restarts. Run locally only.

Checks: from `backend/`, run the YOLO interpreter with `-m pytest -q`; from
`frontend/`, run `npm run typecheck`, `npm test`, `npm run lint`, and
`npm run build:web`. The node tests were exercised with Node 26.3.1. The optional
real-browser procedure is `backend/scripts/browser_smoke.py --help`; install
YOLO's locked `browser` dependency group first. It requires a calibrated local
clip and explicitly chosen candidate numbers.
