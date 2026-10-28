"""ResStock measure arguments from sampled characteristics (plan section 8, B4)."""
import json
from pathlib import Path
import unittest

from atlas_schedules.errors import GeneratorError
from atlas_schedules.residential.arguments import _arguments, unit_arguments

ROOT = Path(__file__).resolve().parents[2]
RECOVERED = ROOT / "data/program-inputs/residential-v1.json"


class RecoveredRecords(unittest.TestCase):
    def test_arguments_match_the_ruby_recovery_inputs(self):
        """The 41 recovered ResStock records: every argument both sides define is equal."""
        records = json.loads(RECOVERED.read_text(encoding="utf-8"))["records"]
        names = set(_arguments()["lookup"])
        compared = 0
        for record_id, record in records.items():
            selected = {k: v for k, v in record["metadata"]["original_selected_options"].items() if k in names}
            ours = unit_arguments(selected)
            theirs = record["metadata"]["expanded_source_arguments"]
            for key, value in ours.items():
                if key in theirs:
                    compared += 1
                    self.assertEqual(value, theirs[key], (record_id, key))
        self.assertGreater(compared, 5000)


class Rules(unittest.TestCase):
    def test_no_pool_and_typed_properties(self):
        arguments = unit_arguments({"Misc Pool": "None", "Clothes Washer": "Standard", "Ceiling Fan": "Standard Efficiency"})
        self.assertEqual(arguments["misc_pool"], "None")
        self.assertEqual(arguments["appliance_clothes_washer_rated_annual_consumption"], 380)
        self.assertEqual(arguments["appliance_clothes_washer_capacity"], 3.2)
        self.assertIsNone(arguments["appliance_clothes_washer_usage_multiplier"])
        self.assertEqual(arguments["ceiling_fans_label_energy_use"], 45)

    def test_unknown_option_is_reported(self):
        with self.assertRaises(GeneratorError):
            unit_arguments({"Lighting": "100% Candles"})


if __name__ == "__main__":
    unittest.main()
