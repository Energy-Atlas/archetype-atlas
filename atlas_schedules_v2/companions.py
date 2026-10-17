"""Companion channels: controls and fixed loads a recipe selects alongside its kernel.

Methods:
- "constant": one value all year (activity W/person, water target temperatures);
- "source_rules": a source rule set evaluated on the calendar;
- "fixed_background": an OpenStudio-HPXML default weekday/weekend profile with
  monthly multipliers (refrigerator, freezer, exterior lighting);
- "translated_thermostat": ResStock thermostat arguments turned into heating and
  cooling setpoints (ResStockArguments `modify_setpoint_schedule`, then HPXML
  `get_hvac_setpoints`). Where cooling falls below heating, both take their midpoint.
"""
from datetime import date, timedelta
from functools import lru_cache
import json
from pathlib import Path

import numpy as np

from .calendar import evaluate_rules
from .errors import GeneratorError

DATA = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def _fixed_backgrounds() -> dict:
    record = json.loads((DATA / "residential/fixed-background-schedules.json").read_text(encoding="utf-8"))
    return record["definition"]["schedules"]


def _is_weekend(day: int, year: int) -> bool:
    return (date(year, 1, 1) + timedelta(days=day)).weekday() > 4


def fixed_background(slot: str, year: int = 2007) -> np.ndarray:
    shape = _fixed_backgrounds()[slot]
    values = []
    for day in range(365):
        month = (date(year, 1, 1) + timedelta(days=day)).month
        profile = shape["weekend_fractions"] if _is_weekend(day, year) else shape["weekday_fractions"]
        scale = shape["monthly_multipliers"][month - 1] / shape["peak_divisor"]
        values.extend(v * scale for v in profile)
    return np.asarray(values)


def _setpoint_profiles(arguments: dict) -> dict:
    profiles = {}
    for mode in ("heating", "cooling"):
        if arguments[f"hvac_control_{mode}_season_period"] != "Jan 1 - Dec 31":
            raise GeneratorError("unsupported_input", f"/thermostat/{mode}", "Only a full-year season is supported")
        for daytype in ("weekday", "weekend"):
            prefix = f"hvac_control_{mode}_{daytype}_setpoint"
            base_f = float(arguments[prefix + "_temp"])
            magnitude_f = float(arguments[prefix + "_offset_magnitude"])
            directions = [float(v) for v in arguments[prefix + "_schedule"].split(",")]
            profiles[mode, daytype] = [(base_f + magnitude_f * d - 32) * 5 / 9 for d in directions]
    return profiles


def thermostat_setpoints(arguments: dict, year: int = 2007) -> dict:
    """{"heating_setpoint": 8760 degC, "cooling_setpoint": 8760 degC}."""
    profiles = _setpoint_profiles(arguments)
    heating_values = []
    cooling_values = []
    for day in range(365):
        daytype = "weekend" if _is_weekend(day, year) else "weekday"
        for heating, cooling in zip(profiles["heating", daytype], profiles["cooling", daytype]):
            if cooling < heating:
                heating = cooling = (heating + cooling) / 2
            heating_values.append(heating)
            cooling_values.append(cooling)
    return {"heating_setpoint": np.asarray(heating_values), "cooling_setpoint": np.asarray(cooling_values)}


def companion_channels(rules: dict, schedules: dict, thermostat_arguments: dict | None, year: int = 2007) -> dict:
    """Channels for every companion rule of a recipe.

    rules: {slot: {"method": ..., ...}}; schedules: rule sets by id.
    """
    channels = {}
    for slot, rule in rules.items():
        method = rule["method"]
        if method == "constant":
            channels[slot] = np.full(8760, float(rule["value"]))
        elif method == "source_rules":
            channels[slot] = evaluate_rules(schedules[rule["schedule"]], year)[0]
        elif method == "fixed_background":
            channels[slot] = fixed_background(rule["source_slot"], year)
        elif method == "translated_thermostat":
            if slot not in channels:
                channels.update(thermostat_setpoints(thermostat_arguments, year))
        else:
            raise GeneratorError("unsupported_binding", f"/companions/{slot}", f"Unknown companion method {method!r}")
    return channels
