"""Build the ResStock housing-characteristics tables the apartment-unit sampler draws from (plan section 8, B2).

Source: sources/resstock-characteristics-lock.json (ResStock dd25369f; fetch with
`python -m scripts.fetch --lock sources/resstock-characteristics-lock.json`). The tables are the
dependency closure of the apartment-unit load and thermostat characteristics.

- Probabilities keep their original values; only rows for other building types are dropped (rows whose
  `Geometry Building Type RECS` or `Geometry Building Type ACS` dependency is not multifamily).
- Geography: `County and PUMA` (drawn given the climate zone), `County`, `PUMA` and `State` are exact
  one-to-one maps apart from the first; they become one list of county-and-PUMA cells per state with each
  cell's county, PUMA and probability given each climate zone. Every table with a county, PUMA or state
  dependency is split into the same per-state files, so a draw within a state and climate zone sums
  county and PUMA out exactly (the sampler draws them as hidden variables and reports neither).
- Each table records its source path and SHA-256 from the lock.

Output: atlas_schedules/data/residential/characteristics/national.json.gz and states/<ST>.json.gz
(gzip, mtime 0; `--check` compares the decompressed JSON).
Usage: python -m scripts.build_resstock_characteristics          (write the tables)
       python -m scripts.build_resstock_characteristics --check  (rebuild and compare)
"""
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "sources/resstock-characteristics-lock.json"
RAW = ROOT / "data/raw/resstock-characteristics"
TARGET = ROOT / "atlas_schedules/data/residential/characteristics"
TABLES = "project_national/housing_characteristics/"
RECS_MULTIFAMILY = ("Multi-Family with 2 - 4 Units", "Multi-Family with 5+ Units")
ACS_MULTIFAMILY = ("2 Unit", "3 or 4 Unit", "5 to 9 Unit", "10 to 19 Unit", "20 to 49 Unit", "50 or more Unit")
GEOGRAPHY_MAPS = ("County and PUMA", "County", "PUMA", "State")
STATE_KEYED = ("County and PUMA", "County", "PUMA", "State")


def read_table(name: str, locked: dict) -> dict:
    path = TABLES + name + ".tsv"
    entry = locked[path]
    text = (RAW / path).read_text(encoding="utf-8")
    lines = [line for line in text.split("\n") if line.strip()]
    header = lines[0].rstrip("\r").split("\t")
    dependencies = [h[len("Dependency="):] for h in header if h.startswith("Dependency=")]
    options = [h[len("Option="):] for h in header if h.startswith("Option=")]
    if header[:len(dependencies) + len(options)] != (["Dependency=" + d for d in dependencies]
                                                      + ["Option=" + o for o in options]):
        raise ValueError(f"{name}: dependency and option columns are not leading and contiguous")
    rows = {}
    for number, line in enumerate(lines[1:], start=2):
        if line.startswith("#"):
            continue
        cells = line.rstrip("\r").split("\t")
        key = tuple(cells[:len(dependencies)])
        if any("|" in value for value in key):
            raise ValueError(f"{name}: dependency value contains the key separator")
        if key in rows:
            raise ValueError(f"{name}: duplicate dependency row at line {number}")
        rows[key] = [float(v) for v in cells[len(dependencies):len(dependencies) + len(options)]]
    return {"name": name, "dependencies": dependencies, "options": options, "rows": rows,
            "source": {"source_id": "resstock", "source_revision": entry["source_revision"], "path": path,
                       "sha256": entry["sha256"]}}


def one_to_one(table: dict) -> dict:
    """{dependency value: option} for a table whose every row puts probability 1 on one option."""
    result = {}
    for key, probabilities in table["rows"].items():
        ones = [i for i, p in enumerate(probabilities) if p == 1.0]
        if len(ones) != 1 or any(p != 0.0 for i, p in enumerate(probabilities) if i != ones[0]):
            raise ValueError(f"{table['name']}: row {key} is not a one-to-one mapping")
        result[key[0]] = table["options"][ones[0]]
    return result


def multifamily(table: dict) -> dict:
    keep = []
    for i, dependency in enumerate(table["dependencies"]):
        if dependency == "Geometry Building Type RECS":
            keep.append((i, RECS_MULTIFAMILY))
        elif dependency == "Geometry Building Type ACS":
            keep.append((i, ACS_MULTIFAMILY))
    rows = {k: v for k, v in table["rows"].items() if all(k[i] in allowed for i, allowed in keep)}
    return dict(table, rows=rows)


def encoded(table: dict, rows: dict) -> dict:
    return {"dependencies": table["dependencies"], "options": table["options"],
            "rows": {"|".join(k): v for k, v in rows.items()}, "source": table["source"]}


def build() -> dict:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    locked = {f["path"]: f for f in lock["files"]}
    tables = {name: read_table(name, locked) for name in lock["dependencies"]}
    for name, table in tables.items():
        if table["dependencies"] != lock["dependencies"][name]:
            raise ValueError(f"{name}: dependencies differ from the lock")

    county_of = one_to_one(tables["County"])
    puma_of = one_to_one(tables["PUMA"])
    state_of_county = one_to_one(tables["State"])
    cells = tables["County and PUMA"]
    states = sorted(set(state_of_county.values()))
    shards = {state: {"cells": [], "tables": {}} for state in states}
    for index, cell in enumerate(cells["options"]):
        county = county_of[cell]
        state = state_of_county[county]
        given_zone = {zone[0]: probabilities[index] for zone, probabilities in cells["rows"].items()
                      if probabilities[index] != 0.0}
        shards[state]["cells"].append({"id": cell, "county": county, "puma": puma_of[cell],
                                       "probability_given_climate_zone": given_zone})

    def state_of(dependency: str, value: str) -> str:
        if dependency == "State":
            return value
        if dependency in ("County", "PUMA"):
            return value.split(",", 1)[0]
        return state_of_county[county_of[value]]  # County and PUMA

    national = {"tables": {}}
    for name in sorted(tables):
        if name in GEOGRAPHY_MAPS:
            continue
        table = multifamily(tables[name])
        geo = [i for i, d in enumerate(table["dependencies"]) if d in STATE_KEYED]
        if not geo:
            national["tables"][name] = encoded(table, table["rows"])
            continue
        split = {state: {} for state in states}
        for key, probabilities in table["rows"].items():
            owners = {state_of(table["dependencies"][i], key[i]) for i in geo}
            if len(owners) != 1:
                raise ValueError(f"{name}: row {key} spans states {owners}")
            split[owners.pop()][key] = probabilities
        for state in states:
            shards[state]["tables"][name] = encoded(table, split[state])
    maps = {"County and PUMA": cells["source"], "County": tables["County"]["source"],
            "PUMA": tables["PUMA"]["source"], "State": tables["State"]["source"]}
    meta = {"source_revision": lock["files"][0]["source_revision"], "lock": "sources/resstock-characteristics-lock.json",
            "multifamily_filter": {"Geometry Building Type RECS": list(RECS_MULTIFAMILY),
                                   "Geometry Building Type ACS": list(ACS_MULTIFAMILY)},
            "geography_sources": maps,
            "interpretation_note": ("Original ResStock probabilities, multifamily rows only. Rows may not sum "
                                    "exactly to one; the sampler normalises each row.")}
    national.update(meta)
    for state in states:
        shards[state].update(meta)
    return {"national.json.gz": national, **{f"states/{state}.json.gz": shards[state] for state in states}}


def serialise(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"


def main() -> None:
    files = build()
    if sys.argv[1:] == ["--check"]:
        stale = [name for name, value in files.items() if not (TARGET / name).exists()
                 or gzip.decompress((TARGET / name).read_bytes()).decode("utf-8") != serialise(value)]
        extra = sorted(str(p.relative_to(TARGET).as_posix()) for p in TARGET.rglob("*.gz")
                       if p.relative_to(TARGET).as_posix() not in files)
        if stale or extra:
            raise SystemExit(f"Characteristic tables differ: {stale[:5]} stale, {extra[:5]} extra")
        print(f"Checked {len(files)} characteristic files")
        return
    for name, value in files.items():
        path = TARGET / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(serialise(value).encode("utf-8"), compresslevel=9, mtime=0))
    size = sum((TARGET / n).stat().st_size for n in files)
    print(f"Wrote {len(files)} characteristic files ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
