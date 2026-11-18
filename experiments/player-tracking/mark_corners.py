"""Click four court corners once and store them for the evaluation harness.

The click is on the first frame at the video's own resolution. Running again
for the same file name replaces that entry. The pose model is not involved.

    python mark_corners.py clip.mp4
    python mark_corners.py clip.mp4 --registry ../vlm-harness/data/corners.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import perspective as P

CORNER_ORDER = list(P.CORNER_LABELS)
DEFAULT_REGISTRY = (
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vlm-harness", "data", "corners.json"))
)
WIN = "corners"
C_CORNER = (0, 220, 255)
C_EDGE = (0, 180, 0)
C_TEXT = (255, 255, 255)


def empty_registry():
    return {"videos": {}}


def load_registry(path):
    if not os.path.exists(path):
        return empty_registry()
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("videos"), dict):
        raise ValueError(f"{path} is not a corner registry")
    return data


def clip_key(video_path):
    return os.path.basename(video_path)


def upsert_clip(registry, video_path, width, height, corners):
    """Return a new registry with this clip's corners replaced."""
    if len(corners) != 4:
        raise ValueError(f"expected 4 corners, got {len(corners)}")
    videos = dict(registry.get("videos", {}))
    videos[clip_key(video_path)] = {
        "width": int(width),
        "height": int(height),
        "corner_order": list(CORNER_ORDER),
        "corners_px": [[float(x), float(y)] for x, y in corners],
    }
    return {"videos": videos}


def save_registry(path, registry):
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(registry, handle, indent=2)
        handle.write("\n")


def click_corners(frame, max_display=(1280, 800)):
    """Click far-left, far-right, near-right, near-left, then press 3.

    Returns the four points in the frame's own pixels, or None if cancelled.
    """
    scaler = P.DisplayScaler(frame.shape, max_display[0], max_display[1])
    state = {"corners": [], "message": f"Click {CORNER_ORDER[0]}."}

    def consider():
        pts = state["corners"]
        if len(pts) < 4:
            nxt = CORNER_ORDER[len(pts)] if pts else CORNER_ORDER[0]
            state["message"] = f"Clicked {len(pts)}/4. Next: {nxt}."
            return
        problems = P.validate_corners(pts, frame.shape)
        if problems:
            print("Rejected corner selection:")
            for problem in problems:
                print(f"  - {problem}")
            state["message"] = "Invalid selection. Press u to undo or r to reset."
            return
        state["message"] = "Corners set. Press 3 to save."

    def on_mouse(event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN or len(state["corners"]) >= 4:
            return
        state["corners"].append(scaler.to_original(x, y))
        consider()

    def render():
        img = scaler.resize(frame)
        pts = [scaler.to_display_int(p) for p in state["corners"]]
        for i, p in enumerate(pts):
            cv2.circle(img, p, 6, C_CORNER, -1, cv2.LINE_AA)
            cv2.putText(img, f"{i + 1}.{CORNER_ORDER[i]}", (p[0] + 8, p[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_CORNER, 1, cv2.LINE_AA)
        for i in range(len(pts) - 1):
            cv2.line(img, pts[i], pts[i + 1], C_EDGE, 2, cv2.LINE_AA)
        if len(pts) == 4:
            cv2.line(img, pts[3], pts[0], C_EDGE, 2, cv2.LINE_AA)
        cv2.rectangle(img, (0, 0), (img.shape[1], 28), (0, 0, 0), -1)
        cv2.putText(img, state["message"][:120], (8, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, C_TEXT, 1, cv2.LINE_AA)
        return img

    print("Click far-left, far-right, near-right, near-left. u undo, r reset, 3 save, q quit.")
    cv2.namedWindow(WIN, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WIN, on_mouse)
    while True:
        cv2.imshow(WIN, render())
        key = cv2.waitKey(20) & 0xFF
        if key in (ord("q"), 27):
            cv2.destroyWindow(WIN)
            return None
        if key == ord("u") and state["corners"]:
            state["corners"].pop()
            consider()
        elif key == ord("r"):
            state["corners"].clear()
            consider()
        elif key == ord("3"):
            if len(state["corners"]) != 4 or P.validate_corners(state["corners"], frame.shape):
                state["message"] = "Click 4 valid corners, then press 3."
                continue
            cv2.destroyWindow(WIN)
            return list(state["corners"])
        try:
            if cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
                return None
        except cv2.error:
            return None


def first_frame(video_path):
    cap = cv2.VideoCapture(video_path)
    try:
        ok, frame = cap.read()
    finally:
        cap.release()
    if not ok or frame is None:
        raise SystemExit(f"ERROR: could not read a frame from {video_path}")
    return frame


def main(argv=None):
    parser = argparse.ArgumentParser(description="Save four court corners for one video.")
    parser.add_argument("video", help="path to the test video")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY, help="corner registry JSON")
    args = parser.parse_args(argv)
    if not os.path.isfile(args.video):
        raise SystemExit(f"ERROR: video not found: {args.video}")
    frame = first_frame(args.video)
    height, width = frame.shape[:2]
    corners = click_corners(frame)
    if corners is None:
        raise SystemExit("cancelled")
    registry = upsert_clip(load_registry(args.registry), args.video, width, height, corners)
    save_registry(args.registry, registry)
    print(f"saved {clip_key(args.video)} ({width}x{height}) to {args.registry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
