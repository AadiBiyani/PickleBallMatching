"""Headless checks for the video diagram writer.

These do not open a window and do not load the pose model.  A stand-in supplies
the foot pixel, and the test checks that the existing homography places it.
"""

import csv
import os
import sys
import tempfile
import unittest

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contact  # noqa: E402
import perspective as P  # noqa: E402
import track_video  # noqa: E402

ANGLED_CORNERS = np.array([[472.0, 232.0],
                           [846.0, 226.0],
                           [1128.0, 706.0],
                           [214.0, 724.0]], dtype=np.float64)
IMAGE_SHAPE = (800, 1280, 3)


class TestRenderTrack(unittest.TestCase):
    def test_red_dot_lands_on_the_court_coordinate(self):
        base, ppf, margin = P.draw_court_diagram(ppf=20)
        img = track_video.render_track(base, [None, (10.0, 22.0)], ppf, margin)
        px = P.feet_to_output_px([[10.0, 22.0]], ppf, margin)[0]
        x, y = int(round(px[0])), int(round(px[1]))
        b, g, r = (int(v) for v in img[y, x])
        self.assertGreater(r, 200)
        self.assertLess(b, 40)
        self.assertLess(g, 40)

    def test_a_gap_does_not_draw_a_dot(self):
        base, ppf, margin = P.draw_court_diagram(ppf=20)
        blank = track_video.render_track(base, [None], ppf, margin)
        drawn = track_video.render_track(base, [(10.0, 22.0)], ppf, margin)

        def red_pixels(img):
            return int(np.count_nonzero(
                (img[:, :, 2] > 200) & (img[:, :, 1] < 40) & (img[:, :, 0] < 40)
            ))

        self.assertEqual(red_pixels(blank), 0)
        self.assertGreater(red_pixels(drawn), 0)


class TestProcessVideo(unittest.TestCase):
    def _run(self, samples):
        calib = P.Calibration.from_corners(ANGLED_CORNERS, IMAGE_SHAPE, "clip.mp4")

        def contact_at(frame, index, fps):
            return samples[index]

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        video_path = os.path.join(tmp.name, "clip.mp4")
        writer = cv2.VideoWriter(
            video_path, cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (IMAGE_SHAPE[1], IMAGE_SHAPE[0])
        )
        self.assertTrue(writer.isOpened())
        frame = np.zeros(IMAGE_SHAPE, dtype=np.uint8)
        for _ in samples:
            writer.write(frame)
        writer.release()

        summary = track_video.process_video(
            video_path, calib, contact_at, tmp.name, preview=False
        )
        with open(summary["csv"], encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        return summary, rows, calib

    def test_known_pixel_is_written_as_court_feet(self):
        calib = P.Calibration.from_corners(ANGLED_CORNERS, IMAGE_SHAPE, "clip.mp4")
        pixel = tuple(float(v) for v in calib.court_to_image([[10.0, 22.0]])[0])
        samples = [
            contact.ContactSample(pixel, contact.BOTH_HEELS),
            contact.ContactSample(None, contact.NO_CONTACT),
            contact.ContactSample(pixel, contact.BOTH_HEELS),
        ]
        summary, rows, _ = self._run(samples)
        self.assertEqual(summary["frames"], 3)
        self.assertEqual(summary["with_feet"], 2)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["contact"], contact.BOTH_HEELS)
        self.assertEqual(rows[1]["contact"], contact.NO_CONTACT)
        self.assertEqual(rows[1]["x_ft"], "")
        self.assertAlmostEqual(float(rows[0]["x_ft"]), 10.0, places=2)
        self.assertAlmostEqual(float(rows[0]["y_ft"]), 22.0, places=2)
        self.assertAlmostEqual(float(rows[2]["x_ft"]), 10.0, places=2)

        cap = cv2.VideoCapture(summary["video"])
        self.assertTrue(cap.isOpened())
        read = 0
        while True:
            ok, _ = cap.read()
            if not ok:
                break
            read += 1
        cap.release()
        self.assertEqual(read, 3)

    def test_single_heel_keeps_court_feet_and_labels_the_row(self):
        calib = P.Calibration.from_corners(ANGLED_CORNERS, IMAGE_SHAPE, "clip.mp4")
        pixel = tuple(float(v) for v in calib.court_to_image([[10.0, 22.0]])[0])
        summary, rows, _ = self._run([
            contact.ContactSample(pixel, contact.SINGLE_HEEL),
        ])
        self.assertEqual(summary["frames"], 1)
        self.assertEqual(summary["with_feet"], 1)
        self.assertEqual(rows[0]["contact"], contact.SINGLE_HEEL)
        self.assertAlmostEqual(float(rows[0]["x_ft"]), 10.0, places=2)
        self.assertAlmostEqual(float(rows[0]["y_ft"]), 22.0, places=2)

    def test_both_heels_out_of_frame_blank_the_row_and_continue(self):
        calib = P.Calibration.from_corners(ANGLED_CORNERS, IMAGE_SHAPE, "clip.mp4")
        pixel = tuple(float(v) for v in calib.court_to_image([[10.0, 22.0]])[0])
        summary, rows, _ = self._run([
            contact.ContactSample(None, contact.OUT_OF_FRAME),
            contact.ContactSample(pixel, contact.BOTH_HEELS),
        ])
        self.assertEqual(summary["frames"], 2)
        self.assertEqual(summary["with_feet"], 1)
        self.assertEqual(rows[0]["contact"], contact.OUT_OF_FRAME)
        self.assertEqual(rows[0]["x_ft"], "")
        self.assertEqual(rows[0]["y_ft"], "")
        self.assertEqual(rows[1]["contact"], contact.BOTH_HEELS)
        self.assertAlmostEqual(float(rows[1]["x_ft"]), 10.0, places=2)
        self.assertAlmostEqual(float(rows[1]["y_ft"]), 22.0, places=2)
