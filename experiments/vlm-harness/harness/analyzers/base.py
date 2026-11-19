"""Analyzer interface.

locate() returns one image point per frame, or no point. It does not see the
court corners. A model pull request adds one module and one entry in _FACTORIES.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from ..contract import LocatedPoint
from ..frames import Frame


class Analyzer(Protocol):
    kind: str
    model_id: str
    is_remote: bool

    def locate(self, frames: Sequence[Frame]) -> Sequence[LocatedPoint]:
        """Player point in each frame's pixels. Both coordinates are None when not visible."""
        ...


def _make_fake(model: str) -> Analyzer:
    from .fake import FakeAnalyzer

    return FakeAnalyzer(model)


def _make_mediapipe(model: str) -> Analyzer:
    from .mediapipe_pose import PoseLandmarkerAnalyzer

    return PoseLandmarkerAnalyzer(model)


def _make_yolo(model: str, **options) -> Analyzer:
    # Optional integration: fake/other models do not import the YOLO package.
    from .yolo import YoloAnalyzer

    return YoloAnalyzer(model_id=model, **options)


_FACTORIES: dict[str, Callable[..., Analyzer]] = {
    "fake": _make_fake,
    "mediapipe": _make_mediapipe,
    "yolo": _make_yolo,
}


def create_analyzer(
    spec: str,
    *,
    positions_path: str | Path | None = None,
    player_id: str | None = None,
) -> Analyzer:
    """Build an analyzer; YOLO consumes a completed continuous tracking export."""
    kind, _, model = spec.partition(":")
    kind = kind.strip().lower()
    if kind not in _FACTORIES:
        known = ", ".join(sorted(_FACTORIES))
        raise ValueError(f"unknown analyzer {kind!r} in {spec!r}; choose from {known}")
    if kind == "yolo":
        return _FACTORIES[kind](model.strip(), positions_path=positions_path, player_id=player_id)
    if positions_path is not None or player_id is not None:
        raise ValueError("--positions and --player-id apply only to the yolo analyzer")
    # Other model PRs register factories taking only the model identifier.
    return _FACTORIES[kind](model.strip())
