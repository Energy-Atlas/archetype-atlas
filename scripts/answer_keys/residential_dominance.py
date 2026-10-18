"""Extract the residential-dominance answer keys from the native captures.

- commercial/occupancy-dominance.json: per packaged configuration, native
  residential and non-residential design people on real prototype geometry
  (`python -m scripts.capture.occupancy_dominance`) and the dominant group's
  people without multipliers.
- commercial/residential-dominant.json.gz: residential-dominant hours cases
  with their carrier and slot rule sets, operating parameters and native final
  channels (`python -m scripts.capture.residential_dominant`).

Usage: python -m scripts.answer_keys.residential_dominance
"""
import gzip
import json
from pathlib import Path

from scripts.answer_keys.family_programmes import pack_days
from scripts.capture.residential_dominant import cases

ROOT = Path(__file__).resolve().parents[2]
DOMINANCE = ROOT / "build/task-10/native-dominance-20261018/dominance-native.json"
HOURS = ROOT / "build/task-10/native-residential-dominant-20261018/residential-dominant-native.json"
KEYS = ROOT / "tests/answer_keys/commercial"


def dominance() -> None:
    rows = {}
    for case in json.loads(DOMINANCE.read_text(encoding="utf-8"))["cases"]:
        totals = case["totals"]
        dominant = totals["residential"] > totals["non_residential"]
        rows[case["case_id"]] = {"residential": totals["residential"], "non_residential": totals["non_residential"],
                                 "dominant_people": sum(s["people"] for s in case["spaces"] if s["residential"] == dominant)}
    payload = {"source": {"capture": str(DOMINANCE.relative_to(ROOT)), "openstudio": "3.10.0",
                          "openstudio_standards": "0.8.6"}, "configurations": rows}
    target = KEYS / "occupancy-dominance.json"
    target.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(target.relative_to(ROOT), len(rows), "configurations")


def hours() -> None:
    native = {c["case_id"]: c for c in json.loads(HOURS.read_text(encoding="utf-8"))["cases"]}
    rows = []
    for item in cases():
        context = item["source_context"]
        carrier = context["occupancy_aggregation"]["constituents"][0]
        rows.append({"case_id": item["case_id"],
                     "carrier": {"rules": carrier["schedule"]["rules"], "people": carrier["nominal_people"]},
                     "slots": {slot: {"rules": d["rules"], "mode": context["slot_modes"][slot]}
                               for slot, d in item["schedules"].items()},
                     "operating": {k: {"modify": p["modify"], "value": p["value"]}
                                   for k, p in item["operating"]["effective_values"].items()},
                     "expected": {slot: pack_days(v) for slot, v in native[item["case_id"]]["channels"].items()}})
    payload = {"source": {"capture": str(HOURS.relative_to(ROOT)), "openstudio": "3.10.0",
                          "openstudio_standards": "0.8.6"}, "cases": rows}
    target = KEYS / "residential-dominant.json.gz"
    target.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"), mtime=0))
    print(target.relative_to(ROOT), len(rows), "cases", target.stat().st_size, "bytes")


if __name__ == "__main__":
    dominance()
    hours()
