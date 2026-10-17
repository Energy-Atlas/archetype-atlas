"""Generate every packaged programme, composition parent and shared-service variant once.

Reports failures by error code; programmes with no slots (unconditioned attics,
plenums) are counted as inactive. Commercial `zero_generated_integral` is a known
upstream outcome, not a failure: ComStock's base-to-peak measures clear any day
whose values are all equal (0/0 scale, NaN rejected by OpenStudio), so flat
data-centre plug loads become zero when a weekday ratio is sampled, and a
positive annual target cannot bind them. Exits 1 on any other failure.
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
from atlas_schedules.programmes import load_recipe, required_services

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "atlas_schedules/data"
OUTPUT = ROOT / "docs/validation/generator-catalogue-smoke.json"
LOCATION = {"state": "NC", "latitude": 35.741, "longitude": -81.389, "utc_offset": -5}


def _configuration(recipe: dict) -> str:
    """The building configuration a programme's shared services follow."""
    if recipe["kind"] == "composition":
        recipe = load_recipe(recipe["composition"]["members"][0][0])
    return recipe["commercial"]["configuration_id"]


def _instance(recipe: dict) -> dict:
    instance = {"key": "unit", "program_id": recipe["program_id"]}
    if recipe["kind"] in ("commercial", "composition"):
        instance["operating_group"] = "building"
    if recipe["kind"] == "apartment_unit":
        instance.update(residents=2, location=LOCATION, extent={"floor_area": 80})
    return instance


def main() -> None:
    started = time.time()
    counts = collections.Counter()
    failures = collections.defaultdict(list)
    upstream_zeroed = []
    for path in sorted((DATA / "recipes").glob("*.json")):
        recipe = json.loads(path.read_text(encoding="utf-8"))
        if not recipe["slots"] and recipe["kind"] not in ("composition",):
            counts["inactive"] += 1
            continue
        instances = [_instance(recipe)]
        linked = required_services(recipe)
        if linked:
            configuration = _configuration(recipe)
            links = {}
            for index, service_id in enumerate(linked):
                service = json.loads((DATA / "services" / f"{service_id}.json").read_text(encoding="utf-8"))
                key = f"service-{index}"
                links[service_id] = key
                instances.append({"key": key, "service_id": service_id, "configuration_id": configuration,
                                  "physical_id": key, "extent": {service["demand"]["basis"]: 1.0},
                                  "operating_group": "building"})
            instances[0]["service_links"] = links
        try:
            generate({"schema_version": "2.0.0", "seed": 1, "instances": instances})
            counts[recipe["kind"]] += 1
        except GeneratorError as error:
            if error.code == "zero_generated_integral" and recipe["kind"] == "commercial":
                upstream_zeroed.append(recipe["program_id"])
            else:
                failures[error.code].append(recipe["program_id"])
    for path in sorted((DATA / "services").glob("*.json")):
        service = json.loads(path.read_text(encoding="utf-8"))
        basis = service["demand"]["basis"]
        for configuration_id in service["configurations"]:
            instance = {"key": "water", "service_id": service["service_id"], "configuration_id": configuration_id,
                        "physical_id": "fixture", "extent": {basis: 1.0}, "operating_group": "building"}
            try:
                generate({"schema_version": "2.0.0", "seed": 1, "instances": [instance]})
                counts["service_variant"] += 1
            except GeneratorError as error:
                failures[error.code].append(f"{service['service_id']}@{configuration_id}")
    report = {"generated": dict(counts), "failures": {k: v for k, v in failures.items()},
              "upstream_zeroed": upstream_zeroed,
              "failure_count": sum(len(v) for v in failures.values())}
    OUTPUT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("generated", "failure_count")}),
          f"upstream_zeroed={len(upstream_zeroed)}", f"{time.time() - started:.0f} s")
    for code, items in failures.items():
        print(code, len(items), items[:5])
    if report["failure_count"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
