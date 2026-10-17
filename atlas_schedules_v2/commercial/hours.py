"""Hours of operation: inferred from occupancy, and built from sampled values.

Ports openstudio-standards 0.8.6:
- `space.rb` `spaces_get_occupancy_schedule`: People-weighted occupancy;
- `schedules/parametric.rb` `model_infer_hours_of_operation_building`:
  daily on/off profile from a 25 % threshold, keeping only the largest gap.
"""
from dataclasses import dataclass
import math

import numpy as np

from .profiles import points_from_hourly, round_half_up

THRESHOLD_FRACTION = 0.25


@dataclass(frozen=True)
class Hours:
    start: float
    end: float
    hours: float


def occupancy_fraction(groups: list[tuple[np.ndarray, float]]) -> np.ndarray:
    """People-weighted occupancy fraction from one (hourly schedule, people) pair per Ruleset.

    Callers merge spaces that share a People Ruleset first (space.rb sums their
    people per Ruleset). Each Ruleset's hourly value times its people is
    rounded to 6 places, summed over Rulesets, then divided by the total people.
    """
    total = sum(weight for _, weight in groups)
    weighted = [[round_half_up(v * weight, 6) for v in values] for values, weight in groups]
    return np.asarray([sum(hour) for hour in zip(*weighted)]) / total


def hours_from_points(points) -> Hours:
    """Start is the first time the on/off profile is 0, end the first time it is 1."""
    start = next((t for t, v in points if v == 0), None)
    end = next((t for t, v in points if v == 1), None)
    if start is None:
        start = end
    if end is None:
        end = start
    if start == end:
        always_on = all(v == 1 for _, v in points)
        return Hours(start, end, 24.0 if always_on else 0.0)
    return Hours(start, end, (end - start) % 24)


def _close_gaps(points):
    """Keep only the largest unoccupied gap (including the one wrapping midnight)."""
    if len(points) <= 3:
        return points
    latest_on = next((t for t, v in reversed(points) if v > 0), None)
    if latest_on is None:
        return points
    wrap = 24 - latest_on if points[0][1] == 0 and points[-1][1] == 0 else 0
    first_off = next(t for t, v in points if v == 0)
    gaps = {}
    previous_time = 0
    previous_value = None
    for time, value in points:
        if time == 0 or value == previous_value:
            continue
        if value == 0:
            gaps[previous_time] = wrap + first_off if time == 24 else time - previous_time
        previous_time = time
        previous_value = value
    gap_start = max(gaps, key=gaps.get)
    gap_end = gap_start + gaps[gap_start]
    if gap_end > 24:
        gap_end -= 24
    closed = {gap_start: 1.0, gap_end: 0.0, 24.0: 0.0 if gap_start > gap_end else 1.0}
    return sorted(closed.items())


def daily_hours(fraction: np.ndarray) -> list[Hours]:
    """Inferred hours of operation for each of the 365 days."""
    result = []
    for day in range(365):
        values = fraction[24 * day:24 * (day + 1)]
        low = values.min()
        threshold = low + (values.max() - low) * THRESHOLD_FRACTION
        on_off = [1.0 if v != 0 and v >= threshold else 0.0 for v in values]
        points = _close_gaps(points_from_hourly(on_off))
        # OpenStudio rejects a point at time 0 when the profile is stored.
        points = [(t, v) for t, v in points if t > 0]
        result.append(hours_from_points(points))
    return result


def sampled_hours(start_seconds: float, duration_seconds: float) -> Hours:
    """Hours of operation from sampled start time and duration.

    CreateTypical truncates fractional hours to whole minutes.
    """
    start = _truncate_to_minute(start_seconds / 3600)
    duration = _truncate_to_minute(duration_seconds / 3600)
    end = start + duration
    points = {}
    if end < 24:
        points[start] = 0.0
        points[end] = 1.0
        points[24.0] = 0.0
    else:
        points[end - 24] = 1.0
        points[start] = 0.0
        points[24.0] = 1.0
    return hours_from_points([(t, v) for t, v in sorted(points.items()) if t > 0])


def _truncate_to_minute(hours: float) -> float:
    return math.floor(hours) + math.floor(60 * (hours % 1)) / 60
