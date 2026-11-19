"""Prototype bridge: run each model in its own environment, never in the API process."""

import json
import os
import subprocess
import threading
from pathlib import Path

from .base import VisionModel

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "backend" / "runtime"
WORKER = ROOT / "backend" / "worker.py"
# Serialize previews and analysis too: a model process must not compete with another job.
_worker_lock = threading.Lock()


def interpreter(kind: str) -> Path:
    experiment = "player-tracking-yolo" if kind == "yolo" else "vlm-harness"
    default = (
        ROOT
        / "experiments"
        / experiment
        / ".venv"
        / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    return Path(os.environ.get(f"{kind.upper()}_PYTHON", str(default))).expanduser().absolute()


class WorkerModel(VisionModel):
    output_space = "image"
    sample_fps = 1.0
    version = "integration-1"

    def __init__(self, kind, model_id, name, owner, description):
        self.kind, self.model_id = kind, model_id
        self.id = f"{kind}:{model_id}"
        self.name, self.owner, self.description = name, owner, description

    def info(self):
        available = interpreter(self.kind).is_file()
        return (
            super()
            .info()
            .model_copy(
                update={
                    "available": available,
                    "unavailable_reason": None
                    if available
                    else f"Set up the {self.kind} worker environment; see backend/README.md.",
                    "selection_mode": "multiple" if self.kind == "yolo" else "first_pose",
                    "requires_calibration": True,
                }
            )
        )

    def locate(self, frames):
        raise ValueError(
            "Real tracking needs a session, source video and calibration; use the worker pipeline."
        )


def invoke(kind: str, request: dict, directory: Path, *, timeout=600) -> dict:
    python = interpreter(kind)
    if not python.is_file():
        raise ValueError(f"The {kind} environment is unavailable. See backend/README.md.")
    directory.mkdir(parents=True, exist_ok=True)
    request_file = directory / "request.json"
    request_file.write_text(json.dumps(request, allow_nan=False), encoding="utf-8")
    with _worker_lock:
        try:
            completed = subprocess.run(
                [str(python), str(WORKER), str(request_file)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f"The {kind} worker exceeded {timeout} seconds. Try a shorter window.") from exc
    (directory / "worker.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    response = directory / "response.json"
    if not response.is_file():
        raise ValueError(f"The {kind} worker stopped without a result. Check its local worker.log.")
    data = json.loads(response.read_text(encoding="utf-8"))
    if completed.returncode or "error" in data:
        raise ValueError(data.get("error", f"The {kind} worker failed."))
    return data
