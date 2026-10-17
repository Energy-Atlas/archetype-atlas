"""Upstream minute-to-hour export: rotate, shift by month, sum per hour, normalise.

OpenStudio-HPXML `schedules.rb` (lines 1477-1501): the whole minute series is
rotated by the unit's random offset, each day is rotated by its state/month
"lead", minutes are summed per hour, and the year is divided by its maximum
(or by 60 for occupants, which are fractions of residents per minute).
"""
from datetime import date, timedelta
import math

import numpy as np

from ..errors import GeneratorError
from .tables import MONTHS


def normalize(values, denominator: float | None = None) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    divisor = values.max() if denominator is None else denominator
    if not math.isfinite(divisor) or divisor <= 0:
        raise GeneratorError("zero_generated_integral", "/channels", "No positive value to normalise by")
    return values / divisor


def shift_and_normalize(minutes: list, offset: int, shifts: dict, year: int = 2007,
                        denominator: float | None = None) -> np.ndarray:
    """Hourly normalised values from a minute series (which may run past the year)."""
    offset %= len(minutes)
    rotated = minutes[offset:] + minutes[:offset]
    hourly = []
    for index in range(365):
        day = date(year, 1, 1) + timedelta(days=index)
        daytype = "weekend" if day.weekday() >= 5 else "weekday"
        lead = shifts[daytype][MONTHS[day.month - 1]] % 1440
        values = rotated[index * 1440:(index + 1) * 1440]
        values = values[lead:] + values[:lead]
        hourly.extend(math.fsum(values[j:j + 60]) for j in range(0, 1440, 60))
    return normalize(hourly, denominator)


def state_shifts(tables, state: str) -> dict:
    """{daytype: {month: lead minutes}} for a US state."""
    try:
        return {daytype: tables.shifts[daytype, state] for daytype in ("weekday", "weekend")}
    except KeyError as error:
        raise GeneratorError("unsupported_input", "/inputs/state", f"No monthly shifts for state {state!r}") from error
