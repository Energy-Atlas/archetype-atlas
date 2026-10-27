"""Programs for the construction-only folders (ADR 0039) and release 1.2.0."""
import json
import unittest
from collections import defaultdict

from scripts import atlas_minor_release, construction_only_programs as cop
from scripts.common import ROOT, load_json

INPUT = cop.OUTPUT
RELEASE = atlas_minor_release.target('1.2.0')


@unittest.skipUnless(INPUT.exists(), 'construction-only input not generated')
class InputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = load_json(INPUT)
        cls.folders = defaultdict(list)
        for p in cls.document['programs']:
            if p['evidence_view'] == 'source':
                cls.folders[(p['template'], p['building_type'])].append(p)

    def test_every_construction_only_folder_has_programs(self):
        self.assertEqual(set(self.folders), cop.wanted())
        self.assertEqual(len(self.folders), 51)

    def test_general_mixes_only_and_one_per_multi_program_type(self):
        for key, programs in self.folders.items():
            leaves = [p for p in programs if p['derivation'] != 'composed']
            mixes = [p for p in programs if p['derivation'] == 'composed']
            with self.subTest(folder=key):
                self.assertTrue(all(m['detail'] == 'GeneralMix' for m in mixes))
                self.assertEqual(len(mixes), 1 if len(leaves) > 1 else 0)

    def test_generic_office_borrows_the_large_detailed_office_areas(self):
        sources = {s['id']: s['path'] for s in self.document['source_files']}
        for composition in self.document['compositions']:
            program = next(p for p in self.document['programs'] if p.get('composition_id') == composition['id'])
            if program['building_type'] == 'Office':
                paths = {sources.get(m['source_geometry_file_id']) for m in composition['members']}
                self.assertEqual(paths, {'data/geometry/ASHRAELargeOfficeDetailed.osm'})

    def test_no_record_collides_with_the_frozen_definitions(self):
        frozen = {p['id'] for p in load_json(ROOT/'data/definition-releases/v0.1.1/programs.json')}
        self.assertEqual({p['id'] for p in self.document['programs']} & frozen, set())

    def test_spreadsheet_errors_stay_unknown(self):
        evidence = {e['id']: e for e in self.document['provenance']}
        errors = [p for p in self.document['programs'] if p['derivation'] != 'composed' and p['evidence_view'] == 'source'
                  for l in p['loads'] if l['quantity'] == 'lighting'
                  and evidence.get(l['evidence_id'], {}).get('original_value') == '#N/A']
        self.assertEqual(len(errors), 6)
        self.assertTrue(all(l['value'] is None for p in errors for l in p['loads'] if l['quantity'] == 'lighting'))

    def test_fillings_follow_the_approved_rules(self):
        rules = {r['rule'] for r in self.document['resolutions']}
        self.assertLessEqual(rules, {'reviewed_no_gas_equipment', 'reviewed_no_occupancy', 'reviewed_no_lighting',
                                     'reviewed_unconditioned', 'reviewed_no_hot_water', 'explicit_zero_magnitude',
                                     'source_complete_no_water_draw', 'reviewed_borrowed_value',
                                     'reviewed_placeholder_zero', 'reviewed_building_setpoints'})
        programs = {p['source_id']: p for p in self.document['programs'] if p['evidence_view'] == 'source'}
        for row in self.document['resolutions']:
            name = programs[row['record_id']]['name'].lower()
            if row['rule'] == 'reviewed_no_occupancy':
                self.assertFalse(any(w in name for w in ('corridor', 'stair', 'storage', 'restroom', 'utility')), name)
            if row['rule'] in ('reviewed_no_lighting', 'reviewed_unconditioned'):
                self.assertTrue(any(w in name for w in ('shaft', 'machine room', 'attic', 'plenum')), name)
        twins = [p for p in self.document['programs'] if p['evidence_view'] == 'reviewed' and p['derivation'] != 'composed']
        self.assertEqual({p['source_definition_id'] for p in twins} <= {p['id'] for p in programs.values()}, True)

    def test_borrowed_values_cite_their_donor(self):
        rows = [r for r in self.document['resolutions'] if r['rule'] == 'reviewed_borrowed_value'
                and r['field'].endswith(('_per_m2', '_W_m2'))]
        self.assertEqual(len(rows), 71)
        for row in rows:
            with self.subTest(row=row['id']):
                self.assertEqual(row['basis'], 'research_assumption')
                self.assertEqual(len(row['evidence']), 2)  # the target's null and the donor's value
                self.assertIsNotNone(row['evidence'][1]['original_value'])
        # What stays unresolved is support-space schedules, whose absence the export accepts.
        self.assertEqual({u['field'] for u in self.document['unresolved']},
                         {'service_water_heating_schedule_id', 'electric_equipment_schedule_id'})

    def test_hot_water_paths_follow_the_source_branches(self):
        branches = {(d['building_type'], d['source_branch']) for d in self.document['water_paths']['draw_paths']}
        self.assertIn(('College', 'lumped_main_draw'), branches)
        self.assertIn(('Laboratory', 'space_type_main_draw'), branches)
        self.assertIn(('TallBuilding', 'tall_building_space_draws'), branches)
        self.assertIn(('SuperTallBuilding', 'tall_building_hotel_floors'), branches)
        self.assertIn(('Office', 'borrowed_lumped_main_draw_per_area'), branches)
        self.assertFalse(any(b.endswith('DataCenterHighITE') for b, _ in branches))
        tall = {d['end_use'] for d in self.document['water_paths']['draw_paths'] if d['building_type'] == 'TallBuilding'}
        self.assertEqual(tall, {'main', 'booster', 'laundry'})

    def test_generic_office_hot_water_is_the_borrowed_per_area_draw(self):
        paths = [d for d in self.document['water_paths']['draw_paths'] if d['building_type'] == 'Office']
        self.assertEqual(len(paths), 5)
        for d in paths:
            area = d['alternate_original_total']
            self.assertAlmostEqual(d['rated_flow_per_area_m3_s_m2'], d['original_flow']*cop.GALLON_M3/60/area, places=18)
            self.assertIn('research assumption', d['interpretation_note'])

    def test_area_defaults_are_pinned(self):
        self.assertEqual(sorted(self.document['area_defaults']), ['2.6.0', '2.7.0', '2.7.1', '2.8.0'])
        self.assertEqual({v['default'] for v in self.document['area_defaults'].values()}, {'Yes'})


@unittest.skipUnless((RELEASE/'manifest.json').exists(), 'release 1.2.0 not written')
class ReleaseTests(unittest.TestCase):
    def test_release_holds_release_1_1_0(self):
        listed = atlas_minor_release.verify('1.2.0')
        earlier = json.loads((ROOT/'data/atlas-releases/v1.1.0/manifest.json').read_text())
        changed = [p for p, e in earlier['files'].items() if listed['files'].get(p) != e]
        self.assertEqual(sorted(changed), ['README.md', 'evidence/glossary.json'])
        self.assertEqual(listed['deleted'], earlier['deleted'])

    def test_new_folders_have_programs_and_export(self):
        from scripts.atlas_exports import Release
        release = Release(release='1.2.0')
        folders = {(p['template'], p['building_type']) for _, p in release.programs.values()}
        self.assertLessEqual(cop.wanted(), folders)
        # Every new program exports in both versions (ADR 0039 sections 6 and 10); a sample of the formerly blocked.
        for prefix in ('90-1-2019.college.general.', '90-1-2013.tall-building.source.corridor', 'doe-ref-pre-1980.office.general.',
                       'doe-ref-pre-1980.courthouse.source.cell', '90-1-2019.office.source.undefined',
                       'doe-ref-1980-2004.college.source.corridor', '90-1-2007.courthouse.general.'):
            program_id = next(p for p in release.program_ids() if p.startswith(prefix))
            self.assertEqual(release.program(program_id, 'source')['source']['release'], 'atlas-release-1.2.0')
            self.assertEqual(release.program(program_id, 'filled')['version'], 'filled')
        program_id = next(p for p in release.program_ids() if p.startswith('90-1-2007.large-data-center-high-ite.source.'))
        self.assertEqual(release.program(program_id, 'filled')['version'], 'filled')


if __name__ == '__main__':
    unittest.main()
