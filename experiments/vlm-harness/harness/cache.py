"""On-disk cache of raw model responses, so reruns cost no quota.

One JSON file per request, keyed by everything that could change the answer.
Only real responses are stored, valid or not. Request errors are never cached,
so a rerun tries them again. The cache lives under output/, which is gitignored.

Copied from liam-test-harness (harness/cache.py); the key is now built by the
caller from a dict, so each analyzer names its own inputs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class CachedResponse:
    raw_text: str
    latency_s: float
    fetched_at: str
    path: Path


def cache_key(inputs: dict) -> str:
    payload = json.dumps(inputs, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def path_for(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> CachedResponse | None:
        path = self.path_for(key)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return CachedResponse(data["raw_text"], float(data["latency_s"]), data["fetched_at"], path)

    def put(self, key: str, raw_text: str, latency_s: float, meta: dict) -> CachedResponse:
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record = {"raw_text": raw_text, "latency_s": latency_s, "fetched_at": fetched_at, "meta": meta}
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
        temporary.replace(path)
        return CachedResponse(raw_text, latency_s, fetched_at, path)
