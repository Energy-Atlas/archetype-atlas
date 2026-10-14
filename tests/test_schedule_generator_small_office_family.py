"""Exact SmallOffice selector, carriers and native cumulative expansion."""
import json
from pathlib import Path
import tempfile
import unittest

from atlas_schedules.resources import ResourceSet

ROOT = Path(__file__).resolve().parents[1]


class SmallOfficeFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.resources=None

    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()

    def family(self):
        from scripts.schedule_generator_build import build_resources
        if self.__class__.resources is None:
            manifest=build_resources(Path(self.directory.name),'small-office')
            self.__class__.resources=ResourceSet(Path(self.directory.name),manifest['resource_set_id'])
        return self.__class__.resources

    def test_scope_preserves_completed_cases_and_actual_records(self):
        from scripts.schedule_generator_families import prepare_small_office_family
        scope, lock = prepare_small_office_family()
        prior = json.loads((ROOT/'sources/schedule-generator-medium-office-scope.json').read_text())
        self.assertEqual(scope['cases'][:61], prior['cases'])
        self.assertEqual(len(scope['cases']), 79)
        additions = scope['cases'][61:]
        self.assertEqual(len({c['template'] for c in additions}), 5)
        self.assertTrue(all(c['building_type']=='SmallOffice' and c['configuration']['conditioning_inputs']=={'building_type':'small_office'} for c in additions))
        self.assertEqual(lock['scope_cases'], scope['cases'])

    def test_selector_closure_and_same_template_view_carriers(self):
        from atlas_schedules.commercial.sampling import sample_operating_parameters, select_conditional
        from atlas_schedules.errors import GeneratorError
        resources=self.family()
        for case in resources.manifest['cases'][61:]:
            recipe=resources.get('program', case['program_id'])['recipe']
            carrier=resources.get('program', recipe['source_context']['carrier_program_id'])['definition']
            self.assertEqual((carrier['building_type'],carrier['template'],carrier['evidence_view']),('SmallOffice',case['template'],case['evidence_view']))
            self.assertIn('Office_SmallOffice',carrier['name'])
            original={d['demand_id']:d for d in resources.get('program',case['program_id'])['definition']['loads']}
            for demand in recipe['resolved']['demands']:
                for field in ('value','unit','basis'):self.assertEqual(demand[field],original[demand['demand_id']][field])
        a=sample_operating_parameters({'building_type':'small_office'},42,resources)
        self.assertEqual(len(a['draw_receipts']),10)
        self.assertTrue(all(r['selectors']['building_type']=='small_office' for r in a['draw_receipts']))
        table=resources.get('commercial','small_office__plugload_sch_weekday_base_peak_ratio')
        row=next(r for r in table['rows'] if sum(r['probabilities'])<1-1e-10)
        with self.assertRaises(GeneratorError): select_conditional(table,row['selectors'],1-1e-12)

    def test_actual_native_profiles_are_present(self):
        import gzip,math
        from atlas_schedules.commercial.parametric import transform_commercial
        path=ROOT/'data/schedule-generator/small-office-family-native.json.gz'
        self.assertTrue(path.exists(),'Exact SmallOffice native capture missing')
        capture=json.loads(gzip.decompress(path.read_bytes()))
        self.assertEqual(len(capture['cases']),90)
        for case in capture['cases']:
            context=dict(case['source_context'],slot_sources=case['schedules'])
            actual=transform_commercial(case['original_channels'],case['operating'],context)
            self.assertEqual(set(actual['channels']),set(case['channels']))
            for slot,want in case['channels'].items():
                self.assertEqual(len(actual['channels'][slot]),8760)
                self.assertEqual(len(want),8760)
                tolerance=1e-4 if 'setpoint' in slot else 1e-6 if slot=='activity' else 1e-8
                for i,(x,y) in enumerate(zip(actual['channels'][slot],want)):
                    self.assertAlmostEqual(x,y,delta=tolerance,msg=(case['case_id'],slot,i,x,y))
                for day,profile in enumerate(actual['source_context']['transforms'][slot]['daily_profiles'],1):
                    key=next(k for k,days in case['final'][slot]['days_used'].items() if day in days)
                    native=case['final'][slot]['profiles']['default' if key=='-1' else key]
                    self.assertEqual([round(t*60) for t,v in profile],[round(t*60) for t,v in native])
                    for (_,value),(_,want_value) in zip(profile,native):self.assertTrue(math.isclose(value,want_value,rel_tol=1e-6,abs_tol=1e-8))
            self.assertEqual(actual['source_context']['special_profiles'],case['special_profiles'])
            self.assertEqual(actual['source_context']['inference']['daily_hoo'],[next(value for value in case['inference']['hoo'].values() if day in value['days_used']) for day in range(1,366)])
            receipts=[r for result in actual['source_context']['transforms'].values() for r in result.get('source_discard_receipts',[])]
            expected=[]
            for slot in ('lighting','electric_equipment'):
                for key,points in case['pre_adjustment'].get(slot,{}).get('profiles',{}).items():
                    if len(points)>1 and max(v for _,v in points)==min(v for _,v in points)>0 and case['final'][slot]['profiles'][key]==[[24.0,0.0]]:
                        expected.extend((slot,day) for day in case['final'][slot]['days_used'].get(key,[]))
            self.assertEqual(sorted((r['slot'],r['day_of_year']) for r in receipts),sorted(expected))
            self.assertTrue(all(r['arithmetic']['new_values']=='NaN' and r['native_default_profile']==[[24.0,0.0]] and r['source_method_evidence'] for r in receipts))

    def test_native_discrete_options_match_exact_selector_rows(self):
        import gzip,zipfile
        from atlas_schedules.commercial.sampling import select_conditional
        from scripts.schedule_generator_sources import compile_member
        path=ROOT/'data/schedule-generator/small-office-family-native.json.gz'
        capture=json.loads(gzip.decompress(path.read_bytes()))
        lock=json.loads((ROOT/'sources/schedule-generator-small-office-lock.json').read_text())
        source=next(a for a in lock['archives'] if a['source_id']=='comstock' and a['format']=='zip')
        with zipfile.ZipFile(ROOT/'data/raw'/source['cache_path']) as archive:
            tables={e['key']:compile_member(archive.read(e['path']),e,source) for e in source['members'] if e['key'].startswith('small_office__')}
        for row in capture['conditional_vectors']:
            self.assertEqual(row['selectors']['building_type'],'small_office')
            table=tables['small_office__'+row['parameter']]
            actual=select_conditional(table,row['selectors'],row['uniform'])
            self.assertEqual((actual['source_row'],actual['original_option']),(row['source_row'],row['selected_option']))

    def test_join_closes_all_three_actual_components(self):
        import copy
        from atlas_schedules.resources import write_resources
        from scripts.schedule_generator_release import validate_native_join
        scope=json.loads((ROOT/'sources/schedule-generator-small-office-scope.json').read_text())
        join=json.loads((ROOT/'data/schedule-generator/small-office-cumulative-native.json').read_text())
        records={('reference','family-native-join'):join}
        for component in join['components']:records['reference',component['reference_resource_key']]=component['lock']
        with tempfile.TemporaryDirectory() as directory:
            def resources(values):
                root=Path(directory)/str(len(list(Path(directory).iterdir())))
                manifest=write_resources(root,values,{})
                return ResourceSet(root,manifest['resource_set_id'])
            validate_native_join(resources(records),scope)
            for mutation in ('missing','mispointed','duplicate'):
                bad=copy.deepcopy(records)
                if mutation=='missing':bad.pop(('reference','small-office-native-lock'))
                if mutation=='mispointed':bad['reference','family-native-join']['fixture_bindings'][-1]['reference_resource_key']='commercial-native-lock'
                if mutation=='duplicate':bad['reference','family-native-join']['components'].append(copy.deepcopy(join['components'][-1]))
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate_native_join(resources(bad),scope)

    def test_multiple_seeds_and_actual_three_family_mixture(self):
        import math
        from unittest.mock import patch
        from atlas_schedules import generate
        from atlas_schedules.contract import validate_bundle
        from scripts.schedule_generator_release import _mixed_request
        resources=self.family()
        calendar={'year':2007,'clock':'local_standard_time','holidays':[]}
        for case in resources.manifest['cases'][61:]:
            instance={'key':case['case_id'],'program_id':case['program_id'],
                'inputs':resources.get('program',case['program_id'])['recipe']['bound_inputs'],
                'basis_bindings':{},'operating_group':None}
            params={'resource_set_id':resources.resource_set_id,'calendar':calendar,'instances':[instance]}
            with self.subTest(program=case['program_id']),patch.object(ResourceSet,'load',return_value=resources):
                a,b=[generate(params,seed) for seed in (42,51)]
                for bundle in (a,b):
                    validate_bundle(bundle)
                    for binding in bundle['bindings']:
                        if binding['kind']!='load':continue
                        actual=math.fsum(bundle['schedules'][binding['schedule_id']]['values'])*binding['effective_magnitude']['value']
                        self.assertTrue(math.isclose(actual,binding['reference_target']['total'],rel_tol=1e-8,abs_tol=1e-12))
                self.assertEqual([v['reference_target'] for v in a['bindings'] if v['kind']=='load'],[v['reference_target'] for v in b['bindings'] if v['kind']=='load'])
                if 'Office_SmallOffice' in case['name']:
                    occupancy=a['constituents'][0]['schedule_ids']['occupancy']
                    self.assertNotEqual(a['schedules'][occupancy]['values'],b['schedules'][occupancy]['values'])
                    activity=a['constituents'][0]['schedule_ids']['activity']
                    self.assertEqual(a['schedules'][activity]['values'],b['schedules'][activity]['values'])
                else:self.assertEqual(a['schedules'],{})
        request=_mixed_request(resources.get('reference','m1-scope'),resources)
        self.assertEqual(len(request['params']['instances']),3)
        with patch.object(ResourceSet,'load',return_value=resources):bundle=generate(request['params'],request['seed'])
        validate_bundle(bundle)
        mixed=bundle['constituents'][-1]
        self.assertEqual(len(mixed['generation']['people_pairs']),3)
        for index in mixed['binding_indices']:
            binding=bundle['bindings'][index]
            if binding['kind']!='load':continue
            components=binding['reference_target']['evidence']['components']
            for hour in range(8760):
                actual=bundle['schedules'][binding['schedule_id']]['values'][hour]*binding['effective_magnitude']['value']
                want=math.fsum(v['factor']*bundle['bindings'][v['binding_index']]['effective_magnitude']['value']*bundle['schedules'][v['schedule_id']]['values'][hour] for v in components)
                self.assertTrue(math.isclose(actual,want,rel_tol=1e-12,abs_tol=1e-12))

    def test_rebuilt_certification_closes_actual_source_operands(self):
        from scripts.schedule_generator_release import validate_family_certification
        resources=self.family()
        validate_family_certification(resources,resources.get('reference','m1-scope'))


if __name__=='__main__': unittest.main()
