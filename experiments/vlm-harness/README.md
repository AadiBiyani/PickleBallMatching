# Court evaluation harness

One test video has its four court corners saved once. Each model then returns only the player's point in the frame it was shown. This harness maps that point through the same homography, assigns a court zone, and scores both against a label file.

Registered analyzers are `fake`, `gemini`, `mediapipe`, and `yolo`. MediaPipe returns a heel point from each sampled image. YOLO consumes a completed continuous tracking export from [player-tracking-yolo](../player-tracking-yolo/README.md). Gemini asks a vision-language model for the foot point; see [Gemini](#gemini) below.

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

## Gemini

The `gemini` analyzer sends the sampled frames to the Gemini API free tier and asks for one player's foot point in each. Like the other analyzers, it returns only a pixel point per frame. The harness applies the homography and assigns the zone; the model never sees the corners or picks a zone. It is ported from the zone harness on `liam-test-harness`, keeping its request shape, rate limiting and response cache, without the model-chosen zone or repeats.

**Only for clips everyone visible in them agreed to send to Google (SYS-08).** The run is refused without `--consent-confirmed`. Free-tier requests may be used by Google to improve its products; the harness prints that reminder and sends with `store=False`, which does not change those terms.

Setup: needs Python 3.11 or newer, because `google-genai` does; `pip install -r requirements.txt` installs it there and skips it on older interpreters, which can still run the other analyzers. Get a free key (no billing account) at https://aistudio.google.com/apikey and put `GEMINI_API_KEY=...` in `.env` in this folder or at the repo root. `.env.example` lists the name; `.env` is gitignored, and the key is never printed.

```bash
python -m harness.run data/drill.mp4 --analyzer gemini --corners data/corners.json --consent-confirmed
python -m harness.run data/drill.mp4 --analyzer gemini:gemini-4-hydrogen --corners data/corners.json \
  --prompt prompts/foot_gemini_v1_right.txt --consent-confirmed
```

- **Models.** `gemini` alone means `gemini-3.8-flash`. `gemini-4-hydrogen` is also on the free tier (checked 2026-11-16 at aistudio.google.com/docs); Gemini 4 Carbon and Argon are not.
- **Prompts.** `prompts/foot_gemini_v1.txt` (default) tracks the one drilling player on the near half. `foot_gemini_v1_right.txt` tracks the near player of the right-hand pair when two pairs drill at once. The file stem is the prompt version; add a new file instead of editing one that has been used for results. `foot_v1.txt` is unchanged and unused by this adapter.
- **What is sent.** All sampled frames in one request, each as a JPEG (quality 90) downscaled so its long side is at most 960 px, preceded by a `Frame <index> (t=<s> s):` caption. The model answers `{"frames": [{"frame_index": 0, "foot_x": 512, "foot_y": 830}]}` with integers 0-1000 normalized to the image, or `null` for both when the feet are not visible. The adapter converts these to pixels of the frame the harness holds (`x_px = foot_x / 1000 * width_px`), so the downscale does not shift the point.
- **Invalid answers.** Each frame is validated separately. Not JSON, a wrong top-level shape, an out-of-range or non-integer coordinate, one coordinate null, extra keys, a duplicate or a missing frame each make that frame (or every frame, for the first two) an invalid response. Invalid frames, like not-visible frames, get no point: they are counted as missing, never dropped and never retried. `analyzer.json` records which it was for every frame, with the reason, plus any frame indices the model returned that were not sent.
- **Rate limits.** Only rate limits are retried: back off 15, 30, 60, then 120 s, or the server's retry hint if longer. A daily-quota error, a persistent rate limit, a missing key or any other request failure stops the run with an error instead of recording frames as not visible.
- **Cache.** Every raw response is saved under `output/cache/gemini/` (gitignored), keyed by model, prompt text, temperature, schema, and the exact JPEG bytes and indices sent. A rerun with the same clip and settings makes no request and needs no key. Delete that folder to force fresh calls.

**First real run (2026-11-18).** A 30 s 1920×1080 tournament-stream recording with two pairs drilling at once, kept outside Git; the uploader confirmed everyone visible consented to third-party API use. Settings: `gemini-3.8-flash`, `foot_gemini_v1_right.txt`, 1 fps (30 frames), provider-default temperature, no labels. Result: 30/30 valid points, 1 request, no rate-limit waits, but 1089 s latency (the earlier zone-harness runs took 49–116 s per request). An eye check of frames 0, 8, 12, 17, 20 and 29 put the point on the right-hand near player at or between the feet every time. The camera lens bends the near baseline, which the straight-line homography does not model, so feet on that baseline project to about 44–45 ft and become `out_of_court` (frames 20 and 29). This is not an accuracy result; that needs labels from someone who did not tune the prompt on this clip.

Run outputs are the shared `results.csv` and `summary.json`, plus `analyzer.json` with the model, prompt version and hash, send settings, every request (cache hit, latency, raw response file) and every frame's outcome.

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

`prompts/foot_v1.txt` is the original placeholder foot-point prompt. The Gemini adapter uses `prompts/foot_gemini_v1*.txt`. A remote analyzer sets `is_remote = True`; the runner then requires `--consent-confirmed`. A request that produces no response should raise `AnalyzerRequestError` (from `harness/analyzers/base.py`), which the CLI reports as an error.

## Tests

```bash
python -m pytest -v
```

The tests use a synthetic clip and do not download a model. `tests/test_gemini.py` uses a stub client: no network, no API key, and no real footage. It checks the request shape, response validation, pixel conversion, caching, rate-limit handling and the consent gate. It says nothing about Gemini's accuracy.

Tested on Windows 11 (10.0.26200) with Python 3.12.10, google-genai 3.5.0, mediapipe 1.2.3, opencv-contrib-python 4.14.0.94, numpy 2.5.5 and pytest 8.4.2: 41 passed, 1 skipped (the YOLO adapter tests, which need the YOLO environment).

To include YOLO adapter tests, use `../player-tracking-yolo/.venv/bin/python -m pytest -v`. They explicitly skip when the optional `player_tracking` package is absent. Fabricated observations test contract errors, exact frame/player selection, scaling, missing rows, shared geometry, CLI behavior and output preservation; they do not measure YOLO accuracy.

The experiment's `ruff.toml` uses the YOLO package's 110-character line length for new code. Keep existing shared-file layout when making focused changes, rather than reformatting surrounding code. From this directory:

```sh
../player-tracking-yolo/.venv/bin/ruff check harness/analyzers/base.py harness/analyzers/yolo.py harness/frames.py harness/run.py tests/test_run.py tests/test_yolo.py tests/test_analyzers.py
../player-tracking-yolo/.venv/bin/ruff format --check harness/analyzers/yolo.py tests/test_yolo.py tests/test_analyzers.py
```
