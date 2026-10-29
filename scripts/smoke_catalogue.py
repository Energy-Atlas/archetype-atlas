"""Generate every programme view, composition parent and shared-service variant of the release once.

Reports failures by error code; programmes with no slots (unconditioned attics,
plenums) are counted as inactive. Exits 1 on any failure.
Writes docs/validation/generator-catalogue-smoke.json.

Usage: python -m scripts.smoke_catalogue
"""
import collections
import json
from pathlib import Path
import sys
import time

from atlas_schedules.errors import GeneratorError
from atlas_schedules.generator import generate
from atlas_schedules.programmes import catalogue, load_recipe, load_service, required_services, service_catalogue

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/validation/generator-catalogue-smoke.json"
LOCATION = {"state": "NC", "latitude": 35.741, "longitude": -81.389, "utc_offset": -5}


def _configuration(recipe: dict) -> str:
    """The building configuration a programme's shared services follow."""
    if recipe["kind"] == "composition":
        composition = recipe["composition"]
        recipe = load_recipe(composition["members"][0][0], composition["member_values"][0])
    return recipe["commercial"]["configuration_id"]


def _instance(recipe: dict) -> dict:
    instance = {"key": "unit", "program_id": recipe["program_id"], "values": recipe["values"]}
    if recipe["kind"] in ("commercial", "composition"):
        instance["operating_group"] = "building"
    if recipe["kind"] == "apartment_unit":
        instance.update(residents=2, location=LOCATION, extent={"floor_area": 80})
    return instance


def main() -> None:
    started = time.time()
    counts = collections.Counter()
    failures = collections.defaultdict(list)
    for program_id, values, _ in catalogue():
        recipe = load_recipe(program_id, values)
        if not recipe.get("slots") and recipe["kind"] not in ("composition", "apartment_unit"):
            counts["inactive"] += 1
            continue
        instances = [_instance(recipe)]
        linked = required_services(recipe)
        if linked:
            configuration = _configuration(recipe)
            links = {}
            for index, service_id in enumerate(linked):
                service = load_service(service_id)
                key = f"service-{index}"
                links[service_id] = key
                instances.append({"key": key, "service_id": service_id, "configuration_id": configuration,
                                  "physical_id": key, "extent": {service["demand"]["basis"]: 1.0},
                                  "operating_group": "building"})
            instances[0]["service_links"] = links
        try:
            generate({"schema_version": "3.0.0", "seed": 1, "instances": instances})
            counts[recipe["kind"]] += 1
        except GeneratorError as error:
            failures[error.code].append(f"{program_id}@{values}")
    for service_id, configuration_id in service_catalogue():
        service = load_service(service_id)
        instance = {"key": "water", "service_id": service_id, "configuration_id": configuration_id,
                    "physical_id": "fixture", "extent": {service["demand"]["basis"]: 1.0}, "operating_group": "building"}
        try:
            generate({"schema_version": "3.0.0", "seed": 1, "instances": [instance]})
            counts["service_variant"] += 1
        except GeneratorError as error:
            failures[error.code].append(f"{service_id}@{configuration_id}")
    report = {"generated": dict(counts), "failures": {k: v for k, v in failures.items()},
              "failure_count": sum(len(v) for v in failures.values())}
    OUTPUT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("generated", "failure_count")}),
          f"{time.time() - started:.0f} s")
    for code, items in failures.items():
        print(code, len(items), items[:5])
    if report["failure_count"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
