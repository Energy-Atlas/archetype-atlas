"""Move each commercial configuration's People topology out of the recipes.

Every recipe of one configuration (building type, template, view) carried the
same People list. This writes atlas_schedules_v2/data/configurations/<id>.json
(sampling building type, People, rule-day inversion) once, and leaves recipes
and shared-service variants with only the configuration id. It refuses to run
if two recipes disagree about a configuration.

Usage: python -m scripts.migrate.configurations
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "atlas_schedules_v2/data"


def _record(spec: dict) -> dict:
    return {"building_type": spec["building_type"], "people": spec["people"],
            "invert_rule_days": spec.get("invert_rule_days", False)}


def main() -> None:
    configurations = {}

    def register(configuration_id: str, record: dict, where: str) -> None:
        known = configurations.setdefault(configuration_id, record)
        if known != record:
            raise SystemExit(f"{where}: configuration {configuration_id} differs from an earlier recipe")

    recipe_paths = sorted((DATA / "recipes").glob("*.json"))
    for path in recipe_paths:
        recipe = json.loads(path.read_text(encoding="utf-8"))
        spec = recipe.get("commercial")
        if spec and "people" in spec:
            register(spec["configuration_id"], _record(spec), path.name)
    service_paths = sorted((DATA / "services").glob("*.json"))
    for path in service_paths:
        service = json.loads(path.read_text(encoding="utf-8"))
        for configuration_id, variant in service["configurations"].items():
            if "people" in variant:
                register(configuration_id, _record(variant), path.name)
    folder = DATA / "configurations"
    folder.mkdir(exist_ok=True)
    for configuration_id, record in configurations.items():
        (folder / f"{configuration_id}.json").write_text(
            json.dumps(dict(record, configuration_id=configuration_id), indent=1, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")
    for path in recipe_paths:
        recipe = json.loads(path.read_text(encoding="utf-8"))
        spec = recipe.get("commercial")
        if spec and "people" in spec:
            recipe["commercial"] = {"configuration_id": spec["configuration_id"], "modes": spec["modes"]}
            path.write_text(json.dumps(recipe, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    for path in service_paths:
        service = json.loads(path.read_text(encoding="utf-8"))
        for configuration_id, variant in service["configurations"].items():
            for key in ("people", "building_type", "invert_rule_days"):
                variant.pop(key, None)
        path.write_text(json.dumps(service, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(configurations), "configurations")


if __name__ == "__main__":
    main()
