"""ComStock operating-hours transform of source schedules.

Pipeline, per building:
1. infer each day's original hours of operation from People-weighted occupancy;
2. build new weekday and weekend hours from the sampled start and duration;
3. for every slot, rewrite each day relative to the original hours and
   re-apply it with the new hours;
4. scale occupancy by the peak occupancy fraction;
5. apply base-to-peak ratios to lighting and plug loads;
6. read hourly values the way the standards gem does.
"""
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from ..calendar import evaluate_rules
from ..errors import GeneratorError
from .base_peak import adjust_day
from .hours import daily_hours, occupancy_fraction, sampled_hours
from .parametric import apply, to_relative
from .profiles import hourly_from_points, points_from_hourly, stored_value

PEAK_OCCUPANCY_FRACTION = 0.231
ORDINARY_DAY_TYPES = {"Default", "Wkdy", "Wknd", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}
BASE_PEAK_PREFIX = {"lighting": "ltg_sch", "additional_lighting": "ltg_sch", "electric_equipment": "plugload_sch"}


@dataclass(frozen=True)
class Slot:
    """One source schedule to transform: its rule set and mode ("hours" or "tstat")."""
    rules: dict
    mode: str


def _is_weekday(day: int, year: int) -> bool:
    return (date(year, 1, 1) + timedelta(days=day)).weekday() < 5


def _floor_and_ceiling(rules: dict) -> tuple[float, float]:
    """Range over ordinary day rules only (design days excluded)."""
    values = []
    for rule in rules["rules"]:
        tokens = rule["day_types"]
        tokens = set(tokens.split("|")) if isinstance(tokens, str) else set(tokens)
        if tokens & ORDINARY_DAY_TYPES:
            values.extend(rule["values"])
    return min(values), max(values)


def _transform_days(slot: Slot, original_hours, new_hours, year: int) -> list[list]:
    raw, _ = evaluate_rules(slot.rules, year)
    floor, ceiling = _floor_and_ceiling(slot.rules)
    cache = {}
    days = []
    for day in range(365):
        kind = "weekday" if _is_weekday(day, year) else "weekend"
        points = points_from_hourly(raw[24 * day:24 * (day + 1)])
        key = (tuple(points), original_hours[day], kind)
        if key not in cache:
            relative = to_relative(points, original_hours[day], floor, ceiling, slot.mode)
            cache[key] = apply(relative, new_hours[kind], floor, ceiling)
        days.append(cache[key])
    return days


def _base_peak(days: list, prefix: str, operating: dict, year: int) -> list:
    weekday_ratio = operating[prefix + "_weekday_base_peak_ratio"]
    weekend_ratio = operating[prefix + "_weekend_base_peak_ratio"]
    bases = []
    if weekday_ratio["modify"]:
        for day in range(365):
            if _is_weekday(day, year):
                days[day], base = adjust_day(days[day], weekday_ratio["value"])
                bases.append(base)
    if weekend_ratio["modify"]:
        if not bases:
            raise GeneratorError("source_selection", "/commercial/base_peak",
                                 "A weekend base-to-peak ratio needs weekday bases")
        lowest_weekday_base = min(bases)
        for day in range(365):
            if not _is_weekday(day, year):
                days[day], _ = adjust_day(days[day], weekend_ratio["value"], lowest_weekday_base)
    return days


def transform(slots: dict[str, Slot], people_groups: list[tuple[dict, float]],
              operating: dict, year: int = 2007) -> dict[str, np.ndarray]:
    """Transformed 8,760-hour arrays for every slot.

    people_groups: (People schedule rule set, design people) pairs used to
    infer the original hours of operation.
    operating: sampled parameters from `sampler.sample_operating_parameters`.
    """
    groups = [(evaluate_rules(rules, year)[0], weight) for rules, weight in people_groups]
    original_hours = daily_hours(occupancy_fraction(groups))
    new_hours = {
        "weekday": sampled_hours(operating["weekday_start_time"]["value"], operating["weekday_duration"]["value"]),
        "weekend": sampled_hours(operating["weekend_start_time"]["value"], operating["weekend_duration"]["value"]),
    }
    output = {}
    for name, slot in slots.items():
        days = _transform_days(slot, original_hours, new_hours, year)
        if name == "occupancy":
            days = [[(t, stored_value(v * PEAK_OCCUPANCY_FRACTION)) for t, v in points] for points in days]
        if name in BASE_PEAK_PREFIX:
            days = _base_peak(days, BASE_PEAK_PREFIX[name], operating, year)
        hourly_cache = {}
        values = []
        for points in days:
            key = tuple(points)
            if key not in hourly_cache:
                hourly_cache[key] = hourly_from_points(points)
            values.extend(hourly_cache[key])
        output[name] = np.asarray(values)
    return output
