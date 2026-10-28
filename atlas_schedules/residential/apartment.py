"""An apartment unit as a ResStock multifamily unit (rulings 185-187; plan section 8, B6).

Inside the unit everything is ResStock's, from one draw per unit:
1. characteristics: residential/characteristics.py, conditioned on the request location (state, climate
   zone), the unit's floor-area bin and residents, and the programme's building type, height class,
   vintages and HVAC (`recipe["resstock_unit"]`);
2. annual energy per end use: residential/arguments.py and residential/annual.py with the caller's exact
   floor area; the design level of each load is fitted to its generated schedule (annual / full-load
   hours), as OpenStudio-HPXML `calc_design_level_from_annual_kwh` does;
3. schedules: the ResStock schedule generator for the unit's residents and installed appliances, and the
   fixed background profiles for refrigeration, well pumps, fuel loads, pools and spas;
4. controls: residents per dwelling unit, ResStock's constant activity, and the sampled thermostat;
5. hot water (ruling 185, P2): the prototype's volume per design person (`recipe["resstock_unit"]
   ["hot_water_m3_per_person"]`) x residents, timed by the unit's own ResStock fixture events, with the
   peak flow fitted to the draw. The building's water service heats it.

Exterior and garage lighting are left to the building: the prototype's exterior lighting covers the site,
and a unit has no garage.
"""
from dataclasses import dataclass
from functools import lru_cache
import json
import math

import numpy as np

from ..budgets import fit_amplitude
from ..companions import fixed_background, thermostat_setpoints
from ..errors import GeneratorError
from ..mixtures import Load
from .annual import annual_loads
from .arguments import unit_arguments
from .characteristics import Conditions, floor_area_option, occupants_option, sample_characteristics
from .generate import Dwelling, generate_dwelling
from .shapes import fan_months
from .tables import DATA as TABLES_DATA, load_drybulb

FT2_PER_M2 = 1 / 0.09290304
WH_PER_THERM = 29307.107017222222
# Defaults.get_occupancy_values: (3716 + 2884) Btu/person/day over 16.5 h, in W.
ACTIVITY_W_PER_PERSON = (3716.0 + 2884.0) / 16.5 * 0.2930710701722222
BUILDING_END_USES = {"lighting_exterior", "lighting_garage"}
EVENT_SLOTS = {"clothes_washer", "dishwasher", "clothes_dryer", "cooking_range", "plug_loads_other", "plug_loads_tv",
               "ceiling_fan", "lighting_interior"}
LIGHTING_HEAT = {"radiant": 0.6, "visible": 0.2, "return_air": 0}
CEILING_FAN_HEAT = {"radiant": 0.558, "latent": 0, "lost": 0}


@dataclass
class UnitResult:
    channels: dict          # slot -> 8760 values (fractions, or degC for setpoints)
    loads: list             # Load
    controls: list          # control slots
    water: tuple            # (annual m3, 8760 fixture shape)
    generation: dict


@lru_cache(maxsize=1)
def _stations() -> list:
    stations = []
    for path in sorted((TABLES_DATA / "weather").glob("USA_*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        stations.append((path.stem, path.name.split("_")[1], record["latitude"], record["longitude"]))
    return stations


def nearest_station(state: str, latitude: float, longitude: float) -> str:
    """The packaged TMY3 station nearest the unit, preferring its own state."""
    def distance(row):
        p1, p2 = math.radians(latitude), math.radians(row[2])
        d = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(row[3] - longitude) / 2) ** 2
        return 2 * math.asin(math.sqrt(d))
    rows = [r for r in _stations() if r[1] == state] or _stations()
    return min(rows, key=distance)[0]


def _heat(load: dict) -> dict:
    if load["end_use"].startswith("lighting_"):
        return LIGHTING_HEAT
    if load["end_use"] == "ceiling_fan":
        return CEILING_FAN_HEAT
    sensible, latent = load["sensible_fraction"], load["latent_fraction"]
    return {"radiant": 0.6 * sensible, "latent": latent, "lost": 1 - sensible - latent}


def conditions_for(spec: dict, location, floor_area_m2: float, residents) -> Conditions:
    return Conditions(state=location.state, building_type=spec["building_type"], floor_area=floor_area_option(floor_area_m2),
                      vintages=tuple(spec["vintages"]), climate_zone=getattr(location, "climate_zone", None),
                      height=spec.get("height"), occupants=None if residents == "resstock" else occupants_option(residents),
                      hvac=tuple(spec["hvac"]) if spec.get("hvac") else None)


def resstock_unit(spec: dict, location, floor_area_m2: float, residents, unit_seed: int, rng_mode: str,
                  type_probabilities) -> UnitResult:
    """One apartment unit; residents is an integer or "resstock" (drawn, vacancy included)."""
    characteristics = sample_characteristics(conditions_for(spec, location, floor_area_m2, residents), unit_seed)
    arguments = unit_arguments(characteristics)
    count = int(arguments["geometry_unit_num_occupants"]) if residents == "resstock" else int(residents)
    bedrooms = int(arguments["geometry_unit_num_bedrooms"])
    weather_id = getattr(location, "weather_id", None) or nearest_station(location.state, location.latitude,
                                                                          location.longitude)
    months = fan_months(load_drybulb(weather_id))
    cfa_ft2 = floor_area_m2 * FT2_PER_M2
    energies = [l for l in annual_loads(arguments, count, bedrooms, cfa_ft2, months, unit_type=arguments["geometry_facility_type"])
                if "annual_kwh" in l and l["end_use"] not in BUILDING_END_USES]
    installed = {"dishwasher": arguments.get("appliance_dishwasher") not in (None, "None"),
                 "clothes_washer": arguments.get("appliance_clothes_washer") not in (None, "None"),
                 "clothes_dryer": arguments.get("appliance_clothes_dryer") not in (None, "None"),
                 "cooking_range": arguments.get("appliance_cooking_range_oven") not in (None, "None"),
                 "plug_loads_other": True, "plug_loads_tv": arguments.get("misc_television") not in (None, "None"),
                 "ceiling_fan": arguments.get("ceiling_fans") not in (None, "None"), "garage": False}
    dwelling = Dwelling(count, location.state, location.latitude, location.longitude, location.utc_offset, weather_id, installed)
    generated = generate_dwelling(dwelling, unit_seed, rng_mode, type_probabilities=type_probabilities)
    channels = {"occupants": generated["occupants"]}
    loads = []
    for load in energies:
        slot = load["end_use"]
        if slot not in channels:
            if slot in EVENT_SLOTS:
                channels[slot] = generated.get(slot, np.zeros(8760))
            else:
                channels[slot] = fixed_background(slot, latitude=location.latitude)
        if "annual_therm" in load:
            total = load["annual_therm"] * WH_PER_THERM
        else:
            total = load["annual_kwh"] * 1000.0
        loads.append(Load(slot, slot, "W/dwelling", "dwelling_unit", load["fuel"], "assigned_zone", total,
                          fit_amplitude(total, "W/dwelling", channels[slot]), _heat(load)))
    channels["activity"] = np.full(8760, ACTIVITY_W_PER_PERSON)
    channels.update(thermostat_setpoints(arguments))
    controls = [{"people": {"basis": "dwelling_unit", "density": float(count)}, "quantity": "occupancy_fraction",
                 "slot": "occupants", "unit": "fraction"},
                {"quantity": "activity", "slot": "activity", "unit": "W/person"},
                {"quantity": "temperature", "slot": "heating_setpoint", "unit": "C"},
                {"quantity": "temperature", "slot": "cooling_setpoint", "unit": "C"}]
    if count > 0:
        water = (spec["hot_water_m3_per_person"] * count, generated["hot_water_fixtures"])
    else:
        water = (0.0, np.zeros(8760))
    generation = {"residents": count, "residents_mode": "resstock" if residents == "resstock" else "caller",
                  "weather_id": weather_id, "characteristics": characteristics}
    return UnitResult(channels, loads, controls, water, generation)


def hot_water_m3_per_person(caller_water: dict, reference_shape: np.ndarray, people_per_m2: float) -> float:
    """Ruling 185 (P2): the prototype's annual volume per m2 over its design occupants per m2."""
    if caller_water["density_unit"] != "m3/s/m2" or people_per_m2 <= 0:
        raise GeneratorError("unsupported_binding", "/caller_water", "Needs a per-area volume and design occupants")
    return float(caller_water["density"] * np.sum(reference_shape) * 3600 / people_per_m2)
