"""Versioned drill definitions (FR-03).

These follow the candidate drills in the project proposal: predictable lateral
feeds, unpredictable lateral feeds, and forehand/backhand target returns. Feed
counts follow the proposal's pilot protocol (~20 valid feeds per drill) and the
recording cap follows the SDP benchmark (recordings up to 60 s).
"""

from .schemas import Drill, Region

MAX_RECORDING_S = 60
FEED_COUNT = 20

_LATERAL_REGIONS = [
    Region(id="left", label="Wide left"),
    Region(id="center", label="Center"),
    Region(id="right", label="Wide right"),
]

_EQUIPMENT = ["Paddle", "20 balls", "Feeder or ball machine", "Phone + tripod"]
_START = "Stand on the center mark, one step behind the baseline, facing the net."

DRILLS: list[Drill] = [
    Drill(
        id="lateral-prescribed",
        version="1.0",
        name="Lateral Coverage - Prescribed",
        summary=f"{FEED_COUNT} feeds · up to {MAX_RECORDING_S} s · Baseline",
        purpose="Measures how far and how fast you cover side-to-side feeds that arrive in a known order.",
        stage="prescribed",
        feed_count=FEED_COUNT,
        max_recording_s=MAX_RECORDING_S,
        equipment=_EQUIPMENT,
        starting_position=_START,
        steps=[
            "Feeds alternate wide left, center, wide right in a fixed order.",
            "Return each feed cross-court so its first bounce lands in the target area.",
            "Recover to the center mark after every feed.",
            f"Stay in camera view until all {FEED_COUNT} feeds are done.",
        ],
        target_area="Opponent's cross-court half, past the kitchen line",
        regions=_LATERAL_REGIONS,
    ),
    Drill(
        id="lateral-reactive",
        version="1.0",
        name="Lateral Coverage - Reactive",
        summary=f"{FEED_COUNT} feeds · up to {MAX_RECORDING_S} s · Baseline",
        purpose="Measures side-to-side coverage when you cannot predict where the next feed is going.",
        stage="reactive",
        feed_count=FEED_COUNT,
        max_recording_s=MAX_RECORDING_S,
        equipment=_EQUIPMENT,
        starting_position=_START,
        steps=[
            "Feeds go wide left, center, or wide right in an unpredictable order.",
            "Return each feed cross-court so its first bounce lands in the target area.",
            "Recover to the center mark after every feed.",
            f"Stay in camera view until all {FEED_COUNT} feeds are done.",
        ],
        target_area="Opponent's cross-court half, past the kitchen line",
        regions=_LATERAL_REGIONS,
    ),
    Drill(
        id="fh-bh-targets",
        version="1.0",
        name="Forehand / Backhand Target Returns",
        summary=f"{FEED_COUNT} feeds · up to {MAX_RECORDING_S} s · Baseline",
        purpose="Compares how reliably you return feeds to a target on your forehand and backhand sides.",
        stage="prescribed",
        feed_count=FEED_COUNT,
        max_recording_s=MAX_RECORDING_S,
        equipment=_EQUIPMENT,
        starting_position=_START,
        steps=[
            "Feeds alternate to your forehand and backhand sides.",
            "Return each feed so its first bounce lands in the marked target area.",
            "Recover to the center mark after every feed.",
            f"Stay in camera view until all {FEED_COUNT} feeds are done.",
        ],
        target_area="Marked deep target zone on the opponent's side",
        regions=[
            Region(id="forehand", label="Forehand side"),
            Region(id="backhand", label="Backhand side"),
        ],
    ),
]

_BY_ID = {d.id: d for d in DRILLS}


def get_drill(drill_id: str) -> Drill | None:
    return _BY_ID.get(drill_id)
