"""Convert compiled v0.8.0 programme recipes into compact v2 recipes.

Input: build/task-10/v080-package/atlas_schedules/data/program/*.json, unpacked
from data/generator-releases/v0.8.0/generator.zip (sha256 bb1eb96b...). Each
legacy recipe already resolved its frozen definition record
(data/definition-releases/v0.1.1) into slots, demands, controls, rule sets and
kernel context; this keeps the fields that change output, plus a compact
source block pointing back to the definition record.

Output: atlas_schedules_v2/data/recipes/<program_id>.json and
atlas_schedules_v2/data/schedules.json (rule sets by id).

Usage: python -m scripts.migrate.recipes
"""
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "build/task-10/v080-package/atlas_schedules/data/program"
TARGET = ROOT / "atlas_schedules_v2/data"
RULE_FIELDS = ("day_types", "start_date", "end_date", "values")
KINDS = {
    "prototype_budget_preserving_commercial_hybrid": "commercial",
    "atlas_frozen_definition_comstock_v33_standards086_hybrid": "commercial",
    "resstock_time_allocation_with_selected_source_companions": "residential",
    "source_fixed_apartment_programme": "fixed",
    "unit_occupancy_interior_lighting": "apartment_unit",
    "actual_generated_source_constituents": "composition",
}
DWELLING_FIELDS = {"residents": "residents", "state": "state", "latitude": "latitude", "longitude": "longitude",
                   "time_zone_utc_offset": "utc_offset", "weather_id": "weather_id", "installed": "installed"}


def _rules(schedule: dict) -> dict:
    return {"rules": [{k: rule[k] for k in RULE_FIELDS} for rule in schedule["rules"]]}


def _definition_locator(provenance: dict) -> str:
    if "source_locator" in provenance:
        return provenance["source_locator"]
    source = provenance["source_object"]
    return f"{source['path']}#{source['locator']}"


def _source(record: dict) -> dict:
    resolved = record["recipe"]["resolved"]
    source = resolved["source"]
    return {
        "family": resolved["source_family"],
        "building_type": source.get("building_type"),
        "template": source.get("template"),
        "view": source.get("evidence_view"),
        "climate": source.get("climate"),
        "vintage": source.get("vintage"),
        "source_id": source.get("source_id"),
        "definition": _definition_locator(record["provenance"]),
        "migrated_from": "v0.8.0 compiled recipe",
    }


def _heat_fractions(demand: dict, resolved: dict):
    """Radiant/latent/lost fractions: from the demand's original value, else from
    the definition aggregation component for the same demand (legacy generator)."""
    original = demand["evidence"].get("original_value")
    if isinstance(original, dict) and "heat_fractions" in original:
        return original["heat_fractions"]
    for receipt in resolved["evidence"]:
        for group in receipt.get("aggregation", {}).get("groups", []):
            for component in group.get("components", []):
                load = component["load"]
                if (load["demand_id"] == demand["demand_id"] or
                        (load.get("end_use") == demand["quantity"] and load.get("fuel") == demand["fuel"]
                         and load.get("host") == demand["host"])):
                    return load.get("heat_fractions")
    return None


def _demand(demand: dict, resolved: dict) -> dict:
    compact = {k: demand[k] for k in ("slot", "quantity", "unit", "value", "basis", "fuel", "host")}
    if demand.get("annual_target"):
        compact["annual_total"] = demand["annual_target"]["total"]
        compact["annual_unit"] = demand["annual_target"]["unit"]
    compact["heat_fractions"] = _heat_fractions(demand, resolved)
    return compact


def _control(control: dict) -> dict:
    compact = {k: control[k] for k in ("slot", "quantity", "unit")}
    if control["quantity"] == "occupancy_fraction":
        evidence = control["evidence"]
        if "residents" in evidence:
            compact["people"] = {"basis": "dwelling_unit", "density": evidence["residents"]}
        elif evidence.get("nominal_density") is not None:
            density = evidence["nominal_density"]
            compact["people"] = {"basis": density["basis"], "density": density["value"], "unit": density["unit"]}
    return compact


def _companions(rules: dict, schedules: dict) -> dict:
    compact = {}
    for slot, rule in rules.items():
        method = rule["method"]
        if method == "source_rules":
            schedule_id = rule["source"]["id"]
            schedules.setdefault(schedule_id, _rules(rule["source"]))
            compact[slot] = {"method": method, "schedule": schedule_id}
        elif method == "constant":
            compact[slot] = {"method": method, "value": rule["value"]}
        elif method == "fixed_background":
            compact[slot] = {"method": method, "source_slot": rule["source_slot"]}
        elif method == "translated_thermostat":
            compact[slot] = {"method": method}
        elif method == "native_constant_ruleset":
            compact[slot] = {"method": "constant", "value": rule["native_hourly_value"]}
        else:
            raise ValueError(f"unknown companion method {method}")
    return compact


def convert(record: dict, schedules: dict) -> dict:
    recipe = record["recipe"]
    resolved = recipe["resolved"]
    context = recipe["source_context"]
    kind = KINDS[context["method"]]
    references = {}
    for slot, source in recipe["reference_sources"].items():
        schedules.setdefault(source["id"], _rules(source))
        references[slot] = source["id"]
    compact = {
        "schema_version": "2.0.0",
        "program_id": record["definition"]["id"],
        "name": record["definition"]["name"],
        "kind": kind,
        "source": _source(record),
        "slots": [{"slot": s["slot"], "kind": s["kind"], "unit": s["unit"],
                   "schedule": references.get(s["slot"])} for s in resolved["slots"]],
        "demands": [_demand(d, resolved) for d in resolved["demands"]],
        "controls": [_control(c) for c in resolved["controls"]],
        "companions": _companions(recipe["companion_rules"], schedules),
        "required_services": [link["source_service_id"] for link in recipe.get("required_service_links") or []],
    }
    if kind == "commercial":
        for part in context["occupancy_aggregation"]["constituents"]:
            schedules.setdefault(part["schedule"]["id"], _rules(part["schedule"]))
        compact["commercial"] = {
            "configuration_id": context["configuration_id"],
            "building_type": context["adaptation"]["sampling_selector"]["building_type"]
            if "sampling_selector" in context.get("adaptation", {}) else "medium_office",
            "modes": context["slot_modes"],
            "people": [[p["schedule"]["id"], p["nominal_people"]]
                       for p in context["occupancy_aggregation"]["constituents"]],
        }
    elif kind == "residential":
        bound = recipe["bound_inputs"]
        compact["dwelling"] = {new: bound[old] for old, new in DWELLING_FIELDS.items()}
        compact["thermostat"] = bound.get("thermostat_arguments")
    elif kind == "apartment_unit":
        # For N > 0 the ResStock unit timing replaces these fixed slots
        # (both lighting slots take the kernel's interior lighting).
        compact["unit_timing"] = {"occupants": "occupants", "lighting_interior": "lighting_interior",
                                  "additional_lighting": "lighting_interior"}
        compact["caller_water"] = _caller_water(recipe["required_service_sets"][0], schedules)
    elif kind == "composition":
        members = recipe["source_composition"]["definition"]["members"]
        compact["composition"] = {"composition_id": recipe["source_composition"]["composition_id"],
                                  "members": [[m["program_id"], m["represented_area_m2"]] for m in members]}
    return compact


# Native OpenStudio controls of the caller-unit water owner (create_water_use.rb:
# 140 F target, sensible 0.2, latent 0.05), identical for every apartment programme.
CALLER_WATER_CONTROLS = {"water_target_temperature": ["temperature", "C", 60.0],
                         "water_sensible_fraction": ["sensible_fraction", "fraction", 0.2],
                         "water_latent_fraction": ["latent_fraction", "fraction", 0.05]}


def _caller_water(requirement: dict, schedules: dict) -> dict:
    demand = requirement["original_demand"]["value"]
    ruleset = requirement["source_ruleset"]["value"]
    schedules.setdefault(ruleset["id"], _rules(ruleset))
    return {"service_id": requirement["source_service_id"], "schedule": ruleset["id"],
            "density": demand["value"], "density_unit": demand["unit"],
            "controls": CALLER_WATER_CONTROLS,
            "source": {"demand": f"{requirement['original_demand']['path']}#{requirement['original_demand']['locator']}",
                       "service": f"{requirement['service_definition']['path']}#{requirement['service_definition']['locator']}"}}


def convert_service(record: dict, schedules: dict) -> dict:
    """A shared physical service (one whole hot-water fixture) with one variant per configuration."""
    recipe = record["recipe"]
    resolved = recipe["resolved"]
    demand = resolved["demands"][0]
    configurations = {}
    for configuration_id, variant in recipe["configurations"].items():
        context = variant["source_context"]
        schedules.setdefault(variant["reference_source"]["id"], _rules(variant["reference_source"]))
        for part in context["occupancy_aggregation"]["constituents"]:
            schedules.setdefault(part["schedule"]["id"], _rules(part["schedule"]))
        configurations[configuration_id] = {
            "schedule": variant["reference_source"]["id"],
            "building_type": context["configuration_association"]["conditioning_inputs"]["building_type"],
            "people": [[p["schedule"]["id"], p["nominal_people"]] for p in context["occupancy_aggregation"]["constituents"]],
            "companions": _companions(variant["companion_rules"], schedules),
        }
    return {
        "schema_version": "2.0.0",
        "service_id": resolved["source_service_id"],
        "kind": "physical_service",
        "source": {"definition": record["provenance"]["source_locator"], "migrated_from": "v0.8.0 compiled service"},
        "demand": {k: demand[k] for k in ("quantity", "unit", "value", "basis", "fuel", "host")},
        "controls": [{k: c[k] for k in ("slot", "quantity", "unit")} for c in resolved["controls"]],
        "configurations": configurations,
    }


def main() -> None:
    schedules = {}
    counts = {}
    (TARGET / "recipes").mkdir(parents=True, exist_ok=True)
    for path in sorted(glob.glob(str(SOURCE / "*.json"))):
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        kind = KINDS[record["recipe"]["source_context"]["method"]]
        compact = convert(record, schedules)
        counts[kind] = counts.get(kind, 0) + 1
        out = TARGET / "recipes" / f"{compact['program_id']}.json"
        out.write_text(json.dumps(compact, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (TARGET / "services").mkdir(parents=True, exist_ok=True)
    for path in sorted((SOURCE.parent / "reference").glob("physical-service__*.json")):
        compact = convert_service(json.loads(path.read_text(encoding="utf-8")), schedules)
        counts["physical_service"] = counts.get("physical_service", 0) + 1
        out = TARGET / "services" / f"{compact['service_id']}.json"
        out.write_text(json.dumps(compact, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    table = TARGET / "schedules.json"
    table.write_text(json.dumps(schedules, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(counts, len(schedules), "schedules", table.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
