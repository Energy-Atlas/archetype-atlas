"""CITATION.cff names the newest atlas release and the two open licences (ADR 0048)."""
import unittest

import yaml

from scripts import atlas_delta
from scripts.common import ROOT


class CitationTest(unittest.TestCase):
    def setUp(self):
        self.cff = yaml.safe_load((ROOT/'CITATION.cff').read_text(encoding='utf-8'))

    def test_names_the_newest_release(self):
        self.assertEqual(self.cff['version'], atlas_delta.RELEASE)

    def test_licences_and_attribution(self):
        self.assertEqual(self.cff['license'], ['MIT', 'CC-BY-4.0'])
        self.assertIn('"Archetype Atlas, Energy-Atlas"', self.cff['message'])

    def test_required_fields(self):
        self.assertEqual(self.cff['cff-version'], '1.2.0')
        for field in ('message', 'title', 'authors', 'date-released'):
            self.assertTrue(self.cff.get(field), field)


if __name__ == '__main__':
    unittest.main()
