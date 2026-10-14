"""Expanded source fixtures need exact operands, complete methods and distinct resources."""
import importlib
import importlib.util
import inspect
import gzip
import hashlib
import math
import json
from pathlib import Path
import tempfile
import unittest

from atlas_schedules.resources import ResourceSet
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ResidentialFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.resources = None

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def family(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.schedule_generator_families'),
                             'Progressive exact family source preparation is missing')
        module = importlib.import_module('scripts.schedule_generator_families')
        if self.__class__.resources is None:
            from scripts.schedule_generator_build import build_resources
            manifest = build_resources(Path(self.directory.name)/'resources', 'residential')
            self.__class__.resources = ResourceSet(Path(self.directory.name)/'resources', manifest['resource_set_id'])
        return self.__class__.resources

    def test_exact_fixture_scope_weather_and_inputs(self):
        resources = self.family()
        cases = resources.manifest['cases']
        self.assertEqual(len(cases), 41)
        self.assertEqual(len({c['weather']['station_filename'] for c in cases}), 37)
        recovery = json.loads((ROOT/'data/program-inputs/residential-v1.json').read_text())
        self.assertEqual({c['configuration_id'] for c in cases}, set(recovery['records']))
        for case in cases:
            record = resources.get('program', case['program_id'])
            self.assertEqual(record['recipe']['bound_inputs']['residents'], record['configuration']['occupants'])
            weather = resources.get('weather', record['recipe']['bound_inputs']['weather_id'])
            self.assertEqual(weather['provenance']['source_sha256'], case['weather']['sha256'])

    def test_all_installed_companions_use_actual_source_operands(self):
        from atlas_schedules.programs import resolve_program
        from atlas_schedules.companions import generate_companions
        resources = self.family()
        found = set()
        recovery = json.loads((ROOT/'data/program-inputs/residential-v1.json').read_text())
        for case in resources.manifest['cases']:
            recipe = resources.get('program', case['program_id'])['recipe']
            resolved = resolve_program(case['program_id'], dict(recipe['bound_inputs'], year=2007), resources)
            fixed = generate_companions(resolved, resources)['channels']
            for load in recovery['records'][case['configuration_id']]['loads']:
                sid = load.get('schedule_id')
                if sid in recovery['schedules'] and load['value']:
                    self.assertEqual(fixed[load['end_use']], recovery['schedules'][sid]['values'])
                    found.add(load['end_use'])
        self.assertEqual(found, {s['name'] for s in recovery['schedules'].values()})

    def test_every_active_channel_has_packaged_receipt(self):
        from scripts.schedule_generator_coverage import build_coverage, coverage_errors
        resources = self.family()
        report = build_coverage(resources)
        self.assertEqual(coverage_errors(report, resources), [])
        self.assertEqual(report['scope']['case_count'], 41)
        self.assertTrue(all(c['source_evidence'] for case in report['cases'] for c in case['channels']))

    def test_native_capture_operand_scope_is_explicit(self):
        from scripts.schedule_generator_reference import capture_residential
        self.assertIn('resources', inspect.signature(capture_residential).parameters,
                      'Independent capture cannot bind the expanded exact source resource set')

    def test_family_packaging_uses_its_resource_identity(self):
        from scripts.schedule_generator_release import _members
        self.assertIn('resources_root', inspect.signature(_members).parameters,
                      'Shipment cannot bind family resources')
        resources = self.family()
        files, identity = _members(resources.get('reference','m1-scope'), resources.root)
        manifest = json.loads(files['atlas_schedules/data/manifest.json'])
        self.assertEqual(identity, manifest['resource_set_id'])
        self.assertEqual(len(manifest['cases']), 41)
        report = json.loads(files['docs/validation/schedule-generator-coverage.json'])
        self.assertEqual(report['resource_set_id'], identity)
        self.assertEqual(report['scope']['case_count'], 41)
        self.assertNotIn('docs/examples/schedule-generator-v1/medium-office-request.json', files)

    def test_uncertified_family_cannot_ship(self):
        from scripts import schedule_generator_release as shipment
        self.assertTrue(callable(getattr(shipment,'validate_family_certification',None)),
                        'Expanded family lacks independent source/multiple-seed shipment gate')
        resources = self.family()
        from atlas_schedules.resources import write_resources
        records = {(e['kind'],e['key']):resources.get(e['kind'],e['key']) for e in resources.manifest['resources']
                   if (e['kind'],e['key']) != ('reference','family-certification')}
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_resources(Path(directory), records, {})
            uncertified = ResourceSet(Path(directory),manifest['resource_set_id'])
            with self.assertRaisesRegex(ValueError, 'certification'):
                shipment.validate_family_certification(uncertified, resources.get('reference','m1-scope'))

    def test_source_capture_matches_all_fixture_branches_and_controls(self):
        path = ROOT/'data/schedule-generator/residential-family-native.json.gz'
        self.assertTrue(path.exists(), 'Independent expanded native branch reference is missing')
        from atlas_schedules.residential import generate_residential
        from atlas_schedules.programs import resolve_program
        from atlas_schedules.companions import generate_companions
        resources = self.family()
        lock = json.loads((ROOT/'sources/schedule-generator-residential-family-reference-lock.json').read_text())
        content = path.read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(),lock['vectors']['sha256'])
        self.assertEqual(len(content),lock['vectors']['size_bytes'])
        payload = gzip.decompress(content)
        self.assertEqual(hashlib.sha256(payload).hexdigest(),lock['vectors']['payload_sha256'])
        captured = json.loads(payload)
        self.assertEqual(captured['provenance'],lock['capture_provenance'])
        native = {c['case_id']: c for c in captured['cases']}
        for case in resources.manifest['cases']:
            with self.subTest(fixture=case['configuration_id']):
                reference = native[case['configuration_id']]
                generated = generate_residential(reference['inputs'], reference['unit_seed'], resources)
                actual = generated['source_context']['activity']
                states = [[state for count,state in runs for _ in range(count)] for runs in reference['resident_state_runs']]
                self.assertEqual(actual['resident_states'], states)
                for key in ('occupant_types','main_state','unit_offset_minutes'):
                    self.assertEqual(actual[key], reference[key])
                self.assertEqual(set(generated['channels']), set(reference['channels']))
                for slot, expected in reference['channels'].items():
                    self.assertTrue(all(math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-8)
                                        for a,b in zip(generated['channels'][slot], expected)), slot)
                if reference['inputs']['residents']:
                    events = generated['source_context']['events']
                    for key in ('event_draws','final_rng_states','power_rows','minute_lengths'):
                        self.assertEqual(events[key], reference[key], key)
                    self.assertEqual(set(events['event_segments']), set(reference['event_segments']))
                    for slot, segments in events['event_segments'].items():
                        expected_segments = reference['event_segments'][slot]
                        self.assertEqual(len(segments),len(expected_segments),slot)
                        for actual_segment, expected_segment in zip(segments,expected_segments):
                            self.assertEqual(actual_segment[:2],expected_segment[:2],slot)
                            self.assertTrue(math.isclose(actual_segment[2],expected_segment[2],rel_tol=1e-6,abs_tol=1e-8),slot)
                    if reference['inputs']['installed']['ceiling_fan']:
                        self.assertEqual(generated['source_context']['shapes']['fan_months'],reference['fan_months'])
                else:
                    self.assertFalse(generated['source_context']['events']['rng_consumed'])
                record = resources.get('program',case['program_id'])
                resolved = resolve_program(case['program_id'], dict(record['recipe']['bound_inputs'],year=2007),resources)
                companions = generate_companions(resolved, resources)['channels']
                profile = resources.get('reference',case['configuration_id']+'-profile')['series']
                for slot in ('heating_setpoint','cooling_setpoint'):
                    self.assertTrue(all(math.isclose(a,b,rel_tol=0,abs_tol=1e-4)
                                        for a,b in zip(companions[slot], profile[slot])), slot)

    def test_multiple_seeds_preserve_targets_fixed_methods_and_vary_occupied_shapes(self):
        from atlas_schedules import generate
        resources = self.family()
        for case in resources.manifest['cases']:
            record = resources.get('program',case['program_id'])
            inputs = record['recipe']['bound_inputs']
            params = {'resource_set_id':resources.resource_set_id,
                'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},
                'instances':[{'key':case['case_id'],'program_id':case['program_id'],
                              'inputs':inputs,'basis_bindings':{},'operating_group':None}]}
            with self.subTest(fixture=case['configuration_id']), patch.object(ResourceSet,'load',return_value=resources):
                a,b = (generate(params,seed) for seed in (42,51))
                ta = {c['demand_id']:c['reference_target'] for c in a['bindings'] if c['kind']=='load'}
                tb = {c['demand_id']:c['reference_target'] for c in b['bindings'] if c['kind']=='load'}
                self.assertEqual(ta,tb)
                for bundle in (a,b):
                    for binding in bundle['bindings']:
                        if binding['kind'] != 'load':
                            continue
                        total = math.fsum(bundle['schedules'][binding['schedule_id']]['values'])*binding['effective_magnitude']['value']
                        if binding['reference_target']['unit'].startswith('m3'):
                            total *= 3600
                        self.assertTrue(math.isclose(total,binding['reference_target']['total'],rel_tol=1e-8,abs_tol=1e-12))
                for slot in record['recipe']['companion_rules']:
                    sid = a['constituents'][0]['schedule_ids'][slot]
                    self.assertEqual(a['schedules'][sid]['values'],b['schedules'][sid]['values'])
                occupancy = a['constituents'][0]['schedule_ids']['occupants']
                if inputs['residents']:
                    self.assertNotEqual(a['schedules'][occupancy]['values'],b['schedules'][occupancy]['values'])
                else:
                    self.assertEqual(a['schedules'],b['schedules'])
