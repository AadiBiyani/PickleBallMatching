"""Registry of available player-tracking models (prototype model selector).

Models default to reporting court feet (`output_space = "court"`). Register a
harness analyzer, which reports pixels, like this (example; not yet available
on this branch). Add output_space="court" once it reports feet:

    from harness.analyzers.yolo import YoloAnalyzer          # from the harness branch
    _MODELS.append(HarnessAnalyzer(YoloAnalyzer("yolo26n-pose"),
                                   name="YOLO pose + ByteTrack", owner="Aadi",
                                   description="...", sample_fps=10))

The Gemini analyzer from experiments/vlm-harness is registered below when the
harness and its dependencies (OpenCV; google-genai to actually call the API)
are installed. Without them the API still starts with the simulated model.
"""

import logging
import sys
from pathlib import Path

from .base import HarnessAnalyzer, LocatedPoint, VisionModel
from .simulated import SimulatedModel

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
VLM_HARNESS = REPO_ROOT / "experiments" / "vlm-harness"

_MODELS: list[VisionModel] = [
    SimulatedModel(),
]


def _load_env() -> None:
    """GEMINI_API_KEY from the harness's .env, then the repo root's. Neither is committed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(VLM_HARNESS / ".env")
    load_dotenv(REPO_ROOT / ".env")


def _gemini_models() -> list[VisionModel]:
    if not (VLM_HARNESS / "harness").is_dir():
        return []
    if str(VLM_HARNESS) not in sys.path:
        sys.path.insert(0, str(VLM_HARNESS))
    try:
        from harness.analyzers.gemini import GeminiAnalyzer
    except ImportError as exc:  # usually OpenCV missing: pip install -r requirements-gemini.txt
        log.warning("Gemini model not registered: %s", exc)
        return []
    _load_env()
    prompts = VLM_HARNESS / "prompts"
    default = HarnessAnalyzer(
        GeminiAnalyzer("gemini-3.8-flash"),
        name="Gemini 3.8 Flash (VLM foot point)",
        owner="Liam",
        description="Free-tier Gemini returns the drilling player's foot point per frame; "
        "the backend maps it to feet with the clip's corners. Prompt foot_gemini_v1.",
        sample_fps=1.0,
    )
    right_pair = HarnessAnalyzer(
        GeminiAnalyzer("gemini-3.8-flash", prompt_path=prompts / "foot_gemini_v1_right.txt"),
        name="Gemini 3.8 Flash, right-hand pair",
        owner="Liam",
        description="Same model; tracks the near player of the right-hand pair when two pairs "
        "drill at once. Prompt foot_gemini_v1_right.",
        sample_fps=1.0,
    )
    right_pair.id = f"{right_pair.id}:right-pair"  # ids must be unique; both share kind:model_id
    return [default, right_pair]


_MODELS.extend(_gemini_models())

MODELS: dict[str, VisionModel] = {m.id: m for m in _MODELS}


def get_model(model_id: str) -> VisionModel | None:
    return MODELS.get(model_id)


__all__ = ["HarnessAnalyzer", "LocatedPoint", "MODELS", "VisionModel", "get_model"]
