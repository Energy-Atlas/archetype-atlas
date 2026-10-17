"""New commercial families against their native 2013 SOURCE pilots.

The family builder's People topology (geometry floor area x definition density,
dominant group) must match native per space, and the kernel must reproduce the
native final values of each shared water service from the definition schedule.
"""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules_v2.commercial.transform import Slot, transform
from scripts.build_family_recipes import occupancy_carrier, services
from tests.v2.test_commercial_families import FRACTION_TOLERANCE, unpack_days

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/commercial/family-pilots.json.gz"
DEFINITIONS = Path(__file__).resolve().parents[2] / "data/definition-releases/v0.1.1/schedules.json"


@unittest.skipUnless(DEFINITIONS.exists(), "frozen definitions not present")
class FamilyPilots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))["cases"]
        cls.schedules = {s["id"]: s for s in json.loads(DEFINITIONS.read_text(encoding="utf-8"))}
        cls.services = {s["id"]: s for s in services()}

    def test_people_per_space_match_native(self):
        for case in self.cases:
            spaces, _ = occupancy_carrier(case["building_type"], case["template"], case["view"])
            built = {name: (area, people) for name, _, area, people in spaces}
            with self.subTest(case=case["case_id"]):
                self.assertEqual(sorted(built), sorted(case["spaces"]))
                for name, (area, people) in case["spaces"].items():
                    self.assertAlmostEqual(built[name][0], area, delta=1e-9)
                    self.assertAlmostEqual(built[name][1], people, delta=1e-9)

    def test_water_matches_native(self):
        for case in self.cases:
            spaces, invert = occupancy_carrier(case["building_type"], case["template"], case["view"])
            people = [(sid, {"rules": self.schedules[sid]["rules"]}, count) for _, sid, _, count in spaces]
            for water in case["water"]:
                schedule_id = self.services[water["service_id"]]["load"]["schedule_id"]
                if schedule_id is None:
                    continue  # laundry: the definitions report no schedule (unknown), so it is not generated
                with self.subTest(case=case["case_id"], service=water["service_id"]):
                    result = transform({"water": Slot({"rules": self.schedules[schedule_id]["rules"]}, "hours")},
                                       people, case["operating"], invert_rule_days=invert)
                    difference = np.abs(result["water"] - unpack_days(water["expected"])).max()
                    self.assertLessEqual(float(difference), FRACTION_TOLERANCE)


if __name__ == "__main__":
    unittest.main()
