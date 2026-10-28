"""ResStock housing-characteristics sampler for apartment units (plan section 8, B3)."""
import collections
import math
import random
import unittest

from atlas_schedules.errors import GeneratorError
from atlas_schedules.residential import characteristics as ch

FIVE_PLUS = "Multi-Family with 5+ Units"
ALL_VINTAGES = ("<1940", "1940s", "1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s")
COMPARED = ("Tenure", "Income RECS2020", "Bedrooms", "Occupants", "Vintage", "Federal Poverty Level", "Lighting",
            "Geometry Stories", "HVAC Heating Efficiency", "Heating Setpoint", "Clothes Washer Presence")


def rejection_draws(conditions: ch.Conditions, attempts: int, seed: int) -> list:
    """Independent check: forward-sample the whole network in a state and keep matching draws."""
    tables, cells = ch._load(conditions.state)
    rng = random.Random(seed)
    zones = tables["ASHRAE IECC Climate Zone 2004"]
    zone_p = dict(zip(zones.options, zones.distribution({})))
    pairs = [(zone, cell) for cell in cells for zone, p in cell["probability_given_climate_zone"].items()]
    weights = [zone_p[zone] * cell["probability_given_climate_zone"][zone] for zone, cell in pairs]
    order, done, pending = [], {"State", "County and PUMA", "County", "PUMA", "ASHRAE IECC Climate Zone 2004"}, dict(
        (n, set(t.dependencies)) for n, t in tables.items() if n != "ASHRAE IECC Climate Zone 2004")
    while pending:
        ready = sorted(n for n, d in pending.items() if d <= done)
        order += ready
        done |= set(ready)
        for n in ready:
            del pending[n]
    fixed = {"Geometry Building Type RECS": conditions.building_type, "Geometry Floor Area": conditions.floor_area,
             "Geometry Building Type Height": conditions.height, "Occupants": conditions.occupants,
             "ASHRAE IECC Climate Zone 2004": conditions.climate_zone}
    if conditions.hvac is not None:
        fixed.update(zip(ch.HVAC, conditions.hvac))
    kept = []
    for _ in range(attempts):
        zone, cell = rng.choices(pairs, weights)[0]
        values = {"State": conditions.state, "ASHRAE IECC Climate Zone 2004": zone, "County and PUMA": cell["id"],
                  "County": cell["county"], "PUMA": cell["puma"]}
        ok = fixed["ASHRAE IECC Climate Zone 2004"] in (None, zone)
        for name in order:
            if not ok:
                break
            table = tables[name]
            try:
                values[name] = rng.choices(table.options, table.distribution(values))[0]
            except GeneratorError:     # a row the multifamily filter dropped: another building type
                ok = False
                break
            if fixed.get(name) is not None and values[name] != fixed[name]:
                ok = False
            if name == "Vintage" and values[name] not in conditions.vintages:
                ok = False
        if ok:
            kept.append(values)
    return kept


def bound(p1: float, p2: float, n1: int, n2: int) -> float:
    p = (p1 * n1 + p2 * n2) / (n1 + n2)
    return 4.5 * math.sqrt(max(p * (1 - p), 1e-4) * (1 / n1 + 1 / n2)) + 2e-3


class Options(unittest.TestCase):
    def test_floor_area_bins_follow_resstock_labels(self):
        self.assertEqual(ch.floor_area_option(40), "0-499")         # 431 ft2
        self.assertEqual(ch.floor_area_option(80), "750-999")       # 861 ft2
        self.assertEqual(ch.floor_area_option(400), "4000+")
        with self.assertRaises(GeneratorError):
            ch.floor_area_option(0)

    def test_residents_map_to_occupant_options(self):
        self.assertEqual([ch.occupants_option(n) for n in (0, 1, 9, 10, 14)], ["0", "1", "9", "10+", "10+"])


class Draws(unittest.TestCase):
    conditions = ch.Conditions(state="NC", building_type=FIVE_PLUS, floor_area="750-999", vintages=("2000s",),
                               climate_zone="4A", height="Multi-Family with 5+ Units, 8+ Stories", occupants="2",
                               hvac=("Electricity", "Ducted Heat Pump", "Ducted Heat Pump", "None", "No"))

    def test_fixed_characteristics_hold_and_draws_repeat(self):
        first = ch.sample_characteristics(self.conditions, 11)
        self.assertEqual(first, ch.sample_characteristics(self.conditions, 11))
        self.assertNotEqual(first, ch.sample_characteristics(self.conditions, 12))
        for seed in range(30):
            draw = ch.sample_characteristics(self.conditions, seed)
            self.assertEqual((draw["State"], draw["Geometry Building Type RECS"], draw["Geometry Floor Area"],
                              draw["Vintage"], draw["ASHRAE IECC Climate Zone 2004"], draw["Occupants"],
                              draw["Geometry Building Type Height"]),
                             ("NC", FIVE_PLUS, "750-999", "2000s", "4A", "2", "Multi-Family with 5+ Units, 8+ Stories"))
            self.assertEqual(tuple(draw[n] for n in ch.HVAC), self.conditions.hvac)
            self.assertNotIn("PUMA", draw)

    def test_impossible_conditions_are_reported(self):
        with self.assertRaises(GeneratorError):
            ch.sample_characteristics(ch.Conditions(state="NC", building_type=FIVE_PLUS, floor_area="750-999",
                                                    vintages=("2000s",), climate_zone="8AK"), 1)


class Exactness(unittest.TestCase):
    """The exact sampler and rejection from forward draws agree on every compared characteristic."""

    def compare(self, conditions, attempts, draws):
        reference = rejection_draws(conditions, attempts, seed=5)
        sampled = [ch.sample_characteristics(conditions, s) for s in range(draws)]
        self.assertGreater(len(reference), 800)
        for name in COMPARED:
            a = collections.Counter(d[name] for d in sampled)
            b = collections.Counter(d[name] for d in reference)
            for option in set(a) | set(b):
                p1, p2 = a[option] / len(sampled), b[option] / len(reference)
                self.assertLess(abs(p1 - p2), bound(p1, p2, len(sampled), len(reference)), (name, option, p1, p2))

    def test_floor_area_and_vintage_only(self):
        self.compare(ch.Conditions(state="DC", building_type=FIVE_PLUS, floor_area="750-999", vintages=ALL_VINTAGES),
                     attempts=12000, draws=1500)

    def test_residents_and_hvac_reweight_their_ancestors(self):
        self.compare(ch.Conditions(state="DC", building_type=FIVE_PLUS, floor_area="500-749", vintages=ALL_VINTAGES,
                                   occupants="1", hvac=("Electricity", "Ducted Heat Pump", "Ducted Heat Pump", "None", "No")),
                     attempts=150000, draws=1500)


if __name__ == "__main__":
    unittest.main()
