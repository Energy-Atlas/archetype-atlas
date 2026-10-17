"""Every documented example request generates a bundle, and a physical mixture
conserves the building's annual energy."""
import json
import math
from pathlib import Path
import unittest

from atlas_schedules.generator import generate

EXAMPLES = Path(__file__).resolve().parents[2] / "docs/examples/schedule-generator"


def example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


class Examples(unittest.TestCase):
    def test_examples_generate(self):
        paths = sorted(EXAMPLES.glob("*.json"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(example=path.name):
                bundle = generate(json.loads(path.read_text(encoding="utf-8")))
                self.assertTrue(bundle["schedules"])

    def test_physical_mixture_conserves_energy(self):
        # 400 m2 office + 100 m2 shop, participation weight 1 each, per 500 m2.
        bundle = generate(example("office-and-retail.json"))
        owners = {o["key"]: o for o in bundle["owners"]}
        for mixed in bundle["mixture"]["loads"]:
            group = (mixed["quantity"], mixed["fuel"], mixed["host"])
            expected = math.fsum(load["annual_total"] * owners[key]["extent"]["floor_area"]
                                 for key in ("office", "shop") for load in owners[key]["loads"]
                                 if (load["quantity"], load["fuel"], load["host"]) == group)
            with self.subTest(load=mixed["slot"]):
                self.assertAlmostEqual(mixed["annual_total"] * 500, expected, delta=1e-9 * expected)


if __name__ == "__main__":
    unittest.main()
