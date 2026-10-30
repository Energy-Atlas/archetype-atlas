"""Record generator 3.0.0 bundles of a fixed sample of requests, as the equivalence key for generator 4.0.0 (ADR 0051).

python -m scripts.capture.generator_3_0_0_bundles        # writes tests/answer_keys/orchestration/generator-3-0-0-bundles.json.gz

Run once under generator 3.0.0 (the packaged recipes, `atlas_schedules/data/recipes`), before stage P3
deleted them. The sample, in packaged recipe order: every tenth commercial recipe without shared
services and every twenty-fifth with them (linked to their services), every second fixed recipe, every
tenth composition parent, every apartment unit (two residents, Hickory NC, climate zone 4A, 80 m2),
every ResStock dwelling, every tenth shared-service variant, and the four example requests. Seed 42,
the default occupant mix. Each case keeps its 3.0.0 request (definition IDs; generator 4.0.0 translates
them through the release's definition map) and, per owner, the loads, controls and extent exactly and
each schedule's unit, sum, maximum and every 37th hour. Generator 4.0.0 must reproduce every value
(tests/schedules/test_generator_3_0_0_equivalence.py): the bundle differs only in the fields 4.0.0
adds (`release`, the owners' `values`) and the versions.
"""
import gzip
import json
import math
from pathlib import Path
import time

import numpy as np

from atlas_schedules import __version__, generate
from atlas_schedules.programmes import load_recipe, required_services

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "atlas_schedules/data"
EXAMPLES = ROOT / "docs/examples/schedule-generator"
OUTPUT = ROOT / "tests/answer_keys/orchestration/generator-3-0-0-bundles.json.gz"
SAMPLE_HOURS = list(range(0, 8760, 37))
LOCATION = {"state": "NC", "latitude": 35.741, "longitude": -81.389, "utc_offset": -5, "climate_zone": "4A"}
SEED = 42


def service(service_id):
    return json.loads((DATA / "services" / f"{service_id}.json").read_text(encoding="utf-8"))


def configuration_of(recipe):
    if recipe["kind"] == "composition":
        recipe = load_recipe(recipe["composition"]["members"][0][0])
    return recipe["commercial"]["configuration_id"]


def instance(recipe):
    out = {"key": "unit", "program_id": recipe["program_id"]}
    if recipe["kind"] in ("commercial", "composition"):
        out["operating_group"] = "building"
    if recipe["kind"] == "apartment_unit":
        out.update(residents=2, location=LOCATION, extent={"floor_area": 80})
    return out


def request_for(recipe):
    instances = [instance(recipe)]
    linked = required_services(recipe)
    if linked:
        configuration = configuration_of(recipe)
        links = {}
        for index, service_id in enumerate(linked):
            key = f"service-{index}"
            links[service_id] = key
            instances.append({"key": key, "service_id": service_id, "configuration_id": configuration, "physical_id": key,
                              "extent": {service(service_id)["demand"]["basis"]: 1.0}, "operating_group": "building"})
        instances[0]["service_links"] = links
    return {"schema_version": "3.0.0", "seed": SEED, "instances": instances}


def sample_requests():
    recipes = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((DATA / "recipes").glob("*.json"))]
    by_kind = {}
    for recipe in recipes:
        by_kind.setdefault(recipe["kind"], []).append(recipe)
    picked = []
    commercial = by_kind["commercial"]
    picked += [r for r in commercial if not r["required_services"]][::10]
    picked += [r for r in commercial if r["required_services"]][::25]
    picked += by_kind["fixed"][::2]
    picked += by_kind["composition"][::10]
    picked += by_kind["apartment_unit"]
    picked += by_kind["residential"]
    cases = [(f"{r['kind']}/{r['program_id']}", request_for(r)) for r in picked if r.get("slots") or r["kind"] in ("composition", "apartment_unit")]
    variants = []
    for path in sorted((DATA / "services").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        for configuration_id in sorted(record["configurations"]):
            variants.append((record["service_id"], configuration_id, record["demand"]["basis"]))
    for service_id, configuration_id, basis in variants[::10]:
        cases.append((f"service/{service_id}@{configuration_id}",
                      {"schema_version": "3.0.0", "seed": SEED, "instances": [
                          {"key": "water", "service_id": service_id, "configuration_id": configuration_id,
                           "physical_id": "fixture", "extent": {basis: 1.0}, "operating_group": "building"}]}))
    for path in sorted(EXAMPLES.glob("*.json")):
        cases.append((f"example/{path.stem}", json.loads(path.read_text(encoding="utf-8"))))
    return cases


def packed_owner(owner, bundle):
    schedules = {}
    for slot, sid in owner["schedules"].items():
        entry = bundle["schedules"][sid]
        values = np.asarray(entry["values"], dtype=float)
        schedules[slot] = {"unit": entry["unit"], "sum": float(values.sum()), "max": float(values.max()),
                           "sampled": values[SAMPLE_HOURS].tolist()}
    return {k: v for k, v in owner.items() if k != "schedules"} | {"schedules": schedules}


def main():
    started = time.time()
    cases = []
    for case_id, request in sample_requests():
        bundle = generate(request)
        cases.append({"id": case_id, "request": request,
                      "owners": [packed_owner(o, bundle) for o in bundle["owners"]],
                      "mixture": packed_owner(bundle["mixture"], bundle) if bundle["mixture"] else None,
                      "operating_groups": bundle["operating_groups"], "unit_seeds": bundle["unit_seeds"]})
    key = {"generator_version": __version__, "schema_version": "3.0.0", "seed": SEED, "sample_hours": SAMPLE_HOURS,
           "cases": cases}
    text = json.dumps(key, separators=(",", ":"), allow_nan=False)
    if any(not math.isfinite(v) for c in cases for o in c["owners"] for s in o["schedules"].values() for v in s["sampled"]):
        raise SystemExit("non-finite sampled value")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(OUTPUT, "wb", mtime=0) as out:
        out.write(text.encode("utf-8"))
    print(f"{len(cases)} cases, {OUTPUT.stat().st_size / 1e6:.2f} MB, {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
