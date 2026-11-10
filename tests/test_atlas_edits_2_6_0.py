"""Release 2.6.0's record edit over release 2.5.0 (ADR 0065 section 3, ADR 0066): the InteriorCeiling of the
openstudio-standards attic contexts."""
import json
import unittest

from scripts import atlas_constructions, atlas_delta, atlas_edits_2_6_0 as edits, attic_boundary

SMALL_OFFICE = ('90-1-2019.small-office-detailed.construction-package.7eee9d',
                '90-1-2019.small-office-detailed.construction-package.ff7fc8')
CEILING = '90-1-2019.typical-interior-ceiling.e4b01c'
EVIDENCE = 'attic-evidence-16def2'
TEMPLATES = ('90-1-2007', '90-1-2013', '90-1-2019', 'doe-ref-1980-2004', 'doe-ref-pre-1980')
# The sets with an openstudio-standards attic (attic_boundary.candidates over release 2.5.0, ADR 0065 section 3).
SETS = {f'{t}.{b}' for t in TEMPLATES[:3] for b in ('full-service-restaurant', 'office', 'quick-service-restaurant',
                                                     'small-office-detailed', 'small-office')}
SETS |= {f'doe-ref-1980-2004.{b}' for b in ('full-service-restaurant', 'office', 'quick-service-restaurant', 'small-hotel',
                                             'small-office-detailed', 'small-office')}
SETS |= {f'doe-ref-pre-1980.{b}' for b in ('office', 'small-hotel', 'small-office-detailed')}


def suite_of(files):
    return atlas_constructions.read_files({p: d for p, d in files.items() if p.startswith(('commercial/', 'evidence/commercial/'))})


class EditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = atlas_delta.files(edits.BASE)
        cls.edited = edits.edit(cls.base)
        cls.files = cls.edited.resolved(cls.base)
        cls.before, cls.after = suite_of(cls.base), suite_of(cls.files)

    @classmethod
    def tearDownClass(cls):
        del cls.base, cls.edited, cls.files, cls.before, cls.after

    def test_summary(self):
        summary = self.edited.summary
        self.assertEqual(len(summary['interior_ceiling']), 24)
        self.assertEqual(sum(len(v) for v in summary['interior_ceiling'].values()), 568)
        self.assertEqual(summary['unresolved'], [])
        self.assertEqual({sid.rsplit('.construction-package.', 1)[0] for sid in summary['interior_ceiling']}, SETS)
        # The generic office sets hold contexts of several references, so their corrected values are per context.
        self.assertEqual({s.split('.')[1] for s in set(summary['interior_ceiling']) - set(summary['common'])}, {'office'})

    def test_only_construction_sets_move(self):
        self.assertEqual(set(self.edited.ids), set(self.edited.summary['interior_ceiling']))
        self.assertTrue(all('.construction-package.' in old for old in self.edited.ids))
        self.assertEqual(self.edited.ids[SMALL_OFFICE[0]], SMALL_OFFICE[1])
        kinds = sorted({p.split('/')[0] if '/constructions/' not in p else 'constructions' for p in self.edited.files})
        self.assertEqual(kinds, ['constructions', 'evidence', 'id-map-2.3.0.json'])
        evidence = sorted(p for p in self.edited.files if p.startswith('evidence/'))
        self.assertEqual(evidence, sorted([f'evidence/commercial/{t}/library.json' for t in TEMPLATES]
                                          + [f'evidence/commercial/{t}/small-hotel.json' for t in TEMPLATES[3:]]))
        self.assertEqual({p.rsplit('/', 1)[1][:-5] for p in self.edited.removed}, set(self.edited.ids))

    def test_the_evidence_row_is_the_export_row(self):
        rows, ids = attic_boundary.evidence_rows('openstudio_standards_rules', True)
        self.assertEqual(ids[-1], EVIDENCE)
        for template in TEMPLATES:
            library = json.loads(self.files[f'evidence/commercial/{template}/library.json'])
            before = json.loads(self.base[f'evidence/commercial/{template}/library.json'])
            self.assertEqual(library, {**before, EVIDENCE: rows[EVIDENCE]})

    def test_every_corrected_context(self):
        for old, keys in self.edited.summary['interior_ceiling'].items():
            new = self.edited.ids[old]
            for key in keys:
                with self.subTest(set=old, context=key):
                    detailed = self.before.export(old, key, 'detailed')
                    stored = self.before.export(old, key, 'unified')
                    unified = self.after.export(new, key, 'unified')
                    fam, found = attic_boundary.recognise(detailed, stored)
                    expected = attic_boundary._ceiling_correction(fam, stored, detailed, found, EVIDENCE)
                    self.assertEqual(unified['components']['InteriorCeiling']['derivation'], expected['corrected'])
                    self.assertEqual(unified['provenance'][edits.CARRIED], attic_boundary.record_correction(expected, edits.ADR))
                    self.assertIn(EVIDENCE, unified['evidence'])
                    # Nothing else of the unified or detailed document changes, beyond the set ID.
                    moved = json.loads(json.dumps(stored).replace(old, new))
                    rest = {k: v for k, v in unified.items() if k not in ('components', 'provenance', 'evidence')}
                    self.assertEqual(rest, {k: v for k, v in moved.items() if k not in ('components', 'provenance', 'evidence')})
                    self.assertEqual({r: c for r, c in unified['components'].items() if r != 'InteriorCeiling'},
                                     {r: c for r, c in moved['components'].items() if r != 'InteriorCeiling'})
                    self.assertEqual({k: v for k, v in unified['components']['InteriorCeiling'].items() if k != 'derivation'},
                                     {k: v for k, v in moved['components']['InteriorCeiling'].items() if k != 'derivation'})
                    self.assertEqual({k: v for k, v in unified['provenance'].items() if k != edits.CARRIED}, moved['provenance'])
                    self.assertEqual(self.after.export(new, key, 'detailed'),
                                     json.loads(json.dumps(detailed).replace(old, new)))

    def test_small_office_derivation(self):
        old, new = SMALL_OFFICE
        unified = self.after.export(new, '4-a', 'unified')
        self.assertEqual(unified['components']['InteriorCeiling']['derivation'],
                         {'contributors': [{'assembly_id': CEILING, 'reference_area_m2': 0.0, 'weight': 1.0}],
                          'source_reference_area_m2': 0.0, 'weight_basis': 'unique_source_recipe_without_reference_exposure'})
        carried = unified['provenance'][edits.CARRIED]
        self.assertEqual(carried['replaced'], self.before.export(old, '4-a', 'unified')['components']['InteriorCeiling']['derivation'])
        self.assertAlmostEqual(carried['paired_ceiling_area_m2'], 511.15624589999993, places=9)
        self.assertEqual(carried['decision'], 'docs/adr/0066-release-2-6-0.md')

    def test_other_sets_unchanged(self):
        moved = set(self.edited.ids)
        for sid in self.before.sets:
            if sid not in moved:
                self.assertEqual(self.after.sets[sid], self.before.sets[sid], sid)

    def test_the_edit_applies_once(self):
        with self.assertRaisesRegex(ValueError, 'already carries'):
            edits.edit(self.files)


if __name__ == '__main__':
    unittest.main()
