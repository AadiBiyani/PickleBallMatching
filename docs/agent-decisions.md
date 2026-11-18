# Agent Decisions Log

This is the running record of material design decisions made in human/agent conversations, as required by `docs/DEVELOPMENT.md` (§3, "Agent-assisted code"). Add new entries at the bottom. Minor agent help (spelling, editor completion) does not need an entry.

Each entry records the date, related issue or pull request, the decision, alternatives considered, rationale, and known consequences. "Decided by" separates choices the human author made from ones the agent proposed and the author accepted.

> **Status: DRAFT.** Entries AD-001 to AD-013 were drafted by the agent (Claude Code) from the session on the `logan/feature/no-issue-prototype-ui` branch. Logan must review, correct, and approve them before the pull request. Nothing here has been reviewed by the team yet.

---

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
