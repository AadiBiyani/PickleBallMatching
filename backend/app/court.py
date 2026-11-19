"""Court geometry shared with the team's court evaluation harness.

Mirrors `experiments/vlm-harness/harness/contract.py` and
`experiments/player-tracking/perspective.py` on the
`nishaant/experiment/no-issue-court-eval-harness` branch, so backend output is
directly comparable to harness output:

- Models report an IMAGE point per frame (or none). They never see the corners.
- The four court corners are clicked in the order far-left, far-right,
  near-right, near-left (as the court appears in the image).
- A homography maps image pixels to COURT FEET: origin at the far-left outside
  corner, x toward the right sideline (0-20 ft), y toward the near baseline
  (0-44 ft). The net is at y = 22.
- The zone is derived here from feet, never chosen by a model.

The homography is solved in pure Python (no OpenCV/NumPy) so the API keeps its
small dependency set. tests/test_court.py checks it against the harness's cases.
When the harness graduates to `models/`, import from there instead of keeping
this copy.
"""

from __future__ import annotations

import math

COURT_WIDTH_FT = 20.0
COURT_LENGTH_FT = 44.0
NET_Y_FT = 22.0
KITCHEN_NEAR_Y_FT = 29.0
TRANSITION_Y_FT = 36.5
CENTER_X_FT = 10.0

CORNER_ORDER = ("far-left", "far-right", "near-right", "near-left")
COURT_CORNERS_FT = ((0.0, 0.0), (COURT_WIDTH_FT, 0.0), (COURT_WIDTH_FT, COURT_LENGTH_FT), (0.0, COURT_LENGTH_FT))

MIN_CORNER_SEPARATION_PX = 10.0
MIN_QUAD_AREA_FRACTION = 0.005

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

Point = tuple[float, float]
Homography = tuple[tuple[float, float, float], ...]


class CalibrationError(ValueError):
    """Unusable court corners or homography."""


def zone_from_feet(x_ft: float, y_ft: float) -> str:
    """Zone on the near half; left/right as seen in the image (harness rules).

    Kitchen is [22, 29), transition [29, 36.5), backcourt [36.5, 44].
    Left is [0, 10), right [10, 20]. Anything else, including the far half,
    is out of court.
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


def _signed_area(p: list[Point]) -> float:
    return 0.5 * sum(p[i][0] * p[(i + 1) % 4][1] - p[(i + 1) % 4][0] * p[i][1] for i in range(4))


def validate_corners(corners: list[Point], width: int | None = None, height: int | None = None) -> list[str]:
    """Human-readable problems with a 4-corner selection (same checks as perspective.py)."""
    if len(corners) != 4 or any(len(c) != 2 for c in corners):
        return ["need exactly 4 corners of (x, y)"]
    p = [(float(x), float(y)) for x, y in corners]
    if not all(math.isfinite(v) for pt in p for v in pt):
        return ["corners contain non-finite values"]
    problems = []
    for i in range(4):
        for j in range(i + 1, 4):
            if math.dist(p[i], p[j]) < MIN_CORNER_SEPARATION_PX:
                problems.append(f"corners {CORNER_ORDER[i]} and {CORNER_ORDER[j]} are nearly identical")
    area = _signed_area(p)
    min_area = 1000.0
    if width and height:
        min_area = max(min_area, MIN_QUAD_AREA_FRACTION * width * height)
    if abs(area) < min_area:
        problems.append("the corners are nearly collinear or too close together")
    crosses = []
    for i in range(4):
        a, b, c = p[i], p[(i + 1) % 4], p[(i + 2) % 4]
        crosses.append((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]))
    if any(abs(c) < 1e-9 for c in crosses):
        problems.append("three corners are collinear")
    elif not (all(c > 0 for c in crosses) or all(c < 0 for c in crosses)):
        problems.append("the corners form a non-convex or self-intersecting shape")
    elif area < 0:
        problems.append("the corners are in reverse order; use far-left, far-right, near-right, near-left")
    return problems


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting for the 8x8 homography system."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            raise CalibrationError("the four corners produced a singular homography")
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            for c in range(col, n + 1):
                m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][c] * x[c] for c in range(r + 1, n))) / m[r][r]
    return x


def compute_homography(src: list[Point], dst: list[Point] | None = None) -> Homography:
    """3x3 matrix mapping src[i] -> dst[i] (H[2][2] = 1), as cv2.getPerspectiveTransform does.

    The default dst maps image corners (CORNER_ORDER) to court feet.
    """
    if dst is None:
        dst = list(COURT_CORNERS_FT)
    a: list[list[float]] = []
    b: list[float] = []
    for (x, y), (u, v) in zip(src, dst):
        a.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y])
        b.append(u)
        a.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y])
        b.append(v)
    h = _solve(a, b)
    return ((h[0], h[1], h[2]), (h[3], h[4], h[5]), (h[6], h[7], 1.0))


def apply_homography(h: Homography, point: Point) -> Point:
    x, y = point
    w = h[2][0] * x + h[2][1] * y + h[2][2]
    if abs(w) < 1e-12:
        raise CalibrationError("point maps to infinity under this homography")
    return ((h[0][0] * x + h[0][1] * y + h[0][2]) / w, (h[1][0] * x + h[1][1] * y + h[1][2]) / w)


def scale_corners(corners: list[Point], from_size: tuple[int, int], to_size: tuple[int, int]) -> list[Point]:
    """Map corners saved at the video's native size into a resized frame."""
    sx = to_size[0] / from_size[0]
    sy = to_size[1] / from_size[1]
    return [(x * sx, y * sy) for x, y in corners]
