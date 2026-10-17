"""Extract native ComStock sampling draws (uniforms -> selected options) for the sampler test.

Sources: data/schedule-generator/reference/{retail,restaurant}-native-discrete.json,
produced by ComStock sampling/tsv_sampling.py (revision 3c103063) on supplied uniforms.

Usage: python -m scripts.answer_keys.sampling
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ("data/schedule-generator/reference/retail-native-discrete.json",
           "data/schedule-generator/reference/restaurant-native-discrete.json")
TARGET = ROOT / "tests/answer_keys/commercial/sampling-draws.json"


def main() -> None:
    observations = []
    for path in SOURCES:
        for o in json.loads((ROOT / path).read_text(encoding="utf-8"))["observations"]:
            observations.append({"building_type": o["selector"], "uniforms": o["uniforms"],
                                 "selected": o["selected_options"]})
    payload = {"source": {"files": list(SOURCES), "method": "ComStock sampling/tsv_sampling.py @ 3c103063"},
               "observations": observations}
    TARGET.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(TARGET.relative_to(ROOT), len(observations), TARGET.stat().st_size)


if __name__ == "__main__":
    main()
