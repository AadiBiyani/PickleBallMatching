"""Point results and the court zones derived from them.

A model reports an image point, or no point. The zone is decided here from
court feet, after the harness has applied the homography.
"""

from __future__ import annotations

from dataclasses import dataclass

COURT_WIDTH_FT = 20.0
COURT_LENGTH_FT = 44.0
NET_Y_FT = 22.0
KITCHEN_NEAR_Y_FT = 29.0
TRANSITION_Y_FT = 36.5
CENTER_X_FT = 10.0

KITCHEN_LEFT = "kitchen_left"
KITCHEN_RIGHT = "kitchen_right"
TRANSITION_LEFT = "transition_left"
TRANSITION_RIGHT = "transition_right"
BACKCOURT_LEFT = "backcourt_left"
BACKCOURT_RIGHT = "backcourt_right"
OUT_OF_COURT = "out_of_court"
NOT_VISIBLE = "not_visible"

ZONE_VALUES = (
    KITCHEN_LEFT,
    KITCHEN_RIGHT,
    TRANSITION_LEFT,
    TRANSITION_RIGHT,
    BACKCOURT_LEFT,
    BACKCOURT_RIGHT,
    OUT_OF_COURT,
    NOT_VISIBLE,
)


@dataclass(frozen=True)
class LocatedPoint:
    """One model's player point in the frame it was shown.

    x_px and y_px are both None when the player is not visible. The origin is
    the top-left of that frame.
    """

    frame_index: int
    x_px: float | None
    y_px: float | None

    @property
    def visible(self) -> bool:
        return self.x_px is not None and self.y_px is not None


def zone_from_feet(x_ft: float, y_ft: float) -> str:
    """Zone on the near half. Left and right are as seen in the image.

    The near half runs from the net (y = 22) to the near baseline (y = 44).
    Kitchen is [22, 29), transition is [29, 36.5), backcourt is [36.5, 44].
    Left is [0, 10) and right is [10, 20]. Anything else is out of court,
    including the far half.
    """
    if x_ft < 0.0 or x_ft > COURT_WIDTH_FT or y_ft < NET_Y_FT or y_ft > COURT_LENGTH_FT:
        return OUT_OF_COURT
    side = "left" if x_ft < CENTER_X_FT else "right"
    if y_ft < KITCHEN_NEAR_Y_FT:
        band = "kitchen"
    elif y_ft < TRANSITION_Y_FT:
        band = "transition"
    else:
        band = "backcourt"
    return f"{band}_{side}"
