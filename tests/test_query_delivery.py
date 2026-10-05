"""Generic delivery must preserve source semantics without bulk downloads."""
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from scripts.common import ROOT, load_atlas, load_json


def read_resource(path):
    return json.loads(gzip.decompress(path.read_bytes())) if path.suffix == '.gz' else load_json(path)


class QueryDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas = load_atlas(ROOT/'data/releases/v0.2.0')
        cls.office = next(r for r in cls.atlas['programs'] if
                          (r['building_type'], r['template'], r['program']) ==
                          ('MediumOffice', '90.1-2013', 'office'))

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.query_delivery'),
                             'Generic delivery is not implemented')
        return __import__('scripts.query_delivery', fromlist=['query_delivery'])

    def pilot(self):
        data = copy.deepcopy(self.atlas)
        data['programs'] = [self.office]
        ids = {v for k, v in self.office.items() if k.endswith('_schedule_id') and v}
        data['schedules'] = [r for r in data['schedules'] if r['id'] in ids]
        for table in list(data):
            if isinstance(data[table], list) and table not in {'programs', 'schedules', 'provenance', 'source_files'}:
                data[table] = []
        return data

    def generate(self, root, data=None, **kwargs):
        return self.module().generate_delivery(root, data or self.pilot(),
                                               {'atlas': {'version': '0.2.0', 'manifest_sha256': 'a'*64}},
                                               **kwargs)

    def packet_records(self, root, manifest, kind):
        index = read_resource(root/manifest['record_types'][kind]['index']['href'])
        return [r for route in index['routes'] for part in route['packets']
                for r in read_resource(root/part['href'])['records']]

    def test_pilot_preserves_values_unknowns_units_and_lazy_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = self.generate(root)
            office = self.packet_records(root, manifest, 'program')[0]
            self.assertEqual(office['id'], self.office['id'])
            self.assertEqual(office['fields']['lighting_W_m2']['value'], self.office['lighting_W_m2'])
            self.assertEqual(office['fields']['lighting_W_m2']['unit'], 'W/m2')
            self.assertEqual(office['fields']['gas_equipment_W_m2']['status'], 'unknown')
            self.assertIsNone(office['fields']['gas_equipment_W_m2']['value'])
            self.assertNotIn('source_attributes', office['fields'])
            details = read_resource(root/office['evidence']['href'])
            self.assertEqual(details['record'], self.office)
            self.assertIn('source_files', details)
            self.assertEqual(self.module().validate_delivery(root), [])

    def test_rules_and_design_days_remain_exact_and_download_separately(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.generate(root)
            office = self.packet_records(root, manifest, 'program')[0]
            field = office['fields']['occupancy_schedule_id']
            schedule = read_resource(root/field['resource']['href'])
            expected = next(r for r in self.atlas['schedules'] if r['id'] == field['value'])
            self.assertEqual(schedule['record']['rules'], expected['rules'])
            self.assertEqual(schedule['representation'], 'rules')
            self.assertNotIn('rules', office['fields'])
            self.assertTrue(any('SmrDsn' in r['day_types'] for r in schedule['record']['rules']))
            self.assertIn('evidence', schedule, 'A lazy schedule must expose its own field provenance')

    def test_annual_profiles_preserve_calendar_and_are_lazy(self):
        data = self.pilot(); data['programs'] = []; data['schedules'] = []
        record = self.atlas['residential_archetypes'][0]
        data['residential_archetypes'] = [record]
        supplement = {'resolutions': [r for r in load_json(ROOT/'data/resolution-releases/v0.4.0/resolutions.json')['resolutions']
                                      if r['record_id'] == record['id'] and r['field'] == 'profile:occupants']}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = self.generate(root, data, supplement=supplement,
                                     profile_root=ROOT/'data/resolution-releases/v0.4.0')
            dto = self.packet_records(root, manifest, 'residential_archetype')[0]
            profile = read_resource(root/dto['reviewed']['profile:occupants']['resource']['href'])
            original = load_json(ROOT/'data/resolution-releases/v0.4.0'/supplement['resolutions'][0]['resolved_value']['profile_file'])
            self.assertEqual(profile['record']['metadata'], original['metadata'])
            self.assertEqual(profile['record']['values'], original['series']['occupants'])
            self.assertEqual(profile['representation'], 'annual_series')

    def test_old_snapshot_survives_rebuild_with_changed_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); old = self.generate(root)
            old_manifest = root/'snapshots'/old['snapshot_id']/'manifest.json'
            old_bytes = old_manifest.read_bytes()
            data = self.pilot(); data['programs'][0] = dict(data['programs'][0], lighting_W_m2=9)
            new = self.generate(root, data)
            self.assertNotEqual(old['snapshot_id'], new['snapshot_id'])
            self.assertEqual(old_manifest.read_bytes(), old_bytes)
            self.assertEqual(self.module().validate_delivery(root), [])

    def test_water_service_keeps_component_flow_and_normalized_schedule_separate(self):
        reporting = load_json(ROOT/'data/water-reporting-releases/v0.1.0/water-reporting.json')
        completion = load_json(ROOT/'data/completion-releases/v0.1.0/commercial-completion.json')
        service = next(r for r in reporting['services'] if r['building_type'] == 'MediumOffice' and r['template'] == '90.1-2013')
        reporting = dict(reporting, services=[service], programs=[], schedules=[])
        completion = dict(completion, draw_paths=[], schedules=[r for r in completion['schedules']
                           if r['equivalent_schedule']['id'] == service['equivalent_schedule_id']])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.generate(root, reporting=reporting, completion=completion)
            dto = self.packet_records(root, manifest, 'water_service')[0]
            self.assertEqual(dto['fields']['reference_rated_flow_m3_s']['value'], service['reference_rated_flow_m3_s'])
            self.assertIn('resource', dto['fields']['equivalent_schedule_id'])
            self.assertNotIn('DomesticHotWater', dto['fields'])

    def test_reviewed_zero_is_opt_in_and_original_evidence_survives(self):
        supplement = {'resolutions': [r for r in load_json(ROOT/'data/resolution-releases/v0.4.0/resolutions.json')['resolutions']
                                      if r['record_id'] == self.office['id']]}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.generate(root, supplement=supplement)
            office = self.packet_records(root, manifest, 'program')[0]
            self.assertIsNone(office['fields']['gas_equipment_W_m2']['value'])
            self.assertEqual(office['reviewed']['gas_equipment_W_m2']['value'], 0)
            self.assertEqual(office['reviewed']['gas_equipment_W_m2']['status'], 'reviewed')
            schedule = read_resource(root/office['reviewed']['gas_equipment_schedule_id']['resource']['href'])
            self.assertEqual(schedule['representation'], 'constant')
            self.assertEqual(schedule['record']['value'], 0)
            evidence = read_resource(root/office['evidence']['href'])
            self.assertEqual(evidence['resolutions']['gas_equipment_W_m2']['original_value'], None)

    def test_full_source_inventory_and_bytes_are_deterministic(self):
        original = copy.deepcopy(self.atlas)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            left, right = Path(a), Path(b)
            m1 = self.generate(left, self.atlas); m2 = self.generate(right, self.atlas)
            self.assertEqual(m1, m2)
            self.assertEqual({p.relative_to(left).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in left.rglob('*') if p.is_file()},
                             {p.relative_to(right).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in right.rglob('*') if p.is_file()})
            self.assertEqual(m1['record_types']['program']['record_count'], 768)
            self.assertEqual(m1['record_types']['envelope_component']['record_count'], 2451)
            self.assertEqual(m1['record_types']['residential_archetype']['record_count'], 41)
            for kind in m1['record_types']:
                index = read_resource(left/m1['record_types'][kind]['index']['href'])
                self.assertTrue(all(p.get('decoded_size_bytes', p['size_bytes']) <= self.module().MAX_PACKET_BYTES
                                    for r in index['routes'] for p in r['packets']))
            self.assertEqual(self.atlas, original)

    def test_tampering_duplicate_ids_and_unsafe_targets_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.generate(root)
            index = read_resource(root/manifest['record_types']['program']['index']['href'])
            (root/index['routes'][0]['packets'][0]['href']).write_text('{}')
            self.assertTrue(any('checksum' in e for e in self.module().validate_delivery(root)))
        with tempfile.TemporaryDirectory() as d:
            data = self.pilot(); data['programs'].append(self.office)
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                self.generate(Path(d), data)
        with self.assertRaisesRegex(ValueError, 'protected'):
            self.generate(ROOT/'data/releases/v0.2.0/new-delivery')


if __name__ == '__main__':
    unittest.main()
