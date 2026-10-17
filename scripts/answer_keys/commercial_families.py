"""Extract compact commercial family answer keys from the native captures.

Sources (all captured on OpenStudio 3.10.0 with openstudio-standards 0.8.6):
- data/schedule-generator/{medium-office,small-office,warehouse}-family-native.json.gz
- data/schedule-generator/reference/schedule-generator-restaurant-programme-native.json.gz
- data/schedule-generator/reference/retail-programme-native.json.xz
- data/schedule-generator/reference/restaurant-water-native.json.gz (water slots)

Each 8760 array is stored as its distinct days plus a 365-entry day index, and
rule sets are stored once in a shared table keyed by schedule id.

Usage: python -m scripts.answer_keys.commercial_families
"""
import gzip
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "tests/answer_keys/commercial/families.json.gz"
PROGRAMME_SOURCES = (
    "data/schedule-generator/medium-office-family-native.json.gz",
    "data/schedule-generator/small-office-family-native.json.gz",
    "data/schedule-generator/warehouse-family-native.json.gz",
    "data/schedule-generator/reference/schedule-generator-restaurant-programme-native.json.gz",
    "data/schedule-generator/reference/retail-programme-native.json.xz",
)
WATER_SOURCE = "data/schedule-generator/reference/restaurant-water-native.json.gz"
RULE_FIELDS = ("day_types", "start_date", "end_date", "values")


def _load(path: str):
    raw = (ROOT / path).read_bytes()
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    elif path.endswith(".xz"):
        raw = lzma.decompress(raw)
    return json.loads(raw)


def pack_days(values: list) -> dict:
    """8760 values -> {"days": distinct 24-value days, "index": 365 day indices}."""
    days = []
    lookup = {}
    index = []
    for day in range(365):
        key = tuple(values[24 * day:24 * (day + 1)])
        if key not in lookup:
            lookup[key] = len(days)
            days.append(list(key))
        index.append(lookup[key])
    return {"days": days, "index": index}


def _schedule_id(schedule: dict, table: dict) -> str:
    table.setdefault(schedule["id"], {"rules": [{k: r[k] for k in RULE_FIELDS} for r in schedule["rules"]]})
    return schedule["id"]


def _programme_cases(table: dict) -> list:
    cases = []
    for path in PROGRAMME_SOURCES:
        for case in _load(path)["cases"]:
            context = case["source_context"]
            if not context["slot_modes"]:
                continue
            cases.append({
                "case_id": case["case_id"],
                "source": path,
                "configuration_id": context["configuration_id"],
                "slots": {name: [_schedule_id(case["schedules"][name], table), mode]
                          for name, mode in context["slot_modes"].items()},
                "people": [[_schedule_id(p["schedule"], table), p["nominal_people"]]
                           for p in context["occupancy_aggregation"]["constituents"]],
                "operating": case["operating"]["effective_values"],
                "expected": {name: pack_days(case["channels"][name]) for name in context["slot_modes"]},
            })
    return cases


def _hours_table(table: dict) -> list:
    return [[e["hoo_start"], e["hoo_end"], e["hoo_hours"], e["days_used"]] for e in table.values()]


def _water_cases() -> list:
    cases = []
    for case in _load(WATER_SOURCE)["cases"]:
        if not case.get("original_water") or not case.get("registration"):
            continue
        cases.append({
            "case_id": case["case_id"],
            "original": pack_days(case["original_water"]["values"]),
            "expected": pack_days(case["final_water"]["values"]),
            "original_hours": _hours_table(case["registration"]["hoo_inputs"]),
            "new_hours": _hours_table(case["modified_hoo"]),
        })
    return cases


def main() -> None:
    table = {}
    payload = {
        "source": {"openstudio": "3.10.0", "openstudio_standards": "0.8.6",
                   "files": list(PROGRAMME_SOURCES) + [WATER_SOURCE]},
        "programme_cases": _programme_cases(table),
        "water_cases": _water_cases(),
        "schedules": table,
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    TARGET.write_bytes(gzip.compress(blob, mtime=0))
    print(f"{TARGET.relative_to(ROOT)}: {len(payload['programme_cases'])} programme cases, "
          f"{len(payload['water_cases'])} water cases, {len(table)} schedules, {TARGET.stat().st_size} bytes")


if __name__ == "__main__":
    main()
