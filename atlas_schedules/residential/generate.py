"""Residential schedules for one dwelling unit (ResStock / OpenStudio-HPXML).

Outputs are normalised hourly shapes (fractions of their own peak, occupants
as a fraction of residents). Annual magnitudes are bound later by budgets.
"""
from dataclasses import dataclass
from datetime import date, timedelta
import math

import numpy as np

from ..errors import GeneratorError
from .activity import simulate_activities
from .events import EventGenerator
from .rng import unit_streams
from .shapes import interior_lighting, occupants, plug_and_fan_shapes
from .shift import normalize, shift_and_normalize, state_shifts
from .tables import load_drybulb, load_tables

INSTALLED_KEYS = ("dishwasher", "clothes_washer", "clothes_dryer", "cooking_range",
                  "plug_loads_other", "plug_loads_tv", "ceiling_fan", "garage")
APPLIANCE_SLOTS = (("hot_water_dishwasher", "dishwasher"), ("dishwasher", "dishwasher"),
                   ("hot_water_clothes_washer", "clothes_washer"), ("clothes_washer", "clothes_washer"),
                   ("clothes_dryer", "clothes_dryer"), ("cooking_range", "cooking_range"))
FIXTURE_COMPONENTS = ("shower", "sink", "bath")


@dataclass(frozen=True)
class Dwelling:
    residents: float
    state: str
    latitude: float
    longitude: float
    utc_offset: float
    weather_id: str | None = None
    installed: dict | None = None


def resident_count(residents: float) -> int:
    """Upstream truncates the resident count to an integer."""
    count = int(residents)
    if residents != 0 and count == 0:
        raise GeneratorError("unsupported_input", "/inputs/residents",
                             "A positive resident count below one has no upstream meaning")
    return count


def _step_months(year: int) -> list:
    return [(date(year, 1, 1) + timedelta(days=step // 96)).month - 1 for step in range(365 * 96)]


def _events(activities, streams, tables, shifts, installed, year) -> dict:
    series = EventGenerator(activities, streams, tables, _step_months(year)).generate(installed)
    offset = activities.offset_minutes
    channels = {}
    for slot, appliance in APPLIANCE_SLOTS:
        present = installed[appliance] and (slot != "clothes_dryer" or installed["clothes_washer"])
        if not present:
            continue
        if max(series[slot]) <= 0:
            raise GeneratorError("zero_generated_integral", f"/channels/{slot}",
                                 "No events were generated; upstream does not retry")
        channels[slot] = shift_and_normalize(series[slot], offset, shifts, year)
    components = []
    for name in FIXTURE_COMPONENTS:
        if max(series[name]) <= 0:
            raise GeneratorError("zero_generated_integral", f"/channels/hot_water_fixtures/{name}",
                                 "A fixture component has no events; upstream does not retry")
        components.append(shift_and_normalize(series[name], offset, shifts, year))
    channels["hot_water_fixtures"] = normalize(np.sum(components, axis=0))
    return channels


def generate_dwelling(dwelling: Dwelling, unit_seed: int, rng_mode: str, year: int = 2007) -> dict:
    """All residential channels for one unit."""
    count = resident_count(dwelling.residents)
    if count == 0:
        # Upstream skips the unit before creating any random stream.
        return {"occupants": np.zeros(8760)}
    streams = unit_streams(rng_mode, unit_seed)
    activities = simulate_activities(count, streams["main"], load_tables(), year)
    return dwelling_channels(dwelling, activities, streams, year)


def dwelling_channels(dwelling: Dwelling, activities, streams: dict, year: int = 2007) -> dict:
    """Channels from given activity traces; events draw from the end-use streams."""
    tables = load_tables()
    shifts = state_shifts(tables, dwelling.state)
    drybulb = load_drybulb(dwelling.weather_id)
    channels = {"occupants": occupants(activities, shifts, year)}
    channels.update(plug_and_fan_shapes(activities, tables, shifts, dwelling.installed, drybulb, year))
    channels["lighting_interior"] = interior_lighting(activities, tables, shifts, dwelling.latitude,
                                                      dwelling.longitude, dwelling.utc_offset, year)
    if dwelling.installed["garage"]:
        channels["lighting_garage"] = channels["lighting_interior"].copy()
    channels.update(_events(activities, streams, tables, shifts, dwelling.installed, year))
    return channels


def generate_occupancy_and_lighting(dwelling: Dwelling, unit_seed: int, rng_mode: str, year: int = 2007) -> dict:
    """Only occupants and interior lighting (apartment units); no weather or events needed."""
    count = resident_count(dwelling.residents)
    if count == 0:
        raise GeneratorError("unsupported_input", "/inputs/residents", "Zero-resident units are skipped by the caller")
    tables = load_tables()
    shifts = state_shifts(tables, dwelling.state)
    streams = unit_streams(rng_mode, unit_seed)
    activities = simulate_activities(count, streams["main"], tables, year)
    return {
        "occupants": occupants(activities, shifts, year),
        "lighting_interior": interior_lighting(activities, tables, shifts, dwelling.latitude,
                                               dwelling.longitude, dwelling.utc_offset, year),
    }
