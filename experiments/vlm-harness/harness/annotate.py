"""Draw a prediction on a copy of its frame so accuracy can be judged by eye.

Valid rows get a crosshair at the predicted foot point and the zone name. Invalid rows
get a red banner with the reason. The original frame is never modified.

Deliberately does not judge correctness; if a label exists it is printed next to the
prediction for the viewer.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

GREEN = (60, 200, 60)
RED = (40, 40, 220)
YELLOW = (0, 215, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def _text_box(img: np.ndarray, text: str, origin: tuple[int, int], color: tuple[int, int, int]) -> None:
    font, scale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1
    (w, h), base = cv2.getTextSize(text, font, scale, thick)
    x, y = origin
    cv2.rectangle(img, (x - 3, y - h - 4), (x + w + 3, y + base + 2), BLACK, -1)
    cv2.putText(img, text, (x, y), font, scale, color, thick, cv2.LINE_AA)


def annotate(
    image: np.ndarray,
    *,
    title: str,
    status: str,
    reason: str,
    zone: str | None,
    foot_px: tuple[int, int] | None,
    label_zone: str | None,
) -> np.ndarray:
    out = image.copy()
    _text_box(out, title, (8, 22), WHITE)
    if status == "ok":
        _text_box(out, f"zone: {zone}", (8, 46), GREEN)
        if foot_px is not None:
            x, y = foot_px
            cv2.drawMarker(out, (x, y), BLACK, cv2.MARKER_CROSS, 26, 5, cv2.LINE_AA)
            cv2.drawMarker(out, (x, y), YELLOW, cv2.MARKER_CROSS, 24, 2, cv2.LINE_AA)
            cv2.circle(out, (x, y), 9, YELLOW, 2, cv2.LINE_AA)
    else:
        _text_box(out, f"{status}: {reason}"[:90], (8, 46), RED)
    if label_zone:
        match = "OK" if status == "ok" and zone == label_zone else "X"
        _text_box(out, f"label: {label_zone} [{match}]", (8, 70), GREEN if match == "OK" else RED)
    return out


def write_jpeg(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise OSError(f"could not encode {path}")
    path.write_bytes(buf.tobytes())  # avoids cv2.imwrite's trouble with non-ASCII Windows paths
