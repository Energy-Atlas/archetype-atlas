"""Rewrite a day profile relative to the hours of operation, then re-apply it.

Ports openstudio-standards 0.8.6 `schedules/parametric.rb`:
- `schedule_ruleset_get_parametric_inputs` -> `to_relative`
- `schedule_day_adjust_from_parameters` -> `apply`

A relative profile is a list of anchored points. Each point sits a signed
offset before the original start, middle or end of operation, and carries one
or two values. Step profiles (fewer than 3 distinct values) store "floor" and
"ceiling" symbolically so they follow the rule set's own range.
"""
from dataclasses import dataclass
import math

from .hours import Hours
from .profiles import round_half_up, store_points

ANCHORS = ("start", "mid", "end")
MAX_RAMP_HOURS = 2.0


@dataclass(frozen=True)
class RelativePoint:
    anchor: str
    offset: float
    values: tuple


def _raw_points(points) -> dict[float, list]:
    """Breakpoints before anchoring; ramped profiles get points at t +/- delta."""
    values = [v for _, v in points]
    step_profile = len(set(values)) < 3
    raw = {}
    for j, (time, value) in enumerate(points):
        if len(points) > 1 and j == len(points) - 1 and value == values[0]:
            continue
        next_value = values[j + 1] if j + 1 < len(points) else values[0]
        if step_profile:
            raw[time] = [value, next_value]
            continue
        previous_time = points[j - 1][0] if j > 0 else points[-1][0] - 24
        next_time = points[j + 1][0] if j + 1 < len(points) else points[0][0] + 24
        delta = min(MAX_RAMP_HOURS, (time - previous_time) * 0.5, (next_time - time) * 0.5)
        left = time - delta
        if left not in raw:
            raw[left + 24 if left < 0 else left] = [value]
        right = time + delta
        raw[right - 24 if right > 24 else right] = [next_value]
    return raw


def _nearest_anchor(time: float, hours: Hours) -> tuple[int, float]:
    """Index of the closest anchor and the offset to it, measured around the clock."""
    anchors = (hours.start, hours.start + hours.hours * 0.5, hours.end)
    offsets = []
    for anchor in anchors:
        options = (anchor - time, anchor - time + 24, anchor - time - 24)
        offsets.append(min(options, key=abs))
    index = min(range(3), key=lambda i: abs(offsets[i]))
    return index, round_half_up(offsets[index], 2)


def to_relative(points, hours: Hours, floor: float, ceiling: float, mode: str) -> list[RelativePoint]:
    """Express a day profile relative to its original hours of operation.

    mode "hours": anchor each point to the nearest of start/mid/end.
    mode "tstat": thermostats keep only a start step and an end step.
    """
    values = [v for _, v in points]
    step_profile = len(set(values)) < 3
    relative = []
    start_values = None
    for time, raw_values in sorted(_raw_points(points).items()):
        index, offset = _nearest_anchor(time, hours)
        if step_profile:
            converted = ["floor" if v == floor else "ceiling" if v == ceiling else v for v in raw_values]
        else:
            converted = list(raw_values)
        if mode == "tstat":
            if index == 0 and start_values is None:
                start_values = list(converted)
            else:
                index = 2
                if start_values is not None:
                    converted = list(reversed(start_values))
            offset = 0
        relative.append(RelativePoint(ANCHORS[index], offset, tuple(converted)))
    return relative


def _anchor_times(start: float, end: float, frequency: float) -> dict[str, float]:
    occupied = end - start if end >= start else 24 + end - start
    mid = start + occupied * 0.5
    minute_grid = [i * 60 * frequency for i in range(int(1 / frequency) + 1)]
    mid_minutes = min(minute_grid, key=lambda m: abs(m - (mid % 1) * 60))
    return {"start": start, "mid": math.floor(mid) + mid_minutes / 60, "end": end}


def _resolve(relative, anchors, floor, ceiling) -> list[list[float]]:
    numbers = {}
    for point in relative:
        time = anchors[point.anchor] - point.offset
        numbers[time] = [floor if v == "floor" else ceiling if v == "ceiling" else v for v in point.values]
    return [[time, value] for time, values in numbers.items() for value in values]


def _fix_order(pairs, frequency):
    """Rotate negative times into the day, start at the earliest time, and pull
    out-of-order times back (CreateTypical calls with error_on_out_of_order=false)."""
    negatives = set()
    for i, pair in enumerate(pairs):
        if pair[0] < 0:
            negatives.add(i)
            pair[0] += 24
    first = min(range(len(pairs)), key=lambda i: pairs[i][0])
    pairs = pairs[first:] + pairs[:first]
    last = None
    for i, pair in enumerate(pairs):
        if last is None:
            last = pair[0]
            continue
        if pair[0] < last or i in negatives:
            if i in negatives:
                updated = 0.0
            else:
                buffer = pairs[i - 1][0] if i < 2 else pairs[i - 1][0] - pairs[i - 2][0]
                updated = pairs[i - 1][0] - min(frequency, buffer)
            pairs[i - 1][0] = updated
            pair[0] = updated
        last = pair[0]
    return pairs


def _insert_ramps(pairs, frequency):
    """Add a linearly interpolated point one step after each change in value."""
    i = 0
    while i < len(pairs):
        time, value = pairs[i]
        if i + 1 < len(pairs):
            next_time, next_value = pairs[i + 1]
        else:
            next_time, next_value = pairs[0][0] + 24, pairs[0][1]
        length = next_time - time
        if length > frequency and value != next_value:
            t = time + frequency
            interpolated = next_value * (t - time) / length + value * (next_time - t) / length
            pairs.insert(i + 1, [t, interpolated])
        i += 1
    return pairs


def _wrap_day(pairs):
    """Drop duplicate times, rotate times past 24 back to the front, close at 24."""
    seen = set()
    unique = []
    for pair in pairs:
        if pair[0] not in seen:
            unique.append(pair)
            seen.add(pair[0])
    rotation = 0
    for pair in reversed(unique):
        if pair[0] > 24:
            rotation -= 1
            pair[0] -= 24
    if rotation:
        unique = unique[rotation:] + unique[:rotation]
    if int(unique[-1][0]) != 24:
        unique.append([24.0, unique[0][1]])
    return unique


def apply(relative, hours: Hours, floor: float, ceiling: float, frequency: float = 1 / 6) -> list[tuple[float, float]]:
    """Re-create a day profile for new hours of operation."""
    anchors = _anchor_times(hours.start, hours.end, frequency)
    pairs = _resolve(relative, anchors, floor, ceiling)
    pairs = _fix_order(pairs, frequency)
    pairs = _insert_ramps(pairs, frequency)
    pairs = _wrap_day(pairs)
    return store_points(pairs)
