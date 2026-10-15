"""All actual Warehouse records and constituent-first source compositions."""
import json
from pathlib import Path
import tempfile
import unittest

from atlas_schedules.resources import ResourceSet

ROOT=Path(__file__).resolve().parents[1]


class WarehouseFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory();cls.resources=None

    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()

    def family(self):
        from scripts.schedule_generator_build import build_resources
        if self.__class__.resources is None:
            directory=Path(self.directory.name)
            manifest=build_resources(directory/'resources','warehouse',directory/'tables')
            self.__class__.resources=ResourceSet(directory/'resources',manifest['resource_set_id'])
        return self.__class__.resources

    def test_exact_scope_preserves_prior_cases_and_source_compositions(self):
        from scripts.schedule_generator_families import prepare_warehouse_family
        scope,lock=prepare_warehouse_family()
        prior=json.loads((ROOT/'sources/schedule-generator-small-office-scope.json').read_text())
        self.assertEqual(scope['cases'][:79],prior['cases'])
        self.assertEqual(len(scope['cases']),119)
        additions=scope['cases'][79:]
        self.assertEqual(len({c['template'] for c in additions}),5)
        definitions={p['id']:p for p in json.loads((ROOT/'data/definition-releases/v0.1.1/programs.json').read_text())}
        self.assertEqual(sum(bool(definitions[c['program_id']].get('composition_id')) for c in additions),10)
        self.assertTrue(all(c['building_type']=='Warehouse' and c['configuration']['conditioning_inputs']=={'building_type':'warehouse'} for c in additions))
        self.assertEqual(lock['scope_cases'],scope['cases'])

    def test_selector_carriers_and_exact_composed_recipes(self):
        from atlas_schedules.commercial.sampling import sample_operating_parameters
        resources=self.family()
        for case in resources.manifest['cases'][79:]:
            record=resources.get('program',case['program_id']);recipe=record['recipe']
            if record['definition'].get('composition_id'):
                allocation=recipe['source_composition']
                self.assertEqual(allocation['parent_program_id'],case['program_id'])
                self.assertEqual(allocation['composition_id'],record['definition']['composition_id'])
                self.assertEqual(recipe['reference_sources'],{})
                self.assertTrue(recipe['calendar_year_locked'],'Derived member targets use the exact declared reference year')
                self.assertEqual(recipe['variable_inputs']['composition_basis_mode'],['source_reference_area_normalized','caller_parent_floor_area'])
                self.assertTrue(all(resources.get('program',m['program_id'])['recipe']['resolved']['source']['template']==case['template'] for m in allocation['definition']['members']))
                continue
            carrier=resources.get('program',recipe['source_context']['carrier_program_id'])['definition']
            self.assertEqual((carrier['building_type'],carrier['template'],carrier['evidence_view']),('Warehouse',case['template'],case['evidence_view']))
            self.assertEqual(carrier['name'],'Office_Warehouse')
            original={d['demand_id']:d for d in record['definition']['loads']}
            for demand in recipe['resolved']['demands']:
                for field in ('value','unit','basis'):self.assertEqual(demand[field],original[demand['demand_id']][field])
        operating=sample_operating_parameters({'building_type':'warehouse'},42,resources)
        self.assertEqual(len(operating['draw_receipts']),10)
        self.assertTrue(all(d['selectors']['building_type']=='warehouse' for d in operating['draw_receipts']))

    def test_capture_inputs_use_actual_rooms_and_ordered_parent_members(self):
        from scripts.schedule_generator_reference import commercial_family_capture_inputs
        resources=self.family()
        inputs=commercial_family_capture_inputs(resources)
        self.assertEqual(len(inputs),250)
        self.assertEqual(len({c['case_id'] for c in inputs}),250)
        for item in inputs:
            pid=item.get('source_member_receipt',{}).get('program_id',item['source_case']['program_id'])
            actual=resources.get('program',pid)['recipe']['source_context']['slot_sources']
            self.assertEqual(item['schedules'],actual)
            self.assertEqual(item['source_context']['occupancy_aggregation'],resources.get('program',pid)['recipe']['source_context']['occupancy_aggregation'])
            self.assertEqual(item['operating']['conditioning_inputs'],{'building_type':'warehouse'})
        children=[c for c in inputs if 'source_member_receipt' in c]
        self.assertEqual(len(children),100)


    def test_parent_generation_indexes_real_children_and_conserves_targets(self):
        import math
        from unittest.mock import patch
        from atlas_schedules import generate
        from atlas_schedules.contract import validate_bundle
        resources=self.family()
        case=next(c for c in resources.manifest['cases'][79:] if resources.get('program',c['program_id'])['definition'].get('composition_id'))
        recipe=resources.get('program',case['program_id'])['recipe']
        inputs=dict(recipe['bound_inputs'],composition_basis_mode='source_reference_area_normalized')
        from atlas_schedules.programs import resolve_program
        from atlas_schedules.contract import _schema_errors
        _schema_errors(resolve_program(case['program_id'],dict(inputs,year=2007),resources),'program')
        params={'resource_set_id':resources.resource_set_id,'calendar':{'year':2007,'clock':'local_standard_time'},
            'instances':[{'key':'requested-parent','program_id':case['program_id'],'inputs':inputs,'basis_bindings':{},'operating_group':None}]}
        with patch.object(ResourceSet,'load',return_value=resources):bundle=generate(params,42)
        validate_bundle(bundle)
        self.assertEqual(len(bundle['constituents']),3)
        parent=bundle['constituents'][-1]
        self.assertEqual((parent['instance_key'],parent['program_id']),('requested-parent',case['program_id']))
        self.assertEqual(parent['source']['template'],case['template'])
        self.assertEqual(parent['generation']['method'],'conserved_source_composition')
        self.assertEqual({s['slot'] for s in recipe['resolved']['slots']},set(parent['schedule_ids']))
        declared={d['demand_id']:d['annual_target']['total'] for d in recipe['resolved']['demands']}
        self.assertEqual([c['program_id'] for c in bundle['constituents'][:2]],[m['program_id'] for m in recipe['source_composition']['definition']['members']])
        self.assertEqual(list(bundle['generation']['operating_groups']),['requested-parent'])
        for i in parent['binding_indices']:
            b=bundle['bindings'][i]
            if b['kind']!='load':continue
            parts=b['reference_target']['evidence']['components']
            expected=math.fsum(p['factor']*bundle['bindings'][p['binding_index']]['reference_target']['total'] for p in parts)
            self.assertEqual(b['reference_target']['total'],expected)
            self.assertTrue(math.isclose(b['reference_target']['total'],declared[b['demand_id']],rel_tol=1e-12,abs_tol=1e-8))

    def test_all_actual_native_room_and_parent_member_profiles(self):
        import gzip,math
        from atlas_schedules.commercial.parametric import transform_commercial
        path=ROOT/'data/schedule-generator/warehouse-family-native.json.gz'
        self.assertTrue(path.exists(),'Actual Warehouse room and parent-member native evidence missing')
        capture=json.loads(gzip.decompress(path.read_bytes()))
        self.assertEqual(len(capture['cases']),250)
        for case in capture['cases']:
            actual=transform_commercial(case['original_channels'],case['operating'],dict(case['source_context'],slot_sources=case['schedules']))
            self.assertEqual(set(actual['channels']),set(case['channels']))
            for slot,want in case['channels'].items():
                tolerance=1e-4 if 'setpoint' in slot else 1e-6 if slot=='activity' else 1e-8
                self.assertEqual(len(want),8760)
                for hour,(x,y) in enumerate(zip(actual['channels'][slot],want)):
                    self.assertAlmostEqual(x,y,delta=tolerance,msg=(case['case_id'],slot,hour,x,y))
                for day,profile in enumerate(actual['source_context']['transforms'][slot]['daily_profiles'],1):
                    key=next(k for k,days in case['final'][slot]['days_used'].items() if day in days)
                    native=case['final'][slot]['profiles']['default' if key=='-1' else key]
                    self.assertEqual([round(t*60) for t,v in profile],[round(t*60) for t,v in native])
                    for (_,x),(_,y) in zip(profile,native):self.assertTrue(math.isclose(x,y,rel_tol=1e-6,abs_tol=1e-8),(case['case_id'],slot,day,x,y))
            self.assertEqual(actual['source_context']['special_profiles'],case['special_profiles'])
            for slot,profiles in actual['source_context'].get('special_profile_alias_receipts',{}).items():
                for special,receipt in profiles.items():
                    self.assertFalse(any(special in r['day_types'].split('|') for r in case['schedules'][slot]['rules']))
                    self.assertIsNone(receipt['original_special_rule'])
                    self.assertEqual(receipt['original_special_state'],'not_explicitly_set')
                    self.assertEqual(receipt['selected_source_rule']['values'],next(r['values'] for r in case['schedules'][slot]['rules'] if r==receipt['selected_source_rule']))
                    self.assertEqual(actual['source_context']['special_profiles'][slot][special],case['final'][slot]['profiles']['default'])
                    self.assertTrue(receipt['tie_policy'] and receipt['transformation_stage'])
            self.assertEqual(actual['source_context']['inference']['daily_hoo'],[next(v for v in case['inference']['hoo'].values() if day in v['days_used']) for day in range(1,366)])

    def test_actual_source_discrete_warehouse_rows(self):
        import gzip,zipfile
        from scripts.schedule_generator_sources import compile_member
        from atlas_schedules.commercial.sampling import select_conditional
        capture=json.loads(gzip.decompress((ROOT/'data/schedule-generator/warehouse-family-native.json.gz').read_bytes()))
        lock=json.loads((ROOT/'sources/schedule-generator-warehouse-lock.json').read_text())
        source=next(a for a in lock['archives'] if a['source_id']=='comstock' and a['format']=='zip')
        with zipfile.ZipFile(ROOT/'data/raw'/source['cache_path']) as archive:
            tables={e['key']:compile_member(archive.read(e['path']),e,source) for e in source['members'] if e['key'].startswith('warehouse__')}
        for row in capture['conditional_vectors']:
            self.assertEqual(row['selectors']['building_type'],'warehouse')
            selected=select_conditional(tables['warehouse__'+row['parameter']],row['selectors'],row['uniform'])
            self.assertEqual((selected['source_row'],selected['original_option']),(row['source_row'],row['selected_option']))

    def test_join_closes_actual_ordered_source_parent_members(self):
        import copy
        from atlas_schedules.resources import write_resources
        from scripts.schedule_generator_release import validate_native_join
        path=ROOT/'data/schedule-generator/warehouse-cumulative-native.json'
        self.assertTrue(path.exists(),'C4 cumulative source-member join missing')
        scope=json.loads((ROOT/'sources/schedule-generator-warehouse-scope.json').read_text())
        join=json.loads(path.read_text())
        records={('reference','family-native-join'):join}
        for component in join['components']:records['reference',component['reference_resource_key']]=component['lock']
        definitions={p['id']:p for p in json.loads((ROOT/'data/definition-releases/v0.1.1/programs.json').read_text())}
        compositions={c['id']:c for c in json.loads((ROOT/'data/definition-releases/v0.1.1/compositions.json').read_text())}
        for case in scope['cases']:
            definition=definitions[case['program_id']]
            if case['building_type']=='Warehouse':records['program',case['program_id']]={'recipe':{}}
            if not definition.get('composition_id'):continue
            composition=compositions[definition['composition_id']]
            records['program',case['program_id']]={'recipe':{'source_composition':{'composition_id':composition['id'],'definition':composition}}}
        with tempfile.TemporaryDirectory() as directory:
            def resources(values):
                root=Path(directory)/str(len(list(Path(directory).iterdir())))
                manifest=write_resources(root,values,{})
                return ResourceSet(root,manifest['resource_set_id'])
            validate_native_join(resources(records),scope)
            self.assertEqual(sum('native_members' in b for b in join['fixture_bindings']),10)
            for mutation in ('missing','mispointed','duplicate','foreign_member','member_order'):
                bad=copy.deepcopy(records)
                parent=next(b for b in bad['reference','family-native-join']['fixture_bindings'] if 'native_members' in b)
                if mutation=='missing':bad.pop(('reference','warehouse-native-lock'))
                if mutation=='mispointed':parent['native_members'][0]['reference_resource_key']='commercial-native-lock'
                if mutation=='duplicate':bad['reference','family-native-join']['components'].append(copy.deepcopy(join['components'][-1]))
                if mutation=='foreign_member':parent['native_members'][0]['program_id']='foreign'
                if mutation=='member_order':parent['native_members'].reverse()
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate_native_join(resources(bad),scope)

    def test_complete_request_and_actual_four_family_source_parent_mix(self):
        import math
        from unittest.mock import patch
        from atlas_schedules import generate
        from atlas_schedules.contract import validate_bundle
        from atlas_schedules.canonical import canonical
        from scripts.schedule_generator_release import _request,_mixed_request
        resources=self.family();scope=resources.get('reference','m1-scope')
        files={f"atlas_schedules/data/program/{c['program_id']}.json":canonical(resources.get('program',c['program_id'])) for c in scope['cases']}
        request=_request(scope,files,resources.resource_set_id)
        self.assertEqual(len(request['params']['instances']),119)
        parents=[i for i in request['params']['instances'] if 'composition_basis_mode' in i['inputs']]
        self.assertEqual(len(parents),10)
        self.assertTrue(all(i['inputs']['composition_basis_mode']=='source_reference_area_normalized' for i in parents))
        mixed_request=_mixed_request(scope,resources)
        self.assertEqual(len(mixed_request['params']['instances']),4)
        parent=next(i for i in mixed_request['params']['instances'] if 'composition_basis_mode' in i['inputs'])
        self.assertEqual(parent['inputs']['composition_basis_mode'],'caller_parent_floor_area')
        with patch.object(ResourceSet,'load',return_value=resources):bundle=generate(mixed_request['params'],mixed_request['seed'])
        validate_bundle(bundle)
        self.assertEqual(len(bundle['constituents']),7)
        self.assertEqual(len(bundle['generation']['source_compositions']),1)
        result=bundle['constituents'][-1]
        self.assertEqual(len(result['generation']['people_pairs']),3)
        for index in result['binding_indices']:
            binding=bundle['bindings'][index]
            if binding['kind']!='load':continue
            parts=binding['reference_target']['evidence']['components']
            for h in range(8760):
                want=math.fsum(p['factor']*bundle['bindings'][p['binding_index']]['effective_magnitude']['value']*bundle['schedules'][p['schedule_id']]['values'][h] for p in parts)
                actual=binding['effective_magnitude']['value']*bundle['schedules'][binding['schedule_id']]['values'][h]
                self.assertTrue(math.isclose(actual,want,rel_tol=1e-12,abs_tol=1e-12))

    def test_all_40_records_two_seeds_and_constituent_first_targets(self):
        import copy,math
        from unittest.mock import patch
        from atlas_schedules import generate
        from atlas_schedules.contract import validate_bundle
        resources=self.family()
        for case in resources.manifest['cases'][79:]:
            recipe=resources.get('program',case['program_id'])['recipe']
            inputs=copy.deepcopy(recipe['bound_inputs'])
            if 'source_composition' in recipe:inputs['composition_basis_mode']='source_reference_area_normalized'
            params={'resource_set_id':resources.resource_set_id,'calendar':{'year':2007,'clock':'local_standard_time'},
                'instances':[{'key':case['case_id'],'program_id':case['program_id'],'inputs':inputs,'basis_bindings':{},'operating_group':None}]}
            with self.subTest(program=case['program_id']),patch.object(ResourceSet,'load',return_value=resources):
                a,b=[generate(params,seed) for seed in (42,51)]
                for bundle in (a,b):
                    validate_bundle(bundle)
                    for binding in bundle['bindings']:
                        if binding['kind']!='load':continue
                        achieved=math.fsum(bundle['schedules'][binding['schedule_id']]['values'])*binding['effective_magnitude']['value']
                        self.assertTrue(math.isclose(achieved,binding['reference_target']['total'],rel_tol=1e-8,abs_tol=1e-8))
                    if 'source_composition' in recipe:
                        parent=bundle['constituents'][-1]
                        self.assertEqual(parent['program_id'],case['program_id'])
                        self.assertEqual(bundle['generation']['request_instance_order'],[case['case_id']])
                        self.assertEqual(bundle['generation']['physical_member_generation_order'],parent['generation']['member_instance_keys'])
                        for index in parent['binding_indices']:
                            binding=bundle['bindings'][index]
                            if binding['kind']!='load':continue
                            parts=binding['reference_target']['evidence']['components']
                            total=math.fsum(p['factor']*bundle['bindings'][p['binding_index']]['reference_target']['total'] for p in parts)
                            self.assertEqual(total,binding['reference_target']['total'])
                self.assertEqual([v['reference_target'] for v in a['bindings'] if v['kind']=='load'],[v['reference_target'] for v in b['bindings'] if v['kind']=='load'])
                owners={c['instance_key']:c for c in b['constituents']}
                varied=False
                for c in a['constituents']:
                    for slot,sid in c['schedule_ids'].items():
                        values=a['schedules'][sid]['values'];other=b['schedules'][owners[c['instance_key']]['schedule_ids'][slot]]['values']
                        if slot=='activity':self.assertEqual(values,other)
                        if values!=other:varied=True
                    occupancy=next((x for x in c['controls'] if x['quantity']=='occupancy_fraction'),None)
                    if occupancy is not None:
                        self.assertEqual(occupancy['evidence']['nominal_density']['value'],.021097264416751055)
                self.assertTrue(varied,'Actual Warehouse temporal variation missing: '+case['program_id'])

    def test_parent_inventory_and_declared_composition_denominator(self):
        from scripts.schedule_generator_coverage import build_catalogue_inventory,build_coverage
        resources=self.family()
        coverage=build_coverage(resources)
        self.assertEqual(coverage['outside_scope']['composition_count'],368)
        self.assertEqual(coverage['scope']['composition_count'],10)
        inventory=build_catalogue_inventory(resources)
        parent_ids={c['program_id'] for c in resources.manifest['cases'] if 'source_composition' in resources.get('program',c['program_id'])['recipe']}
        for programme in inventory['programs']:
            if programme['id'] not in parent_ids:continue
            for channel in programme['channels']:
                if channel['source_state']=='known' and channel['slot']=='lighting':
                    self.assertEqual(channel['status'],'generated')
                    self.assertTrue(channel['runtime_slot'].startswith('load/lighting/'))
                    self.assertEqual(channel['resolved_source_evidence'][0]['method'],'sum_original_member_annual_targets_before_rng')
                    self.assertTrue(channel['resolved_source_evidence'][0]['original_parent_definition'])

    def test_native_source_associations_match_packaged_recipes(self):
        import copy,gzip
        from scripts.schedule_generator_release import validate_native_case_sources
        resources=self.family();scope=resources.get('reference','m1-scope')
        join=resources.get('reference','family-native-join')
        capture=json.loads(gzip.decompress((ROOT/'data/schedule-generator/warehouse-family-native.json.gz').read_bytes()))
        validate_native_case_sources(resources,scope,join,{'warehouse-native-lock':capture})
        selected=next(b for b in join['fixture_bindings'] if 'native_members' in b)['native_members'][0]['native_case_id']
        for mutation in ('profile','carrier','configuration','missing_public_draw'):
            bad=dict(capture,cases=list(capture['cases']))
            i=next(i for i,c in enumerate(bad['cases']) if c['case_id']==selected)
            case=copy.deepcopy(bad['cases'][i]);bad['cases'][i]=case
            if mutation=='profile':next(iter(case['schedules'].values()))['rules'][0]['values'][0]+=.01
            if mutation=='carrier':case['source_context']['occupancy_aggregation']['constituents'][0]['nominal_people']=2
            if mutation=='configuration':case['source_context']['configuration_id']='foreign'
            if mutation=='missing_public_draw':bad['cases']=[c for c in bad['cases'] if c['case_id']!=selected+'@full_request-51']
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                validate_native_case_sources(resources,scope,join,{'warehouse-native-lock':bad})

    def test_historical_certification_rejects_changed_current_implementation(self):
        from scripts.schedule_generator_release import validate_family_certification
        resources=self.family();scope=resources.get('reference','m1-scope')
        certificate=resources.get('reference','family-certification')
        self.assertTrue('implementation_source_sha256' in certificate,'Current implementation source qualification missing')
        self.assertIn('scripts/schedule_generator_release.py',certificate['implementation_source_sha256'])
        self.assertTrue(any('warehouse-native-association-green' in r['log'] for r in certificate['validation_receipts']))
        # C4's immutable certificate still closes its source/association proof,
        # but its implementation receipt cannot certify subsequent C5 code.
        with self.assertRaisesRegex(ValueError,'^Family certificate implementation/checker source differs from tested code$'):
            validate_family_certification(resources,scope)

    def test_source_parent_policy_export_enumerates_all_operands_and_slots(self):
        self.family()
        table=json.loads((Path(self.directory.name)/'tables/programs.json').read_text())
        parents=[p for p in table['programs'] if 'source_composition' in p]
        self.assertEqual(len(parents),10)
        for policy in parents:
            self.assertTrue(policy.get('slots'),'Derived source parent export must retain actual declared slots')
            self.assertIn('composition_basis_mode',policy['required_inputs'])
            self.assertEqual(policy['aggregate_binding_policy'],'actual_original_member_targets_before_rng')


if __name__=='__main__':unittest.main()
