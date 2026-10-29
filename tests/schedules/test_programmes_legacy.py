"""Every migrated programme against the frozen v0.8.0 generator (single instance, seed 42).

Commercial programmes share the operating group name the legacy request used,
so they sample the same operating parameters; residential programmes use R1
streams, so they replay the same draws. Schedules are compared at the
engineering tolerance and loads with `assert_binding` (source magnitudes since O15).
"""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules.generator import generate
from tests.schedules.helpers import assert_binding, assert_schedule, legacy_fixed_slot, load_recipe, rebuilt, release_key

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/orchestration/programmes.json.gz"
UNIT_EXTENT = {"floor_area": 1, "dwelling_unit": 1, "person": 1, "absolute": 1}


def request_for(program_id: str) -> dict:
    recipe = load_recipe(program_id)
    release_id, values = release_key(program_id)
    instance = {"key": "unit", "program_id": release_id, **({"values": values} if values else {})}
    if recipe["kind"] == "commercial":
        instance["operating_group"] = "group"
    return {"schema_version": "3.0.0", "seed": 42, "occupancy": {"mix": "national"}, "instances": [instance]}


class LegacyProgrammes(unittest.TestCase):
    def test_every_programme(self):
        cases = json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))["cases"]
        for case in cases:
            if rebuilt(case["program_id"]):
                continue
            with self.subTest(program=case["program_id"]):
                bundle = generate(request_for(case["program_id"]), residential_rng="ruby_mt", flat_days="native")
                owner = bundle["owners"][0]
                for slot, packed in case["slots"].items():
                    if legacy_fixed_slot(owner, slot):
                        continue
                    values = np.asarray(bundle["schedules"][owner["schedules"][slot]]["values"])
                    assert_schedule(self, slot, values, packed)
                self.assertEqual([b["slot"] for b in case["bindings"]], [load["slot"] for load in owner["loads"]])
                demands = load_recipe(case["program_id"])["demands"]
                for expected, actual, demand in zip(case["bindings"], owner["loads"], demands):
                    assert_binding(self, actual, expected, demand.get("value"))


if __name__ == "__main__":
    unittest.main()
