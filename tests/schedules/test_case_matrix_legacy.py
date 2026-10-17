"""The two A5 case-matrix requests against the frozen v0.8.0 generator.

Each legacy v1.2 request is translated to a v2 request (same keys, extents,
groups, seeds, R1 residential streams). Legacy caller-water owners were
explicit instances; v2 creates them as "<unit key>/water", so they are matched
through their building and unit.
"""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules.generator import generate

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/orchestration/case-matrix.json.gz"
TOLERANCE = 1e-6
SAMPLE_HOURS = np.arange(0, 8760, 37)
COMPOSITION_BASIS = {"source_reference_area_normalized": "reference_area", "caller_parent_floor_area": "caller_area"}


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


@unittest.skipUnless(ANSWER_KEY.exists(), "legacy case-matrix answer key not extracted")
class LegacyCaseMatrix(unittest.TestCase):
    def check_schedule(self, label: str, values: np.ndarray, packed: dict) -> None:
        if "days" in packed:
            expected = np.asarray([packed["days"][i] for i in packed["index"]], dtype=float).reshape(8760)
            self.assertLessEqual(float(np.abs(values - expected).max()), TOLERANCE, label)
            return
        daily = values.reshape(365, 24).sum(axis=1)
        self.assertLessEqual(float(np.abs(daily - np.asarray(packed["daily"])).max()), 24 * TOLERANCE, label)
        self.assertLessEqual(float(np.abs(values[SAMPLE_HOURS] - np.asarray(packed["sample"])).max()), TOLERANCE, label)

    def test_both_cases(self):
        cases = json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))["cases"]
        for case in cases:
            request, keys = translate(case["request"], case["seed"])
            bundle = generate(request, residential_rng="ruby_mt")
            owners = {o["key"]: o for o in bundle["owners"]}
            for legacy in case["owners"]:
                key = keys.get(legacy["instance_key"], legacy["instance_key"])
                with self.subTest(case=case["case_id"], owner=legacy["instance_key"]):
                    owner = owners[key]
                    for slot, packed in legacy["schedules"].items():
                        values = np.asarray(bundle["schedules"][owner["schedules"][slot]]["values"])
                        self.check_schedule(slot, values, packed)
                    # Loads in demand order (a slot can carry two fuels, e.g. a gas and an electric dryer).
                    expected = [b for b in legacy["bindings"] if b["amplitude"] is not None]
                    self.assertEqual([b["slot"] for b in expected], [load["slot"] for load in owner["loads"]])
                    for binding, load in zip(expected, owner["loads"]):
                        self.assertAlmostEqual(load["amplitude"] / binding["amplitude"], 1, delta=1e-9)
                        self.assertAlmostEqual(load["annual_total"] / binding["annual_total"], 1, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
