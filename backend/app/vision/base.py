"""Vision-model interface.

Feet are the project's unit, and models are expected to report court feet
themselves by default (`output_space = "court"`). Court feet: origin at the
far-left outside corner, x 0-20 toward the right sideline, y 0-44 toward the
near baseline, net at y = 22.

Models written for the team's court evaluation harness report image pixels
instead (`output_space = "image"`). They never see the corners; the pipeline
projects their points with the clip's saved corners, exactly as the harness
does. Either way the zone is derived by the pipeline, never by the model.

To add your model:
1. A harness analyzer (an object with `kind`, `model_id`, `is_remote`, and
   `locate(frames)`): wrap it with `HarnessAnalyzer` in `app/vision/__init__.py`.
   If it already returns feet, give it `output_space = "court"`.
2. Otherwise subclass `VisionModel` and implement `locate()`.

Frames come from `app/frames.py` and have the harness frame fields
(`index`, `time_s`, `width_px`, `height_px`, `image`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from ..frames import Frame
from ..schemas import VisionModelInfo

OutputSpace = Literal["court", "image"]


@dataclass(frozen=True)
class LocatedPoint:
    """The player's position in one frame; the harness's LocatedPoint plus optional feet.

    Court models fill x_ft / y_ft; image models fill x_px / y_px (pixels of the
    frame they were shown, origin top-left). A model may fill both. When the
    player is not visible, leave all four None but still return the frame; never
    drop it (NFR-06).
    """

    frame_index: int
    x_px: float | None = None
    y_px: float | None = None
    x_ft: float | None = None
    y_ft: float | None = None

    @property
    def has_feet(self) -> bool:
        return self.x_ft is not None and self.y_ft is not None

    @property
    def has_pixels(self) -> bool:
        return self.x_px is not None and self.y_px is not None

    @property
    def visible(self) -> bool:
        return self.has_feet or self.has_pixels


class VisionModel(ABC):
    id: str  # unique registry key shown in the app's model selector
    kind: str  # harness analyzer kind, e.g. "yolo", "gemini", "mediapipe"
    model_id: str  # exact model, e.g. "yolo26n-pose", "gemini-3.8-flash"
    name: str
    owner: str
    version: str
    description: str
    output_space: OutputSpace = "court"  # expected default: the model reports court feet
    is_remote: bool = False  # True if frames leave this machine (needs consent, SYS-08)
    requires_clip_file: bool = True  # False only for models that never read pixels
    sample_fps: float = 10.0  # frames per second handed to locate()

    def info(self) -> VisionModelInfo:
        return VisionModelInfo(
            id=self.id,
            kind=self.kind,
            model_id=self.model_id,
            name=self.name,
            owner=self.owner,
            version=self.version,
            description=self.description,
            is_remote=self.is_remote,
            requires_clip_file=self.requires_clip_file,
            sample_fps=self.sample_fps,
            output_space=self.output_space,
        )

    @abstractmethod
    def locate(self, frames: Sequence[Frame]) -> Sequence[LocatedPoint]:
        """One point per frame (feet for court models, pixels for image models)."""


class HarnessAnalyzer(VisionModel):
    """Registers an analyzer written for the court evaluation harness, unchanged.

    Harness analyzers report pixels, so the default output space is "image".
    Pass output_space="court" (or set it on the analyzer) once it reports feet.
    The harness's own point objects are accepted as long as they have
    `frame_index` and `x_px`/`y_px` and/or `x_ft`/`y_ft`.
    """

    def __init__(
        self,
        analyzer: Any,
        *,
        name: str,
        owner: str,
        description: str,
        version: str = "0.1.0",
        sample_fps: float = 1.0,
        output_space: OutputSpace | None = None,
    ) -> None:
        self._analyzer = analyzer
        self.kind = analyzer.kind
        self.model_id = analyzer.model_id
        self.id = f"{self.kind}:{self.model_id}"
        self.is_remote = bool(getattr(analyzer, "is_remote", False))
        self.output_space = output_space or getattr(analyzer, "output_space", "image")
        self.name = name
        self.owner = owner
        self.description = description
        self.version = version
        self.sample_fps = sample_fps

    def locate(self, frames: Sequence[Frame]) -> list[LocatedPoint]:
        return [
            LocatedPoint(
                p.frame_index,
                getattr(p, "x_px", None),
                getattr(p, "y_px", None),
                getattr(p, "x_ft", None),
                getattr(p, "y_ft", None),
            )
            for p in self._analyzer.locate(frames)
        ]
