# Project brief

A short summary of `docs/project-proposal.md` for day-to-day work. The proposal is the source. If this file disagrees with it, the proposal wins.

## Problem and users

Pickleball players have ratings and video analysis tools, but nothing that recommends a doubles partner from measured, direction-specific court coverage. The project tests whether individual drill measurements add useful information beyond skill ratings.

- **Primary users:** collegiate and recreational doubles players.
- **Secondary:** captains and coaches, as optional advisers. They are not required operators, and there is no roster-management workflow.
- **Skeptics:** players who distrust automated selection. They need visible evidence, review options, and control over the final choice.

## End-to-end flow

1. **Prepare.** The player signs in, picks a drill, and sets the phone on a tripod. Live camera checks block recording until the setup passes.
2. **Record and upload.** A human feeder or ball machine runs the drill. The app uploads to private storage through a temporary signed URL. A failed upload retries under the same session ID.
3. **Analyze.** A background worker calibrates the court, tracks the player and the ball, and classifies each attempt. Anything it cannot observe confidently is marked uncertain.
4. **Store.** Attempt outcomes, confidence values, coverage measurements, and clip references are saved. Results are versioned by drill version and analysis version.
5. **Review.** The player inspects results and evidence clips, flags questionable attempts, or repeats a drill.
6. **Recommend.** The app requests ranked partner recommendations with explanations.

The team calls steps 1-4, drill recording to coverage profile, **Flow 1**. It is the current prototyping target.

## Drills and measurements

Candidate drills: predictable lateral feeds, unpredictable lateral feeds, and forehand/backhand target returns. The starting pilot protocol is about 20 valid feeds per drill, balanced across directions, on two separate sessions.

| Measurement | Definition |
| --- | --- |
| Directional movement | Displacement and travel time in court coordinates, grouped by direction |
| Response-time proxy | Time from a visible feed event to first detected movement. Not a clinical reaction time |
| Return success | Successful returns divided by confidently scored valid feeds, by direction or shot type |
| Court coverage | Estimated return success per tested court region and time window, from defined starting positions |

**A successful attempt:** the player returns the ball over the net and its first landing is inside the drill's defined opposing-court area. Confident misses, net failures, and out-of-bounds returns are failures. Invalid feeds and uncertain outcomes leave both the numerator and the denominator, and their reasons are shown. Untested regions are unknown, not failures.

Return proportions are reported with sample counts, exclusions, and 95% Wilson intervals.

## Matching

Filter first: registered candidates with enough comparable drill data who pass the requester's hard filters, such as distance and skill range. Then rank:

```
pair score = wC * C + wS * S + wP * P      (weights nonnegative, sum to 1)
```

- `C`: combined coverage. The initial proxy averages the higher of the two players' return-success values across comparable region/time scenarios.
- `S`: compatibility with the requester's desired skill range.
- `P`: agreement with court-side preferences.

Self-reported play style is shown as context and has no numeric weight yet. Missing required coverage means no supported score. The score is not a win probability. Weights are tuned on pilot data and frozen before held-out evaluation. The comparison baseline is skill-only matching on the same candidate pool.

## Planned architecture

Client-server. The matching engine starts as a module inside the backend.

| Layer | Planned technology |
| --- | --- |
| Mobile app | React Native, TypeScript, VisionCamera, React Native SVG. Selected iPhones first, Android later |
| Backend API | Python, FastAPI, SQLAlchemy, Alembic |
| Background analysis | Celery workers with a Redis broker |
| Vision | OpenCV for court calibration and homography, MediaPipe Pose Landmarker as the first pose candidate, PyTorch for ball-model experiments, FFmpeg |
| Data | PostgreSQL with PostGIS, hosted on Supabase. Supabase Auth |
| Storage | Private Amazon S3 bucket with temporary signed URLs |
| Hosting | Amazon EC2. GPU instances only if the turnaround target needs them |
| Tooling | Docker Compose, GitHub Actions, pytest, Jest, CVAT for labeling |

Homography maps points on the court plane only: ground-contact positions and ball landing spots. A ball in the air needs separate trajectory analysis.

## Evaluation targets (provisional)

| Area | Initial target |
| --- | --- |
| Court mapping | Mean ground-position error of 0.30 m or less |
| Attempt scoring | Macro-F1 of 0.85 or more while retaining at least 80% of valid feeds |
| Turnaround | Results about one minute after recording ends, upload included |
| Matching usefulness | Coverage-based ranking compared with a skill-only baseline, using paired drills and player feedback |

The pilot group is roughly 8-12 consenting players. Train, validation, and test data are split by player and session. Outcome labels are settled by two reviewers. Pretrained models are benchmarked before any fine-tuning.

## Not in the MVP

Full-match analysis, live coaching or line calls, offline analysis, messaging, court booking, payments, and tournament management.

## Prototype status

As of 2026-11-16. Check the branches for the current state.

| Branch | Experiment | Supports |
| --- | --- | --- |
| `aadi-drill-results-summary` | `experiments/drill-results/`: browser demo of attempt scoring on synthetic sessions. TypeScript, Vite, Vitest, Playwright | FR-10, FR-12 |
| `nishaant-player-tracking` | `experiments/player-tracking/`: heel tracking with MediaPipe plus a four-corner homography. Writes positions in court feet. Python 3.12 | FR-08 |
| `liam-test-harness` | `experiments/vlm-harness/`: planned, see `docs/vlm-harness-notes.md` | FR-08, FR-09 evaluation |

Court coordinates used by player-tracking: feet, origin at the far-left outside corner as seen by the camera, `x` from 0 to 20 toward the right sideline, `y` from 0 to 44 toward the near baseline, net at `y = 22`, kitchen lines at `y = 15` and `y = 29`.
