# YOLO player tracking

A local, independent experiment for Personalized Doubles Partner Coordination. Upload a video, explicitly select **one or more on-court players**, run pretrained YOLO26n pose + ByteTrack, and inspect/download their image-space trajectories. Spectators can be left unselected. Ball tracking is not implemented.

## Run locally

From the repository root, with Python 3.12 and [uv](https://docs.astral.sh/uv/) installed:

```sh
cd experiments/player-tracking-yolo
uv sync --frozen --python 3.12
uv run player-tracker prepare-model
uv run player-tracker serve --port 8000
```

Open http://127.0.0.1:8000. API documentation is at http://127.0.0.1:8000/docs. The initial weight download needs internet; processing then stays local. `prepare-model` reports the checksum and download duration separately. CPU is the default. CLI/API accept `device=mps` only when PyTorch reports it available; CPU was validated here.

1. Upload a short video; the demo accepts MP4/MOV/AVI/MKV/WebM files OpenCV can decode, up to 600 MiB, 300 seconds, 240 FPS, and a 3840×2160 pixel budget.
2. Choose a starting frame where the intended players are detected. Check their numbered boxes or use the keyboard-accessible checkbox list. Candidate numbers are preview labels, not persistent identities. The selection text maps them to exported `player_1`, `player_2`, etc.
3. Start tracking. The default window is 300 consecutive frames, capped at 1,800; selecting a later starting frame does not generate predictions for earlier frames.
4. Inspect the per-player counts and annotated frame sequence. Play/pause and scrub through it. Download JSON, CSV, run metadata, and the frame manifest.

There is one inference worker for both previews and jobs, with at most eight outstanding inference tasks. Each run gets a fresh model/tracker. This is a loopback-only demo with no authentication, persistent job registry, cancellation, or automatic artifact cleanup. A server restart forgets video/job IDs, although files remain in `runtime/api/`. Keep the server local; it is not a deployed multi-user application. A browser reload requires another upload through this minimal UI; known job URLs still work until server restart.

## CLI

The CLI calls the same tracking function as the API. Coordinates are always original decoded image pixels, even when a preview is visually resized.

```sh
uv run player-tracker inspect ../../"Screen Recording 2026-11-16 175406 (1).mp4"
uv run player-tracker preview ../../"Screen Recording 2026-11-16 175406 (1).mp4" --frame 600 --output runtime/preview-check
```

Read `preview.jpg` and `preview.json`, then pass each chosen box as a repeated `--bbox`. This example selects the four on-court candidates in the supplied short clip at frame 600:

```sh
uv run player-tracker run ../../"Screen Recording 2026-11-16 175406 (1).mp4" \
  --frame 600 --max-frames 290 \
  --bbox 1340.47998046875 431.6657409667969 1574.8564453125 938.3992309570312 \
  --bbox 497.3127136230469 181.86996459960938 638.0219116210938 474.9153747558594 \
  --bbox 1023.2100219726562 110.83685302734375 1110.3416748046875 271.9643859863281 \
  --bbox 613.3551635742188 94.23065185546875 737.4307250976562 274.6238708496094
```

This command is provided for reproduction; the recorded four-player run was performed through the actual browser/API flow below. Paths and boxes are specific to the supplied file. Do not reuse its boxes for another recording.

## Output and shared-harness integration

Schema **1.1 is the YOLO experiment's internal export**. The [shared harness adapter](../vlm-harness/README.md#evaluate-a-yolo-tracking-run) translates it to `LocatedPoint`; team review of this integration remains pending. See `contracts.py` and `exports.py`. Each run produces:

- `positions.json`: metadata plus `frames`, a flat list containing **one observation for every selected player on every processed frame**, including missing positions. Key observations by `(frame_index, player_id)`.
- `positions.csv`: the same observations; bounding boxes flattened to `bbox_x1`, `bbox_y1`, `bbox_x2`, `bbox_y2`. Missing values are empty CSV fields, JSON `null`.
- `run.json`: source hash, original dimensions/FPS, model/weight checksum, tracker YAML/checksum, software/device, settings, selections and track IDs, timing, completion/error, and aggregate/per-player counts.
- `frames/00000600.jpg`, etc.: original-size annotated images. Selected boxes are green with player and track IDs; usable ankle estimates/trails are yellow. Unselected tracked detections remain gray. Text identifies missing states. No trail crosses a missing observation.
- `manifest.json`: **one entry per video frame**, with its timestamp, JPEG filename and each player's status. The browser viewer uses this sequence; no encoded MP4 or audio is produced. Playback follows timestamp spacing and waits for each image, so it can be slower than real time.

`processed_frame_count` counts images. `observation_count = processed_frame_count × selected_player_count`. Usable/missing totals count player observations; `per_player_counts` separates each trajectory. `complete=true` means the requested processing window finished, not that every position exists or is correct.

Each observation includes `player_id`, `frame_index`, `timestamp_s`, `selected_track_id`, `status`, `reason`, available bounding box, `image_x_px`, `image_y_px`, `point_source="ankle_midpoint"`, and ankle confidences. The reference point is the midpoint of COCO ankle landmarks 15/16, with both finite, in frame, and above the configured threshold (default 0.5). It is above the floor and is **not a measured foot-floor contact point**. It differs from the heel reference used by the MediaPipe approach; align that definition before comparing errors.

Statuses are `ok`, `target_not_detected`, or `keypoints_unreliable`. First-frame selection requires IoU ≥0.5 with the best tracked box and a lead greater than 0.1 over the second-best box. Duplicate selections mapping to one ID fail. IDs then remain locked; new IDs are not silently accepted as the same person. Stable IDs are not identity ground truth.

Frames are tracked continuously with stride 1. Monotonic nonnegative OpenCV decoder timestamps are used when available; otherwise **all** timestamps use frame index/FPS and metadata records the CFR assumption. Variable-frame-rate accuracy is unvalidated. The shared harness samples by **exact source frame index**, selects an explicit player, validates source identity/window, and rescales image coordinates if needed. Homography and zone assignment remain in the shared code. `sample_validation_rows` remains available for timestamp consumers, with explicit tolerance and no interpolation.

Fatal errors are job-level failures. Saved partial runs have `complete=false` and remain downloadable. No invented rows are added after a fatal failure. Model loading (including first lazy imports), processing (decode/inference/JPEG writes), and total-before-final-export are separately described in metadata; the initial weight download is outside those run timings.

## API

| Method/path | Purpose |
| --- | --- |
| `POST /api/videos` | Multipart `file`; returns generated video ID and decoded metadata |
| `GET /api/videos/{id}/preview?frame_index=600` | Original-pixel candidate boxes and preview image URL |
| `POST /api/jobs` | `{video_id, selections: [{frame_index, bbox: {x1,y1,x2,y2}}, …], config: {max_frames: 290}}`; returns 202 and job ID |
| `GET /api/jobs/{id}` | `queued`, `running`, `completed`, or `failed`, progress and metadata |
| `GET /api/jobs/{id}/artifacts/{name}` | Allowlisted JSON/CSV/manifest downloads |
| `GET /api/jobs/{id}/frames/{8-digit-frame}.jpg` | Annotated frame after completion/failure |

Clients cannot provide filesystem paths. All selections must use the same frame; 1–8 players are supported. Strict input models reject extra fields, invalid types, bounds and nonfinite values. Invalid uploads/selections return useful 422 errors, over-limit uploads 413, full queues 429, and unknown IDs/artifacts 404. A selection that fails the model's overlap rule becomes a failed job with the reason.

## Checks

```sh
uv run pytest -q
uv run ruff check .
uv run ruff format --check --quiet .
uv run python -m compileall -q player_tracking
```

The normal pytest suite uses tiny generated videos and deterministic fake detections, with **no model download, network calls, or real inference**. These are software checks, not model-accuracy evidence. No existing application test suite or type checker was present in the original repository.

For the opt-in real browser check, keep the server running in another terminal:

```sh
uv sync --frozen --group browser
uv run --group browser playwright install chromium
uv run --group browser python scripts/browser_smoke.py \
  ../../"Screen Recording 2026-11-16 175406 (1).mp4" \
  --frame 600 --candidates 1 2 3 4 --max-frames 290
```

Playwright is an optional development dependency, not part of the application runtime. Choose candidate numbers by inspecting the preview. It tests actual upload/preview/tracking HTTP calls, keyboard multi-selection, original coordinates at a narrow width, completed results, playback/scrubbing, and a real download. It saves screenshots and observed responses under `runtime/browser-evidence/`.

## Observed result and limits

On the supplied 1920×1080, 30 FPS broadcast screen recording, the first single-player CPU check processed frames 0–299 with 300 usable estimates in 11.57 seconds of processing. The later four-player browser check processed frames 600–889 in 11.21 seconds, producing 1,160 observations: **612 usable and 548 missing**. Both near-side players had 290/290 usable estimates; both far-side players had 16/290, then lost their original IDs. Later overlays show new IDs on those far-side players. This is a real limitation of the tested configuration, not proof that those people left the image.

The two windows belong to the same source recording. They are smoke checks, **not independent held-out evaluation data**. The longer recording was inspected, not processed end to end. Without reference labels, image error, physical accuracy and comprehensive identity-switch rate remain unmeasured. Shared court projection is now connected through the harness; its real-video smoke check uses explicitly approximate corners. Coverage, attempt scoring, ball tracking, training, re-identification, matching, production persistence and Figma matching remain outside this experiment.

Full evidence, versions, limitations and the team checklist: [`../../doc/yolo-player-tracking.md`](../../doc/yolo-player-tracking.md).

## Dependencies and model provenance

Exact versions and hashes for dependencies are in `uv.lock`; the validated environment used Python 3.12.15, Ultralytics 8.4.215, PyTorch 2.15.0, OpenCV 5.1.0.95, NumPy 2.5.5, FastAPI 0.163.2, Pydantic 2.14.3, Uvicorn 0.54.0, lap 0.5.14, pytest 9.2.0, and Ruff 0.17.5. Browser validation used Playwright 1.65.2 and Chromium build 1255.

Official weights: https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n-pose.pt

Exact model: **Ultralytics YOLO26n-pose**, the nano pose model pretrained on COCO keypoints, with no fine-tuning here. Official documentation: [YOLO26 overview](https://docs.ultralytics.com/models/yolo26/), [pose](https://docs.ultralytics.com/tasks/pose/), [tracking](https://docs.ultralytics.com/modes/track/), and [architecture YAML at installed v8.4.215](https://github.com/ultralytics/ultralytics/blob/v8.4.215/ultralytics/cfg/models/26/yolo26-pose.yaml). We explicitly supply ByteTrack configuration, retain tracker state across consecutive frames, and use ankle keypoints 15/16 from the 17-keypoint output. Defaults remain CPU, image size 640, detection confidence 0.1 and ankle confidence 0.5.

Observed SHA-256: `eb3bb8268828aeaf515cec23a4bfafd793944a86fe9af94ba7823609c14522a9`.

Ultralytics code/config and its model distribution use the project's AGPL-3.0/enterprise licensing model; see [Ultralytics licensing](https://www.ultralytics.com/license). The installed package reports AGPL-3.0. OpenCV and python-multipart use Apache-2.0; NumPy uses BSD-3-Clause with bundled 0BSD/MIT/Zlib/CC0 notices; FastAPI/Pydantic/pytest use MIT; Uvicorn BSD-3-Clause; lap BSD-2-Clause; Playwright Apache-2.0; Ruff MIT. The installed PyTorch distribution lists Apache-2.0 (including LLVM-exception), BSD-2/3-Clause, BSL-1.0, ISC, MIT, and Zlib notices. Consult the upstream distributions' full notices when sharing or integrating this experiment; no certification is claimed.

API details were checked against [Ultralytics pose](https://docs.ultralytics.com/tasks/pose/), [tracking](https://docs.ultralytics.com/modes/track/), and [Playwright actions](https://playwright.dev/python/docs/input) / [downloads](https://playwright.dev/python/docs/downloads).
