"""End-to-end source scope, order and conserved constituent pilots."""
import copy
import gzip
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet
from atlas_schedules.contract import validate_bundle
from atlas_schedules.comparison import compare_bundles

ROOT = Path(__file__).resolve().parents[1]
OFFICE = 'program-0e670d8dc556f7f5bdd7f1a9'
PLENUM = 'program-f41ee055c01c510fa42096ae'
OCCUPIED = 'program-03fe19ed8968e605f4be3b8d'
VACANT = 'program-e0993499165be6c7b5bf9efa'


class GeneratorCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads((ROOT/'atlas_schedules/data/manifest.json').read_text())
        cls.resources = ResourceSet.load(manifest['resource_set_id'])

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas_schedules.generator'),
                             'public generation implementation is missing')
        from atlas_schedules import generate
        self.generate = generate

    def instance(self, key, program=OFFICE, group=None, basis=None):
        return {'key': key, 'program_id': program,
                'inputs': copy.deepcopy(self.resources.get('program', program)['recipe']['bound_inputs']),
                'basis_bindings': basis or {}, 'operating_group': group}

    def params(self, instances, mixture=None):
        result = {'resource_set_id': self.resources.resource_set_id,
                  'calendar': {'year': 2007, 'clock': 'local_standard_time', 'holidays': []},
                  'instances': instances}
        if mixture is not None:
            result['mixture'] = mixture
        return result

    def assert_conserved(self, bundle):
        validate_bundle(bundle)
        for schedule in bundle['schedules'].values():
            self.assertEqual(len(schedule['values']), 8760)
        for binding in bundle['bindings']:
            if binding['kind'] == 'load':
                total = math.fsum(bundle['schedules'][binding['schedule_id']]['values'])
                total *= binding['effective_magnitude']['value']
                if binding['reference_target']['unit'].startswith('m3'):
                    total *= 3600
                self.assertTrue(math.isclose(total, binding['reference_target']['total'],
                                            rel_tol=1e-8, abs_tol=1e-12))


class PilotTests(GeneratorCase):
    def test_medium_office_and_two_apartment_pilots(self):
        for instances in ([self.instance('office', group='office-building')],
                          [self.instance('unit-a', OCCUPIED), self.instance('unit-b', VACANT)]):
            params = self.params(instances)
            first = self.generate(params, 42)
            second = self.generate(params, 42)
            self.assert_conserved(first)
            self.assertEqual(compare_bundles(first, second, self.resources.get('reference', 'comparison-policy')), [])
            self.assertEqual(len(first['constituents']), len(instances))
            for constituent in first['constituents']:
                self.assertNotIn('reference_channels', constituent['inputs'])
                self.assertNotIn('reference_budgets', constituent['inputs'])
                self.assertIn('source_context', constituent['generation'])
        occupied = self.generate(self.params([self.instance('unit', OCCUPIED)]), 42)
        refrigerator = next(b for b in occupied['bindings'] if b.get('demand_id') ==
                            next(d['demand_id'] for d in occupied['constituents'][0]['demands'] if d['quantity']=='refrigerator'))
        self.assertEqual(refrigerator['reference_target']['total'], 434000)
        self.assertEqual(refrigerator['reference_target']['evidence']['original_value']['annual_kwh'], 434)

    def test_source_unit_order_and_coordinated_commercial_group(self):
        instances = [self.instance('a', VACANT), self.instance('b', VACANT), self.instance('c', VACANT),
                     self.instance('office-a', group='same'), self.instance('office-b', group='same'),
                     self.instance('plenum', PLENUM, group='same')]
        bundle = self.generate(self.params(instances), 42)
        self.assertEqual(bundle['generation']['residential_unit_order'], ['a', 'b', 'c'])
        self.assertEqual(bundle['generation']['unit_seeds'], {'a':42, 'b':84, 'c':252})
        contexts = [c['generation']['source_context'] for c in bundle['constituents'][3:]]
        self.assertEqual(contexts[0]['operating_receipt'], contexts[1]['operating_receipt'])
        self.assertEqual(contexts[0]['operating_receipt'], contexts[2]['operating_receipt'])
        swapped = self.generate(self.params([instances[1],instances[0],instances[2]]), 42)
        self.assertEqual(swapped['generation']['unit_seeds']['a'], 84)
        zero = self.generate(self.params(instances[:3]), 0)
        self.assertEqual(zero['generation']['unit_seeds'], {'a':0, 'b':0, 'c':0})
        occupied = self.generate(self.params([self.instance('o', OCCUPIED)]), 42)
        streams = occupied['constituents'][0]['generation']['source_context']['residential']['activity']['enduse_seeds']
        self.assertEqual(list(streams), ['hygiene','dishwasher','clothes_washer','clothes_dryer','ev','cooking'])
        self.assertEqual(streams['ev'], 3143890026)

    def test_all_declared_cases_and_accepted_inactive_receipts(self):
        for case in self.resources.get('reference','m1-scope')['cases']:
            with self.subTest(case=case['case_id']):
                instance = self.instance('case',case['program_id'])
                if 'residents' not in instance['inputs']: instance['operating_group']='building'
                bundle = self.generate(self.params([instance]),42)
                self.assert_conserved(bundle)
                constituent = bundle['constituents'][0]
                self.assertEqual(constituent['generation']['case_id'], case['case_id'])
                if not constituent['slots']:
                    self.assertEqual(bundle['schedules'], {})
                    self.assertEqual(bundle['bindings'], [])
                    self.assertTrue(constituent['evidence'][0]['accepted_absence'])
                    self.assertEqual(constituent['generation']['status'], 'accepted_inactive')

    def test_public_scope_and_unknown_operands_fail_closed(self):
        params = self.params([self.instance('office')])
        for mutate in (lambda p: p['calendar'].update(year=2009),
                       lambda p: p['instances'][0]['inputs'].update(weekday_start_time=3600),
                       lambda p: p['instances'][0].update(basis_bindings={'multiplicity':True}),
                       lambda p: p['instances'][0].update(basis_bindings={'inferred_unit_area':100}),
                       lambda p: p['instances'][0].update(basis_bindings={'floor_area_m2':2**2048}),
                       lambda p: p['instances'][0].update(program_id='unknown')):
            bad = copy.deepcopy(params); mutate(bad)
            with self.assertRaises(GeneratorError): self.generate(bad,42)
        with self.assertRaises(GeneratorError): self.generate(params,True)

    def test_public_scope_uses_declared_cases_not_only_compiler_status(self):
        get=ResourceSet.get
        def narrowed(resources,kind,key):
            record=get(resources,kind,key)
            if (kind,key)==('reference','m1-scope'):
                record['cases']=[c for c in record['cases'] if c['program_id']!=OFFICE]
            return record
        # Controlled scope operand mutation; real resource loading/resolution.
        with patch.object(ResourceSet,'get',narrowed),self.assertRaises(GeneratorError) as raised:
            self.generate(self.params([self.instance('office')]),42)
        self.assertEqual(raised.exception.code,'unsupported_binding')

    def test_positive_target_zero_events_propagates_without_reseeding(self):
        from atlas_schedules.residential.activity import simulate_activities
        def no_events(inputs, seed, resources):
            result = simulate_activities(inputs,seed,resources)
            result['resident_states'] = [[0]*35040 for _ in result['resident_states']]
            return result
        # Controlled component fixture, not a naturally occurring annual seed.
        with patch('atlas_schedules.residential.simulate_activities', side_effect=no_events):
            with self.assertRaises(GeneratorError) as raised:
                self.generate(self.params([self.instance('unit',OCCUPIED)]),42)
        self.assertEqual(raised.exception.code,'zero_generated_integral')
        self.assertIn('/instances/unit/',raised.exception.path)

    def test_generation_runs_with_stdlib_only_from_copied_package(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(ROOT/'atlas_schedules', Path(d)/'atlas_schedules',ignore=shutil.ignore_patterns('__pycache__'))
            request = self.params([self.instance('office')])
            (Path(d)/'request.json').write_text(json.dumps(request))
            command = [sys.executable,'-S','-c',
                       "import json; from atlas_schedules import generate; b=generate(json.load(open('request.json')),42); print(len(b['schedules']))"]
            result = subprocess.run(command,cwd=d,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertGreater(int(result.stdout),0)

    def test_exact_activity_receipts_and_unknown_inactive_omissions(self):
        bundle=self.generate(self.params([self.instance('unit',OCCUPIED)]),42)
        activity=bundle['constituents'][0]['generation']['source_context']['residential']['activity']
        self.assertIn('resident_states',activity)
        self.assertIn('decisions',activity)
        self.assertIn('main_state',activity)
        changed=copy.deepcopy(bundle)
        changed['constituents'][0]['generation']['source_context']['residential']['activity']['resident_states'][0][0]=6
        self.assertTrue(compare_bundles(changed,bundle,self.resources.get('reference','comparison-policy')))
        changed=copy.deepcopy(bundle)
        states=changed['constituents'][0]['generation']['source_context']['residential']['activity']['resident_states'][0]
        position=states.index(0);states[position]=False
        self.assertTrue(compare_bundles(changed,bundle,self.resources.get('reference','comparison-policy')))
        malformed=copy.deepcopy(bundle)
        malformed['bindings'].pop(0)
        malformed['constituents'][0]['binding_indices']=list(range(len(malformed['bindings'])))
        with self.assertRaises(GeneratorError): validate_bundle(malformed)
        inactive=self.generate(self.params([self.instance('empty',PLENUM)]),42)
        inactive['constituents'][0]['evidence'][0]['accepted_absence']=False
        with self.assertRaises(GeneratorError): validate_bundle(inactive)
        vacant=self.generate(self.params([self.instance('vacant',VACANT)]),42)
        changed=copy.deepcopy(vacant)
        sid=changed['constituents'][0]['schedule_ids']['occupants']
        changed['schedules'][sid]['values'][0]=False
        self.assertTrue(compare_bundles(changed,vacant,self.resources.get('reference','comparison-policy')))

    def test_runtime_schema_checker_matches_oracle_on_malformed_contracts(self):
        from atlas_schedules.contract import validate_request, _check_schema
        from jsonschema import Draft202012Validator
        import json
        schema=json.loads((ROOT/'schemas/schedule-generator-request-v1.schema.json').read_text())
        for mutate in [lambda p:p.update(extra=0),lambda p:p['calendar'].update(year=True),
                       lambda p:p['instances'][0].update(inputs=[]),lambda p:p['calendar'].update(clock='UTC'),
                       lambda p:p['instances'][0].update(key=''),lambda p:p['instances'][0].update(operating_group=4),
                       lambda p:p['instances'][0].update(basis_bindings={'extents':{'floor_area':{'value':-1,'unit':'m2','evidence':{}}}})]:
            bad=self.params([self.instance('office')]);mutate(bad)
            self.assertTrue(list(Draft202012Validator(schema).iter_errors(bad)))
            with self.assertRaises(GeneratorError):validate_request(bad,42)
        with self.assertRaises(GeneratorError) as raised:_check_schema(1,{'multipleOf':2},{},'')
        self.assertEqual(raised.exception.code,'unsupported_schema')
        for name in ('request','program','bundle'):
            self.assertEqual((ROOT/f'schemas/schedule-generator-{name}-v1.schema.json').read_bytes(),
                             (ROOT/f'atlas_schedules/schemas/schedule-generator-{name}-v1.schema.json').read_bytes())
        bad=self.params([self.instance('office')])
        bad['instances'][0]['basis_bindings']={'extents':{'floor_area':{'value':1,'unit':'m2','evidence':{'unsupported':{1,2}}}}}
        with self.assertRaises(GeneratorError):validate_request(bad,42)

    def test_complete_pilot_examples_validate_and_reproduce_numerically(self):
        from jsonschema import Draft202012Validator
        directory=ROOT/'docs/examples/schedule-generator-v1'
        schema=json.loads((ROOT/'schemas/schedule-generator-bundle-v1.schema.json').read_text())
        for name in ('medium-office','two-apartments','mixed-families','all-declared-cases'):
            target=directory/(name+'-bundle.json.gz')
            self.assertTrue(target.exists(),'Complete generated example is missing')
            request=json.loads((directory/(name+'-request.json')).read_text())
            from atlas_schedules.resources import strict_json
            bundle=strict_json(gzip.decompress(target.read_bytes()),str(target))
            self.assert_conserved(bundle)
            self.assertEqual(list(Draft202012Validator(schema).iter_errors(bundle)),[])
            self.assertEqual(request['params']['resource_set_id'],self.resources.resource_set_id)
            if name=='medium-office':
                regenerated=self.generate(request['params'],request['seed'])
                self.assertEqual(compare_bundles(regenerated,bundle,self.resources.get('reference','comparison-policy')),[])
            if name=='all-declared-cases':
                self.assertEqual({c['generation']['case_id'] for c in bundle['constituents']},
                                 {c['case_id'] for c in self.resources.get('reference','m1-scope')['cases']})

    def test_unknown_kernel_channel_cannot_disappear_as_inactive(self):
        from atlas_schedules.residential import generate_residential
        from atlas_schedules.programs import resolve_program
        def unknown(inputs,unit_seed,resources):
            result=generate_residential(inputs,unit_seed,resources)
            result['channels']['unresolved_active_load']=[0.2]*8760
            return result
        for false_absence in (False,True):
            def prepared(program,inputs,resources):
                resolved=resolve_program(program,inputs,resources)
                if false_absence:
                    resolved['evidence'][0]['absent_demands'].append({'end_use':'unresolved_active_load','value':False})
                return resolved
            with self.subTest(false_absence=false_absence):
                with patch('atlas_schedules.generator.generate_residential',side_effect=unknown),\
                        patch('atlas_schedules.generator.resolve_program',side_effect=prepared),self.assertRaises(GeneratorError) as raised:
                    self.generate(self.params([self.instance('unit',VACANT)]),42)
                self.assertEqual(raised.exception.code,'invalid_channels')
