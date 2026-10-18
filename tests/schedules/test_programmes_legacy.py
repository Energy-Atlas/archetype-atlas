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

from atlas_schedules.generator import generate
from atlas_schedules.programmes import load_recipe
from tests.schedules.helpers import assert_schedule

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/orchestration/programmes.json.gz"
UNIT_EXTENT = {"floor_area": 1, "dwelling_unit": 1, "person": 1, "absolute": 1}


def request_for(program_id: str) -> dict:
    recipe = load_recipe(program_id)
    instance = {"key": "unit", "program_id": program_id}
    if recipe["kind"] == "commercial":
        instance["operating_group"] = "group"
    return {"schema_version": "2.0.0", "seed": 42, "instances": [instance]}


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
