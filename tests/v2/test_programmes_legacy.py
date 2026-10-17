"""Every migrated programme against the frozen v0.8.0 generator (single instance, seed 42).

Commercial programmes share the operating group name the legacy request used,
so they sample the same operating parameters; residential programmes use R1
streams, so they replay the same draws. Schedules are compared at the
engineering tolerance and amplitudes relative to their value.
"""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules_v2.generator import generate
from atlas_schedules_v2.programmes import load_recipe

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/orchestration/programmes.json.gz"
TOLERANCE = 1e-6
UNIT_EXTENT = {"floor_area": 1, "dwelling_unit": 1, "person": 1, "absolute": 1}


SAMPLE_HOURS = np.arange(0, 8760, 37)


def assert_schedule(test, label, values, packed):
    if "days" in packed:
        expected = np.asarray([packed["days"][i] for i in packed["index"]], dtype=float).reshape(8760)
        test.assertLessEqual(float(np.abs(values - expected).max()), TOLERANCE, label)
        return
    daily = values.reshape(365, 24).sum(axis=1)
    test.assertLessEqual(float(np.abs(daily - np.asarray(packed["daily"])).max()), 24 * TOLERANCE, label)
    test.assertLessEqual(float(np.abs(values[SAMPLE_HOURS] - np.asarray(packed["sample"])).max()), TOLERANCE, label)


def request_for(program_id: str) -> dict:
    recipe = load_recipe(program_id)
    instance = {"key": "unit", "program_id": program_id}
    if recipe["kind"] == "commercial":
        instance["operating_group"] = "group"
    return {"schema_version": "2.0.0", "seed": 42, "instances": [instance]}


@unittest.skipUnless(ANSWER_KEY.exists(), "legacy programme answer key not extracted")
class LegacyProgrammes(unittest.TestCase):
    def test_every_programme(self):
        cases = json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))["cases"]
        for case in cases:
            with self.subTest(program=case["program_id"]):
                bundle = generate(request_for(case["program_id"]), residential_rng="ruby_mt")
                owner = bundle["owners"][0]
                for slot, packed in case["slots"].items():
                    values = np.asarray(bundle["schedules"][owner["schedules"][slot]]["values"])
                    assert_schedule(self, slot, values, packed)
                self.assertEqual([b["slot"] for b in case["bindings"]], [load["slot"] for load in owner["loads"]])
                for expected, actual in zip(case["bindings"], owner["loads"]):
                    self.assertAlmostEqual(actual["amplitude"] / expected["amplitude"], 1, delta=1e-9)
                    self.assertAlmostEqual(actual["annual_total"] / expected["annual_total"], 1, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
