"""Ollama adapter for local vision models (e.g. qwen3-vl:8b, gemma4:12b-it-qat).

POSTs to the local Ollama server's /api/chat with the batch's JPEGs as base64 `images`
on one user message, the frame captions listed in image order in the text, and the
shared JSON schema as `format`. Nothing leaves the machine.

Host comes from OLLAMA_HOST (default http://localhost:11434).

Deliberately does not validate output, retry, or cache (see contract, throttle, cache).
"""

from __future__ import annotations

import base64
import os
from collections.abc import Sequence
from typing import Any

import httpx

from ..frames import Frame
from .base import RateLimited, RequestFailed, frame_caption

DEFAULT_HOST = "http://localhost:11434"
REQUEST_TIMEOUT_S = 900.0   # first call loads the model; large batches on a laptop GPU are slow


class OllamaAnalyzer:
    kind = "ollama"
    is_remote = False
    default_batch_size: int | None = 8   # keeps image tokens + KV cache within an 8 GB GPU
    default_min_interval_s = 0.0
    notice = None

    def __init__(self, model_id: str, transport: httpx.BaseTransport | None = None, host: str | None = None) -> None:
        self.model_id = model_id
        self.host = (host or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/")
        if not self.host.startswith("http"):
            self.host = "http://" + self.host
        self._client = httpx.Client(base_url=self.host, timeout=REQUEST_TIMEOUT_S, transport=transport)

    @property
    def name(self) -> str:
        return f"ollama:{self.model_id}"

    def build_payload(self, frames: Sequence[Frame], prompt: str, schema: dict, temperature: float | None) -> dict:
        order = "\n".join(f"Image {n + 1}: {frame_caption(f)}" for n, f in enumerate(frames))
        content = f"{prompt}\n\nThe images are attached in this order:\n{order}"
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                    "images": [base64.b64encode(f.jpeg).decode("ascii") for f in frames],
                }
            ],
            "format": schema,
            "stream": False,
        }
        if temperature is not None:
            payload["options"] = {"temperature": temperature}
        return payload

    def request(self, frames: Sequence[Frame], prompt: str, schema: dict, temperature: float | None) -> str:
        payload = self.build_payload(frames, prompt, schema, temperature)
        try:
            resp = self._client.post("/api/chat", json=payload)
        except httpx.ConnectError as exc:
            raise RequestFailed(
                f"Could not reach Ollama at {self.host}: is Ollama running? "
                f"Install from https://ollama.com, then `ollama pull {self.model_id}`."
            ) from exc
        except httpx.HTTPError as exc:
            raise RequestFailed(f"Ollama request failed ({type(exc).__name__}): {exc}") from exc
        if resp.status_code == 429:
            raise RateLimited("Ollama server busy (429)")
        if resp.status_code == 404:
            raise RequestFailed(f"Ollama model {self.model_id!r} not found. Run `ollama pull {self.model_id}`.")
        if resp.status_code >= 400:
            raise RequestFailed(f"Ollama HTTP {resp.status_code}: {resp.text[:300]}")
        try:
            return resp.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise RequestFailed(f"Unexpected Ollama reply shape: {resp.text[:300]}") from exc
