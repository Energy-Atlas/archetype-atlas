"""Programme recipes: assemble them from the release and turn one programme instance into
channels and bindings.

A recipe is assembled from a release program, its generation block and its folder's tables
(`assemble`, ADR 0049). It lists the programme's slots (loads, controls, resident counts),
its demands (annual magnitude per basis unit), its companions and, per kind, the kernel inputs:
- "commercial": ComStock transform (slot modes and a configuration id; the folder's
  configuration holds the sampling building type, People per space and rule-day inversion);
- "residential": ResStock dwelling (residents, location, weather, installed
  appliances, thermostat arguments);
- "fixed": source rule sets used as they are.

Annual targets come from the original source shape before any transform, so a
transform moves energy in time without changing the annual total.
"""
from collections.abc import Mapping
from functools import lru_cache
import json
from pathlib import Path

import numpy as np

from .budgets import annual_target
from .calendar import evaluate_rules
from .commercial.profiles import round_half_up, stored_value
from .commercial.transform import Slot, transform
from .companions import companion_channels
from .errors import GeneratorError
from .release import current
from .residential.generate import Dwelling, generate_dwelling
from .residential.occupancy import type_probabilities
from .residential.tables import load_tables

DATA = Path(__file__).resolve().parent / "data"


class Schedules(Mapping):
    """The release's schedules by ID, read per folder as they are asked for."""

    def __init__(self, release):
        self.release = release

    def __getitem__(self, schedule_id):
        try:
            return self.release.schedules(self.release.folder_of(schedule_id))[schedule_id]
        except (GeneratorError, ValueError, KeyError):
            raise KeyError(schedule_id) from None

    def __iter__(self):
        for folder in self.release.generation_folders():
            yield from self.release.schedules(folder)

    def __len__(self):
        return sum(1 for _ in self)


def schedules() -> Schedules:
    return Schedules(current())


def load_configuration(configuration_id: str) -> dict:
    """A commercial building configuration: sampling building type, People per space
    (occupancy schedule id, design people) and rule-day inversion."""
    return _configuration(current(), configuration_id)


@lru_cache(maxsize=None)
def _configuration(release, configuration_id: str) -> dict:
    return assemble_configuration(release, configuration_id)


def configuration_people(configuration: dict) -> list:
    table = schedules()
    return [(schedule_id, table[schedule_id], count) for schedule_id, count in configuration["people"]]


def load_recipe(program_id: str, values: str | None = None) -> dict:
    """The recipe of a release program in one view (source or filled; default per its block)."""
    return _recipe(current(), program_id, values)


@lru_cache(maxsize=None)
def _recipe(release, program_id: str, values: str | None) -> dict:
    return assemble(release, program_id, values)


def catalogue() -> list:
    """(program ID, view, method) of every program view the release can generate, in folder order."""
    release = current()
    return [(rid, view, block["method"]) for folder in release.generation_folders()
            for rid, block in release.generation(folder).get("programs", {}).items() for view in block["views"]]


def service_catalogue() -> list:
    """(service ID, configuration ID) of every shared service and configuration it runs under."""
    release = current()
    return [(sid, cid) for folder in release.generation_folders()
            for sid, block in release.generation(folder).get("services", {}).items() for cid in block["configurations"]]


def load_service(service_id: str) -> dict:
    return _service(current(), service_id)


@lru_cache(maxsize=None)
def _service(release, service_id: str) -> dict:
    return assemble_service(release, service_id)


# ------------------------------------------------------------------- assembly
# A recipe is assembled from the release (ADR 0049): the program record, its generation
# block, the folder's schedules, services and configurations. The block holds only what
# the record does not state: per view, the commercial configuration, the ResStock unit
# characteristics, or a ResStock dwelling's executed annual inputs.
VIEWS = ("source", "filled")
SAMPLING = {
    "MediumOffice": "medium_office", "SmallOffice": "small_office", "Warehouse": "warehouse",
    "RetailStandalone": "retail", "FullServiceRestaurant": "full_service_restaurant",
    "QuickServiceRestaurant": "quick_service_restaurant", "RetailStripmall": "strip_mall",
    "LargeOffice": "large_office", "LargeHotel": "large_hotel", "SmallHotel": "small_hotel",
    "Hospital": "hospital", "Outpatient": "outpatient", "PrimarySchool": "primary_school",
    "SecondarySchool": "secondary_school", "SuperMarket": "supermarket",
}
TEMPLATES = {"90.1-2007": ("90_1_2007", "ashrae_90_1_2007"), "90.1-2013": ("90_1_2013", "ashrae_90_1_2013"),
             "90.1-2019": ("90_1_2019", "ashrae_90_1_2019"), "DOE Ref Pre-1980": ("doe_ref_pre_1980", "doe_ref_pre_1980"),
             "DOE Ref 1980-2004": ("doe_ref_1980_2004", "doe_ref_1980_2004")}
LOAD_SLOTS = {"lighting": "electricity", "electric_equipment": "electricity", "gas_equipment": "natural gas",
              "hot_water_volume": "water"}
SETPOINTS = (("heating_setpoint", "heating_setpoint_schedule_id"), ("cooling_setpoint", "cooling_setpoint_schedule_id"))
# OpenStudio-standards water use equipment: constant sensible 0.2 and latent 0.05
# fraction schedules (create_water_use.rb), target temperature from the service.
WATER_FRACTIONS = {"water_sensible_fraction": 0.2, "water_latent_fraction": 0.05}
WATER_CONTROLS = [{"slot": "water_target_temperature", "quantity": "temperature", "unit": "C"},
                  {"slot": "water_sensible_fraction", "quantity": "sensible_fraction", "unit": "fraction"},
                  {"slot": "water_latent_fraction", "quantity": "latent_fraction", "unit": "fraction"}]
DWELLING_FIELDS = ("slots", "demands", "controls", "companions", "required_services", "dwelling", "thermostat")


def view_record(record: dict, view: str) -> dict:
    """The record as one export reads it: `source` keeps actual values only, `filled` applies every
    filling (ADR 0036 section 4: a filling's `set` replaces the field it fills)."""
    def walk(value):
        if isinstance(value, dict):
            if view == "filled" and "filling" in value:
                kept = {k: v for k, v in value.items() if k != "filling"}
                return walk({**kept, **value["filling"]["set"]})
            return {k: walk(v) for k, v in value.items() if k != "filling"}
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value
    return walk(record)


def default_values(block: dict) -> str:
    """Filled where the block has a filled view, else source (ADR 0049 section 4)."""
    return "filled" if "filled" in block["views"] else "source"


def load_of(record: dict, quantity: str):
    return next((l for l in record["loads"] if l["quantity"] == quantity), None)


def known_positive(load) -> bool:
    return load is not None and load["status"] == "known" and load["value"] is not None and load["value"] > 0


def heat_fractions(load: dict) -> dict | None:
    """The load's thermal effects (e.g. radiant, latent, lost) when every one is known; otherwise
    null, so unknowns stay explicit. Descriptive text in water effects is not a fraction."""
    effects = {k: v for k, v in (load.get("thermal_effects") or {}).items() if isinstance(v, dict)}
    if not effects or any(e["status"] != "known" for e in effects.values()):
        return None
    return {name: effects[name]["value"] for name in sorted(effects)}


def water_fractions(effects: dict) -> dict:
    """Sensible and latent fractions of a water draw: the release's, else openstudio-standards' constants."""
    return {slot: (effects.get(key) or {}).get("value", default)
            for (slot, default), key in zip(WATER_FRACTIONS.items(), ("sensible_fraction", "latent_fraction"))}


def commercial_body(record: dict) -> dict:
    """ComStock slots of one source program: known non-zero loads become slots and demands, occupancy
    adds an occupancy control with its density and an activity control, setpoints come from the
    program's parameters, program hot water adds its target temperature, and hot water of a shared
    service becomes a required service. Every slot is transformed by hours, setpoints by thermostat."""
    slots, demands, controls, companions, modes = [], [], [], {}, {}
    occupancy = load_of(record, "occupancy")
    if known_positive(occupancy):
        slots.append({"slot": "occupancy", "kind": "resident_count", "unit": "fraction", "schedule": occupancy["schedule_id"]})
        controls.append({"slot": "occupancy", "quantity": "occupancy_fraction", "unit": "fraction",
                         "people": {"basis": "floor_area", "density": occupancy["value"], "unit": "person/m2"}})
        modes["occupancy"] = "hours"
    required = []
    for quantity, fuel in LOAD_SLOTS.items():
        load = load_of(record, quantity)
        if not known_positive(load):
            continue
        if quantity == "hot_water_volume" and load.get("service_id"):
            required.append(load["service_id"])   # the water of a shared physical service (ADR 0027)
            continue
        slots.append({"slot": quantity, "kind": "load", "unit": "fraction", "schedule": load["schedule_id"]})
        demands.append({"slot": quantity, "quantity": quantity, "unit": load["unit"], "value": load["value"],
                        "basis": load["basis"], "fuel": fuel, "host": "assigned_zone", "heat_fractions": heat_fractions(load)})
        modes[quantity] = "hours"
        if quantity == "hot_water_volume":
            slot = "hot_water_volume_target_temperature"
            slots.append({"slot": slot, "kind": "control", "unit": "C", "schedule": None})
            controls.append({"slot": slot, "quantity": "temperature", "unit": "C"})
            companions[slot] = {"method": "constant", "value": load["target_temperature_degC"]}
    parameters = record.get("parameters", {})
    for slot, key in SETPOINTS:
        parameter = parameters.get(key)
        if parameter and parameter["status"] == "known":
            slots.append({"slot": slot, "kind": "control", "unit": "C", "schedule": parameter["value"]})
            controls.append({"slot": slot, "quantity": "temperature", "unit": "C"})
            modes[slot] = "tstat"
    activity = parameters.get("activity_schedule_id")
    if known_positive(occupancy) and activity and activity["status"] == "known":
        slots.append({"slot": "activity", "kind": "control", "unit": "W/person", "schedule": activity["value"]})
        controls.append({"slot": "activity", "quantity": "activity", "unit": "W/person"})
        modes["activity"] = "hours"
    return {"slots": slots, "demands": demands, "controls": controls, "companions": companions,
            "required_services": required, "modes": modes}


def fixed_body(record: dict) -> dict:
    """Source rule sets used as they are (apartment-building corridors and offices): occupancy,
    interior lighting and equipment, activity and setpoints, each on its source schedule."""
    slots, demands, controls, companions = [], [], [], {}
    occupancy = load_of(record, "occupancy")
    if known_positive(occupancy):
        slots.append({"slot": "occupants", "kind": "control", "unit": "fraction", "schedule": occupancy["schedule_id"]})
        controls.append({"slot": "occupants", "quantity": "occupancy_fraction", "unit": "fraction",
                         "people": {"basis": "floor_area", "density": occupancy["value"], "unit": "person/m2"}})
    for quantity, slot in (("lighting", "lighting_interior"), ("electric_equipment", "electric_equipment")):
        load = load_of(record, quantity)
        if known_positive(load):
            slots.append({"slot": slot, "kind": "load", "unit": "fraction", "schedule": load["schedule_id"]})
            demands.append({"slot": slot, "quantity": quantity, "unit": load["unit"], "value": load["value"],
                            "basis": load["basis"], "fuel": LOAD_SLOTS[quantity], "host": "assigned_zone",
                            "heat_fractions": heat_fractions(load)})
    parameters = record["parameters"]
    activity = parameters.get("activity_schedule_id") or {}
    named = [("activity", activity)] if known_positive(occupancy) and activity.get("status") == "known" else []
    named += [(slot, parameters.get(key) or {}) for slot, key in SETPOINTS]
    for slot, parameter in named:
        if parameter.get("status") != "known":
            continue
        unit = "W/person" if slot == "activity" else "C"
        slots.append({"slot": slot, "kind": "control", "unit": unit, "schedule": parameter["value"]})
        controls.append({"slot": slot, "quantity": "activity" if slot == "activity" else "temperature", "unit": unit})
        companions[slot] = {"method": "source_rules", "schedule": parameter["value"]}
    if known_positive(load_of(record, "hot_water_volume")):
        raise GeneratorError("unsupported_binding", "/program_id",
                             f"{record['id']}: hot water outside an apartment has no fixed-recipe form")
    return {"slots": slots, "demands": demands, "controls": controls, "companions": companions, "required_services": []}


def caller_water(record: dict, services: dict) -> dict | None:
    """An apartment's hot water: the building's water service, its per-area volume on its schedule."""
    water = load_of(record, "hot_water_volume")
    if not known_positive(water):
        return None
    load = services[water["service_id"]]["load"]
    fractions = water_fractions(load.get("thermal_effects") or {})
    return {"service_id": water["service_id"], "density": water["value"], "density_unit": water["unit"],
            "schedule": water["schedule_id"],
            "controls": {"water_target_temperature": ["temperature", "C", load["target_temperature_degC"]],
                         "water_sensible_fraction": ["sensible_fraction", "fraction", fractions["water_sensible_fraction"]],
                         "water_latent_fraction": ["latent_fraction", "fraction", fractions["water_latent_fraction"]]}}


def member_values(release, program_id: str, view: str) -> str:
    """A mix member takes its parent's view where it has one, else its source values."""
    block = release.program(program_id)[1].get("generation")
    return view if block and view in block["views"] else "source"


def assemble(release, program_id: str, values: str | None = None) -> dict:
    """The recipe of one release program in one view (`values`: source or filled; default per block)."""
    folder, record = release.program(program_id)
    block = record.get("generation")
    if block is None:
        raise GeneratorError("unsupported_input", "/program_id",
                             f"{program_id} has no generation block in release {release.version}")
    view = values or default_values(block)
    if view not in block["views"]:
        raise GeneratorError("unsupported_input", "/values", f"{program_id} has no {view} view; it has {sorted(block['views'])}")
    parameters = block["views"][view]
    method = block["method"]
    data = view_record(record, view)
    recipe = {"schema_version": "2.0.0", "program_id": program_id, "values": view, "name": record["name"],
              "source": {"release": release.version, "program": release.program_paths[program_id],
                         "generation": f"{folder}/generation.json#/programs/{program_id}",
                         "family": record.get("source_family"), "template": record.get("template"),
                         "building_type": record.get("building_type")}}
    if method == "comstock_hours":
        body = commercial_body(data)
        modes = body.pop("modes")
        recipe.update(kind="commercial", **body,
                      commercial={"configuration_id": parameters["configuration_id"], "modes": modes})
    elif method == "fixed":
        recipe.update(kind="fixed", **fixed_body(data))
    elif method == "composition":
        members = data["composition"]["members"]
        recipe.update(kind="composition", slots=[], demands=[], controls=[], companions={}, required_services=[],
                      composition={"composition_id": program_id,
                                   "members": [[m["program_id"], m["represented_area_m2"]] for m in members],
                                   "member_values": [member_values(release, m["program_id"], view) for m in members]})
    elif method == "resstock_unit":
        water = caller_water(data, release.services(folder))
        recipe.update(kind="apartment_unit", required_services=[], resstock_unit=parameters["resstock_unit"],
                      **({"caller_water": water} if water else {}))
    elif method == "resstock_dwelling":
        recipe.update(kind="residential", **{k: parameters[k] for k in DWELLING_FIELDS})
    else:
        raise GeneratorError("unsupported_input", "/program_id", f"Unknown generation method {method!r}")
    return recipe


def assemble_service(release, service_id: str) -> dict:
    """A shared hot-water service: the release service's volume and schedule under each configuration
    its block lists, with the target temperature and the draw's sensible and latent fractions."""
    folder = release.folder_of(service_id)
    service = release.services(folder).get(service_id)
    block = release.generation(folder).get("services", {}).get(service_id)
    if service is None or block is None:
        raise GeneratorError("unsupported_binding", "/service_id", f"No shared service {service_id!r}")
    load = service["load"]
    temperature = round_half_up(stored_value(load["target_temperature_degC"]), 5)
    companions = {"water_target_temperature": {"method": "constant", "value": temperature},
                  **{slot: {"method": "constant", "value": value}
                     for slot, value in water_fractions(load.get("thermal_effects") or {}).items()}}
    return {"schema_version": "2.0.0", "service_id": service_id, "kind": "physical_service",
            "source": {"release": release.version, "service": f"{folder}/services.json#{service_id}",
                       "generation": f"{folder}/generation.json#/services/{service_id}"},
            "demand": {"quantity": load["quantity"], "unit": load["unit"], "value": load["value"], "basis": load["basis"],
                       "fuel": "water", "host": "building_service"},
            "controls": WATER_CONTROLS,
            "configurations": {cid: {"schedule": load["schedule_id"], "companions": companions}
                               for cid in block["configurations"]}}


def assemble_configuration(release, configuration_id: str) -> dict:
    found = release.configurations.get(configuration_id)
    if found is None:
        raise GeneratorError("unsupported_binding", "/configuration_id", f"No configuration {configuration_id!r}")
    return {"configuration_id": configuration_id, **found[1]}


def required_services(recipe: dict) -> list:
    """Shared services an instance must link: its own, or for a composition parent
    the ordered union of its members' (members are generated without links)."""
    if recipe["kind"] != "composition":
        return list(recipe["required_services"])
    services = []
    composition = recipe["composition"]
    for (program_id, _), values in zip(composition["members"], composition["member_values"]):
        services.extend(s for s in load_recipe(program_id, values)["required_services"] if s not in services)
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
