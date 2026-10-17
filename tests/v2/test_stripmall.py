"""Stripmall: three People Rulesets set the building hours that shared water follows."""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules_v2.commercial.transform import Slot, transform
from tests.v2.test_commercial_families import FRACTION_TOLERANCE, unpack_days

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/commercial/stripmall.json.gz"


class StripmallPilot(unittest.TestCase):
    def test_water_follows_the_grouped_building_hours(self):
        data = json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))
        schedules = data["schedules"]
        for case in data["cases"]:
            people = [(sid, schedules[sid], count) for sid, count in case["people"]]
            slots = {name: Slot(schedules[w["schedule_id"]], "hours") for name, w in case["water"].items()}
            result = transform(slots, people, case["operating"])
            for name, water in case["water"].items():
                with self.subTest(case=case["case_id"], schedule=name):
                    difference = np.abs(result[name] - unpack_days(water["expected"])).max()
                    self.assertLessEqual(float(difference), FRACTION_TOLERANCE)


if __name__ == "__main__":
    unittest.main()
