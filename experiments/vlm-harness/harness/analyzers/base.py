"""Analyzer interface.

locate() returns one image point per frame, or no point. It does not see the
court corners. A model pull request adds one module and one entry in _FACTORIES.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
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


_FACTORIES: dict[str, Callable[[str], Analyzer]] = {
    "fake": _make_fake,
}


def create_analyzer(spec: str) -> Analyzer:
    """Build an analyzer from 'kind' or 'kind:model'. Only fake is registered here."""
    kind, _, model = spec.partition(":")
    kind = kind.strip().lower()
    if kind not in _FACTORIES:
        known = ", ".join(sorted(_FACTORIES))
        raise ValueError(f"unknown analyzer {kind!r} in {spec!r}; choose from {known}")
    return _FACTORIES[kind](model.strip())
