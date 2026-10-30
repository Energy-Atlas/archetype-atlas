"""The nine newer families' packaged programmes against native captures.

One template per family, both views, seeds 42 and 51
(scripts/capture/commercial_families.py, OpenStudio 3.10 / openstudio-standards
0.8.6). Each case rebuilds its inputs from the packaged recipe or the
configuration's water services, the configuration's People and the sampled
operating parameters, and every final slot must match within 1e-6.
"""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules.commercial.sampler import load_tables, sample_operating_parameters
from atlas_schedules.commercial.transform import Slot, transform
from atlas_schedules.programmes import configuration_people, load_configuration, schedules
from atlas_schedules.seeds import commercial_group_seed
from tests.schedules.helpers import TOLERANCE, load_recipe, load_service, retired, unpack_days

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/commercial/family-programmes.json.gz"
GROUP = "building"


def _slots(case: dict) -> dict:
    table = schedules()
    if case["subject"] == "water":
        slots = {}
        for name in case["expected"]:
            service_id = name.removeprefix("water:")
            variant = load_service(service_id)["configurations"][case["configuration_id"]]
            slots[name] = Slot(table[variant["schedule"]], "hours")
        return slots
    recipe = load_recipe(case["subject"])
    modes = recipe["commercial"]["modes"]
    return {s["slot"]: Slot(table[s["schedule"]], modes[s["slot"]]) for s in recipe["slots"] if s["slot"] in modes}


class FamilyProgrammes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))
        # DOE Ref cases name recipes replaced in stage X1.2
        cls.compared = [c for c in cls.data["cases"] if not retired(c["subject"], c["configuration_id"], c["case_id"])]

    def test_every_family_template_is_covered(self):
        configurations = {c["configuration_id"] for c in self.data["cases"]}
        self.assertEqual(len(configurations), 2 * len(self.data["source"]["templates"]))

    def test_sampler_still_gives_the_captured_parameters(self):
        # Drift guard: the captures used this sampler (itself checked against
        # native tsv_sampling.py draws in test_sampler).
        for case in self.compared:
            building_type = load_configuration(case["configuration_id"])["building_type"]
            sampled = sample_operating_parameters(load_tables(building_type), building_type,
                                                  commercial_group_seed(case["seed"], GROUP))
            with self.subTest(case=case["case_id"]):
                self.assertEqual({k: {"modify": v["modify"], "value": v["value"]} for k, v in sampled.items()},
                                 case["operating"])

    def test_slots_match_native_output(self):
        for case in self.compared:
            configuration = load_configuration(case["configuration_id"])
            slots = _slots(case)
            self.assertEqual(sorted(slots), sorted(case["expected"]), case["case_id"])
            result = transform(slots, configuration_people(configuration), case["operating"],
                               invert_rule_days=configuration["invert_rule_days"], flat_days="native")
            for name in slots:
                with self.subTest(case=case["case_id"], slot=name):
                    difference = np.abs(result[name] - unpack_days(case["expected"][name])).max()
                    self.assertLessEqual(float(difference), TOLERANCE)


if __name__ == "__main__":
    unittest.main()
