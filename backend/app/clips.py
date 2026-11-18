"""Pre-recorded clips that stand in for a real recording upload."""

from pathlib import Path

from .schemas import Clip

CLIP_DIR = Path(__file__).resolve().parent.parent / "sample_clips"
SYNTHETIC = Clip(id="synthetic", name="Synthetic clip (no video)", synthetic=True)
_EXTENSIONS = {".mp4", ".mov"}


def list_clips() -> list[Clip]:
    clips = [
        Clip(id=p.name, name=p.stem, size_mb=round(p.stat().st_size / 1_000_000, 1))
        for p in sorted(CLIP_DIR.glob("*"))
        if p.suffix.lower() in _EXTENSIONS
    ]
    return clips + [SYNTHETIC]


def resolve(clip_id: str) -> tuple[Clip, Path | None] | None:
    """Return the clip and its file path (None for synthetic), or None if unknown."""
    if clip_id == SYNTHETIC.id:
        return SYNTHETIC, None
    for clip in list_clips():
        if clip.id == clip_id:
            return clip, CLIP_DIR / clip_id
    return None
