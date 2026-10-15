"""Original source service recipe/binding semantics, distinct from programme scope."""
import copy
import unittest
from unittest.mock import patch

from atlas_schedules.errors import GeneratorError


class RestaurantServiceRecipeTests(unittest.TestCase):
    def test_exact_thirteen_definitions_enumerate_twenty_six_configuration_cases(self):
        from scripts.schedule_generator_restaurants import compile_service_records
        records=compile_service_records()
        self.assertEqual(len(records),13)
        combinations=[]
        for (kind,key),record in records.items():
            self.assertEqual(kind,'reference')
            self.assertEqual(key,'physical-service__'+record['definition']['id'])
            self.assertNotIn('program_id',record['recipe']['resolved'])
            self.assertEqual(record['provenance']['source_path'],'data/definition-releases/v0.1.1/services.json')
            self.assertIn('#/',record['provenance']['source_locator'])
            variants=record['recipe']['configurations']
            self.assertEqual(len(variants),2)
            self.assertEqual({c.rsplit('__',1)[1] for c in variants},{'source','reviewed'})
            for config,variant in variants.items():
                self.assertEqual(variant['source_context']['source_hoo_configuration_id'],config)
                self.assertFalse(variant['source_context']['parametric_apply']['error_on_out_of_order'])
                self.assertEqual(variant['adaptation']['original_source_service_id'],record['definition']['id'])
                combinations.append((record['definition']['id'],config))
        self.assertEqual(len(set(combinations)),26)

    def resource_fixture(self):
        from scripts.schedule_generator_restaurants import compile_service_records
        records=compile_service_records()
        class Resources:
            resource_set_id='source-service-binding-test-only'
            def get(self,kind,key):
                if (kind,key) not in records:raise GeneratorError('missing_resource',kind+'/'+key,'Exact compiled test service absent')
                return copy.deepcopy(records[kind,key])
        return Resources()

    def instance(self,booster=False,view='source',area=200,multiplier=3):
        sid='service-26df36d04c21572b9838d63f' if booster else 'service-24ad7408506ea3d448dc35d0'
        extent={'value':1 if booster else area*multiplier,'unit':'1' if booster else 'm2',
                'evidence':{'caller':'Explicit synthetic physical fixture binding for actual source definition'}}
        inputs={'source_hoo_configuration_id':'full_service_restaurant__90_1_2013__'+view,
                'physical_fixture_evidence':{'caller':'Actual caller fixture identity/source role binding'}}
        if not booster:inputs.update(fixture_floor_area_m2=area,fixture_space_multiplier=multiplier,
            fixture_extent_evidence={'area':{'value':area,'unit':'m2','caller':'explicit'},
                                    'multiplier':{'value':multiplier,'unit':'1','caller':'explicit'}})
        return {'owner_kind':'physical_service','source_service_id':sid,'physical_id':'caller-booster' if booster else 'caller-main',
            'key':'fixture','inputs':inputs,'operating_group':'caller-restaurant',
            'basis_bindings':{'extents':{'absolute' if booster else 'floor_area':extent},'multiplicity':1}}

    def test_original_per_area_main_budget_and_absolute_booster_remain_unscaled_before_rng(self):
        from atlas_schedules.services import resolve_physical_service
        resources=self.resource_fixture()
        calendar={'year':2007,'clock':'local_standard_time','holidays':[]}
        first=resolve_physical_service(self.instance(),calendar,resources)
        second=resolve_physical_service(self.instance(area=500,multiplier=2),calendar,resources)
        self.assertEqual(first['inputs']['reference_budgets'],second['inputs']['reference_budgets'])
        self.assertEqual(first['demands'][0]['value'],1.0028861931924306e-6)
        self.assertEqual(first['shared_services'][0]['extent']['value'],600)
        self.assertEqual(first['shared_services'][0]['physical_operands']['fixture_floor_area_m2'],200)
        self.assertEqual(first['shared_services'][0]['physical_operands']['fixture_space_multiplier'],3)
        self.assertEqual(first['demands'][0]['basis'],'floor_area')
        booster=resolve_physical_service(self.instance(booster=True),calendar,resources)
        self.assertEqual(booster['demands'][0]['basis'],'absolute')
        self.assertEqual(booster['demands'][0]['value'],8.390996121200001e-5)
        self.assertEqual(booster['shared_services'][0]['extent']['value'],1)
        self.assertEqual(booster['source_service_definition']['beneficiary_program_ids'],[])
        self.assertEqual(first['source_service_definition']['load']['zone_heat_assignment'],'unresolved')
        self.assertEqual(first['source_service_definition']['load']['thermal_effects'],{})

    def test_missing_foreign_or_twice_scaled_physical_bindings_reject(self):
        from atlas_schedules.services import resolve_physical_service
        resources=self.resource_fixture();calendar={'year':2007,'clock':'local_standard_time','holidays':[]}
        for mutation in ('missing_area','missing_multiplier','missing_extent_receipt','wrong_extent','extra_multiplicity',
                         'foreign_template','foreign_family','missing_context','wrong_year','unknown_service','component','unknown_operand'):
            instance=self.instance()
            calendar={'year':2007,'clock':'local_standard_time','holidays':[]}
            if mutation=='missing_area':instance['inputs'].pop('fixture_floor_area_m2')
            elif mutation=='missing_multiplier':instance['inputs'].pop('fixture_space_multiplier')
            elif mutation=='missing_extent_receipt':instance['inputs'].pop('fixture_extent_evidence')
            elif mutation=='wrong_extent':instance['basis_bindings']['extents']['floor_area']['value']*=3
            elif mutation=='extra_multiplicity':instance['basis_bindings']['multiplicity']=3
            elif mutation=='foreign_template':instance['inputs']['source_hoo_configuration_id']='full_service_restaurant__90_1_2019__source'
            elif mutation=='foreign_family':instance['inputs']['source_hoo_configuration_id']='quick_service_restaurant__90_1_2013__source'
            elif mutation=='missing_context':instance['inputs'].pop('source_hoo_configuration_id')
            elif mutation=='wrong_year':calendar={**calendar,'year':2009}
            elif mutation=='unknown_service':instance['source_service_id']='service-'+'0'*24
            elif mutation=='component':instance['inputs']['allocation_mode']='component'
            else:instance['inputs']['guessed_heater_efficiency']=.8
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):resolve_physical_service(instance,calendar,resources)

    def test_foreign_owner_and_boolean_multiplicity_cannot_masquerade_as_a_fixture(self):
        from atlas_schedules.services import resolve_physical_service
        resources=self.resource_fixture();calendar={'year':2007,'clock':'local_standard_time','holidays':[]}
        for mutation in ('foreign_owner','boolean_multiplicity'):
            instance=self.instance()
            if mutation=='foreign_owner':
                instance.update(owner_kind='program',program_id='caller-programme')
                instance.pop('source_service_id');instance.pop('physical_id')
            else:instance['basis_bindings']['multiplicity']=True
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):resolve_physical_service(instance,calendar,resources)

    def test_actual_source_fixed_controls_match_every_native_fixture_without_heat_inference(self):
        from atlas_schedules.companions import generate_companions
        from scripts.schedule_generator_restaurants import compile_service_records
        from scripts.schedule_generator_reference import load_restaurant_water_reference
        records=compile_service_records();capture=load_restaurant_water_reference();resources=self.resource_fixture()
        slots={'water_target_temperature':'target_temperature','water_sensible_fraction':'sensible_fraction','water_latent_fraction':'latent_fraction'}
        observations=0
        for native in capture['native']['cases']:
            for fixture in native['fixtures']:
                recipe=records['reference','physical-service__'+fixture['source_service_id']]['recipe']
                variant=recipe['configurations'][native['source_hoo_configuration_id']]
                resolved={'inputs':{'year':2007,'holidays':[],'companion_rules':variant['companion_rules']}}
                actual=generate_companions(resolved,resources)
                for slot,source_slot in slots.items():
                    self.assertEqual(actual['channels'][slot],fixture['controls'][source_slot]['values'])
                    self.assertEqual(actual['source_context']['companion_receipts'][slot]['method'],'native_constant_ruleset')
                    receipt=actual['source_context']['companion_receipts'][slot]
                    self.assertEqual(receipt['native_getter_precision']['actual_native_source_profile'],fixture['controls'][source_slot]['profiles']['default'])
                    self.assertEqual(receipt['native_getter_precision']['hourly_value'],fixture['controls'][source_slot]['values'][0])
                    self.assertEqual(receipt['native_getter_precision']['native_special_profiles'],fixture['controls'][source_slot]['special_profiles'])
                self.assertEqual(recipe['resolved']['source_service_definition']['load']['thermal_effects'],{})
                observations+=1
        self.assertEqual(observations,52)

    def test_native_fixed_control_storage_and_getter_receipts_are_strict(self):
        from atlas_schedules.companions import generate_companions
        from scripts.schedule_generator_restaurants import compile_service_records
        recipe=next(iter(compile_service_records().values()))['recipe'];resources=self.resource_fixture()
        variant=next(iter(recipe['configurations'].values()))
        for mutation in ('missing_original','boolean','nonfinite','wrong_storage','wrong_hourly','unknown_slot','missing_native_evidence','wrong_special'):
            rules=copy.deepcopy(variant['companion_rules']);slot='water_target_temperature';rule=rules[slot]
            if mutation=='missing_original':rule.pop('original_value')
            elif mutation=='boolean':rule['original_value']=True
            elif mutation=='nonfinite':rule['original_value']=float('nan')
            elif mutation=='wrong_storage':rule['stored_value']+=.001
            elif mutation=='wrong_hourly':rule['native_hourly_value']+=.001
            elif mutation=='unknown_slot':rules['unqualified_native_constant']=rules.pop(slot)
            elif mutation=='wrong_special':rule['native_special_profiles']['WntrDsn']=[[24,0]]
            else:rule['evidence'].pop('native_output_sha256')
            resolved={'inputs':{'year':2007,'holidays':[],'companion_rules':rules}}
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):generate_companions(resolved,resources)

    def test_actual_restaurant_sampling_uses_ten_source_draws_and_preserves_reachable_tail_error(self):
        from scripts.schedule_generator_restaurants import compile_sampling_records
        from scripts.schedule_generator_reference import load_restaurant_water_reference
        from atlas_schedules.commercial.sampling import sample_operating_parameters,select_conditional
        records=compile_sampling_records()
        class Resources:
            def get(self,kind,key):return copy.deepcopy(records[kind,key])
        resources=Resources();capture=load_restaurant_water_reference();seen=set()
        for given in capture['inputs']['cases']:
            selector=given['source_hoo_configuration_id'].split('__')[0]
            group_seed=given['operating']['source_seed_receipt']['group_seed']
            if (selector,group_seed) in seen:continue
            seen.add((selector,group_seed))
            actual=sample_operating_parameters({'building_type':selector},group_seed,resources)
            self.assertEqual(actual['effective_values'],given['operating']['effective_values'])
            self.assertEqual([{k:r[k] for k in ('parameter','uniform','selection')} for r in actual['draw_receipts']],given['operating']['draw_receipts'])
            self.assertEqual(len(actual['draw_receipts']),10)
        self.assertEqual(len(seen),40)
        for selector,row in [('full_service_restaurant',2),('quick_service_restaurant',17)]:
            table=records['commercial',selector+'__plugload_sch_weekday_base_peak_ratio']
            matched=next(r for r in table['rows'] if r['source_row']==row)
            self.assertAlmostEqual(sum(matched['probabilities']),.999999907,places=12)
            with self.assertRaises(GeneratorError) as error:select_conditional(table,matched['selectors'],.99999999)
            self.assertEqual(error.exception.code,'source_selection')
            self.assertIn('source_row='+str(row),error.exception.message)
            self.assertIn(selector,error.exception.message)
            self.assertIn('raw_cdf_sum=0.999999907',error.exception.message)


class RestaurantServiceGeneratorTests(unittest.TestCase):
    def public_resources(self):
        from scripts.schedule_generator_restaurants import compile_service_records,compile_sampling_records
        from atlas_schedules.resources import strict_json
        from scripts.common import ROOT
        records=compile_service_records();records.update(compile_sampling_records())
        cases=[{'source_service_id':r['definition']['id'],'source_hoo_configuration_id':c,
            'case_id':'C5-'+r['definition']['id']+'__'+c} for r in records.values() if 'recipe' in r
            for c in r['recipe']['configurations']]
        records['reference','m1-scope']={'milestone_id':'C5-native-service-contract-test','scope_version':'1.0.0',
            'calendar':{'year':2007},'cases':[],'service_cases':cases}
        records['reference','comparison-policy']=strict_json((ROOT/'sources/schedule-generator-policy.json').read_bytes(),'policy')
        class Resources:
            resource_set_id='actual-source-service-test-fixture-not-a-shipped-artifact'
            def get(self,kind,key):return copy.deepcopy(records[kind,key])
        return Resources()

    def test_actual_public_service_generation_closes_twenty_six_cases_two_seeds_and_fixed_controls(self):
        from atlas_schedules import generate
        from atlas_schedules.contract import validate_bundle
        from scripts.schedule_generator_reference import load_restaurant_water_reference
        resources=self.public_resources();capture=load_restaurant_water_reference();inputs={c['case_id']:c for c in capture['inputs']['cases']}
        targets={};trajectories={};observations=0
        for native in capture['native']['cases']:
            given=inputs[native['case_id']]
            for fixture in native['fixtures']:
                sid=fixture['source_service_id'];record=resources.get('reference','physical-service__'+sid)
                instance={'owner_kind':'physical_service','key':'fixture','source_service_id':sid,'physical_id':'caller-'+sid,
                    'operating_group':given['operating']['source_seed_receipt']['operating_group'],
                    'inputs':{'source_hoo_configuration_id':given['source_hoo_configuration_id'],
                              'physical_fixture_evidence':{'caller':'Explicit native source fixture association'}},
                    'basis_bindings':{'extents':{},'multiplicity':1}}
                if record['definition']['load']['basis']=='floor_area':
                    original=fixture['source_physical_reference'];area=original['floor_area_m2'];multiplier=original['multiplier']
                    instance['inputs'].update(fixture_floor_area_m2=area,fixture_space_multiplier=multiplier,
                        fixture_extent_evidence={'area':{'value':area,'unit':'m2','caller':'Explicit source reference fixture'},
                                                'multiplier':{'value':multiplier,'unit':'1','caller':'Explicit source reference fixture'}})
                    instance['basis_bindings']['extents']['floor_area']={'value':area*multiplier,'unit':'m2','evidence':{'caller':'Physical fixture area×multiplier once'}}
                else:instance['basis_bindings']['extents']['absolute']={'value':1,'unit':'1','evidence':{'caller':'Absolute whole booster once'}}
                params={'schema_version':'1.1.0','resource_set_id':resources.resource_set_id,
                    'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'instances':[instance]}
                seed=given['operating']['source_seed_receipt']['master_seed']
                with patch('atlas_schedules.generator.ResourceSet.load',return_value=resources):actual=generate(params,seed)
                validate_bundle(actual);owner=actual['constituents'][0]
                self.assertNotIn('program_id',owner);self.assertEqual(owner['source_service_id'],sid)
                water=actual['schedules'][owner['schedule_ids']['hot_water_volume']]['values']
                self.assertLess(max(abs(a-b) for a,b in zip(water,native['final_water']['values'])),1e-8)
                self.assertEqual(actual['generation']['residential_unit_order'],[])
                self.assertEqual(actual['generation']['operating_groups'][instance['operating_group']]['operating']['effective_values'],given['operating']['effective_values'])
                for slot,native_slot in [('water_target_temperature','target_temperature'),('water_sensible_fraction','sensible_fraction'),('water_latent_fraction','latent_fraction')]:
                    self.assertEqual(actual['schedules'][owner['schedule_ids'][slot]]['values'],fixture['controls'][native_slot]['values'])
                binding=actual['bindings'][0];key=(sid,given['source_hoo_configuration_id'])
                if key in targets:self.assertEqual(binding['reference_target'],targets[key])
                else:targets[key]=binding['reference_target']
                trajectories.setdefault(key,[]).append(water);observations+=1
        self.assertEqual(len(targets),26);self.assertEqual(observations,52)
        self.assertTrue(all(v[0]!=v[1] for v in trajectories.values()))

    def test_all_original_programme_recipes_use_exact_view_model_and_external_water_links(self):
        from scripts.schedule_generator_restaurants import compile_program_records,restaurant_program_cases
        records=compile_program_records();cases=restaurant_program_cases();links=[];inactive=0
        self.assertEqual(len(cases),46)
        for case in cases:
            record=records['program',case['program_id']];recipe=record['recipe'];resolved=recipe['resolved']
            self.assertEqual(recipe['bound_inputs']['source_hoo_configuration_id'],case['configuration_id'])
            self.assertEqual(recipe['source_context']['occupancy_aggregation']['policy'],'explicit_source_model_nonresidential_people')
            self.assertNotIn('carrier_program_id',recipe['source_context'])
            self.assertNotIn('hot_water_volume',{s['slot'] for s in resolved['slots']})
            self.assertEqual(resolved['shared_services'],[])
            original={l['demand_id']:l for l in record['definition']['loads']}
            for demand in resolved['demands']:
                for field in ('value','unit','basis'):self.assertEqual(demand[field],original[demand['demand_id']][field])
            required=recipe.get('required_service_links',[])
            self.assertEqual({l['source_service_id'] for l in required},set(record['definition']['service_ids']))
            links.extend(required)
            if not resolved['slots']:inactive+=1
            if case['evidence_view']=='reviewed':self.assertTrue(all('Kitchen' not in p['source_space_name'] for p in recipe['source_context']['occupancy_aggregation']['constituents']))
        self.assertEqual(len(links),10);self.assertEqual(inactive,16)


class RestaurantProgrammeServiceLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.schedule_generator_restaurants import compile_program_records
        cls.records=compile_program_records()

    def resolved_pair(self):
        from atlas_schedules.programs import resolve_program
        from atlas_schedules.services import resolve_physical_service
        records=self.records
        class Resources:
            def get(self,kind,key):return copy.deepcopy(records[kind,key])
        resources=Resources();pid='program-76fabb7b85c683f4f7d8c873'
        recipe=records['program',pid]['recipe']
        programme={'key':'kitchen','owner_kind':'program','program_id':pid,'inputs':copy.deepcopy(recipe['bound_inputs']),
            'operating_group':'actual-source-restaurant','basis_bindings':{},
            'service_links':{'service-24ad7408506ea3d448dc35d0':'main'}}
        source=resolve_program(pid,dict(programme['inputs'],year=2007,holidays=[]),resources)
        service=RestaurantServiceRecipeTests().instance(area=139.4052442,multiplier=1)
        service.update(key='main',operating_group=programme['operating_group'])
        resolved=resolve_physical_service(service,{'year':2007,'clock':'local_standard_time','holidays':[]},resources)
        return [(programme,source),(service,resolved)]

    def test_original_active_programme_water_link_resolves_existing_fixture_before_rng(self):
        from atlas_schedules.services import prepare_required_service_links
        pairs=self.resolved_pair();plans=prepare_required_service_links(pairs,'1.1.0')
        self.assertEqual(len(plans),1);plan=plans[0]
        self.assertEqual(plan['programme_instance_key'],'kitchen');self.assertEqual(plan['service_instance_key'],'main')
        self.assertEqual(plan['source_service_id'],'service-24ad7408506ea3d448dc35d0')
        self.assertEqual(plan['original_programme_load']['quantity'],'hot_water_volume')
        self.assertEqual(plan['source_reference_target'],pairs[1][1]['inputs']['reference_budgets'][plan['source_service_id']])
        self.assertEqual(len(pairs),2,'Link resolution must not create a service owner')

    def test_missing_foreign_alias_context_budget_or_version_reject_before_rng(self):
        from atlas_schedules.services import prepare_required_service_links
        for mutation in ('missing_link','missing_owner','wrong_sid','extra_booster','wrong_group','wrong_context','wrong_template',
                         'wrong_budget','wrong_beneficiary','wrong_original_load','old_contract'):
            pairs=self.resolved_pair();programme,source=pairs[0];service,resolved=pairs[1];version='1.1.0'
            if mutation=='missing_link':programme.pop('service_links')
            elif mutation=='missing_owner':pairs.pop()
            elif mutation=='wrong_sid':resolved['source_service_id']='service-'+'0'*24
            elif mutation=='extra_booster':programme['service_links']['service-26df36d04c21572b9838d63f']='main'
            elif mutation=='wrong_group':service['operating_group']='another-model'
            elif mutation=='wrong_context':resolved['inputs']['source_context']['source_hoo_configuration_id']='foreign-config'
            elif mutation=='wrong_template':resolved['source']['template']='90.1-2019'
            elif mutation=='wrong_budget':resolved['inputs']['reference_budgets'][resolved['source_service_id']]['total']*=2
            elif mutation=='wrong_beneficiary':resolved['source_service_definition']['beneficiary_program_ids']=[]
            elif mutation=='wrong_original_load':source['required_service_links'][0]['original_demand']['value']*=2
            else:version='1.0.0'
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):prepare_required_service_links(pairs,version)

    def test_actual_programme_plus_main_public_generation_and_required_mixture_closure(self):
        from atlas_schedules import generate
        records=copy.deepcopy(self.records);pairs=self.resolved_pair();instances=[p[0] for p in pairs]
        config=instances[0]['inputs']['source_hoo_configuration_id']
        for instance in instances:instance['operating_group']=config
        area=instances[1]['inputs']['fixture_floor_area_m2']
        extent={'value':area,'unit':'m2','evidence':{'caller':'Explicit source-reference programme extent, separate from HOO context'}}
        instances[0]['basis_bindings']={'extents':{'floor_area':extent},'multiplicity':1}
        scope=records['reference','m1-scope']
        scope['service_cases']=[{'source_service_id':r['definition']['id'],'source_hoo_configuration_id':c,
            'case_id':'C5-'+r['definition']['id']+'__'+c} for r in records.values() if r.get('recipe',{}).get('required_contract_version')=='1.1.0' and 'configurations' in r['recipe']
            for c in r['recipe']['configurations']]
        class Resources:
            resource_set_id='actual-programme-service-integration-test-only'
            def get(self,kind,key):return copy.deepcopy(records[kind,key])
        resources=Resources();params={'schema_version':'1.1.0','resource_set_id':resources.resource_set_id,
            'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'instances':instances,
            'mixture':{'program_id':'caller-programme-and-required-main','composition_id':None,
                'members':[{'instance_key':'kitchen','weight':1}],
                'result_basis':'floor_area','denominator':copy.deepcopy(extent)}}
        with patch('atlas_schedules.generator.ResourceSet.load',return_value=resources):actual=generate(params,42)
        kitchen,main,result=actual['constituents']
        self.assertEqual(len(kitchen['service_links']),1)
        link=kitchen['service_links'][0];self.assertIn(link['binding_index'],main['binding_indices'])
        self.assertEqual(link['source_service_id'],main['source_service_id'])
        self.assertNotIn('hot_water_volume',kitchen['schedule_ids'])
        self.assertEqual(result['generation']['service_selection']['effective_service_members'],[{'instance_key':'main'}])
        self.assertEqual(len([b for b in actual['bindings'] if b['kind']=='load' and b['reference_target']['quantity']=='hot_water_volume']),2)
        physical=actual['bindings'][link['binding_index']]
        mixed=next(actual['bindings'][i] for i in result['binding_indices'] if actual['bindings'][i]['kind']=='load' and actual['bindings'][i]['reference_target']['quantity']=='hot_water_volume')
        self.assertAlmostEqual(mixed['reference_target']['total'],physical['reference_target']['total'],places=10)
        self.assertEqual(len(actual['generation']['operating_groups']),1)
        originals=actual['generation']['operating_groups'][config]['original_owner_weather_records']
        self.assertEqual([r['weather'] for r in originals],[kitchen['source']['weather'],main['source']['weather']])

    def authority_bundle(self):
        """Actual source Kitchen/Main/Booster; public generation, no fixture oracle."""
        if not hasattr(self.__class__,'original_authority_bundle'):
            from atlas_schedules import generate
            records=copy.deepcopy(self.records);instances=[p[0] for p in self.resolved_pair()]
            config=instances[0]['inputs']['source_hoo_configuration_id']
            booster=RestaurantServiceRecipeTests().instance(booster=True)
            booster['key']='booster';instances.append(booster)
            for instance in instances:instance['operating_group']=config
            instances[0]['basis_bindings']={'floor_area_m2':100}
            scope=records['reference','m1-scope']
            scope['service_cases']=[{'source_service_id':r['definition']['id'],'source_hoo_configuration_id':c,
                'case_id':'C5-'+r['definition']['id']+'__'+c} for r in records.values()
                if 'configurations' in r.get('recipe',{}) for c in r['recipe']['configurations']]
            class Resources:
                resource_set_id='actual-original-requirement-authority-test'
                def get(self,kind,key):return copy.deepcopy(records[kind,key])
            resources=Resources();params={'schema_version':'1.1.0','resource_set_id':resources.resource_set_id,
                'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'instances':instances}
            with patch('atlas_schedules.generator.ResourceSet.load',return_value=resources):
                self.__class__.original_authority_bundle=generate(params,42)
        return copy.deepcopy(self.original_authority_bundle)

    def test_generated_original_inventory_survives_independently_and_requires_literal_true(self):
        from atlas_schedules.contract import validate_bundle
        actual=self.authority_bundle();programme=actual['constituents'][0]
        expected=self.records['program',programme['program_id']]['recipe']['required_service_links']
        self.assertEqual(programme.get('required_service_links'),expected,
                         'Original source inventory is lost after generation')
        validate_bundle(actual)
        for flag in (False,None,'true',1):
            changed=copy.deepcopy(actual);changed['constituents'][0]['required_service_links'][0]['required']=flag
            with self.subTest(flag=flag),self.assertRaises(GeneratorError):validate_bundle(changed)
        changed=copy.deepcopy(actual);changed['constituents'][0].pop('required_service_links')
        with self.assertRaises(GeneratorError):validate_bundle(changed)

    def test_coherent_main_to_booster_alias_cannot_override_original_requirement(self):
        from atlas_schedules.contract import validate_bundle
        actual=self.authority_bundle();validate_bundle(actual)
        programme,main,booster=actual['constituents'];original=copy.deepcopy(programme['service_links'][0]['evidence'])
        index=next(i for i in booster['binding_indices'] if actual['bindings'][i]['kind']=='load')
        binding=actual['bindings'][index];link=programme['service_links'][0]
        link.update(source_service_id=booster['source_service_id'],physical_id=booster['physical_id'],
            instance_key=booster['instance_key'],binding_index=index,demand_id=binding['demand_id'],
            slot=binding['slot'],schedule_id=binding['schedule_id'])
        self.assertNotEqual(main['source_service_id'],link['source_service_id'])
        self.assertEqual(link['evidence'],original,'The actual exploit leaves original Main proof unchanged')
        with self.assertRaises(GeneratorError):validate_bundle(actual)

    def test_required_aliases_cannot_be_dropped_duplicated_or_redefined(self):
        from atlas_schedules.contract import validate_bundle
        original=self.authority_bundle();validate_bundle(original)
        mutations=('missing_links','empty_links','duplicate_link','original_value','original_unit','original_basis',
                   'original_temperature','original_assignment','alias_evidence','physical_value','physical_fuel',
                   'physical_host','physical_definition','binding_original_target','configuration','source_beneficiary')
        for mutation in mutations:
            changed=copy.deepcopy(original);programme,service,booster=changed['constituents']
            link=programme['service_links'][0]
            if mutation=='missing_links':programme.pop('service_links')
            elif mutation=='empty_links':programme['service_links']=[]
            elif mutation=='duplicate_link':programme['service_links'].append(copy.deepcopy(link))
            elif mutation.startswith('original_'):
                field={'original_value':'value','original_unit':'unit','original_basis':'basis',
                       'original_temperature':'target_temperature_degC','original_assignment':'zone_heat_assignment'}[mutation]
                value={'value':2e-6,'unit':'m3/s','basis':'absolute','target_temperature_degC':82.22222,
                       'zone_heat_assignment':'invented_zone'}[field]
                # Coherently edit the alias and inventory; physical original source remains the independent check.
                if programme.get('required_service_links'):
                    programme['required_service_links'][0]['original_demand'][field]=value
                link['evidence']['original_programme_load'][field]=value
            elif mutation=='alias_evidence':link['evidence']['source_requirement']={'id':'foreign-source'}
            elif mutation=='physical_value':service['demands'][0]['value']*=2
            elif mutation=='physical_fuel':
                service['demands'][0]['fuel']='electricity'
                changed['bindings'][link['binding_index']]['fuel']='electricity'
                changed['bindings'][link['binding_index']]['reference_target']['fuel']='electricity'
            elif mutation=='physical_host':
                service['demands'][0]['host']='space'
                changed['bindings'][link['binding_index']]['host']='space'
                changed['bindings'][link['binding_index']]['reference_target']['host']='space'
            elif mutation=='physical_definition':service['shared_services'][0]['source_service_definition']['load']['value']*=2
            elif mutation=='binding_original_target':link['evidence']['source_reference_target']['total']*=2
            elif mutation=='configuration':service['generation']['source_inputs']['source_hoo_configuration_id']='foreign-context'
            else:programme['source']['source_id']='program-foreign-original-beneficiary'
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):validate_bundle(changed)

    def test_malformed_original_context_and_operating_receipts_fail_contextually(self):
        from atlas_schedules.contract import validate_bundle
        original=self.authority_bundle();validate_bundle(original)
        for mutation in ('groups','group_receipt','operating','people_context'):
            changed=copy.deepcopy(original);group=changed['constituents'][0]['generation']['operating_group']
            if mutation=='groups':changed['generation']['operating_groups']=None
            elif mutation=='group_receipt':changed['generation']['operating_groups'][group]=None
            elif mutation=='operating':changed['generation']['operating_groups'][group]['operating']=None
            else:changed['constituents'][1]['generation']['source_inputs']['occupancy_aggregation']=None
            error=None
            try:validate_bundle(changed)
            except Exception as caught:error=caught
            with self.subTest(mutation=mutation):self.assertIsInstance(error,GeneratorError,
                'Malformed actual source proof must fail contextually, not pass or leak '+repr(error))

    def test_original_inventory_and_explicit_main_deduplicate_through_public_composition(self):
        from atlas_schedules import compose_constituents
        from atlas_schedules.contract import validate_bundle
        actual=self.authority_bundle();programme,main,booster=actual['constituents']
        mixture={'program_id':'actual-required-main-result','composition_id':None,
            'members':[{'instance_key':'kitchen','weight':1}],'service_members':[{'instance_key':'main'}],
            'result_basis':'floor_area','denominator':{'value':100,'unit':'m2','evidence':{'caller':'Explicit result'}}}
        result=compose_constituents([actual],mixture,actual['metadata']['calendar']);validate_bundle(result)
        retained=result['constituents'][0]
        self.assertEqual(retained.get('required_service_links'),
            self.records['program',programme['program_id']]['recipe']['required_service_links'])
        parent=result['constituents'][-1];receipt=parent['generation']['service_selection']
        self.assertEqual(receipt['effective_service_members'],[{'instance_key':'main'}])
        self.assertTrue(receipt['required_links'][0]['deduplicated'])
        self.assertEqual(receipt['original_programme_members'],mixture['members'])
        water=next(d for d in parent['demands'] if d['quantity']=='hot_water_volume')
        physical=actual['bindings'][programme['service_links'][0]['binding_index']]
        self.assertAlmostEqual(water['annual_target']['total'],
            physical['reference_target']['total']*139.4052442/100,places=10)
        for sid in actual['schedules']:self.assertEqual(result['schedules'][sid],actual['schedules'][sid])

    def test_missing_public_programme_alias_fails_before_sampling(self):
        from atlas_schedules import generate
        records=self.records;instance=self.resolved_pair()[0][0];instance.pop('service_links')
        class Resources:
            resource_set_id='actual-missing-alias-test-only'
            def get(self,kind,key):return copy.deepcopy(records[kind,key])
        resources=Resources();params={'schema_version':'1.1.0','resource_set_id':resources.resource_set_id,
            'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'instances':[instance]}
        with patch('atlas_schedules.generator.ResourceSet.load',return_value=resources),patch('atlas_schedules.generator.sample_operating_parameters') as sampler:
            with self.assertRaises(GeneratorError) as error:generate(params,42)
        self.assertEqual(error.exception.code,'requires_binding');self.assertIn('service_links',error.exception.path)
        sampler.assert_not_called()

    def test_group_matches_only_unused_weather_representation_and_preserves_consumed_dependencies(self):
        from atlas_schedules.generator import _group_context
        pairs=self.resolved_pair();programme=pairs[0][1];service=pairs[1][1]
        original=copy.deepcopy((programme['source']['weather'],service['source']['weather']))
        self.assertNotEqual(*original)
        expected=_group_context(programme)
        self.assertEqual(expected,_group_context(service))
        self.assertEqual((programme['source']['weather'],service['source']['weather']),original)
        for mutation in ('configuration','view','people','calendar','caller','used_weather'):
            changed=copy.deepcopy(service);context=changed['inputs']['source_context']
            if mutation=='configuration':context['configuration_id']='foreign-config'
            elif mutation=='view':context['occupancy_aggregation']['evidence_view']='reviewed'
            elif mutation=='people':context['occupancy_aggregation']['constituents'][0]['nominal_people']+=1
            elif mutation=='calendar':context['source_clock']['TZ']='America/New_York'
            elif mutation=='caller':context['parametric_apply']['error_on_out_of_order']=True
            else:changed['source']['weather']={'mode':'used','weather_id':'unqualified-weather'}
            with self.subTest(mutation=mutation):
                try:actual=_group_context(changed)
                except GeneratorError:continue
                self.assertNotEqual(actual,expected)

    def test_all_46_programmes_and_26_service_cases_generate_at_two_actual_public_seeds(self):
        import math
        from atlas_schedules import generate
        from scripts.schedule_generator_restaurants import qualification_request,service_cases
        from scripts.schedule_generator_reference import load_restaurant_programme_reference,load_restaurant_public_water_reference
        records=copy.deepcopy(self.records);records['reference','m1-scope']['service_cases']=service_cases(records)
        class Resources:
            resource_set_id='actual-46-programme-26-service-public-matrix-test-only'
            def get(self,kind,key):return copy.deepcopy(records[kind,key])
        resources=Resources();params=qualification_request(records);params['resource_set_id']=resources.resource_set_id
        programme={c['case_id']:c for c in load_restaurant_programme_reference()['native']['cases']}
        water={c['case_id']:c for c in load_restaurant_public_water_reference()['native']['cases']}
        targets={};series={};fixed={}
        for seed in (42,51):
            with patch('atlas_schedules.generator.ResourceSet.load',return_value=resources):bundle=generate(params,seed)
            self.assertEqual(len(bundle['constituents']),72);self.assertEqual(len(bundle['schedules']),294)
            self.assertEqual(len(bundle['generation']['operating_groups']),20)
            self.assertEqual(sum(len(c.get('service_links',[])) for c in bundle['constituents']),10)
            for owner in bundle['constituents']:
                if owner['owner_kind']=='program':
                    expected=programme[owner['instance_key']+'@full_request-'+str(seed)]['channels']
                else:
                    config=owner['inputs']['source_hoo_configuration_id'];native=water[config+'__'+str(seed)]
                    fixture=next(f for f in native['fixtures'] if f['source_service_id']==owner['source_service_id'])
                    expected={'hot_water_volume':native['final_water']['values'],**{slot:fixture['controls'][native_slot]['values'] for slot,native_slot in
                        [('water_target_temperature','target_temperature'),('water_sensible_fraction','sensible_fraction'),('water_latent_fraction','latent_fraction')]}}
                self.assertEqual(set(owner['schedule_ids']),set(expected))
                for slot,sid in owner['schedule_ids'].items():
                    values=bundle['schedules'][sid]['values']
                    self.assertLessEqual(max(abs(a-b) for a,b in zip(values,expected[slot])),1e-8)
                    series.setdefault((owner['instance_key'],slot),[]).append(values)
                    if owner['owner_kind']=='physical_service' and slot!='hot_water_volume':
                        key=(owner['instance_key'],slot)
                        if key in fixed:self.assertEqual(values,fixed[key])
                        else:fixed[key]=values
                for index in owner['binding_indices']:
                    binding=bundle['bindings'][index]
                    if binding['kind']!='load':continue
                    key=(owner['instance_key'],binding['demand_id'])
                    if key in targets:self.assertEqual(binding['reference_target'],targets[key])
                    else:targets[key]=binding['reference_target']
                    achieved=math.fsum(bundle['schedules'][binding['schedule_id']]['values'])*binding['effective_magnitude']['value']
                    if binding['reference_target']['quantity']=='hot_water_volume':achieved*=3600
                    self.assertTrue(math.isclose(achieved,binding['reference_target']['total'],rel_tol=1e-8,abs_tol=1e-12))
        self.assertEqual(len(fixed),78);self.assertEqual(len(targets),96)
        self.assertTrue(all(values[0]!=values[1] for (key,slot),values in series.items() if slot=='hot_water_volume'))
        self.assertTrue(any(values[0]!=values[1] for (key,slot),values in series.items() if slot=='lighting'))


if __name__=='__main__':unittest.main()
