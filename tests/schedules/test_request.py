"""Request validation and generator behaviour that does not need an answer key."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from atlas_schedules.errors import GeneratorError
from atlas_schedules.generator import generate
from atlas_schedules.release import translate
from tests.schedules.helpers import load_recipe

COMMERCIAL = "90-1-2013.warehouse.source.office.7fc5a6"  # Warehouse office area 90.1-2013 (no shared services)
DWELLING = "resstock-sdr.multifamily-5-plus-low-rise.7ak-1980s-500-749ft2-b143851.d8e286"    # ResStock dwelling (2 residents, Anchorage)
APARTMENT = "90-1-2007.highrise-apartment.source.apartment.d88967"   # apartment dwelling unit
DATA_CENTRE = "90-1-2007.large-office.source.office-large-data-center.8883eb"  # OfficeLarge Data Center 90.1-2007 (flat plug load)
RESTAURANT = "90-1-2013.quick-service-restaurant.source.kitchen.9911f2"  # Quick Service Restaurant 90.1-2013 (needs kitchen water)
WATER = "90-1-2013.quick-service-restaurant.main.1be363"
RESTAURANT_CONFIGURATION = "quick_service_restaurant__90_1_2013__source"
DEPARTMENT = "doe-ref-1980-2004.hospital.department.diagnostics-mixed.407fa7"  # composition of three spaces


def request(*instances, **extra) -> dict:
    return {"schema_version": "3.0.0", "seed": 7, "instances": list(instances), **extra}


class Validation(unittest.TestCase):
    def assert_code(self, code: str, document: dict) -> None:
        with self.assertRaises(GeneratorError) as caught:
            generate(document)
        self.assertEqual(caught.exception.code, code)

    def test_schema_errors_name_the_field(self):
        with self.assertRaises(GeneratorError) as caught:
            generate(request({"key": "a", "program_id": COMMERCIAL, "extent": {"floor_area": -1}}))
        self.assertEqual(caught.exception.code, "invalid_request")
        self.assertIn("/instances/0/extent/floor_area", caught.exception.path)

    def test_duplicate_keys(self):
        self.assert_code("duplicate_instance", request({"key": "a", "program_id": COMMERCIAL},
                                                       {"key": "a", "program_id": COMMERCIAL}))

    def test_unknown_programme(self):
        self.assert_code("unsupported_binding", request({"key": "a", "program_id": "90-1-2013.warehouse.source.nowhere.000000"}))

    def test_views(self):
        self.assert_code("unsupported_input", request({"key": "a", "program_id": RESTAURANT, "values": "filled"}))
        self.assert_code("invalid_request", request({"key": "a", "program_id": COMMERCIAL, "values": "reviewed"}))
        water = {"key": "w", "service_id": WATER, "configuration_id": RESTAURANT_CONFIGURATION, "physical_id": "f",
                 "extent": {"floor_area": 1}, "values": "source"}
        self.assert_code("invalid_request", request(water))
        self.assertEqual(load_recipe(COMMERCIAL)["values"], "filled")
        self.assertEqual(load_recipe(COMMERCIAL, "source")["values"], "source")

    def test_definition_ids_translate_through_the_definition_map(self):
        self.assert_code("invalid_request", request({"key": "a", "program_id": "program-b910ee0c34e9eeb3ecd573c4"}))
        document = translate(request({"key": "r", "program_id": "program-080dc08cd2d7af6c7d419d0a",
                                      "service_links": {"service-1981fa97b9fd7d47efcf39dd": "w"}},
                                     {"key": "w", "service_id": "service-1981fa97b9fd7d47efcf39dd",
                                      "configuration_id": RESTAURANT_CONFIGURATION, "physical_id": "f"}))
        self.assertEqual(document["instances"][0], {"key": "r", "program_id": RESTAURANT, "values": "source",
                                                    "service_links": {WATER: "w"}})
        self.assertEqual(document["instances"][1]["service_id"], WATER)

    def test_ids_must_be_well_formed(self):
        for field, value in (("program_id", "../schedules"), ("program_id", "program-unknown")):
            with self.subTest(value=value):
                self.assert_code("invalid_request", request({"key": "a", field: value}))
        water = {"key": "w", "service_id": WATER, "configuration_id": "../schedules", "physical_id": "f"}
        self.assert_code("invalid_request", request(water))

    def test_unknown_configuration(self):
        water = {"key": "w", "service_id": WATER, "configuration_id": "large_office__90_1_2013__nowhere",
                 "physical_id": "f", "extent": {"floor_area": 1}}
        self.assert_code("unsupported_binding", request(water))

    def test_an_instance_is_a_programme_or_a_service(self):
        self.assert_code("invalid_request", request({"key": "a", "program_id": COMMERCIAL, "service_id": WATER}))

    def test_keys_cannot_contain_a_slash(self):
        self.assert_code("invalid_request", request({"key": "u/water", "program_id": COMMERCIAL}))

    def test_residents_follow_the_resstock_range(self):
        unit = {"key": "u", "program_id": APARTMENT, "extent": {"floor_area": 80.0},
                "location": {"state": "NC", "latitude": 35.741, "longitude": -81.389, "utc_offset": -5}}
        self.assert_code("invalid_request", request({**unit, "residents": 12}))
        bundle = generate(request({**unit, "residents": 11}))
        self.assertTrue(bundle["schedules"])

    def test_seed_must_be_an_integer(self):
        self.assert_code("invalid_seed", request({"key": "home", "program_id": DWELLING}, seed=42.0))

    def test_unknown_stream_mode(self):
        with self.assertRaises(GeneratorError) as caught:
            generate(request({"key": "home", "program_id": DWELLING}), residential_rng="other")
        self.assertEqual(caught.exception.code, "invalid_request")

    def test_required_services_must_be_linked(self):
        self.assert_code("service_links", request({"key": "r", "program_id": RESTAURANT}))

    def test_links_must_name_a_service_instance_of_that_service(self):
        self.assert_code("invalid_request", request(
            {"key": "r", "program_id": RESTAURANT, "service_links": {WATER: "missing"}}))
        self.assert_code("invalid_request", request(
            {"key": "r", "program_id": RESTAURANT, "service_links": {WATER: "office"}},
            {"key": "office", "program_id": COMMERCIAL}))

    def test_mixture_services_must_be_service_instances(self):
        self.assert_code("invalid_request", request(
            {"key": "a", "program_id": COMMERCIAL, "extent": {"floor_area": 1}},
            {"key": "b", "program_id": COMMERCIAL, "extent": {"floor_area": 1}},
            mixture={"program_id": "m", "members": [{"instance": "a", "weight": 1}], "services": ["b"],
                     "result_basis": "floor_area", "denominator": 1}))

    def test_linked_services_need_a_denominator(self):
        restaurant = {"key": "r", "program_id": RESTAURANT, "service_links": {WATER: "w"}, "operating_group": "g"}
        water = {"key": "w", "service_id": WATER, "configuration_id": RESTAURANT_CONFIGURATION, "physical_id": "f",
                 "extent": {"floor_area": 116.17147592}, "operating_group": "g"}
        self.assert_code("invalid_mixture", request(
            restaurant, water, mixture={"program_id": "m", "members": [{"instance": "r", "weight": 1}]}))

    def test_operating_group_conflict_in_either_order(self):
        office = {"key": "o", "program_id": COMMERCIAL, "operating_group": "g"}
        water = {"key": "w", "service_id": WATER, "configuration_id": RESTAURANT_CONFIGURATION, "physical_id": "f",
                 "extent": {"floor_area": 1}, "operating_group": "g"}
        for instances in ((office, water), (water, office)):
            with self.subTest(first=instances[0]["key"]):
                self.assert_code("operating_group_conflict", request(*instances))

    def test_mixture_weights_must_sum_to_one(self):
        document = request({"key": "a", "program_id": COMMERCIAL},
                           mixture={"program_id": "m", "members": [{"instance": "a", "weight": 0.5}]})
        self.assert_code("invalid_mixture", document)

    def test_extents_need_a_denominator(self):
        document = request({"key": "a", "program_id": COMMERCIAL, "extent": {"floor_area": 10}},
                           mixture={"program_id": "m", "members": [{"instance": "a", "weight": 1}]})
        self.assert_code("invalid_mixture", document)


class Behaviour(unittest.TestCase):
    def test_same_request_same_bundle(self):
        document = request({"key": "office", "program_id": COMMERCIAL, "operating_group": "b"})
        self.assertEqual(generate(document)["schedules"], generate(document)["schedules"])

    def test_shared_operating_group_shares_hours(self):
        bundle = generate(request({"key": "a", "program_id": COMMERCIAL, "operating_group": "b"},
                                  {"key": "b2", "program_id": COMMERCIAL, "operating_group": "b"}))
        a = bundle["schedules"]["schedule:a:occupancy"]["values"]
        b = bundle["schedules"]["schedule:b2:occupancy"]["values"]
        self.assertEqual(a, b)

    def test_commercial_loads_bind_their_source_magnitude(self):
        # O15: the density is the amplitude; the annual total follows the sampled hours.
        recipe = load_recipe(COMMERCIAL)
        density = next(d["value"] for d in recipe["demands"] if d["slot"] == "lighting")
        totals = set()
        for seed in (7, 8):
            bundle = generate(request({"key": "office", "program_id": COMMERCIAL}, seed=seed))
            lighting = next(load for load in bundle["owners"][0]["loads"] if load["slot"] == "lighting")
            values = np.asarray(bundle["schedules"]["schedule:office:lighting"]["values"])
            self.assertEqual(lighting["amplitude"], density)
            self.assertAlmostEqual(lighting["amplitude"] * values.sum() / lighting["annual_total"], 1, delta=1e-12)
            totals.add(round(lighting["annual_total"], 6))
        self.assertEqual(len(totals), 2)

    def test_composition_parent_weights_members_by_their_source_magnitudes(self):
        bundle = generate(request({"key": "p", "program_id": DEPARTMENT, "operating_group": "g"}))
        owners = {o["key"]: o for o in bundle["owners"]}
        members = [o for k, o in owners.items() if k.startswith("source-member/")]
        area = sum(m["extent"]["floor_area"] for m in members)
        values = lambda owner, slot: np.asarray(bundle["schedules"][owner["schedules"][slot]]["values"])
        for mixed in owners["p"]["loads"]:
            parts = [(m["extent"]["floor_area"] / area, load, m) for m in members for load in m["loads"]
                     if (load["quantity"], load["fuel"], load["host"]) == (mixed["quantity"], mixed["fuel"], mixed["host"])]
            self.assertAlmostEqual(mixed["amplitude"], sum(f * load["amplitude"] for f, load, _ in parts), delta=1e-9)
            expected = sum(f * load["amplitude"] * values(m, load["slot"]) for f, load, m in parts)
            got = mixed["amplitude"] * values(owners["p"], mixed["slot"])
            self.assertLessEqual(float(np.abs(got - expected).max()), 1e-9 * float(expected.max()))

    def test_data_centre_plug_loads_stay_constant(self):
        # Documented: base-to-peak leaves flat days unchanged (section 4.6.3).
        document = request({"key": "dc", "program_id": DATA_CENTRE, "operating_group": "office"})
        values = np.asarray(generate(document)["schedules"]["schedule:dc:electric_equipment"]["values"])
        self.assertGreater(float(values.min()), 0)
        # Native ComStock clears those days; the source density then binds a zero schedule (O15).
        native = generate(document, flat_days="native")
        self.assertEqual(max(native["schedules"]["schedule:dc:electric_equipment"]["values"]), 0)
        load = next(l for l in native["owners"][0]["loads"] if l["slot"] == "electric_equipment")
        self.assertEqual(load["annual_total"], 0)

    def test_requests_cannot_choose_the_ruby_stream(self):
        with self.assertRaises(GeneratorError) as caught:
            generate(request({"key": "home", "program_id": DWELLING}, residential_rng="ruby_mt"))
        self.assertEqual(caught.exception.code, "invalid_request")

    def test_both_residential_modes_run(self):
        for mode in ("pcg64", "ruby_mt"):
            bundle = generate(request({"key": "home", "program_id": DWELLING}), residential_rng=mode)
            occupants = np.asarray(bundle["schedules"]["schedule:home:occupants"]["values"])
            self.assertTrue(0 < occupants.max() <= 1)


class CommandLine(unittest.TestCase):
    def test_cli_writes_a_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.json"
            out = Path(folder) / "bundle.json"
            path.write_text(json.dumps(request({"key": "office", "program_id": COMMERCIAL})), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "atlas_schedules", str(path), "-o", str(out)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("schedule:office:lighting", json.loads(out.read_text(encoding="utf-8"))["schedules"])

    def test_cli_reports_an_unreadable_request(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.json"
            path.write_text("{not json", encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "atlas_schedules", str(path)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("cannot read", result.stderr)


class ReferenceLocations(unittest.TestCase):
    def test_dwelling_follows_the_reference_climate(self):
        lighting = {}
        for case in ("1A", "8"):
            bundle = generate(request({"key": "home", "program_id": DWELLING, "reference_location": case}))
            lighting[case] = np.asarray(bundle["schedules"]["schedule:home:lighting_interior"]["values"])
        # Interior lighting follows the location's sunset times (same seed, same occupants).
        self.assertGreater(float(np.abs(lighting["1A"] - lighting["8"]).max()), 0.01)


if __name__ == "__main__":
    unittest.main()
