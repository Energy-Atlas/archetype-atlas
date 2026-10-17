"""The operating-parameter sampler against native ComStock tsv_sampling.py draws."""
import json
from pathlib import Path
import unittest

from atlas_schedules_v2.commercial.sampler import DRAW_ORDER, load_tables, sample_operating_parameters, select_option
from atlas_schedules_v2.errors import GeneratorError

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/commercial/sampling-draws.json"


class NativeDraws(unittest.TestCase):
    def test_supplied_uniforms_select_the_native_options(self):
        for observation in json.loads(ANSWER_KEY.read_text(encoding="utf-8"))["observations"]:
            tables = load_tables(observation["building_type"])
            selectors = {"building_type": observation["building_type"]}
            for parameter, uniform in zip(DRAW_ORDER, observation["uniforms"]):
                table = tables[parameter]
                option = table["options"][select_option(table, selectors, uniform)]
                self.assertEqual(option, observation["selected"][parameter])
                selectors[parameter] = option


class Sampling(unittest.TestCase):
    def test_same_seed_same_parameters(self):
        tables = load_tables("medium_office")
        first = sample_operating_parameters(tables, "medium_office", 123)
        self.assertEqual(first, sample_operating_parameters(tables, "medium_office", 123))
        self.assertEqual(first["weekday_start_time"]["unit"], "s")

    def test_draw_beyond_table_total_is_an_error(self):
        table = {"dependencies": [], "options": ["a"], "rows": [{"selectors": {}, "probabilities": [0.5]}]}
        with self.assertRaises(GeneratorError):
            select_option(table, {}, 0.75)


if __name__ == "__main__":
    unittest.main()
