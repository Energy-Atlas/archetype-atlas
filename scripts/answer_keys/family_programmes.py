"""Extract the native programme captures of the newer families as an answer key.

Source: build/task-10/native-family-programmes-20261017/<family>-native.json,
written by `python -m scripts.capture.commercial_families` (OpenStudio 3.10,
openstudio-standards 0.8.6, ComStock measures; one template per family, both
views, seeds 42 and 51). Per case: configuration, seed, programme (or the
configuration's water services), the sampled operating parameters and each
slot's final hourly values.

Usage: python -m scripts.answer_keys.family_programmes
"""
import gzip
import json
from pathlib import Path

from scripts.capture.commercial_families import FAMILIES, cases_for

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "build/task-10/native-family-programmes-20261017"
TARGET = ROOT / "tests/answer_keys/commercial/family-programmes.json.gz"


def pack_days(values: list) -> dict:
    """8760 values -> {"days": distinct 24-value days, "index": 365 day indices}."""
    days, lookup, index = [], {}, []
    for day in range(365):
        key = tuple(values[24 * day:24 * (day + 1)])
        if key not in lookup:
            lookup[key] = len(days)
            days.append(list(key))
        index.append(lookup[key])
    return {"days": days, "index": index}


def main() -> None:
    cases = []
    for building_type in FAMILIES:
        native = {c["case_id"]: c for c in
                  json.loads((CAPTURE / f"{building_type}-native.json").read_text(encoding="utf-8"))["cases"]}
        for item in cases_for(building_type):
            configuration_id, rest = item["case_id"].split("@")
            seed, subject = rest.split("/")
            operating = {name: {"modify": p["modify"], "value": p["value"]}
                         for name, p in item["operating"]["effective_values"].items()}
            cases.append({"case_id": item["case_id"], "configuration_id": configuration_id, "seed": int(seed),
                          "subject": subject, "operating": operating,
                          "expected": {slot: pack_days(values) for slot, values in native[item["case_id"]]["channels"].items()}})
    payload = {"source": {"capture": str(CAPTURE.relative_to(ROOT)), "openstudio": "3.10.0",
                          "openstudio_standards": "0.8.6", "templates": FAMILIES, "seeds": [42, 51]},
               "cases": cases}
    TARGET.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"), mtime=0))
    print(TARGET.relative_to(ROOT), len(cases), "cases", TARGET.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
