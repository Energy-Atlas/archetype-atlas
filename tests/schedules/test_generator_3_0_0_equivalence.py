"""Generator 4.0.0, assembling its recipes from the release, reproduces generator 3.0.0's bundles (ADR 0051).

The key `tests/answer_keys/orchestration/generator-3-0-0-bundles.json.gz` holds 3.0.0 bundles of a fixed
sample of requests over every recipe kind, shared services and the example requests, captured by
`scripts/capture/generator_3_0_0_bundles.py` from the packaged recipes before they left the tree. Each
3.0.0 request (definition IDs) is translated through the release's definition map; the 4.0.0 bundle
must then agree in every owner's loads, controls, extent and generation record, and in every
schedule's unit, sum, maximum and sampled hours, within 1e-9. The bundle differs only in what 4.0.0
adds (`release`, each owner's `values`) and in the versions, and in the IDs: a 3.0.0 owner named its
definition program or service, which the 4.0.0 owner names by its release ID (also inside the keys of
composition members and apartment water owners).
"""
import gzip
import json
from pathlib import Path
import re
import unittest

import numpy as np

from atlas_schedules.errors import GeneratorError
from atlas_schedules.generator import generate
from atlas_schedules.release import definition_map, translate

ANSWER_KEY = Path(__file__).resolve().parents[1] / "answer_keys/orchestration/generator-3-0-0-bundles.json.gz"
ADDED = ("values",)   # owner fields 4.0.0 adds
TOLERANCE = 1e-9
DEFINITION_ID = re.compile(r"(program|service)-[0-9a-f]{24}")


def release_ids(value, mapped: dict):
    """The value with every definition ID written as its release ID (recursively through strings)."""
    def one(match):
        text = match.group(0)
        if text.startswith("program-"):
            return mapped["programs"][text]["program_id"]
        return mapped["services"][text]
    if isinstance(value, str):
        return DEFINITION_ID.sub(one, value)
    if isinstance(value, dict):
        return {k: release_ids(v, mapped) for k, v in value.items()}
    if isinstance(value, list):
        return [release_ids(v, mapped) for v in value]
    return value


def legacy_fixed(expected: dict, owner: dict) -> dict:
    """The stated exception (ADR 0051 section 3): a 90.1 apartment-building fixed recipe's legacy form kept a
    zero-density occupancy slot, which the release values leave out, and dropped heat fractions the release
    knows. Applies only to a fixed programme owner (no generation record) from a definition ID."""
    if not (expected["kind"] == "program" and expected["program_id"].startswith("program-") and expected["generation"] == {}):
        return expected
    dropped = any(c["slot"] == "occupants" for c in expected["controls"]) and not any(c["slot"] == "occupants" for c in owner["controls"])
    return {**expected,
            "controls": [c for c in expected["controls"] if not (dropped and c["slot"] == "occupants")],
            "schedules": {s: v for s, v in expected["schedules"].items() if not (dropped and s == "occupants")},
            "loads": [{**l, "heat_fractions": ...} if l["heat_fractions"] is None else l for l in expected["loads"]]}


def owner_equal(test, expected: dict, owner: dict, bundle: dict, hours: list) -> None:
    expected = legacy_fixed(expected, owner)
    expected = {**expected, **release_ids({k: expected[k] for k in ("key", "program_id", "service_id", "generation")},
                                          definition_map())}
    test.assertEqual(set(owner) - set(ADDED), set(expected))
    for field in ("key", "kind", "program_id", "service_id", "extent", "multiplicity", "controls", "generation"):
        test.assertEqual(owner[field], expected[field], field)
    test.assertEqual(len(owner["loads"]), len(expected["loads"]))
    for load, want in zip(owner["loads"], expected["loads"]):
        for field in ("slot", "quantity", "unit", "basis", "fuel", "host", "heat_fractions"):
            if field == "heat_fractions" and want[field] is ...:
                test.assertIsInstance(load[field], dict)   # known in the release, unknown in the legacy form
                continue
            test.assertEqual(load[field], want[field], field)
        for field in ("annual_total", "amplitude"):
            test.assertAlmostEqual(load[field], want[field], delta=TOLERANCE * max(1.0, abs(want[field])), msg=load["slot"])
    test.assertEqual(sorted(owner["schedules"]), sorted(expected["schedules"]))
    for slot, want in expected["schedules"].items():
        entry = bundle["schedules"][owner["schedules"][slot]]
        values = np.asarray(entry["values"], dtype=float)
        test.assertEqual(entry["unit"], want["unit"], slot)
        test.assertAlmostEqual(float(values.sum()), want["sum"], delta=TOLERANCE * max(1.0, abs(want["sum"])), msg=slot)
        test.assertAlmostEqual(float(values.max()), want["max"], delta=TOLERANCE * max(1.0, abs(want["max"])), msg=slot)
        np.testing.assert_allclose(values[hours], np.asarray(want["sampled"]), rtol=0, atol=TOLERANCE, err_msg=slot)


class Generator300Equivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with gzip.open(ANSWER_KEY, "rb") as handle:
            cls.key = json.loads(handle.read().decode("utf-8"))

    @classmethod
    def tearDownClass(cls):
        del cls.key

    def test_key_covers_every_kind(self):
        kinds = {case["id"].split("/")[0] for case in self.key["cases"]}
        self.assertEqual(kinds, {"commercial", "fixed", "composition", "apartment_unit", "residential", "service", "example"})
        self.assertEqual(self.key["generator_version"], "3.0.0")
        self.assertGreaterEqual(len(self.key["cases"]), 250)

    def test_every_case_reproduces(self):
        hours = self.key["sample_hours"]
        retired = definition_map()["retired"]
        skipped = 0
        for case in self.key["cases"]:
            with self.subTest(case=case["id"]):
                request = translate(case["request"])
                if any(i.get("program_id") in retired for i in request["instances"]):
                    # The 12 hotel corridor compositions no release program holds (ADR 0051 section 3).
                    with self.assertRaisesRegex(GeneratorError, "translate"):
                        generate(request)
                    skipped += 1
                    continue
                self.assertEqual(request["schema_version"], "4.0.0")
                bundle = generate(request)
                self.assertEqual(bundle["schema_version"], "4.0.0")
                self.assertEqual([o["key"] for o in bundle["owners"]],
                                 [release_ids(o["key"], definition_map()) for o in case["owners"]])
                for owner, expected in zip(bundle["owners"], case["owners"]):
                    owner_equal(self, expected, owner, bundle, hours)
                    if owner["kind"] == "program":
                        self.assertIn(owner["values"], ("source", "filled"))
                if case["mixture"]:
                    owner_equal(self, case["mixture"], bundle["mixture"], bundle, hours)
                self.assertEqual(bundle["operating_groups"], case["operating_groups"])
                self.assertEqual(bundle["unit_seeds"], case["unit_seeds"])
        self.assertEqual(skipped, 3)


if __name__ == "__main__":
    unittest.main()
