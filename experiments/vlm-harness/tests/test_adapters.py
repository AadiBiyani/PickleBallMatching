"""Acceptance cases 10-11: Gemini and Ollama adapters with stubs (no network, no key, no Ollama)."""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from harness.analyzers.base import RateLimited, RequestFailed
from harness.analyzers.gemini import GeminiAnalyzer, _classify
from harness.analyzers.ollama import OllamaAnalyzer
from harness.contract import response_json_schema
from harness.frames import extract_frames

SCHEMA = response_json_schema()


@pytest.fixture(scope="module")
def frames(video_small):
    return extract_frames(video_small)


class Recorder:
    def __init__(self, reply="{}", exc=None):
        self.reply, self.exc, self.calls = reply, exc, []

    def create(self, **kw):
        self.calls.append(kw)
        if self.exc:
            raise self.exc
        return type("I", (), {"output_text": self.reply})()


def gemini_with(recorder):
    client = type("C", (), {"interactions": recorder})()
    return GeminiAnalyzer("gemini-3.8-flash", client=client)


def test_gemini_request_shape(frames):
    rec = Recorder(reply='{"frames": []}')
    text = gemini_with(rec).request(frames, "PROMPT", SCHEMA, temperature=0.5)
    assert text == '{"frames": []}'
    kw = rec.calls[0]
    assert kw["model"] == "gemini-3.8-flash"
    assert kw["store"] is False
    assert kw["response_format"] == {"type": "text", "mime_type": "application/json", "schema": SCHEMA}
    assert kw["generation_config"] == {"temperature": 0.5}
    parts = kw["input"]
    assert parts[0] == {"type": "text", "text": "PROMPT"}
    images = [p for p in parts if p["type"] == "image"]
    assert len(images) == 5 and {p["mime_type"] for p in images} == {"image/jpeg"}
    assert base64.b64decode(images[0]["data"]) == frames[0].jpeg
    captions = [p["text"] for p in parts[1:] if p["type"] == "text"]
    assert captions == [f"Frame {i} (t={i:.1f} s):" for i in range(5)]
    # caption directly precedes its image
    assert parts[1]["type"] == "text" and parts[2]["type"] == "image"


def test_gemini_default_temperature_not_sent(frames):
    rec = Recorder()
    gemini_with(rec).request(frames[:1], "P", SCHEMA, temperature=None)
    assert "generation_config" not in rec.calls[0]


def test_gemini_missing_key_is_readable(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RequestFailed, match="GEMINI_API_KEY is not set"):
        GeminiAnalyzer("gemini-3.8-flash").check_ready()


class FakeAPIError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def test_gemini_error_classification(frames):
    e = _classify(FakeAPIError(429, "RESOURCE_EXHAUSTED ... 'retryDelay': '37s'"))
    assert isinstance(e, RateLimited) and e.retry_after_s == 37.0 and not e.quota_exhausted
    e = _classify(FakeAPIError(429, "quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier"))
    assert isinstance(e, RateLimited) and e.quota_exhausted
    e = _classify(FakeAPIError(500, "internal"))
    assert isinstance(e, RequestFailed)
    with pytest.raises(RateLimited):
        gemini_with(Recorder(exc=FakeAPIError(429, "RESOURCE_EXHAUSTED"))).request(frames[:1], "P", SCHEMA, None)


def ollama_with(handler):
    return OllamaAnalyzer("qwen3-vl:8b", transport=httpx.MockTransport(handler), host="http://ollama.test")


def test_ollama_payload_shape(frames):
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": '{"frames": []}'}})

    text = ollama_with(handler).request(frames, "PROMPT", SCHEMA, temperature=0.2)
    assert text == '{"frames": []}'
    body = seen["body"]
    assert seen["url"] == "http://ollama.test/api/chat"
    assert body["model"] == "qwen3-vl:8b" and body["stream"] is False and body["format"] == SCHEMA
    assert body["options"] == {"temperature": 0.2}
    msg = body["messages"][0]
    assert len(msg["images"]) == 5 and base64.b64decode(msg["images"][4]) == frames[4].jpeg
    assert "Image 5: Frame 4 (t=4.0 s):" in msg["content"]


def test_ollama_connection_refused_is_readable(frames):
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(RequestFailed, match="is Ollama running"):
        ollama_with(handler).request(frames[:1], "P", SCHEMA, None)


def test_ollama_model_not_pulled(frames):
    with pytest.raises(RequestFailed, match="ollama pull qwen3-vl:8b"):
        ollama_with(lambda r: httpx.Response(404, json={"error": "model not found"})).request(frames[:1], "P", SCHEMA, None)
