"""Zone boundaries and one known homography."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "player-tracking"))

import perspective as court

from harness.contract import zone_from_feet


RECTANGLE = [[0.0, 0.0], [200.0, 0.0], [200.0, 440.0], [0.0, 440.0]]


def test_rectangle_point_lands_in_kitchen_left():
    homography = court.compute_homography(RECTANGLE)
    x_ft, y_ft = court.apply_homography(homography, [[50.0, 250.0]])[0]
    assert abs(x_ft - 5.0) < 1e-3
    assert abs(y_ft - 25.0) < 1e-3
    assert zone_from_feet(float(x_ft), float(y_ft)) == "kitchen_left"


def test_zone_edges():
    assert zone_from_feet(0.0, 22.0) == "kitchen_left"
    assert zone_from_feet(9.9, 28.9) == "kitchen_left"
    assert zone_from_feet(10.0, 25.0) == "kitchen_right"
    assert zone_from_feet(5.0, 29.0) == "transition_left"
    assert zone_from_feet(5.0, 36.5) == "backcourt_left"
    assert zone_from_feet(20.0, 44.0) == "backcourt_right"
    assert zone_from_feet(5.0, 21.9) == "out_of_court"
    assert zone_from_feet(-0.1, 30.0) == "out_of_court"
    assert zone_from_feet(5.0, 44.1) == "out_of_court"
