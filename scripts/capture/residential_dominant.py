"""Native captures of the residential-dominant (inverted rule-day) hours path.

No packaged configuration is residential-dominant, so these cases build the
condition on purpose: the People carrier is residential (all people in guest or
patient rooms), which makes openstudio-standards infer hours from residential
occupancy and invert its rule days. Two kinds of carrier:
- real: guest-room and patient-room occupancy, with those programmes and a
  non-residential programme of the same building;
- crafted occupancy rule sets that stress which day profile becomes the
  default (never inverted): seasonal weekday rules against an all-year
  weekend, a near tie of two weekday profiles, one profile per weekday, a
  default-only schedule, and a plain weekday/weekend split.
Cases run through scripts/capture/commercial.rb (OpenStudio 3.10,
openstudio-standards 0.8.6) at seeds 42 and 51.

Usage: python -m scripts.capture.residential_dominant OUT_DIR
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from atlas_schedules.commercial.sampler import load_tables, sample_operating_parameters
from atlas_schedules.programmes import load_recipe, schedules
from atlas_schedules.seeds import commercial_group_seed
from scripts.capture.commercial_families import GROUP, HARNESS, LOCKED, SEEDS

START, END = "2014-01-01T00:00:00+00:00", "2014-12-31T00:00:00+00:00"
NIGHT = [0.9] * 6 + [0.6, 0.4, 0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 0.9, 0.9, 0.9, 0.9]
NIGHT_B = [0.8] * 5 + [0.5] * 3 + [0.1] * 9 + [0.5] * 3 + [0.8] * 4
NIGHT_C = [0.7] * 8 + [0.2] * 8 + [0.7] * 8
NIGHT_D = [0.7] * 10 + [0.2] * 6 + [0.7] * 8   # on/off pattern distinct from NIGHT and NIGHT_B
WEEKEND = [0.9] * 9 + [0.6] * 6 + [0.4] * 4 + [0.8] * 5
EXTRA = ([0.95] * 7 + [0.3] * 10 + [0.95] * 7, [0.6] * 4 + [0.15] * 14 + [0.6] * 6, [1.0] * 10 + [0.5] * 6 + [1.0] * 8)


def _rule(day_types: str, values: list, start: str = START, end: str = END) -> dict:
    return {"day_types": day_types, "start_date": start, "end_date": end, "values": values}


CRAFTED = {
    "weekend_most_frequent": [_rule("Default", NIGHT),
                              _rule("Wkdy", NIGHT_B, "2014-05-01T00:00:00+00:00", "2014-08-31T00:00:00+00:00"),
                              _rule("Wkdy", NIGHT_D, "2014-09-01T00:00:00+00:00"),
                              _rule("Wknd", WEEKEND)],
    "weekday_near_tie": [_rule("Default", NIGHT), _rule("Wkdy", NIGHT_B, "2014-07-01T00:00:00+00:00"),
                         _rule("Wknd", WEEKEND)],
    "one_profile_per_weekday": [_rule("Default", NIGHT), _rule("Tue", NIGHT_B), _rule("Wed", NIGHT_C),
                                _rule("Thu", EXTRA[0]), _rule("Fri", EXTRA[1]), _rule("Sat", WEEKEND),
                                _rule("Sun", EXTRA[2])],
    "default_only": [_rule("Default", NIGHT)],
    "weekday_weekend": [_rule("Default", NIGHT), _rule("Wknd", WEEKEND)],
}
# (carrier occupancy rule set id, programmes, sampling building type)
REAL = {
    "large_hotel_guest_room": ("schedule-7a18e153dfd8afdd8217",
                               ["program-132a52fdf711e662eb073b7e", "program-760ff60a379b3a6900ab48c0"], "large_hotel"),
    "small_hotel_guest_room": ("schedule-5f6cff53c3fd003a0123", ["program-7c390dcb50dd322603bf5b08"], "small_hotel"),
    "hospital_patient_room": ("schedule-5eb5d81977991b16bd52",
                              ["program-f865ed686e13690b038d8546", "program-9ed1fe7cff073eb8a66bd545"], "hospital"),
}
GUEST_LIGHTING = "program-132a52fdf711e662eb073b7e"


def _rows(rules: list, name: str) -> dict:
    return {"source_name": name, "rules": [{**r, "type": "Constant" if len(r["values"]) == 1 else "Hourly"} for r in rules]}


def _case(case_id: str, carrier_rules: list, carrier_name: str, slots: dict, building_type: str, seed: int) -> dict:
    """slots: {slot: (rules, mode)}."""
    operating = sample_operating_parameters(load_tables(building_type), building_type, commercial_group_seed(seed, GROUP))
    return {"case_id": case_id,
            "source_context": {"year": 2007, "steps_per_hour": 6, "residential_carrier": True, "channels_only": True,
                               "slot_modes": {slot: mode for slot, (_, mode) in slots.items()},
                               "occupancy_aggregation": {"constituents": [
                                   {"nominal_people": 100.0, "schedule": _rows(carrier_rules, carrier_name), "residential": True}]},
                               "occupancy_adjustment": {"peak_occ_frac": 0.231}},
            "schedules": {slot: _rows(rules, f"{case_id}#{slot}") for slot, (rules, _) in slots.items()},
            "operating": {"effective_values": operating}}


def _programme_slots(program_id: str) -> dict:
    recipe = load_recipe(program_id)
    modes = recipe["commercial"]["modes"]
    table = schedules()
    return {s["slot"]: (table[s["schedule"]]["rules"], modes[s["slot"]]) for s in recipe["slots"] if s["slot"] in modes}


def cases() -> list:
    """Every case with its carrier and slot rule sets, so the key can rebuild it."""
    table = schedules()
    items = []
    for seed in SEEDS:
        for name, (carrier, programmes, building_type) in REAL.items():
            for program_id in programmes:
                items.append(_case(f"{name}@{seed}/{program_id}", table[carrier]["rules"], carrier,
                                   _programme_slots(program_id), building_type, seed))
        lighting = _programme_slots(GUEST_LIGHTING)["lighting"]
        for name, rules in CRAFTED.items():
            items.append(_case(f"{name}@{seed}", rules, name, {"occupancy": (rules, "hours"), "lighting": lighting},
                               "large_hotel", seed))
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--source", type=Path, default=LOCKED / "source")
    parser.add_argument("--openstudio", type=Path,
                        default=LOCKED / "runtime/OpenStudio-3.10.0+86d7e215a1-Windows/bin/openstudio.exe")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    input_path, output_path = args.out / "residential-dominant-input.json", args.out / "residential-dominant-native.json"
    input_path.write_text(json.dumps(cases()) + "\n", encoding="utf-8", newline="\n")
    result = subprocess.run([str(args.openstudio), str(HARNESS), str(args.source), str(input_path), str(output_path)],
                            capture_output=True, text=True, env={**os.environ, "TZ": "UTC"})
    (args.out / "residential-dominant.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        sys.exit(f"harness failed ({result.returncode}); see residential-dominant.log")
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
