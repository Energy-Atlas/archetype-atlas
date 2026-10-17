"""Capture legacy generator output for single-programme requests (orchestration answer key).

Runs the frozen v0.8.0 legacy generator (unpacked from
data/generator-releases/v0.8.0/generator.zip, sha256 bb1eb96b..., into
build/task-10/v080-package) on one request per programme: seed 42, one
instance, unit extents for every demand basis. Stores per slot the hourly
values (as distinct days plus a day index) and per demand the fitted amplitude.

Usage: python -m scripts.answer_keys.legacy_programmes [program ids...]
"""
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "build/task-10/v080-package"
TARGET = ROOT / "tests/answer_keys/orchestration/programmes.json.gz"
KINDS = {"prototype_budget_preserving_commercial_hybrid", "atlas_frozen_definition_comstock_v33_standards086_hybrid",
         "resstock_time_allocation_with_selected_source_companions", "source_fixed_apartment_programme"}
EXTENT_UNITS = {"floor_area": "m2", "dwelling_unit": "dwelling", "person": "person", "absolute": "1"}
SEED = 42


SAMPLE_HOURS = list(range(0, 8760, 37))


def _pack(values: list) -> dict:
    """Distinct days plus a day index; stochastic series (over 60 distinct days)
    as 365 daily sums plus values at every 37th hour."""
    days, lookup, index = [], {}, []
    for day in range(365):
        key = tuple(values[24 * day:24 * (day + 1)])
        if key not in lookup:
            lookup[key] = len(days)
            days.append(list(key))
        index.append(lookup[key])
    if len(days) > 60:
        daily = [sum(values[24 * d:24 * (d + 1)]) for d in range(365)]
        return {"daily": daily, "sample": [values[h] for h in SAMPLE_HOURS]}
    return {"days": days, "index": index}


def repack(path: Path) -> None:
    """Re-encode an existing capture with the current _pack (no regeneration)."""
    payload = json.loads(gzip.decompress(path.read_bytes()))
    for case in payload["cases"]:
        for slot, packed in case["slots"].items():
            if "days" in packed:
                values = [v for i in packed["index"] for v in packed["days"][i]]
                case["slots"][slot] = _pack(values)
    path.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"), mtime=0))


def _request(record: dict, resource_set_id: str) -> dict:
    recipe = record["recipe"]
    inputs = dict(recipe["bound_inputs"])
    bases = {d["basis"] for d in recipe["resolved"]["demands"]}
    extents = {b: {"value": 1, "unit": EXTENT_UNITS[b], "evidence": {"caller": "answer key unit extent"}} for b in bases}
    version = recipe.get("required_contract_version", "1.0.0")
    instance = {"key": "unit", "program_id": record["definition"]["id"], "inputs": inputs,
                "basis_bindings": {"extents": extents},
                "operating_group": "group" if "slot_modes" in recipe["source_context"] else None}
    if version != "1.0.0":
        instance["owner_kind"] = "program"
        if recipe.get("required_service_links") is not None:
            instance["service_links"] = {}
    return {"schema_version": version, "resource_set_id": resource_set_id,
            "calendar": {"year": 2007, "clock": "local_standard_time", "holidays": []},
            "instances": [instance]}


def main() -> None:
    sys.path.insert(0, str(PACKAGE))
    from atlas_schedules import generate  # the legacy package
    from atlas_schedules.errors import GeneratorError
    manifest = json.loads((PACKAGE / "atlas_schedules/data/manifest.json").read_text(encoding="utf-8"))
    wanted = set(sys.argv[1:])
    cases, failures = [], {}
    for path in sorted((PACKAGE / "atlas_schedules/data/program").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        method = record["recipe"]["source_context"]["method"]
        program_id = record["definition"]["id"]
        if method not in KINDS or (wanted and program_id not in wanted):
            continue
        try:
            bundle = generate(_request(record, manifest["resource_set_id"]), SEED)
        except GeneratorError as error:
            failures[program_id] = f"{error.code} {error.path} {error.message}"[:200]
            continue
        constituent = bundle["constituents"][0]
        schedules = {s["id"]: s for s in bundle["schedules"].values()} if isinstance(bundle["schedules"], dict) else {}
        slots = {}
        for slot, schedule_id in constituent["schedule_ids"].items():
            slots[slot] = _pack(bundle["schedules"][schedule_id]["values"])
        bindings = []  # in demand order; one slot may carry two fuels
        for index in constituent["binding_indices"]:
            binding = bundle["bindings"][index]
            if "effective_magnitude" in binding:
                bindings.append({"slot": binding["slot"], "amplitude": binding["effective_magnitude"]["value"],
                                 "unit": binding["effective_magnitude"]["unit"],
                                 "annual_total": binding["reference_target"]["total"]})
        cases.append({"program_id": program_id, "method": method, "seed": SEED, "slots": slots,
                      "bindings": bindings, "operating": bundle["generation"].get("operating_groups")})
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": {"package": "data/generator-releases/v0.8.0/generator.zip",
                          "package_sha256": "bb1eb96b", "seed": SEED},
               "cases": cases, "failures": failures}
    TARGET.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"), mtime=0))
    print(f"{len(cases)} cases, {len(failures)} failures, {TARGET.stat().st_size} bytes")
    for program_id, message in list(failures.items())[:8]:
        print(" ", program_id, message)


if __name__ == "__main__":
    if sys.argv[1:] == ["--repack"]:
        repack(TARGET)
        print(TARGET.stat().st_size)
    else:
        main()
