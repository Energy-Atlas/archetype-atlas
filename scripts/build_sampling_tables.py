"""Build ComStock operating-parameter sampling tables for one or more building types.

Source: data/raw/comstock/sampling/tsvs/tsvs-v33.zip (ComStock revision
3c103063, pinned in sources/schedule-generator-lock.json; fetched with
`python -m scripts.fetch`). Each of the ten tables keeps the rows for the
building type with their original probabilities and 1-based source line.
Start times and durations are converted from hours to seconds; base-to-peak
ratios are fractions, with NA (do not modify) as null.

Usage: python -m scripts.build_sampling_tables strip_mall large_office ...
       python -m scripts.build_sampling_tables --check   (compare with the packaged tables)
"""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

from atlas_schedules_v2.commercial.sampler import DRAW_ORDER

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/comstock/sampling/tsvs/tsvs-v33.zip"
TARGET = ROOT / "atlas_schedules_v2/data/commercial/sampling"
SOURCE_REVISION = "3c103063c0debb177a200dd1df8406b8d0f8d515"
HOURS = {"weekday_start_time", "weekend_start_time", "weekday_duration", "weekend_duration"}
RATIOS = {"plugload_sch_weekday_base_peak_ratio", "plugload_sch_weekend_base_peak_ratio",
          "ltg_sch_weekday_base_peak_ratio", "ltg_sch_weekend_base_peak_ratio"}


def _table(archive: zipfile.ZipFile, parameter: str, building_type: str) -> dict:
    member = f"tsvs-v33/{parameter}.tsv"
    blob = archive.read(member)
    rows = list(csv.reader(io.StringIO(blob.decode("utf-8")), delimiter="\t"))
    header = rows[0]
    dependencies = [h.split("=", 1)[1] for h in header if h.startswith("Dependency=")]
    options = [h.split("=", 1)[1] for h in header if h.startswith("Option=")]
    selected = []
    for line, row in enumerate(rows[1:], start=2):
        if not row or row[0] != building_type:
            continue
        selectors = dict(zip(dependencies, row[:len(dependencies)]))
        probabilities = [float(v) for v in row[len(dependencies):len(dependencies) + len(options)]]
        selected.append({"selectors": selectors, "probabilities": probabilities, "source_row": line})
    table = {"dependencies": dependencies, "options": options, "rows": selected,
             "provenance": {"source_id": "comstock", "source_path": member, "source_revision": SOURCE_REVISION,
                            "source_sha256": hashlib.sha256(blob).hexdigest(), "original_unit": "probability",
                            "field_locator": "source_path#row=<1-based source line>"}}
    if parameter in HOURS:
        table["option_values"] = [float(o) * 3600 for o in options]
        table["option_unit"] = "s"
    elif parameter in RATIOS:
        table["option_values"] = [None if o == "NA" else float(o) for o in options]
        table["option_unit"] = "1"
    return table


def build(building_type: str) -> dict:
    with zipfile.ZipFile(ARCHIVE) as archive:
        return {parameter: _table(archive, parameter, building_type) for parameter in DRAW_ORDER}


def _numeric_view(tables: dict) -> dict:
    return {p: {"dependencies": t["dependencies"], "options": t["options"], "option_values": t.get("option_values"),
                "option_unit": t.get("option_unit"),
                "rows": [(r["selectors"], r["probabilities"], r["source_row"]) for r in t["rows"]]}
            for p, t in tables.items()}


def main() -> None:
    if sys.argv[1:] == ["--check"]:
        for path in sorted(TARGET.glob("*.json")):
            packaged = json.loads(path.read_text(encoding="utf-8"))
            same = _numeric_view(build(path.stem)) == _numeric_view(packaged)
            print(path.stem, "identical" if same else "DIFFERENT")
        return
    for building_type in sys.argv[1:]:
        tables = build(building_type)
        if not all(t["rows"] for t in tables.values()):
            raise SystemExit(f"{building_type}: missing rows in some tables")
        path = TARGET / f"{building_type}.json"
        path.write_text(json.dumps(tables, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(path.relative_to(ROOT), path.stat().st_size)


if __name__ == "__main__":
    main()
