"""Registry of available player-tracking models (prototype model selector).

Models default to reporting court feet (`output_space = "court"`). Register a
harness analyzer, which reports pixels, like this (example; not yet available
on this branch). Add output_space="court" once it reports feet:

    from harness.analyzers.yolo import YoloAnalyzer          # from the harness branch
    _MODELS.append(HarnessAnalyzer(YoloAnalyzer("yolo26n-pose"),
                                   name="YOLO pose + ByteTrack", owner="Aadi",
                                   description="...", sample_fps=10))
"""

from .base import HarnessAnalyzer, LocatedPoint, VisionModel
from .simulated import SimulatedModel
from .workers import WorkerModel

_MODELS: list[VisionModel] = [
    SimulatedModel(),
    WorkerModel("yolo", "yolo26n-pose", "YOLO pose + ByteTrack", "Aadi",
                "Tracks explicitly selected players continuously; ankle midpoint positions."),
    WorkerModel("mediapipe", "pose-landmarker-lite", "MediaPipe Pose Landmarker", "Nishaant",
                "One detected pose per sample; heel positions. No selected-player identity lock."),
]

MODELS: dict[str, VisionModel] = {m.id: m for m in _MODELS}


def get_model(model_id: str) -> VisionModel | None:
    return MODELS.get(model_id)


__all__ = ["HarnessAnalyzer", "LocatedPoint", "MODELS", "VisionModel", "get_model"]
