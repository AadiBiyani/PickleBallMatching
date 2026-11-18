# YOLO player-tracking implementation and evidence

## Scope and working plan

Source brief: `Player_Tracking_Context.md`; inspected alongside `AGENTS.md` and the project proposal/development plan. Starting branch was `main`, with no application code. Work is isolated on `aadi-yolo-player-tracking`, under `experiments/player-tracking-yolo/`; existing context and videos are preserved.

The user confirmed YOLO pose + ByteTrack as their model assignment. Nishaant's MediaPipe approach addresses the same tracking task; Liam owns the shared validation framework. Liam's contract and the team's Figma screens have not been supplied. Integration and Figma alignment remain pending.

1. Establish Python 3.12, pretrained YOLO26n pose, explicit ByteTrack, and a CLI run on supplied video.
2. Add explicit preview-box selection, persistent selected ID, ankle-midpoint positions, per-frame missing states, and JSON/CSV/annotations.
3. Test surrounding logic offline; add one serialized FastAPI worker and a thin browser flow.
4. Inspect real outputs and document reproducibility, limitations, and the adapter boundary for Liam.

The broader project includes React Native mobile capture, FastAPI, Celery/Redis, storage, coverage, and matching. This independent Python/browser experiment addresses image-space player position only, rather than replacing that architecture. Court calibration was deferred. No ball tracking, attempt classification, training, coverage/skill scoring, or competing validation framework is included.

The user subsequently requested support for all on-court players and confirmed **explicit selection of one or more players**, leaving spectators unselected. The implementation expanded to independent per-player trajectories and schema 1.1. This is the material change to the original single-player plan.

## Initial environment and inputs

- Apple Silicon macOS; system Python 3.9.6. Homebrew Python 3.12.15 is available and selected for the project virtual environment.
- `uv` is installed. PyTorch, Ultralytics, OpenCV, FastAPI, and pytest were initially absent from system Python. No system FFmpeg executable was found.
- The supplied short video `Screen Recording 2026-11-16 175406 (1).mp4` decoded as 1920×1080, 30 FPS, 890 frames (29.667 s). SHA-256: `b443df69b1d50ac7fa650155825e3b2f9972867f467a51f5a52d8b4f1c9fc6df`.
- The longer `Screen Recording 2026-11-16 175406.mp4` decoded as 2560×1600, 30 FPS, 7,493 frames (249.767 s). Only metadata and its opening frame were inspected; no full tracking run is claimed for it.
- Both opening images show broadcast doubles-match footage with spectators. This differs from the software development plan's prescribed fixed-camera individual drills; those capture conditions remain unvalidated here.
- Official Ultralytics docs confirm `yolo26n-pose.pt`, COCO ankle indices 15/16, original-image keypoint coordinates, and `model.track(..., persist=True, tracker=...)`. A new model/tracker instance will be used for each independent run.
- Videos, weights, runtime artifacts, and virtual environments are excluded from Git. No push or merge is authorized.

## Completed implementation

- Original-image preview boxes, mouse/keyboard selection of 1–8 people on one frame, and unchanged pixel coordinates when the preview is resized.
- First-frame matching requires IoU ≥0.5 with a lead >0.1 over alternatives. Duplicate selections mapping to one ID fail. Each ID then stays locked; new IDs are not silently substituted.
- Continuous stride-1 inference, fresh model/tracker per run, and one observation per player per processed frame. Statuses distinguish `ok`, `target_not_detected`, and `keypoints_unreliable`.
- Ankle midpoint requires both COCO ankles (15/16) to be finite, in-frame and above a configurable threshold (default 0.5). Missing positions are JSON null / empty CSV cells; each player's trail breaks independently on gaps.
- Decoder timestamps, documented frame-index/FPS fallback, and invalid-FPS rejection. Metadata records hashes, software/device, thresholds, selections, counts and timing scopes.
- JSON, CSV, metadata, annotated JPEGs and a frame manifest. Browser playback/scrubbing works; no encoded MP4/audio is produced.
- Actual FastAPI upload/preview/job/polling/download requests, generated IDs, strict validation, one serialized inference worker, and explicit incomplete output after fatal failures. The CLI uses the same core.
- Deterministic offline tests and a small sampling/export boundary for Liam. Full setup, contract and API details are in the [experiment README](../experiments/player-tracking-yolo/README.md).

## Environment and provenance

Validated on macOS 26.6.2 arm64 using Python 3.12.15. CUDA and MPS were unavailable in the inspected sandbox, so all recorded runs used CPU. No system FFmpeg executable was found; the frame viewer avoids an unverified encoding assumption.

Exact dependency versions are locked in `uv.lock`: Ultralytics 8.4.215, torch 2.15.0, torchvision 0.29.2, OpenCV 5.1.0.95, NumPy 2.5.5, FastAPI 0.163.2, Pydantic 2.14.3, Uvicorn 0.54.0, lap 0.5.14, python-multipart 0.0.34, pytest 9.2.0, httpx 0.28.1, Ruff 0.17.5. Optional browser checks used Playwright 1.65.2 and existing Chromium build 1255. Installed dependency/license notices are summarized in the README.

Official weights: https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n-pose.pt. Observed SHA-256: `eb3bb8268828aeaf515cec23a4bfafd793944a86fe9af94ba7823609c14522a9`. The download helper reported 2.596 s, excluding initial import/setup. Downloading is separate from run model-loading and processing timing.

## Actual validation results

| Check | Observed result |
| --- | --- |
| First real backend check | YOLO pose + ByteTrack ran for 30 consecutive frames. IDs 1, 2, 3 appeared throughout. Loop 2.323 s; loading 1.053 s. This checked model execution before selecting the provisional target. |
| CLI development window, frames 0–299 | Explicit near-left white-shirt selection: 300 usable / 300 observations, ID 1. Processing 11.571 s; loading 1.275 s; total-before-export 12.959 s. Final-frame overlay inspected. |
| Browser/API window, frames 600–889 | Four on-court players selected; spectator excluded. 290 frames, 1,160 observations: 612 usable (52.76%), 548 missing (47.24%), zero unreliable-ankle records in this run. Processing 11.206 s; warm-server model loading 0.037 s; total-before-export 11.638 s. |
| Per-player counts | Near-right black (`player_1`, ID 1): 290 usable. Near-left white (`player_2`, ID 2): 290 usable. Far-right black (`player_3`, ID 3) and far-left gray (`player_4`, ID 4): each 16 usable / 274 missing. |
| Browser controls | Real upload/preview/tracking requests; keyboard multi-selection; original boxes unchanged at 390px width; per-player table; playback advanced at least two frames; pause/final-frame scrub; real JSON download; no JS page errors or horizontal page overflow at tested sizes. |
| Offline tests | 37 passed. One dependency warning: Starlette TestClient recommends httpx2 instead of the installed httpx. Tests work; no warning suppression or migration was applied. |
| Lint, formatting and syntax | `ruff check .`, `ruff format --check --quiet .`, and `python -m compileall -q player_tracking` passed. |
| Existing checks/build | No pre-existing application tests, type checker, or frontend build existed on this branch. `uv sync` built/installed the Python package. Remote CI was not run. |

The later window is separated from the development window but belongs to the **same recording**, not an independent held-out evaluation dataset. Model size/thresholds/tracker settings remained at their defaults for that check; the multi-player feature was introduced after the first single-player smoke.

Visual inspection covered input/selection previews, development frame 299, multi-player frames 616 and 750, and the browser screenshot at frame 889. Near-side boxes and ankle proxies align with the intended people in those inspected images. At frame 616 both far-side people remain visible but the selected IDs are missing. At frame 750 detections on those players have new IDs 19 and 22; frame 889 shows ID 24 on the far-left player. This demonstrates **ID fragmentation** in this configuration. It does not quantify every wrong-player assignment or certify uninspected frames.

## Commands, failures and corrections

All experiment commands below ran from `experiments/player-tracking-yolo/`. The installed `player-tracker` command is equivalent to `.venv/bin/python -m player_tracking.cli`.

| Action | Actual outcome |
| --- | --- |
| Repo docs/status/remote inspection; `git switch -c aadi-yolo-player-tracking` | Team remote `https://github.com/AadiBiyani/PickleBallMatching` confirmed; feature branch created with approval. Existing context/videos preserved. |
| `uv python list --only-installed` | Sandbox cache denial; approved retry found Python 3.12.15. |
| `uv sync --python /opt/homebrew/bin/python3.12` | Environment, local package and dependencies installed; lockfile created. |
| `player-tracker prepare-model` | Official download succeeded; checksum above recorded. |
| CLI inspect/preview commands | Decoded metadata/candidates obtained from supplied footage, including preview frame 600. |
| CLI run with frame-0 white-shirt box and `--max-frames 300 --output runtime/smoke-development` | Completed; run artifacts listed below. |
| First core test suite | 21 passed. |
| First expanded API tests | 26 passed, 2 failed: test doubles passed a keyword-only `track` argument positionally. Fixed to `track=track`; 28 passed. |
| Multi-player and failure checks | 32 passed, then invalid-FPS/corrupt-export tests brought the final suite to 37 passing tests. |
| Ruff checks | Import ordering, dict style and shared test-log annotation issues corrected. Formatting check found unformatted files; formatter applied; final checks pass. |
| `player-tracker serve --port 8000` | Sandbox blocked local port binding; approved retry started FastAPI. Restarted after multi-player API changes. |
| `uv sync --group browser` | Installed optional Playwright/greenlet; app runtime stays separate. |
| Browser launch | Sandbox denied Chromium bootstrap permission; approved retry worked using cached Chromium. |
| `.venv/bin/python scripts/browser_smoke.py '../../Screen Recording 2026-11-16 175406 (1).mp4' --frame 600 --candidates 1 2 3 4 --max-frames 290` | Passed through actual model/API/browser, saved screenshots and observed response. |
| License metadata inspection | Initial one-liner had a quoting syntax error; heredoc retry succeeded. Draft python-multipart license corrected to Apache-2.0 from installed metadata. |
| Final review | Protected failed jobs against unreadable partial metadata exports leaving status stuck at `running`; regression test passes. An initial documentation patch used incompatible duplicate-path operations and was rejected before changes; corrected with a single update. |

## Local evidence artifacts

Paths are relative to `experiments/player-tracking-yolo/`. Inputs, weights, outputs and screenshots are ignored by Git.

- `runtime/backend-smoke/check.json`: initial 30-frame execution check.
- `runtime/smoke-development/3853ebd0707c4ddfaca6587ba86f076b/`: initial single-player run, earlier schema 1.0 before the user-approved multi-player change.
- `runtime/api/runs/b2cfeb75a83c43729b000e83c0d466a2/`: four-player schema 1.1 metadata, JSON/CSV, manifest and 290 annotated frames.
- `runtime/browser-evidence/browser-check.json`: observed browser checks and job metadata.
- `runtime/browser-evidence/downloaded-positions.json`: actual browser download.
- `runtime/browser-evidence/selection-mobile.png`, `results-mobile.png`, `results-desktop.png`: screenshots actually captured. Selection-mobile and results-desktop were visually inspected. These do not represent human review or a narrated walkthrough.

Use the README's exact setup/CLI/test/browser commands to reproduce. No IDE-agent screenshot or personal review was created by the agent. Test output can be captured in an IDE terminal for the team's submission.

## Liam handoff and remaining work

The proposed schema 1.1 keys observations by `(frame_index, player_id)`, with tracker IDs separate. The manifest has one entry per image; positions have one entry per player/frame. Preserve null/empty missing values and `complete=false` runs. Hashes, settings, FPS, stride, timestamps and reference-point metadata support comparison. `sample_validation_rows(..., player_id=...)` samples after tracking using explicit tolerance, retaining missing/unmatched results. No compatibility with Liam's unknown contract is asserted.

Before accuracy reporting: obtain Liam's contract; agree ankle midpoint versus MediaPipe heels/ground-contact definitions; collect approximately 20–30 matching manual reference points plus identity labels; use independent drill footage/setups; report error on usable labeled frames alongside missing/wrong-player counts. No physical-accuracy target, comprehensive identity-switch rate or labeled image error was measured. Far-side ID fragmentation needs investigation on development footage, followed by a fresh independent check. Court mapping, re-identification, ball tracking, training and production integration remain outside this prototype.

## Team completion checklist

- [ ] GitHub Project with owners, issues and acceptance criteria.
- [ ] Team review/adoption of [development-process.md](development-process.md), covering architecture, branches, reviews, merges and CI.
- [ ] All screens of the chosen Figma flow and its link. This module demonstrates real API calls but has no verified Figma alignment.
- [ ] Nontrivial code contributions from every member. This work is uncommitted pending user review; no push, merge, peer approval or team adoption is claimed.
- [ ] Narrated complete-prototype walkthrough, including bugs and limitations.
- [ ] Repository/process links, contribution table, personal reflections and GenAI statements.

Suggested contribution-table entry to review: **Aadi Biyani — pretrained YOLO pose + ByteTrack experiment, explicit multi-player selection, structured exports, local API/browser, offline tests and real-footage smoke evidence.** This is not a claim of an existing commit or human review.

Suggested GenAI statement: “I used Codex to inspect the project context, develop the YOLO pose/ByteTrack prototype, and write tests and documentation. The agent ran software checks and a real browser/model smoke test, which exposed far-side track-ID loss; those limitations are included in the evidence. I am responsible for reviewing the implementation and deciding how it integrates with the team's validation framework.” Aadi should edit this to match actual use and supply personal learning, time-savings and review experiences; those reflections must not be invented.

## Sources

- https://docs.ultralytics.com/tasks/pose/
- https://docs.ultralytics.com/modes/track/
- https://docs.ultralytics.com/quickstart/
- https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/trackers/bytetrack.yaml
- https://playwright.dev/python/docs/input
- https://playwright.dev/python/docs/downloads
