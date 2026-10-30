"""Local occupant-type mix by composition (plan section 7, O14)."""
from pathlib import Path
import subprocess
import sys
import unittest

from atlas_schedules import generate
from atlas_schedules.errors import GeneratorError
from atlas_schedules.residential.occupancy import load_mix, type_probabilities
from atlas_schedules.residential.tables import load_tables

ROOT = Path(__file__).resolve().parents[2]
RAW = [ROOT / "data/raw/atus/atusact-0324.zip", ROOT / "data/raw/acs/csv_pus-2024-1yr.zip"]
DWELLING = "resstock-sdr.multifamily-5-plus-low-rise.7ak-1980s-500-749ft2-b143851.d8e286"    # ResStock dwelling in Alaska


def request(**extra) -> dict:
    return {"schema_version": "4.0.0", "seed": 7, "instances": [{"key": "home", "program_id": DWELLING}], **extra}


class Tables(unittest.TestCase):
    def test_cells_windows_and_states_are_complete(self):
        mix = load_mix()
        self.assertEqual(len(mix["cells"]), 16)
        self.assertEqual(set(mix["windows"]), {"2003-2019", "2022-2024"})
        for window in mix["windows"].values():
            for cell in mix["cells"]:
                self.assertAlmostEqual(sum(window["cells"][cell]["probabilities"]), 1, delta=1e-5)
        self.assertEqual(len(mix["states"]), 51)
        for state, composition in mix["states"].items():
            self.assertEqual(set(composition), {"under_15", *mix["cells"]}, state)
            self.assertAlmostEqual(sum(composition.values()), 1, delta=1e-5)

    def test_classifier_reproduces_resstock_nationally(self):
        window = load_mix()["windows"]["2003-2019"]
        self.assertLess(window["mean_abs_difference_from_resstock"], 0.015)
        self.assertGreater(window["mean_top_probability"], 0.8)


class Mix(unittest.TestCase):
    def test_state_mix_is_the_cell_composition(self):
        mix, national = load_mix(), list(load_tables().occupant_type_probabilities)
        composition, cells = mix["states"]["NY"], mix["windows"]["2003-2019"]["cells"]
        expected = [composition["under_15"] * p for p in national]
        for cell in mix["cells"]:
            expected = [e + composition[cell] * p for e, p in zip(expected, cells[cell]["probabilities"])]
        total = sum(expected)
        for got, want in zip(type_probabilities("NY", "2003-2019", national), expected):
            self.assertAlmostEqual(got, want / total, delta=1e-12)

    def test_unknown_state_is_rejected(self):
        with self.assertRaises(GeneratorError):
            type_probabilities("ZZ", "2003-2019", [0.25] * 4)

    def test_generator_defaults_to_the_state_mix(self):
        bundle = generate(request())
        self.assertEqual(bundle["occupancy"], {"mix": "state", "window": "2003-2019"})
        shares = bundle["owners"][0]["generation"]["occupant_type_probabilities"]
        national = list(load_tables().occupant_type_probabilities)
        self.assertEqual(shares, type_probabilities("AK", "2003-2019", national))

    def test_national_mix_reproduces_resstock(self):
        bundle = generate(request(occupancy={"mix": "national"}))
        shares = bundle["owners"][0]["generation"]["occupant_type_probabilities"]
        self.assertEqual(shares, list(load_tables().occupant_type_probabilities))

    def test_window_is_selectable(self):
        recent = generate(request(occupancy={"window": "2022-2024"}))
        older = generate(request())
        self.assertNotEqual(recent["owners"][0]["generation"]["occupant_type_probabilities"],
                            older["owners"][0]["generation"]["occupant_type_probabilities"])

    def test_unknown_options_are_rejected(self):
        with self.assertRaises(GeneratorError) as caught:
            generate(request(occupancy={"mix": "county"}))
        self.assertEqual(caught.exception.code, "invalid_request")


@unittest.skipUnless(all(p.exists() for p in RAW),
                     "pinned ATUS/ACS inputs absent (python -m scripts.fetch --lock sources/occupancy-mix-lock.json)")
class Derivation(unittest.TestCase):
    def test_tables_rebuild_identically(self):
        result = subprocess.run([sys.executable, "-m", "scripts.derive_occupancy_mix", "--check"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
