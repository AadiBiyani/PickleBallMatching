# YOLO player-tracking implementation and evidence

## Scope and design

The experiment locates explicitly selected players using pretrained YOLO26n-pose
and ByteTrack. It provides a local CLI, FastAPI/browser demo, annotated frame
playback and structured position exports. The shared harness applies court
homography and assigns zones after tracking. Setup and contracts are documented
in the [YOLO README](../experiments/player-tracking-yolo/README.md) and
[harness README](../experiments/vlm-harness/README.md).

- Select 1–8 detected players on one preview frame using original-image boxes.
  Matching requires IoU ≥0.5 and a lead greater than 0.1 over alternatives.
- Process consecutive frames with a fresh tracker for each run. Lock selected
  IDs; do not silently switch to a new ID after a loss.
- Use the midpoint of COCO ankles 15/16 only when both are finite, in frame and
  above the configured confidence threshold (default 0.5).
- Preserve one observation per selected player per processed frame. Missing
  states distinguish `target_not_detected` from `keypoints_unreliable`; positions
  remain null and drawn trails break at gaps.
- Record source/model hashes, software, settings, selected IDs, timing and
  completion status. Fatal processing failures preserve explicitly incomplete runs.
- Keep model inference separate from evaluation sampling. Multi-player support
  extends the original single-player plan; evaluation selects one exported player.

No ball tracking, attempt scoring, coverage/skill estimation, model training or
partner matching is implemented. This is a local prototype, not the production
mobile/upload/storage architecture.

## Environment and inputs

Recorded checks used macOS 26.6.2 arm64, Python 3.12.15 and CPU execution.
CUDA/MPS were unavailable in the inspected sandbox. Exact dependencies are in
`experiments/player-tracking-yolo/uv.lock`; the environment included Ultralytics
8.4.215, torch 2.15.0, OpenCV 5.1.0.95, NumPy 2.5.5, pytest 9.2.0 and Ruff 0.17.5.
Browser checks used Playwright 1.65.2 and Chromium build 1255.

Official weights: [yolo26n-pose.pt](https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n-pose.pt).
Observed SHA-256: `eb3bb8268828aeaf515cec23a4bfafd793944a86fe9af94ba7823609c14522a9`.
Weights download separately from model loading and inference; there was no fine-tuning.

The short input, `Screen Recording 2026-11-16 175406 (1).mp4`, is 1920×1080,
30 FPS, 890 frames (29.667 s). SHA-256:
`b443df69b1d50ac7fa650155825e3b2f9972867f467a51f5a52d8b4f1c9fc6df`.
The longer supplied recording is 2560×1600, 30 FPS, 7,493 frames (249.767 s);
only its metadata and opening frame were inspected.

These are broadcast doubles clips with spectators, not the prescribed individual
drills. Separate windows from the short clip are not independent held-out data.
Videos, weights, virtual environments and generated results are gitignored.

## Recorded validation — 2026-11-18

| Check | Observed result |
| --- | --- |
| YOLO software tests | 37 passed; one existing Starlette/httpx deprecation warning |
| Shared harness tests | 36 passed, including 26 export/sampling cases and three factory regression cases |
| Isolated combination with MediaPipe PR #3 | 41 passed: the 36 harness tests plus PR #3's five adapter tests using stub detections |
| YOLO lint and formatting | Passed |
| Harness lint / new-file formatting | Passed using the commands in its README; existing shared layout preserved |
| Python compilation / `git diff --check` | Passed |
| Shared requirements compared with `origin/main` | Identical; YOLO uses its separate locked environment |

Run the software suites from their respective directories:

```sh
# experiments/player-tracking-yolo
.venv/bin/python -m pytest -q

# experiments/vlm-harness
../player-tracking-yolo/.venv/bin/python -m pytest -q
```

These tests use synthetic videos and observations, not model accuracy labels.
Independent geometry references include `(50,250)` pixels on a 200×440 rectangle
mapping to `(5,25)` feet / `kitchen_left`, and a second player at `(15,40)` feet /
`backcourt_right`. Tests cover source/sample indices, player selection, resizing,
both missing statuses, incomplete/invalid exports, wrong sources, CLI failures
and repeated-run preservation.

The compatibility copy used PR #3 head
`fc4b620e9cd3a194198671d74ea88b4974834ce4`, retaining its adapter, contact helper
and tests and adding its one-argument registration to the current factory.
It is saved under ignored `runtime/pr3-compat-review/`. This checks interface
compatibility without merging PR #3 or running real MediaPipe inference.
The 41-test result overlaps the 36-test result; it is not 41 additional cases.

Meaningful corrections during development included fixing test doubles that
passed keyword-only `track` positionally, preventing corrupt partial exports
from leaving API jobs stuck at `running`, and preserving other analyzers'
one-argument factory signature. Explicit lint configuration exposed import-order
issues; ordinary imports now precede the geometry-path setup.

## Real model and browser evidence

| Run | Observed result |
| --- | --- |
| Initial backend smoke | 30 consecutive frames; IDs 1, 2 and 3 appeared throughout |
| Single-player CLI, frames 0–299 | Near-left white-shirt player: 300 usable positions; 11.571 s processing |
| Four-player browser/API, frames 600–889 | 290 frames / 1,160 observations: 612 usable and 548 missing; 11.206 s processing |
| Fresh four-player integration run, same window | Same 612 usable / 548 missing counts; 11.37 s processing |

In both four-player runs, each near-side player had 290 usable estimates. Each
far-side player had 16 usable estimates followed by 274 missing observations.
Visual inspection at frames 616 and 750 showed the far-side people still visible
but their original IDs lost; later detections had new IDs. This demonstrates ID
fragmentation, not people necessarily leaving the image or a comprehensive
identity-error measurement.

The browser check exercised real upload/preview/tracking calls, keyboard
multi-selection, unchanged original boxes at 390px width, per-player results,
play/pause, final-frame scrubbing and JSON download. No page errors or horizontal
overflow were observed at the tested sizes. Screenshots were actually captured;
they do not establish human review. The browser was not rerun for the later
harness/factory changes; the API tests passed.

## Shared-harness integration — 2026-11-18

`harness/analyzers/yolo.py` validates complete schema-1.1 exports, source
SHA-256/dimensions, model identity, selected player and covered frame window.
It matches exact source frame indices after continuous tracking and scales
positions with resized frames. Missing estimates remain null. Shared geometry
and zone functions produce court results; `analyzer.json` preserves original
metadata and sampled missing reasons. Unique output directories prevent overwrites.

Other analyzer factories retain `factory(model)`. Only YOLO receives export
options. YOLO's locked environment remains separate from shared/MediaPipe
requirements to avoid overlapping OpenCV installations. Decisions and alternatives
are recorded in [agent-decisions.md](../docs/agent-decisions.md).

The real integration smoke used agent-estimated corners from frame 600:
`[[637,191],[1095,189],[1623,884],[150,897]]`, ordered far-left, far-right,
near-right, near-left. These **approximate** marks have occlusion/lens-distortion
limitations and are not reviewed calibration or accuracy ground truth. The
registry and output summaries retain that annotation.

At 1 FPS over `[600,890)`, each evaluation sampled frames 600, 630, …, 870.
Both near players retained all ten positions. The tested far player retained one
point and nine `not_visible` samples. Native and 960-pixel long-side evaluations
of the same player produced identical court coordinates (maximum difference
0.0 ft). No labels were supplied, so accuracy/error metrics remained unavailable.

Real CLI reproduction, from `experiments/vlm-harness`, using the saved local run:

```sh
../player-tracking-yolo/.venv/bin/python -m harness.run \
  '../../Screen Recording 2026-11-16 175406 (1).mp4' \
  --analyzer yolo:yolo26n-pose \
  --positions ../player-tracking-yolo/runtime/shared-harness-smoke/d3a4e1544aab4ff8acb0b067d24ae284/positions.json \
  --player-id player_2 \
  --corners ../player-tracking-yolo/runtime/shared-harness-smoke/approximate-corners.json \
  --start-frame 600 --stop-frame 890 --fps 1 \
  --output ../player-tracking-yolo/runtime/shared-harness-smoke/cli-evaluation
```

This command exited 0 and wrote CSV, summary and provenance. A repeat after the
factory changes also succeeded with output under `runtime/shared-harness-smoke/pr3-followup`.
The CLI's `missing 0` without reference labels counts missing *labeled* positions;
tracking availability is retained in observation rows and run metadata.

## Local evidence artifacts

Paths below are relative to `experiments/player-tracking-yolo/` and remain ignored:

- `runtime/smoke-development/3853ebd0707c4ddfaca6587ba86f076b/`: early single-player run.
- `runtime/api/runs/b2cfeb75a83c43729b000e83c0d466a2/`: browser/API four-player run.
- `runtime/browser-evidence/`: browser-check JSON, downloaded positions and mobile/desktop screenshots.
- `runtime/shared-harness-smoke/d3a4e1544aab4ff8acb0b067d24ae284/`: fresh integration tracking run.
- `runtime/shared-harness-smoke/approximate-corners.json` and `validation.json`: calibration annotation and integration assertions/output paths.

## Remaining limitations

- Ankle midpoint is above the floor and differs from a heel or measured ground
  contact. Agree reference definitions before comparing physical position errors.
- Far-side ID fragmentation remains; automatic re-identification is not implemented.
- No independent drill/reference-label set was evaluated, so physical accuracy,
  wrong-player frequency and comprehensive identity-switch rates remain unmeasured.
- Variable-frame-rate alignment remains unvalidated. The tracking export records
  decoder timestamps or its documented FPS fallback; harness labels use frame/FPS.
- Harness evaluation is one player per run, and zones cover only the near half.
  A visible far-half point is `out_of_court`, not `not_visible`.
- Logan's shared model-selection/calibration/results UI remains separate work.
  Remote CI and real MediaPipe inference were not part of these recorded checks.
