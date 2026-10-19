"""Programme recipes: load them and turn one programme instance into channels and bindings.

A recipe (data/recipes/<program_id>.json) lists the programme's slots (loads,
controls, resident counts), its demands (annual magnitude per basis unit), its
companions and, per kind, the kernel inputs:
- "commercial": ComStock transform (slot modes and a configuration id; the
  configuration in data/configurations/ holds the sampling building type,
  People per space and rule-day inversion);
- "residential": ResStock dwelling (residents, location, weather, installed
  appliances, thermostat arguments);
- "fixed": source rule sets used as they are.

Annual targets come from the original source shape before any transform, so a
transform moves energy in time without changing the annual total.
"""
from functools import lru_cache
import json
from pathlib import Path

import numpy as np

from .budgets import annual_target
from .calendar import evaluate_rules
from .commercial.transform import Slot, transform
from .companions import companion_channels
from .errors import GeneratorError
from .residential.generate import Dwelling, generate_dwelling
from .residential.occupancy import type_probabilities
from .residential.tables import load_tables

DATA = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def schedules() -> dict:
    return json.loads((DATA / "schedules.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_configuration(configuration_id: str) -> dict:
    """A commercial building configuration: sampling building type, People per space
    (occupancy Ruleset id, design people) and rule-day inversion."""
    path = DATA / "configurations" / f"{configuration_id}.json"
    if not path.exists():
        raise GeneratorError("unsupported_binding", "/configuration_id", f"No configuration {configuration_id!r}")
    return json.loads(path.read_text(encoding="utf-8"))


def configuration_people(configuration: dict) -> list:
    table = schedules()
    return [(schedule_id, table[schedule_id], count) for schedule_id, count in configuration["people"]]


@lru_cache(maxsize=None)
def load_recipe(program_id: str) -> dict:
    path = DATA / "recipes" / f"{program_id}.json"
    if not path.exists():
        raise GeneratorError("unsupported_binding", "/program_id", f"No recipe for {program_id!r}")
    return json.loads(path.read_text(encoding="utf-8"))


def required_services(recipe: dict) -> list:
    """Shared services an instance must link: its own, or for a composition parent
    the ordered union of its members' (members are generated without links)."""
    if recipe["kind"] != "composition":
        return list(recipe["required_services"])
    services = []
    for program_id, _ in recipe["composition"]["members"]:
        services.extend(s for s in load_recipe(program_id)["required_services"] if s not in services)
    return services


def _reference_shapes(recipe: dict) -> dict:
    table = schedules()
    return {s["slot"]: evaluate_rules(table[s["schedule"]])[0] for s in recipe["slots"] if s["schedule"]}


def annual_targets(recipe: dict) -> list:
    """Annual total per demand, in demand order (a slot may carry two fuels),
    from direct evidence or magnitude x reference shape."""
    shapes = _reference_shapes(recipe)
    targets = []
    for demand in recipe["demands"]:
        if "annual_total" in demand:
            targets.append(demand["annual_total"])
        else:
            targets.append(annual_target(demand["value"], demand["unit"], shapes[demand["slot"]]))
    return targets


def _commercial_channels(recipe: dict, operating: dict, flat_days: str) -> dict:
    table = schedules()
    spec = recipe["commercial"]
    slots = {s["slot"]: Slot(table[s["schedule"]], spec["modes"][s["slot"]])
             for s in recipe["slots"] if s["slot"] in spec["modes"]}
    configuration = load_configuration(spec["configuration_id"])
    return transform(slots, configuration_people(configuration), operating,
                     invert_rule_days=configuration["invert_rule_days"], flat_days=flat_days)


@lru_cache(maxsize=1)
def reference_locations() -> dict:
    """DOE Commercial Reference locations (NREL/TP-5500-46861 Table 2) bound to TMY3 stations."""
    table = json.loads((DATA / "weather" / "reference-locations.json").read_text(encoding="utf-8"))
    return {row["climate_case"]: row for row in table["locations"]}


def dwelling_for(recipe: dict, reference_location: str | None = None) -> Dwelling:
    d = dict(recipe["dwelling"])
    if reference_location:
        where = reference_locations()[reference_location]
        d.update(state=where["state"], latitude=where["latitude"], longitude=where["longitude"],
                 utc_offset=where["utc_offset"], weather_id=where["weather_id"])
    return Dwelling(d["residents"], d["state"], d["latitude"], d["longitude"], d["utc_offset"],
                    d["weather_id"], d["installed"])


def occupant_type_probabilities(state: str, occupancy: tuple | None) -> list:
    """The dwelling's occupant-type shares: the state mix, or ResStock's national shares."""
    mix, window = occupancy or ("national", None)
    national = list(load_tables().occupant_type_probabilities)
    return national if mix == "national" else type_probabilities(state, window, national)


def _residential_channels(recipe: dict, unit_seed: int, rng_mode: str, reference_location: str | None = None,
                          occupancy: tuple | None = None) -> dict:
    dwelling = dwelling_for(recipe, reference_location)
    return generate_dwelling(dwelling, unit_seed, rng_mode,
                             type_probabilities=occupant_type_probabilities(dwelling.state, occupancy))


def _fixed_channels(recipe: dict) -> dict:
    return _reference_shapes(recipe)


def instance_channels(recipe: dict, *, operating: dict | None = None, unit_seed: int | None = None,
                      rng_mode: str = "pcg64", reference_location: str | None = None,
                      flat_days: str = "documented", occupancy: tuple | None = None) -> dict:
    """Hourly channels for every slot of the recipe; occupancy = (mix, window) for residential."""
    kind = recipe["kind"]
    if kind == "commercial":
        channels = _commercial_channels(recipe, operating, flat_days)
    elif kind == "residential":
        channels = _residential_channels(recipe, unit_seed, rng_mode, reference_location, occupancy)
    elif kind == "fixed":
        channels = _fixed_channels(recipe)
    else:
        raise GeneratorError("unsupported_binding", "/program_id", f"Recipe kind {kind!r} is generated elsewhere")
    latitude = dwelling_for(recipe, reference_location).latitude if kind == "residential" else None
    channels.update(companion_channels(recipe["companions"], schedules(), recipe.get("thermostat"),
                                       latitude=latitude))
    selected = {}
    for slot in recipe["slots"]:
        name = slot["slot"]
        if name not in channels:
            raise GeneratorError("missing_channel", f"/slots/{name}", "The recipe selects a slot nothing generated")
        selected[name] = np.asarray(channels[name], dtype=float)
    for name in recipe["companions"]:
        if name not in selected and name in channels:
            selected[name] = np.asarray(channels[name], dtype=float)
    return selected
