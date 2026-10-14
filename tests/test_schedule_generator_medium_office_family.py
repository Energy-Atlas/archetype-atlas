"""Cumulative scope must bind every real MediumOffice template/view carrier."""
import json
from pathlib import Path
import tempfile
import unittest
from atlas_schedules.resources import ResourceSet
ROOT = Path(__file__).resolve().parents[1]

class MediumOfficeFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.resources=None

    @classmethod
    def tearDownClass(cls): cls.directory.cleanup()

    def family(self):
        if self.__class__.resources is None:
            from scripts.schedule_generator_build import build_resources
            manifest=build_resources(Path(self.directory.name),'medium-office')
            self.__class__.resources=ResourceSet(Path(self.directory.name),manifest['resource_set_id'])
        return self.__class__.resources

    def test_cumulative_source_scope_preserves_existing_order(self):
        from scripts.schedule_generator_families import prepare_medium_office_family
        scope, lock = prepare_medium_office_family()
        original = json.loads((ROOT/'sources/schedule-generator-m1-scope.json').read_text())
        residential = json.loads((ROOT/'sources/schedule-generator-residential-scope.json').read_text())
        self.assertEqual(scope['cases'][:10], original['cases'])
        self.assertEqual([c for c in scope['cases'] if c['building_type'] != 'MediumOffice'], residential['cases'])
        self.assertEqual(len(scope['cases']), 61)
        commercial = [c for c in scope['cases'] if c['building_type'] == 'MediumOffice']
        self.assertEqual(len(commercial),20)
        self.assertEqual(len({c['template'] for c in commercial}),5)
        self.assertEqual(lock['scope_cases'],scope['cases'])

    def test_native_join_rejects_missing_mispointed_duplicate_components(self):
        import copy
        from scripts.schedule_generator_release import validate_native_join
        from atlas_schedules.resources import write_resources
        scope=json.loads((ROOT/'sources/schedule-generator-medium-office-scope.json').read_text())
        receipt=json.loads((ROOT/'data/schedule-generator/medium-office-cumulative-native.json').read_text())
        records={('reference','family-native-join'):receipt}
        for component in receipt['components']: records['reference',component['reference_resource_key']]=component['lock']
        with tempfile.TemporaryDirectory() as directory:
            def resource_set(variant):
                root=Path(directory)/str(len(list(Path(directory).iterdir())))
                manifest=write_resources(root,variant,{})
                return ResourceSet(root,manifest['resource_set_id'])
            validate_native_join(resource_set(records),scope)
            for mutation in ('missing','mispointed','duplicate'):
                bad=copy.deepcopy(records)
                if mutation=='missing': bad.pop(('reference','residential-native-lock'))
                if mutation=='mispointed': bad['reference','family-native-join']['components'][0]['reference_resource_key']='commercial-native-lock'
                if mutation=='duplicate': bad['reference','family-native-join']['components'].append(copy.deepcopy(receipt['components'][0]))
                with self.subTest(mutation=mutation),self.assertRaises(ValueError): validate_native_join(resource_set(bad),scope)

    def test_public_mixed_family_example_uses_actual_bound_members(self):
        from scripts.schedule_generator_release import _mixed_request
        resources=self.family()
        scope=resources.get('reference','m1-scope')
        request=_mixed_request(scope,resources)
        instances=request['params']['instances']
        self.assertEqual(len(instances),2)
        self.assertIn('residents',instances[0]['inputs'])
        self.assertEqual(resources.get('program',instances[1]['program_id'])['definition']['template'],'DOE Ref Pre-1980')
        self.assertEqual(request['params']['resource_set_id'],resources.resource_set_id)
        self.assertEqual([m['instance_key'] for m in request['params']['mixture']['members']],[i['key'] for i in instances])

    def test_restricted_package_has_correct_counts_and_resource_identity(self):
        import copy
        from scripts.schedule_generator_release import _members
        from atlas_schedules.resources import manifest_identity
        resources=self.family()
        scope=copy.deepcopy(resources.get('reference','m1-scope'));scope['milestone_id']='C2-one'
        scope['cases']=[next(c for c in scope['cases'] if c['template']=='DOE Ref Pre-1980' and 'Office_MediumOffice' in c['name'])]
        files,identity=_members(scope,resources.root)
        manifest=json.loads(files['atlas_schedules/data/manifest.json'])
        self.assertEqual(manifest_identity(manifest),identity)
        self.assertNotEqual(identity,resources.resource_set_id)
        self.assertEqual(manifest['cases'],scope['cases'])
        guide=files['docs/schedule-generator.md'].decode()
        self.assertIn('C2-one',guide);self.assertIn('1 exact case',guide)
        self.assertNotIn('41 residential source fixtures and 20',guide)
        self.assertNotIn('mixed-family-request.json',guide)

    def test_unverified_equal_profile_arithmetic_still_fails(self):
        from atlas_schedules.commercial.parametric import _bpr
        from atlas_schedules.errors import GeneratorError
        with self.assertRaises(GeneratorError): _bpr([[4,.05],[24,.05]],.3)
        for points,ratio in [([[24,float('nan')]],.3),([[4,.05],[24,.3]],float('inf'))]:
            with self.assertRaises(GeneratorError): _bpr(points,ratio)

    def test_all_template_views_match_native_profiles(self):
        import gzip, math
        from atlas_schedules.commercial.parametric import transform_commercial
        capture=ROOT/'data/schedule-generator/medium-office-family-native.json.gz'
        self.assertTrue(capture.exists(),'Actual per-template/view native reference missing')
        reference=json.loads(gzip.decompress(capture.read_bytes()))
        self.assertEqual(len(reference['cases']),100)
        for case in reference['cases']:
            with self.subTest(case=case['case_id']):
                context=dict(case['source_context'],slot_sources=case['schedules'])
                actual=transform_commercial(case['original_channels'],case['operating'],context)
                self.assertEqual(set(actual['channels']),set(case['channels']))
                for slot,expected in case['channels'].items():
                    for index,(value,want) in enumerate(zip(actual['channels'][slot],expected)):
                        self.assertTrue(math.isclose(value,want,rel_tol=0 if 'setpoint' in slot else 1e-6,abs_tol=1e-4 if 'setpoint' in slot else 1e-6 if slot=='activity' else 1e-8),(slot,index,value,want))
                    for day,profile in enumerate(actual['source_context']['transforms'][slot]['daily_profiles'],1):
                        key=next(k for k,days in case['final'][slot]['days_used'].items() if day in days)
                        native=case['final'][slot]['profiles']['default' if key=='-1' else key]
                        self.assertEqual([round(t*60) for t,v in profile],[round(t*60) for t,v in native])
                        for (_,v),(_,want) in zip(profile,native): self.assertTrue(math.isclose(v,want,rel_tol=1e-6,abs_tol=1e-8))
                self.assertEqual(actual['source_context']['special_profiles'],case['special_profiles'])
                receipts=[r for item in actual['source_context']['transforms'].values() for r in item.get('source_discard_receipts',[])]
                expected_discards=[]
                for slot in ('lighting','electric_equipment'):
                    for key,points in case['pre_adjustment'][slot]['profiles'].items():
                        if len(points)>1 and max(v for _,v in points)==min(v for _,v in points)>0:
                            for day in case['final'][slot]['days_used'].get(key,[]):
                                if day%7==0 and case['final'][slot]['profiles'][key]==[[24.0,0.0]]:
                                    expected_discards.append((slot,day))
                self.assertEqual(sorted((r['slot'],r['day_of_year']) for r in receipts),sorted(expected_discards))
                self.assertTrue(all(r['day_of_year']%7==0 and r['arithmetic']['new_values']=='NaN' and r['native_default_profile']==[[24.0,0.0]] for r in receipts))
                self.assertEqual(actual['source_context']['inference']['daily_hoo'],[next(value for value in case['inference']['hoo'].values() if day in value['days_used']) for day in range(1,366)])

    def test_native_capture_accepts_exact_family_resources(self):
        import inspect
        from scripts.schedule_generator_reference import capture_commercial,commercial_family_capture_inputs
        self.assertIn('resources',inspect.signature(capture_commercial).parameters)
        self.assertTrue(callable(commercial_family_capture_inputs))

    def test_exact_template_view_carriers_and_original_targets(self):
        resources=self.family()
        cases=resources.manifest['cases']
        definitions=json.loads((ROOT/'data/definition-releases/v0.1.1/programs.json').read_text())
        originals={p['id']:p for p in definitions}
        for case in cases:
            if case['building_type']!='MediumOffice': continue
            recipe=resources.get('program',case['program_id'])['recipe']
            context=recipe['source_context']
            carrier=originals[context['carrier_program_id']]
            self.assertEqual(carrier['template'],case['template'])
            self.assertEqual(carrier['evidence_view'],case['evidence_view'])
            self.assertIn('Office_MediumOffice',carrier['name'])
            original={l['demand_id']:l for l in originals[case['program_id']]['loads']}
            for demand in recipe['resolved']['demands']:
                for field in ('value','unit','basis'): self.assertEqual(demand[field],original[demand['demand_id']][field])
            self.assertEqual(context['configuration_id'],recipe['bound_inputs']['configuration_id'])
        from scripts.schedule_generator_coverage import build_coverage,coverage_errors
        self.assertEqual(coverage_errors(build_coverage(resources),resources),[])
    def test_commercial_seeds_and_cumulative_mixed_member_trajectories(self):
        import math
        from unittest.mock import patch
        from atlas_schedules import generate
        from atlas_schedules.contract import validate_bundle
        resources=self.family()
        calendar={'year':2007,'clock':'local_standard_time','holidays':[]}
        def instance(case,extent=None):
            return {'key':case['case_id'],'program_id':case['program_id'],
                'inputs':resources.get('program',case['program_id'])['recipe']['bound_inputs'],
                'basis_bindings':extent or {},'operating_group':None}
        for case in resources.manifest['cases']:
            if case['building_type']!='MediumOffice': continue
            params={'resource_set_id':resources.resource_set_id,'calendar':calendar,'instances':[instance(case)]}
            with self.subTest(program=case['program_id']),patch.object(ResourceSet,'load',return_value=resources):
                a,b=(generate(params,seed) for seed in (42,51))
                for bundle in (a,b):
                    validate_bundle(bundle)
                    for binding in bundle['bindings']:
                        if binding['kind']!='load': continue
                        achieved=math.fsum(bundle['schedules'][binding['schedule_id']]['values'])*binding['effective_magnitude']['value']
                        if binding['reference_target']['unit'].startswith('m3'): achieved*=3600
                        self.assertTrue(math.isclose(achieved,binding['reference_target']['total'],rel_tol=1e-8,abs_tol=1e-12))
                self.assertEqual([c['reference_target'] for c in a['bindings'] if c['kind']=='load'],[c['reference_target'] for c in b['bindings'] if c['kind']=='load'])
                if 'Office_MediumOffice' in case['name']:
                    sid=a['constituents'][0]['schedule_ids']['occupancy']
                    self.assertNotEqual(a['schedules'][sid]['values'],b['schedules'][sid]['values'])
                    for slot in resources.get('program',case['program_id'])['recipe']['companion_rules']:
                        sid=a['constituents'][0]['schedule_ids'][slot]
                        self.assertEqual(a['schedules'][sid]['values'],b['schedules'][sid]['values'])
        residential=next(c for c in resources.manifest['cases'] if c['building_type']!='MediumOffice' and resources.get('program',c['program_id'])['recipe']['bound_inputs']['residents']>0)
        office=next(c for c in resources.manifest['cases'] if c['template']=='DOE Ref Pre-1980' and 'Office_MediumOffice' in c['name'])
        extent=lambda basis,value,unit:{'extents':{basis:{'value':value,'unit':unit,'evidence':{'caller':'explicit experiment extent'}}}}
        instances=[instance(residential,extent('dwelling_unit',1,'dwelling')),instance(office,extent('floor_area',100,'m2'))]
        params={'resource_set_id':resources.resource_set_id,'calendar':calendar,'instances':instances,
            'mixture':{'program_id':'cumulative-residential-doe-office','composition_id':None,'members':[{'instance_key':i['key'],'weight':.5} for i in instances],
                'result_basis':'floor_area','denominator':{'value':100,'unit':'m2','evidence':{'caller':'explicit mixed experiment'}}}}
        with patch.object(ResourceSet,'load',return_value=resources): bundle=generate(params,42)
        validate_bundle(bundle)
        mixed=bundle['constituents'][-1]
        self.assertEqual(len(mixed['generation']['people_pairs']),2)
        for index in mixed['binding_indices']:
            binding=bundle['bindings'][index]
            if binding['kind']!='load': continue
            components=binding['reference_target']['evidence']['components']
            for hour in range(8760):
                actual=bundle['schedules'][binding['schedule_id']]['values'][hour]*binding['effective_magnitude']['value']
                want=math.fsum(c['factor']*bundle['bindings'][c['binding_index']]['effective_magnitude']['value']*bundle['schedules'][c['schedule_id']]['values'][hour] for c in components)
                self.assertTrue(math.isclose(actual,want,rel_tol=1e-12,abs_tol=1e-12))

if __name__=='__main__': unittest.main()
