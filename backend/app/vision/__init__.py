"""Registry of available player-tracking models (prototype model selector)."""

from .base import VisionModel
from .simulated import SimulatedModel

# Teammates: import and add your model instance here.
_MODELS: list[VisionModel] = [
    SimulatedModel(),
]

MODELS: dict[str, VisionModel] = {m.id: m for m in _MODELS}


def get_model(model_id: str) -> VisionModel | None:
    return MODELS.get(model_id)
