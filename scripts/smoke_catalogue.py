"""Generate every programme view, composition parent and shared-service variant of the release once.

Reports failures by error code; programmes with no slots (unconditioned attics,
plenums) are counted as inactive. Exits 1 on any failure.
Writes docs/validation/generator-catalogue-smoke.json.

Usage: python -m scripts.smoke_catalogue [--sample N]

`--sample N` generates a deterministic subset instead: at most N recipes of every
family (kind × template × building type), spread evenly over the sorted recipes, and
at most N configurations of every service. It reports to standard output only; the
full run writes the report. The recipes are assembled from the release the generator
reads (atlas_schedules.release.current; ADR 0051).
"""
import argparse
import collections
import json
import math
from pathlib import Path
import sys
import time

from atlas_schedules.errors import GeneratorError
from atlas_schedules.generator import generate
from atlas_schedules.programmes import catalogue, load_recipe, load_service, required_services, service_catalogue
from atlas_schedules.release import current

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


def spread(items: list, sample: int | None) -> list:
    """At most `sample` items spread evenly over the list (every item when sample is None)."""
    if sample is None or len(items) <= sample:
        return items
    return items[:: math.ceil(len(items) / sample)][:sample]


def family(recipe: dict) -> tuple:
    source = recipe["source"]
    return recipe["kind"], source.get("template"), source.get("building_type")


def recipes(sample: int | None) -> list:
    """The release's recipes to generate, in catalogue order: all, or `sample` per family."""
    loaded = [load_recipe(program_id, values) for program_id, values, _ in catalogue()]
    if sample is None:
        return loaded
    families = collections.defaultdict(list)
    for recipe in loaded:
        families[family(recipe)].append(recipe)
    return [recipe for key in sorted(families, key=str) for recipe in spread(families[key], sample)]


def services(sample: int | None) -> list:
    """(service ID, configuration ID) variants: all, or `sample` configurations per service."""
    by_service = collections.defaultdict(list)
    for service_id, configuration_id in service_catalogue():
        by_service[service_id].append(configuration_id)
    return [(sid, cid) for sid in sorted(by_service) for cid in spread(sorted(by_service[sid]), sample)]


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", type=int, help="at most this many recipes per family and configurations per service")
    args = parser.parse_args(argv)
    started = time.time()
    counts = collections.Counter()
    failures = collections.defaultdict(list)
    release = current()
    for recipe in recipes(args.sample):
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
            generate({"schema_version": "4.0.0", "seed": 1, "instances": instances})
            counts[recipe["kind"]] += 1
        except GeneratorError as error:
            failures[error.code].append(f"{recipe['program_id']}@{recipe['values']}")
    for service_id, configuration_id in services(args.sample):
        service = load_service(service_id)
        instance = {"key": "water", "service_id": service_id, "configuration_id": configuration_id,
                    "physical_id": "fixture", "extent": {service["demand"]["basis"]: 1.0}, "operating_group": "building"}
        try:
            generate({"schema_version": "4.0.0", "seed": 1, "instances": [instance]})
            counts["service_variant"] += 1
        except GeneratorError as error:
            failures[error.code].append(f"{service_id}@{configuration_id}")
    report = {"release": release.provenance(), "generated": dict(counts), "failures": {k: v for k, v in failures.items()},
              "failure_count": sum(len(v) for v in failures.values())}
    if args.sample is None:
        OUTPUT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("generated", "failure_count")}),
          f"{time.time() - started:.0f} s" + (f" (sample {args.sample} per family)" if args.sample else ""),
          f"release {release.version}")
    for code, items in failures.items():
        print(code, len(items), items[:5])
    if report["failure_count"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
