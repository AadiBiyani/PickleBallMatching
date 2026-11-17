"""CLI: run analyzers x repeats on one clip and write results, annotated frames, and a table.

    python -m harness.run CLIP --analyzer gemini:gemini-3.8-flash --consent-confirmed
    python -m harness.run CLIP --analyzer ollama:qwen3-vl:8b --analyzer ollama:gemma4:12b-it-qat
    python -m harness.run CLIP --analyzer fake:valid

Every frame of every repeat gets a row, valid or not. Raw responses are cached under
output/cache, so a rerun with the same settings sends no requests.

Deliberately does not compute court coordinates in feet, classify attempts, or run a CV
baseline (later work; see docs/vlm-harness-notes.md).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from . import annotate as ann
from .analyzers.base import Analyzer, RateLimited, RequestFailed, create_analyzer
from .cache import ResponseCache, cache_key
from .contract import (
    REASON_QUOTA,
    REASON_RATE_LIMITED,
    REASON_REQUEST_FAILED,
    FrameResult,
    extra_indices,
    norm_to_px,
    request_error_results,
    response_json_schema,
    validate_response,
)
from .frames import DEFAULT_FPS, DEFAULT_LONG_SIDE_PX, Frame, extract_frames
from .labels import default_labels_path, load_labels
from .metrics import foot_spread_px, match_labels, self_agreement, valid_rate, zone_accuracy
from .throttle import QuotaExhausted, Throttle

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_DIR.parents[1]
DEFAULT_OUTPUT = EXPERIMENT_DIR / "output"
DEFAULT_PROMPT = EXPERIMENT_DIR / "prompts" / "zone_v1.txt"

RESULT_COLUMNS = [
    "clip", "analyzer", "model_id", "prompt_version", "temperature", "repeat", "frame_index",
    "time_s", "status", "reason", "zone", "foot_x_px", "foot_y_px", "label_zone",
    "request_latency_s", "cache_hit", "raw_response_path",
]
SUMMARY_COLUMNS = [
    "analyzer", "model_id", "frames", "repeats", "rows", "valid_rows", "valid_rate",
    "request_error_rows", "self_agreement", "foot_spread_px", "s_per_clip",
    "zone_accuracy", "n_labeled_frames",
]


class ConsentRequired(ValueError):
    pass


@dataclass(frozen=True)
class AnalyzerSummary:
    analyzer: str
    model_id: str
    frames: int
    repeats: int
    rows: int
    valid_rows: int
    valid_rate: float | None
    request_error_rows: int
    self_agreement: float | None
    foot_spread_px: float | None
    s_per_clip: float | None
    zone_accuracy: float | None
    n_labeled_frames: int


@dataclass
class RunOutcome:
    run_dir: Path
    rows: list[dict]
    summaries: list[AnalyzerSummary]
    unmatched_labels: list[dict] = field(default_factory=list)


def _fmt(v: float | None, digits: int = 3) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}"


def _chunks(items: Sequence[Frame], size: int) -> list[list[Frame]]:
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


def _new_run_dir(output_root: Path, clip_stem: str) -> Path:
    base = output_root / "runs" / f"{datetime.now():%Y%m%d-%H%M%S}_{clip_stem}"
    run_dir, n = base, 1
    while run_dir.exists():
        n += 1
        run_dir = base.with_name(f"{base.name}_{n}")
    run_dir.mkdir(parents=True)
    return run_dir


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def run_harness(
    video: str | Path,
    analyzers: Sequence[Analyzer],
    *,
    fps: float = DEFAULT_FPS,
    long_side_px: int = DEFAULT_LONG_SIDE_PX,
    repeats: int = 1,
    batch_size: int | None = None,
    labels_path: str | Path | None = None,
    min_interval_s: float | None = None,
    temperature: float | None = None,
    consent_confirmed: bool = False,
    prompt_path: str | Path = DEFAULT_PROMPT,
    output_root: str | Path = DEFAULT_OUTPUT,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> RunOutcome:
    if repeats < 1:
        raise ValueError("--repeats must be >= 1")
    if batch_size is not None and batch_size < 1:
        raise ValueError("--batch-size must be >= 1")
    if not analyzers:
        raise ValueError("at least one --analyzer is required")
    remote = [a.name for a in analyzers if a.is_remote]
    if remote and not consent_confirmed:
        raise ConsentRequired(
            f"{', '.join(remote)} send frames to a third-party API. Re-run with --consent-confirmed only if "
            "everyone visible in this clip agreed to that use (SYS-08, AGENTS.md)."
        )
    for a in analyzers:
        check = getattr(a, "check_ready", None)
        if check is not None:
            check()

    video = Path(video)
    prompt_path = Path(prompt_path)
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    prompt_version = prompt_path.stem
    prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    schema = response_json_schema()

    frames = extract_frames(video, fps=fps, long_side_px=long_side_px)
    frame_by_index = {f.index: f for f in frames}
    log(f"Extracted {len(frames)} frames at {fps:g} fps, {frames[0].width_px}x{frames[0].height_px} px from {video.name}")

    labels_file = Path(labels_path) if labels_path else default_labels_path(video)
    if labels_path and not labels_file.is_file():
        raise ValueError(f"labels file not found: {labels_file}")
    labeled: dict[int, str] = {}
    unmatched: list[dict] = []
    if labels_file.is_file():
        match = match_labels(load_labels(labels_file), {f.index: f.time_s for f in frames}, fps)
        labeled = match.by_frame
        unmatched = [asdict(lab) for lab in match.unmatched]
        log(f"Labels: {labels_file.name}, {len(labeled)} matched frames, {len(unmatched)} unmatched labels")
    else:
        log("Labels: none (zone accuracy will be n/a)")

    output_root = Path(output_root)
    cache = ResponseCache(output_root / "cache")
    run_dir = _new_run_dir(output_root, _safe(video.stem))
    for f in frames:
        (run_dir / "frames").mkdir(exist_ok=True)
        (run_dir / "frames" / f"frame_{f.index:04d}_t{f.time_s:.1f}s.jpg").write_bytes(f.jpeg)

    rows: list[dict] = []
    summaries: list[AnalyzerSummary] = []
    run_meta: dict = {"analyzers": {}}
    temp_label = "default" if temperature is None else temperature

    for analyzer in analyzers:
        if getattr(analyzer, "notice", None):
            log(analyzer.notice)
        interval = analyzer.default_min_interval_s if min_interval_s is None else min_interval_s
        throttle = Throttle(min_interval_s=interval, clock=clock, sleep=sleep, log=log)
        size = batch_size or analyzer.default_batch_size or len(frames)
        batches = _chunks(frames, size)
        quota_hit = False
        latency_by_repeat: list[float | None] = []
        extras: list[dict] = []
        a_rows: list[dict] = []
        log(f"[{analyzer.name}] {len(batches)} request(s) per repeat x {repeats} repeat(s)")

        for r in range(repeats):
            repeat_latency: float | None = 0.0
            for batch in batches:
                indices = [f.index for f in batch]
                key = cache_key(
                    analyzer.kind, analyzer.model_id, prompt_version, prompt_sha, temperature,
                    [f"{f.index}:{f.sha256}" for f in batch], r,
                )
                cached = cache.get(key)
                raw_path = ""
                latency: float | None = None
                hit = False
                if cached is not None:
                    results = validate_response(cached.raw_text, indices)
                    latency, raw_path, hit = cached.latency_s, str(cached.path), True
                    text = cached.raw_text
                elif quota_hit:
                    results, text = request_error_results(indices, REASON_QUOTA), None
                else:
                    try:
                        text, latency = throttle.call(
                            lambda b=batch: analyzer.request(b, prompt, schema, temperature)
                        )
                        stored = cache.put(
                            key, text, latency,
                            {"analyzer": analyzer.name, "model_id": analyzer.model_id,
                             "prompt_version": prompt_version, "temperature": temp_label,
                             "repeat": r, "frame_indices": indices, "clip": video.name},
                        )
                        raw_path = str(stored.path)
                        results = validate_response(text, indices)
                    except QuotaExhausted as exc:
                        quota_hit = True
                        log(f"  quota exhausted, skipping remaining requests for {analyzer.name}: {exc}")
                        results, text = request_error_results(indices, REASON_QUOTA), None
                    except RateLimited as exc:
                        log(f"  still rate limited after backoff: {exc}")
                        results, text = request_error_results(indices, REASON_RATE_LIMITED), None
                    except RequestFailed as exc:
                        log(f"  request failed: {exc}")
                        results, text = request_error_results(indices, f"{REASON_REQUEST_FAILED}: {exc}"), None
                if text is not None:
                    extra = extra_indices(text, indices)
                    if extra:
                        extras.append({"repeat": r, "batch": indices, "extra_indices": extra})
                if latency is None or repeat_latency is None:
                    repeat_latency = None
                else:
                    repeat_latency += latency
                for res in results:
                    a_rows.append(_row(video.name, analyzer, prompt_version, temp_label, r,
                                       frame_by_index[res.frame_index], res, labeled, latency, hit, raw_path))
            latency_by_repeat.append(repeat_latency)

        _annotate(run_dir, analyzer, a_rows, frame_by_index)
        summaries.append(_summarize(analyzer, a_rows, len(frames), repeats, labeled, latency_by_repeat))
        rows.extend(a_rows)
        run_meta["analyzers"][analyzer.name] = {
            "model_id": analyzer.model_id, "batch_size": size, "min_interval_s": interval,
            "throttle_waits_s": [round(w, 2) for w in throttle.waits_s], "extra_indices": extras,
        }

    _write_csv(run_dir / "results.csv", RESULT_COLUMNS, rows)
    _write_csv(run_dir / "summary.csv", SUMMARY_COLUMNS, [asdict(s) for s in summaries])
    run_meta.update({
        "clip": str(video), "fps": fps, "long_side_px": long_side_px, "frames": len(frames),
        "frame_size_px": [frames[0].width_px, frames[0].height_px], "repeats": repeats,
        "prompt_version": prompt_version, "prompt_sha256": prompt_sha, "temperature": temp_label,
        "labels_file": str(labels_file) if labels_file.is_file() else None,
        "unmatched_labels": unmatched, "python": sys.version.split()[0], "platform": platform.platform(),
        "created": datetime.now().isoformat(timespec="seconds"),
    })
    (run_dir / "run.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    log("")
    log(format_table(summaries))
    log(f"\nWrote {run_dir}")
    return RunOutcome(run_dir, rows, summaries, unmatched)


def _row(clip, analyzer, prompt_version, temp_label, repeat, frame: Frame, res: FrameResult,
         labeled, latency, hit, raw_path) -> dict:
    fx = fy = ""
    if res.is_valid and res.foot_x_norm is not None and res.foot_y_norm is not None:
        fx = norm_to_px(res.foot_x_norm, frame.width_px)
        fy = norm_to_px(res.foot_y_norm, frame.height_px)
    return {
        "clip": clip, "analyzer": analyzer.name, "model_id": analyzer.model_id,
        "prompt_version": prompt_version, "temperature": temp_label, "repeat": repeat,
        "frame_index": frame.index, "time_s": frame.time_s, "status": res.status, "reason": res.reason,
        "zone": res.zone or "", "foot_x_px": fx, "foot_y_px": fy,
        "label_zone": labeled.get(frame.index, ""),
        "request_latency_s": "" if latency is None else round(latency, 3),
        "cache_hit": hit, "raw_response_path": raw_path,
    }


def _annotate(run_dir: Path, analyzer: Analyzer, rows: list[dict], frames: dict[int, Frame]) -> None:
    """Annotated copies for repeat 0 only: enough to judge by eye in a minute."""
    out = run_dir / "annotated" / _safe(analyzer.name) / "r0"
    for row in rows:
        if row["repeat"] != 0:
            continue
        frame = frames[row["frame_index"]]
        foot = (row["foot_x_px"], row["foot_y_px"]) if row["foot_x_px"] != "" else None
        img = ann.annotate(
            frame.decode(),
            title=f"{analyzer.name}  frame {frame.index}  t={frame.time_s:.1f}s",
            status=row["status"], reason=row["reason"], zone=row["zone"] or None,
            foot_px=foot, label_zone=row["label_zone"] or None,
        )
        ann.write_jpeg(out / f"frame_{frame.index:04d}_t{frame.time_s:.1f}s.jpg", img)


def _summarize(analyzer, rows, n_frames, repeats, labeled, latency_by_repeat) -> AnalyzerSummary:
    ok = [r["status"] == "ok" for r in rows]
    zones_by_frame: dict[int, list[str | None]] = {}
    points_by_frame: dict[int, list[tuple[int, int] | None]] = {}
    for r in rows:
        valid = r["status"] == "ok"
        zones_by_frame.setdefault(r["frame_index"], []).append(r["zone"] if valid else None)
        pt = (r["foot_x_px"], r["foot_y_px"]) if valid and r["foot_x_px"] != "" else None
        points_by_frame.setdefault(r["frame_index"], []).append(pt)
    acc, n_scored = zone_accuracy(
        [(r["frame_index"], r["zone"] if r["status"] == "ok" else None) for r in rows], labeled
    )
    lat = [x for x in latency_by_repeat if x is not None]
    return AnalyzerSummary(
        analyzer=analyzer.name, model_id=analyzer.model_id, frames=n_frames, repeats=repeats,
        rows=len(rows), valid_rows=sum(ok), valid_rate=valid_rate(ok),
        request_error_rows=sum(1 for r in rows if r["status"] == "request_error"),
        self_agreement=self_agreement(zones_by_frame) if repeats > 1 else None,
        foot_spread_px=foot_spread_px(points_by_frame) if repeats > 1 else None,
        s_per_clip=statistics.fmean(lat) if lat else None,
        zone_accuracy=acc, n_labeled_frames=n_scored // repeats if repeats else 0,
    )


def format_table(summaries: Sequence[AnalyzerSummary]) -> str:
    header = ["analyzer", "valid_rate", "self_agree", "foot_spread_px", "s_per_clip", "zone_acc (n)", "req_errors"]
    body = [
        [
            s.analyzer,
            f"{_fmt(s.valid_rate)} ({s.valid_rows}/{s.rows})",
            _fmt(s.self_agreement),
            _fmt(s.foot_spread_px, 1),
            _fmt(s.s_per_clip, 2),
            "n/a" if s.zone_accuracy is None else f"{s.zone_accuracy:.3f} ({s.n_labeled_frames})",
            str(s.request_error_rows),
        ]
        for s in summaries
    ]
    widths = [max(len(r[i]) for r in [header, *body]) for i in range(len(header))]
    line = lambda r: "  ".join(c.ljust(w) for c, w in zip(r, widths))  # noqa: E731
    return "\n".join([line(header), "  ".join("-" * w for w in widths), *map(line, body)])


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in columns})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m harness.run", description=__doc__.split("\n\n")[0])
    p.add_argument("clip", help="path to a video file")
    p.add_argument("--analyzer", action="append", required=True,
                   help="kind:model, e.g. gemini:gemini-3.8-flash, ollama:qwen3-vl:8b, fake:valid (repeatable)")
    p.add_argument("--fps", type=float, default=DEFAULT_FPS, help="frames sampled per second (default 1)")
    p.add_argument("--long-side", type=int, default=DEFAULT_LONG_SIDE_PX, help="resize long side to this many px (default 960)")
    p.add_argument("--repeats", type=int, default=1, help="runs per analyzer for self-agreement (default 1)")
    p.add_argument("--batch-size", type=int, default=None, help="frames per request (default: all for Gemini, 8 for Ollama)")
    p.add_argument("--labels", default=None, help="labels CSV (time_s,zone); default <clip_stem>.labels.csv beside the clip")
    p.add_argument("--min-interval-s", type=float, default=None, help="minimum seconds between requests (default: 10 Gemini, 0 Ollama)")
    p.add_argument("--temperature", type=float, default=None, help="sampling temperature (default: provider default)")
    p.add_argument("--consent-confirmed", action="store_true",
                   help="confirm everyone in the clip agreed to sending it to a third-party API (required for Gemini)")
    p.add_argument("--prompt", default=str(DEFAULT_PROMPT), help="prompt file; its stem is the prompt version")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT), help="output root (default ./output)")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        from dotenv import load_dotenv

        load_dotenv(EXPERIMENT_DIR / ".env")
        load_dotenv(REPO_ROOT / ".env")
    except ImportError:
        pass
    try:
        analyzers = [create_analyzer(spec) for spec in args.analyzer]
        run_harness(
            args.clip, analyzers, fps=args.fps, long_side_px=args.long_side, repeats=args.repeats,
            batch_size=args.batch_size, labels_path=args.labels, min_interval_s=args.min_interval_s,
            temperature=args.temperature, consent_confirmed=args.consent_confirmed,
            prompt_path=args.prompt, output_root=args.output,
        )
    except (ValueError, RequestFailed, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
