"""The two A5 case-matrix requests against the frozen v0.8.0 generator.

Each legacy v1.2 request is translated to a v2 request (same keys, extents,
groups, seeds, R1 residential streams). Legacy caller-water owners were
explicit instances; v2 creates them as "<unit key>/water", so they are matched
through their building and unit. A composition parent's mixed loads weight its
members by their amplitudes, which are source magnitudes since O15 (the legacy
generator fitted them), so only its people heat and setpoints are compared;
test_request checks the mixed loads against the members.
"""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules.generator import generate
from atlas_schedules.programmes import load_recipe
from tests.schedules.helpers import assert_binding, assert_schedule, rebuilt, retired, translate, without_rebuilt

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/orchestration/case-matrix.json.gz"


class LegacyCaseMatrix(unittest.TestCase):
    def test_both_cases(self):
        cases = json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))["cases"]
        for case in cases:
            request, keys = translate(without_rebuilt(case["request"]), case["seed"])
            bundle = generate(request, residential_rng="ruby_mt", flat_days="native")
            owners = {o["key"]: o for o in bundle["owners"]}
            compared = 0
            for legacy in case["owners"]:
                if rebuilt(legacy.get("program_id")) or retired(legacy["instance_key"]) or legacy["instance_key"] not in keys:
                    continue  # rebuilt families, DOE Ref services replaced in stage X1.2, and the water of removed units
                compared += 1
                key = keys.get(legacy["instance_key"], legacy["instance_key"])
                with self.subTest(case=case["case_id"], owner=legacy["instance_key"]):
                    owner = owners[key]
                    parent = legacy.get("program_id") and load_recipe(legacy["program_id"])["kind"] == "composition"
                    for slot, packed in legacy["schedules"].items():
                        if parent and slot.startswith("load/"):
                            continue
                        values = np.asarray(bundle["schedules"][owner["schedules"][slot]]["values"])
                        assert_schedule(self, slot, values, packed)
                    # Loads in demand order (a slot can carry two fuels, e.g. a gas and an electric dryer).
                    expected = [b for b in legacy["bindings"] if b["amplitude"] is not None]
                    self.assertEqual([b["slot"] for b in expected], [load["slot"] for load in owner["loads"]])
                    if parent:
                        continue
                    for binding, load in zip(expected, owner["loads"]):
                        assert_binding(self, load, binding)
            self.assertGreater(compared, 0, case["case_id"])


if __name__ == "__main__":
    unittest.main()
