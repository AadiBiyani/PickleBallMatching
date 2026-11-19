"""Ultralytics adapter. Importing the package or running fake tests downloads nothing."""

import os
import time
from pathlib import Path

from .contracts import BoundingBox, Detection, InputError, TrackingConfig

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
WEIGHTS = RUNTIME / "weights" / "yolo26n-pose.pt"
TRACKER_CONFIG = Path(__file__).with_name("bytetrack.yaml")


def prepare_model() -> dict:
    WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(RUNTIME / "ultralytics"))
    from ultralytics.utils.downloads import attempt_download_asset

    existed = WEIGHTS.exists()
    start = time.perf_counter()
    downloaded = Path(attempt_download_asset(str(WEIGHTS)))
    if not downloaded.is_file():
        raise InputError("Official model download did not produce a weight file.")
    from .video import sha256_file

    return {
        "path": str(downloaded),
        "already_present": existed,
        "download_elapsed_s": time.perf_counter() - start,
        "sha256": sha256_file(downloaded),
    }


class YoloBackend:
    def __init__(self, config: TrackingConfig):
        if not WEIGHTS.is_file():
            raise InputError("Model weights are missing. Run: player-tracker prepare-model")
        os.environ.setdefault("YOLO_CONFIG_DIR", str(RUNTIME / "ultralytics"))
        start = time.perf_counter()
        import torch
        from ultralytics import YOLO

        if config.device == "mps" and not torch.backends.mps.is_available():
            raise InputError("MPS is unavailable on this machine. Use device=cpu.")
        self.config = config
        # A fresh instance per preview/run prevents persistent tracker state leaking.
        self.model = YOLO(str(WEIGHTS), task="pose")
        self.load_seconds = time.perf_counter() - start

    def detect(self, frame, *, track: bool) -> list[Detection]:
        options = {
            "imgsz": self.config.image_size,
            "conf": self.config.detection_confidence,
            "device": self.config.device,
            "classes": [0],
            "verbose": False,
        }
        if track:
            result = self.model.track(frame, persist=True, tracker=str(TRACKER_CONFIG), **options)[0]
        else:
            result = self.model.predict(frame, **options)[0]
        if result.boxes is None:
            return []
        boxes = result.boxes.xyxy.cpu().tolist()
        confidences = result.boxes.conf.cpu().tolist()
        ids = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None] * len(boxes)
        # .xy is mapped by Ultralytics back to the original frame, not letterbox input pixels.
        keypoints = result.keypoints.xy.cpu().tolist() if result.keypoints is not None else []
        scores = (
            result.keypoints.conf.cpu().tolist()
            if result.keypoints is not None and result.keypoints.conf is not None
            else []
        )
        detections = []
        for index, (box, confidence, track_id) in enumerate(zip(boxes, confidences, ids, strict=True)):
            ankles = []
            for key in (15, 16):
                if index < len(keypoints) and index < len(scores) and key < len(keypoints[index]):
                    ankles.append((*keypoints[index][key], scores[index][key]))
                else:
                    ankles.append(None)
            detections.append(
                Detection(
                    BoundingBox(x1=box[0], y1=box[1], x2=box[2], y2=box[3]),
                    confidence,
                    track_id,
                    ankles[0],
                    ankles[1],
                )
            )
        return detections
