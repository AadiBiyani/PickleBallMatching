# VLM harness experiment: plan

**Status (2026-11-16):** the MVP below is built in `experiments/vlm-harness/` and its offline tests pass. **It has not yet been run on a real clip or a real model.** The larger design after the MVP section is a draft for later work and has not been reviewed by the team.

## MVP scope (approved 2026-11-16)

**Question:** can a free vision-language model tell where a pickleball player is on the court from drill video frames, well enough to be worth pursuing? This is the "first step" at the end of this file, made repeatable.

**Hard constraint:** zero cost. No paid APIs, no billing accounts.

**In scope:**
- One `Analyzer` interface with three adapters:
  - Gemini API free tier (default `gemini-3.8-flash`)
  - local Ollama, with the model as a parameter
  - a fake with canned synthetic responses
- Shared OpenCV frame extraction: 1 fps by default, long side resized to 960 px, JPEG q90. Every analyzer gets identical bytes.
- Per frame, the model returns a zone from a fixed grid and a foot point. Output is structured JSON, validated, and an invalid response is a counted failure.
- As few requests per clip as possible, with throttling, backoff on rate limits, and an on-disk cache of every raw response.
- Per run: a CSV, annotated frames, `--repeats N` with self-agreement, and one comparison table (valid-response rate, self-agreement, seconds per clip).
- Zone accuracy when a labels CSV exists. The harness is useful without labels.

**Out of scope for the MVP:**
- the CV baseline
- homography and court coordinates in feet
- attempt-outcome classification
- the full metric set below

**Decisions:**
- **Zone grid (8 values).** The camera is assumed to be behind the player's baseline, with the player on the near half. Left and right are as seen in the image, split by the centerline extended to the net.
  - `kitchen_{left,right}`: net to the kitchen line
  - `transition_{left,right}`: kitchen line to the half-way point, 14.5 ft from the net, which has no painted line
  - `backcourt_{left,right}`: half-way point to the baseline
  - `out_of_court`
  - `not_visible`
  - In the court frame below (feet, near half): kitchen `y_ft` 22–29, transition 29–36.5, backcourt 36.5–44. Left `x_ft` 0–10, right 10–20.
- **Coordinates.** Models return the foot point as integers 0–1000 normalized to the image, which is how Gemini and Qwen3-VL are trained to ground. The harness converts to pixels: `floor(v/1000*(size-1)+0.5)`. The point is null exactly when the zone is `not_visible`.
- **Validation is per frame.** The outcomes are:
  - Not JSON, or the wrong top-level shape: every frame in the request is invalid.
  - A bad entry: only that frame is invalid.
  - An absent frame: `missing_frame`.
  - A duplicate index: invalid.
  - Extra keys: rejected.
  - Extra indices: listed in `run.json`.
- **Self-agreement** is the mean over frames of the share of repeats that match the most common zone. An invalid response counts as disagreement, and the denominator is N.
- **Rate limits.** Backoff is 15, 30, 60, then 120 s, or the server's retry hint if longer. Then the frame gets `request_error`. A daily-quota error stops further calls. Only rate limits are retried; invalid output never is. Request errors are not cached.
- **Consent.** Remote analyzers require `--consent-confirmed` (SYS-08). The Gemini analyzer prints a reminder that free-tier requests may be used by Google to improve its products, and sends with `store=False`.
- **Provider facts (checked 2026-11-16 at aistudio.google.com/docs):**
  - `gemini-3.8-flash` is stable and free.
  - `gemini-4-hydrogen` is free. Gemini 4 Carbon and Argon are not.
  - Inline requests are capped at 20 MB.
  - A 960×540 frame is about 6 tiles of 258 tokens.
  - Free-tier RPM and RPD are not published on the docs page.
- **Local models for an 8 GB RTX 5060 Laptop GPU with 32 GB RAM:** `qwen3-vl:8b` (6.2 GB) and `gemma4:12b-it-qat` (7.2 GB), with `gemma4:e4b-it-qat` as the fallback. The default Ollama batch is 8 frames per request.

**Acceptance cases (agreed before implementation; all offline):**
1. A synthetic 5 s 1920×1080 clip gives 5 frames at 1 fps at t = 0..4 s, each 960×540. At 2 fps it gives 10. A portrait clip gives 540×960.
2. A valid response gives 5 `ok` rows. Foot (500, 1000) on 960×540 becomes px (480, 539).
3. A missing frame 3 gives 4 ok rows and 1 `missing_frame`, so the valid rate is 0.80.
4. A non-JSON response makes all 5 rows `json_parse_error`. The raw text is still cached.
5. Each of these invalidates only its own frame with `schema_error`: zone `kitchen_center`, `foot_x=1200`, or `not_visible` with coordinates.
6. Repeat zones `[A,A,B]` → 0.667, `[A,A,A]` → 1.0, `[A,invalid,A]` → 0.667. The clip mean is 0.778.
7. Zone accuracy:
   - Labels `[kl,kl,tr,tr,bl]` against predictions `[kl,kr,tr,invalid,bl]` give 0.60.
   - A label at 2.4 s matches the frame at 2.0 s.
   - A label at 9 s is unmatched.
   - No labels gives `n/a`.
8. A second identical run makes 0 analyzer calls and produces the same `results.csv` apart from `cache_hit`.
9. Rate limiting:
   - Two 429s then success: 3 calls, with waits of 15 and 30 s.
   - Always 429: `request_error/rate_limited`, with nothing cached.
10. Gemini adapter: the request has inline JPEG parts, captions and the schema. A missing key gives a readable error, and the key is never printed. The run is refused without consent.
11. Ollama adapter: the payload has `format`, base64 `images` and `stream: false`. A refused connection says "is Ollama running?".
12. Two analyzers give a table with two rows.

## MVP observed results

**Environment:**
- Windows 11 Home 10.0.26200, Python 3.12.10, in a fresh venv in `experiments/vlm-harness/.venv`
- opencv-contrib-python 4.14.0.94, google-genai 3.4.0, pydantic 2.14.3, httpx 0.28.1, numpy 2.5.5, pytest 8.4.2

**Offline tests:**
- `python -m pytest -v`: **54 passed, 0 failed** in 15.0 s on the first run, with no code changes needed.
- All 12 acceptance cases above are covered.
- The video fixtures are synthetic MJPG clips generated in a temp folder.

**CLI smoke run, 2026-11-16:**
- Input: a synthetic 6 s 1080p clip, 3 labels, the fake analyzers `valid`, `noisy` and `missing_frame`, with `--repeats 3`.
- Exit code 0. The run wrote `results.csv`, `summary.csv`, `run.json`, 6 sent frames, and annotated frames for each analyzer.
- Checked by eye: valid frames show the crosshair, zone and label match. Invalid frames show a red `invalid_response: missing_frame` banner.
- The table matched hand calculation:

| Analyzer | Valid rate | Self-agreement |
| --- | --- | --- |
| `valid` | 1.000 | 1.000 |
| `noisy` | 1.000 | 0.667 |
| `missing_frame` | 0.833 | 0.833 |

These numbers come from canned synthetic responses and **say nothing about any model**.

**Not yet run:**
- **Gemini on a real clip:** needs a key in `.env` and a clip whose participants consented to third-party API use.
- **Ollama:** it is not installed on the dev machine, and no models are pulled.
- **macOS:** not tested.

Record the first real runs here: clip, settings, the table, and an eye check of the annotated frames.

**First Gemini run, 2026-11-16:**
- Clip: a 29.7 s 1920×1080 30 fps screen recording of a tournament stream. The camera is elevated behind the near baseline. Two pairs drill at once, one on each half. The clip is outside Git. The uploader confirmed that everyone visible consented to third-party API use.
- Target: the near-side player of the right-hand pair. Prompt `zone_v2_right.txt` was added for this, and v1 is unchanged.
- Settings: `gemini:gemini-3.8-flash`, 1 fps (30 frames), 960 px long side, `--repeats 3`, provider-default temperature, 1 request per repeat, no labels.

| Analyzer | Valid rate | Self-agreement | Foot spread (px) | s/clip | Zone acc | Request errors |
| --- | --- | --- | --- | --- | --- | --- |
| `gemini:gemini-3.8-flash` | 1.000 (90/90) | 1.000 | 0.0 | 79.6 | n/a | 0 |

- All 90 rows were fresh calls with no cache hits. The repeats differ by about 1 px per frame, so the 0.0 spread is a real median and not duplicated output. Request latency was 49–116 s.
- Repeat 0 zones: transition_right 20, backcourt_right 8, kitchen_right 2.
- Eye check of frames 0, 12, 17, 20, 24 and 29:
  - The point is on the right-hand player every time, never on the left pair. It lands at or between the feet.
  - Zones look right in 0, 17 and 24.
  - Frame 12 (kitchen_right) has the feet at the kitchen line.
  - Frames 20 and 29 (backcourt_right) have the feet at the baseline/sideline corner, so out_of_court is also arguable.
- Without labels this is not an accuracy result. Next step: a labels CSV from someone who has not tuned the prompt on this clip, with a rule for feet on a line.

**Known limitations:**
- The zone grid assumes a camera behind the player's baseline.
- The transition/backcourt boundary has no painted line, so expect disagreement near it, from models and from labelers.
- Self-agreement depends on temperature. Runs default to the provider's own temperature, recorded as `default`.
- `s_per_clip` excludes throttle and backoff waits.
- Annotated frames are written for repeat 0 only.

---

The sections below are the earlier, larger design. They are later work beyond the MVP.

## Question

Which analysis approach should Flow 1 (drill recording to coverage profile) use? The harness runs several interchangeable analyzers on the same clips and scores them the same way, so the answer comes from numbers.

It supplies evaluation evidence for FR-08 with NFR-06 (court position) and FR-09 with NFR-05 (attempt classification). Latency and cost per clip inform NFR-01 and C-05.

## Candidates

Each candidate is a complete pipeline behind one interface. Comparing only vision-language models against each other would leave out the most likely winner for position data.

| Kind | What it is |
| --- | --- |
| VLM only | One adapter per provider and model. The model sees sampled frames and returns structured output |
| CV baseline | Pose tracking plus homography, the approach in `experiments/player-tracking/` |
| Hybrid | CV for positions, a VLM for attempt outcomes or drill-level description |

Known risks for the VLM-only route, to be measured, not assumed: sparse frame sampling misses fast movement, position output is imprecise and can be invented, and repeated runs can disagree.

Model names are deliberately absent. Choose them when building and read each provider's current documentation for video and image input limits.

## Interface sketch

```python
class Analyzer(Protocol):
    name: str        # "cv-baseline", "vlm-<provider>-<model>"
    version: str     # bump when the prompt, sampling, or logic changes

    def analyze(self, clip: Clip) -> AnalysisResult: ...
```

`AnalysisResult` holds:

- `positions`: rows of `time_s`, `x_ft`, `y_ft`, `status`. A frame with no estimate keeps its row with empty coordinates and a status that says why.
- `attempts`: rows of `attempt_id`, `start_s`, `end_s`, `outcome`, `exclusion_reason`. Outcomes are the four values in `AGENTS.md`.
- `run`: analyzer name and version, exact model ID, prompt version, frame sampling settings, latency in seconds, cost in dollars, and the path of the saved raw response.

Positions use the player-tracking court frame so results are directly comparable: feet, origin at the far-left outside corner, `x` from 0 to 20, `y` from 0 to 44. Convert to meters only when checking NFR-06.

## Controls

- The harness extracts frames itself, at one frame rate and resolution for every analyzer. Providers handle raw video differently, and that difference must stay out of the comparison.
- Prompts are files with versions. The output schema is validated, and an invalid response is a counted failure.
- Each VLM analyzer runs several times per clip to measure run-to-run variation.
- Raw responses are cached on disk so scoring can be rerun without paying again.

## Ground truth

A small labeled set of drill clips: player ground position at a fixed sampling rate, and attempt outcomes. The plan calls for CVAT labeling and two reviewers on outcome labels. Clips and labels that show a participant stay out of Git. Clips used to tune prompts or thresholds are kept apart from the clips used to report results.

## Metrics

| Metric | Notes |
| --- | --- |
| Position error | Mean, maximum, and 95th percentile, plus the count of missing estimates |
| Zone accuracy | Share of labeled samples placed in the correct court zone |
| Attempt classification | Macro-F1 over successful and unsuccessful, the retained share of valid attempts, missed and spurious attempts |
| Schema validity | Share of runs that return valid structured output |
| Run-to-run variation | Spread of the metrics above across repeated runs on one clip |
| Latency and cost | Per clip |

## Proposed layout

```
experiments/vlm-harness/
  README.md            what it is, how to run, requirements supported
  requirements.txt
  harness/
    contract.py        Clip, AnalysisResult, validation
    frames.py          shared frame extraction
    analyzers/         one module per analyzer
    metrics.py
    run.py             CLI: analyzers x clips x repeats -> results
  prompts/
  tests/               contract, metrics, and adapter tests with fake responses
```

## Open decisions

- Which models to include, and the API budget.
- Where clips come from, and whether everyone in them has agreed to third-party API use.
- Whether VLM analyzers are asked for coordinates, for court zones, or both.
- Frame rate and resolution for shared extraction.
- How the CV baseline handles the four-corner click that `track_video.py` currently needs from a person.

## First step

Before writing harness code, give one VLM a single clip and ask where the player is at five timestamps. Check the answers by eye. If most are wrong, lead with the CV baseline and treat VLM-only as the comparison.
