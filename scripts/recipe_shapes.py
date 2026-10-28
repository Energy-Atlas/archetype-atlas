"""Commercial generator recipe shapes (schema 2.0.0), shared by the recipe builders.

Moved from scripts/build_family_recipes.py, which built the 90.1 recipes from the frozen
definitions and left the tree in stage X1.3 (ADR 0046 section 7; readable at the tag
`frozen-data-2026-10-27`). The packaged 90.1 recipes stay as it wrote them;
scripts/build_reference_recipes.py builds the DOE Ref recipes with these rules:
- one recipe per source programme: known non-zero loads become slots and demands,
  occupancy adds an occupancy control with its density and an activity control,
  setpoints come from the programme's parameters, programme hot water adds its target
  temperature, and hot water of a shared service becomes a required service;
- residential space types as openstudio-standards names them, for the dominant group.
"""
import re

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


def _load(programme: dict, quantity: str):
    return next((l for l in programme["loads"] if l["quantity"] == quantity), None)


def _known_positive(load) -> bool:
    return load is not None and load["status"] == "known" and load["value"] is not None and load["value"] > 0


RESIDENTIAL_SPACE_TYPES = re.compile(r"\sApartment|GuestRoom|PatRoom|ResBedroom|ResLiving")


def _residential(space) -> bool:
    """openstudio-standards space.rb `space_residential?`: by space type name."""
    return bool(space.space_type and RESIDENTIAL_SPACE_TYPES.search(space.space_type))


def heat_fractions(load: dict) -> dict | None:
    """The load's thermal effects (e.g. radiant, latent, lost) when every one is
    known in the definitions; otherwise null, so unknowns stay explicit."""
    effects = load.get("thermal_effects") or {}
    if not effects or any(e["status"] != "known" for e in effects.values()):
        return None
    return {name: effects[name]["value"] for name in sorted(effects)}


def programme_recipe(programme: dict, people_list: list, configuration: str, sampling: str,
                     invert: bool, definition: str) -> dict:
    """The commercial recipe of one source programme; `definition` locates its record."""
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
                        "basis": load["basis"], "fuel": fuel, "host": "assigned_zone",
                        "heat_fractions": heat_fractions(load)})
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
                   "definition": definition},
        "slots": slots, "demands": demands, "controls": controls, "companions": companions,
        "required_services": required_services,
        "commercial": {"configuration_id": configuration, "building_type": sampling, "modes": modes, "people": people_list,
                       "invert_rule_days": invert},
    }


# OpenStudio-standards water use equipment: constant sensible 0.2 and latent 0.05
# fraction schedules (create_water_use.rb), target temperature from the service.
WATER_FRACTIONS = {"water_sensible_fraction": 0.2, "water_latent_fraction": 0.05}
WATER_CONTROLS = [{"slot": "water_target_temperature", "quantity": "temperature", "unit": "C"},
                  {"slot": "water_sensible_fraction", "quantity": "sensible_fraction", "unit": "fraction"},
                  {"slot": "water_latent_fraction", "quantity": "latent_fraction", "unit": "fraction"}]
