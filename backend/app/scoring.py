"""Coverage-profile calculations (FR-10, FR-11).

Rules from the SDP / proposal:
- invalid feeds and uncertain attempts are excluded from scored counts, with reasons kept;
- confidently observed failures stay in the denominator;
- flagged attempts keep their original prediction but are excluded until re-recorded (SR-9);
- regions with fewer than MIN_SCORED_PER_REGION scored attempts are "insufficient", not low;
- return proportions report a 95% Wilson interval.
"""

import math
from statistics import mean

from .schemas import Attempt, Exclusions, Region, RegionResult

MIN_SCORED_PER_REGION = 5
Z_95 = 1.959964


def wilson_interval(successes: int, n: int, z: float = Z_95) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def is_scored(a: Attempt) -> bool:
    return a.outcome in ("success", "failure") and not a.flagged


def exclusions(attempts: list[Attempt]) -> Exclusions:
    return Exclusions(
        invalid_feed=sum(a.outcome == "invalid_feed" for a in attempts),
        uncertain=sum(a.outcome == "uncertain" for a in attempts),
        flagged=sum(a.flagged and a.outcome in ("success", "failure") for a in attempts),
    )


def region_results(
    attempts: list[Attempt], regions: list[Region], min_scored: int = MIN_SCORED_PER_REGION
) -> list[RegionResult]:
    out = []
    for r in regions:
        scored = [a for a in attempts if a.region_id == r.id and is_scored(a)]
        n = len(scored)
        k = sum(a.outcome == "success" for a in scored)
        sufficient = n >= min_scored
        ci = wilson_interval(k, n) if sufficient else None
        travel = [a.travel_time_s for a in scored if a.travel_time_s is not None]
        out.append(
            RegionResult(
                region_id=r.id,
                label=r.label,
                scored=n,
                successes=k,
                success_rate=(k / n) if sufficient else None,
                ci_low=ci[0] if ci else None,
                ci_high=ci[1] if ci else None,
                avg_travel_time_s=round(mean(travel), 2) if travel and sufficient else None,
                sufficient=sufficient,
            )
        )
    return out


def overall(attempts: list[Attempt]) -> dict:
    scored = [a for a in attempts if is_scored(a)]
    n = len(scored)
    k = sum(a.outcome == "success" for a in scored)
    ci = wilson_interval(k, n)
    resp = [a.response_time_s for a in scored if a.response_time_s is not None]
    return {
        "scored": n,
        "successes": k,
        "success_rate": (k / n) if n else None,
        "ci_low": ci[0] if ci else None,
        "ci_high": ci[1] if ci else None,
        "avg_response_time_s": round(mean(resp), 2) if resp else None,
    }
