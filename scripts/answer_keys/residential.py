"""Extract compact residential answer keys from the native Ruby captures.

Sources (Ruby 3.2.2 running OpenStudio-HPXML `BuildResidentialScheduleFile`,
ResStock revision dd25369):
- data/schedule-generator/residential-family-native.json.gz (52 units)
- data/schedule-generator/apartment/selected-native.json.gz (6 occupancy/lighting units)

Random hourly values do not compress, so most channels are stored as a
signature: 365 daily sums plus the values at a fixed sample of hours. Two units
keep full arrays. Discrete outcomes (occupant types, unit offset) are exact.

Usage: python -m scripts.answer_keys.residential
"""
import gzip
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FAMILY = "data/schedule-generator/residential-family-native.json.gz"
APARTMENT = "data/schedule-generator/apartment/selected-native.json.gz"
TARGET = ROOT / "tests/answer_keys/residential"
SAMPLE_HOURS = np.arange(0, 8760, 37)
FULL_CASES = {"one", "multiple"}
SYNTHETIC = {"component_no_events", "component_boundary", "component_all_absent"}


def _load(path: str) -> dict:
    return json.loads(gzip.decompress((ROOT / path).read_bytes()))


def _signature(arrays: dict, key: str, values, full: bool) -> None:
    values = np.asarray(values, dtype=float)
    arrays[f"{key}|daily"] = values.reshape(365, 24).sum(axis=1)
    arrays[f"{key}|sample"] = values[SAMPLE_HOURS]
    if full:
        arrays[f"{key}|full"] = values


def main() -> None:
    arrays = {}
    cases = []
    for path, kind in ((FAMILY, "dwelling"), (APARTMENT, "occupancy_and_lighting")):
        for case in _load(path)["cases"]:
            if case.get("fan_on"):
                # Probe of the full measure with the ceiling fan on and no weather.
                # The apartment method has no fan step (ADR 0030), so it does not apply.
                continue
            entry = {"case_id": case["case_id"], "kind": kind, "inputs": case["inputs"],
                     "unit_seed": case["unit_seed"], "offset_minutes": case.get("unit_offset_minutes"),
                     "occupant_types": case.get("occupant_types"),
                     "error": case.get("source_error"),
                     "undefined": case.get("source_undefined_channels") or []}
            if case["case_id"] in SYNTHETIC:
                entry["state_runs"] = case["resident_state_runs"]
            channels = {}
            for name, values in (case.get("channels") or {}).items():
                if values is None or any(v is None for v in values):
                    continue
                channels[name] = True
                _signature(arrays, f"{case['case_id']}|{name}", values, case["case_id"] in FULL_CASES)
            entry["channels"] = sorted(channels)
            cases.append(entry)
    TARGET.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(TARGET / "channels.npz", sample_hours=SAMPLE_HOURS, **arrays)
    payload = {"source": {"files": [FAMILY, APARTMENT], "ruby": "3.2.2", "resstock_revision": "dd25369"},
               "cases": cases}
    (TARGET / "cases.json").write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8",
                                       newline="\n")
    size = (TARGET / "channels.npz").stat().st_size
    print(f"{len(cases)} cases, channels.npz {size} bytes")


if __name__ == "__main__":
    main()
