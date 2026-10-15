"""Exact native Retail source/view contexts; full programme qualification separate."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import unittest

from atlas_schedules.errors import GeneratorError
from atlas_schedules.commercial.parametric import _infer

ROOT=Path(__file__).resolve().parents[1]


def captured_context(given,native):
    inventory=copy.deepcopy(native['native_people']);parts=[]
    for person in inventory:
        if person['nominal_people']==0:continue
        parts.append({'schedule':copy.deepcopy(next(p['schedule'] for p in given['source_people'] if p['space_name']==person['space_name'])),
            'nominal_people':person['nominal_people'],'residential':person['residential'],
            'source_space_name':person['space_name'],'program_id':person['program_id'],
            'source_program_id':person['source_program_id'],'source_floor_area_m2':person['floor_area_m2'],
            'source_multiplier':person['multiplier'],'source_density_person_m2':person['source_density_person_m2'],
            'evidence':{'source_people_definition':copy.deepcopy(person['source_definition']),
                'source_people_field':copy.deepcopy(person['source_field_evidence']),
                'native_nominal_people':person['nominal_people'],
                'native_people_object_handle':person['native_people_object_handle'],
                'source_geometry':copy.deepcopy(given['geometry_receipt'])}})
    scope=dict(copy.deepcopy(given['adaptation']),model_family='RetailStandalone',
        original_people_inventory=inventory,native_people_object_count=native['native_people_object_count'],
        native_sorted_space_order=copy.deepcopy(native['source_space_order']))
    config=given['configuration_id']
    lock=json.loads((ROOT/'sources/schedule-generator-retail-context-reference-lock.json').read_text())
    caller=next(e for e in lock['source_runtime_primary_dependency_receipts']['files'] if e['path']=='source/create_typical.rb')
    policy=dict(copy.deepcopy(given['parametric_apply']),source_member=copy.deepcopy(caller))
    return {'year':2007,'holidays':[],'configuration_id':config,'source_hoo_configuration_id':config,
        'standards_version':'0.8.6','steps_per_hour':6,
        'source_clock':{'TZ':'UTC','variant':'controlled_no_DST_local_standard_calendar'},
        'parametric_apply':policy,
        'occupancy_aggregation':{'policy':'explicit_source_model_nonresidential_people',
            'source_hoo_configuration_id':config,'evidence_view':given['evidence_view'],
            'constituents':parts,'source_model_scope':scope}}


class RetailNativeContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lock=json.loads((ROOT/'sources/schedule-generator-retail-context-reference-lock.json').read_text())
        values={}
        for key in ('inputs','vectors'):
            entry=lock[key];blob=(ROOT/entry['source_path']).read_bytes()
            assert hashlib.sha256(blob).hexdigest()==entry['sha256'] and len(blob)==entry['size_bytes']
            raw=gzip.decompress(blob)
            assert hashlib.sha256(raw).hexdigest()==entry['payload_sha256'] and len(raw)==entry['payload_size_bytes']
            values[key]=json.loads(raw)
        cls.given={c['case_id']:c for c in values['inputs']['cases']}
        cls.native=values['vectors']['cases']

    def test_all_ten_source_view_people_contexts_match_actual_native_daily_hoo(self):
        self.assertEqual(len(self.native),20)
        for native in self.native:
            with self.subTest(case_id=native['case_id']):
                actual=_infer(captured_context(self.given[native['case_id']],native))
                wanted=native['original_hoo'];profiles={day:wanted['profiles']['default' if rule=='-1' else rule]
                    for rule,days in wanted['days_used'].items() for day in days}
                self.assertEqual(actual['daily_profiles'],[profiles[d] for d in range(1,366)])
                self.assertEqual(actual['source_model_people_receipt']['source_hoo_configuration_id'],native['configuration_id'])

    def test_source_zero_shared_people_inventory_and_consumed_context_cannot_be_redefined(self):
        native=next(c for c in self.native if c['configuration_id']=='retail__90_1_2007__source')
        original=captured_context(self.given[native['case_id']],native)
        _infer(original)
        for mutation in ('zero_missing','zero_positive','shared_handle','people_missing','source_order','wrong_view',
                         'wrong_density','wrong_native_weight','foreign_schedule','wrong_calendar','wrong_clock','wrong_caller'):
            context=copy.deepcopy(original);aggregation=context['occupancy_aggregation'];scope=aggregation['source_model_scope']
            if mutation=='zero_missing':scope['original_people_inventory']=[p for p in scope['original_people_inventory'] if p['nominal_people']>0]
            elif mutation=='zero_positive':next(p for p in scope['original_people_inventory'] if p['nominal_people']==0)['source_density_person_m2']=1
            elif mutation=='shared_handle':
                people=[p for p in scope['original_people_inventory'] if p['source_space_type']=='Retail']
                self.assertEqual(len(people),2);people[1]['native_people_object_handle']='foreign-native-object'
            elif mutation=='people_missing':aggregation['constituents'].pop()
            elif mutation=='source_order':aggregation['constituents'].reverse()
            elif mutation=='wrong_view':aggregation['evidence_view']='reviewed'
            elif mutation=='wrong_density':aggregation['constituents'][0]['source_density_person_m2']*=2
            elif mutation=='wrong_native_weight':aggregation['constituents'][0]['nominal_people']*=2
            elif mutation=='foreign_schedule':aggregation['constituents'][0]['schedule']['id']='foreign-native-schedule'
            elif mutation=='wrong_calendar':context['year']=2008
            elif mutation=='wrong_clock':context['source_clock']['TZ']='America/New_York'
            else:context['parametric_apply']['error_on_out_of_order']=True
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):_infer(context)


    def test_malformed_native_source_proof_fails_contextually(self):
        native=self.native[0];original=captured_context(self.given[native['case_id']],native)
        for mutation in ('selection','inventory','part','geometry','policy','boolean_density','nonfinite_nominal'):
            context=copy.deepcopy(original);aggregation=context['occupancy_aggregation'];scope=aggregation['source_model_scope']
            if mutation=='selection':scope['selected_program_ids']=[{}]
            elif mutation=='inventory':scope['original_people_inventory'][0]=None
            elif mutation=='part':aggregation['constituents'][0]=None
            elif mutation=='geometry':aggregation['constituents'][0]['evidence']['source_geometry']=None
            elif mutation=='policy':context['parametric_apply']=None
            elif mutation=='boolean_density':scope['original_people_inventory'][0]['source_density_person_m2']=True
            else:scope['original_people_inventory'][0]['nominal_people']=float('nan')
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):_infer(context)


    def test_actual_twenty_public_group_draws_use_exact_retail_source_selector(self):
        from scripts.schedule_generator_retail import compile_sampling_records
        from atlas_schedules.commercial.sampling import sample_operating_parameters
        records=compile_sampling_records()
        class Resources:
            def get(self,kind,key):return copy.deepcopy(records[kind,key])
        for case in self.given.values():
            with self.subTest(case_id=case['case_id']):
                actual=sample_operating_parameters({'building_type':'retail'},case['group_seed'],Resources())
                self.assertEqual(actual['effective_values'],case['operating']['effective_values'])
                self.assertEqual([{k:r[k] for k in ('parameter','selectors','uniform','selection')} for r in actual['draw_receipts']],
                    [{k:r[k] for k in ('parameter','selectors','uniform','selection')} for r in case['operating']['draw_receipts']])
                self.assertEqual(len(actual['draw_receipts']),10)
        self.assertEqual(len(records),11)


    def test_actual_twelve_physical_main_profiles_and_hourly_values_match_native(self):
        from atlas_schedules.calendar import evaluate_rules
        from atlas_schedules.commercial.parametric import transform_commercial
        observed=0
        for native in self.native:
            if native['source_service_id'] is None:continue
            given=self.given[native['case_id']];context=captured_context(given,native)
            context.update(slot_sources={'hot_water_volume':given['water_schedule']},slot_modes={'hot_water_volume':'hours'},
                occupancy_adjustment={'peak_occ_frac':.231,'source_key':'comstock__resources__options_lookup_tsv',
                    'source_options':['baseline_hvac_sizing=autosize','baseline_hvac_sizing=hardsize']})
            with self.subTest(case_id=native['case_id']):
                actual=transform_commercial({'hot_water_volume':evaluate_rules(given['water_schedule'],2007,[])['values']},given['operating'],context)
                self.assertEqual(actual['channels']['hot_water_volume'],native['changed_water']['values'])
                wanted=native['changed_water'];profiles={day:wanted['profiles']['default' if rule=='-1' else rule]
                    for rule,days in wanted['days_used'].items() for day in days}
                for day,points in enumerate(actual['source_context']['transforms']['hot_water_volume']['daily_profiles'],1):
                    self.assertEqual(points,profiles[day])
                self.assertEqual(actual['source_context']['special_profiles']['hot_water_volume'],wanted['special_profiles'])
                observed+=1
        self.assertEqual(observed,12)

    def test_group_projection_ignores_only_method_unused_weather_with_originals_retained(self):
        from atlas_schedules.generator import _group_context
        native=self.native[0];given=self.given[native['case_id']];context=captured_context(given,native)
        context.update(method='prototype_budget_preserving_commercial_hybrid',occupancy_adjustment={'peak_occ_frac':.231},
            configuration_association={'conditioning_inputs':{'building_type':'retail'},'source_hoo_configuration_id':given['configuration_id'],
                                       'evidence_view':given['evidence_view']})
        programme={'inputs':{'source_context':context},'source':{'building_type':'RetailStandalone','template':given['template'],
            'vintage':None,'weather':{'mode':'not_used','interpretation':'Exact selected interior methods have no weather operand'}}}
        service=copy.deepcopy(programme);service['source']['weather']=None
        self.assertEqual(_group_context(programme),_group_context(service))
        self.assertIsNotNone(programme['source']['weather']);self.assertIsNone(service['source']['weather'])
        for mutation in ('configuration','view','people','calendar','caller','used_weather'):
            changed=copy.deepcopy(service);source=changed['inputs']['source_context']
            if mutation=='configuration':source['source_hoo_configuration_id']='foreign-config'
            elif mutation=='view':source['occupancy_aggregation']['evidence_view']='foreign-view'
            elif mutation=='people':source['occupancy_aggregation']['constituents'][0]['nominal_people']*=2
            elif mutation=='calendar':source['source_clock']['TZ']='America/New_York'
            elif mutation=='caller':source['parametric_apply']['error_on_out_of_order']=True
            else:changed['source']['weather']={'mode':'used','weather_id':'foreign-weather'}
            with self.subTest(mutation=mutation):
                try:actual=_group_context(changed)
                except GeneratorError:continue
                self.assertNotEqual(actual,_group_context(programme))


if __name__=='__main__':unittest.main()
