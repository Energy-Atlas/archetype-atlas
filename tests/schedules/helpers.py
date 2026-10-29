"""Shared helpers for the schedule generator tests."""
import json
from pathlib import Path

import numpy as np

from atlas_schedules import programmes
from atlas_schedules.release import definition_map, translate as release_ids

TOLERANCE = 1e-6                      # fraction tolerance (ADR 0035)
SAMPLE_HOURS = np.arange(0, 8760, 37)
# Rebuilt from the definitions after the legacy keys were captured (new configuration
# ids, water as linked services); the native family keys check them instead.
REBUILT_BUILDING_TYPES = frozenset({"MediumOffice", "SmallOffice", "Warehouse"})
# DOE Ref recipes, configurations and services built from the frozen definitions and replaced in stage X1.2
# (ADR 0046) by recipes written from release 2.0.0; the keys keep their captures, the tests skip them.
RETIRED = json.loads((Path(__file__).resolve().parents[1] / "answer_keys/retired-doe-ref.json").read_text(encoding="utf-8"))
RETIRED_IDS = frozenset(RETIRED["program_ids"] + RETIRED["configuration_ids"] + RETIRED["service_ids"])
COMPOSITION_BASIS = {"source_reference_area_normalized": "reference_area", "caller_parent_floor_area": "caller_area"}


def release_key(program_id: str) -> tuple:
    """(release program ID, view) of a definition program ID the keys were captured with (ADR 0049)."""
    entry = definition_map()["programs"].get(program_id)
    return (entry["program_id"], entry["values"]) if entry else (program_id, None)


def release_service(service_id: str) -> str:
    return definition_map()["services"].get(service_id, service_id)


def load_recipe(program_id: str, values: str | None = None) -> dict:
    """A recipe by definition or release program ID."""
    release_id, view = release_key(program_id)
    return programmes.load_recipe(release_id, values or view)


def load_service(service_id: str) -> dict:
    return programmes.load_service(release_service(service_id))


def legacy_fixed_slot(owner: dict, slot: str) -> bool:
    """A legacy key's zero-density occupancy slot of a 90.1 apartment-building fixed programme, which the release
    values leave out (ADR 0049 section 3); any other missing slot still fails."""
    if slot in owner["schedules"] or slot != "occupants" or not owner.get("program_id"):
        return False
    return programmes.load_recipe(owner["program_id"], owner["values"])["kind"] == "fixed"


def members(recipe: dict) -> list:
    """[(member recipe, reference area)] of a composition recipe."""
    composition = recipe["composition"]
    return [(programmes.load_recipe(pid, values), area)
            for (pid, area), values in zip(composition["members"], composition["member_values"])]


def unpack_days(packed: dict) -> np.ndarray:
    return np.asarray([packed["days"][i] for i in packed["index"]], dtype=float).reshape(8760)


def assert_schedule(test, label, values, packed):
    if "days" in packed:
        expected = np.asarray([packed["days"][i] for i in packed["index"]], dtype=float).reshape(8760)
        test.assertLessEqual(float(np.abs(values - expected).max()), TOLERANCE, label)
        return
    daily = values.reshape(365, 24).sum(axis=1)
    test.assertLessEqual(float(np.abs(daily - np.asarray(packed["daily"])).max()), 24 * TOLERANCE, label)
    test.assertLessEqual(float(np.abs(values[SAMPLE_HOURS] - np.asarray(packed["sample"])).max()), TOLERANCE, label)


def assert_binding(test, load, binding, source_value=None):
    """A load against a legacy binding. ResStock loads (per dwelling) keep their annual totals, so both
    match. Every other load binds its source magnitude since O15 while the legacy generator fitted an
    amplitude to a fixed total: both bindings scale the same generated shape, so total / amplitude
    (its integral) must agree, and the amplitude is the source value where the test knows it."""
    if load["unit"].endswith("/dwelling"):
        test.assertAlmostEqual(load["amplitude"] / binding["amplitude"], 1, delta=1e-9)
        test.assertAlmostEqual(load["annual_total"] / binding["annual_total"], 1, delta=1e-9)
        return
    if source_value is not None:
        test.assertAlmostEqual(load["amplitude"] / source_value, 1, delta=1e-12)
    if binding["annual_total"] == 0 or binding["amplitude"] == 0:
        test.assertEqual(load["annual_total"], 0)
        return
    ratio = (load["annual_total"] / binding["annual_total"]) / (load["amplitude"] / binding["amplitude"])
    test.assertAlmostEqual(ratio, 1, delta=1e-9)


def translate(legacy: dict, seed: int) -> tuple[dict, dict]:
    """(v2 request, {legacy owner key: v2 owner key})."""
    units = {}
    for instance in legacy["instances"]:
        if instance.get("unit_id") and instance.get("program_id"):
            units[(instance["building_realization_id"], instance["unit_id"])] = instance["key"]
    instances, keys = [], {}
    for instance in legacy["instances"]:
        bindings = instance.get("basis_bindings", {})
        extent = {basis: e["value"] for basis, e in bindings.get("extents", {}).items()}
        inputs = instance.get("inputs", {})
        if instance.get("physical_binding_kind") == "caller_unit_prototype_density_fixed_dhw":
            unit_key = units[(instance["building_realization_id"], instance["unit_id"])]
            keys[instance["key"]] = unit_key + "/water"
            continue
        keys[instance["key"]] = instance["key"]
        if instance.get("owner_kind") == "physical_service":
            instances.append({"key": instance["key"], "service_id": instance["source_service_id"],
                              "configuration_id": inputs["source_hoo_configuration_id"],
                              "physical_id": instance["physical_id"], "extent": extent,
                              "operating_group": instance.get("operating_group")})
            continue
        v2 = {"key": instance["key"], "program_id": instance["program_id"]}
        if extent:
            v2["extent"] = extent
        if "multiplicity" in bindings:
            v2["multiplicity"] = bindings["multiplicity"]
        if instance.get("operating_group"):
            v2["operating_group"] = instance["operating_group"]
        if "N" in inputs:
            v2["residents"] = inputs["N"]
            if inputs["N"] > 0:
                v2["location"] = {"state": inputs["state"], "latitude": inputs["latitude"],
                                  "longitude": inputs["longitude"], "utc_offset": inputs["time_zone_utc_offset"]}
        if instance.get("service_links"):
            v2["service_links"] = instance["service_links"]
        if "composition_basis_mode" in inputs:
            v2["composition_basis"] = COMPOSITION_BASIS[inputs["composition_basis_mode"]]
        instances.append(v2)
    # Native and legacy keys used ResStock's national occupant-type shares; their definition IDs are written as
    # release IDs and views.
    return release_ids({"schema_version": "3.0.0", "seed": seed, "occupancy": {"mix": "national"},
                        "instances": instances}), keys


def retired(*texts) -> bool:
    """Whether a case names a DOE Ref recipe, configuration or service replaced in stage X1.2."""
    return any(i in text for text in texts if text for i in RETIRED_IDS)


def rebuilt(program_id: str | None) -> bool:
    """Whether a programme belongs to a family the legacy keys no longer describe (apartment units are
    ResStock units since plan section 8, B7)."""
    if program_id is None:
        return False
    if program_id in RETIRED_IDS:
        return True
    recipe = load_recipe(program_id)
    return recipe["kind"] == "apartment_unit" or recipe["source"].get("building_type") in REBUILT_BUILDING_TYPES


def without_rebuilt(legacy_request: dict) -> dict:
    """The legacy request without instances of rebuilt families or retired services, nor the water of removed units."""
    removed = {(i.get("building_realization_id"), i.get("unit_id")) for i in legacy_request["instances"]
               if i.get("unit_id") and rebuilt(i.get("program_id"))}
    return {**legacy_request, "instances": [
        i for i in legacy_request["instances"] if not rebuilt(i.get("program_id")) and not retired(i.get("source_service_id"))
        and not (i.get("physical_binding_kind") == "caller_unit_prototype_density_fixed_dhw"
                 and (i.get("building_realization_id"), i.get("unit_id")) in removed)]}
