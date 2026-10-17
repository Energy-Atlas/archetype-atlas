"""The commercial kernel against native OpenStudio 3.10 / standards 0.8.6 output."""
import gzip
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules_v2.commercial.base_peak import adjust_day
from atlas_schedules_v2.commercial.hours import Hours, hours_from_points, sampled_hours
from atlas_schedules_v2.commercial.transform import Slot, transform

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/commercial/kernel-cases.json.gz"
FRACTION_TOLERANCE = 1e-6


def load_cases():
    return json.loads(gzip.decompress(ANSWER_KEY.read_bytes()))["cases"]


class NativeCases(unittest.TestCase):
    def test_every_slot_matches_native_output(self):
        for case in load_cases():
            slots = {name: Slot(case["schedules"][name], mode) for name, mode in case["slot_modes"].items()}
            groups = [(g["schedule"], g["people"]) for g in case["people_groups"]]
            result = transform(slots, groups, case["operating"])
            for name in slots:
                with self.subTest(case=case["case_id"], slot=name):
                    expected = np.asarray(case["expected"][name])
                    self.assertLessEqual(float(np.abs(result[name] - expected).max()), FRACTION_TOLERANCE)


class Pieces(unittest.TestCase):
    def test_sampled_hours_wrap_past_midnight(self):
        hours = sampled_hours(20 * 3600, 8 * 3600)
        self.assertEqual(hours, Hours(20.0, 4.0, 8.0))

    def test_always_on_profile_has_24_hours(self):
        self.assertEqual(hours_from_points([(24.0, 1.0)]).hours, 24.0)

    def test_equal_valued_day_reads_as_cleared(self):
        points, base = adjust_day([(8.0, 0.5), (24.0, 0.5)], 0.2)
        self.assertEqual((points, base), ([(24.0, 0.0)], 0.0))

    def test_weekend_base_is_capped_by_weekday_base(self):
        points, base = adjust_day([(8.0, 0.1), (18.0, 1.0), (24.0, 0.1)], 0.5, weekday_base=0.3)
        self.assertAlmostEqual(base, 0.3)


if __name__ == "__main__":
    unittest.main()
