from app import scoring
from app.schemas import Attempt, Region


def _a(n: int, outcome: str, region: str = "left", **kw) -> Attempt:
    return Attempt(number=n, region_id=region, outcome=outcome, t_start_ms=0, t_end_ms=1, **kw)


def test_fr10_fixture_excludes_invalid_and_uncertain():
    # SDP FR-10 test method: 6 successes, 2 failures, 1 invalid feed, 1 uncertain.
    attempts = (
        [_a(i, "success") for i in range(6)]
        + [_a(6, "failure"), _a(7, "failure")]
        + [_a(8, "invalid_feed", reason="out"), _a(9, "uncertain", reason="hidden")]
    )
    totals = scoring.overall(attempts)
    assert totals["scored"] == 8
    assert totals["success_rate"] == 0.75
    ex = scoring.exclusions(attempts)
    assert (ex.invalid_feed, ex.uncertain, ex.flagged) == (1, 1, 0)


def test_region_below_minimum_is_insufficient_not_low():
    regions = [Region(id="left", label="L"), Region(id="right", label="R")]
    attempts = [_a(i, "success", "left") for i in range(5)] + [_a(9, "failure", "right")]
    left, right = scoring.region_results(attempts, regions)
    assert left.sufficient and left.success_rate == 1.0
    assert not right.sufficient and right.success_rate is None and right.scored == 1


def test_flagged_attempt_leaves_scored_counts_but_keeps_prediction():
    attempts = [_a(1, "success", flagged=True), _a(2, "failure")]
    totals = scoring.overall(attempts)
    assert totals["scored"] == 1 and totals["successes"] == 0
    assert scoring.exclusions(attempts).flagged == 1
    assert attempts[0].outcome == "success"


def test_wilson_interval_known_value():
    low, high = scoring.wilson_interval(6, 8)
    assert round(low, 3) == 0.409 and round(high, 3) == 0.929
