"""Copy the ComStock v33 conditional sampling tables into atlas_schedules_v2/data.

Input: the compiled v0.8.0 generator package (data/generator-releases/v0.8.0/
generator.zip, sha256 bb1eb96b..., unpacked to build/task-10/v080-package).
The tables are the ComStock tsvs-v33 rows for one building type each, with
their original cells and provenance; this keeps the fields the sampler reads.

Usage: python -m scripts.migrate.sampling_tables
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "build/task-10/v080-package/atlas_schedules/data/commercial"
TARGET = ROOT / "atlas_schedules_v2/data/commercial/sampling"
BUILDING_TYPES = ("medium_office", "small_office", "warehouse", "retail",
                  "full_service_restaurant", "quick_service_restaurant")
KEEP = ("dependencies", "options", "option_values", "option_unit", "provenance")


def main() -> None:
    from atlas_schedules_v2.commercial.sampler import DRAW_ORDER
    for building_type in BUILDING_TYPES:
        prefix = "" if building_type == "medium_office" else building_type + "__"
        tables = {}
        for parameter in DRAW_ORDER:
            table = json.loads((SOURCE / f"{prefix}{parameter}.json").read_text(encoding="utf-8"))
            compact = {k: table[k] for k in KEEP if k in table}
            compact["rows"] = [{"selectors": r["selectors"], "probabilities": r["probabilities"],
                                "source_row": r["source_row"]} for r in table["rows"]]
            tables[parameter] = compact
        TARGET.mkdir(parents=True, exist_ok=True)
        path = TARGET / f"{building_type}.json"
        path.write_text(json.dumps(tables, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(path.relative_to(ROOT), path.stat().st_size)


if __name__ == "__main__":
    main()
