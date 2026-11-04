"""Release 2.4.0's record edits over release 2.3.0 (ADR 0060), and its exports in Program JSON 6.1.0 (ADR 0061)."""
import json
import unittest
from collections import Counter

from jsonschema import Draft202012Validator

from atlas_schedules import programmes
from atlas_schedules.release import Release as Reader
from scripts import atlas_contracts, atlas_delta, atlas_edits, atlas_edits_2_4_0 as edits, release_editor
from scripts.atlas_exports import Release
from scripts.atlas_format import slug
from scripts.common import ROOT, load_json
from scripts.lighting_controls import prototype_root
from tests.test_atlas_edits import MemoryStore

CAPPED = {'FullServiceRestaurant': 2, 'LargeOffice': 2, 'MediumOffice': 1, 'QuickServiceRestaurant': 2, 'RetailStandalone': 5,
          'RetailStripmall': 3, 'SmallOffice': 1, 'Warehouse': 3}
PNNL_OFFICE = {('90.1-2007', 'WholeBuilding - Sm Office_SmallOffice'): 10.67131,
               ('90.1-2007', 'WholeBuilding - Md Office_MediumOffice'): 11.02666,
               ('90.1-2007', 'WholeBuilding - Lg Office_LargeOffice'): 11.61158,
               ('90.1-2013', 'WholeBuilding - Sm Office_SmallOffice'): 10.90742,
               ('90.1-2013', 'WholeBuilding - Md Office_MediumOffice'): 10.19587,
               ('90.1-2013', 'WholeBuilding - Lg Office-basement_LargeOffice'): 10.27324,
               ('90.1-2013', 'WholeBuilding - Lg Office-others_LargeOffice'): 10.27324,
               ('90.1-2019', 'WholeBuilding - Sm Office_SmallOffice'): 6.98149,
               ('90.1-2019', 'WholeBuilding - Md Office_MediumOffice'): 6.66362,
               ('90.1-2019', 'WholeBuilding - Lg Office-basement_LargeOffice'): 6.59986,
               ('90.1-2019', 'WholeBuilding - Lg Office-others_LargeOffice'): 6.59986}


class MemoryStore240(MemoryStore):
    def __init__(self, files):
        super().__init__(files)
        self.manifest = {**self.manifest, 'release': edits.RELEASE}
        self.version = edits.RELEASE

    def describe(self):
        return 'release 2.4.0 in memory'


class EditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = atlas_delta.files(edits.BASE)
        cls.edited = edits.edit(cls.base)
        cls.files = cls.edited.resolved(cls.base)
        cls.cap = load_json(edits.CAP)
        cls.power = load_json(edits.LIGHTING_POWER)
        cls.services = load_json(edits.SERVICES)

    @classmethod
    def tearDownClass(cls):
        del cls.base, cls.edited, cls.files

    def records(self, files=None):
        files = files or self.files
        return {json.loads(d)['id']: (p, json.loads(d)) for p, d in files.items() if p.startswith('commercial/') and '/programs/' in p}

    def evidence(self, folder, eid):
        return json.loads(self.files[f'evidence/{folder}.json'])[eid]

    def test_ids_follow_their_rules_and_no_file_cites_a_moved_id(self):
        self.assertEqual(release_editor.program_ids(self.files), {})
        self.assertEqual(release_editor.set_ids(self.files, {}), {})
        moved = release_editor.Substitution({old: '@moved@' for old in self.edited.ids})
        stale = [p for p, d in self.files.items() if p.endswith('.json') and not p.startswith('residential/') and p != 'id-map.json'
                 and '@moved@' in moved(d.decode('utf-8'))]
        self.assertEqual(stale, [])
        self.assertEqual(set(self.edited.removed), {p for p in self.base if p not in self.files})
        self.assertFalse(any('.construction-' in i for i in self.edited.ids))
        self.assertEqual(json.loads(edits.id_map_bytes(self.edited.ids))['ids'], self.edited.ids)

    def test_every_edited_file_meets_its_release_record_schema_and_storage_format(self):
        from scripts import release_schemas
        self.assertEqual(release_schemas.errors(self.edited.files), [])
        for path, data in self.edited.files.items():
            with self.subTest(path=path):
                self.assertEqual(atlas_edits.encode(path, json.loads(data)), data)

    def test_every_known_lighting_controls_block_states_the_cap(self):
        rules, nones = Counter(), Counter()
        for pid, (path, record) in self.records().items():
            controls = record.get('lighting_controls')
            if not controls or controls['status'] != 'known':
                self.assertNotIn(edits.FIELD, controls or {}, pid)
                continue
            cap = controls[edits.FIELD]
            self.assertEqual(set(cap), {'rule', 'evidence_id'}, pid)
            self.assertIn(cap['evidence_id'], record['evidence_ids'])
            row = self.evidence(path.split('/programs/')[0], cap['evidence_id'])
            self.assertTrue(row['source_file'], pid)
            if cap['rule']:
                self.assertEqual(record['template'], '90.1-2019', pid)
                rules[record['building_type']] += 1
            else:
                nones[record['template']] += 1
        self.assertEqual(dict(rules), CAPPED)
        self.assertEqual(set(nones) >= {'90.1-2007', '90.1-2013', 'DOE Ref Pre-1980', 'DOE Ref 1980-2004', 'IECC 2018', 'IECC 2021'}, True)

    def test_the_medium_office_rule_is_pnnls(self):
        records = self.records()
        pid = self.edited.ids['90-1-2019.medium-office.source.whole-building-md-office.d597bd']
        path, record = records[pid]
        rule = record['lighting_controls'][edits.FIELD]['rule']
        self.assertAlmostEqual(rule['cap_W_m2'], 0.02/0.09290304, places=12)
        self.assertAlmostEqual(rule['cap_W_m2'], 0.215, places=3)
        self.assertAlmostEqual(rule['lighting_threshold_W_m2'], 0.02/0.093, places=12)
        self.assertEqual(rule['source_values'], {'cap': 0.02, 'threshold': 0.02, 'unit': 'W/ft2', 'cap_conversion_m2_per_ft2': 0.09290304,
                                                 'threshold_conversion_m2_per_ft2': 0.093})
        self.assertEqual((rule['condition'], rule['comparison'], rule['action'], rule['calling_point']),
                         ('zone_occupant_count_zero', 'zone_lighting_power_density_at_least_threshold', 'set_lights_to_cap',
                          'BeginTimestepBeforePredictor'))
        self.assertEqual((rule['zones'], rule['controlled_zones']), (15, 15))
        self.assertEqual([c['zone'] for c in rule['zone_conditions']], ['Perimeter_mid_ZN_2'])
        row = self.evidence('commercial/90-1-2019/medium-office', record['lighting_controls'][edits.FIELD]['evidence_id'])
        self.assertIn('SET_Core_bottom_Light_EMS_Program', row['original_value'])
        self.assertIn('IF (Core_bottom_Occ_Sensor <= 0) && (Core_bottom_LSr_IP >= 0.02)', row['original_value']['SET_Core_bottom_Light_EMS_Program'])
        glossary = json.loads(self.files['evidence/glossary.json'])
        self.assertEqual(glossary['source_files'][row['source_file']]['path'], 'ASHRAE901_OfficeMedium/ASHRAE901_OfficeMedium_STD2019_Buffalo.idf')
        warehouse = next(r for _, r in records.values() if r['template'] == '90.1-2019' and r['name'] == 'Fine_Warehouse')
        self.assertEqual(warehouse['lighting_controls'][edits.FIELD]['rule']['condition_zone'], 'Zone1 Office')
        strip = next(r for _, r in records.values() if r['template'] == '90.1-2019' and r['building_type'] == 'RetailStripmall'
                     and r.get('lighting_controls', {}).get(edits.FIELD, {}).get('rule'))
        self.assertEqual(strip['lighting_controls'][edits.FIELD]['rule']['additional_lighting_when_capped_W_m2'], 0.0)

    def test_the_cap_is_absent_where_the_source_models_have_none(self):
        self.assertEqual({t: e['rule'] for t, e in self.cap['templates'].items()},
                         {t: None for t in ('90.1-2007', '90.1-2013', 'DOE Ref 1980-2004', 'DOE Ref Pre-1980', 'IECC 2006', 'IECC 2009',
                                            'IECC 2012', 'IECC 2015', 'IECC 2018', 'IECC 2021')})
        for template in ('IECC 2018', 'IECC 2021', '90.1-2013'):
            row = self.cap['evidence'][self.cap['templates'][template]['evidence_id']]
            self.assertEqual(row['original_value']['LPD_Ctrl_header'], '0')
            self.assertEqual(self.cap['scan'][template], {'models': 304, 'with_rule': 0})
        self.assertEqual(self.cap['scan']['90.1-2019'], {'models': 304, 'with_rule': 152})
        hospital = [r for r in self.cap['records'] if r['building_type'] == 'Hospital']
        self.assertTrue(hospital and all(r['rule'] is None for r in hospital))
        datacenter = next(r for r in self.cap['records'] if r['space_type'] == 'OfficeLarge Data Center')
        self.assertIsNone(datacenter['rule'])
        self.assertTrue(self.cap['evidence'][datacenter['evidence_id']]['original_value']['rule_in_other_zones_of_the_model'])

    def test_office_lighting_follows_pnnl_and_nothing_else_changes_value(self):
        before, after = self.records(self.base), self.records()
        changed = set()
        for old, (_, record) in before.items():
            if record['mode'] != 'source':
                continue
            new = after[self.edited.ids.get(old, old)][1]
            values = lambda r: sorted((l['demand_id'], atlas_edits.filled_entry(l, True)['value'] or 0) for l in r['loads'])
            if values(record) != values(new):
                changed.add((record['template'], record['name']))
                lighting = next(l for l in new['loads'] if l['quantity'] == 'lighting')
                self.assertEqual(lighting['value'], PNNL_OFFICE[record['template'], record['name']])
                row = self.evidence(f'commercial/{slug(record["template"])}/{slug(record["building_type"])}', lighting['evidence_id'])
                self.assertEqual(row['original_value']['replaced_value_W_m2'],
                                 next(l['value'] for l in record['loads'] if l['quantity'] == 'lighting'))
                self.assertTrue(row['locator'].startswith('Lights '))
        self.assertEqual(changed, set(PNNL_OFFICE))
        medium = after[self.edited.ids['90-1-2019.medium-office.source.whole-building-md-office.d597bd']][1]
        self.assertEqual(next(l['value'] for l in medium['loads'] if l['quantity'] == 'lighting'), 6.66362)

    def test_elevators_and_reach_ins_become_building_services(self):
        added = {}
        for path, data in self.files.items():
            if path.endswith('/services.json') and path.startswith('commercial/90-1-'):
                old = json.loads(self.base[path])
                for sid, service in json.loads(data).items():
                    if sid not in old:
                        added[sid] = (path.rsplit('/', 1)[0], service)
        self.assertEqual(len(added), len(self.services['services']))
        self.assertEqual(Counter(s['end_use'] for _, s in added.values()), {'elevator': 48, 'refrigeration_equipment': 36})
        records = self.records()
        for sid, (folder, service) in added.items():
            with self.subTest(service=sid):
                schedules = json.loads(self.files[folder+'/schedules.json'])['schedules']
                self.assertIn(service['load']['schedule_id'], schedules)
                for pid in service['beneficiary_program_ids']:
                    self.assertTrue(records[pid][0].startswith(folder+'/programs/source/'))
                if service['assignment'] == 'building_level':
                    self.assertEqual(service['beneficiary_program_ids'], [])
                    self.assertEqual(service['load']['thermal_effects']['lost']['value'], 1.0)
                else:
                    self.assertEqual(len(service['beneficiary_program_ids']), 1)
        by_name = {(f, s['name']): s for f, s in added.values()}
        motor = by_name['commercial/90-1-2019/medium-office', 'Core_bottom_Elevators_Equip']
        self.assertEqual(motor['load']['value'], 16363.22)
        self.assertEqual(records[motor['beneficiary_program_ids'][0]][1]['name'], 'WholeBuilding - Md Office_MediumOffice')
        self.assertEqual(motor['load']['thermal_effects']['radiant']['value'], 0.5)
        self.assertEqual(by_name['commercial/90-1-2019/secondary-school', 'Mech_ZN_1_FLR_1_Elevators_Equip']['load']['value'], 22659.35)
        self.assertEqual(by_name['commercial/90-1-2019/outpatient', 'Floor 1 Elevator Pump Room_Elevators_Equip']['load']['value'], 13672.78)
        self.assertEqual(by_name['commercial/90-1-2019/midrise-apartment', 'G Corridor_Elevators_Equip']['load']['value'], 8012.15)
        self.assertEqual(by_name['commercial/90-1-2019/highrise-apartment', 'T Corridor_Elevators_Equip']['load']['value'], 17212.05)
        for folder, watts in (('hospital', 57630.4), ('large-hotel', 75383.39), ('large-office', 226203.93)):
            service = by_name[f'commercial/90-1-2019/{folder}', 'Elevators']
            self.assertEqual((service['load']['value'], service['assignment']), (watts, 'building_level'))
        kitchens = [s for (f, n), s in by_name.items() if 'Reach-in' in n and f.startswith('commercial/90-1-2019/')]
        self.assertEqual(len(kitchens), 12)
        self.assertTrue(all(records[s['beneficiary_program_ids'][0]][1]['name'].startswith('Kitchen_') for s in kitchens))
        # The two objects an atlas program already carries are not doubled.
        self.assertNotIn(('commercial/90-1-2019/small-hotel', 'ElevatorCoreFlr1_Elevators_Equip'), by_name)
        self.assertNotIn(('commercial/90-1-2019/outpatient', 'Elevators_Lights_Fan'), by_name)
        self.assertEqual(len(self.services['excluded']), 6)

    def test_exports_take_program_json_6_1_0(self):
        release = Release(files=self.files, release='2.4.0')
        ids = release.program_ids()
        sample = [self.edited.ids['90-1-2019.medium-office.source.whole-building-md-office.d597bd'],
                  next(i for i in ids if i.startswith('90-1-2019.warehouse.source.fine.')),
                  next(i for i in ids if i.startswith('90-1-2019.large-office.source.office-large-data-center.')),
                  next(i for i in ids if i.startswith('90-1-2013.small-office.source.whole-building-sm-office.')),
                  next(i for i in ids if i.startswith('doe-ref-pre-1980.small-office.source.whole-building')),
                  next(i for i in ids if i.startswith('90-1-2019.medium-office.general.') or i.startswith('90-1-2019.small-hotel.general.')),
                  next(i for i in ids if i.startswith('iecc-2021.medium-office.source.whole-building'))]
        schema = Draft202012Validator(load_json(ROOT/'schemas'/atlas_contracts.PROGRAM_6_1[0]))
        for pid in sample:
            for version in ('source', 'filled') if not pid.startswith('iecc-') else ('source',):
                with self.subTest(program=pid, version=version):
                    document = release.program(pid, version)
                    schema.validate(document)
                    self.assertEqual((document['schema_version'], document['source']['release']), ('6.1.0', 'atlas-release-2.4.0'))
                    rows = {e['id']: e for e in document['source']['evidence']}
                    self.assertEqual(atlas_contracts.cited({k: v for k, v in document.items() if k not in ('source', 'metadata')}) - set(rows), set())
                    controls = document.get('lighting_controls')
                    if controls and controls['status'] == 'known':
                        cap = controls[atlas_contracts.CAP_FIELD]
                        self.assertIn(cap['evidence_id'], rows)
                        pointer = '/lighting_controls/unoccupied_lighting_cap/rule'
                        if cap['rule'] is None:
                            self.assertEqual(document['nulls'][pointer]['status'], 'none')
                            self.assertEqual(document['nulls'][pointer]['reason'], rows[cap['evidence_id']]['interpretation_note'])
                        else:
                            self.assertNotIn(pointer, document['nulls'])
        medium = release.program(sample[0], 'filled')
        self.assertEqual(next(l['value'] for l in medium['loads'] if l['end_use'] == 'lighting'), 6.66362)
        self.assertEqual(len(medium['building_service_ids']), 2)
        services = release.building_services('90-1-2019/hospital')
        self.assertEqual((services['schema_version'], services['release']), ('1.0.1', 'atlas-release-2.4.0'))
        self.assertEqual(sorted(s['name'] for s in services['services'] if s['end_use'] == 'elevator'), ['Elevators', 'Elevators_Lights_Fan'])
        with self.assertRaises(ValueError):   # 2.3.0 exports 6.0.0, which has no cap field
            Release(files=self.files, release='2.3.0').program(sample[0], 'source')

    def test_the_generator_assembles_the_edited_folders(self):
        reader = Reader(MemoryStore240(self.files))
        views = 0
        for folder in ('commercial/90-1-2019/medium-office', 'commercial/90-1-2019/warehouse', 'commercial/90-1-2013/large-office',
                       'commercial/90-1-2019/hospital'):
            document = reader.generation(folder)
            for rid, block in document['programs'].items():
                for view in block['views']:
                    programmes.assemble(reader, rid, view)
                    views += 1
        self.assertGreater(views, 20)


class InputTests(unittest.TestCase):
    """The committed inputs reproduce from the source models where they are on this machine."""

    def setUp(self):
        if not (prototype_root()/'commercial-ashrae901/ASHRAE901_OfficeMedium').is_dir():
            self.skipTest('PNNL prototype IDFs not on this machine (ATLAS_PROTOTYPE_ROOT)')

    def test_the_lighting_cap_reproduces(self):
        from scripts import lighting_cap
        self.assertEqual(lighting_cap.encode(lighting_cap.build()), lighting_cap.OUTPUT.read_bytes())

    def test_the_lighting_power_reproduces(self):
        from scripts import pnnl_lighting_power
        self.assertEqual(pnnl_lighting_power.encode(pnnl_lighting_power.build()), pnnl_lighting_power.OUTPUT.read_bytes())

    def test_the_services_reproduce(self):
        from scripts import pnnl_services
        self.assertEqual(pnnl_services.encode(pnnl_services.build()), pnnl_services.OUTPUT.read_bytes())


class ContractTests(unittest.TestCase):
    def test_program_json_6_1_is_6_0_with_the_optional_cap(self):
        older = load_json(ROOT/'schemas'/atlas_contracts.PROGRAM[0])
        newer = load_json(ROOT/'schemas'/atlas_contracts.PROGRAM_6_1[0])
        self.assertEqual(newer['$id'], 'urn:archetype-atlas:program-json:6.1.0')
        for version in ('source', 'filled'):
            controls = newer['$defs'][version]['properties']['lighting_controls']
            self.assertIn(atlas_contracts.CAP_FIELD, controls['properties'])
            self.assertNotIn(atlas_contracts.CAP_FIELD, controls.get('required', []))
            self.assertNotIn(atlas_contracts.CAP_FIELD, older['$defs'][version]['properties']['lighting_controls']['properties'])
        self.assertEqual({r: atlas_contracts.PROGRAM_BY_RELEASE[r] for r in ('2.3.0', '2.4.0')},
                         {'2.3.0': atlas_contracts.PROGRAM, '2.4.0': atlas_contracts.PROGRAM_6_1})
        self.assertEqual(atlas_contracts.meaning('/lighting_controls/unoccupied_lighting_cap/rule')[:2], ('none', 'record'))


if __name__ == '__main__':
    unittest.main()
