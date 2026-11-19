"""Pack the demo kit: the footage and calibration the full demo needs, which git does not hold.

The clip shows identifiable players, so it is gitignored and shared through the
team drive instead (SDP SYS-08). This bundles, for one clip in backend/sample_clips:

    <clip>                      the analysis clip (exact bytes; YOLO's export is tied to its SHA-256)
    corners.json                only this clip's court-corner entry (harness registry format)
    exports.json                only this clip's YOLO export entry, if one is registered
    <positions file>            the YOLO tracking export named by that entry
    kit.json                    manifest: file sizes and SHA-256, provenance, how to install
    README.txt                  short human instructions

The browser preview is not packed; setup_demo.py regenerates it.

    .\\backend\\.venv\\Scripts\\python.exe backend\\scripts\\make_demo_kit.py --clip test-60s.mp4 --out demo-kit
    (macOS/Linux: backend/.venv/bin/python backend/scripts/make_demo_kit.py ...)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SAMPLE_CLIPS = Path(__file__).resolve().parents[1] / "sample_clips"
KIT_VERSION = 1

README = """PickleBall Matching - demo kit (version {version})
==================================================

Contents: {clip} (the prototype's demo "recording"), its court corners, and
{yolo_line}

Install it from the repository root (see docs/DEMO.md for the whole guide):

    Windows:      .\\backend\\.venv\\Scripts\\python.exe backend\\scripts\\setup_demo.py PATH\\TO\\{zip_name} --models
    macOS/Linux:  backend/.venv/bin/python backend/scripts/setup_demo.py path/to/{zip_name} --models

Privacy: the clip shows identifiable people. Share it only within the team, never
commit it to git, and do not send it to remote models (e.g. Gemini) unless
everyone in it has agreed to third-party processing.
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pack the demo kit for one clip in backend/sample_clips.")
    parser.add_argument("--clip", default="test-60s.mp4", help="clip file name in backend/sample_clips")
    parser.add_argument("--out", type=Path, default=Path("demo-kit"), help="output folder for the zip")
    parser.add_argument("--note", default="", help="free-text provenance recorded in kit.json")
    args = parser.parse_args(argv)

    clip = SAMPLE_CLIPS / args.clip
    if not clip.is_file():
        print(f"error: {clip} not found", file=sys.stderr)
        return 2
    registry = json.loads((SAMPLE_CLIPS / "corners.json").read_text(encoding="utf-8"))
    corner_entry = registry.get("videos", {}).get(args.clip)
    if corner_entry is None:
        print(f"error: no corners saved for {args.clip} in sample_clips/corners.json", file=sys.stderr)
        return 2

    clip_sha = sha256(clip)
    files: dict[str, Path] = {args.clip: clip}
    corners = {"videos": {args.clip: corner_entry}}
    exports: dict = {}
    yolo = None
    exports_path = SAMPLE_CLIPS / "exports.json"
    if exports_path.is_file():
        entry = json.loads(exports_path.read_text(encoding="utf-8")).get("yolo", {}).get(args.clip)
        if entry:
            positions = SAMPLE_CLIPS / entry["positions"]
            meta = json.loads(positions.read_text(encoding="utf-8"))["metadata"]
            if meta["source"]["sha256"] != clip_sha:
                print("error: the YOLO export was tracked on a different file than this clip", file=sys.stderr)
                return 2
            files[entry["positions"]] = positions
            exports = {"yolo": {args.clip: entry}}
            yolo = {
                "player_id": entry["player_id"],
                "frames": [entry.get("start_frame"), entry.get("stop_frame")],
                "note": entry.get("note", ""),
                "model": meta.get("model_name"),
            }

    manifest = {
        "kit_version": KIT_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "demo_clip": args.clip,
        "note": args.note,
        "clip": {
            "width": corner_entry["width"],
            "height": corner_entry["height"],
            "corners_note": corner_entry.get("note", ""),
        },
        "yolo": yolo,
        "files": {
            name: {"bytes": path.stat().st_size, "sha256": clip_sha if path == clip else sha256(path)}
            for name, path in files.items()
        },
        "install": "python backend/scripts/setup_demo.py <this zip> --models  (see docs/DEMO.md)",
    }

    args.out.mkdir(parents=True, exist_ok=True)
    zip_name = f"pickleball-demo-kit-{Path(args.clip).stem}.zip"
    zip_path = args.out / zip_name
    yolo_line = (
        f"a YOLO tracking run ({yolo['player_id']}: {yolo['note'] or 'see kit.json'})." if yolo else "no YOLO run."
    )
    with zipfile.ZipFile(zip_path, "w") as z:
        for name, path in files.items():
            # Video does not compress; store it. JSON is deflated.
            mode = zipfile.ZIP_STORED if path.suffix.lower() in (".mp4", ".mov") else zipfile.ZIP_DEFLATED
            z.write(path, name, compress_type=mode)
        z.writestr("corners.json", json.dumps(corners, indent=2) + "\n", zipfile.ZIP_DEFLATED)
        if exports:
            z.writestr("exports.json", json.dumps(exports, indent=2) + "\n", zipfile.ZIP_DEFLATED)
        z.writestr("kit.json", json.dumps(manifest, indent=2) + "\n", zipfile.ZIP_DEFLATED)
        z.writestr(
            "README.txt",
            README.format(version=KIT_VERSION, clip=args.clip, yolo_line=yolo_line, zip_name=zip_name),
            zipfile.ZIP_DEFLATED,
        )
    print(f"wrote {zip_path} ({zip_path.stat().st_size / 1e6:.1f} MB): {', '.join(files)} + corners/exports/kit.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
