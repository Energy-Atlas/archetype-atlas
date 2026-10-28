"""Packaged recipes and configurations against the native family captures.

test_commercial_families checks the kernel with the inputs carried in the
answer key. This test builds the same inputs from the packaged data instead:
each case's programme recipe gives the slots and modes, its configuration gives
the People topology and rule-day inversion, and the native sampled operating
parameters drive the transform. Programme hot water that a recipe moves into a
linked shared service is checked through that service's variant.
"""
import gzip
import json
from pathlib import Path
import re
import unittest

import numpy as np

from atlas_schedules.commercial.transform import Slot, transform
from atlas_schedules.generator import load_service
from atlas_schedules.programmes import configuration_people, load_configuration, load_recipe, schedules
from tests.schedules.helpers import TOLERANCE, retired, unpack_days

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/commercial/families.json.gz"


def _recipe(case_id: str) -> dict:
    """The case's programme recipe; composition member cases (".../member-N") resolve to the member."""
    recipe = load_recipe(re.search(r"program-[0-9a-f]{24}", case_id).group(0))
    member = re.search(r"/member-(\d+)", case_id)
    if member:
        recipe = load_recipe(recipe["composition"]["members"][int(member.group(1))][0])
    return recipe


class RecipesAgainstNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cases = json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))["programme_cases"]
        # DOE Ref cases name recipes replaced in stage X1.2
        cls.cases = [c for c in cases if not retired(c["case_id"], c["configuration_id"])]

    def test_recipe_slots_match_native_output(self):
        table = schedules()
        for case in self.cases:
            recipe = _recipe(case["case_id"])
            configuration = load_configuration(recipe["commercial"]["configuration_id"])
            modes = recipe["commercial"]["modes"]
            slots = {s["slot"]: Slot(table[s["schedule"]], modes[s["slot"]])
                     for s in recipe["slots"] if s["slot"] in modes and s["slot"] in case["expected"]}
            result = transform(slots, configuration_people(configuration), case["operating"],
                               invert_rule_days=configuration["invert_rule_days"], flat_days="native")
            for name in slots:
                with self.subTest(case=case["case_id"], slot=name):
                    difference = np.abs(result[name] - unpack_days(case["expected"][name])).max()
                    self.assertLessEqual(float(difference), TOLERANCE)

    def test_programme_water_moved_to_services_matches_native_output(self):
        table = schedules()
        checked = 0
        for case in self.cases:
            recipe = _recipe(case["case_id"])
            if "hot_water_volume" not in case["expected"] or any(s["slot"] == "hot_water_volume" for s in recipe["slots"]):
                continue
            configuration_id = recipe["commercial"]["configuration_id"]
            configuration = load_configuration(configuration_id)
            for service_id in recipe["required_services"]:
                variant = load_service(service_id)["configurations"][configuration_id]
                result = transform({"hot_water_volume": Slot(table[variant["schedule"]], "hours")},
                                   configuration_people(configuration), case["operating"],
                                   invert_rule_days=configuration["invert_rule_days"], flat_days="native")
                with self.subTest(case=case["case_id"], service=service_id):
                    difference = np.abs(result["hot_water_volume"] - unpack_days(case["expected"]["hot_water_volume"])).max()
                    self.assertLessEqual(float(difference), TOLERANCE)
                    checked += 1
        self.assertGreater(checked, 0)  # Medium Office programme water now lives in shared services


if __name__ == "__main__":
    unittest.main()
