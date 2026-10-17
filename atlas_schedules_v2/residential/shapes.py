"""Occupancy-driven shapes: occupants, interior lighting, plug loads, TV, ceiling fan.

OpenStudio-HPXML `schedules.rb` lines 913-1075. From the activity traces:
`home` = share of residents not away; `awake` = share neither away nor asleep.
A load with day profile p and month multiplier m gets
`min(p) + (p[h] x m - min(p)) x awake` at each 15-minute step. No random draws.
"""
import calendar
from datetime import date, timedelta
import math

import numpy as np

from .activity import AWAY, SLEEPING, STEPS_PER_YEAR, Activities
from .lighting import monthly_profiles
from .shift import shift_and_normalize

FAN_MONTH_THRESHOLD_F = 63.0


def resident_fractions(activities: Activities) -> tuple[np.ndarray, np.ndarray]:
    """(awake share per 15-minute step, home share per 15-minute step)."""
    states = activities.states
    count = states.shape[0]
    away = (states == AWAY).sum(axis=0) / count
    sleeping = (states == SLEEPING).sum(axis=0) / count
    return 1 - (away + sleeping), 1 - away


def _minutes(step_values) -> list:
    return np.repeat(np.asarray(step_values, dtype=float), 15).tolist()


def occupants(activities: Activities, shifts: dict, year: int = 2007) -> np.ndarray:
    _, home = resident_fractions(activities)
    return shift_and_normalize(_minutes(home), activities.offset_minutes, shifts, year, denominator=60)


def _modulated(awake, weekday, weekend, monthly, year: int) -> list:
    """Step values min + (full - min) x awake for weekday/weekend profiles and month multipliers."""
    values = np.empty(STEPS_PER_YEAR)
    for index in range(365):
        day = date(year, 1, 1) + timedelta(days=index)
        profile = weekend if day.weekday() >= 5 else weekday
        minimum = min(profile)
        full = np.repeat(np.asarray(profile, dtype=float) * monthly[day.month - 1], 4)
        step = slice(index * 96, (index + 1) * 96)
        values[step] = minimum + (full - minimum) * awake[step]
    return values


def fan_months(drybulb, year: int = 2007) -> list:
    """1 for months whose mean dry-bulb exceeds 63 F, else 0."""
    flags = []
    start = 0
    for month in range(1, 13):
        hours = calendar.monthrange(year, month)[1] * 24
        mean = math.fsum(drybulb[start:start + hours]) / hours
        flags.append(int(mean * 1.8 + 32 > FAN_MONTH_THRESHOLD_F))
        start += hours
    return flags


def plug_and_fan_shapes(activities: Activities, tables, shifts: dict, installed: dict,
                        drybulb, year: int = 2007) -> dict:
    awake, _ = resident_fractions(activities)
    custom, defaults = tables.custom, tables.defaults
    specs = {
        "plug_loads_other": (defaults["plug_loads_other", "WeekdayScheduleFractions"],
                             defaults["plug_loads_other", "WeekendScheduleFractions"],
                             custom["plug_loads_other", "PlugLoadsOtherMonthlyMultipliers"]),
        "plug_loads_tv": (custom["plug_loads_tv", "PlugLoadsTVWeekdayFractions"],
                          custom["plug_loads_tv", "PlugLoadsTVWeekendFractions"],
                          custom["plug_loads_tv", "PlugLoadsTVMonthlyMultipliers"]),
        "ceiling_fan": (defaults["ceiling_fan", "WeekdayScheduleFractions"],
                        defaults["ceiling_fan", "WeekendScheduleFractions"],
                        fan_months(drybulb, year)),
    }
    shapes = {}
    for slot, (weekday, weekend, monthly) in specs.items():
        if installed[slot]:
            steps = _modulated(awake, weekday, weekend, monthly, year)
            shapes[slot] = shift_and_normalize(_minutes(steps), activities.offset_minutes, shifts, year)
    return shapes


def interior_lighting(activities: Activities, tables, shifts: dict, latitude: float, longitude: float,
                      utc_offset: float, year: int = 2007) -> np.ndarray:
    awake, _ = resident_fractions(activities)
    seasonal = tables.custom["lighting_interior", "LightingInteriorMonthlyMultipliers"]
    profiles = monthly_profiles(latitude, longitude, utc_offset, seasonal)
    steps = np.empty(STEPS_PER_YEAR)
    for index in range(365):
        month = (date(year, 1, 1) + timedelta(days=index)).month
        profile = profiles[month - 1]
        minimum = min(profile)
        full = np.repeat(np.asarray(profile), 4)
        step = slice(index * 96, (index + 1) * 96)
        steps[step] = minimum + (full - minimum) * awake[step]
    return shift_and_normalize(_minutes(steps), activities.offset_minutes, shifts, year)
