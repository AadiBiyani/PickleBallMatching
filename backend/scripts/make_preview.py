"""Make a browser-playable preview copy of a sample clip.

Clips written by OpenCV (for example a trimmed copy) use MPEG-4 Part 2 ("mp4v"),
which browsers do not play. This writes `<stem>.preview.mp4` next to the clip:
H.264, yuv420p, no audio, resized to a web-friendly width, with the index at the
start of the file so playback starts immediately. The original clip is never
modified, so its saved corners and any tracking exports stay valid.

The API serves the preview at GET /api/clips/{clip_id}/preview, and the app
plays it in the simulated camera screens. Preview files are not analysis clips.

Needs FFmpeg; the imageio-ffmpeg package bundles one:
    python -m pip install imageio-ffmpeg
    python backend/scripts/make_preview.py backend/sample_clips/test-60s.mp4
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("clip", type=Path, help="clip in backend/sample_clips")
    parser.add_argument("--width", type=int, default=1280, help="output width in px (height keeps the aspect ratio)")
    parser.add_argument("--crf", type=int, default=26, help="H.264 quality, lower is better (default 26)")
    args = parser.parse_args(argv)

    try:
        import imageio_ffmpeg
    except ImportError:
        print("error: install imageio-ffmpeg first: python -m pip install imageio-ffmpeg", file=sys.stderr)
        return 2
    if not args.clip.is_file():
        print(f"error: clip not found: {args.clip}", file=sys.stderr)
        return 2

    out = args.clip.with_name(f"{args.clip.stem}.preview.mp4")
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
        "-i", str(args.clip),
        "-an",
        "-vf", f"scale={args.width}:-2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(args.crf), "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out),
    ]  # fmt: skip
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"error: ffmpeg failed: {result.stderr.strip()}", file=sys.stderr)
        return result.returncode
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
