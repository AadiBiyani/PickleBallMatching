"""Gemini API adapter (free tier) using the google-genai Interactions API.

Sends all frames of a batch inline as base64 JPEG parts, each preceded by its caption,
with the shared JSON schema as `response_format`. Uses `store=False` so the interaction
is not kept server-side. Free-tier content may still be used by Google to improve its
products; `notice` carries that reminder and the CLI prints it.

Model IDs checked against aistudio.google.com/docs on 2026-11-16: `gemini-3.8-flash`
(default) and `gemini-4-hydrogen` are on the free tier; Gemini 4 Carbon and Argon are not.

Deliberately does not validate output, retry, or cache (see contract, throttle, cache).
"""

from __future__ import annotations

import base64
import os
import re
from collections.abc import Sequence
from typing import Any

from ..frames import Frame
from .base import RateLimited, RequestFailed, frame_caption

API_KEY_ENV = "GEMINI_API_KEY"
FREE_TIER_NOTICE = (
    "Note: Gemini free-tier requests may be used by Google to improve its products. "
    "Send only footage everyone in it agreed to (SYS-08)."
)
_RETRY_DELAY_RE = re.compile(r"retry[_ ]?delay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", re.IGNORECASE)


class GeminiAnalyzer:
    kind = "gemini"
    is_remote = True
    default_batch_size: int | None = None      # whole clip in one request
    default_min_interval_s = 10.0
    notice = FREE_TIER_NOTICE

    def __init__(self, model_id: str, client: Any | None = None) -> None:
        self.model_id = model_id
        self._client = client

    @property
    def name(self) -> str:
        return f"gemini:{self.model_id}"

    def _get_client(self) -> Any:
        if self._client is None:
            key = os.environ.get(API_KEY_ENV, "").strip()
            if not key:
                raise RequestFailed(
                    f"{API_KEY_ENV} is not set. Put it in the repo-root .env (see .env.example); "
                    "get a free key at https://aistudio.google.com/apikey"
                )
            from google import genai  # imported lazily so tests and Ollama runs need no SDK setup

            self._client = genai.Client(api_key=key)
        return self._client

    def check_ready(self) -> None:
        """Fail fast (before any frame is sent) if the API key is missing."""
        self._get_client()

    def build_input(self, frames: Sequence[Frame], prompt: str) -> list[dict]:
        parts: list[dict] = [{"type": "text", "text": prompt}]
        for f in frames:
            parts.append({"type": "text", "text": frame_caption(f)})
            parts.append({"type": "image", "data": base64.b64encode(f.jpeg).decode("ascii"), "mime_type": "image/jpeg"})
        return parts

    def request(self, frames: Sequence[Frame], prompt: str, schema: dict, temperature: float | None) -> str:
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "input": self.build_input(frames, prompt),
            "response_format": {"type": "text", "mime_type": "application/json", "schema": schema},
            "store": False,
        }
        if temperature is not None:
            kwargs["generation_config"] = {"temperature": temperature}
        try:
            interaction = client.interactions.create(**kwargs)
        except Exception as exc:  # SDK error classes vary by version; classify by code/text
            raise _classify(exc) from exc
        text = getattr(interaction, "output_text", None)
        if text is None:
            raise RequestFailed("Gemini response had no output_text")
        return text


def _classify(exc: Exception) -> Exception:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    text = str(exc)
    if code == 429 or "RESOURCE_EXHAUSTED" in text:
        match = _RETRY_DELAY_RE.search(text)
        retry_after = float(match.group(1)) if match else None
        per_day = "PerDay" in text or "per day" in text.lower()
        return RateLimited(f"Gemini rate limit: {text[:300]}", retry_after, quota_exhausted=per_day)
    return RequestFailed(f"Gemini request failed ({type(exc).__name__}): {text[:300]}")
