"""Build commercial programme recipes for a family from the frozen definitions.

Inputs:
- data/definition-releases/v0.1.1/{programs,compositions}.json (frozen definitions);
- the prototype geometry the template uses (openstudio-standards
  `<template>.prototype_inputs.json` -> `geometry_osm`, read from the locked
  raw cache data/raw/openstudio-standards).

For each template and view of the family:
- People topology for inferring hours of operation: every geometry space with a
  known positive occupancy density contributes floor area x density people on
  its programme's occupancy schedule (no zone multiplier, as OpenStudio
  `People.getNumberOfPeople(floorArea)`), in space-name order;
- one recipe per source programme (one per standards space type): known
  non-zero loads become slots and demands, occupancy adds an occupancy control
  with its density and an activity control, setpoints come from the
  programme's parameters, programme hot water adds its target temperature;
- one composition recipe per department or general mix (members by area).

Usage: python -m scripts.build_family_recipes LargeOffice Hospital ...   (write recipes)
       python -m scripts.build_family_recipes --check                    (compare with the packaged recipes)
"""
from functools import lru_cache
import json
import re
from pathlib import Path
import sys

from scripts.family_sources.osm import read_spaces

ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS = ROOT / "data/definition-releases/v0.1.1"
STANDARDS = ROOT / "data/raw/openstudio-standards"
TARGET = ROOT / "atlas_schedules/data/recipes"
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


@lru_cache(maxsize=1)
def programmes() -> list:
    return json.loads((DEFINITIONS / "programs.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def compositions() -> dict:
    return {c["id"]: c for c in json.loads((DEFINITIONS / "compositions.json").read_text(encoding="utf-8"))}


@lru_cache(maxsize=None)
def geometry_file(building_type: str, template: str) -> Path:
    folder = TEMPLATES[template][1]
    inputs = STANDARDS / "lib/openstudio-standards/standards/ashrae_90_1" / folder / "data" / f"{folder}.prototype_inputs.json"
    rows = json.loads(inputs.read_text(encoding="utf-8"))["prototype_inputs"]
    name = next(r["geometry_osm"] for r in rows if r["building_type"] == building_type)
    return STANDARDS / "data/geometry" / name


def configuration_id(building_type: str, template: str, view: str) -> str:
    return f"{SAMPLING[building_type]}__{TEMPLATES[template][0]}__{view}"


def _load(programme: dict, quantity: str):
    return next((l for l in programme["loads"] if l["quantity"] == quantity), None)


def _known_positive(load) -> bool:
    return load is not None and load["status"] == "known" and load["value"] is not None and load["value"] > 0


def source_programmes(building_type: str, template: str, view: str) -> dict:
    """Standards space type -> source programme for one template and view."""
    suffix = "_" + building_type
    return {p["name"][:-len(suffix)]: p for p in programmes()
            if p["building_type"] == building_type and p["template"] == template and p["evidence_view"] == view
            and p["detail"] == "SourcePrograms" and p["name"].endswith(suffix)}


RESIDENTIAL_SPACE_TYPES = re.compile(r"\sApartment|GuestRoom|PatRoom|ResBedroom|ResLiving")


def _residential(space) -> bool:
    """openstudio-standards space.rb `space_residential?`: by space type name."""
    return bool(space.space_type and RESIDENTIAL_SPACE_TYPES.search(space.space_type))


@lru_cache(maxsize=None)
def occupancy_carrier(building_type: str, template: str, view: str) -> tuple:
    """(occupied spaces of the dominant group, residential dominant?).

    parametric.rb model_infer_hours_of_operation_building compares design people
    (number of people x zone multiplier) in residential and non-residential
    spaces and infers hours from the larger group; each entry is
    (space name, occupancy schedule id, floor area, design people without multiplier).
    """
    by_type = source_programmes(building_type, template, view)
    groups = {True: [], False: []}
    totals = {True: 0.0, False: 0.0}
    for space in sorted(read_spaces(geometry_file(building_type, template)), key=lambda s: s.name):
        programme = by_type.get(space.standards_space_type)
        occupancy = _load(programme, "occupancy") if programme else None
        if not _known_positive(occupancy):
            continue
        count = space.floor_area_m2 * occupancy["value"]
        residential = _residential(space)
        groups[residential].append((space.name, occupancy["schedule_id"], space.floor_area_m2, count))
        totals[residential] += count * space.multiplier
    residential_dominant = totals[True] > totals[False]
    return tuple(groups[residential_dominant]), residential_dominant


def people_by_space(building_type: str, template: str, view: str) -> list:
    return list(occupancy_carrier(building_type, template, view)[0])


def people(building_type: str, template: str, view: str) -> list:
    """[(occupancy schedule id, design people)] of the dominant group, by space name."""
    return [[schedule_id, count] for _, schedule_id, _, count in people_by_space(building_type, template, view)]


def programme_recipe(programme: dict, people_list: list, configuration: str, sampling: str,
                     invert: bool = False) -> dict:
    slots, demands, controls, companions, modes = [], [], [], {}, {}
    occupancy = _load(programme, "occupancy")
    if _known_positive(occupancy):
        slots.append({"slot": "occupancy", "kind": "resident_count", "unit": "fraction", "schedule": occupancy["schedule_id"]})
        controls.append({"slot": "occupancy", "quantity": "occupancy_fraction", "unit": "fraction",
                         "people": {"basis": "floor_area", "density": occupancy["value"], "unit": "person/m2"}})
        modes["occupancy"] = "hours"
    required_services = []
    for quantity, fuel in LOAD_SLOTS.items():
        load = _load(programme, quantity)
        if not _known_positive(load):
            continue
        if quantity == "hot_water_volume" and load.get("service_id"):
            # The water belongs to a shared physical service (ADR 0027); the programme links it.
            required_services.append(load["service_id"])
            continue
        slots.append({"slot": quantity, "kind": "load", "unit": "fraction", "schedule": load["schedule_id"]})
        demands.append({"slot": quantity, "quantity": quantity, "unit": load["unit"], "value": load["value"],
                        "basis": load["basis"], "fuel": fuel, "host": "assigned_zone", "heat_fractions": None})
        modes[quantity] = "hours"
        if quantity == "hot_water_volume":
            slot = "hot_water_volume_target_temperature"
            slots.append({"slot": slot, "kind": "control", "unit": "C", "schedule": None})
            controls.append({"slot": slot, "quantity": "temperature", "unit": "C"})
            companions[slot] = {"method": "constant", "value": load["target_temperature_degC"]}
    parameters = programme.get("parameters", {})
    for slot, key in SETPOINTS:
        parameter = parameters.get(key)
        if parameter and parameter["status"] == "known":
            slots.append({"slot": slot, "kind": "control", "unit": "C", "schedule": parameter["value"]})
            controls.append({"slot": slot, "quantity": "temperature", "unit": "C"})
            modes[slot] = "tstat"
    activity = parameters.get("activity_schedule_id")
    if _known_positive(occupancy) and activity and activity["status"] == "known":
        slots.append({"slot": "activity", "kind": "control", "unit": "W/person", "schedule": activity["value"]})
        controls.append({"slot": "activity", "quantity": "activity", "unit": "W/person"})
        modes["activity"] = "hours"
    return {
        "schema_version": "2.0.0", "program_id": programme["id"], "name": programme["name"], "kind": "commercial",
        "source": {"family": programme["source_family"], "building_type": programme["building_type"],
                   "template": programme["template"], "view": programme["evidence_view"],
                   "climate": programme["climate"], "vintage": None, "source_id": programme["source_id"],
                   "definition": "data/definition-releases/v0.1.1/programs.json#" + programme["id"]},
        "slots": slots, "demands": demands, "controls": controls, "companions": companions,
        "required_services": required_services,
        "commercial": {"configuration_id": configuration, "building_type": sampling, "modes": modes, "people": people_list,
                       "invert_rule_days": invert},
    }


def composition_recipe(programme: dict) -> dict:
    composition = compositions()[programme["composition_id"]]
    return {
        "schema_version": "2.0.0", "program_id": programme["id"], "name": programme["name"], "kind": "composition",
        "source": {"family": programme["source_family"], "building_type": programme["building_type"],
                   "template": programme["template"], "view": programme["evidence_view"],
                   "definition": "data/definition-releases/v0.1.1/compositions.json#" + composition["id"]},
        "slots": [], "demands": [], "controls": [], "companions": {}, "required_services": [],
        "composition": {"composition_id": composition["id"],
                        "members": [[m["program_id"], m["represented_area_m2"]] for m in composition["members"]]},
    }


@lru_cache(maxsize=1)
def services() -> list:
    return json.loads((DEFINITIONS / "services.json").read_text(encoding="utf-8"))


# OpenStudio-standards water use equipment: constant sensible 0.2 and latent 0.05
# fraction schedules (create_water_use.rb), target temperature from the service.
WATER_FRACTIONS = {"water_sensible_fraction": 0.2, "water_latent_fraction": 0.05}
WATER_CONTROLS = [{"slot": "water_target_temperature", "quantity": "temperature", "unit": "C"},
                  {"slot": "water_sensible_fraction", "quantity": "sensible_fraction", "unit": "fraction"},
                  {"slot": "water_latent_fraction", "quantity": "latent_fraction", "unit": "fraction"}]


def service_record(service: dict, building_type: str) -> dict:
    """One shared hot-water service with a variant per view of its template."""
    from atlas_schedules.commercial.profiles import round_half_up, stored_value
    load = service["load"]
    template = service["template"]
    companions = {"water_target_temperature": {"method": "constant",
                                               "value": round_half_up(stored_value(load["target_temperature_degC"]), 5)}}
    companions.update({slot: {"method": "constant", "value": value} for slot, value in WATER_FRACTIONS.items()})
    configurations = {}
    for view in ("source", "reviewed"):
        if not source_programmes(building_type, template, view):
            continue
        configurations[configuration_id(building_type, template, view)] = {
            "schedule": load["schedule_id"], "building_type": SAMPLING[building_type],
            "people": people(building_type, template, view), "companions": companions,
            "invert_rule_days": occupancy_carrier(building_type, template, view)[1]}
    return {
        "schema_version": "2.0.0", "service_id": service["id"], "kind": "physical_service",
        "source": {"definition": "data/definition-releases/v0.1.1/services.json#" + service["id"]},
        "demand": {"quantity": load["quantity"], "unit": load["unit"], "value": load["value"], "basis": load["basis"],
                   "fuel": "water", "host": "building_service"},
        "controls": WATER_CONTROLS, "configurations": configurations,
    }


def build_services(building_type: str) -> list:
    """Shared water services with a known rate and schedule (unknown schedules stay unknown, not generated)."""
    return [service_record(s, building_type) for s in services()
            if s["building_type"] == building_type and s["template"] in TEMPLATES and s["load"]["value"]
            and s["load"]["schedule_id"]]


def build_family(building_type: str) -> list:
    recipes = []
    sampling = SAMPLING[building_type]
    for template in TEMPLATES:
        for view in ("source", "reviewed"):
            selected = [p for p in programmes() if p["building_type"] == building_type
                        and p["template"] == template and p["evidence_view"] == view]
            if not selected:
                continue
            people_list = people(building_type, template, view)
            invert = occupancy_carrier(building_type, template, view)[1]
            configuration = configuration_id(building_type, template, view)
            for programme in selected:
                if programme["detail"] == "SourcePrograms":
                    recipes.append(programme_recipe(programme, people_list, configuration, sampling, invert))
                elif programme.get("composition_id"):
                    recipes.append(composition_recipe(programme))
    return recipes


def _summary(recipe: dict) -> dict:
    """What must agree with a migrated recipe."""
    if recipe["kind"] == "composition":
        return {"kind": "composition", "members": recipe["composition"]["members"]}
    summary = {"kind": recipe["kind"], "slots": [(s["slot"], s["kind"], s["schedule"]) for s in recipe["slots"]],
               "demands": [(d["slot"], d["unit"], d["value"]) for d in recipe["demands"]],
               "required_services": recipe.get("required_services", [])}
    if recipe["kind"] == "commercial":
        totals = {}
        people_list = recipe["commercial"].get("people") or _configuration(recipe["commercial"]["configuration_id"])["people"]
        for schedule_id, count in people_list:
            totals[schedule_id] = totals.get(schedule_id, 0) + count
        summary["people"] = {k: round(v, 9) for k, v in totals.items()}
        summary["modes"] = recipe["commercial"]["modes"]
        summary["configuration"] = recipe["commercial"]["configuration_id"]
    return summary


def _configuration(configuration_id: str) -> dict:
    return json.loads((TARGET.parent / "configurations" / f"{configuration_id}.json").read_text(encoding="utf-8"))


def _service_summary(record: dict) -> dict:
    variants = {}
    for key, variant in record["configurations"].items():
        building = variant if "people" in variant else _configuration(key)
        totals = {}
        for schedule_id, count in building["people"]:
            totals[schedule_id] = round(totals.get(schedule_id, 0) + count, 9)
        variants[key] = (variant["schedule"], building["building_type"], totals,
                         {k: v["value"] for k, v in variant["companions"].items()})
    return {"demand": record["demand"], "variants": variants}


def check_services(building_types) -> int:
    folder = TARGET.parent / "services"
    total = 0
    for building_type in building_types:
        same = differ = missing = 0
        for record in build_services(building_type):
            path = folder / f"{record['service_id']}.json"
            if not path.exists():
                missing += 1
                continue
            a = _service_summary(record)
            b = _service_summary(json.loads(path.read_text(encoding="utf-8")))
            if a == b:
                same += 1
            else:
                differ += 1
                if differ <= 2:
                    print("  ", record["service_id"], {k: (a[k], b[k]) for k in a if a[k] != b[k]})
        print(f"{building_type} services: identical {same}, different {differ}, not migrated {missing}")
        total += differ
    return total


def check(building_types) -> int:
    total = 0
    for building_type in building_types:
        built = {r["program_id"]: r for r in build_family(building_type)}
        same = differ = missing = 0
        for program_id, recipe in built.items():
            path = TARGET / f"{program_id}.json"
            if not path.exists():
                missing += 1
                continue
            migrated = json.loads(path.read_text(encoding="utf-8"))
            a, b = _summary(recipe), _summary(migrated)
            if a == b:
                same += 1
            else:
                differ += 1
                if differ <= 3:
                    for key in a:
                        if a.get(key) != b.get(key):
                            print(f"  {building_type} {recipe['name']} {key}: built {str(a.get(key))[:160]} | migrated {str(b.get(key))[:160]}")
        print(f"{building_type}: built {len(built)}, identical {same}, different {differ}, not migrated {missing}")
        total += differ
    return total


def main() -> None:
    if sys.argv[1:2] == ["--check"]:
        # Offices and Warehouse stay migrated from the legacy package (different People carrier).
        families = sys.argv[2:] or [bt for bt in SAMPLING if bt not in ("MediumOffice", "SmallOffice", "Warehouse")]
        different = check(families) + check_services(families)
        raise SystemExit(1 if different else 0)
    table_path = TARGET.parent / "schedules.json"
    table = json.loads(table_path.read_text(encoding="utf-8"))
    definitions = {s["id"]: s for s in json.loads((DEFINITIONS / "schedules.json").read_text(encoding="utf-8"))}

    def keep(schedule_id):
        if schedule_id and schedule_id not in table:
            table[schedule_id] = {"rules": [{k: r[k] for k in ("day_types", "start_date", "end_date", "values")}
                                            for r in definitions[schedule_id]["rules"]]}

    configurations = TARGET.parent / "configurations"
    for building_type in sys.argv[1:]:
        recipes = build_family(building_type)
        for recipe in recipes:
            for slot in recipe["slots"]:
                keep(slot["schedule"])
            spec = recipe.get("commercial")
            if spec:
                for schedule_id, _ in spec["people"]:
                    keep(schedule_id)
                record = {"configuration_id": spec["configuration_id"], "building_type": spec["building_type"],
                          "people": spec["people"], "invert_rule_days": spec["invert_rule_days"]}
                (configurations / f"{spec['configuration_id']}.json").write_text(
                    json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
                recipe["commercial"] = {"configuration_id": spec["configuration_id"], "modes": spec["modes"]}
            path = TARGET / f"{recipe['program_id']}.json"
            path.write_text(json.dumps(recipe, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        records = build_services(building_type)
        for record in records:
            for variant in record["configurations"].values():
                keep(variant["schedule"])
                for key in ("people", "building_type", "invert_rule_days"):
                    variant.pop(key)
            path = TARGET.parent / "services" / f"{record['service_id']}.json"
            path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(building_type, len(recipes), "recipes", len(records), "services")
    table_path.write_text(json.dumps(table, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(table), "rule sets")


if __name__ == "__main__":
    main()
