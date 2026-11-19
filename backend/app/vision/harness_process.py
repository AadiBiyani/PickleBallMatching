"""Run a model through the court evaluation harness in that model's own Python environment.

MediaPipe and YOLO need separate environments (each pins a different OpenCV
distribution, and YOLO is locked to Python 3.12), so the backend never imports
them. Instead it runs the harness CLI as a subprocess:

    <model python> -m harness.run <clip> --analyzer <spec> --corners <registry>
                   --fps <n> --output <run root> [model-specific args]

from `experiments/vlm-harness/`, and reads the run's `results.csv`. Those rows
are already in court feet with the harness's zones, so the backend does no
geometry for these models; the app and the harness cannot disagree.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..frames import Frame
from ..schemas import Clip, CourtPoint
from .base import LocatedPoint, VisionModel

REPO_ROOT = Path(__file__).resolve().parents[3]
HARNESS_DIR = REPO_ROOT / "experiments" / "vlm-harness"
RUNS_DIR = Path(__file__).resolve().parents[2] / "harness_runs"
TIMEOUT_S = 900


def venv_python(venv_dir: Path) -> Path:
    """The interpreter inside a virtual environment, on Windows or macOS/Linux."""
    windows = venv_dir / "Scripts" / "python.exe"
    return windows if sys.platform == "win32" else venv_dir / "bin" / "python"


@dataclass(frozen=True)
class HarnessRun:
    rows: list[CourtPoint]
    frame_size_px: tuple[int, int]
    run_dir: Path
    processing_s: float


class HarnessError(Exception):
    """The harness refused or failed; the message is safe to show the player."""


class HarnessProcessModel(VisionModel):
    """A harness analyzer, run as a subprocess in its own environment."""

    output_space = "court"  # results.csv is already in court feet
    needs_corners = True  # the harness always projects with the clip's saved corners
    requires_clip_file = True
    is_remote = False
    version = "harness"

    def __init__(
        self,
        *,
        id: str,
        analyzer: str,
        name: str,
        owner: str,
        description: str,
        python: Path,
        sample_fps: float,
        clip_args: Callable[[str], list[str] | None] | None = None,
        export_note: str | None = None,
    ) -> None:
        self.id = id
        self.analyzer = analyzer
        self.kind, _, model = analyzer.partition(":")
        self.model_id = model or self.kind
        self.name = name
        self.owner = owner
        self.description = description
        self.python = python
        self.sample_fps = sample_fps
        # Returns extra CLI args for a clip, or None when the clip has no export for this model.
        self._clip_args = clip_args
        self.needs_export = clip_args is not None
        self._export_note = export_note

    # ---- availability ------------------------------------------------------

    def unavailable_reason(self) -> str | None:
        if not (HARNESS_DIR / "harness" / "run.py").is_file():
            return "The court evaluation harness is missing from experiments/vlm-harness."
        if not self.python.is_file():
            rel = self.python.relative_to(REPO_ROOT) if self.python.is_relative_to(REPO_ROOT) else self.python
            return f"Its Python environment is not set up ({rel})."
        return None

    def clip_problem(self, clip: Clip, path: Path | None) -> str | None:
        problem = super().clip_problem(clip, path)
        if problem is None and self.needs_export and self._clip_args(clip.id) is None:
            return self._export_note or f"No precomputed {self.name} run is registered for {clip.name}."
        return problem

    def locate(self, frames: Sequence[Frame]) -> list[LocatedPoint]:
        raise TypeError(f"{self.name} runs on whole clips through the harness; use analyze_clip()")

    # ---- running ------------------------------------------------------------

    def command(self, clip_path: Path, corners_path: Path, run_root: Path) -> list[str]:
        extra = self._clip_args(clip_path.name) if self._clip_args else []
        if extra is None:
            raise HarnessError(self._export_note or f"No precomputed {self.name} run for {clip_path.name}.")
        return [
            str(self.python), "-m", "harness.run", str(clip_path),
            "--analyzer", self.analyzer,
            "--corners", str(corners_path),
            "--fps", f"{self.sample_fps:g}",
            "--output", str(run_root),
            *extra,
        ]  # fmt: skip

    def analyze_clip(self, clip_path: Path, corners_path: Path, session_id: str) -> HarnessRun:
        reason = self.unavailable_reason()
        if reason:
            raise HarnessError(f"{self.name} is unavailable: {reason}")
        run_root = RUNS_DIR / session_id
        run_root.mkdir(parents=True, exist_ok=True)
        cmd = self.command(clip_path, corners_path, run_root)
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd, cwd=HARNESS_DIR, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=TIMEOUT_S, env=env,
            )  # fmt: skip
        except subprocess.TimeoutExpired as exc:
            raise HarnessError(f"{self.name} took longer than {TIMEOUT_S} s and was stopped.") from exc
        elapsed = round(time.perf_counter() - started, 2)
        if proc.returncode != 0:
            raise HarnessError(_harness_message(proc.stderr) or f"{self.name} exited with code {proc.returncode}.")
        run_dir = _run_dir(proc.stdout, run_root)
        return read_run(run_dir, elapsed)


def _harness_message(stderr: str) -> str | None:
    """The harness prints `error: <reason>` on a handled failure; otherwise the last line."""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("error: "):
            return line.removeprefix("error: ")
    return lines[-1] if lines else None


def _run_dir(stdout: str, run_root: Path) -> Path:
    for line in stdout.splitlines():
        if line.startswith("wrote "):
            return Path(line.removeprefix("wrote ").strip())
    runs = sorted((run_root / "runs").glob("*/results.csv"), key=lambda p: p.stat().st_mtime)
    if not runs:
        raise HarnessError("The harness finished without writing results.csv.")
    return runs[-1].parent


def _num(value: str) -> float | None:
    return float(value) if value not in ("", None) else None


def read_run(run_dir: Path, processing_s: float) -> HarnessRun:
    """Turn a harness run folder into backend track rows."""
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    rows = []
    with (run_dir / "results.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            source = row.get("source_frame_index", "")
            rows.append(
                CourtPoint(
                    frame_index=int(row["frame_index"]),
                    source_frame_index=int(source) if source else None,
                    time_s=float(row["time_s"]),
                    x_px=_num(row["x_px"]),
                    y_px=_num(row["y_px"]),
                    x_ft=_num(row["x_ft"]),
                    y_ft=_num(row["y_ft"]),
                    zone=row["zone"],
                )
            )
    width, height = summary["frame_size_px"]
    return HarnessRun(rows, (int(width), int(height)), run_dir, processing_s)
