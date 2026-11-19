"""Pre-recorded clips that stand in for a real recording upload, and their court corners.

Corners use the harness's registry format (see `corners.example.json`), so a
`corners.json` made with the harness's `mark_corners.py` can be copied into
`sample_clips/` unchanged. Corners are in the video's native pixels, in the
order far-left, far-right, near-right, near-left.
"""

import json
import os
from pathlib import Path

from . import court
from .schemas import Clip

CLIP_DIR = Path(__file__).resolve().parent.parent / "sample_clips"
CORNERS_PATH = CLIP_DIR / "corners.json"
# Precomputed runs for export-backed models (YOLO), keyed by model id then clip file name.
# See exports.example.json. Paths inside are relative to sample_clips/.
EXPORTS_PATH = CLIP_DIR / "exports.json"
# Browser-playable copies made by scripts/make_preview.py; shown in the app, never analyzed.
PREVIEW_SUFFIX = ".preview"
# The prototype's fixed demo clip: the "recording" the camera screens play back and the
# model screen analyzes. Falls back to the clip picker when the file is absent.
DEMO_CLIP = os.environ.get("PBM_DEMO_CLIP", "test-60s.mp4")
_EXTENSIONS = {".mp4", ".mov"}

# The synthetic clip's "camera": the same corners as the harness's corners.example.json.
SYNTHETIC_SIZE = (1920, 1080)
SYNTHETIC_CORNERS = ((420.0, 180.0), (1500.0, 180.0), (1760.0, 980.0), (160.0, 980.0))
SYNTHETIC = Clip(id="synthetic", name="Synthetic clip (no video)", synthetic=True, has_corners=True)


def _registry() -> dict:
    if not CORNERS_PATH.is_file():
        return {}
    try:
        data = json.loads(CORNERS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise court.CalibrationError(f"{CORNERS_PATH.name} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("videos"), dict):
        raise court.CalibrationError(f"{CORNERS_PATH.name} is not a corner registry")
    return data["videos"]


def _exports() -> dict:
    if not EXPORTS_PATH.is_file():
        return {}
    try:
        data = json.loads(EXPORTS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def yolo_args(clip_id: str) -> list[str] | None:
    """Harness CLI args to replay a registered YOLO export for this clip, or None if there is none.

    Entry shape: {"positions": "<file in sample_clips>", "player_id": "player_1",
                  "start_frame": 600, "stop_frame": 890}
    """
    entry = _exports().get("yolo", {}).get(clip_id)
    if not isinstance(entry, dict) or not entry.get("positions") or not entry.get("player_id"):
        return None
    positions = CLIP_DIR / entry["positions"]
    if not positions.is_file():
        return None
    args = ["--positions", str(positions), "--player-id", str(entry["player_id"])]
    if entry.get("start_frame") is not None:
        args += ["--start-frame", str(int(entry["start_frame"]))]
    if entry.get("stop_frame") is not None:
        args += ["--stop-frame", str(int(entry["stop_frame"]))]
    return args


_EXPORT_READERS = {"yolo": yolo_args}


def list_clips() -> list[Clip]:
    try:
        videos = _registry()
    except court.CalibrationError:
        videos = {}
    clips = [
        Clip(
            id=p.name,
            name=p.stem,
            size_mb=round(p.stat().st_size / 1_000_000, 1),
            has_corners=p.name in videos,
            exports=[model_id for model_id, read in _EXPORT_READERS.items() if read(p.name) is not None],
            preview_url=f"/api/clips/{p.name}/preview" if preview_path(p.name) else None,
        )
        for p in sorted(CLIP_DIR.glob("*"))
        if p.suffix.lower() in _EXTENSIONS and not p.stem.endswith(PREVIEW_SUFFIX)
    ]
    return clips + [SYNTHETIC]


def preview_path(clip_id: str) -> Path | None:
    """The browser-playable copy of a clip, if one was made."""
    path = CLIP_DIR / f"{Path(clip_id).stem}{PREVIEW_SUFFIX}.mp4"
    return path if path.is_file() else None


def demo_clip() -> Clip | None:
    """The fixed demo clip, if it is present in sample_clips."""
    return next((c for c in list_clips() if c.id == DEMO_CLIP), None)


def resolve(clip_id: str) -> tuple[Clip, Path | None] | None:
    """Return the clip and its file path (None for synthetic), or None if unknown."""
    if clip_id == SYNTHETIC.id:
        return SYNTHETIC, None
    for clip in list_clips():
        if clip.id == clip_id:
            return clip, CLIP_DIR / clip_id
    return None


def corners_for(clip_id: str, width: int, height: int) -> list[court.Point]:
    """Saved corners for a clip, checked the same way the harness checks them."""
    if clip_id == SYNTHETIC.id:
        corners = list(SYNTHETIC_CORNERS)
        return court.scale_corners(corners, SYNTHETIC_SIZE, (width, height))
    videos = _registry()
    if clip_id not in videos:
        raise court.CalibrationError(
            f"No court corners saved for {clip_id}. Mark them with the harness's mark_corners.py "
            f"and add the entry to sample_clips/{CORNERS_PATH.name}."
        )
    raw = videos[clip_id]
    if (int(raw["width"]), int(raw["height"])) != (width, height):
        raise court.CalibrationError(
            f"{clip_id} is {width}x{height}, but its saved corners are for {raw['width']}x{raw['height']}"
        )
    if tuple(raw.get("corner_order", ())) != court.CORNER_ORDER:
        raise court.CalibrationError(f"{clip_id} corner_order must be {list(court.CORNER_ORDER)}")
    corners = [(float(x), float(y)) for x, y in raw["corners_px"]]
    problems = court.validate_corners(corners, width, height)
    if problems:
        raise court.CalibrationError(f"Saved corners for {clip_id} are unusable: {'; '.join(problems)}")
    return corners
