"""Contract tests with fabricated observations, never model-accuracy evidence."""

import copy
import csv
import hashlib
import json

import cv2
import numpy as np
import pytest

pytest.importorskip(
    "player_tracking",
    reason="YOLO adapter tests use the player-tracking-yolo environment",
)

from harness.analyzers.base import create_analyzer
from harness.analyzers.yolo import YoloAnalyzer
from harness.frames import Frame, extract_frames
from harness.run import main, run_harness


@pytest.fixture
def exported(tmp_path):
    video = tmp_path / "synthetic.avi"
    writer = cv2.VideoWriter(
        str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (200, 440)
    )
    assert writer.isOpened()
    for _ in range(6):
        writer.write(np.zeros((440, 200, 3), dtype=np.uint8))
    writer.release()
    rows = []
    for index in range(2, 6):
        for player, track, x, y in [
            ("player_1", 7, 50, 250),
            ("player_2", 9, 150, 400),
        ]:
            missing = player == "player_1" and index in (3, 4)
            rows.append(
                {
                    "player_id": player,
                    "frame_index": index,
                    "timestamp_s": index / 10,
                    "selected_track_id": track,
                    "status": (
                        "target_not_detected" if index == 3 else "keypoints_unreliable"
                    )
                    if missing
                    else "ok",
                    "reason": "Synthetic missing observation" if missing else None,
                    "image_x_px": None if missing else float(x),
                    "image_y_px": None if missing else float(y),
                    "point_source": "ankle_midpoint",
                }
            )
    data = {
        "schema_version": "1.1",
        "metadata": {
            "complete": True,
            "model_name": "yolo26n-pose.pt",
            "source": {
                "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                "width": 200,
                "height": 440,
                "frame_count": 6,
            },
            "processing_stride": 1,
            "coordinate_system": "original_image_pixels",
            "point_source": "ankle_midpoint",
            "selected_track_ids": {"player_1": 7, "player_2": 9},
            "start_frame": 2,
            "processed_frame_count": 4,
            "requested_frame_count": 4,
            "fixture": "Fabricated test observations, no YOLO inference",
        },
        "frames": rows,
    }
    positions = tmp_path / "positions.json"
    positions.write_text(json.dumps(data))
    corners = tmp_path / "corners.json"
    corners.write_text(
        json.dumps(
            {
                "videos": {
                    video.name: {
                        "width": 200,
                        "height": 440,
                        "corner_order": [
                            "far-left",
                            "far-right",
                            "near-right",
                            "near-left",
                        ],
                        "corners_px": [[0, 0], [200, 0], [200, 440], [0, 440]],
                    }
                }
            }
        )
    )
    return video, positions, corners, data


def analyzer_for(exported, player="player_1"):
    return create_analyzer(
        "yolo:yolo26n-pose", positions_path=exported[1], player_id=player
    )


def test_registration_requires_explicit_export_and_player(exported):
    with pytest.raises(ValueError, match="explicit --player-id"):
        create_analyzer("yolo", positions_path=exported[1])
    with pytest.raises(ValueError, match="Unknown YOLO player_id"):
        analyzer_for(exported, "spectator")
    with pytest.raises(ValueError, match="model must match"):
        create_analyzer(
            "yolo:yolo11n-pose", positions_path=exported[1], player_id="player_1"
        )
    assert analyzer_for(exported).model_id == "yolo26n-pose.pt"
    with pytest.raises(ValueError, match="only to the yolo"):
        create_analyzer("fake", positions_path=exported[1])


def test_exact_source_index_and_explicit_player_take_priority_over_timestamps(exported):
    image = np.zeros((220, 100, 3), dtype=np.uint8)
    frame = Frame(37, 999.0, 100, 220, image, source_frame_index=2)
    first = analyzer_for(exported).locate([frame])[0]
    second = analyzer_for(exported, "player_2").locate([frame])[0]
    assert (first.frame_index, first.x_px, first.y_px) == (37, 25, 125)
    assert (second.x_px, second.y_px) == (75, 200)
    with pytest.raises(ValueError, match="source_frame_index"):
        analyzer_for(exported).locate([Frame(0, 0.2, 100, 220, image)])
    with pytest.raises(ValueError, match="was not tracked"):
        analyzer_for(exported).locate([Frame(0, 0, 100, 220, image, 0)])


@pytest.mark.parametrize("long_side", [None, 220])
def test_shared_projection_missing_rows_labels_and_audit(exported, tmp_path, long_side):
    video, _, corners, _ = exported
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "time_s,zone,x_ft,y_ft\n"
        + "".join(f"{index / 10},kitchen_left,5,25\n" for index in range(2, 6))
    )
    analyzer = analyzer_for(exported)
    outcome = run_harness(
        video,
        analyzer,
        corners,
        labels_path=labels,
        fps=10,
        long_side_px=long_side,
        output_root=tmp_path / "results",
        start_frame=2,
        stop_frame=6,
    )
    assert [row["source_frame_index"] for row in outcome.rows] == [2, 3, 4, 5]
    assert [row["frame_index"] for row in outcome.rows] == [0, 1, 2, 3]
    assert [row["time_s"] for row in outcome.rows] == [0.2, 0.3, 0.4, 0.5]
    assert [row["zone"] for row in outcome.rows] == [
        "kitchen_left",
        "not_visible",
        "not_visible",
        "kitchen_left",
    ]
    assert outcome.rows[0]["x_ft"] == pytest.approx(5)
    assert outcome.rows[0]["y_ft"] == pytest.approx(25)
    assert outcome.score.zone_accuracy == 0.5
    assert outcome.score.n_position_missing == 2
    assert outcome.score.n_position_scored == 2
    assert outcome.score.position_error_mean_ft == pytest.approx(0)
    with (outcome.run_dir / "results.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert rows[1]["x_px"] == rows[1]["x_ft"] == ""
    audit = json.loads((outcome.run_dir / "analyzer.json").read_text())
    assert audit["player_id"] == "player_1"
    assert audit["tracking_metadata"]["point_source"] == "ankle_midpoint"
    assert audit["samples"][1]["observation"]["status"] == "target_not_detected"
    assert audit["samples"][2]["observation"]["status"] == "keypoints_unreliable"
    assert (
        audit["samples"][1]["observation"]["reason"] == "Synthetic missing observation"
    )
    assert (
        "ultralytics" not in __import__("sys").modules
    )  # reading exports does not load a model


def test_source_identity_dimensions_and_window_are_checked(exported, tmp_path):
    video, _, corners, _ = exported
    analyzer = analyzer_for(exported)
    with pytest.raises(ValueError, match="not fully tracked"):
        run_harness(video, analyzer, corners, output_root=tmp_path)
    wrong_video = tmp_path / "other.avi"
    wrong_video.write_bytes(b"different bytes")
    with pytest.raises(ValueError, match="SHA-256"):
        analyzer.validate_video(wrong_video, 200, 440, 2, 6)
    with pytest.raises(ValueError, match="dimensions"):
        analyzer.validate_video(video, 201, 440, 2, 6)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda d: d.update(schema_version="1.0"), "schema_version"),
        (lambda d: d["metadata"].update(complete=False), "complete"),
        (lambda d: d["metadata"].update(processing_stride=30), "continuous"),
        (
            lambda d: d["metadata"].update(coordinate_system="normalized"),
            "original_image_pixels",
        ),
        (lambda d: d["metadata"].update(point_source="heel"), "ankle_midpoint"),
        (lambda d: d["metadata"]["source"].update(width="200"), "width"),
        (lambda d: d["metadata"].update(requested_frame_count=5), "counts differ"),
        (lambda d: d["frames"].append(copy.deepcopy(d["frames"][0])), "Duplicate"),
        (lambda d: d["frames"].pop(0), "one observation"),
        (lambda d: d["frames"][0].update(selected_track_id=9), "track ID"),
        (lambda d: d["frames"][0].update(image_x_px=None), "both coordinates"),
        (lambda d: d["frames"][0].update(image_x_px=200.0), "outside"),
        (lambda d: d["frames"][2].update(image_x_px=10.0), "two null"),
        (lambda d: d["frames"][0].update(image_x_px=float("nan")), "finite"),
        (lambda d: d["frames"][0].update(status="invented"), "Input should be"),
    ],
)
def test_bad_exports_fail_explicitly(exported, mutation, message):
    _, positions, _, data = exported
    mutation(data)
    positions.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=message):
        YoloAnalyzer(positions_path=positions, player_id="player_1")


def test_sampler_tracks_original_indices_at_lower_rate(exported):
    clip = extract_frames(exported[0], fps=5, start_frame=2, stop_frame=6)
    assert [(f.index, f.source_frame_index, f.time_s) for f in clip.frames] == [
        (0, 2, 0.2),
        (1, 4, 0.4),
    ]


@pytest.mark.parametrize(
    "options",
    [
        {"start_frame": -1},
        {"start_frame": 3, "stop_frame": 3},
        {"fps": float("nan")},
        {"fps": float("inf")},
    ],
)
def test_bad_sampling_options_are_rejected(exported, options):
    with pytest.raises(ValueError):
        extract_frames(exported[0], **options)


def test_cli_and_repeated_runs_preserve_outputs(exported, tmp_path, capsys):
    video, positions, corners, _ = exported
    options = [
        str(video),
        "--analyzer",
        "yolo",
        "--positions",
        str(positions),
        "--player-id",
        "player_2",
        "--corners",
        str(corners),
        "--start-frame",
        "2",
        "--stop-frame",
        "6",
        "--fps",
        "10",
        "--output",
        str(tmp_path / "results"),
    ]
    assert main(options) == 0
    assert main(options) == 0
    assert "zone accuracy n/a" in capsys.readouterr().out
    outputs = list((tmp_path / "results/runs").glob("*/results.csv"))
    assert len(outputs) == 2
    with outputs[0].open() as stream:
        rows = list(csv.DictReader(stream))
    assert all(row["zone"] == "backcourt_right" for row in rows)
    assert main(options + ["--player-id", "absent"]) == 2
    assert "Unknown YOLO player_id" in capsys.readouterr().err
