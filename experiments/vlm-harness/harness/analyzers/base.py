"""Analyzer interface, provider errors, and the registry that maps CLI specs to adapters.

An adapter only sends one request (a batch of frames plus prompt and schema) and returns
the model's raw text. Parsing, validation, caching, throttling and metrics are shared, so
adding a model means one new module and one entry in `_FACTORIES`.

Deliberately does not validate model output.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from ..frames import Frame


class RateLimited(Exception):
    """Provider said "too many requests". `quota_exhausted` means retrying today is pointless."""

    def __init__(self, message: str, retry_after_s: float | None = None, quota_exhausted: bool = False) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s
        self.quota_exhausted = quota_exhausted


class RequestFailed(Exception):
    """Any other failure to get a response (network, server error, bad config)."""


class Analyzer(Protocol):
    kind: str          # "gemini", "ollama", "fake"
    model_id: str      # exact model ID sent to the provider
    is_remote: bool    # True if frames leave this machine (consent required)
    default_batch_size: int | None   # None = all frames in one request
    default_min_interval_s: float

    @property
    def name(self) -> str: ...

    def request(self, frames: Sequence[Frame], prompt: str, schema: dict, temperature: float | None) -> str:
        """Send one request and return the raw response text. Raises RateLimited or RequestFailed."""
        ...


def frame_caption(frame: Frame) -> str:
    """Text placed immediately before each image so the model can index its answers."""
    return f"Frame {frame.index} (t={frame.time_s:.1f} s):"


def _make_gemini(model: str) -> Analyzer:
    from .gemini import GeminiAnalyzer

    return GeminiAnalyzer(model)


def _make_ollama(model: str) -> Analyzer:
    from .ollama import OllamaAnalyzer

    return OllamaAnalyzer(model)


def _make_fake(model: str) -> Analyzer:
    from .fake import FakeAnalyzer

    return FakeAnalyzer(model)


_FACTORIES: dict[str, Callable[[str], Analyzer]] = {
    "gemini": _make_gemini,
    "ollama": _make_ollama,
    "fake": _make_fake,
}

DEFAULT_MODELS = {"gemini": "gemini-3.8-flash"}


def create_analyzer(spec: str) -> Analyzer:
    """Build an analyzer from 'kind:model', e.g. 'gemini:gemini-3.8-flash', 'ollama:qwen3-vl:8b',
    'fake:valid'. 'gemini' alone uses the default model."""
    kind, _, model = spec.partition(":")
    kind = kind.strip().lower()
    if kind not in _FACTORIES:
        raise ValueError(f"unknown analyzer {kind!r} in {spec!r}; choose from {sorted(_FACTORIES)}")
    model = model.strip() or DEFAULT_MODELS.get(kind, "")
    if not model:
        raise ValueError(f"analyzer {spec!r} needs a model, e.g. '{kind}:<model>'")
    return _FACTORIES[kind](model)
