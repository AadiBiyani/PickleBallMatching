import math

from .contracts import BoundingBox, Detection, FrameRecord, InputError, TrackingConfig


def intersection_over_union(a: BoundingBox, b: BoundingBox) -> float:
    intersection = max(0, min(a.x2, b.x2) - max(a.x1, b.x1)) * max(0, min(a.y2, b.y2) - max(a.y1, b.y1))
    union = (a.x2 - a.x1) * (a.y2 - a.y1) + (b.x2 - b.x1) * (b.y2 - b.y1) - intersection
    return intersection / union


def select_track(box: BoundingBox, detections: list[Detection], config: TrackingConfig) -> int:
    ranked = sorted(
        (
            (intersection_over_union(box, item.bbox), item.track_id)
            for item in detections
            if item.track_id is not None
        ),
        reverse=True,
    )
    if not ranked or ranked[0][0] < config.selection_iou:
        raise InputError(
            "No tracked person overlaps the selected box enough. Select a clear detected player."
        )
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] <= config.ambiguity_margin:
        raise InputError(
            "Selection overlaps multiple tracked people ambiguously. Choose a clearer preview frame."
        )
    return ranked[0][1]


def position_record(
    frame_index: int, track_id: int, detections: list[Detection], width: int, height: int, threshold: float
) -> FrameRecord:
    matches = [item for item in detections if item.track_id == track_id]
    base = {"frame_index": frame_index, "timestamp_s": 0, "selected_track_id": track_id}
    if not matches:
        return FrameRecord(**base, status="target_not_detected", reason="Selected track ID is not detected.")
    if len(matches) != 1:
        raise RuntimeError("Tracker returned duplicate IDs in one frame.")
    item = matches[0]
    confidence = {}
    reasons = []
    for name, ankle in (("left", item.left_ankle), ("right", item.right_ankle)):
        if ankle is None:
            reasons.append(f"{name} ankle missing")
            continue
        x, y, score = ankle
        if math.isfinite(score):
            confidence[f"{name}_ankle_confidence"] = score
        if not all(math.isfinite(value) for value in ankle):
            reasons.append(f"{name} ankle has nonfinite values")
        elif not 0 <= score <= 1 or score < threshold:
            reasons.append(f"{name} ankle below confidence threshold")
        elif not (0 <= x < width and 0 <= y < height):
            reasons.append(f"{name} ankle outside original image")
    if reasons:
        return FrameRecord(
            **base, bbox=item.bbox, status="keypoints_unreliable", reason="; ".join(reasons), **confidence
        )
    return FrameRecord(
        **base,
        bbox=item.bbox,
        status="ok",
        image_x_px=(item.left_ankle[0] + item.right_ankle[0]) / 2,
        image_y_px=(item.left_ankle[1] + item.right_ankle[1]) / 2,
        **confidence,
    )
