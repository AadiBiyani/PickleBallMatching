# vlm-harness (MVP)

A quick, zero-cost check of one question: **can a free vision-language model tell where a pickleball player is on the court from drill video frames, well enough to be worth pursuing?**

The harness samples frames from a clip and asks each analyzer two things for every frame:
- the court zone the player is in, from a fixed 8-value grid
- the pixel location of the player's feet

It records every answer, valid or not. It writes a CSV and annotated frames so you can judge accuracy by eye. It prints one comparison table across analyzers.

**What it is not (yet):**
- no CV baseline
- no homography and no court coordinates in feet
- no attempt-outcome classification
- not the full metric set in `docs/vlm-harness-notes.md`

Those are later work.

## Requirements supported

| ID | What this provides | Not covered |
| --- | --- | --- |
| FR-08 (court position), in part | Zone-level position per sampled frame, plus a foot point in pixels | Positions in feet. Continuous tracking |
| NFR-06, in part | Zone accuracy against labels, as early evidence about whether VLM positions are worth pursuing | The NFR-06 position-error threshold in meters needs homography and is not measured |
| SYS-08 | Remote analyzers refuse to run without `--consent-confirmed`. Footage, frames and output are gitignored | Consent records themselves |

## Analyzers

| Spec | What it is | Cost |
| --- | --- | --- |
| `gemini:gemini-3.8-flash` (default for `gemini`) | Gemini API free tier, Interactions API, frames inline | Free tier. Requests may be used by Google to improve its products, and the harness prints a reminder |
| `gemini:gemini-4-hydrogen` | Also on the free tier as of 2026-11-16. Gemini 4 Carbon and Argon are not | Free tier |
| `ollama:<tag>` | Local model through Ollama, e.g. `qwen3-vl:8b`, `gemma4:12b-it-qat` | Free, local |
| `fake:<scenario>` | Canned **synthetic** responses for tests: `valid`, `noisy`, `invalid_json`, `missing_frame`, `bad_zone`, `rate_limit_then_ok`, `always_rate_limited`, `quota_exhausted`, `request_failed` | None |

To add a model, write one module in `harness/analyzers/` with a `request(frames, prompt, schema, temperature) -> str` method, then add one entry to `_FACTORIES` in `harness/analyzers/base.py`. Validation, caching, throttling and metrics are shared.

**Recommended Ollama models for an 8 GB GPU with 32 GB RAM** (RTX 5060 Laptop, checked 2026-11-16):

| Model | Tag | Size | Notes |
| --- | --- | --- | --- |
| Qwen3-VL | `qwen3-vl:8b` | 6.2 GB | Fits fully on the GPU |
| Gemma 4 | `gemma4:12b-it-qat` | 7.2 GB | At the edge of 8 GB and may spill a little to the CPU |
| Gemma 4 fallback | `gemma4:e4b-it-qat` | 6.1 GB | Use if 12b is too slow |

The mixture-of-experts tags (`qwen3-vl:30b-a3b`, 20 GB, and `gemma4:26b-a4b-it-qat`, 16 GB) run split across CPU and GPU. Try them only after the above.

## Setup

Python 3.12. Run from this folder.

```
cd experiments/vlm-harness
python -m venv .venv
.venv\Scripts\activate            # macOS: source .venv/bin/activate
pip install -r requirements.txt
```

- **Gemini:** get a free key at https://aistudio.google.com/apikey. No billing account is needed. Put `GEMINI_API_KEY=...` in the repo-root `.env`, which `.env.example` lists and Git ignores. The key is never printed.
- **Ollama:** install from https://ollama.com, then run:

  ```
  ollama pull qwen3-vl:8b
  ollama pull gemma4:12b-it-qat
  ```

  The harness talks to `OLLAMA_HOST`, or `http://localhost:11434` if that is not set.

## Run

Put clips in `data/` (gitignored) or anywhere outside the repo.

```
# Offline smoke test (synthetic responses)
python -m harness.run data\clip.mp4 --analyzer fake:valid --repeats 3

# Gemini free tier. Only for clips everyone in them agreed to send to Google.
python -m harness.run data\clip.mp4 --analyzer gemini:gemini-3.8-flash --repeats 3 --consent-confirmed

# Local models, compared in one table
python -m harness.run data\clip.mp4 --analyzer ollama:qwen3-vl:8b --analyzer ollama:gemma4:12b-it-qat --repeats 3
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--fps` | 1 | Frames sampled per second |
| `--long-side` | 960 | Resize so the long side is this many px. Every analyzer sees identical JPEGs |
| `--repeats` | 1 | Runs per analyzer, for self-agreement |
| `--batch-size` | all frames (Gemini), 8 (Ollama) | Frames per request |
| `--min-interval-s` | 10 (Gemini), 0 (Ollama) | Pause between requests |
| `--temperature` | provider default | Self-agreement depends on this, so compare analyzers at stated temperatures |
| `--labels` | `<clip_stem>.labels.csv` beside the clip | Zone labels, see below |
| `--consent-confirmed` | off | Required for remote analyzers |

**Rate limits.** Google does not publish the free-tier RPM/RPD on its docs page, so check your quota in AI Studio. The harness behaves as follows:
- It sends one request per clip by default.
- On a 429 it backs off for 15, 30, 60 and 120 s, using the server's retry hint when that is longer.
- If the 429 persists, it records `request_error / rate_limited`.
- On a daily-quota error it stops calling that analyzer for the rest of the run.

Only rate limits are retried. An invalid response is a result and is never retried.

**Cache.** Every raw response is saved under `output/cache/`. The cache key covers:
- analyzer and model ID
- prompt version and text
- temperature
- frame hashes
- repeat number

A rerun with the same settings costs no quota. Request errors are not cached.

## Output

Each run creates `output/runs/<YYYYmmdd-HHMMSS>_<clip>/`. Everything under it is gitignored.

| File | Contents |
| --- | --- |
| `frames/` | The exact JPEGs sent to every analyzer |
| `annotated/<analyzer>/r0/` | Repeat 0 drawn on the frames: a yellow crosshair at the foot point and the zone name. Invalid rows get a red banner with the reason. With labels, it also shows `label: <zone> [OK]` or `[X]` |
| `results.csv` | One row per analyzer × repeat × frame |
| `summary.csv` | One row per analyzer |
| `run.json` | Settings, prompt hash, throttle waits, extra frame indices, unmatched labels, Python and OS |

`results.csv` columns: `clip, analyzer, model_id, prompt_version, temperature, repeat, frame_index, time_s, status, reason, zone, foot_x_px, foot_y_px, label_zone, request_latency_s, cache_hit, raw_response_path`.

**Status values:**
- `ok`
- `invalid_response`, with reason `json_parse_error`, `schema_error: ...` or `missing_frame`
- `request_error`, with reason `rate_limited`, `quota_exhausted` or `request_failed: ...`

A frame with no estimate keeps its row, with empty coordinates.

**Comparison table and summary:**
- `valid_rate`: valid rows divided by frames × repeats.
- `self_agree`: for each frame, the share of repeats that match its most common zone, averaged over frames. An invalid response counts as disagreement. Shown only with `--repeats` ≥ 2.
- `foot_spread_px`: the median distance from each frame's median foot point across repeats.
- `s_per_clip`: summed request latency per repeat, averaged over repeats. Throttle and backoff waits are excluded. Cached rows reuse the original latency.
- `zone_acc (n)`: shown only with labels. An invalid or missing prediction counts as wrong.

## Data contract

**Zones** are on the near half, with the camera behind the player's baseline. Left and right are as seen in the image, split by the centerline extended to the net.

| Zone | Extent |
| --- | --- |
| `kitchen_left` / `kitchen_right` | Net to the kitchen line (7 ft) |
| `transition_left` / `transition_right` | Kitchen line to halfway to the baseline (≈14.5 ft from the net, no painted line) |
| `backcourt_left` / `backcourt_right` | Halfway to the baseline (22 ft) |
| `out_of_court` | Behind the baseline, outside a sideline, or on the far half |
| `not_visible` | Player or feet not visible |

The same zones in the court frame from the notes (feet, near half): kitchen `y_ft` 22–29, transition 29–36.5, backcourt 36.5–44. Left `x_ft` 0–10, right 10–20. The MVP does not compute feet.

**Model response** (validated with pydantic, and sent as the JSON schema to both providers):

```json
{"frames": [{"frame_index": 0, "zone": "kitchen_left", "foot_x": 512, "foot_y": 830}]}
```

- `foot_x` and `foot_y` are integers from 0 to 1000, normalized to the image. They are `null` exactly when the zone is `not_visible`.
- Extra keys are rejected.
- The harness converts the point to pixels: `px = floor(v / 1000 * (size - 1) + 0.5)`.
- Each frame index sent must appear exactly once.

**Labels CSV** (optional, UTF-8, header required). The harness is fully usable without one.

```
time_s,zone
0.0,backcourt_left
1.0,transition_left
```

- Each label matches the nearest sampled frame within half the sampling interval (±0.5 s at 1 fps).
- Labels with no frame in range are listed in `run.json` and not scored.
- A malformed file is rejected with its line number.
- Do not tune the prompt on the clips you report accuracy for.

**Prompt:** `prompts/zone_v1.txt`. Its file stem is the prompt version, recorded on every row. To change the prompt, add `zone_v2.txt` rather than editing v1.

## Validate

```
python -m pytest -v
```

The tests use pytest. They run with no network, no API key, no Ollama, and no video file: the video fixtures are synthetic clips generated in a temp folder. `tests/test_*.py` covers the acceptance cases in `docs/vlm-harness-notes.md`.

Tested on Windows 11 (10.0.26200) with Python 3.12.10, opencv-contrib-python 4.14.0.94, google-genai 3.4.0, pydantic 2.14.3, httpx 0.28.1 and pytest 8.4.2. The code uses `pathlib` throughout and should run on macOS, but that has not been tested there.

## Data and privacy

- Never commit clips, frames, labels or `output/`. This folder's `.gitignore` covers `output/`, `data/`, `*.labels.csv` and `.venv/`.
- Send footage to Gemini only when everyone visible in it has agreed to third-party API use (SYS-08). Free-tier requests may be used by Google to improve its products. The harness sends with `store=False`, but that does not change Google's training terms.
- Ollama runs locally, and frames do not leave the machine.
