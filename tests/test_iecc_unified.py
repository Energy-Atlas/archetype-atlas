"""Release 1.6.0: unified constructions of the IECC commercial family (ADR 0045)."""
import math
import os
import unittest
from collections import Counter

from scripts import atlas_minor_release, iecc_unified
from scripts.common import load_json

RELEASE = atlas_minor_release.target('1.6.0')
IDFS = iecc_unified.idf_root()


class CompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import iecc_commercial_overlay
        cls.documents = iecc_commercial_overlay.constructions()
        cls.areas = load_json(iecc_unified.OUTPUT)['areas']

    def unified(self, cid):
        edition, building_type, climate = self.documents.where[cid]
        detailed, _ = self.documents.pair(cid)
        return detailed, iecc_unified.unified(detailed, self.areas[edition][building_type][climate])

    def test_every_context_is_ready(self):
        states = Counter()
        for cid in sorted(self.documents.where)[::37]:
            states[self.unified(cid)[1]['status']] += 1
        self.assertEqual(set(states), {'ready'})

    def test_medium_office_wall_weights_follow_net_areas(self):
        cid = next(c for c, w in self.documents.where.items() if w == ('2021', 'MediumOffice', '5A'))
        detailed, unified = self.unified(cid)
        wall = unified['components']['ExteriorWall']
        self.assertEqual(wall['status'], 'ready')
        self.assertAlmostEqual(math.fsum(r['weight'] for r in wall['derivation']['contributors']), 1.0, 12)
        self.assertEqual(wall['derivation']['weight_basis'], 'source_model_net_component_area')
        window = unified['components']['ExteriorWindow']['derivation']['source_reference_area_m2']
        walls = wall['derivation']['source_reference_area_m2']
        self.assertAlmostEqual(window/(window+walls), detailed["fenestration_defaults"]["all"]["S"], 2)
        self.assertEqual(unified['mass_accounting'], detailed['mass_accounting'])
        self.assertEqual(unified['infiltration'], detailed['infiltration'])

    def test_adiabatic_ffactor_floors_are_listed(self):
        cid = next(c for c, w in self.documents.where.items() if w == ('2015', 'SmallOffice', '3C'))
        _, unified = self.unified(cid)
        excluded = unified['provenance']['excluded_ground_constructions']['entries']
        self.assertTrue(any(e['role'] == 'InteriorFloor' for e in excluded))


@unittest.skipUnless(IDFS.is_dir(), 'set ATLAS_PROTOTYPE_ROOT to the extracted PNNL prototypes')
class AreaTests(unittest.TestCase):
    def test_areas_reproduce(self):
        self.assertEqual(iecc_unified.encode(iecc_unified.build(IDFS)), iecc_unified.OUTPUT.read_bytes())


@unittest.skipUnless((RELEASE/'manifest.json').exists(), 'release 1.6.0 not written')
class Release160Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.atlas_exports import Release
        cls.listed = atlas_minor_release.verify('1.6.0')
        cls.release = Release(release='1.6.0')

    def test_iecc_contexts_export_unified(self):
        sets = [s for s in self.release.constructions.sets if s.startswith('iecc-') and
                any(p.startswith('commercial/') and p.endswith(f'/constructions/{s}.json') for p in self.release.files)]
        self.assertEqual(len(sets), 96)
        for sid in sets[::11]:
            key = sorted(self.release.constructions.sets[sid]['contexts'])[0]
            with self.subTest(set=sid, context=key):
                document = self.release.construction(sid, key, 'unified')
                self.assertEqual((document['schema_version'], document['status']), ('3.1.0', 'ready'))

    def test_programs_still_export_as_5_4_0(self):
        program_id = next(p for p in self.release.program_ids() if p.startswith('iecc-2021.medium-office.source.whole'))
        document = self.release.program(program_id, 'source')
        self.assertEqual((document['schema_version'], document['source']['release']), ('5.4.0', 'atlas-release-1.6.0'))
        self.assertIn('lighting_controls', document)


@unittest.skipUnless((RELEASE/'manifest.json').exists() and os.environ.get('ATLAS_RELEASE_CHECK'),
                     'set ATLAS_RELEASE_CHECK=1 to rebuild release 1.6.0 (about 5 minutes)')
class Release160CheckTests(unittest.TestCase):
    def test_release_reproduces_byte_for_byte(self):
        atlas_minor_release.check('1.6.0')


if __name__ == '__main__':
    unittest.main()
