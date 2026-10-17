"""The commercial kernel against every native family capture.

Medium Office, Small Office, Warehouse, Restaurants and Retail programme cases,
plus Restaurant water slots, from OpenStudio 3.10 / openstudio-standards 0.8.6.
"""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules_v2.commercial.hours import Hours
from atlas_schedules_v2.commercial.transform import Slot, hourly_values, transform, transform_days

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/commercial/families.json.gz"
FRACTION_TOLERANCE = 1e-6


def unpack_days(packed: dict) -> np.ndarray:
    return np.asarray([packed["days"][i] for i in packed["index"]], dtype=float).reshape(8760)


def hours_by_day(table: list) -> list:
    hours = [None] * 365
    for start, end, length, days in table:
        for day in days:
            hours[day - 1] = Hours(start, end, length)
    return hours


class FamilyCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))

    def test_programme_slots_match_native_output(self):
        schedules = self.data["schedules"]
        for case in self.data["programme_cases"]:
            slots = {name: Slot(schedules[sid], mode) for name, (sid, mode) in case["slots"].items()}
            people = [(sid, schedules[sid], count) for sid, count in case["people"]]
            result = transform(slots, people, case["operating"])
            for name in slots:
                with self.subTest(case=case["case_id"], slot=name):
                    difference = np.abs(result[name] - unpack_days(case["expected"][name])).max()
                    self.assertLessEqual(float(difference), FRACTION_TOLERANCE)

    def test_restaurant_water_matches_native_output(self):
        for case in self.data["water_cases"]:
            original = unpack_days(case["original"])
            original_hours = hours_by_day(case["original_hours"])
            new = hours_by_day(case["new_hours"])
            # Day 1 of 2007 is a Monday and day 6 a Saturday.
            new_hours = {"weekday": new[0], "weekend": new[5]}
            days = transform_days(original, original.min(), original.max(), "hours", original_hours, new_hours)
            with self.subTest(case=case["case_id"]):
                difference = np.abs(hourly_values(days) - unpack_days(case["expected"])).max()
                self.assertLessEqual(float(difference), FRACTION_TOLERANCE)


if __name__ == "__main__":
    unittest.main()
