"""Original Retail records/parents/explicit fixture bindings, before shipment."""
import copy
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class RetailRecipeTests(unittest.TestCase):
    def test_exact_64_programmes_and_20_constituent_first_parents_keep_original_inputs(self):
        from scripts.schedule_generator_retail import compile_program_records
        records=compile_program_records();scope=records['reference','m1-scope']
        original=[p for p in json.loads((ROOT/'data/definition-releases/v0.1.1/programs.json').read_text()) if p['building_type']=='RetailStandalone']
        self.assertEqual([c['program_id'] for c in scope['cases']],[p['id'] for p in original])
        self.assertEqual(len(original),64)
        physical=parents=0
        for case,definition in zip(scope['cases'],original):
            recipe=records['program',case['program_id']]['recipe']
            self.assertEqual(recipe['required_contract_version'],'1.1.0')
            self.assertEqual(recipe['required_service_links'],[])
            self.assertEqual(recipe['resolved']['shared_services'],[])
            if definition['derivation']=='composed':
                parents+=1
                self.assertEqual(recipe['reference_sources'],{})
                self.assertEqual(recipe['source_context']['method'],'actual_generated_source_constituents')
                self.assertEqual(recipe['bound_inputs']['carrier_policy'],'actual_generated_source_constituents')
                self.assertEqual(recipe['source_composition']['composition_id'],definition['composition_id'])
            else:
                physical+=1;context=recipe['source_context']
                self.assertEqual(context['source_hoo_configuration_id'],case['configuration_id'])
                self.assertEqual(context['occupancy_aggregation']['source_model_scope']['model_family'],'RetailStandalone')
                self.assertNotIn('carrier_program_id',context)
                self.assertEqual(recipe['bound_inputs']['carrier_policy'],'explicit_source_model_nonresidential_people')
                originals={l['demand_id']:l for l in definition['loads']}
                for demand in recipe['resolved']['demands']:
                    for field in ('value','unit','basis'):self.assertEqual(demand[field],originals[demand['demand_id']][field])
        self.assertEqual((physical,parents),(44,20))


    def test_three_unallocated_absolute_main_definitions_have_exact_six_view_cases(self):
        from scripts.schedule_generator_retail import compile_service_records,load_context_reference
        from atlas_schedules.services import resolve_physical_service
        from atlas_schedules.companions import generate_companions
        records=compile_service_records();self.assertEqual(len([k for k in records if k[1].startswith('physical-service__')]),3)
        class Resources:
            resource_set_id="test-retail-actual-native-operands"
            def get(self,kind,key):return copy.deepcopy(records[kind,key])
        captured=load_context_reference();observed=0
        for native in captured['vectors']['cases']:
            sid=native['source_service_id']
            if sid is None:continue
            record=records['reference','physical-service__'+sid]
            self.assertEqual(record['definition']['beneficiary_program_ids'],[])
            self.assertEqual(record['definition']['load']['basis'],'absolute')
            self.assertEqual(record['definition']['load']['value'],1.8927058920000003e-5)
            self.assertEqual(len(record['recipe']['configurations']),2)
            instance={'key':'explicit-main','owner_kind':'physical_service','source_service_id':sid,'physical_id':'caller-main',
                'inputs':{'source_hoo_configuration_id':native['configuration_id'],'physical_fixture_evidence':{'caller':'Explicit absolute source main'}},
                'operating_group':native['configuration_id'],'basis_bindings':{'multiplicity':1,
                    'extents':{'absolute':{'value':1,'unit':'1','evidence':{'caller':'Explicit whole fixture once'}}}}}
            resolved=resolve_physical_service(instance,{'year':2007,'clock':'local_standard_time','holidays':[]},Resources())
            self.assertNotIn('program_id',resolved)
            self.assertEqual(resolved['shared_services'][0]['extent']['value'],1)
            actual=generate_companions(resolved,Resources())
            for slot,source in [('water_target_temperature','target_temperature'),('water_sensible_fraction','sensible_fraction'),('water_latent_fraction','latent_fraction')]:
                self.assertEqual(actual['channels'][slot],native['controls'][source]['values'])
                self.assertEqual(resolved['inputs']['companion_rules'][slot]['method'],'native_constant_ruleset')
            self.assertEqual(record['definition']['load']['zone_heat_assignment'],'unresolved')
            observed+=1
        self.assertEqual(observed,12)


class RetailPublicFamilyTests(unittest.TestCase):
    def test_complete_ordered_family_request_runs_both_seeds_and_binds_original_targets(self):
        import math
        import tempfile
        from unittest.mock import patch
        from atlas_schedules import generate
        from atlas_schedules.contract import validate_bundle
        from atlas_schedules.resources import ResourceSet,write_resources
        from scripts.schedule_generator_retail import compile_program_records,compile_service_records,qualification_request
        records=compile_program_records();records.update(compile_service_records())
        params=qualification_request(records)
        self.assertEqual(len(params['instances']),70)
        self.assertEqual([i['program_id'] for i in params['instances'][:64]],
            [c['program_id'] for c in records['reference','m1-scope']['cases']])
        self.assertTrue(all(i['owner_kind']=='physical_service' for i in params['instances'][64:]))
        import hashlib,time
        from atlas_schedules.canonical import canonical
        targets=[];fixed=[];variable=[];measurements=[]
        with tempfile.TemporaryDirectory() as directory:
            manifest=write_resources(Path(directory),records,{'scope':'Retail-qualification-test-not-certification'})
            resources=ResourceSet(Path(directory),manifest['resource_set_id'])
            params['resource_set_id']=resources.resource_set_id
            for seed in (42,51):
                started=time.monotonic()
                with patch.object(ResourceSet,'load',return_value=resources):bundle=generate(params,seed)
                generation_seconds=time.monotonic()-started
                validate_bundle(bundle)
                self.assertEqual(len(bundle['constituents']),128)
                parents=[o for o in bundle['constituents'] if o['generation'].get('method')=='conserved_source_composition']
                self.assertEqual(len(parents),20)
                self.assertEqual(len([o for o in bundle['constituents'] if o['owner_kind']=='physical_service']),6)
                self.assertEqual(bundle['generation']['request_instance_order'],[i['key'] for i in params['instances']])
                targets.append([hashlib.sha256(canonical(b['reference_target'])).hexdigest() for b in bundle['bindings'] if b['kind']=='load'])
                fixed_ids={o['schedule_ids'][slot] for o in bundle['constituents'] for slot in o['generation'].get('companions',{}).get('companion_receipts',{})}
                # Actual native294 activity observations are constant and unchanged.
                activity_ids={o['schedule_ids']['activity'] for o in bundle['constituents'] if 'activity' in o['schedule_ids']}
                self.assertTrue(all(len(set(bundle['schedules'][sid]['values']))==1 for sid in activity_ids))
                fixed_ids.update(activity_ids)
                self.assertTrue(fixed_ids)
                fixed.append({k:hashlib.sha256(canonical(v['values'])).hexdigest() for k,v in bundle['schedules'].items() if k in fixed_ids})
                variable.append({k:hashlib.sha256(canonical(v['values'])).hexdigest() for k,v in bundle['schedules'].items() if k not in fixed_ids})
                self.assertTrue(any(len(set(v['values']))>1 for k,v in bundle['schedules'].items() if k not in fixed_ids))
                for owner in parents:
                    for index in owner['binding_indices']:
                        b=bundle['bindings'][index]
                        if b['kind']!='load':continue
                        components=b['reference_target']['evidence']['components']
                        expected=math.fsum(c['factor']*bundle['bindings'][c['binding_index']]['reference_target']['total'] for c in components)
                        self.assertAlmostEqual(b['reference_target']['total'],expected,delta=max(1e-8,abs(expected)*1e-12))
                measurements.append({'seed':seed,'generation_seconds':generation_seconds,'requested_owners':70,
                    'actual_owners':len(bundle['constituents']),'source_parents':len(parents),'physical_services':6,
                    'schedules':len(bundle['schedules']),'bindings':len(bundle['bindings']),'fixed_channel_count':len(fixed_ids)})
                del bundle
        self.assertEqual(targets[0],targets[1])
        self.assertEqual(fixed[0],fixed[1])
        self.assertNotEqual(variable[0],variable[1])
        (ROOT/'build/task-10/retail-public-family-green-20261014-03.json').write_bytes(canonical({'status':'passed_public_family_test_not_certification','measurements':measurements,
            'target_hashes_equal_across_seeds':True,'fixed_array_hashes_equal_across_seeds':True,'generated_arrays_vary_across_seeds':True}))


if __name__=='__main__':unittest.main()
