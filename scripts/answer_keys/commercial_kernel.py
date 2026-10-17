"""Extract the compact commercial kernel answer key from the native capture.

Source: data/schedule-generator/commercial-vectors.json, captured by
scripts/reference_commercial.rb on OpenStudio 3.10.0 with openstudio-standards
0.8.6 (see that file's provenance block). Keeps only what the kernel test
needs: rule sets, slot modes, the occupancy carrier, sampled operating values
and the native final hourly channels.

Usage: python -m scripts.answer_keys.commercial_kernel
"""
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/schedule-generator/commercial-vectors.json"
TARGET = ROOT / "tests/answer_keys/commercial/kernel-cases.json.gz"
RULE_FIELDS = ("day_types", "start_date", "end_date", "values")


def _rules(schedule: dict) -> dict:
    return {"rules": [{k: rule[k] for k in RULE_FIELDS} for rule in schedule["rules"]]}


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    cases = []
    for case in data["cases"]:
        context = case["source_context"]
        cases.append({
            "case_id": case["case_id"],
            "configuration_id": context["configuration_id"],
            "slot_modes": context["slot_modes"],
            "schedules": {name: _rules(case["schedules"][name]) for name in context["slot_modes"]},
            "people": [{"schedule_id": p["schedule"]["id"], "schedule": _rules(p["schedule"]),
                        "people": p["nominal_people"]}
                       for p in context["occupancy_aggregation"]["constituents"]],
            "operating": case["operating"]["effective_values"],
            "expected": case["channels"],
        })
    payload = {
        "source": {"path": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
                   "openstudio": "3.10.0", "openstudio_standards": "0.8.6",
                   "ruby": data["ruby_description"]},
        "cases": cases,
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    TARGET.write_bytes(gzip.compress(blob, mtime=0))
    print(f"{TARGET.relative_to(ROOT)}: {len(cases)} cases, {TARGET.stat().st_size} bytes")


if __name__ == "__main__":
    main()
