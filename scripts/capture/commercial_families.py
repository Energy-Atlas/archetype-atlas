"""Native captures of packaged commercial programmes with OpenStudio 3.10.

For each family's assigned template, both views and each seed, every active
programme of that configuration becomes one case of scripts/capture/commercial.rb:
its slot rule sets (and modes) from the packaged recipe, the configuration's
People list as the inference carrier (residential when the configuration
inverts rule days), and operating parameters sampled for the seed's operating
group. One more case per configuration carries every shared water service that
follows it. The harness runs pinned openstudio-standards 0.8.6 and ComStock
measure code natively: occupancy inference, the hours transform, the occupancy
adjustment and base-to-peak, and records the final hourly channels.

Usage: python -m scripts.capture.commercial_families OUT_DIR [LargeOffice ...]
Needs a frozen source folder and OpenStudio runtime (--source, --openstudio);
the defaults are the locked copies kept under build/task-10/native-warehouse-20261014-01.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from atlas_schedules.commercial.sampler import load_tables, sample_operating_parameters
from atlas_schedules.generator import load_service
from atlas_schedules.programmes import load_configuration, schedules
from atlas_schedules.seeds import commercial_group_seed

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "atlas_schedules/data"
HARNESS = Path(__file__).resolve().parent / "commercial.rb"
LOCKED = ROOT / "build/task-10/native-warehouse-20261014-01"
SEEDS = (42, 51)
GROUP = "building"
# One template per family (user decision 2026-10-17, plan section 7), both views.
FAMILIES = {
    "large_office": "90_1_2019", "large_hotel": "doe_ref_1980_2004", "small_hotel": "90_1_2007",
    "hospital": "doe_ref_pre_1980", "outpatient": "90_1_2019", "primary_school": "90_1_2013",
    "secondary_school": "doe_ref_1980_2004", "supermarket": "90_1_2007", "strip_mall": "doe_ref_pre_1980",
}


def _definition(schedule_id: str, name: str | None = None) -> dict:
    """A rule set in the standards row form model_add_schedule reads.

    model_add_schedule returns an existing schedule of the same name, so every
    slot gets its own name: slots that share a rule set must not share the
    object the harness transforms in place.
    """
    rules = [{**rule, "type": "Constant" if len(rule["values"]) == 1 else "Hourly"}
             for rule in schedules()[schedule_id]["rules"]]
    return {"source_name": name or schedule_id, "rules": rules}


def _context(configuration: dict, modes: dict) -> dict:
    residential = configuration["invert_rule_days"]
    constituents = [{"nominal_people": count, "schedule": _definition(schedule_id), "residential": residential}
                    for schedule_id, count in configuration["people"]]
    return {"year": 2007, "steps_per_hour": 6, "slot_modes": modes, "residential_carrier": residential,
            "occupancy_aggregation": {"constituents": constituents},
            "occupancy_adjustment": {"peak_occ_frac": 0.231}, "channels_only": True}


def _recipes_by_configuration() -> dict:
    found = {}
    for path in sorted((DATA / "recipes").glob("*.json")):
        recipe = json.loads(path.read_text(encoding="utf-8"))
        spec = recipe.get("commercial")
        if recipe["kind"] == "commercial" and spec and spec["modes"]:
            found.setdefault(spec["configuration_id"], []).append(recipe)
    return found


def _services_by_configuration() -> dict:
    found = {}
    for path in sorted((DATA / "services").glob("*.json")):
        service = json.loads(path.read_text(encoding="utf-8"))
        for configuration_id in service["configurations"]:
            found.setdefault(configuration_id, []).append(service["service_id"])
    return found


def cases_for(building_type: str) -> list:
    recipes, services = _recipes_by_configuration(), _services_by_configuration()
    cases = []
    for view in ("source", "reviewed"):
        configuration_id = f"{building_type}__{FAMILIES[building_type]}__{view}"
        configuration = load_configuration(configuration_id)
        tables = load_tables(configuration["building_type"])
        for seed in SEEDS:
            operating = sample_operating_parameters(tables, configuration["building_type"],
                                                    commercial_group_seed(seed, GROUP))
            for recipe in recipes.get(configuration_id, []):
                modes = recipe["commercial"]["modes"]
                slot_schedules = {s["slot"]: _definition(s["schedule"], f"{s['schedule']}#{s['slot']}")
                                  for s in recipe["slots"] if s["slot"] in modes}
                cases.append({"case_id": f"{configuration_id}@{seed}/{recipe['program_id']}",
                              "source_context": _context(configuration, modes), "schedules": slot_schedules,
                              "operating": {"effective_values": operating}})
            water = {}
            for service_id in services.get(configuration_id, []):
                variant = load_service(service_id)["configurations"][configuration_id]
                water[f"water:{service_id}"] = _definition(variant["schedule"], f"{variant['schedule']}#{service_id}")
            if water:
                cases.append({"case_id": f"{configuration_id}@{seed}/water",
                              "source_context": _context(configuration, {slot: "hours" for slot in water}),
                              "schedules": water, "operating": {"effective_values": operating}})
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("families", nargs="*", default=list(FAMILIES))
    parser.add_argument("--source", type=Path, default=LOCKED / "source")
    parser.add_argument("--openstudio", type=Path,
                        default=LOCKED / "runtime/OpenStudio-3.10.0+86d7e215a1-Windows/bin/openstudio.exe")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for building_type in args.families:
        started = time.time()
        cases = cases_for(building_type)
        input_path = args.out / f"{building_type}-input.json"
        output_path = args.out / f"{building_type}-native.json"
        input_path.write_text(json.dumps(cases) + "\n", encoding="utf-8", newline="\n")
        result = subprocess.run([str(args.openstudio), str(HARNESS), str(args.source), str(input_path), str(output_path)],
                                capture_output=True, text=True, env={**os.environ, "TZ": "UTC"})
        (args.out / f"{building_type}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            sys.exit(f"{building_type}: harness failed ({result.returncode}); see {building_type}.log")
        print(building_type, len(cases), "cases", f"{time.time() - started:.0f} s", flush=True)


if __name__ == "__main__":
    main()
