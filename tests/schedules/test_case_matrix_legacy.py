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
from tests.schedules.helpers import assert_schedule, rebuilt, translate, without_rebuilt

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
                if rebuilt(legacy.get("program_id")):
                    continue
                compared += 1
                key = keys.get(legacy["instance_key"], legacy["instance_key"])
                with self.subTest(case=case["case_id"], owner=legacy["instance_key"]):
                    owner = owners[key]
                    for slot, packed in legacy["schedules"].items():
                        values = np.asarray(bundle["schedules"][owner["schedules"][slot]]["values"])
                        assert_schedule(self, slot, values, packed)
                    # Loads in demand order (a slot can carry two fuels, e.g. a gas and an electric dryer).
                    expected = [b for b in legacy["bindings"] if b["amplitude"] is not None]
                    self.assertEqual([b["slot"] for b in expected], [load["slot"] for load in owner["loads"]])
                    for binding, load in zip(expected, owner["loads"]):
                        self.assertAlmostEqual(load["amplitude"] / binding["amplitude"], 1, delta=1e-9)
                        self.assertAlmostEqual(load["annual_total"] / binding["annual_total"], 1, delta=1e-9)
            self.assertGreater(compared, 0, case["case_id"])


if __name__ == "__main__":
    unittest.main()
