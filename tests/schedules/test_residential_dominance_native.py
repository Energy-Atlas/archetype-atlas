"""The residential-dominant (inverted rule-day) path against native captures.

openstudio-standards infers hours from residential occupancy and inverts its
rule days when residential spaces hold most design people. Two checks:
- every packaged configuration's dominance flag and dominant-group people
  match native totals on real prototype geometry;
- residential-dominant cases (real guest- and patient-room carriers, and
  crafted rule sets that stress which profile stays the uninverted default)
  match native final channels with inversion on.
"""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules.commercial.transform import Slot, transform
from atlas_schedules.programmes import load_configuration
from tests.schedules.helpers import TOLERANCE, unpack_days

KEYS = Path(__file__).resolve().parents[1] / "answer_keys/commercial"


class OccupancyDominance(unittest.TestCase):
    def test_configurations_follow_native_dominance(self):
        rows = json.loads((KEYS / "occupancy-dominance.json").read_text(encoding="utf-8"))["configurations"]
        self.assertEqual(len(rows), 150)
        for configuration_id, row in rows.items():
            configuration = load_configuration(configuration_id)
            with self.subTest(configuration=configuration_id):
                self.assertEqual(configuration["invert_rule_days"], row["residential"] > row["non_residential"])
                people = sum(count for _, count in configuration["people"])
                self.assertAlmostEqual(people, row["dominant_people"], delta=1e-9 * max(people, 1))


class ResidentialDominantHours(unittest.TestCase):
    def test_inverted_hours_match_native_output(self):
        cases = json.loads(gzip.decompress((KEYS / "residential-dominant.json.gz").read_bytes()))["cases"]
        for case in cases:
            people = [("carrier", {"rules": case["carrier"]["rules"]}, case["carrier"]["people"])]
            slots = {name: Slot({"rules": s["rules"]}, s["mode"]) for name, s in case["slots"].items()}
            result = transform(slots, people, case["operating"], invert_rule_days=True, flat_days="native")
            for name in slots:
                with self.subTest(case=case["case_id"], slot=name):
                    difference = np.abs(result[name] - unpack_days(case["expected"][name])).max()
                    self.assertLessEqual(float(difference), TOLERANCE)


if __name__ == "__main__":
    unittest.main()
