"""Load the corner registry and scale corners into the frame a model sees.

Corners are stored in the video's own pixels. A run that does not resize uses
them unchanged. A run that passes --long-side scales them by the same factor
as the frame.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


CORNER_ORDER = ("far-left", "far-right", "near-right", "near-left")


@dataclass(frozen=True)
class CornerEntry:
    width: int
    height: int
    corners_px: tuple[tuple[float, float], ...]


def load_registry(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"corner registry not found: {path}")
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("videos"), dict):
        raise ValueError(f"{path} is not a corner registry")
    return data


def entry_for(registry: dict, clip_name: str, video_width: int, video_height: int) -> CornerEntry:
    """Return the saved corners when the video dimensions match.

    clip_name is the file name, not a directory path. A different width or
    height is refused so a calibration cannot be applied to another frame size.
    """
    videos = registry["videos"]
    if clip_name not in videos:
        raise ValueError(f"no corners saved for {clip_name}")
    raw = videos[clip_name]
    width = int(raw["width"])
    height = int(raw["height"])
    if width != int(video_width) or height != int(video_height):
        raise ValueError(
            f"{clip_name} is {video_width}x{video_height}, "
            f"but the registry has {width}x{height}"
        )
    order = tuple(raw.get("corner_order", ()))
    if order != CORNER_ORDER:
        raise ValueError(f"{clip_name} corner_order must be {list(CORNER_ORDER)}")
    corners = tuple((float(x), float(y)) for x, y in raw["corners_px"])
    if len(corners) != 4:
        raise ValueError(f"{clip_name} must have 4 corners")
    return CornerEntry(width, height, corners)


def scale_corners(entry: CornerEntry, frame_width: int, frame_height: int) -> list[list[float]]:
    """Map saved corners into the frame the model was shown."""
    sx = float(frame_width) / float(entry.width)
    sy = float(frame_height) / float(entry.height)
    return [[x * sx, y * sy] for x, y in entry.corners_px]
