import pathlib
import tempfile
import unittest

from scripts import reproduce
from scripts.build import build_atlas, write_atlas


class ReproduceTests(unittest.TestCase):
    def test_rebuild_detects_canonical_byte_changes(self):
        with tempfile.TemporaryDirectory() as d:
            target = pathlib.Path(d)
            write_atlas(build_atlas(pilot=True), target)
            self.assertEqual(reproduce.check_rebuild(target, pilot=True), [])
            with (target/'programs.json').open('a') as f:
                f.write(' ')
            self.assertIn('programs.json', reproduce.check_rebuild(target, pilot=True))
