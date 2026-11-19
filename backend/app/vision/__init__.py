"""Registry of available player-tracking models (prototype model selector).

- `simulated`: in-process stand-in that reports court feet; always available.
- `mediapipe`, `yolo`: real models from `experiments/vlm-harness/`, run through the
  harness CLI in each model's own Python environment (see harness_process.py).
  They show as unavailable until that environment exists. Override an
  interpreter with PBM_MEDIAPIPE_PYTHON or PBM_YOLO_PYTHON.

Models default to reporting court feet. An in-process harness analyzer can also be
registered with HarnessAnalyzer (pixels, projected by the backend).
"""

import os
from pathlib import Path

from .. import clips
from .base import HarnessAnalyzer, LocatedPoint, VisionModel
from .harness_process import HARNESS_DIR, REPO_ROOT, HarnessProcessModel, venv_python
from .simulated import SimulatedModel


def _python(env_var: str, default_venv: Path) -> Path:
    override = os.environ.get(env_var)
    return Path(override) if override else venv_python(default_venv)


_MODELS: list[VisionModel] = [
    SimulatedModel(),
    HarnessProcessModel(
        id="mediapipe",
        analyzer="mediapipe:pose-landmarker-lite",
        name="MediaPipe pose landmarker",
        owner="Nishaant",
        description="Heel point in each sampled frame (one pose per frame). Runs live through the court harness.",
        python=_python("PBM_MEDIAPIPE_PYTHON", HARNESS_DIR / ".venv"),
        sample_fps=2.0,
    ),
    HarnessProcessModel(
        id="yolo",
        analyzer="yolo:yolo26n-pose",
        name="YOLO pose + ByteTrack (precomputed run)",
        owner="Aadi",
        description="Replays a completed YOLO tracking export for the chosen player (ankle midpoint) through the court harness.",
        python=_python("PBM_YOLO_PYTHON", REPO_ROOT / "experiments" / "player-tracking-yolo" / ".venv"),
        sample_fps=2.0,
        clip_args=clips.yolo_args,
        export_note="No precomputed YOLO run is registered for this clip. Add it to sample_clips/exports.json.",
    ),
]

MODELS: dict[str, VisionModel] = {m.id: m for m in _MODELS}


def get_model(model_id: str) -> VisionModel | None:
    return MODELS.get(model_id)


__all__ = ["HarnessAnalyzer", "HarnessProcessModel", "LocatedPoint", "MODELS", "VisionModel", "get_model"]
