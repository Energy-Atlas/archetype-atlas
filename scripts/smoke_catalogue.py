"""Generate every packaged programme, composition parent and shared-service variant once.

Reports failures by error code; programmes with no slots (unconditioned attics,
plenums) are counted as inactive. Writes docs/validation/schedule-generator-catalogue-smoke.json.

Usage: python -m scripts.smoke_catalogue
"""
import collections
import json
from pathlib import Path
import time

from atlas_schedules_v2.errors import GeneratorError
from atlas_schedules_v2.generator import generate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "atlas_schedules_v2/data"
OUTPUT = ROOT / "docs/validation/schedule-generator-catalogue-smoke.json"
LOCATION = {"state": "NC", "latitude": 35.741, "longitude": -81.389, "utc_offset": -5}


def _instance(recipe: dict) -> dict:
    instance = {"key": "unit", "program_id": recipe["program_id"]}
    if recipe["kind"] == "commercial":
        instance["operating_group"] = "building"
    if recipe["kind"] == "apartment_unit":
        instance.update(residents=2, location=LOCATION, extent={"floor_area": 80})
    return instance


def main() -> None:
    started = time.time()
    counts = collections.Counter()
    failures = collections.defaultdict(list)
    for path in sorted((DATA / "recipes").glob("*.json")):
        recipe = json.loads(path.read_text(encoding="utf-8"))
        if not recipe["slots"] and recipe["kind"] not in ("composition",):
            counts["inactive"] += 1
            continue
        instances = [_instance(recipe)]
        if recipe.get("required_services"):
            counts["needs_service_links"] += 1
            continue
        try:
            generate({"schema_version": "2.0.0", "seed": 1, "instances": instances})
            counts[recipe["kind"]] += 1
        except GeneratorError as error:
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
              "failure_count": sum(len(v) for v in failures.values()), "seconds": round(time.time() - started)}
    OUTPUT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("generated", "failure_count", "seconds")}))
    for code, items in failures.items():
        print(code, len(items), items[:5])


if __name__ == "__main__":
    main()
