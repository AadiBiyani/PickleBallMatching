# Court evaluation harness

One test video has its four court corners saved once. Each model then returns only the player's point in the frame it was shown. This harness maps that point through the same homography, assigns a court zone, and scores both against a label file.

The pose landmarker is registered as `mediapipe`. YOLO and Gemini are not in this folder yet. Each of those lands as its own analyzer module later.

## Setup

From this directory, with Python 3.9 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`opencv-contrib-python` is listed after `mediapipe` in `requirements.txt`. Keep that order. MediaPipe can replace the windowed OpenCV package, and the corner click tool needs the windowed build.

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

Each run writes `output/runs/<timestamp>_<clip>/results.csv` and `summary.json`.

## Add a model

Add one module under `harness/analyzers/` with `locate(frames) -> points`. Each point is a `LocatedPoint`: the frame index and `x_px`, `y_px` in that frame, or both coordinates null when the player is not visible. Register it in `_FACTORIES` in `harness/analyzers/base.py`. The module must not apply the homography or choose the zone.

`prompts/foot_v1.txt` is the foot-point prompt for a later vision-language adapter.

## Tests

```bash
python -m pytest -v
```

The tests use a synthetic clip and do not download a model.
