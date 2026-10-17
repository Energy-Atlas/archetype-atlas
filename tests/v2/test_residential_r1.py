"""R1 (Ruby MT replay) residential output against native Ruby 3.2.2 captures."""
import json
from pathlib import Path
import unittest

import numpy as np

from atlas_schedules_v2.errors import GeneratorError
from atlas_schedules_v2.residential.activity import Activities, simulate_activities
from atlas_schedules_v2.residential.generate import (Dwelling, dwelling_channels, generate_dwelling,
                                                     generate_occupancy_and_lighting)
from atlas_schedules_v2.residential.rng import RubyStream, unit_streams
from atlas_schedules_v2.residential.tables import load_tables

KEYS = Path(__file__).resolve().parents[1] / "answer_keys/residential"
REFERENCE_VECTORS = Path(__file__).resolve().parents[2] / "data/schedule-generator/reference-vectors.json"
TOLERANCE = 1e-6


def dwelling(inputs: dict) -> Dwelling:
    return Dwelling(inputs["residents"], inputs.get("state"), inputs.get("latitude"), inputs.get("longitude"),
                    inputs.get("time_zone_utc_offset"), inputs.get("weather_id"), inputs.get("installed"))


def activities_from_runs(runs: list, offset: int) -> Activities:
    traces = [np.concatenate([np.full(length, state, dtype=np.int8) for length, state in resident])
              for resident in runs]
    return Activities(np.asarray(traces), [], offset)


class NativeUnits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((KEYS / "cases.json").read_text(encoding="utf-8"))["cases"]
        cls.arrays = np.load(KEYS / "channels.npz")
        cls.hours = cls.arrays["sample_hours"]

    def assert_channel(self, case_id: str, name: str, values: np.ndarray) -> None:
        key = f"{case_id}|{name}"
        daily = values.reshape(365, 24).sum(axis=1)
        self.assertLessEqual(float(np.abs(daily - self.arrays[key + "|daily"]).max()), 24 * TOLERANCE)
        self.assertLessEqual(float(np.abs(values[self.hours] - self.arrays[key + "|sample"]).max()), TOLERANCE)
        if key + "|full" in self.arrays:
            self.assertLessEqual(float(np.abs(values - self.arrays[key + "|full"]).max()), TOLERANCE)

    def run_case(self, case: dict) -> dict:
        unit = dwelling(case["inputs"])
        if case["kind"] == "occupancy_and_lighting":
            if unit.residents == 0:
                return {}  # the caller skips zero-resident apartment units
            return generate_occupancy_and_lighting(unit, case["unit_seed"], "ruby_mt")
        if "state_runs" in case:
            activities = activities_from_runs(case["state_runs"], case["offset_minutes"])
            return dwelling_channels(unit, activities, unit_streams("ruby_mt", case["unit_seed"]))
        return generate_dwelling(unit, case["unit_seed"], "ruby_mt")

    def test_every_native_unit(self):
        for case in self.cases:
            with self.subTest(case=case["case_id"]):
                if case["error"]:
                    # Upstream fails comparing with NaN when a component has no events.
                    with self.assertRaises(GeneratorError) as caught:
                        self.run_case(case)
                    self.assertEqual(caught.exception.code, "zero_generated_integral")
                    continue
                result = self.run_case(case)
                self.assertEqual(sorted(result), case["channels"])
                for name in case["channels"]:
                    self.assert_channel(case["case_id"], name, result[name])


class DiscreteOutcomes(unittest.TestCase):
    def test_occupant_types_and_offsets_are_identical(self):
        cases = json.loads((KEYS / "cases.json").read_text(encoding="utf-8"))["cases"]
        tables = load_tables()
        for case in cases:
            count = int(case["inputs"]["residents"])
            if count == 0 or "state_runs" in case or case["occupant_types"] is None:
                continue
            streams = unit_streams("ruby_mt", case["unit_seed"])
            activities = simulate_activities(count, streams["main"], tables)
            with self.subTest(case=case["case_id"]):
                self.assertEqual(activities.occupant_types, case["occupant_types"])
                self.assertEqual(activities.offset_minutes, case["offset_minutes"])


class RubyStreamDraws(unittest.TestCase):
    @unittest.skipUnless(REFERENCE_VECTORS.exists(), "native draw vectors not present")
    def test_draws_match_ruby(self):
        data = json.loads(REFERENCE_VECTORS.read_text(encoding="utf-8"))
        for vector in data["random_vectors"]:
            stream = RubyStream(int(vector["seed"]))
            for draw in vector["draws"]:
                value = stream.random() if draw["limit"] is None else stream.randbelow(draw["limit"])
                self.assertEqual(value, draw["value"])


if __name__ == "__main__":
    unittest.main()
