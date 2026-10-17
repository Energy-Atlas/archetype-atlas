"""Extract the native 2013 SOURCE pilots of the new commercial families as an answer key.

Sources: build/task-10/native-{large-office,large-hotel,hospital,outpatient}-pilot-20261014-01/
native-output.json, real OpenStudio 3.10 / openstudio-standards 0.8.6 runs at
seeds 42 and 51. Per case: the native People per space (floor area, design
people) of the dominant occupancy group, the sampled operating parameters, and
each shared water service's final hourly values.

Usage: python -m scripts.answer_keys.family_pilots
"""
import gzip
import json
from pathlib import Path

from scripts.answer_keys.commercial_families import pack_days

ROOT = Path(__file__).resolve().parents[2]
PILOTS = {"LargeOffice": "native-large-office-pilot-20261014-01", "LargeHotel": "native-large-hotel-pilot-20261014-01",
          "Hospital": "native-hospital-pilot-20261014-01", "Outpatient": "native-outpatient-pilot-20261014-01"}
TARGET = ROOT / "tests/answer_keys/commercial/family-pilots.json.gz"


def _spaces(case: dict) -> dict:
    if "people_spaces" in case:
        return {s["space_name"]: [s["floor_area_m2"], s["nominal_people"]] for s in case["people_spaces"]}
    return {o["space_name"]: [o["floor_area_m2"], o["actual_carrier_operand_people"]] for o in case["carrier"]["operands"]}


def _water(case: dict) -> list:
    water = []
    if "final_water" in case:  # one shared water Ruleset for every fixture
        service = case["fixtures"][0]["source_service_id"]
        return [{"service_id": service, "expected": pack_days(case["final_water"]["values"])}]
    for handle, channel in case["channels"].items():
        if channel[0]["kind"] != "WaterUseEquipment":
            continue
        fixture = next(f for f in case["fixture_receipts"] if f["schedule_handle"] == handle)
        water.append({"service_id": fixture["source_service_id"], "expected": pack_days(case["final"][handle]["values"])})
    return water


def main() -> None:
    cases = []
    for building_type, folder in PILOTS.items():
        output = json.loads((ROOT / "build/task-10" / folder / "native-output.json").read_text(encoding="utf-8"))
        for case in output["cases"]:
            cases.append({"building_type": building_type, "template": "90.1-2013", "view": "source",
                          "case_id": case["case_id"], "operating": case["operating"]["effective_values"],
                          "spaces": _spaces(case), "water": _water(case)})
    payload = {"source": {"pilots": list(PILOTS.values()), "openstudio": "3.10.0", "openstudio_standards": "0.8.6"},
               "cases": cases}
    TARGET.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"), mtime=0))
    print(TARGET.relative_to(ROOT), len(cases), "cases", TARGET.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
