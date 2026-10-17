"""Expand an hourly rule set into 8,760 values for one non-leap year.

Follows openstudio-standards `Standards.Model#model_add_schedule`: rules are
applied in source order, so a later matching rule overrides an earlier one;
the `Default` rule supplies the default day; design-day rules (`WntrDsn`,
`SmrDsn`) are kept aside and never enter the annual array; `Hol` rows are
ignored by that method, and explicit holiday dates select the default day.
"""
import calendar as _calendar
from datetime import date, timedelta

import numpy as np

from .errors import GeneratorError

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
DESIGN_DAYS = ("WntrDsn", "SmrDsn")


def _month_day(text: str) -> tuple[int, int]:
    """Accept 'MM-DD', 'YYYY-MM-DD' or an ISO datetime; return (month, day)."""
    if len(text) == 5:
        text = "2000-" + text
    parsed = date.fromisoformat(text[:10])
    return parsed.month, parsed.day


def _profile(rule: dict) -> list[float]:
    values = rule["values"]
    if len(values) == 1:
        return [float(values[0])] * 24
    if len(values) != 24:
        raise GeneratorError("invalid_schedule", "/rules/values", "One constant or 24 hourly values required")
    return [float(v) for v in values]


def _day_types(rule: dict) -> set[str]:
    tokens = rule["day_types"]
    if isinstance(tokens, str):
        tokens = tokens.split("|")
    return set(tokens)


def _applies(tokens: set[str], weekday: int) -> bool:
    if DAY_NAMES[weekday] in tokens:
        return True
    if weekday < 5 and "Wkdy" in tokens:
        return True
    return weekday >= 5 and "Wknd" in tokens


def _active(start: tuple, end: tuple, month_day: tuple) -> bool:
    if start <= end:
        return start <= month_day <= end
    return month_day >= start or month_day <= end


def evaluate_rules(schedule: dict, year: int = 2007, holidays: tuple[str, ...] = ()) -> tuple[np.ndarray, dict]:
    """Return (8760 hourly values, design-day profiles keyed by WntrDsn/SmrDsn)."""
    if _calendar.isleap(year):
        raise GeneratorError("leap_year", "/calendar/year", "Non-leap year required")
    holiday_dates = {date.fromisoformat(h) for h in holidays}
    compiled = []
    default = None
    design = {}
    for rule in schedule["rules"]:
        tokens = _day_types(rule)
        profile = _profile(rule)
        if "Default" in tokens:
            default = profile
        for key in DESIGN_DAYS:
            if key in tokens:
                design[key] = profile
        start = _month_day(rule["start_date"])
        end = _month_day(rule["end_date"])
        compiled.append((tokens, start, end, profile))
    if default is None:
        # Standards creates an empty default day when no Default row exists;
        # OpenStudio reads it as zero.
        default = [0.0] * 24
    days = []
    for index in range(365):
        day = date(year, 1, 1) + timedelta(days=index)
        selected = default
        if day not in holiday_dates:
            month_day = (day.month, day.day)
            for tokens, start, end, profile in compiled:
                if _active(start, end, month_day) and _applies(tokens, day.weekday()):
                    selected = profile
        days.append(selected)
    return np.asarray(days, dtype=float).reshape(8760), design
