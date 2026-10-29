"""ResStock annual equations: the Python port against the pinned Ruby methods (plan section 8, B5).

The answer key holds 240 sampled apartment units and the loads scripts/recover_residential_inputs.rb gave
under the pinned OpenStudio runtime (written by scripts/validate_resstock_annual.py).
"""
import json
import math
from pathlib import Path
import unittest

from atlas_schedules.residential.annual import annual_loads, equivalent_bedrooms
from atlas_schedules.residential.arguments import expand_properties

KEY = Path(__file__).resolve().parents[1] / "answer_keys/resstock-annual.json"
TOLERANCE = 1e-9


class RubyEquivalence(unittest.TestCase):
    def test_every_unit_and_end_use_matches_the_ruby_methods(self):
        units = json.loads(KEY.read_text(encoding="utf-8"))["units"]
        self.assertEqual(len(units), 240)
        for unit in units:
            expanded = expand_properties(unit["arguments"])
            port = annual_loads(expanded, unit["occupants"], unit["bedrooms"], unit["cfa_ft2"], unit["fan_months"],
                                unit_type=expanded["geometry_facility_type"])
            ruby = unit["ruby_loads"]
            self.assertEqual([p["end_use"] for p in port], [r["end_use"] for r in ruby], unit["record_id"])
            for p, r in zip(port, ruby):
                for key in ("annual_kwh", "annual_therm", "daily_gallons"):
                    if key in r:
                        self.assertTrue(math.isclose(p[key], r[key], rel_tol=TOLERANCE, abs_tol=TOLERANCE),
                                        (unit["record_id"], p["end_use"], key, p[key], r[key]))
                if "heat_fractions" in r and "sensible_fraction" in p:
                    self.assertAlmostEqual(p["sensible_fraction"], r["heat_fractions"]["radiant"] / 0.6, places=12)
                    self.assertAlmostEqual(p["latent_fraction"], r["heat_fractions"]["latent"], places=12)


class Rules(unittest.TestCase):
    def test_equivalent_bedrooms_follow_the_recs_regression(self):
        self.assertAlmostEqual(equivalent_bedrooms(2, 2), -1.36 + 1.49 * 2)

    def test_vacant_units_keep_only_refrigeration(self):
        arguments = expand_properties({"appliance_refrigerator": "748 kWh/yr, 100% Usage", "lighting": "100% LED, 100% Usage",
                                       "appliance_cooking_range_oven": "Electricity, Standard, Non-Convection, 100% Usage",
                                       "misc_plug_loads": "100% Usage", "misc_television": "100% Usage"})
        loads = {l["end_use"]: l["annual_kwh"] for l in annual_loads(arguments, 0, 2, 800, [0] * 12)}
        self.assertEqual(loads["refrigerator"], 748)
        self.assertTrue(all(v == 0 for k, v in loads.items() if k != "refrigerator"))


if __name__ == "__main__":
    unittest.main()
