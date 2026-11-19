# Agent-assisted decisions

## 2026-11-18 — Connect YOLO tracking to the shared court harness

- **Issue/PR:** no issue or PR created for this integration yet. The prerequisite harness entered `main` in PR #2 (`e22f8e5`). Work continues on the user's existing `aadi-yolo-player-tracking` branch, which predates the adopted naming convention; future branches follow `DEVELOPMENT.md`.
- **Human direction:** integrate the merged geometry/harness, preserving explicit player selection and continuous YOLO pose + ByteTrack tracking. The user approved approximate corners for a smoke test only.
- **Decision:** merge `origin/main` into the existing branch and register an adapter reading completed schema-1.1 exports. Keep the model, tracker, multi-player UI and native exports intact. Geometry and zones remain shared.
- **Alternatives:** running ByteTrack on sparse samples changes temporal behavior; re-running inference for every evaluation duplicates work; nearest-timestamp matching needs a tolerance and can choose a different frame. The adapter instead uses exact source indices retained by the harness sampler.
- **Contract:** one explicit player per evaluation, validated source SHA-256/dimensions/model/window and observations, resized points, preserved nulls, and a provenance file retaining missing reasons and ankle reference. This does not establish equivalence with heel/floor-contact labels.
- **Initial dependency approach (superseded below):** reuse the locked Python 3.12 YOLO environment and align shared OpenCV/pytest requirements with it. Review of MediaPipe PR #3 led to keeping the model environments separate instead; no new library was added.
- **Consequences:** trajectories can be evaluated repeatedly through common geometry. Near-half zone scope and one player per harness run remain. Shared UI wiring, measured accuracy, reference-point agreement and production packaging remain follow-ups. Experiment imports are temporary; product code should eventually move to the directories specified in `DEVELOPMENT.md`.
- **Approach changes:** exact-frame sampling replaces the proposed nearest-timestamp approach for this adapter. Unique directories prevent evaluations overwriting each other. The older process proposal now points to the adopted process.
- **Agent involvement:** Codex implemented adapter/sampling/CLI changes, tests and docs and ran local verification. Human diff review, teammate approval, remote CI and pushing this integration are not claimed.

Commands, outcomes, limitations and local evidence are in
[the YOLO notes](../doc/yolo-player-tracking.md#shared-harness-integration--2026-11-18).

## 2026-11-18 — Align the YOLO integration with MediaPipe PR #3

- **Issue/PR:** compatibility review of [PR #3](https://github.com/AadiBiyani/PickleBallMatching/pull/3) at `fc4b620e9cd3a194198671d74ea88b4974834ce4`, following integration commit `c13573c`.
- **Factory decision:** preserve ordinary `factory(model)` calls. Route `positions_path` and `player_id` only to YOLO, and reject them for other analyzers. Passing even null YOLO keywords to every factory would break PR #3's one-argument MediaPipe factory. Regression tests exercise that exact signature; an isolated combined copy also runs PR #3's actual adapter tests.
- **Dependency correction:** supersedes the earlier combined-environment approach. Restore shared `requirements.txt` to `main` and keep YOLO's locked environment separate. This avoids changing MediaPipe's dependency choices or installing overlapping OpenCV distributions together. A single environment would require a separately resolved and validated dependency set; it is not established here.
- **Formatting decision:** restore unchanged statements' existing layout and verify equal syntax trees. Add a local Ruff configuration matching YOLO's line length for new files; lint the modified shared files but avoid reformatting their surrounding code. No repository-wide formatting migration is implied.
- **Validation boundary:** PR #3's adapter and tests were exercised in an isolated, ignored copy. This verifies factory/point-contract compatibility with stub detections, not real MediaPipe installation or inference. Keep recorded local results distinct from remote CI and teammate review.

## 2026-11-18 — Resolve the merge with MediaPipe on main

- **Human direction:** resolve the conflicts after PR #3 merged, using `aadi/experiment/yolo-player-tracking` going forward. The user retains responsibility for pushing.
- **Merge:** bring `origin/main` at `7f20e0a` into the YOLO branch. Resolve the registry conflict by retaining `fake`, `mediapipe`, and `yolo`, preserving the one-argument MediaPipe factory and YOLO-only export options. Combine both README workflows and keep the environments separate. Incoming MediaPipe requirements remain unchanged.
- **Correction:** linting the combined harness found two E402 import-order errors in the incoming MediaPipe module. Move its ordinary relative imports above the existing path setup; keep the intentional delayed `contact` import. No inference behavior changes.
- **Validation:** the merged working tree passes 37 YOLO tests and 41 harness tests, including MediaPipe's stub-based tests. YOLO tests emit one existing FastAPI/Starlette TestClient deprecation warning. Real MediaPipe inference, Logan's UI, and remote CI are not validated by these tests. UI integration remains a separate planned change.

## 2026-11-18 — Prototype UI and API for the record → upload → analysis flow

- **Issue/PR:** no issue; the work was assigned when the team redistributed responsibilities for the prototype. Branch `logan/feature/no-issue-prototype-ui`; pull request pending.
- **Format:** this section was written on that branch before this log existed on `main`, and its entries are numbered AD-001 to AD-015 because the pull request description refers to those numbers. Each entry records the date, related work, who decided, the decision, alternatives, rationale, and consequences.

> **Status: DRAFT.** These entries were drafted by the agent (Claude Code) from the session on `logan/feature/no-issue-prototype-ui`. Logan must review, correct, and approve them before the pull request. Nothing here has been reviewed by the team yet.

### AD-001: SDP values override the Figma mockup

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui` branch; PR pending; no issue
- **Decided by:** Logan (human)
- **Decision:** The Figma prototype is for visualization only. Where it conflicts with `docs/software-development-plan.md` (numbers, limits, states, terminology), the app follows the SDP.
- **Alternatives considered:** Match the mockup exactly; resolve each conflict case by case.
- **Rationale:** The SDP is the graded, reviewed source of requirements. The mockup was drawn before several SDP values were settled.
- **Consequences:**
  - Several screens differ visibly from Figma (see AD-006 to AD-008).
  - The Figma file should be updated, or the differences explained in the prototype video.

### AD-002: Frontend stack is Expo (React Native + TypeScript), run in a browser

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; PR pending
- **Decided by:** Logan required that the prototype be "interactive on a Windows PC, not a real iOS implementation." The agent proposed the stack; Logan accepted.
- **Decision:** Build `frontend/` with Expo SDK 58 + Expo Router + TypeScript and run it in a desktop browser through react-native-web. On wide screens the app renders in a phone-sized frame.
- **Alternatives considered:**
  - A plain web app (Vite + React): faster to start, but its screens would have to be rewritten for the planned React Native app.
  - A native iOS build: needs a Mac/Xcode or EAS Build, and nobody on the team needs it for this assignment.
  - A Windows desktop app: no reuse toward the product.
- **Rationale:** The SDP's stack is React Native + TypeScript. The same screens can later be built for iOS, and nothing besides Node is needed on Windows.
- **Consequences:**
  - No real camera access. A live preview will need `react-native-vision-camera` and a development build later.
  - SDK 58 and React Native 0.88 differ from older docs: `StyleSheet.absoluteFillObject` is removed, `initialRouteName` is replaced, and web flex styles behave differently.
  - The Expo template's `frontend/AGENTS.md` is kept as component-specific agent guidance.

### AD-003: Recording, upload, and attempt scoring are simulated

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; `ref/UI.md`
- **Decided by:** Logan (human), per `ref/UI.md` and follow-up instructions
- **Decision:**
  - Camera screens show a static court illustration. The four setup checks are simulated: tapping a tile toggles it, and recording stays disabled until all four pass (FR-04 behavior).
  - Recording is a timer with a feed counter. Upload sends a pre-recorded clip that is already on the server.
  - Attempt outcomes are generated per session (seeded by session ID).
- **Alternatives considered:** Real capture with `expo-camera`/VisionCamera; real file upload to S3.
- **Rationale:** The assignment focuses on turning the Figma flow into code with at least one API call. Real capture is blocked on device support and on the vision work.
- **Consequences:**
  - Results are not real measurements. Every results screen lists this under its limitations.
  - The prototype video must say which parts are simulated.

### AD-004: Prototype-only vision-model selector, backed by a pluggable model registry

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; `ref/UI.md`
- **Decided by:**
  - Logan (human) decided that a selector appears before the upload step and that the API call passes a pre-recorded clip to the chosen model.
  - The agent designed the registry interface.
- **Decision:**
  - `backend/app/vision/` defines a `VisionModel` base class with `track(clip_path, drill, seed) -> TrackResult`, plus a registry that `GET /api/models` lists.
  - The upload endpoint calls the selected model.
  - A "Simulated tracker" is the only model registered so far.
- **Alternatives considered:**
  - Hard-code one model.
  - Have each teammate expose their own HTTP service.
  - Let the app call model code directly.
- **Rationale:** The three vision prototypes can be compared behind one endpoint without UI changes, and the winner can be kept as-is.
- **Consequences:**
  - Per `DEVELOPMENT.md`, model source and training belong in `models/` (or `experiments/` while exploratory). `backend/app/vision/` should hold only thin adapters that import from there.
  - Heavy dependencies (PyTorch, OpenCV, MediaPipe) may not support the Python 3.15 used by the backend venv. A Python 3.12/3.13 environment may be needed.
  - The selector screen will not ship in production.

### AD-005: Provisional court-coordinate convention for tracking output

> **Superseded by AD-014.** The backend now uses the court evaluation harness's contract. This entry is kept as the record of the original decision.

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; FR-08, NFR-06
- **Decided by:** Agent proposal; **needs confirmation from the vision team**
- **Decision:**
  - Track points are `{t_ms, x_m, y_m, confidence}` in metres.
  - The origin is the assessed player's baseline at the left sideline, as seen from behind the baseline. `x` runs along the baseline (0–6.10 m) and `y` toward the net (0–6.71 m).
  - Frames with no detection are returned with null coordinates, never dropped.
- **Alternatives considered:** Normalized 0–1 coordinates; a court-centre origin; pixel coordinates with the homography applied later.
- **Rationale:**
  - Metres match NFR-06's 0.30 m error target.
  - Returning undetected frames as nulls satisfies NFR-06's rule that missing estimates are not silently removed.
- **Consequences:**
  - All three vision prototypes must emit this format for a fair comparison.
  - The definition of a player's "ground position" (ankle midpoint, bounding-box bottom, etc.) is still undecided.

### AD-006: Report coverage per direction, not on a 3×3 grid

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; FR-11, FR-12; AD-001
- **Decided by:** Agent proposal under AD-001; accepted by Logan
- **Decision:** Results show return success per tested direction: wide left / center / wide right for the lateral drills, forehand / backhand for target returns. The mockup's 3×3 zone grid is not used.
- **Alternatives considered:** Keep the 3×3 grid; keep the grid but mark most cells as insufficient.
- **Rationale:**
  - With about 20 feeds per drill (proposal pilot protocol), nine cells cannot each reach FR-11's minimum of 5 scored attempts.
  - The proposal groups measurements by direction.
- **Consequences:**
  - The results visual differs from Figma 4.1.
  - Regions are defined per drill in `backend/app/drills.py`.

### AD-007: Drill set, feed count, and recording cap

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; FR-03; AD-001
- **Decided by:** Agent proposal under AD-001; accepted by Logan
- **Decision:**
  - The drills are the proposal's three candidates: Lateral Coverage – Prescribed, Lateral Coverage – Reactive, and Forehand/Backhand Target Returns. They replace the mockup's four.
  - Each drill has 20 feeds and a 60 s recording cap (the SDP benchmark), with automatic stop.
  - Drills are versioned (`v1.0`).
- **Alternatives considered:** The mockup's drills (Kitchen Dink Returns, Transition Zone Resets, Deep Lob Recovery); the mockup's 2+ minute recordings.
- **Rationale:**
  - The proposal's candidate drills and protocol.
  - The instructor's SDP feedback recommended time-limited recording to reduce variability.
- **Consequences:**
  - Final drill choices still depend on pilot testing and advice from experienced players.
  - Twenty feeds in 60 s means one feed every 3 s, which may be too fast for human feeders. Validate this during the pilot.

### AD-008: Scoring and exclusion rules shown in results

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; FR-09, FR-10, FR-11, FR-12, SR-9
- **Decided by:** Agent, implementing SDP/proposal rules; accepted by Logan
- **Decision:**
  - There are only two exclusion categories, invalid feed and uncertain. "Player out of frame" is one of the uncertain reasons.
  - Confidently observed misses count as failures.
  - Directions with fewer than 5 scored attempts show "Not enough data", never a low score.
  - Rates show 95% Wilson intervals.
  - Flagged attempts keep their original prediction but leave the scored counts.
  - The mockup's "Reliability: Medium" label is replaced by scored and excluded counts.
- **Alternatives considered:** A third "out of frame" category; a single reliability label.
- **Rationale:** These follow the SDP and proposal directly. A "reliability" label had no definition in either document.
- **Consequences:**
  - `backend/tests/test_scoring.py` encodes the SDP FR-10 fixture (6 successes, 2 failures, 1 invalid feed, 1 uncertain → 8 scored, 75%).
  - Whether flagged attempts should ever count again (for example after review) is still open.

### AD-009: Session lifecycle and idempotent upload retry

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; FR-05, FR-06, FR-07, NFR-04
- **Decided by:** Agent proposal; accepted by Logan
- **Decision:**
  - A session is created when recording stops. Its status moves `awaiting_upload` → `uploaded` → `queued` → `processing` → `completed` | `failed`.
  - Upload retries reuse the same session ID.
  - Repeating an upload after it succeeded returns the current state instead of queueing another analysis.
  - Repeating a publish returns the existing profile version.
- **Alternatives considered:** Create the session at upload time; let retries create new sessions.
- **Rationale:** FR-07 says retries must not create duplicates. NFR-04 says repeated deliveries must publish at most one result set.
- **Consequences:**
  - The app polls `GET /api/sessions/{id}` every second; a push mechanism may replace this later.
  - Insufficient or failed assessments never replace a published profile (FR-15).

### AD-010: Demo scenarios and debug tooling

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`
- **Decided by:**
  - Logan (human) required every screen to be reachable through a debug toggle.
  - The agent designed the mechanism.
- **Decision:**
  - Sessions carry a `scenario`: `normal`, `upload_error`, `processing_error`, or `insufficient_data`.
  - A debug panel (docked beside the phone frame on desktop) sets the scenario for the next recording and can jump to any screen.
  - Jumping uses the prototype-only endpoints `POST /api/debug/sessions` and `POST /api/debug/reset`.
  - Simulated exclusions are capped so that only `insufficient_data` can produce "Not enough data".
- **Alternatives considered:** Frontend-only mock data for debug jumps; separate hard-coded demo screens.
- **Rationale:** One source of truth (the backend), so debug jumps show real states. Error and empty screens can be shown on demand for the demo video.
- **Consequences:**
  - The debug endpoints and `scenario` field must be removed or blocked from deployed builds.
  - The panel can be hidden with `EXPO_PUBLIC_DEBUG=false`.

### AD-011: In-memory persistence, no authentication

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; SYS-01, SYS-08, NFR-03
- **Decided by:** Agent proposal for prototype scope; accepted by Logan
- **Decision:** The backend stores sessions and profiles in memory for a single demo player, with no authentication. CORS is open for local development.
- **Alternatives considered:** Supabase Auth + PostgreSQL now; SQLite.
- **Rationale:** These are outside the chosen user flow and would slow the prototype down.
- **Consequences:**
  - Data resets on restart.
  - SYS-01/SYS-08/NFR-03 (authentication, access control, consent) are not met yet. They must be implemented before any real participant data is used.

### AD-012: Repository layout follows DEVELOPMENT.md

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; `docs/DEVELOPMENT.md` §1
- **Decided by:** Logan (human)
- **Decision:** Rename the app folder from `mobile/` to `frontend/`. The backend stays in `backend/`.
- **Alternatives considered:** Keep `mobile/` and propose changing the process document instead.
- **Rationale:** Match the team's agreed monorepo structure.
- **Consequences:**
  - Some layout work remains:
    - Vision code from teammates should go into `models/` or `experiments/`.
    - Cross-component tests go into `tests/`.
    - No CI workflows exist yet under `.github/workflows/`.
  - The branch was renamed from `logan-ui` to `logan/feature/no-issue-prototype-ui` to follow the `<developer>/<type>/<issue>-<description>` convention. There is no issue because the work was assigned when the team redistributed responsibilities for the prototype.

### AD-013: Agent run skill and headless browser driver

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`
- **Decided by:** Logan requested it (`/run-skill-generator`); the agent designed it
- **Decision:** Commit `.claude/skills/run-pickleball-matching/` with a `SKILL.md` and `driver.mjs`. The driver uses `playwright-core` with the system's Chrome and has three modes:
  - `smoke`: API checks
  - `flow`: a full end-to-end browser walk-through with screenshots
  - `shot`: screenshot a single route
- **Alternatives considered:** Keep the driver as an untracked scratch script; add a full Playwright test suite under `tests/`.
- **Rationale:** Lets any teammate or agent start, demo, and regression-check the prototype on Windows quickly.
- **Consequences:**
  - Verified only on Windows PowerShell 5.1.
  - If CI adopts it, it should move to `tests/` (end-to-end) per `DEVELOPMENT.md`.
  - Running the smoke check exposed a real scenario bug (AD-010's exclusion cap), which is now fixed and covered by a backend regression test.

### AD-014: Adopt the court evaluation harness's tracking contract (supersedes AD-005)

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; `nishaant/experiment/no-issue-court-eval-harness` (commit `72f6ca4`); FR-08, NFR-06, SYS-08
- **Decided by:** Logan (human) chose to match the shared harness. The agent implemented the port.
- **Decision:**
  - The backend's vision interface is now the harness's: `locate(frames) -> LocatedPoint(frame_index, x_px, y_px)`, one image point per frame, or none.
  - The backend, not the model, maps points to court feet using the clip's four saved corners. The feet frame has its origin at the far-left outside corner, with x running 0–20 ft and y running 0–44 ft toward the near baseline.
  - The backend then derives the harness zone (`kitchen/transition/backcourt` × `left/right`, `out_of_court`, `not_visible`).
  - Corners use the harness registry format (`corners.json`).
  - `HarnessAnalyzer` registers any harness analyzer unchanged.
  - `GET /api/sessions/{id}/track` returns rows in the harness's `results.csv` shape.
  - Models declare `sample_fps` and `is_remote`. The app shows a consent warning for remote models.
- **Alternatives considered:**
  - Keep AD-005's metres convention and convert at the boundary.
  - Import the harness code directly from `experiments/`, which `DEVELOPMENT.md` discourages for product code.
  - Add OpenCV/NumPy to the API to reuse `perspective.py` as-is.
- **Rationale:**
  - Every vision branch (Nishaant's MediaPipe tracker, Liam's harness design notes, and the shared harness) already uses court feet with this origin.
  - With one contract, a model scores identically in the harness and in the app.
  - The pure-Python homography keeps the API's dependency set small.
- **Consequences:**
  - `app/court.py` is a copy of the harness's geometry. `tests/test_court.py` repeats the harness's zone and homography cases. A one-off comparison with `perspective.py` agreed to within 1e-5 ft for points on the court. The differences only grow, up to about 0.2 ft, for pixels far off the court near the horizon, because `perspective.py` casts corners to float32. When the harness graduates to `models/`, the backend should import from there instead.
  - Real clips now need saved corners and OpenCV (`requirements-vision.txt`).
  - The point used to locate a player (ankle midpoint, heel midpoint, or a point the model picks) is still not agreed, so position errors are not yet comparable across models.
  - `ANALYSIS_VERSION` was bumped to `proto-0.2`.

### AD-015: Feet as the default unit; models may report court feet directly

- **Date:** 2026-11-18
- **Related:** `logan/feature/no-issue-prototype-ui`; refines AD-014; FR-08, NFR-06
- **Decided by:** Logan (human) said to expect the vision models to eventually default to feet. The agent implemented the backend support.
- **Decision:**
  - Feet are the unit for all positions and distances. The attempt field `lateral_m` became `lateral_ft`.
  - Each model declares an `output_space`:
    - `"court"` (the default): the model reports `x_ft`/`y_ft` itself, and no corners are needed in the backend.
    - `"image"`: the model reports pixels, which the backend projects with the clip's saved corners as in AD-014.
  - A `LocatedPoint` may carry pixels, feet, or both. Feet win when both are present.
  - The backend always derives the zone.
  - Harness analyzers default to `"image"` until they declare feet.
  - The simulated model now reports feet.
- **Alternatives considered:**
  - Keep pixels as the only model output (AD-014 as written).
  - Require every model to report feet now. Aadi's YOLO tracker and the shared harness currently report pixels.
- **Rationale:** The team expects models to output court feet, as Nishaant's MediaPipe tracker already does. Supporting both forms keeps today's pixel-based harness analyzers working without blocking that move.
- **Consequences:**
  - A model that reports feet does its own court calibration, so its calibration error is not separable from its tracking error in the backend. The court evaluation harness scores only pixel models today and would need a matching option to score feet-reporting models fairly.
  - NFR-06's 0.30 m target is about 0.98 ft.
