"""Mixture scenarios against the frozen v0.8.0 generator.

Apartment building with caller water pulled in whole, a restaurant with its
linked service, an explicitly listed service, a source parent without a
denominator, an office with a ResStock dwelling, and two dwellings.
"""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules.generator import generate
from tests.schedules.test_case_matrix_legacy import TOLERANCE, translate
from tests.schedules.test_programmes_legacy import assert_schedule

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/orchestration/mixtures.json.gz"


def translate_mixture(legacy: dict, seed: int) -> dict:
    request, _ = translate(legacy, seed)
    mixture = legacy["mixture"]
    v2 = {"program_id": mixture["program_id"],
          "members": [{"instance": m["instance_key"], "weight": m["weight"]} for m in mixture["members"]]}
    if mixture.get("service_members"):
        v2["services"] = [m["instance_key"] for m in mixture["service_members"]]
    if mixture.get("result_basis"):
        v2["result_basis"] = mixture["result_basis"]
        v2["denominator"] = mixture["denominator"]["value"]
    request["mixture"] = v2
    return request


@unittest.skipUnless(ANSWER_KEY.exists(), "legacy mixture answer key not extracted")
class LegacyMixtures(unittest.TestCase):
    def test_every_scenario(self):
        for scenario in json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))["scenarios"]:
            with self.subTest(scenario=scenario["scenario"]):
                bundle = generate(translate_mixture(scenario["request"], scenario["seed"]), residential_rng="ruby_mt")
                mixed = bundle["mixture"]
                self.assertEqual(sorted(mixed["schedules"]), sorted(scenario["schedules"]))
                for slot, packed in scenario["schedules"].items():
                    values = np.asarray(bundle["schedules"][mixed["schedules"][slot]]["values"])
                    assert_schedule(self, slot, values, packed)
                expected = [b for b in scenario["bindings"] if b["amplitude"] is not None]
                self.assertEqual([b["slot"] for b in expected], [load["slot"] for load in mixed["loads"]])
                for binding, load in zip(expected, mixed["loads"]):
                    self.assertAlmostEqual(load["amplitude"] / binding["amplitude"], 1, delta=1e-9)
                    self.assertAlmostEqual(load["annual_total"] / binding["annual_total"], 1, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
