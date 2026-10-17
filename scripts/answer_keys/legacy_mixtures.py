"""Capture legacy mixture outputs for scenarios built from valid legacy requests.

Scenarios reuse instances from the two A5 case-matrix requests and the M1
example requests (docs/examples/schedule-generator-v1), run on the frozen
v0.8.0 generator (build/task-10/v080-package):
- apartment_building: every apartment unit of one caller building, weighted
  by floor area, whose caller-unit water owners are pulled in whole;
- restaurant_linked_service: a restaurant programme and its linked shared service;
- explicit_service: a Retail programme with a shared service listed explicitly;
- composition_parent: a reference-area Retail source parent, no denominator;
- office_and_dwelling: Medium Office and a ResStock dwelling on a floor-area basis;
- two_dwellings: two ResStock dwellings, no denominator.
Stores the mixed owner's schedules and load bindings.

Usage: python -m scripts.answer_keys.legacy_mixtures
"""
import copy
import gzip
import json
from pathlib import Path
import sys

from scripts.answer_keys.legacy_case_matrix import _pack

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "build/task-10/v080-package"
CASES = PACKAGE / "references/case-matrix"
EXAMPLES = ROOT / "docs/examples/schedule-generator-v1"
TARGET = ROOT / "tests/answer_keys/orchestration/mixtures.json.gz"
EVIDENCE = {"caller": "answer key scenario"}


def _case(name: str) -> dict:
    return json.loads((CASES / f"{name}.request.json").read_text(encoding="utf-8"))


def _base(params: dict, instances: list, realizations: list, mixture: dict) -> dict:
    return {"schema_version": "1.2.0", "resource_set_id": params["resource_set_id"], "calendar": params["calendar"],
            "building_realizations": realizations, "instances": instances, "mixture": mixture}


def _denominator(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit, "evidence": EVIDENCE}


def apartment_building(case1: dict) -> dict:
    params = case1["params"]
    realization = params["building_realizations"][0]
    building = realization["building_realization_id"]
    units = [i for i in params["instances"] if i.get("building_realization_id") == building and i.get("program_id")]
    unit_ids = {u["unit_id"] for u in units}
    water = [i for i in params["instances"] if i.get("building_realization_id") == building
             and not i.get("program_id") and i.get("unit_id") in unit_ids]
    areas = [u["basis_bindings"]["extents"]["floor_area"]["value"] for u in units]
    total = sum(areas)
    mixture = {"program_id": "apartment-building", "composition_id": None,
               "members": [{"instance_key": u["key"], "weight": a / total} for u, a in zip(units, areas)],
               "result_basis": "floor_area", "denominator": _denominator(total, "m2")}
    return _base(params, copy.deepcopy(units + water), [realization], mixture)


def _linked(case2: dict):
    params = case2["params"]
    programme = next(i for i in params["instances"] if i.get("service_links"))
    service_key = next(iter(programme["service_links"].values()))
    service = next(i for i in params["instances"] if i["key"] == service_key)
    return params, copy.deepcopy(programme), copy.deepcopy(service)


def restaurant_linked_service(case2: dict) -> dict:
    params, programme, service = _linked(case2)
    programme["basis_bindings"] = {"extents": {"floor_area": {"value": 200, "unit": "m2", "evidence": EVIDENCE}}}
    mixture = {"program_id": "restaurant", "composition_id": None,
               "members": [{"instance_key": programme["key"], "weight": 1.0}],
               "result_basis": "floor_area", "denominator": _denominator(200, "m2")}
    return _base(params, [programme, service], [], mixture)


def explicit_service(case2: dict) -> dict:
    params = case2["params"]
    service = copy.deepcopy(next(i for i in params["instances"] if i.get("owner_kind") == "physical_service"
                                 and "retail" in i["inputs"]["source_hoo_configuration_id"]))
    configuration = service["inputs"]["source_hoo_configuration_id"]
    programme = copy.deepcopy(next(i for i in params["instances"] if i.get("program_id") and not i.get("service_links")
                                   and i.get("inputs", {}).get("configuration_id") == configuration
                                   and "composition_basis_mode" not in i["inputs"]))
    programme["operating_group"] = service["operating_group"]
    programme["basis_bindings"] = {"extents": {"floor_area": {"value": 300, "unit": "m2", "evidence": EVIDENCE}}}
    mixture = {"program_id": "retail-with-service", "composition_id": None,
               "members": [{"instance_key": programme["key"], "weight": 1.0}],
               "service_members": [{"instance_key": service["key"]}],
               "result_basis": "floor_area", "denominator": _denominator(300, "m2")}
    return _base(params, [programme, service], [], mixture)


def composition_parent(case2: dict) -> dict:
    params = case2["params"]
    parent = copy.deepcopy(next(i for i in params["instances"]
                                if i.get("inputs", {}).get("composition_basis_mode") == "source_reference_area_normalized"))
    mixture = {"program_id": "parent", "composition_id": None, "members": [{"instance_key": parent["key"], "weight": 1.0}]}
    return _base(params, [parent], [], mixture)


def _example(name: str, resource_set_id: str) -> dict:
    params = json.loads((EXAMPLES / f"{name}-request.json").read_text(encoding="utf-8"))["params"]
    params["resource_set_id"] = resource_set_id
    return params


def main() -> None:
    sys.path.insert(0, str(PACKAGE))
    from atlas_schedules import generate  # the legacy package
    case1, case2 = _case("unit-chain-and-caller-closure"), _case("commercial-group-and-source-parent-closure")
    resource = case1["params"]["resource_set_id"]
    scenarios = {
        "apartment_building": (apartment_building(case1), case1["seed"]),
        "restaurant_linked_service": (restaurant_linked_service(case2), case2["seed"]),
        "explicit_service": (explicit_service(case2), case2["seed"]),
        "composition_parent": (composition_parent(case2), case2["seed"]),
        "office_and_dwelling": (_example("mixed-families", resource), 42),
        "two_dwellings": (_example("two-apartments", resource), 42),
    }
    captured = []
    for name, (params, seed) in scenarios.items():
        bundle = generate(params, seed)
        mixed = bundle["constituents"][-1]
        captured.append({
            "scenario": name, "seed": seed, "request": params, "mixed_key": mixed["instance_key"],
            "schedules": {slot: _pack(bundle["schedules"][sid]["values"]) for slot, sid in mixed["schedule_ids"].items()},
            "bindings": [{"slot": bundle["bindings"][i].get("slot"),
                          "amplitude": bundle["bindings"][i].get("effective_magnitude", {}).get("value"),
                          "annual_total": bundle["bindings"][i].get("reference_target", {}).get("total")}
                         for i in mixed["binding_indices"]],
        })
        print(name, mixed["instance_key"], len(mixed["schedule_ids"]), "schedules", flush=True)
    TARGET.write_bytes(gzip.compress(json.dumps({"source": {"package": "v0.8.0"}, "scenarios": captured},
                                                separators=(",", ":"), sort_keys=True).encode("utf-8"), mtime=0))
    print(TARGET.relative_to(ROOT), TARGET.stat().st_size)


if __name__ == "__main__":
    main()
