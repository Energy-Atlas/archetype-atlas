"""Request validation and generator behaviour that does not need an answer key."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from atlas_schedules_v2.errors import GeneratorError
from atlas_schedules_v2.generator import generate

OFFICE = "program-0e670d8dc556f7f5bdd7f1a9"      # Medium Office 90.1-2013
DWELLING = "program-03fe19ed8968e605f4be3b8d"    # ResStock dwelling (2 residents, Anchorage)


def request(*instances, **extra) -> dict:
    return {"schema_version": "2.0.0", "seed": 7, "instances": list(instances), **extra}


class Validation(unittest.TestCase):
    def assert_code(self, code: str, document: dict) -> None:
        with self.assertRaises(GeneratorError) as caught:
            generate(document)
        self.assertEqual(caught.exception.code, code)

    def test_schema_errors_name_the_field(self):
        with self.assertRaises(GeneratorError) as caught:
            generate(request({"key": "a", "program_id": OFFICE, "extent": {"floor_area": -1}}))
        self.assertEqual(caught.exception.code, "invalid_request")
        self.assertIn("/instances/0/extent/floor_area", caught.exception.path)

    def test_duplicate_keys(self):
        self.assert_code("duplicate_instance", request({"key": "a", "program_id": OFFICE},
                                                       {"key": "a", "program_id": OFFICE}))

    def test_unknown_programme(self):
        self.assert_code("unsupported_binding", request({"key": "a", "program_id": "program-unknown"}))

    def test_mixture_weights_must_sum_to_one(self):
        document = request({"key": "a", "program_id": OFFICE},
                           mixture={"program_id": "m", "members": [{"instance": "a", "weight": 0.5}]})
        self.assert_code("invalid_mixture", document)

    def test_extents_need_a_denominator(self):
        document = request({"key": "a", "program_id": OFFICE, "extent": {"floor_area": 10}},
                           mixture={"program_id": "m", "members": [{"instance": "a", "weight": 1}]})
        self.assert_code("invalid_mixture", document)


class Behaviour(unittest.TestCase):
    def test_same_request_same_bundle(self):
        document = request({"key": "office", "program_id": OFFICE, "operating_group": "b"})
        self.assertEqual(generate(document)["schedules"], generate(document)["schedules"])

    def test_shared_operating_group_shares_hours(self):
        bundle = generate(request({"key": "a", "program_id": OFFICE, "operating_group": "b"},
                                  {"key": "b2", "program_id": OFFICE, "operating_group": "b"}))
        a = bundle["schedules"]["schedule:a:occupancy"]["values"]
        b = bundle["schedules"]["schedule:b2:occupancy"]["values"]
        self.assertEqual(a, b)

    def test_annual_target_survives_the_transform(self):
        owner = generate(request({"key": "office", "program_id": OFFICE}))["owners"][0]
        lighting = next(load for load in owner["loads"] if load["slot"] == "lighting")
        bundle = generate(request({"key": "office", "program_id": OFFICE}))
        values = np.asarray(bundle["schedules"]["schedule:office:lighting"]["values"])
        self.assertAlmostEqual(lighting["amplitude"] * values.sum(), lighting["annual_total"], delta=1e-6)

    def test_both_residential_modes_run(self):
        for mode in ("pcg64", "ruby_mt"):
            bundle = generate(request({"key": "home", "program_id": DWELLING}, residential_rng=mode))
            occupants = np.asarray(bundle["schedules"]["schedule:home:occupants"]["values"])
            self.assertTrue(0 < occupants.max() <= 1)


class CommandLine(unittest.TestCase):
    def test_cli_writes_a_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.json"
            out = Path(folder) / "bundle.json"
            path.write_text(json.dumps(request({"key": "office", "program_id": OFFICE})), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "atlas_schedules_v2", str(path), "-o", str(out)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("schedule:office:lighting", json.loads(out.read_text(encoding="utf-8"))["schedules"])


if __name__ == "__main__":
    unittest.main()
