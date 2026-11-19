"""Install a demo kit (made by make_demo_kit.py) so this clone can run the full demo.

Run it from the repository root with the backend's Python (see docs/DEMO.md):

    Windows:      .\\backend\\.venv\\Scripts\\python.exe backend\\scripts\\setup_demo.py PATH\\TO\\pickleball-demo-kit-test-60s.zip --models
    macOS/Linux:  backend/.venv/bin/python backend/scripts/setup_demo.py path/to/pickleball-demo-kit-test-60s.zip --models

Steps:
  1. Verify every file in the kit against the SHA-256 in kit.json.
  2. Copy the clip and YOLO export into backend/sample_clips/, and merge the clip's
     entries into sample_clips/corners.json and exports.json. Files or entries that
     already exist with different contents are left alone unless --force is given.
  3. Make the browser-playable preview (installs imageio-ffmpeg into this Python if
     needed; skip with --no-preview).
  4. With --models: build the MediaPipe environment (experiments/vlm-harness/.venv,
     Python 3.13 via uv unless --mediapipe-python is given) and the YOLO environment
     (experiments/player-tracking-yolo/.venv via `uv sync --frozen --python 3.12`).
  5. Ask the backend which demo pieces are ready.

Everything it writes is gitignored. Safe to re-run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
SAMPLE_CLIPS = BACKEND / "sample_clips"
HARNESS = REPO / "experiments" / "vlm-harness"
YOLO = REPO / "experiments" / "player-tracking-yolo"
SUPPORTED_KIT_VERSIONS = {1}


def say(msg: str) -> None:
    print(msg, flush=True)


def venv_python(venv: Path) -> Path:
    return venv / "Scripts" / "python.exe" if sys.platform == "win32" else venv / "bin" / "python"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path | None = None) -> None:
    say(f"    $ {' '.join(str(c) for c in cmd)}")
    # An activated venv (VIRTUAL_ENV) makes `uv sync` warn that it is ignoring it; drop it for children.
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    result = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env)
    if result.returncode != 0:
        raise SystemExit(f"error: command failed with exit code {result.returncode}")


# ---- 1-2: kit contents -----------------------------------------------------------


def open_kit(kit: Path, workdir: Path) -> Path:
    if kit.is_dir():
        return kit
    if kit.suffix.lower() != ".zip" or not kit.is_file():
        raise SystemExit(f"error: {kit} is not a kit zip or folder")
    with zipfile.ZipFile(kit) as z:
        for name in z.namelist():  # the kit is flat; refuse anything that would escape the folder
            if Path(name).name != name:
                raise SystemExit(f"error: unexpected path in kit: {name}")
        z.extractall(workdir)
    return workdir


def merge_entry(path: Path, section: list[str], key: str, value: dict, force: bool) -> str:
    """Put value at data[section...][key] in a JSON file, keeping all other entries."""
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    node = data
    for part in section:
        node = node.setdefault(part, {})
    if key in node and node[key] != value and not force:
        raise SystemExit(
            f"error: {path.name} already has a different entry for {key}. "
            "Re-run with --force to replace it with the kit's."
        )
    status = "unchanged" if node.get(key) == value else "added"
    node[key] = value
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return status


def install_kit(src: Path, force: bool) -> dict:
    manifest = json.loads((src / "kit.json").read_text(encoding="utf-8"))
    if manifest.get("kit_version") not in SUPPORTED_KIT_VERSIONS:
        raise SystemExit(f"error: kit version {manifest.get('kit_version')} is not supported by this script")
    say(f"[1/5] Verifying {len(manifest['files'])} files against kit.json")
    for name, info in manifest["files"].items():
        actual = sha256(src / name)
        if actual != info["sha256"]:
            raise SystemExit(f"error: {name} is corrupted (SHA-256 {actual[:12]}..., expected {info['sha256'][:12]}...)")
        say(f"    ok  {name} ({info['bytes'] / 1e6:.1f} MB)")

    say("[2/5] Installing into backend/sample_clips/")
    SAMPLE_CLIPS.mkdir(parents=True, exist_ok=True)
    for name, info in manifest["files"].items():
        dest = SAMPLE_CLIPS / name
        if dest.is_file() and sha256(dest) == info["sha256"]:
            say(f"    unchanged  {name}")
            continue
        if dest.exists() and not force:
            raise SystemExit(f"error: {dest} exists with different contents. Re-run with --force to replace it.")
        shutil.copy2(src / name, dest)
        say(f"    copied     {name}")
    clip = manifest["demo_clip"]
    corners = json.loads((src / "corners.json").read_text(encoding="utf-8"))["videos"][clip]
    say(f"    {merge_entry(SAMPLE_CLIPS / 'corners.json', ['videos'], clip, corners, force):10} corners for {clip}")
    if (src / "exports.json").is_file():
        for model_id, entries in json.loads((src / "exports.json").read_text(encoding="utf-8")).items():
            status = merge_entry(SAMPLE_CLIPS / "exports.json", [model_id], clip, entries[clip], force)
            say(f"    {status:10} {model_id} export for {clip}")
    return manifest


# ---- 3: preview ------------------------------------------------------------------------


def make_preview(clip: str) -> None:
    say("[3/5] Making the browser-playable preview")
    try:
        import imageio_ffmpeg  # noqa: F401
    except ImportError:
        say("    imageio-ffmpeg is missing; installing it into this Python")
        run([sys.executable, "-m", "pip", "install", "-q", "imageio-ffmpeg"])
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import make_preview as mp  # noqa: PLC0415

    if mp.main([str(SAMPLE_CLIPS / clip)]) != 0:
        raise SystemExit("error: making the preview failed")


# ---- 4: model environments ----------------------------------------------------------------


def find_python(version: str, override: str | None) -> str:
    if override:
        return override
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit(
            f"error: uv is not installed. Install uv (https://docs.astral.sh/uv/) or pass "
            f"--mediapipe-python with a Python {version} interpreter."
        )
    found = subprocess.run([uv, "python", "find", version], capture_output=True, text=True)
    if found.returncode != 0:
        run([uv, "python", "install", version])
        found = subprocess.run([uv, "python", "find", version], capture_output=True, text=True, check=True)
    return found.stdout.strip()


def setup_models(mediapipe_python: str | None) -> None:
    say("[4/5] Building the model environments (first time: a few minutes and about 1.5 GB)")
    venv = HARNESS / ".venv"
    if not venv_python(venv).is_file():
        python = find_python("3.13", mediapipe_python)
        say(f"    MediaPipe: creating {venv.relative_to(REPO)} with {python}")
        run([python, "-m", "venv", venv])
    else:
        say(f"    MediaPipe: {venv.relative_to(REPO)} exists; making sure requirements are installed")
    run([venv_python(venv), "-m", "pip", "install", "-q", "-r", HARNESS / "requirements.txt"])

    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("error: uv is required for the YOLO environment (https://docs.astral.sh/uv/)")
    say(f"    YOLO: syncing {YOLO.relative_to(REPO) / '.venv'} (locked, Python 3.12)")
    run([uv, "sync", "--frozen", "--python", "3.12"], cwd=YOLO)


# ---- 5: verify ---------------------------------------------------------------------------------


def verify(clip: str) -> None:
    say("[5/5] Asking the backend what is ready")
    sys.path.insert(0, str(BACKEND))
    try:
        from app import clips  # noqa: PLC0415
        from app.vision import MODELS  # noqa: PLC0415
    except ImportError as exc:
        say(f"    skipped: run this script with the backend's Python to check ({exc})")
        return
    demo = clips.demo_clip()
    if demo is None or demo.id != clip:
        say(f"    note: the app's demo clip is {clips.DEMO_CLIP!r}; set PBM_DEMO_CLIP={clip} to use this kit's clip")
        demo = next((c for c in clips.list_clips() if c.id == clip), None)
    checks = {
        "clip listed": demo is not None,
        "court corners": bool(demo and demo.has_corners),
        "YOLO export": bool(demo and "yolo" in demo.exports),
        "browser preview": bool(demo and demo.preview_url),
    }
    for model_id in ("mediapipe", "yolo"):
        reason = MODELS[model_id].unavailable_reason()
        checks[f"{model_id} model"] = reason is None
        if reason:
            say(f"    {model_id}: {reason}")
    for name, ok in checks.items():
        say(f"    {'ok ' if ok else 'MISSING'}  {name}")
    if all(checks.values()):
        say("Demo is ready. Start the servers as described in docs/DEMO.md.")
    else:
        say("Some pieces are missing (see above). The app still runs; missing models show as unavailable.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install a PickleBall Matching demo kit.")
    parser.add_argument("kit", type=Path, help="kit zip (or an unzipped kit folder)")
    parser.add_argument("--models", action="store_true", help="also build the MediaPipe and YOLO environments")
    parser.add_argument("--mediapipe-python", help="Python 3.12/3.13 interpreter for MediaPipe (default: uv's 3.13)")
    parser.add_argument("--no-preview", action="store_true", help="skip making the browser preview")
    parser.add_argument("--force", action="store_true", help="replace existing files or entries that differ")
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as tmp:
        manifest = install_kit(open_kit(args.kit, Path(tmp)), args.force)
    clip = manifest["demo_clip"]
    if args.no_preview:
        say("[3/5] Skipped the preview (--no-preview)")
    else:
        make_preview(clip)
    if args.models:
        setup_models(args.mediapipe_python)
    else:
        say("[4/5] Skipped the model environments (add --models to build them)")
    verify(clip)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
