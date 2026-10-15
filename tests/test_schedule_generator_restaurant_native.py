"""Actual source/reviewed native water/HOO evidence, before release certification."""
import copy
import hashlib
import json
import math
from pathlib import Path
import unittest

from atlas_schedules.calendar import evaluate_rules
from atlas_schedules.errors import GeneratorError

ROOT=Path(__file__).resolve().parents[1]
from scripts.schedule_generator_reference import load_restaurant_water_reference


def water_context(given,native):
    schedule=given['people_schedule']
    parts=[dict(schedule=copy.deepcopy(schedule),nominal_people=p['nominal_people'],residential=p['residential'],
        source_space_name=p['space_name'],program_id=p['program_id'],source_program_id=p['source_program_id'],
        source_floor_area_m2=p['floor_area_m2'],source_multiplier=p['multiplier'],
        source_density_person_m2=p['source_density_person_m2'],
        evidence={'source_geometry':given['geometry_receipt'],'source_people_definition':given['people'][i]['source_definition'],
            'native_nominal_people':p['nominal_people'],'source_method':'space.rb:423-518 People.getNumberOfPeople(space.floorArea); same schedule weights added before round6',
            'native_capture_output_sha256':'f195b7f97b9d386f6e6660948c6cadb52a7d6bd3a51b5f3527edd09fa923f039'})
        for i,p in enumerate(native['people'])]
    return {'year':2007,'holidays':[],'steps_per_hour':6,'standards_version':'0.8.6',
        'configuration_id':given['source_hoo_configuration_id'],'source_hoo_configuration_id':given['source_hoo_configuration_id'],
        'slot_sources':{'hot_water_volume':given['water_schedule']},'slot_modes':{'hot_water_volume':'hours'},
        'occupancy_aggregation':{'policy':'explicit_source_model_nonresidential_people',
            'source_hoo_configuration_id':given['source_hoo_configuration_id'],'evidence_view':given['evidence_view'],
            'constituents':parts,'source_model_scope':copy.deepcopy(given['adaptation']),
            'interpretation':'Exact native source/view model reference; physical fixture extent separately caller-bound'},
        'occupancy_adjustment':{'peak_occ_frac':.231,'source_key':'comstock__resources__options_lookup_tsv',
            'source_options':['baseline_hvac_sizing=autosize','baseline_hvac_sizing=hardsize']},
        'source_clock':{'TZ':'UTC','variant':'controlled_no_DST_local_standard_calendar'},
        'parametric_apply':copy.deepcopy(given['parametric_apply'])}


class RestaurantNativeWaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        captured=load_restaurant_water_reference()
        cls.inputs={c['case_id']:c for c in captured['inputs']['cases']}
        cls.native={c['case_id']:c for c in captured['native']['cases']}

    def test_literal_fixed_operand_projection_closes_actual_arrays_and_rejects_mutations(self):
        from scripts.schedule_generator_restaurants import fixed_native_operand_projection,validate_fixed_native_operands
        captured=load_restaurant_water_reference();projection=fixed_native_operand_projection(captured)
        validate_fixed_native_operands(projection,captured)
        self.assertEqual(projection['source_capture']['payload_sha256'],captured['lock']['vectors']['payload_sha256'])
        for source,projected in zip(captured['native']['cases'],projection['cases']):
            self.assertEqual(source['case_id'],projected['case_id'])
            for native,fixture in zip(source['fixtures'],projected['fixtures']):
                self.assertEqual(native['source_service_id'],fixture['source_service_id'])
                for name,control in fixture['controls'].items():
                    actual=native['controls'][name]
                    self.assertNotIn('values',control)
                    self.assertEqual(control['profiles'],actual['profiles'])
                    self.assertEqual(control['special_profiles'],actual['special_profiles'])
                    self.assertEqual(control['hourly_count'],8760)
                    self.assertTrue(all(v==control['hourly_value'] for v in actual['values']))
        for mutation in ('missing','pointer','profile','hourly','native_body'):
            projected=copy.deepcopy(projection);actual=copy.deepcopy(captured)
            control=projected['cases'][0]['fixtures'][0]['controls']['target_temperature']
            if mutation=='missing':projected['cases'].pop()
            elif mutation=='pointer':control['source_native_pointer']='/cases/999999'
            elif mutation=='profile':control['profiles']['default'][0][1]+=1
            elif mutation=='hourly':control['hourly_value']+=1
            else:actual['native']['cases'][0]['fixtures'][0]['controls']['target_temperature']['values'][0]+=1
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):validate_fixed_native_operands(projected,actual)

    def test_actual_twenty_view_specific_people_aggregations_match_native_daily_hoo(self):
        from atlas_schedules.commercial.parametric import _infer
        seen=set()
        for key,native in self.native.items():
            given=self.inputs[key];config=given['source_hoo_configuration_id']
            if config in seen:continue
            seen.add(config)
            with self.subTest(configuration=config):
                actual=_infer(water_context(given,native))
                expected=[]
                for day in range(1,366):
                    index=next(k for k,days in native['inferred_original']['days_used'].items() if day in days)
                    expected.append(native['inferred_original']['profiles']['default' if index=='-1' else index])
                self.assertEqual(actual['daily_profiles'],expected)
        self.assertEqual(len(seen),20)

    def test_actual_selected_false_water_profiles_specials_and_hourly_values(self):
        from atlas_schedules.commercial.parametric import transform_commercial
        for key,native in self.native.items():
            given=self.inputs[key];context=water_context(given,native)
            with self.subTest(case_id=key):
                actual=transform_commercial({'hot_water_volume':evaluate_rules(given['water_schedule'],2007,[])['values']},given['operating'],context)
                for hour,(a,b) in enumerate(zip(actual['channels']['hot_water_volume'],native['final_water']['values'])):
                    self.assertTrue(math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-8),(key,hour,a,b))
                for day,profile in enumerate(actual['source_context']['transforms']['hot_water_volume']['daily_profiles'],1):
                    index=next(k for k,days in native['final_water']['days_used'].items() if day in days)
                    wanted=native['final_water']['profiles']['default' if index=='-1' else index]
                    self.assertEqual([round(t*60) for t,v in profile],[round(t*60) for t,v in wanted])
                    for (_,a),(_,b) in zip(profile,wanted):self.assertTrue(math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-8))
                self.assertEqual(actual['source_context']['special_profiles']['hot_water_volume'],native['final_water']['special_profiles'])

    def test_source_configuration_scope_and_unqualified_math_remain_strict(self):
        from atlas_schedules.commercial.parametric import _infer
        key=next(k for k in self.native if '__source__' in k);context=water_context(self.inputs[key],self.native[key])
        for mutation in ('missing_context','foreign_view','foreign_configuration','missing_people','foreign_schedule','missing_evidence','zero_weight'):
            changed=copy.deepcopy(context);aggregation=changed['occupancy_aggregation']
            if mutation=='missing_context':changed.pop('source_hoo_configuration_id')
            elif mutation=='foreign_view':aggregation['evidence_view']='reviewed'
            elif mutation=='foreign_configuration':aggregation['source_hoo_configuration_id']='medium_office_90_1_2013'
            elif mutation=='missing_people':aggregation['constituents'].pop()
            elif mutation=='foreign_schedule':aggregation['constituents'][0]['schedule']['id']='foreign-source-schedule'
            elif mutation=='missing_evidence':aggregation['constituents'][0]['evidence']={}
            else:aggregation['constituents'][0]['nominal_people']=0
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):_infer(changed)

    def test_reviewed_reference_cannot_be_replaced_by_normalized_or_tampered_people(self):
        from atlas_schedules.commercial.parametric import _infer
        key=next(k for k in self.native if '__reviewed__' in k);context=water_context(self.inputs[key],self.native[key])
        for mutation in ('normalized_policy','nominal','density','native_evidence'):
            changed=copy.deepcopy(context);aggregation=changed['occupancy_aggregation'];part=aggregation['constituents'][0]
            if mutation=='normalized_policy':aggregation['policy']='explicit_single_nonresidential_reference_carrier';part['nominal_people']=1
            elif mutation=='nominal':part['nominal_people']=1
            elif mutation=='density':part['source_density_person_m2']=1
            else:part['evidence'].pop('native_nominal_people')
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):_infer(changed)

    def test_selected_source_apply_policy_is_explicit_and_default_true_rejects(self):
        from atlas_schedules.commercial.parametric import transform_commercial
        key=next(iter(self.native));given=self.inputs[key];context=water_context(given,self.native[key])
        for mutation in ('missing','default_true','foreign_locator'):
            changed=copy.deepcopy(context)
            if mutation=='missing':changed.pop('parametric_apply')
            elif mutation=='default_true':changed['parametric_apply']['error_on_out_of_order']=True
            else:changed['parametric_apply']['source_method']='unverified arbitrary caller'
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):
                transform_commercial({'hot_water_volume':evaluate_rules(given['water_schedule'],2007,[])['values']},given['operating'],changed)

    def test_curated_reference_missing_mispointed_payload_and_scope_reject(self):
        lock=load_restaurant_water_reference()['lock']
        for mutation in ('missing','mispointed','payload_hash','foreign_config','missing_service'):
            changed=copy.deepcopy(lock)
            if mutation=='missing':changed['vectors']['source_path']='data/schedule-generator/reference/missing-native.json.gz'
            elif mutation=='mispointed':changed['vectors']['source_path']=changed['inputs']['source_path']
            elif mutation=='payload_hash':changed['vectors']['payload_sha256']='0'*64
            elif mutation=='foreign_config':changed['configuration_ids'][0]='foreign-source-configuration'
            else:changed['source_service_ids'].pop()
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):load_restaurant_water_reference(changed)


class RestaurantProgrammeReferenceTests(unittest.TestCase):
    def test_curated_actual_programme_and_public_water_associations_close(self):
        from scripts.schedule_generator_reference import load_restaurant_programme_reference,load_restaurant_public_water_reference
        programme=load_restaurant_programme_reference();water=load_restaurant_public_water_reference()
        self.assertEqual(len(programme['native']['cases']),230)
        self.assertEqual(len({c['source_case']['program_id'] for c in programme['inputs']}),46)
        self.assertEqual(len(water['native']['cases']),40)
        self.assertEqual(sum(len(c['fixtures']) for c in water['native']['cases']),52)
        for case in water['inputs']['cases']:
            self.assertEqual(case['operating']['source_seed_receipt']['operating_group'],case['source_hoo_configuration_id'])

    def test_curated_programme_missing_mispointed_duplicate_or_foreign_scope_rejects(self):
        from scripts.schedule_generator_reference import load_restaurant_programme_reference
        lock=json.loads((ROOT/'sources/schedule-generator-restaurant-programme-reference-lock.json').read_text(encoding='utf-8'))
        for mutation in ('missing','mispointed','payload','count'):
            changed=copy.deepcopy(lock)
            if mutation=='missing':changed['vectors']['source_path']='data/schedule-generator/reference/missing-programme.json.gz'
            elif mutation=='mispointed':changed['vectors']=changed['inputs']
            elif mutation=='payload':changed['vectors']['payload_sha256']='0'*64
            else:changed['capture_summary']['programme_count']=45
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):load_restaurant_programme_reference(changed)


if __name__=='__main__':unittest.main()
