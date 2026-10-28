"""Apartment units as ResStock multifamily units (rulings 185-187; plan section 8, B6)."""
import copy
import math
import unittest
from unittest import mock

import numpy as np

from atlas_schedules import generator, programmes
from atlas_schedules.calendar import evaluate_rules
from atlas_schedules.errors import GeneratorError
from atlas_schedules.request import Location
from atlas_schedules.residential.annual import annual_loads
from atlas_schedules.residential.apartment import FT2_PER_M2, hot_water_m3_per_person, resstock_unit
from atlas_schedules.residential.arguments import unit_arguments
from atlas_schedules.residential.shapes import fan_months
from atlas_schedules.residential.tables import load_drybulb

APARTMENT = "program-60b1063b9fe00c5c29654bb9"   # 90.1-2007 high-rise apartment unit
LOCATION = {"state": "NC", "latitude": 35.741, "longitude": -81.389, "utc_offset": -5, "climate_zone": "4A"}


def resstock_recipe() -> dict:
    """The prototype recipe with the ResStock block that stage B7 writes from the release."""
    recipe = copy.deepcopy(programmes.load_recipe(APARTMENT))
    shape = evaluate_rules(programmes.schedules()[recipe["caller_water"]["schedule"]])[0]
    people = next(c for c in recipe["controls"] if c["slot"] == "occupants")["people"]["density"]
    recipe["resstock_unit"] = {
        "building_type": "Multi-Family with 5+ Units", "height": "Multi-Family with 5+ Units, 8+ Stories",
        "vintages": ["2000s"], "hvac": ["Electricity", "Ducted Heat Pump", "Ducted Heat Pump", "None", "No"],
        "hot_water_m3_per_person": hot_water_m3_per_person(recipe["caller_water"], shape, people)}
    return recipe


def generate(*units, seed=7):
    recipe, real = resstock_recipe(), generator.load_recipe
    with mock.patch.object(generator, "load_recipe", lambda pid: recipe if pid == APARTMENT else real(pid)):
        return generator.generate({"schema_version": "3.0.0", "seed": seed, "instances": list(units)})


def unit(key, residents, area=80.0, **location):
    return {"key": key, "program_id": APARTMENT, "extent": {"floor_area": area}, "residents": residents,
            "location": {**LOCATION, **location}}


class Units(unittest.TestCase):
    def test_loads_are_the_ported_resstock_annuals_on_the_units_own_schedules(self):
        bundle = generate(unit("u", 2))
        owner = next(o for o in bundle["owners"] if o["key"] == "u")
        characteristics = owner["generation"]["characteristics"]
        arguments = unit_arguments(characteristics)
        months = fan_months(load_drybulb(owner["generation"]["weather_id"]))
        expected = {}
        for load in annual_loads(arguments, 2, int(arguments["geometry_unit_num_bedrooms"]), 80 * FT2_PER_M2, months):
            if "annual_kwh" in load and load["end_use"] not in ("lighting_exterior", "lighting_garage"):
                value = load["annual_therm"] * 29307.107017222222 if "annual_therm" in load else load["annual_kwh"] * 1000
                expected.setdefault(load["end_use"], []).append(value)
        got = {}
        for load in owner["loads"]:
            got.setdefault(load["slot"], []).append(load["annual_total"])
            values = np.asarray(bundle["schedules"][owner["schedules"][load["slot"]]]["values"])
            self.assertTrue(math.isclose(load["amplitude"] * values.sum(), load["annual_total"], rel_tol=1e-9))
            self.assertEqual((load["unit"], load["basis"]), ("W/dwelling", "dwelling_unit"))
        self.assertEqual(got, expected)
        self.assertEqual(owner["extent"], {"floor_area": 80.0, "dwelling_unit": 1.0})
        self.assertEqual([c["slot"] for c in owner["controls"]], ["occupants", "activity", "heating_setpoint", "cooling_setpoint"])
        self.assertEqual(characteristics["Occupants"], "2")

    def test_hot_water_is_per_resident_and_timed_by_the_units_fixture_events(self):
        bundle = generate(unit("a", 1), unit("b", 3))
        owners = {o["key"]: o for o in bundle["owners"]}
        per_person = resstock_recipe()["resstock_unit"]["hot_water_m3_per_person"]
        self.assertAlmostEqual(per_person * 1000 / 365, 66.33, places=2)
        for key, residents in (("a", 1), ("b", 3)):
            water = owners[f"{key}/water"]["loads"][0]
            self.assertTrue(math.isclose(water["annual_total"], per_person * residents, rel_tol=1e-12))
            draws = np.asarray(bundle["schedules"][f"schedule:{key}%2Fwater:hot_water_volume"]["values"])
            home = np.asarray(bundle["schedules"][f"schedule:{key}:occupants"]["values"])
            # Fixture events follow the residents' activities; only upstream event runs that outlast a departure
            # fall in empty hours (the prototype schedule put 30 % of a one-resident unit's water there).
            self.assertLess(float(draws[home == 0].sum() / draws.sum()), 0.01)

    def test_drawn_residents_include_vacant_units(self):
        location = Location(**LOCATION)
        spec = resstock_recipe()["resstock_unit"]
        vacant = next(s for s in range(1, 400) if resstock_unit(spec, location, 80.0, "resstock", s, "pcg64", None).generation["residents"] == 0)
        result = resstock_unit(spec, location, 80.0, "resstock", vacant, "pcg64", None)
        self.assertEqual(result.water[0], 0.0)
        self.assertEqual({l.slot for l in result.loads if l.annual_total > 0}, {"refrigerator"})

    def test_requests_and_determinism(self):
        self.assertEqual(generate(unit("u", 2)), generate(unit("u", 2)))
        with self.assertRaises(GeneratorError) as caught:
            generator.generate({"schema_version": "2.0.0", "seed": 7, "instances": [
                {k: v for k, v in unit("u", "resstock").items()}]})
        self.assertEqual(caught.exception.code, "invalid_request")
        with self.assertRaises(GeneratorError) as caught:
            generator.generate({"schema_version": "3.0.0", "seed": 7, "instances": [unit("u", "resstock")]})
        self.assertEqual(caught.exception.code, "unsupported_input")   # prototype recipe: the caller gives residents


if __name__ == "__main__":
    unittest.main()
