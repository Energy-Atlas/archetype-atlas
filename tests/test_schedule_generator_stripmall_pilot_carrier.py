"""The tracked Stripmall pilot carrier extract is pinned and reproducible."""
import gzip
import json
import unittest

from atlas_schedules.errors import GeneratorError
from scripts import schedule_generator_stripmall_pilot_carrier as carrier
from scripts.common import ROOT


class StripmallPilotCarrier(unittest.TestCase):
    def test_tracked_extract_matches_lock_and_rebuilds_when_pilot_present(self):
        lock = json.loads((ROOT/carrier.LOCK).read_bytes())
        self.assertTrue(carrier.verify_extract()['passed'])
        if (ROOT/lock['original']['path']).exists(): self.assertTrue(carrier.verify_extract(rebuild=True)['rebuilt'])

    def test_missing_field_rejects(self):
        z = (ROOT/json.loads((ROOT/carrier.LOCK).read_bytes())['extract']['path']).read_bytes()
        payload = json.loads(gzip.decompress(z)); del payload['cases'][0]['registration']
        with self.assertRaises(GeneratorError): carrier.build_extract(json.dumps(payload).encode(), 'pilot.json')


if __name__ == '__main__': unittest.main()
