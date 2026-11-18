"""Corner registry lookup."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "player-tracking"))

import mark_corners

from harness.corners import CORNER_ORDER, entry_for, load_registry, scale_corners


def _registry(width, height, corners):
    return {
        "videos": {
            "clip.mp4": {
                "width": width,
                "height": height,
                "corner_order": list(CORNER_ORDER),
                "corners_px": corners,
            }
        }
    }


def test_registry_rejects_a_different_video_size(tmp_path):
    path = tmp_path / "corners.json"
    path.write_text(json.dumps(_registry(200, 100, [[0, 0], [10, 0], [10, 10], [0, 10]])))
    registry = load_registry(path)
    with pytest.raises(ValueError, match="registry has 200x100"):
        entry_for(registry, "clip.mp4", 200, 80)


def test_scale_corners_follows_the_frame_size():
    registry = _registry(200, 100, [[10, 20], [30, 20], [30, 80], [10, 80]])
    entry = entry_for(registry, "clip.mp4", 200, 100)
    assert scale_corners(entry, 100, 50)[0] == [5.0, 10.0]


def test_mark_corners_replaces_the_same_clip(tmp_path):
    path = tmp_path / "corners.json"
    first = mark_corners.upsert_clip(
        mark_corners.empty_registry(), "clip.mp4", 200, 100,
        [(0, 0), (20, 0), (20, 40), (0, 40)],
    )
    mark_corners.save_registry(path, first)
    second = mark_corners.upsert_clip(
        load_registry(path), "clip.mp4", 200, 100,
        [(1, 2), (3, 2), (3, 4), (1, 4)],
    )
    assert len(second["videos"]) == 1
    assert second["videos"]["clip.mp4"]["corners_px"][0] == [1.0, 2.0]
    entry = entry_for(second, "clip.mp4", 200, 100)
    assert entry.corners_px[3] == (1.0, 4.0)
