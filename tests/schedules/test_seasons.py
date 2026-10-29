"""Southern-hemisphere season alignment of the residential month-indexed terms (O13)."""
import unittest

import numpy as np

from atlas_schedules import generate
from atlas_schedules.companions import fixed_background
from atlas_schedules.residential.lighting import sunset_hours
from atlas_schedules.residential.seasons import for_hemisphere, season_month, seasonal
from atlas_schedules.residential.tables import load_tables

APARTMENT = "program-60b1063b9fe00c5c29654bb9"


class SeasonShift(unittest.TestCase):
    def test_months_shift_six_only_south(self):
        self.assertEqual([season_month(m, 40.0) for m in range(1, 13)], list(range(1, 13)))
        self.assertEqual([season_month(m, -33.9) for m in range(1, 13)], [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6])
        self.assertEqual(seasonal(list(range(12)), -1.0), [6, 7, 8, 9, 10, 11, 0, 1, 2, 3, 4, 5])

    def test_northern_tables_are_untouched(self):
        tables = load_tables()
        self.assertIs(for_hemisphere(tables, 42.4), tables)

    def test_southern_tables_rotate_only_monthly_multipliers(self):
        tables = load_tables()
        south = for_hemisphere(tables, -33.9)
        for key, values in tables.custom.items():
            expected = seasonal(values, -33.9) if "Monthly" in key[1] else values
            self.assertEqual(south.custom[key], expected, key)

    def test_southern_summer_gets_the_extra_hour(self):
        # Upstream's April-October hour gives summer sunsets in daylight-saving clock
        # time (London June 21:11, like BST). Shifted, Sydney gets it in its own summer:
        # about 20:10 (daylight saving) in January, about 16:55 (standard) in June.
        sunsets = sunset_hours(-33.87, 151.21, 10.0)
        self.assertAlmostEqual(sunsets[0], 20.1, delta=0.3)
        self.assertAlmostEqual(sunsets[5], 16.9, delta=0.3)

    def test_fixed_background_follows_the_hemisphere(self):
        north = fixed_background("refrigerator").reshape(365, 24).sum(1)
        south = fixed_background("refrigerator", latitude=-33.9).reshape(365, 24).sum(1)
        july, january = slice(181, 212), slice(0, 31)
        self.assertAlmostEqual(float(south[january].mean()), float(north[july].mean()), delta=1e-3 * north.mean())

    def test_southern_apartment_lights_later_in_january(self):
        unit = {"key": "u", "program_id": APARTMENT, "residents": 2, "extent": {"floor_area": 80.0},
                "location": {"state": "CA", "latitude": -33.87, "longitude": 151.21, "utc_offset": 10}}
        bundle = generate({"schema_version": "3.0.0", "seed": 7, "instances": [unit]})
        days = np.asarray(bundle["schedules"]["schedule:u:lighting_interior"]["values"]).reshape(365, 24)
        evening = lambda d: float(days[d, 16:19].sum() / days[d].sum())
        # Late afternoon is a larger share of the day's lighting in southern winter (June) than in summer (January).
        self.assertGreater(np.mean([evening(d) for d in range(151, 181)]), np.mean([evening(d) for d in range(0, 31)]))


if __name__ == "__main__":
    unittest.main()
