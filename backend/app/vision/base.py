"""Interface every player-tracking model implements.

To add your model:
1. Create `app/vision/<your_model>.py` with a class that subclasses VisionModel.
2. Implement `track()` so it reads the clip and returns court-coordinate points.
3. Register an instance in `app/vision/__init__.py`.

The UI and API do not change: the model selector lists whatever is registered.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from ..schemas import Drill, TrackResult, VisionModelInfo


class VisionModel(ABC):
    id: str
    name: str
    owner: str
    version: str
    description: str
    # False only for models that do not read video (e.g. the simulated stand-in).
    requires_clip_file: bool = True

    def info(self) -> VisionModelInfo:
        return VisionModelInfo(
            id=self.id,
            name=self.name,
            owner=self.owner,
            version=self.version,
            description=self.description,
            requires_clip_file=self.requires_clip_file,
        )

    @abstractmethod
    def track(self, clip_path: Path | None, drill: Drill, seed: int) -> TrackResult:
        """Return timestamped ground positions of the assessed player.

        clip_path is None only for synthetic clips (models with requires_clip_file=False).
        Frames where the player is not found must be returned with x_m/y_m = None,
        not dropped (NFR-06: missing estimates cannot be silently removed).
        """
