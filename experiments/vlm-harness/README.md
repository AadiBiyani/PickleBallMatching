# Court evaluation harness

One test video has its four court corners saved once. Each model then returns only the player's point in the frame it was shown. This harness maps that point through the same homography, assigns a court zone, and scores both against a label file.

Registered analyzers are `fake`, `mediapipe`, and `yolo`. MediaPipe returns a heel point from each sampled image. YOLO consumes a completed continuous tracking export from [player-tracking-yolo](../player-tracking-yolo/README.md). Gemini still needs an adapter.

## Setup

From this directory, with Python 3.9 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For YOLO, use the separate **Python 3.12** environment in `../player-tracking-yolo/.venv`. From that experiment, run `uv sync --frozen --python 3.12` first. Run the harness with that interpreter as shown below; **do not also install this directory's requirements into the YOLO environment**. The export adapter downloads no model or dependency.

The harness requirements include MediaPipe from merged PR #3 and retain its `opencv-contrib-python` dependency. YOLO keeps its own locked `opencv-python` environment. These are separate installation paths, not one combined dependency set. The shared geometry and adapter software tests have been exercised with YOLO's installed versions, but real MediaPipe inference has not been validated in that environment. [OpenCV's package instructions](https://pypi.org/project/opencv-python/) require choosing one distribution per environment because all variants install `cv2`; installing distributions in a particular order does not provide isolation. A future shared UI can dispatch each pipeline to its environment while consuming the common result contract.

## Save corners once

Click far-left, far-right, near-right, near-left on the first frame, then press 3. `u` undoes, `r` resets, and `q` cancels. The points are stored at the video's own resolution under the clip's file name.

```bash
python ../player-tracking/mark_corners.py data/drill.mp4 --registry data/corners.json
```

`data/` is gitignored. `corners.example.json` shows the registry shape.

## Run

```bash
python -m harness.run data/drill.mp4 --analyzer fake --corners data/corners.json
python -m harness.run data/drill.mp4 --analyzer mediapipe:pose-landmarker-lite --corners data/corners.json
```

The pose analyzer finds one player's heels and returns that pixel. The first run downloads `pose_landmarker_lite.task` into `experiments/player-tracking/models/`, which is gitignored. It does not choose a zone.

`--fps` defaults to 1. The frames stay at the video's own size unless `--long-side` is set. When it is set, the saved corners are scaled into that smaller frame.

A labels file is optional. If `drill.labels.csv` sits beside the clip, it is used. Pass `--labels` to choose another file.

```text
time_s,zone,x_ft,y_ft
0.0,kitchen_left,4.0,25.0
1.0,backcourt_right,15.0,40.0
```

`x_ft` and `y_ft` may be left empty. Zone accuracy still runs. Position error is reported only for rows that have both.

Each run writes `output/runs/<timestamp>_<clip>_<analyzer>_<unique-id>/results.csv` and `summary.json`. Unique directories prevent repeated evaluations from overwriting each other. The summary retains the saved corner entry and its annotations, scaled corners and sampling settings.

## Evaluate a YOLO tracking run

1. Use the YOLO browser or CLI to explicitly select players and finish a continuous tracking run. Obtain its `positions.json`; incomplete runs are rejected.
2. Save court corners with the shared tool above. Use the same video bytes as the tracking run; SHA-256 and image dimensions are checked.
3. Select one exported `player_id` and a window wholly covered by the run. A run starting at frame 600 and processing 290 frames uses `[600, 890)`:

```bash
# From experiments/vlm-harness; replace the paths for your video and export.
../player-tracking-yolo/.venv/bin/python -m harness.run /path/to/clip.mp4 \
  --analyzer yolo:yolo26n-pose \
  --positions /path/to/positions.json --player-id player_1 \
  --corners data/corners.json --start-frame 600 --stop-frame 890 --fps 1
```

`--stop-frame` is exclusive; omitting it requests the rest of the video, not just the tracked window. Unprocessed footage causes an error rather than being counted as missed detections. Repeat with another explicit player ID for a multi-player export. Model comparisons must use the same player, corners, window, sampling rate and labels.

YOLO tracks continuously before sampling. `frame_index` in `results.csv` is the harness sample ID; the added `source_frame_index` is the original decoded frame. Matching uses exact source indices instead of rounded timestamps. Harness label timestamps still use its existing frame-index/FPS convention; variable-frame-rate label alignment is unvalidated.

The adapter returns only `LocatedPoint` image coordinates. Shared `perspective.py` applies homography and `zone_from_feet` assigns zones. `--long-side 960` rescales exported points and corners together; it does **not** rerun YOLO at another inference resolution. `analyzer.json` retains the original model/settings, player ID, export checksum, sampled observations, missing reasons and source timestamps. Both missing statuses become null coordinates / `not_visible`; neither is interpolated or removed.

The model remains **YOLO26n-pose (`yolo26n-pose.pt`) + ByteTrack**. Ankle midpoint is a ground-position proxy, not measured foot-floor contact. Agree reference definitions before comparing physical errors. Zones cover only the **near half**: a visible far-half point is `out_of_court`, not `not_visible`. Accuracy is unavailable without labels. Logan's shared model-selector/browser wiring remains separate work; this change exposes the evaluation adapter and CLI.

## Add a model

Add one module under `harness/analyzers/` with `locate(frames) -> points`. Each point is a `LocatedPoint`: the sample index and `x_px`, `y_px` in that frame, or both coordinates null when not visible. Register it in `_FACTORIES` in `harness/analyzers/base.py`. Ordinary factories keep the existing `factory(model)` signature; the registry passes export configuration only to YOLO and rejects YOLO-only options for other analyzers. The module must not apply homography or choose zones. Export-backed analyzers may implement `validate_video(video, width, height, start_frame, stop_frame)` and `provenance()`; the runner calls these to validate the source and retain an audit file.

`prompts/foot_v1.txt` is the foot-point prompt for a later vision-language adapter.

## Tests

```bash
python -m pytest -v
```

The tests use a synthetic clip and do not download a model.

To include YOLO adapter tests, use `../player-tracking-yolo/.venv/bin/python -m pytest -v`. They explicitly skip when the optional `player_tracking` package is absent. Fabricated observations test contract errors, exact frame/player selection, scaling, missing rows, shared geometry, CLI behavior and output preservation; they do not measure YOLO accuracy.

The experiment's `ruff.toml` uses the YOLO package's 110-character line length for new code. Keep existing shared-file layout when making focused changes, rather than reformatting surrounding code. From this directory:

```sh
../player-tracking-yolo/.venv/bin/ruff check harness/analyzers/base.py harness/analyzers/yolo.py harness/frames.py harness/run.py tests/test_run.py tests/test_yolo.py tests/test_analyzers.py
../player-tracking-yolo/.venv/bin/ruff format --check harness/analyzers/yolo.py tests/test_yolo.py tests/test_analyzers.py
```
