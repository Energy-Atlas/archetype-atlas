"""Day profiles as OpenStudio stores them, and conversion to hourly values.

A day profile is a list of (until_hour, value) points: each value holds from
the previous point up to and including `until_hour`, and the last point is at
24. This matches OpenStudio `ScheduleDay` times/values.
"""
import math

Point = tuple[float, float]


def round_half_up(value: float, places: int) -> float:
    """Ruby 3.2 `Float#round(places)` (numeric.c `round_half_up`).

    Halves round away from zero, and the result is nudged when `value * scale`
    lost a half in binary. Without the nudge, 5- and 6-decimal results differ
    from native output by one unit at ties (commercial family answer keys).
    """
    scale = 10.0 ** places
    scaled = value * scale
    rounded = math.floor(scaled + 0.5) if scaled > 0 else math.ceil(scaled - 0.5)
    if scale != 1:
        if value > 0 and (rounded + 0.5) / scale <= value:
            rounded += 1
        elif value <= 0 and (rounded - 0.5) / scale >= value:
            rounded -= 1
    return rounded / scale


def points_from_hourly(values) -> list[Point]:
    """Collapse 24 hourly values into change points (or one point for 1 value)."""
    values = [float(v) for v in values]
    if len(values) == 1:
        return [(24.0, values[0])]
    points = []
    for hour, value in enumerate(values):
        if hour == 23 or value != values[hour + 1]:
            points.append((float(hour + 1), value))
    return points


def stored_value(value: float) -> float:
    """OpenStudio keeps day values as 15-significant-digit text. This matters:
    it decides which side of a 5-decimal rounding tie a value lands on
    (commercial answer key, occupancy x 0.231)."""
    return float(f"{value:.15g}")


def store_points(points) -> list[Point]:
    """OpenStudio `ScheduleDay.addValue`: truncate times to whole minutes,
    keep the last value per time, drop times outside (0, 24], sort."""
    stored = {}
    for time, value in points:
        hour = math.floor(time)
        minute = math.floor((time - hour) * 60)
        native_time = (hour * 60 + minute) / 60
        if 0 < native_time <= 24:
            stored[native_time] = stored_value(value)
    return sorted(stored.items())


def hourly_from_points(points, steps_per_hour: int = 6) -> list[float]:
    """Hourly values as openstudio-standards 0.8.6 reads them under OpenStudio 3.10.

    The standards gem compares version strings lexically, so 3.10.0 takes its
    legacy branch: sample each hour at the profile's smallest point interval
    (at most 15 minutes), average, and round to 5 places. Each sample time is
    snapped forward to the model timestep, as `ScheduleDay.getValue` does.
    """
    minutes = [int(round(time * 60)) for time, _ in points]
    interval = 15
    previous = 0
    for minute in minutes:
        interval = min(interval, minute - previous)
        previous = minute
    offsets = range(interval, 61, interval)
    timestep = 60 / steps_per_hour
    queries = [math.ceil(offset / timestep) * timestep for offset in offsets]
    values = [value for _, value in points]
    hourly = []
    for hour in range(24):
        samples = [_value_at(minutes, values, hour * 60 + q) for q in queries]
        hourly.append(round_half_up(math.fsum(samples) / len(samples), 5))
    return hourly


def _value_at(minutes: list[int], values: list[float], minute: float) -> float:
    for until, value in zip(minutes, values):
        if until >= minute:
            return value
    return values[-1]
