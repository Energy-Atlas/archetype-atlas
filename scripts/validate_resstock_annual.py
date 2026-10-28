"""Check the Python port of the ResStock annual equations against the pinned Ruby methods (plan section 8, B5).

Samples apartment units with the ported characteristics sampler (residential/characteristics.py), turns
them into measure arguments (residential/arguments.py), and runs both
- scripts/recover_residential_inputs.rb under the pinned OpenStudio runtime (executes the pinned
  OpenStudio-HPXML and ResStock methods; no simulation), and
- residential/annual.py,
then compares every end use (kWh, therm, gal/day, sensible and latent fractions).

Inputs: the runtimes of sources/runtime-lock.json (`python -m scripts.runtime --destination <dir>`; a short
directory avoids the Windows path limit), the weather archive of sources/generator-source-lock.json and the
characteristic tables. Writes docs/validation/resstock-annual-equivalence.json and the answer key
tests/answer_keys/resstock-annual.json that tests/schedules/test_resstock_annual.py checks without Ruby.

Usage: python -m scripts.validate_resstock_annual --runtime C:/Users/me/art
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tarfile
import zipfile

from atlas_schedules.residential import characteristics as ch
from atlas_schedules.residential.annual import annual_loads
from atlas_schedules.residential.arguments import expand_properties, lookup_arguments
from atlas_schedules.residential.shapes import fan_months
from atlas_schedules.residential.tables import load_drybulb

ROOT = Path(__file__).resolve().parents[1]
REVISION = "dd25369f41a83a0767aefeeac0b6f8a0b0edd649"
REPORT = ROOT / "docs/validation/resstock-annual-equivalence.json"
ANSWER_KEY = ROOT / "tests/answer_keys/resstock-annual.json"
TOLERANCE = 1e-9
STATES = ("NC", "CA", "NY", "TX", "FL", "IL", "WA", "AZ", "MA", "MN", "GA", "CO")
VINTAGES = (("2000s",), ("2010s",), ("1970s", "1980s", "1990s"), ("<1940", "1940s", "1950s", "1960s"))
AREAS = (40, 60, 80, 110, 150)
HEIGHTS = ("Multi-Family with 5+ Units, 1-3 Stories", "Multi-Family with 5+ Units, 4-7 Stories",
           "Multi-Family with 5+ Units, 8+ Stories")
# Arguments the closure does not sample but the Ruby driver reads; fixed for an apartment unit whose water
# heater and foundation are the building's.
FIXED = {"dhw_fixtures": "Standard, 100% Usage", "dhw_water_heater": "Electricity, Tank, UEF 0.92",
         "geometry_garage_type": "None", "geometry_foundation_type": "Above Apartment", "geometry_unit_level": "Middle"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stations() -> dict:
    """{state: (station id, EPW file name, SHA-256)}: the first packaged TMY3 station of each state."""
    chosen = {}
    for path in sorted((ROOT / "atlas_schedules/data/weather").glob("USA_*.json")):
        state = path.name.split("_")[1]
        if state in STATES and state not in chosen:
            provenance = json.loads(path.read_text(encoding="utf-8"))["provenance"]
            chosen[state] = (path.stem, provenance["source_path"], provenance["source_sha256"])
    missing = sorted(set(STATES) - set(chosen))
    if missing:
        raise SystemExit(f"No packaged weather station for {missing}")
    return chosen


def units() -> list:
    result, seed = [], 0
    for s, state in enumerate(STATES):
        for k in range(20):
            five_plus = k % 4 != 3
            conditions = ch.Conditions(
                state=state, building_type="Multi-Family with 5+ Units" if five_plus else "Multi-Family with 2 - 4 Units",
                floor_area=ch.floor_area_option(AREAS[(k + s) % len(AREAS)]), vintages=VINTAGES[(k + 2 * s) % len(VINTAGES)],
                height=HEIGHTS[k % 3] if five_plus else None, occupants=None if k % 2 else ch.occupants_option(1 + k % 4))
            seed += 1
            try:
                values = ch.sample_characteristics(conditions, seed)
            except Exception as error:  # an empty cell is reported, not hidden
                result.append({"record_id": f"unit-{seed:04d}", "state": state, "skipped": str(error)[:160]})
                continue
            arguments = lookup_arguments(values)
            arguments.update(FIXED)
            arguments["geometry_num_floors_above_grade"] = arguments.get("geometry_num_floors_above_grade", "1")
            result.append({"record_id": f"unit-{seed:04d}", "state": state, "occupants": int(arguments["geometry_unit_num_occupants"]),
                           "bedrooms": int(arguments["geometry_unit_num_bedrooms"]), "arguments": arguments,
                           "characteristics": values})
    return result


def compare(port: list, ruby: list) -> list:
    """Differences between two load lists in upstream order."""
    issues = []
    if [p["end_use"] for p in port] != [r["end_use"] for r in ruby]:
        return [{"end_uses": [[p["end_use"] for p in port], [r["end_use"] for r in ruby]]}]
    for p, r in zip(port, ruby):
        pairs = []
        for key in ("annual_kwh", "annual_therm", "daily_gallons"):
            if key in r:  # the Ruby driver reports gas pool and spa heaters in kWh only
                pairs.append((key, p.get(key), r[key]))
        if "heat_fractions" in r and "sensible_fraction" in p:
            pairs.append(("sensible_fraction", p["sensible_fraction"], r["heat_fractions"]["radiant"] / 0.6))
            pairs.append(("latent_fraction", p["latent_fraction"], r["heat_fractions"]["latent"]))
        for key, a, b in pairs:
            if a is None or b is None or not math.isclose(a, b, rel_tol=TOLERANCE, abs_tol=TOLERANCE):
                issues.append({"end_use": p["end_use"], "field": key, "port": a, "ruby": b})
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=ROOT / "build/runtime")
    parser.add_argument("--work", type=Path, default=ROOT / "build/resstock-annual")
    args = parser.parse_args()
    runtime_lock = json.loads((ROOT / "sources/runtime-lock.json").read_text(encoding="utf-8"))
    entries = {e["name"]: e for e in runtime_lock["archives"]}
    openstudio = args.runtime / "openstudio-windows" / entries["openstudio-windows"]["root"] / "bin/openstudio.exe"
    source = args.runtime / "rs" / entries["rs"]["root"]
    for name, path in (("openstudio-windows", openstudio), ("rs", None)):
        marker = json.loads((args.runtime / name / ".atlas-extraction.json").read_text(encoding="utf-8"))
        if marker["archive_sha256"] != entries[name]["sha256"]:
            raise SystemExit(f"Runtime {name} is not the locked archive")
        if path is not None and digest(path) != marker["files"][path.relative_to(args.runtime / name).as_posix()]:
            raise SystemExit("Modified OpenStudio executable")
        if name == "rs":
            for relative, expected in marker["files"].items():
                if relative.endswith((".rb", ".tsv", ".csv")) and digest(args.runtime / name / relative) != expected:
                    raise SystemExit(f"Modified pinned source {relative}")
    archive_path = args.runtime / "rs.tar.gz"
    if digest(archive_path) != entries["rs"]["sha256"]:
        raise SystemExit("Modified ResStock archive")
    args.work.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path) as tar:
        post = tar.extractfile(f"{entries['rs']['root']}/measures/ResStockArgumentsPostHPXML/measure.rb").read()
    (args.work / "post-hpxml.rb").write_bytes(post)

    weather_lock = json.loads((ROOT / "sources/weather-lock.json").read_text(encoding="utf-8"))
    weather_zip = ROOT / "data/raw/weather/usa-tmy3-epw.zip"
    if digest(weather_zip) != weather_lock["sha256"]:
        raise SystemExit("Weather archive is not the locked one")
    epw = {}
    with zipfile.ZipFile(weather_zip) as z:
        names = z.namelist()
        for state, (station, filename, sha) in stations().items():
            data = z.read(next(n for n in names if n.endswith("/" + filename) or n == filename))
            if hashlib.sha256(data).hexdigest() != sha:
                raise SystemExit(f"Weather member checksum mismatch: {filename}")
            target = args.work / filename
            target.write_bytes(data)
            epw[state] = (target, station)

    sample = units()
    runnable = [u for u in sample if "skipped" not in u]
    inputs = [{"record_id": u["record_id"], "occupants": u["occupants"], "bedrooms": u["bedrooms"],
               "arguments": u["arguments"], "epw_path": str(epw[u["state"]][0])} for u in runnable]
    (args.work / "inputs.json").write_text(json.dumps(inputs, indent=1), encoding="utf-8")
    subprocess.run([str(openstudio), str(ROOT / "scripts/recover_residential_inputs.rb"), str(source),
                    str(args.work / "inputs.json"), str(args.work / "execution.json"), str(args.work / "post-hpxml.rb")],
                   check=True, cwd=ROOT)
    execution = json.loads((args.work / "execution.json").read_text(encoding="utf-8"))
    results = {r["record_id"]: r for r in execution["results"]}

    report, keys = [], []
    for unit in runnable:
        ruby = results[unit["record_id"]]
        months = fan_months(load_drybulb(epw[unit["state"]][1]))
        expanded = expand_properties(unit["arguments"])
        port = annual_loads(expanded, unit["occupants"], unit["bedrooms"], ruby["source_cfa_ft2"], months,
                            unit_type=expanded["geometry_facility_type"], garage_area_ft2=ruby["source_garage_area_ft2"])
        ruby_loads = [{k: v for k, v in load.items() if k not in ("host", "method", "fuel", "target_temperature_degC")}
                      for load in ruby["loads"] if load["end_use"] != "hot_water_fixtures"]
        issues = compare(port, ruby_loads)
        report.append({"record_id": unit["record_id"], "state": unit["state"], "issues": issues})
        keys.append({"record_id": unit["record_id"], "arguments": unit["arguments"], "occupants": unit["occupants"],
                     "bedrooms": unit["bedrooms"], "cfa_ft2": ruby["source_cfa_ft2"], "fan_months": months,
                     "ruby_loads": ruby_loads})
    failed = [r for r in report if r["issues"]]
    end_uses = sorted({load["end_use"] for k in keys for load in k["ruby_loads"]})
    summary = {"schema_version": "1.0.0", "source_revision": REVISION, "runtime_version": execution["runtime_version"],
               "tolerance_relative": TOLERANCE, "units_sampled": len(sample), "units_compared": len(report),
               "units_skipped": [u for u in sample if "skipped" in u], "units_failed": len(failed),
               "end_uses": end_uses, "fixed_arguments": FIXED, "results": report}
    REPORT.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    ANSWER_KEY.write_text(json.dumps({"schema_version": "1.0.0", "source_revision": REVISION,
                                      "runtime_version": execution["runtime_version"], "units": keys},
                                     separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(report)} units compared, {len(failed)} with differences, {len(summary['units_skipped'])} skipped; "
          f"end uses {end_uses}")
    for row in failed[:10]:
        print(row["record_id"], row["issues"][:3])


if __name__ == "__main__":
    main()
