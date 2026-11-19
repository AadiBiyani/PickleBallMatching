import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from .backend import RUNTIME, prepare_model
from .contracts import BoundingBox, InputError, Selection, TrackingConfig
from .tracking import preview_video, run_tracking
from .video import inspect_video


def main():
    parser = argparse.ArgumentParser(description="YOLO pose + ByteTrack selected-players prototype")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare-model", help="Download official weights separately from inference.")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("video", type=Path)
    preview = commands.add_parser("preview")
    run = commands.add_parser("run")
    for command in (preview, run):
        command.add_argument("video", type=Path)
        command.add_argument("--frame", type=int, default=0)
        command.add_argument("--device", choices=["cpu", "mps"], default="cpu")
        command.add_argument(
            "--output", type=Path, default=RUNTIME / "previews" if command is preview else RUNTIME / "runs"
        )
    run.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        action="append",
        required=True,
        metavar=("X1", "Y1", "X2", "Y2"),
        help="Repeat once per selected player.",
    )
    run.add_argument("--max-frames", type=int, default=300)
    run.add_argument("--ankle-confidence", type=float, default=0.5)
    serve = commands.add_parser("serve")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        if args.command == "prepare-model":
            result = prepare_model()
        elif args.command == "inspect":
            result = inspect_video(args.video).model_dump()
        elif args.command == "preview":
            result = preview_video(args.video, args.output, args.frame, TrackingConfig(device=args.device))
        elif args.command == "run":
            selections = [
                Selection(
                    frame_index=args.frame,
                    bbox=BoundingBox(**dict(zip(("x1", "y1", "x2", "y2"), box, strict=True))),
                )
                for box in args.bbox
            ]
            result = run_tracking(
                args.video,
                selections,
                TrackingConfig(
                    device=args.device, max_frames=args.max_frames, ankle_confidence=args.ankle_confidence
                ),
                args.output,
            )
        else:
            import uvicorn

            uvicorn.run("player_tracking.api:create_app", factory=True, host="127.0.0.1", port=args.port)
            return
        print(json.dumps(result, indent=2, allow_nan=False))
    except (InputError, ValidationError, OSError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
