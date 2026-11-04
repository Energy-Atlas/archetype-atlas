"""Release 2.5.0's record edits over release 2.4.0 (ADR 0063), and its exports in Program JSON 6.2.0."""
import json
import math
import unittest
from collections import Counter

from jsonschema import Draft202012Validator

from atlas_schedules import programmes
from atlas_schedules.release import Release as Reader
from scripts import atlas_contracts, atlas_delta, atlas_edits, atlas_edits_2_5_0 as edits, conditioning_sides, release_editor
from scripts.atlas_exports import Release
from scripts.common import ROOT, load_json
from scripts.lighting_controls import space_type
from tests.test_atlas_edits import MemoryStore

T = ('90.1-2007', '90.1-2013', '90.1-2019')
D = ('DOE Ref Pre-1980', 'DOE Ref 1980-2004')
BOTH, HEATING, COOLING = ('heating', 'cooling'), ('heating',), ('cooling',)
# (template, building type, space type): the sides the source equipment does not serve, where 2.4.0 gave a setpoint.
AFFECTED = {
    **{(t, 'Warehouse', 'Bulk'): COOLING for t in T + D},
    **{(t, 'RetailStandalone', 'Entry'): COOLING for t in T + D},
    **{(t, 'SmallHotel', s): COOLING for t in T for s in ('Stair', 'Stair4', 'Mechanical')},
    **{(t, 'SmallHotel', s): BOTH for t in T for s in ('Storage', 'Storage4Front', 'Storage4Rear', 'Laundry')},
    **{(t, 'SmallHotel', s): COOLING for t in D for s in ('Stair', 'Storage')},
    **{(t, 'MidriseApartment', s): BOTH for t in T for s in ('Corridor', 'Corridor_topfloor')},
    **{(t, 'MidriseApartment', 'Corridor'): COOLING for t in D},
    **{(t, 'Outpatient', s): BOTH for t in D for s in ('Elec/MechRoom', 'ElevatorPumpRoom', 'Janitor', 'Stair', 'Toilet', 'Undeveloped')},
    **{(t, 'Courthouse', 'Parking'): BOTH for t in T + D},
    **{(t, b, s): HEATING for t in T for b, s in (('LargeDataCenterHighITE', 'StandaloneDataCenter'),
                                                 ('LargeDataCenterLowITE', 'StandaloneDataCenter'),
                                                 ('SmallDataCenterHighITE', 'ComputerRoom'), ('SmallDataCenterLowITE', 'ComputerRoom'))},
}
EVERY_TEMPLATE = ('warehouse.department.storage-mixed', 'retail-standalone.general.general-mixed',
                  'small-hotel.department.vertical-circulation-mixed', 'small-hotel.department.support-mixed',
                  'small-hotel.general.general-mixed')


class MemoryStore250(MemoryStore):
    def __init__(self, files):
        super().__init__(files)
        self.manifest = {**self.manifest, 'release': edits.RELEASE}
        self.version = edits.RELEASE

    def describe(self):
        return 'release 2.5.0 in memory'


def degrees(files, folder, sid):
    table = json.loads(files[folder+'/schedules.json'])
    return sorted({v for rule in table['schedules'][sid]['rules'] for v in table['days'][rule['day']]})


class EditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = atlas_delta.files(edits.BASE)
        cls.edited = edits.edit(cls.base)
        cls.files = cls.edited.resolved(cls.base)
        cls.sides = load_json(edits.SIDES_INPUT)

    @classmethod
    def tearDownClass(cls):
        del cls.base, cls.edited, cls.files

    def records(self, files=None):
        files = files or self.files
        return {json.loads(d)['id']: (p, json.loads(d)) for p, d in files.items() if p.startswith('commercial/') and '/programs/' in p}

    def test_ids_follow_their_rules_and_no_file_cites_a_moved_id(self):
        self.assertEqual(release_editor.program_ids(self.files), {})
        moved = release_editor.Substitution({old: '@moved@' for old in self.edited.ids})
        stale = [p for p, d in self.files.items() if p.endswith('.json') and not p.startswith('residential/') and p != 'id-map.json'
                 and '@moved@' in moved(d.decode('utf-8'))]
        self.assertEqual(stale, [])
        self.assertEqual(set(self.edited.removed), {p for p in self.base if p not in self.files})
        self.assertFalse(any('.construction-' in i for i in self.edited.ids))
        self.assertEqual(json.loads(edits.id_map_bytes(self.edited.ids))['ids'], self.edited.ids)
        mixes = sum(1 for _, r in self.records(self.base).values() if r['derivation'] == 'composed')
        self.assertEqual(len(self.edited.ids), len(AFFECTED) + mixes)   # every mix gains its coverage

    def test_every_edited_file_meets_its_release_record_schema_and_storage_format(self):
        from scripts import release_schemas
        self.assertEqual(release_schemas.errors(self.edited.files), [])
        for path, data in self.edited.files.items():
            with self.subTest(path=path):
                self.assertEqual(atlas_edits.encode(path, json.loads(data)), data)

    def test_sides_no_equipment_serves_become_explicit_nulls(self):
        before, after = self.records(self.base), self.records()
        changed = {}
        for old, (path, record) in before.items():
            if record['mode'] != 'source':
                continue
            new = after[self.edited.ids.get(old, old)][1]
            sides = tuple(s for s in BOTH if record['parameters'][edits.FIELD[s]] != new['parameters'][edits.FIELD[s]])
            if not sides:
                self.assertEqual(record, {**new, 'id': record['id']}, old)
                continue
            changed[record['template'], record['building_type'], space_type(record)] = sides
            folder = path.split('/programs/')[0]
            conditioning = new['parameters']['conditioning']
            self.assertEqual((conditioning['status'], conditioning['unit']), ('known', 'state'))
            self.assertEqual(conditioning['value'], {f'{s}_enabled': s not in sides for s in BOTH})
            row = json.loads(self.files[f'evidence/{folder}.json'])[conditioning['evidence_id']]
            source = json.loads(self.files['evidence/glossary.json'])['source_files'][row['source_file']]
            self.assertTrue(source['path'].startswith('data/geometry/') and source['path'].endswith('.json'))
            self.assertEqual(source['version'], 'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907')
            for side in sides:
                parameter = new['parameters'][edits.FIELD[side]]
                self.assertEqual((parameter['status'], parameter['value'], parameter['evidence_id']),
                                 ('known', None, conditioning['evidence_id']))
                replaced = row['original_value']['replaced_schedules'][edits.FIELD[side]]
                old_parameter = record['parameters'][edits.FIELD[side]]
                self.assertEqual(replaced['schedule_id'], old_parameter['value'])
                # The source schedule stays in the evidence and in the folder table.
                self.assertEqual(degrees(self.files, folder, replaced['schedule_id']), degrees(self.base, folder, old_parameter['value']))
                self.assertEqual(replaced['degC'], [min(degrees(self.base, folder, old_parameter['value'])),
                                                    max(degrees(self.base, folder, old_parameter['value']))])
        self.assertEqual(changed, AFFECTED)
        self.assertEqual(len(self.edited.summary['conditioning']['changed']), len(AFFECTED))

    def test_the_placeholder_temperatures_are_the_ones_the_review_named(self):
        records = {(r['template'], r['building_type'], space_type(r)): (p, r) for p, r in self.records(self.base).values()}
        for key, side, value in ((('90.1-2019', 'Warehouse', 'Bulk'), 'cooling', [50.0]),
                                 (('90.1-2019', 'RetailStandalone', 'Entry'), 'cooling', [100.0]),
                                 (('90.1-2019', 'SmallHotel', 'Stair'), 'cooling', [40.0]),
                                 (('90.1-2019', 'SmallHotel', 'Storage'), 'heating', [7.2])):
            path, record = records[key]
            self.assertEqual(degrees(self.base, path.split('/programs/')[0], record['parameters'][edits.FIELD[side]]['value']), value)

    def test_existing_unconditioned_programs_and_mixed_service_are_kept(self):
        summary = self.edited.summary['conditioning']
        kept = {self.records(self.base)[pid][1]['name'] for pid in summary['kept']}
        self.assertTrue({'ElevatorCore_SmallHotel', 'Elec/MechRoom_SmallHotel', 'Attic_SmallHotel', 'Plenum_MediumOffice',
                         'Corridor_HighriseApartment'} <= kept)
        self.assertEqual(sorted(e['program_id'].split('.')[0] for e in summary['mixed']), ['doe-ref-1980-2004', 'doe-ref-pre-1980'])
        for entry in summary['mixed']:
            self.assertIn('.outpatient.source.utility.', entry['program_id'])
            self.assertNotIn(entry['program_id'], self.edited.ids)
            self.assertAlmostEqual(entry['heating_served_area_share'], 0.3607, places=4)

    def test_every_mix_records_its_coverage_and_mixes_each_side_over_its_members(self):
        records = self.records()
        for pid, (path, mix) in records.items():
            if mix['derivation'] != 'composed':
                continue
            folder = path.split('/programs/')[0]
            coverage = mix['composition']['setpoint_coverage']
            members = [records[m['program_id']][1] for m in mix['composition']['members']]
            areas = [m['represented_area_m2'] for m in mix['composition']['members']]
            for side in BOTH:
                with self.subTest(mix=pid, side=side):
                    states = [edits.member_side(r, side) for r in members]
                    parameter = mix['parameters'][edits.FIELD[side]]
                    if 'unknown' in states:
                        self.assertIsNone(coverage[side])
                        self.assertIsNone(parameter['value'])
                        continue
                    having = [a for a, s in zip(areas, states) if s == 'yes']
                    expected = 1.0 if len(having) == len(areas) else math.fsum(having) / math.fsum(areas)
                    self.assertEqual(coverage[side], expected)
                    self.assertEqual(parameter['value'] is None, not having)
                    self.assertEqual(mix['parameters']['conditioning']['value'][f'{side}_enabled'], bool(having))
                    if having:
                        values = [v for r, s in zip(members, states) if s == 'yes'
                                  for v in degrees(self.files, folder, r['parameters'][edits.FIELD[side]]['value'])]
                        mixed = degrees(self.files, folder, parameter['value'])
                        self.assertGreaterEqual(min(mixed), min(values) - 1e-9)
                        self.assertLessEqual(max(mixed), max(values) + 1e-9)

    def test_full_coverage_mixes_keep_their_values(self):
        before, after = self.records(self.base), self.records()
        for old, (path, mix) in before.items():
            if mix['derivation'] != 'composed':
                continue
            new = after[self.edited.ids[old]][1]
            self.assertEqual(new['loads'], json.loads(release_editor.Substitution(self.edited.ids)(json.dumps(mix['loads']))), old)
            for side in BOTH:
                if new['composition']['setpoint_coverage'][side] == 1.0:
                    self.assertEqual(new['parameters'][edits.FIELD[side]], mix['parameters'][edits.FIELD[side]], old)

    def test_five_mixes_per_template_change_as_the_review_expected(self):
        summary = self.edited.summary['mixes']
        partial = {pid for pid, v in summary.items() if (v['heating'][1], v['cooling'][1]) != ('all', 'all')}
        templates = {pid.split('.')[0] for pid in summary if pid.startswith(('90-1-', 'doe-ref-', 'iecc-'))}
        for template in templates:
            for name in EVERY_TEMPLATE:
                self.assertTrue(any(p.startswith(f'{template}.{name}.') for p in partial), (template, name))
        warehouse = next(v for p, v in summary.items() if p.startswith('90-1-2019.warehouse.department.storage-mixed.'))
        self.assertEqual(warehouse['heating'], (1.0, 'all'))
        self.assertAlmostEqual(warehouse['cooling'][0], 0.30303, places=5)

    def test_the_warehouse_storage_mix_cools_at_the_fine_storage_setpoint(self):
        records = self.records()
        mix = next(r for p, r in records.values() if r['template'] == '90.1-2019' and r['name'] == 'Storage_Mixed_Warehouse')
        folder = 'commercial/90-1-2019/warehouse'
        fine = next(r for p, r in records.values() if r['template'] == '90.1-2019' and r['name'] == 'Fine_Warehouse')
        self.assertEqual(degrees(self.files, folder, mix['parameters']['cooling_setpoint_schedule_id']['value']), [26.7])
        self.assertEqual(degrees(self.files, folder, fine['parameters']['cooling_setpoint_schedule_id']['value']), [26.7])
        heating = degrees(self.files, folder, mix['parameters']['heating_setpoint_schedule_id']['value'])
        self.assertAlmostEqual(heating[0], 0.6969697 * 10.0 + 0.3030303 * 15.56, places=4)
        old = next(r for p, r in self.records(self.base).values() if r['template'] == '90.1-2019' and r['name'] == 'Storage_Mixed_Warehouse')
        self.assertAlmostEqual(degrees(self.base, folder, old['parameters']['cooling_setpoint_schedule_id']['value'])[0], 42.94, places=2)

    def test_exports_take_program_json_6_2_0(self):
        release = Release(files=self.files, release='2.5.0')
        ids = release.program_ids()
        pick = lambda prefix: next(i for i in ids if i.startswith(prefix))
        bulk, storage = pick('90-1-2019.warehouse.source.bulk.'), pick('90-1-2019.small-hotel.source.storage.')
        mix, support = pick('90-1-2019.warehouse.department.storage-mixed.'), pick('90-1-2019.small-hotel.department.support-mixed.')
        iecc = pick('iecc-2021.warehouse.source.bulk.')
        schema = Draft202012Validator(load_json(ROOT/'schemas'/atlas_contracts.PROGRAM_6_2[0]))
        documents = {}
        for pid in (bulk, storage, mix, support, iecc, pick('90-1-2019.warehouse.source.fine.')):
            for version in ('source', 'filled') if not pid.startswith('iecc-') else ('source',):
                document = release.program(pid, version)
                schema.validate(document)
                self.assertEqual((document['schema_version'], document['source']['release']), ('6.2.0', 'atlas-release-2.5.0'))
                documents[pid, version] = document
        source = documents[bulk, 'source']
        self.assertEqual({k: source['controls'][k] for k in ('heating_enabled', 'cooling_enabled', 'conditioning_state')},
                         {'heating_enabled': True, 'cooling_enabled': False, 'conditioning_state': 'heating_only'})
        self.assertIsNone(source['controls']['cooling_setpoint_schedule_id'])
        null = source['nulls']['/controls/cooling_setpoint_schedule_id']
        self.assertEqual(null['status'], 'not_conditioned')
        self.assertIn('UnitHeater', null['reason'])
        self.assertIn("'Warehouse ClgSetp BulkStorage', 50.0 degC", null['reason'])
        self.assertEqual(documents[bulk, 'filled']['controls']['conditioning_state'], 'heating_only')
        self.assertNotIn('cooling_setpoint_schedule_id', documents[bulk, 'filled']['controls'])
        self.assertEqual(documents[storage, 'source']['controls']['conditioning_state'], 'unconditioned')
        self.assertEqual(documents[storage, 'filled']['controls']['conditioning_state'], 'unconditioned')
        for version in ('source', 'filled'):
            coverage = documents[mix, version]['controls']['setpoint_coverage']
            self.assertEqual(coverage['heating'], 1.0)
            self.assertAlmostEqual(coverage['cooling'], 0.30303030303, places=10)
            self.assertEqual(documents[support, version]['controls']['setpoint_coverage']['cooling'], 0.0)
            self.assertEqual(documents[support, version]['controls']['conditioning_state'], 'heating_only')
        filled = documents[mix, 'filled']
        active = {r['field']: r['active_area_fraction'] for r in filled['metadata']['resolutions']
                  if r.get('rule') == 'area-weighted-active-member-controls'}
        self.assertAlmostEqual(active['cooling_setpoint_schedule_id'], filled['controls']['setpoint_coverage']['cooling'], places=12)
        self.assertEqual(documents[support, 'source']['nulls']['/controls/cooling_setpoint_schedule_id']['status'], 'not_conditioned')
        self.assertNotIn('setpoint_coverage', documents[pick('90-1-2019.warehouse.source.fine.'), 'source']['controls'])
        self.assertEqual(documents[iecc, 'source']['nulls']['/controls/cooling_setpoint_schedule_id']['status'], 'not_conditioned')
        with self.assertRaises(ValueError):   # 2.4.0 exports 6.1.0, which has no coverage
            Release(files=self.files, release='2.4.0').program(mix, 'source')

    def test_the_generator_assembles_the_edited_folders(self):
        reader = Reader(MemoryStore250(self.files))
        views = 0
        for folder in ('commercial/90-1-2019/warehouse', 'commercial/90-1-2019/small-hotel', 'commercial/90-1-2019/retail-standalone',
                       'commercial/doe-ref-1980-2004/small-hotel', 'commercial/iecc-2021/warehouse'):
            document = reader.generation(folder)
            for rid, block in document['programs'].items():
                for view in block['views']:
                    programmes.assemble(reader, rid, view)
                    views += 1
        self.assertGreater(views, 30)


class InputTests(unittest.TestCase):
    def test_the_system_types_follow_their_builders(self):
        document = load_json(conditioning_sides.OUTPUT)
        types = document['system_types']
        self.assertEqual((types['UnitHeater']['heating'], types['UnitHeater']['cooling']), (True, False))
        self.assertEqual(types['UnitHeater']['cooling_coil_lines'], [])
        self.assertTrue(types['UnitHeater']['heating_coil_lines'])
        # A PVAV map record gives no cooling_type; the builder makes a cooling coil.
        self.assertEqual((types['PVAV']['heating'], types['PVAV']['cooling']), (True, True))
        self.assertTrue(types['PVAV']['cooling_coil_lines'])
        self.assertEqual(Counter(f['status'] for f in document['folders'].values()), {'decided': 123, 'no_hvac_map': 6})
        hospital = [r for r in document['records'] if r['building_type'] == 'Hospital' and r['space_type'] == 'Basement'
                    and r['template'].startswith('DOE Ref')]
        self.assertEqual([(r['heating'], r['cooling'], r['hvac_map']['heating']) for r in hospital], [('served', 'served', 'not_served')] * 2)


class ContractTests(unittest.TestCase):
    def test_program_json_6_2_is_6_1_with_the_status_and_the_optional_coverage(self):
        older = load_json(ROOT/'schemas'/atlas_contracts.PROGRAM_6_1[0])
        newer = load_json(ROOT/'schemas'/atlas_contracts.PROGRAM_6_2[0])
        self.assertEqual(newer['$id'], 'urn:archetype-atlas:program-json:6.2.0')
        for version in ('source', 'filled'):
            controls = newer['$defs'][version]['$defs']['controls']
            self.assertIn('setpoint_coverage', controls['properties'])
            self.assertNotIn('setpoint_coverage', controls['required'])
            self.assertNotIn('setpoint_coverage', older['$defs'][version]['$defs']['controls']['properties'])
            status = newer['$defs'][version]['properties']['nulls']['additionalProperties']['properties']['status']['enum']
            self.assertEqual(status, ['unknown', 'none', 'not_applicable', 'not_conditioned'])
        self.assertIs(atlas_contracts.PROGRAM_BY_RELEASE['2.5.0'], atlas_contracts.PROGRAM_6_2)


if __name__ == '__main__':
    unittest.main()
