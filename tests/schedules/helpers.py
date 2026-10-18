"""Shared helpers for the schedule generator tests."""
import numpy as np

TOLERANCE = 1e-6                      # fraction tolerance (ADR 0035)
SAMPLE_HOURS = np.arange(0, 8760, 37)
COMPOSITION_BASIS = {"source_reference_area_normalized": "reference_area", "caller_parent_floor_area": "caller_area"}


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
    return {"schema_version": "2.0.0", "seed": seed, "instances": instances}, keys
