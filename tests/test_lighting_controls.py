"""Release 1.5.0: lighting controls and plenum programs (ADR 0044)."""
import json
import math
import os
import unittest
from collections import Counter
from pathlib import Path

from scripts import atlas_minor_release, lighting_controls, plenum_aliases
from scripts.common import ROOT, load_json

RELEASE = atlas_minor_release.target('1.5.0')
PROTOTYPES = Path(os.environ.get('ATLAS_PROTOTYPE_ROOT', ''))


class InputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = load_json(lighting_controls.OUTPUT)
        cls.records = {(r['template'], r['building_type'], r['space_type']): r['lighting_controls'] for r in cls.document['records']}

    def test_scan_counts(self):
        scan = self.document['scan']
        self.assertEqual({t: s['with_controls'] for t, s in scan.items() if t.startswith(('IECC', '90.1'))},
                         {'90.1-2007': 0, '90.1-2013': 247, '90.1-2019': 247, 'IECC 2006': 0, 'IECC 2009': 0,
                          'IECC 2012': 106, 'IECC 2015': 247, 'IECC 2018': 247, 'IECC 2021': 247})
        self.assertTrue(all(s['models'] == 304 for t, s in scan.items() if t.startswith(('IECC', '90.1'))))
        for key in ('doe-reference-pre1980', 'doe-reference-post1980', 'residential-prototypes', 'manufactured-housing-prototypes'):
            self.assertEqual(scan[key]['with_controls'], 0, key)

    def test_medium_office_2021(self):
        block = self.records[('IECC 2021', 'MediumOffice', 'WholeBuilding - Md Office')]
        d = block['daylighting']
        self.assertEqual((d['control_type'], d['method'], d['illuminance_setpoint_lux'], d['controlled_zones'], d['zones']),
                         ('continuous_off', 'split_flux', 377.0, 12, 15))
        self.assertAlmostEqual(d['controlled_floor_fraction'], 0.4078, 4)
        self.assertAlmostEqual(d['controlled_lighting_fraction'], 0.2133, 4)
        self.assertIsNone(self.records[('IECC 2021', 'MediumOffice', 'Plenum')]['daylighting'])
        self.assertIsNone(self.records[('90.1-2007', 'MediumOffice', 'WholeBuilding - Md Office')]['daylighting'])

    def test_cold_climate_skylights_differ(self):
        block = self.records[('90.1-2019', 'Warehouse', 'Fine')]
        self.assertEqual(sorted(block['daylighting_by_climate']), ['6A', '6B', '7A', '8A'])
        self.assertEqual(sorted(block['climate_evidence_ids']), ['6A', '6B', '7A', '8A'])

    def test_every_evidence_cited_exists(self):
        evidence = {e['id'] for e in self.document['provenance']}
        sources = {s['id'] for s in self.document['source_files']}
        self.assertLessEqual({e['source_file_id'] for e in self.document['provenance']}, sources)
        for block in [*self.records.values(), *self.document['templates_without_controls'].values()]:
            cited = [block.get('evidence_id'), *block.get('climate_evidence_ids', {}).values(),
                     (block.get('standards_rule') or {}).get('evidence_id')]
            self.assertLessEqual({e for e in cited if e}, evidence)

    def test_90_1_records_carry_the_standards_rule(self):
        rules = [b for (t, _, _), b in self.records.items() if t.startswith('90.1')]
        self.assertGreater(sum('standards_rule' in b for b in rules), 0.95*len(rules))
        office = self.records[('90.1-2019', 'LargeOffice', 'WholeBuilding - Lg Office-others')]['standards_rule']
        self.assertEqual((office['primary_sidelit_nongeometry_fraction'], office['secondary_sidelit_nongeometry_fraction']), (0.68, 0.32))


@unittest.skipUnless((PROTOTYPES/'commercial-iecc').is_dir(), 'set ATLAS_PROTOTYPE_ROOT to the extracted PNNL prototypes')
class AnswerKeyTests(unittest.TestCase):
    """Independent reads of the IDFs against the committed records (ADR 0035 tolerance)."""

    def control_fractions(self, path, zones):
        from scripts import idf_reader
        model = idf_reader.Model(path)
        floors = Counter()
        for s in model.surfaces():
            if s['type'] == 'floor':
                floors[s['zone'].lower()] += idf_reader.area(s['vertices'])
        area = {z: floors[z]*model.zones[z]['multiplier'] for z in zones}
        controlled = {f[1].lower(): math.fsum(float(f[i+1]) for i in range(13, len(f), 3) if f[i].strip())
                      for f in model.all('daylighting:controls')}
        return math.fsum(area[z] for z in zones if z in controlled)/math.fsum(area.values())

    def test_controlled_floor_fractions(self):
        document = load_json(lighting_controls.OUTPUT)
        records = {(r['template'], r['building_type'], r['space_type']): r['lighting_controls'] for r in document['records']}
        cases = [('commercial-iecc', 'IECC', 'OfficeMedium', '2021', 'Buffalo', 'IECC 2021', 'MediumOffice', 'WholeBuilding - Md Office'),
                 ('commercial-ashrae901', 'ASHRAE901', 'Warehouse', '2019', 'Fairbanks', '90.1-2019', 'Warehouse', 'Fine'),
                 ('commercial-iecc', 'IECC', 'SchoolPrimary', '2012', 'Miami', 'IECC 2012', 'PrimarySchool', 'Gym')]
        for family, prefix, pnnl, year, city, template, building_type, space_type in cases:
            path = PROTOTYPES/family/f'{prefix}_{pnnl}'/f'{prefix}_{pnnl}_STD{year}_{city}.idf'
            from scripts.iecc_commercial_zones import CITIES
            models = lighting_controls.TypeModels(lighting_controls.Extract(PROTOTYPES), family, pnnl, year,
                                                  lighting_controls.template_tags(year) if prefix == 'ASHRAE901'
                                                  else lighting_controls.Lookup())
            zones = models.groups[space_type]
            block = records[(template, building_type, space_type)]
            daylighting = block.get('daylighting_by_climate', {}).get(CITIES[city][1], block['daylighting'])
            expected = self.control_fractions(path, zones)
            with self.subTest(template=template, building_type=building_type, city=city):
                got = 0.0 if daylighting is None else daylighting['controlled_floor_fraction']
                self.assertAlmostEqual(got, expected, delta=1e-6)


class PlenumTests(unittest.TestCase):
    def test_every_gap_is_aliased_and_none_is_left(self):
        document = load_json(plenum_aliases.OUTPUT)
        gaps = load_json(ROOT/'data/program-inputs/construction-only-v1.json')['coverage_gaps']
        self.assertEqual(document['coverage_gaps'], [])
        self.assertEqual({(g['template'], g['building_type'], g['space']) for g in gaps},
                         {(a['template'], a['building_type'], a['space']) for a in document['aliased_spaces']})
        sources = [p for p in document['programs'] if p['evidence_view'] == 'source']
        self.assertEqual(len(sources), 19)
        self.assertEqual({p['name'].split('_')[0] for p in sources}, {'Plenum'})
        self.assertEqual(len(document['programs']), 38)
        rules = Counter(r['rule'] for r in document['resolutions'])
        for rule in ('reviewed_no_occupancy', 'reviewed_no_lighting', 'reviewed_no_hot_water', 'reviewed_unconditioned'):
            self.assertEqual(rules[rule], 19, rule)
        self.assertEqual({u['field'] for u in document['unresolved']}, {'electric_equipment_schedule_id'})


@unittest.skipUnless((RELEASE/'manifest.json').exists(), 'release 1.5.0 not written')
class Release150Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.atlas_exports import Release
        cls.listed = atlas_minor_release.verify('1.5.0')
        cls.release = Release(release='1.5.0')

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.listed, cls.release

    def test_every_commercial_leaf_program_states_its_controls(self):
        states = Counter()
        for pid, (_, stored) in self.release.programs.items():
            composed = stored['derivation'] == 'composed'
            with self.subTest(program=pid):
                self.assertEqual('lighting_controls' in stored, not composed)
            if not composed:
                block = stored['lighting_controls']
                states[(stored['template'].split(' ')[0], block['status'], block.get('daylighting') is not None)] += 1
        self.assertEqual(states[('DOE', 'unknown', False)], 0)
        self.assertEqual(states[('IECC', 'unknown', False)], 0)
        self.assertGreater(states[('90.1-2019', 'known', True)] + states[('90.1-2013', 'known', True)], 0)

    def test_commercial_programs_export_as_5_4_0(self):
        for prefix, version in (('iecc-2021.medium-office.source.whole', 'source'), ('90-1-2019.warehouse.source.', 'filled'),
                                ('doe-ref-pre-1980.hospital.source.', 'filled')):
            program_id = next(p for p in self.release.program_ids() if p.startswith(prefix))
            document = self.release.program(program_id, version)
            self.assertEqual((document['schema_version'], document['source']['release']), ('5.4.0', 'atlas-release-1.5.0'))
            if prefix.startswith('doe'):
                self.assertIsNone(document['lighting_controls']['daylighting'])

    def test_dwellings_and_their_constructions_export(self):
        dwellings = self.release.dwellings
        iecc = next(p for p in dwellings.program_ids() if p.startswith('iecc-2021.single-family.gas-appliances.'))
        document = self.release.program(iecc, 'source')
        self.assertEqual((document['schema_version'], document['source']['release']), ('5.4.0', 'atlas-release-1.5.0'))
        self.assertNotIn('lighting_controls', document)
        stored = dwellings.stored(iecc)
        construction = self.release.construction(stored['construction_set_id'], '4-a.slab', 'detailed')
        self.assertEqual(construction['release'], 'atlas-release-1.5.0')

    def test_plenum_programs_export_filled(self):
        for pid, (_, stored) in self.release.programs.items():
            if stored['name'].startswith('Plenum_') and stored['building_type'] in ('TallBuilding', 'Laboratory'):
                with self.subTest(program=pid):
                    self.assertEqual(self.release.program(pid, 'filled')['schema_version'], '5.4.0')

    def test_plenum_programs_join_the_folders(self):
        names = Counter((stored['template'], stored['building_type']) for _, stored in self.release.programs.values()
                        if stored['name'].startswith('Plenum_'))
        self.assertEqual(names[('90.1-2013', 'TallBuilding')], 1)
        self.assertEqual(names[('DOE Ref Pre-1980', 'MediumOfficeDetailed')], 1)


@unittest.skipUnless((RELEASE/'manifest.json').exists() and os.environ.get('ATLAS_RELEASE_CHECK'),
                     'set ATLAS_RELEASE_CHECK=1 to rebuild release 1.5.0 (about 5 minutes)')
class Release150CheckTests(unittest.TestCase):
    def test_release_reproduces_byte_for_byte(self):
        atlas_minor_release.check('1.5.0')


if __name__ == '__main__':
    unittest.main()
