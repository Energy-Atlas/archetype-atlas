"""Every documented example request generates a bundle."""
import json
from pathlib import Path
import unittest

from atlas_schedules.generator import generate

EXAMPLES = Path(__file__).resolve().parents[2] / "docs/examples/schedule-generator"


class Examples(unittest.TestCase):
    def test_examples_generate(self):
        paths = sorted(EXAMPLES.glob("*.json"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(example=path.name):
                bundle = generate(json.loads(path.read_text(encoding="utf-8")))
                self.assertTrue(bundle["schedules"])


if __name__ == "__main__":
    unittest.main()
