"""Extract the compact Stripmall answer key (2013 SOURCE pilot, seeds 42 and 51).

Sources:
- data/schedule-generator/stripmall/pilot-2013-source-carrier.json.gz, the
  tracked extract of the native OpenStudio 3.10 pilot (see its lock);
- data/definition-releases/v0.1.1/{programs,schedules}.json for the frozen
  occupancy and water rule sets the native model used.

The pilot has three People Rulesets (store types 1-3) across ten spaces, and
three shared water Rulesets, each registered by its first fixture.

Usage: python -m scripts.answer_keys.stripmall
"""
import gzip
import json
from pathlib import Path

from scripts.answer_keys.commercial_families import RULE_FIELDS, pack_days

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "data/schedule-generator/stripmall/pilot-2013-source-carrier.json.gz"
DEFINITIONS = ROOT / "data/definition-releases/v0.1.1"
TARGET = ROOT / "tests/answer_keys/commercial/stripmall.json.gz"
TYPE_PROGRAMMES = {"Type1": "program-f9034faffb02f5e77056c6cf", "Type2": "program-75cf4ec07b0c6053a2e1ba6d",
                   "Type3": "program-e44fc2ec3f865c660176b600"}


def _rules(schedule: dict) -> dict:
    return {"rules": [{k: r[k] for k in RULE_FIELDS} for r in schedule["rules"]]}


def main() -> None:
    pilot = json.loads(gzip.decompress(PILOT.read_bytes()))
    programmes = {p["id"]: p for p in json.loads((DEFINITIONS / "programs.json").read_text(encoding="utf-8"))}
    schedules = {s["id"]: s for s in json.loads((DEFINITIONS / "schedules.json").read_text(encoding="utf-8"))}
    occupancy_ids = {}
    for kind, program_id in TYPE_PROGRAMMES.items():
        load = next(l for l in programmes[program_id]["loads"] if l["quantity"] == "occupancy")
        occupancy_ids[kind] = load["schedule_id"]
    table = {}
    cases = []
    for case in pilot["cases"]:
        people = []
        for operand in case["carrier"]["operands"]:
            kind = operand["schedule_name"].split()[-1].split("_")[0]
            schedule_id = occupancy_ids[kind]
            table.setdefault(schedule_id, _rules(schedules[schedule_id]))
            people.append([schedule_id, operand["actual_carrier_operand_people"]])
        water = {}
        for handle, channel in case["channels"].items():
            if channel[0]["kind"] != "WaterUseEquipment":
                continue
            fixture = next(f for f in case["fixture_receipts"] if f["schedule_handle"] == handle)
            schedule_id = fixture["atlas_schedule_id"]
            table.setdefault(schedule_id, _rules(schedules[schedule_id]))
            water[case["original"][handle]["name"]] = {
                "schedule_id": schedule_id,
                "expected": pack_days(case["final"][handle]["values"]),
            }
        cases.append({"case_id": case["case_id"], "people": people, "water": water,
                      "operating": case["operating"]["effective_values"]})
    payload = {"source": {"pilot": str(PILOT.relative_to(ROOT)).replace("\\", "/"),
                          "definitions": "data/definition-releases/v0.1.1", "openstudio": "3.10.0"},
               "cases": cases, "schedules": table}
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    TARGET.write_bytes(gzip.compress(blob, mtime=0))
    print(f"{TARGET.relative_to(ROOT)}: {len(cases)} cases, {TARGET.stat().st_size} bytes")


if __name__ == "__main__":
    main()
