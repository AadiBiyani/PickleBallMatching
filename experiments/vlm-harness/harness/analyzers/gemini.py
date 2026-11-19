"""Gemini API (free tier) as a harness analyzer.

locate() sends the sampled frames inline as JPEG parts, each preceded by a
caption with its frame index, and asks for the foot point of one player as
integers 0-1000 normalized to the image. It converts each point to pixels of
the frame it was given. It never sees the court corners and never picks a zone:
the harness applies the homography and derives the zone.

Ported from liam-test-harness (harness/analyzers/gemini.py and harness/run.py):
the request shape, error classification, throttling and cache are unchanged;
the model-chosen zone and the repeats loop are removed.

Model IDs checked against aistudio.google.com/docs on 2026-11-16:
`gemini-3.8-flash` (default) and `gemini-4-hydrogen` are on the free tier.

Frames go to Google. The runner refuses remote analyzers unless consent is
confirmed (SYS-08), and this module carries a free-tier reminder in `notice`.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import cv2

from ..cache import ResponseCache, cache_key
from ..contract import LocatedPoint
from ..frames import Frame, resize_long_side
from ..throttle import Throttle
from . import foot_response as contract
from .base import AnalyzerRequestError, RateLimited

EXPERIMENT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_PROMPT = EXPERIMENT_DIR / "prompts" / "foot_gemini_v1.txt"
DEFAULT_CACHE = EXPERIMENT_DIR / "output" / "cache" / "gemini"
DEFAULT_SEND_LONG_SIDE = 960
DEFAULT_MIN_INTERVAL_S = 10.0
JPEG_QUALITY = 90

API_KEY_ENV = "GEMINI_API_KEY"
FREE_TIER_NOTICE = (
    "Note: Gemini free-tier requests may be used by Google to improve its products. "
    "Send only footage everyone in it agreed to (SYS-08)."
)
_RETRY_DELAY_RE = re.compile(r"retry[_ ]?delay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", re.IGNORECASE)


def frame_caption(frame: Frame) -> str:
    """Text placed immediately before each image so the model can index its answers."""
    return f"Frame {frame.index} (t={frame.time_s:.1f} s):"


def encode_jpeg(frame: Frame, long_side_px: int | None) -> bytes:
    """JPEG of the frame, downscaled (never upscaled) so its long side is at most long_side_px.

    The model answers in normalized coordinates, so sending a smaller copy does
    not change which pixel of the original frame a point refers to.
    """
    image = frame.image
    if long_side_px is not None and max(image.shape[:2]) > long_side_px:
        image = resize_long_side(image, long_side_px)
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise ValueError(f"JPEG encoding failed for frame {frame.index}")
    return buffer.tobytes()


def _classify(exc: Exception) -> AnalyzerRequestError:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    text = str(exc)
    if code == 429 or "RESOURCE_EXHAUSTED" in text:
        match = _RETRY_DELAY_RE.search(text)
        retry_after = float(match.group(1)) if match else None
        per_day = "PerDay" in text or "per day" in text.lower()
        return RateLimited(f"Gemini rate limit: {text[:300]}", retry_after, quota_exhausted=per_day)
    return AnalyzerRequestError(f"Gemini request failed ({type(exc).__name__}): {text[:300]}")


class GeminiAnalyzer:
    kind = "gemini"
    is_remote = True
    notice = FREE_TIER_NOTICE

    def __init__(
        self,
        model: str = "",
        *,
        prompt_path: str | Path | None = None,
        client: Any | None = None,
        temperature: float | None = None,
        batch_size: int | None = None,
        send_long_side_px: int | None = DEFAULT_SEND_LONG_SIDE,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        cache_dir: str | Path = DEFAULT_CACHE,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
        log: Callable[[str], None] = print,
    ) -> None:
        self.model_id = model.strip() or DEFAULT_MODEL
        path = Path(prompt_path) if prompt_path is not None else DEFAULT_PROMPT
        if not path.is_file():
            raise ValueError(f"prompt file not found: {path}")
        self.prompt_path = path
        self.prompt = path.read_text(encoding="utf-8")
        self.prompt_version = path.stem
        self.prompt_sha256 = hashlib.sha256(self.prompt.encode("utf-8")).hexdigest()
        if batch_size is not None and batch_size < 1:
            raise ValueError("batch size must be >= 1")
        self.temperature = temperature
        self.batch_size = batch_size
        self.send_long_side_px = send_long_side_px
        self._client = client
        self._cache = ResponseCache(cache_dir)
        throttle_options = {"min_interval_s": min_interval_s, "log": log}
        if clock is not None:
            throttle_options["clock"] = clock
        if sleep is not None:
            throttle_options["sleep"] = sleep
        self._throttle = Throttle(**throttle_options)
        self._log = log
        self._requests: list[dict] = []
        self._frames: list[dict] = []
        self._extra: list[int] = []

    def _get_client(self) -> Any:
        if self._client is None:
            key = os.environ.get(API_KEY_ENV, "").strip()
            if not key:
                raise AnalyzerRequestError(
                    f"{API_KEY_ENV} is not set. Put it in experiments/vlm-harness/.env or the repo-root .env "
                    "(see .env.example); get a free key at https://aistudio.google.com/apikey"
                )
            from google import genai  # imported lazily so other analyzers and tests need no SDK

            self._client = genai.Client(api_key=key)
        return self._client

    def build_input(self, frames: Sequence[Frame], jpegs: Sequence[bytes]) -> list[dict]:
        parts: list[dict] = [{"type": "text", "text": self.prompt}]
        for frame, jpeg in zip(frames, jpegs):
            parts.append({"type": "text", "text": frame_caption(frame)})
            parts.append(
                {"type": "image", "data": base64.b64encode(jpeg).decode("ascii"), "mime_type": "image/jpeg"}
            )
        return parts

    def _send(self, frames: Sequence[Frame], jpegs: Sequence[bytes]) -> str:
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "input": self.build_input(frames, jpegs),
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": contract.response_json_schema(),
            },
            "store": False,
        }
        if self.temperature is not None:
            kwargs["generation_config"] = {"temperature": self.temperature}
        try:
            interaction = client.interactions.create(**kwargs)
        except Exception as exc:  # SDK error classes vary by version; classify by code and text
            raise _classify(exc) from exc
        text = getattr(interaction, "output_text", None)
        if text is None:
            raise AnalyzerRequestError("Gemini response had no output_text")
        return text

    def _key(self, frames: Sequence[Frame], jpegs: Sequence[bytes]) -> str:
        return cache_key(
            {
                "analyzer": self.kind,
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "prompt_sha256": self.prompt_sha256,
                "temperature": self.temperature,
                "schema": contract.response_json_schema(),
                "frames": [
                    [f.index, round(f.time_s, 3), hashlib.sha256(j).hexdigest()]
                    for f, j in zip(frames, jpegs)
                ],
            }
        )

    def locate(self, frames: Sequence[Frame]) -> list[LocatedPoint]:
        self._requests, self._frames, self._extra = [], [], []
        jpegs = [encode_jpeg(frame, self.send_long_side_px) for frame in frames]
        size = self.batch_size or max(1, len(frames))
        located: list[LocatedPoint] = []
        for start in range(0, len(frames), size):
            batch = list(frames[start : start + size])
            batch_jpegs = jpegs[start : start + size]
            indices = [frame.index for frame in batch]
            key = self._key(batch, batch_jpegs)
            cached = self._cache.get(key)
            if cached is None:
                try:
                    text, latency = self._throttle.call(lambda: self._send(batch, batch_jpegs))
                except AnalyzerRequestError as exc:
                    if start:
                        exc.args = (
                            f"{exc} Earlier batches are cached; a rerun resumes at frame {indices[0]}.",
                        )
                    raise
                cached = self._cache.put(
                    key,
                    text,
                    latency,
                    {
                        "model_id": self.model_id,
                        "prompt_version": self.prompt_version,
                        "frame_indices": indices,
                    },
                )
                hit = False
            else:
                hit = True
            self._requests.append(
                {
                    "frame_indices": indices,
                    "cache_hit": hit,
                    "latency_s": cached.latency_s,
                    "fetched_at": cached.fetched_at,
                    "raw_response_path": str(cached.path),
                }
            )
            self._extra.extend(contract.extra_indices(cached.raw_text, indices))
            for frame, result in zip(batch, contract.parse_foot_response(cached.raw_text, indices)):
                self._frames.append(
                    {
                        "frame_index": frame.index,
                        "status": result.status,
                        "reason": result.reason,
                        "foot_x_norm": result.foot_x_norm,
                        "foot_y_norm": result.foot_y_norm,
                    }
                )
                if result.status == contract.STATUS_OK:
                    located.append(
                        LocatedPoint(
                            frame.index,
                            contract.norm_to_px(result.foot_x_norm, frame.width_px),
                            contract.norm_to_px(result.foot_y_norm, frame.height_px),
                        )
                    )
                else:
                    # Not visible and invalid answers both have no point; analyzer.json keeps which it was.
                    located.append(LocatedPoint(frame.index, None, None))
        return located

    def provenance(self) -> dict:
        """Written to analyzer.json by the runner: settings, every request, and every frame's outcome."""
        counts: dict[str, int] = {}
        for row in self._frames:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        return {
            "analyzer": self.kind,
            "model_id": self.model_id,
            "is_remote": self.is_remote,
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
            "temperature": "default" if self.temperature is None else self.temperature,
            "send_long_side_px": self.send_long_side_px,
            "jpeg_quality": JPEG_QUALITY,
            "batch_size": self.batch_size,
            "throttle_waits_s": list(self._throttle.waits_s),
            "status_counts": counts,
            "extra_frame_indices": sorted(set(self._extra)),
            "requests": self._requests,
            "frames": self._frames,
        }
