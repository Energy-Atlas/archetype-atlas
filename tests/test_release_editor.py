"""Release 2.0.0 IDs follow interpreter-independent content rules (ADR 0046 section 8, decision U)."""
import json
import unittest

from scripts import atlas_snapshot, release_editor
from scripts.atlas_format import h6


class RuleTests(unittest.TestCase):
    def test_hashes_ignore_float_noise_below_nine_digits(self):
        a = {'u': 0.123456789012345, 'layers': [{'k': 1.0000000000000002}]}
        b = {'u': 0.123456789012399, 'layers': [{'k': 1.0}]}
        self.assertEqual(h6(release_editor.rounded(a)), h6(release_editor.rounded(b)))
        self.assertNotEqual(h6(release_editor.rounded(a)), h6(release_editor.rounded({**a, 'u': 0.1234568})))
        self.assertIs(release_editor.rounded(True), True)

    def test_substitution_keeps_suffixes(self):
        substitute = release_editor.Substitution({'a.b.c.123456': 'a.b.c.abcdef'})
        self.assertEqual(substitute('"a.b.c.123456.5-a.unified" "a.b.c.123456:composition" "x.a.b.c.123456"'),
                         '"a.b.c.abcdef.5-a.unified" "a.b.c.abcdef:composition" "x.a.b.c.123456"')


class Release200IdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = atlas_snapshot.files()

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.files

    def test_every_commercial_id_agrees_with_its_rule(self):
        self.assertEqual(release_editor.edit(self.files)[1], {})

    def test_id_map_points_at_ids_in_the_release(self):
        ids = json.loads(self.files[release_editor.ID_MAP])['ids']
        text = b'\n'.join(d for p, d in self.files.items() if p != release_editor.ID_MAP).decode('utf-8')
        for old, new in list(ids.items())[::97]:
            self.assertIn(new, text, old)
            self.assertNotIn('"'+old+'"', text, old)


if __name__ == '__main__':
    unittest.main()
