"""Native residential-dominance check for every packaged commercial configuration.

For each family, template and view, scripts/capture/occupancy_dominance.rb
loads the template's prototype geometry, gives each space the People the
builder assumes (floor area x the definition's occupancy density for its
standards space type), and records native design-people totals for residential
and non-residential spaces (openstudio-standards space_residential?, numberOfPeople
x multiplier). scripts/answer_keys/occupancy_dominance.py turns them into a key
that tests compare with the packaged configurations.

Usage: python -m scripts.capture.occupancy_dominance OUT_DIR
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.build_family_recipes import (SAMPLING, TEMPLATES, _known_positive, _load, configuration_id,
                                          geometry_file, source_programmes)

HARNESS = Path(__file__).resolve().parent / "occupancy_dominance.rb"
LOCKED = Path(__file__).resolve().parents[2] / "build/task-10/native-warehouse-20261014-01"


def cases() -> list:
    items = []
    for building_type in SAMPLING:
        for template in TEMPLATES:
            for view in ("source", "reviewed"):
                densities = {}
                for space_type, programme in source_programmes(building_type, template, view).items():
                    occupancy = _load(programme, "occupancy")
                    if _known_positive(occupancy):
                        densities[space_type] = occupancy["value"]
                items.append({"case_id": configuration_id(building_type, template, view),
                              "geometry_path": str(geometry_file(building_type, template)), "densities": densities})
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--source", type=Path, default=LOCKED / "source")
    parser.add_argument("--openstudio", type=Path,
                        default=LOCKED / "runtime/OpenStudio-3.10.0+86d7e215a1-Windows/bin/openstudio.exe")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    input_path, output_path = args.out / "dominance-input.json", args.out / "dominance-native.json"
    input_path.write_text(json.dumps(cases()) + "\n", encoding="utf-8", newline="\n")
    result = subprocess.run([str(args.openstudio), str(HARNESS), str(args.source), str(input_path), str(output_path)],
                            capture_output=True, text=True, env={**os.environ, "TZ": "UTC"})
    (args.out / "dominance.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        sys.exit(f"harness failed ({result.returncode}); see dominance.log")
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
