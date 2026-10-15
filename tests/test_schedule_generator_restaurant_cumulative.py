"""Cumulative source-backed integration, distinct from independent ZIP gates."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from atlas_schedules.resources import ResourceSet
from scripts.common import ROOT


class RestaurantCumulativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory()
        root=Path(cls.temporary.name)
        with zipfile.ZipFile(ROOT/'data/generator-releases/v0.5.1/generator.zip') as archive:
            for name in archive.namelist():
                if name.startswith('atlas_schedules/data/'):
                    target=root/name.removeprefix('atlas_schedules/data/')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(archive.read(name))
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        cls.prior=ResourceSet(root,manifest['resource_set_id'])
        from scripts.schedule_generator_restaurants import compile_cumulative_records
        cls.records=compile_cumulative_records(cls.prior)
        from scripts.schedule_generator_restaurant_certification import build_native_join
        build_native_join(cls.records)

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def cumulative_resources(self):
        if not hasattr(self.__class__,'resources'):
            from atlas_schedules.resources import write_resources
            root=Path(self.temporary.name)/'expanded'
            manifest=write_resources(root,self.records,{'scope':'restaurant-cumulative-integration-test'})
            self.__class__.resources=ResourceSet(root,manifest['resource_set_id'])
        return self.resources

    def source_gate_positive_coverage_fixture(self):
        """Rehashed positive gate fixture, never actual candidate certification."""
        if not hasattr(self.__class__,'positive_coverage_resources'):
            from atlas_schedules.resources import write_resources
            records=copy.deepcopy(self.records);scope=records['reference','m1-scope']
            for case in scope['cases']:
                case['source_gate_status']='passed'
                records['program',case['program_id']]['case']=copy.deepcopy(case)
            for case in scope['service_cases']:case['source_gate_status']='passed'
            root=Path(self.temporary.name)/'synthetic-source-gate-positive-coverage-fixture'
            manifest=write_resources(root,records,{'scope':'synthetic-source-gate-positive-coverage-fixture-not-certificate'})
            self.__class__.positive_coverage_resources=ResourceSet(root,manifest['resource_set_id'])
        return self.positive_coverage_resources

    def test_cumulative_scope_preserves_prior_recipes_and_appends_exact_owner_cases(self):
        records=self.records
        previous=self.prior.get('reference','m1-scope')
        scope=records['reference','m1-scope']
        self.assertEqual(scope['cases'][:119],previous['cases'])
        self.assertEqual(len(scope['cases']),165)
        self.assertEqual(len(scope['service_cases']),26)
        self.assertEqual(len({(c['source_service_id'],c['source_hoo_configuration_id']) for c in scope['service_cases']}),26)
        for case in previous['cases']:
            self.assertEqual(records['program',case['program_id']],self.prior.get('program',case['program_id']))
        compiled={r['id'] for r in records['reference','catalogue-index']['programs'] if r['status'] in {'compiled','accepted_inactive'}}
        self.assertEqual(compiled,{c['program_id'] for c in scope['cases']})
        self.assertNotIn(('reference','family-certification'),records,'A prior certificate must not certify expanded runtime/scope')
        native=records['reference','restaurant-water-fixed-native-operands']
        for (kind,key),record in records.items():
            if not key.startswith('physical-service__'):continue
            for variant in record['recipe']['configurations'].values():
                for method in variant['companion_rules'].values():
                    receipt=method['evidence']['native_control_reference'];value=native
                    for part in receipt['json_pointer'].strip('/').split('/'):
                        value=value[int(part)] if isinstance(value,list) else value[part]
                    self.assertEqual(value['profiles']['default'],method['native_source_profile'])

    def test_actual_cumulative_mixture_keeps_programme_weights_and_whole_services(self):
        from atlas_schedules import generate
        from scripts.schedule_generator_release import _mixed_request
        from scripts.schedule_generator_restaurants import qualification_request
        records=self.records
        resources=self.cumulative_resources()
        params=_mixed_request(self.prior.get('reference','m1-scope'),self.prior)['params']
        params.update(schema_version='1.1.0',resource_set_id=resources.resource_set_id)
        for instance in params['instances']:instance['owner_kind']='program'
        request=qualification_request(records)
        # qualification_request enumerates its programme scope, so select real
        # new restaurant owners after filtering the exact scoped cases below.
        selected={}
        for case in records['reference','m1-scope']['cases'][119:]:
            if case['template']!='90.1-2013':continue
            if case['program_id']=='program-76fabb7b85c683f4f7d8c873':selected['full']=case
            if case['building_type']=='QuickServiceRestaurant' and case['evidence_view']=='reviewed' and 'Dining' in case['name']:
                selected['quick']=case
        self.assertEqual(set(selected),{'full','quick'})
        area={'value':100,'unit':'m2','evidence':{'caller':'Explicit experiment area, separate from source HOO geometry'}}
        services=[]
        for label,case in selected.items():
            instance=next(i for i in request['instances'] if i.get('program_id')==case['program_id'])
            instance['basis_bindings']={'extents':{'floor_area':copy.deepcopy(area)},'multiplicity':1}
            params['instances'].append(instance)
            fixture_instances=[i for i in request['instances'] if i.get('owner_kind')=='physical_service' and i['operating_group']==case['configuration_id']]
            services.extend(fixture_instances)
        self.assertEqual(len(services),3)
        params['instances'].extend(services)
        weights=[.1,.15,.2,.1,.25,.2]
        params['mixture'].update(program_id='actual-cumulative-restaurants-and-whole-fixtures',
            members=[{'instance_key':i['key'],'weight':w} for i,w in zip(params['instances'][:6],weights)],
            service_members=[{'instance_key':i['key']} for i in services])
        with patch('atlas_schedules.generator.ResourceSet.load',return_value=resources):bundle=generate(params,42)
        result=bundle['constituents'][-1];owners={c['instance_key']:c for c in bundle['constituents']}
        receipt=result['generation']['service_selection']
        self.assertEqual(result['generation']['members'],params['mixture']['members'])
        self.assertEqual(receipt['effective_service_members'],params['mixture']['service_members'])
        self.assertEqual(len(result['shared_services']),3)
        self.assertEqual(len({s['physical_id'] for s in result['shared_services']}),3)
        denominator=params['mixture']['denominator']['value'];expected={};hourly={}
        for instance,weight in [(i,w) for i,w in zip(params['instances'][:6],weights)]+[(i,1) for i in services]:
            owner=owners[instance['key']]
            for index in owner['binding_indices']:
                binding=bundle['bindings'][index]
                if binding['kind']!='load':continue
                demand=next(d for d in owner['demands'] if d['demand_id']==binding['demand_id'])
                extent=owner['basis_bindings']['extents'][demand['basis']]['value']
                factor=extent/denominator*(1 if owner['owner_kind']=='physical_service' else weight)
                carrier='m3/s' if demand['quantity']=='hot_water_volume' else 'W'
                group=(demand['quantity'],carrier,demand['fuel'],demand['host'])
                expected.setdefault(group,[]).append(factor*binding['reference_target']['total'])
                hourly.setdefault(group,[]).append(factor*binding['effective_magnitude']['value']*bundle['schedules'][binding['schedule_id']]['values'][137])
        self.assertEqual(len(result['demands']),len(expected))
        for index in result['binding_indices']:
            binding=bundle['bindings'][index]
            if binding['kind']!='load':continue
            demand=next(d for d in result['demands'] if d['demand_id']==binding['demand_id'])
            group=(demand['quantity'],'m3/s' if demand['quantity']=='hot_water_volume' else 'W',demand['fuel'],demand['host'])
            self.assertTrue(math.isclose(binding['reference_target']['total'],math.fsum(expected[group]),rel_tol=1e-12,abs_tol=1e-12))
            actual=binding['effective_magnitude']['value']*bundle['schedules'][binding['schedule_id']]['values'][137]
            self.assertTrue(math.isclose(actual,math.fsum(hourly[group]),rel_tol=1e-8,abs_tol=1e-12))

    def test_coverage_separates_required_programme_links_and_physical_case_denominators(self):
        from scripts.schedule_generator_coverage import build_coverage
        resources=self.cumulative_resources();report=build_coverage(resources)
        self.assertEqual(report['scope']['case_count'],165)
        self.assertEqual(report['scope']['service_case_count'],26)
        self.assertEqual(len(report['service_cases']),26)
        self.assertEqual(sum(len(c['channels']) for c in report['service_cases']),104)
        links=[link for c in report['cases'] for link in c.get('required_service_links',[])]
        self.assertEqual(len(links),10)
        self.assertTrue(all(l['source_channel']=='hot_water_volume' for l in links))
        self.assertTrue(all(l['ownership']=='external_physical_service' for l in links))
        self.assertTrue(all(l['caller_binding_required'] and not l['fully_bound_example_proven'] for l in links))
        for link in links:
            self.assertEqual(len(link['allowed_service_case_ids']),1)
            proof=link['source_evidence']
            self.assertEqual(proof['resource_kind'],'program')
            self.assertIn('/recipe/required_service_links/',proof['pointer'])
        self.assertEqual(sum(len(c['expected_slots']) for c in report['cases']),1266)
        self.assertEqual(sum(len(c['expected_slots']) for c in report['service_cases']),104)
        self.assertEqual(report['scope']['declared_owned_slot_count'],1370)

    def test_coverage_rejects_missing_mispointed_duplicate_service_or_alias_evidence(self):
        from scripts.schedule_generator_coverage import build_coverage,coverage_errors
        resources=self.source_gate_positive_coverage_fixture();original=build_coverage(resources)
        self.assertEqual(coverage_errors(original,resources),[])
        for mutation in ('missing','mispointed','duplicate','alias','native_pointer','evidence_inventory','definition_count','all_service_fields'):
            report=copy.deepcopy(original)
            if mutation=='missing':report['service_cases'].pop()
            elif mutation=='mispointed':report['service_cases'][0]['source_service_id']=next(c['source_service_id'] for c in report['service_cases'] if c['source_service_id']!=report['service_cases'][0]['source_service_id'])
            elif mutation=='duplicate':report['service_cases'][1]=copy.deepcopy(report['service_cases'][0])
            elif mutation=='alias':next(c for c in report['cases'] if c.get('required_service_links'))['required_service_links'][0]['allowed_service_case_ids']=[]
            elif mutation=='native_pointer':report['service_cases'][0]['channels'][1]['native_evidence']['pointer']='/cases/999999'
            elif mutation=='definition_count':report['scope']['source_service_definition_count']=26
            elif mutation=='all_service_fields':
                report.pop('service_cases')
                for key in ('service_case_count','service_case_ids','source_service_definition_count',
                            'declared_owned_slot_count','required_programme_service_link_count'):report['scope'].pop(key)
            else:report['evidence_inventory'].pop()
            self.assertNotEqual(report,original)
            errors=coverage_errors(report,resources)
            with self.subTest(mutation=mutation):
                self.assertTrue(any('denominator' in e or 'does not close' in e or 'evidence inventory differs' in e for e in errors),errors)

    def test_catalogue_inventory_retains_active_water_as_required_typed_link(self):
        from scripts.schedule_generator_coverage import build_catalogue_inventory
        inventory=build_catalogue_inventory(self.cumulative_resources())
        programmes={p['id']:p for p in inventory['programs']}
        count=0
        for declaration in self.records['reference','m1-scope']['cases'][119:]:
            programme=programmes[declaration['program_id']]
            for channel in programme['channels']:
                if channel['slot']!='hot_water_volume' or channel['source_state'] not in {'known','shared'}:continue
                count+=1
                self.assertEqual(channel['status'],'generated')
                self.assertIsNone(channel['runtime_slot'])
                link=channel['resolved_service_link_evidence']
                self.assertEqual(link['ownership'],'external_physical_service')
                self.assertTrue(link['caller_binding_required'])
                self.assertFalse(link['fully_bound_example_proven'])
                self.assertEqual(len(link['allowed_service_case_ids']),1)
        self.assertEqual(count,20,'Ten actual source aliases appear in loads and services, without twenty physical owners')
        self.assertFalse(inventory['full_extraction_complete'])

    def test_native_association_joins_actual_programme_and_typed_service_sources(self):
        from scripts.schedule_generator_restaurant_certification import build_native_join,validate_native_associations
        records=self.records;join=build_native_join(records);resources=self.cumulative_resources()
        self.assertEqual(len(join['components']),7)
        self.assertEqual(len(join['fixture_bindings']),165)
        self.assertEqual(len(join['service_bindings']),26)
        report=validate_native_associations(resources,join)
        self.assertEqual(report['programme_native_cases'],230)
        self.assertEqual(report['public_water_native_cases'],40)
        self.assertEqual(report['private_water_fixture_observations'],52)
        for mutation in ('missing','mispointed','duplicate','foreign_people','fixed_operand'):
            changed=copy.deepcopy(join);overrides={}
            if mutation=='missing':changed['components'].pop()
            elif mutation=='mispointed':changed['service_bindings'][0]['public_native_fixtures'][0]['pointer']='/cases/999999'
            elif mutation=='duplicate':changed['fixture_bindings'][-1]=copy.deepcopy(changed['fixture_bindings'][-2])
            elif mutation=='foreign_people':
                case=records['reference','m1-scope']['cases'][119]
                record=copy.deepcopy(records['program',case['program_id']])
                record['recipe']['source_context']['occupancy_aggregation']['constituents'][0]['nominal_people']+=1
                overrides['program',case['program_id']]=record
            else:
                key='restaurant-water-fixed-native-operands';record=copy.deepcopy(records['reference',key])
                record['cases'][0]['fixtures'][0]['controls']['target_temperature']['profiles']['default'][0][1]+=1
                overrides['reference',key]=record
            class ChangedResources:
                def get(self,kind,key):return copy.deepcopy(overrides[kind,key]) if (kind,key) in overrides else resources.get(kind,key)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                validate_native_associations(ChangedResources(),changed)

    def test_actual_230_native_programme_arrays_and_profiles_match_current_packaged_operands(self):
        from scripts.schedule_generator_restaurant_certification import compare_native_programmes
        report=compare_native_programmes(self.cumulative_resources())
        self.assertEqual(report['status'],'passed')
        self.assertEqual(report['tested_cases'],230)
        self.assertEqual(report['hourly_values_compared'],8322000)
        self.assertEqual(report['daily_special_profiles_compared'],348650)
        self.assertEqual(report['differences'],[])

    def test_release_join_and_complete_example_use_explicit_typed_service_namespace(self):
        from atlas_schedules.canonical import canonical
        from atlas_schedules.contract import validate_request
        from scripts.schedule_generator_release import validate_native_join,_request,_mixed_request
        resources=self.cumulative_resources();scope=copy.deepcopy(self.records['reference','m1-scope'])
        scope['milestone_id']='C5'
        validate_native_join(resources,scope)
        files={'atlas_schedules/data/reference/m1-scope.json':canonical(scope)}
        for (kind,key),record in self.records.items():
            if kind=='program' or key.startswith('physical-service__'):
                files['atlas_schedules/data/'+kind+'/'+key+'.json']=canonical(record)
        request=_request(scope,files,resources.resource_set_id)
        self.assertEqual(request['schema_version'],'1.1.0')
        self.assertEqual(request['params']['schema_version'],'1.1.0')
        self.assertEqual(len(request['params']['instances']),191)
        self.assertEqual([i['key'] for i in request['params']['instances']],
            [c['case_id'] for c in scope['cases']]+[c['case_id'] for c in scope['service_cases']])
        self.assertEqual(sum(i['owner_kind']=='physical_service' for i in request['params']['instances']),26)
        validate_request(request['params'],request['seed'])
        mixed=_mixed_request(scope,resources)
        self.assertEqual(mixed['schema_version'],'1.1.0')
        self.assertEqual(len(mixed['params']['mixture']['members']),6)
        self.assertEqual(len(mixed['params']['mixture']['service_members']),3)
        validate_request(mixed['params'],mixed['seed'])

    def test_c5_certificate_cannot_reuse_programme_only_denominator(self):
        import hashlib
        from atlas_schedules.canonical import canonical
        from scripts.schedule_generator_release import (validate_family_certification,certification_dependency_hash,
            implementation_sources,implementation_source_hash)
        resources=self.cumulative_resources();scope=copy.deepcopy(self.records['reference','m1-scope'])
        scope['milestone_id']='C5'
        native={'vectors':{'explicit':'contract-only fixture, not an actual certificate'},
            'fixture_order':[c['configuration_id'] for c in scope['cases']]}
        certificate={'status':'passed','case_ids':[c['case_id'] for c in scope['cases']],
            'scope_sha256':hashlib.sha256(canonical(scope)).hexdigest(),
            'dependency_sha256':certification_dependency_hash(resources.manifest),
            'native_source_discrete_numerical_passed':True,'annual_target_invariance_passed':True,
            'temporal_variation_and_fixed_channels_passed':True,'master_seeds':[42,51],
            'native_reference':native['vectors']}
        class Fixture:
            manifest=resources.manifest
            def get(self,kind,key):
                if key=='family-certification':return copy.deepcopy(certificate)
                if key=='family-native-lock':return copy.deepcopy(native)
                return resources.get(kind,key)
        with self.assertRaisesRegex(ValueError,'service|owned|denominator'):
            validate_family_certification(Fixture(),scope)
        # A positive checker-contract fixture closes actual source associations;
        # these explicit synthetic flags do not constitute a shipping certificate.
        join=resources.get('reference','family-native-join');blob=canonical(join)
        native['vectors']={'source_path':'data/schedule-generator/restaurant-cumulative-native.json',
            'sha256':hashlib.sha256(blob).hexdigest(),'size_bytes':len(blob)}
        certificate.update(native_reference=native['vectors'],
            service_case_ids=[c['case_id'] for c in scope['service_cases']],
            declared_owned_slot_count=1370,required_service_link_count=10,source_service_definition_count=13,
            family_qualifications={family:{
                'programme_case_ids':[c['case_id'] for c in scope['cases'] if c['building_type']==family],
                'service_case_ids':[c['case_id'] for c in scope['service_cases'] if c['building_type']==family],
                'master_seeds':[42,51],'native_source_discrete_numerical_passed':True,'bound_public_examples_passed':True}
                for family in ('FullServiceRestaurant','QuickServiceRestaurant')},
            implementation_source_sha256={name:implementation_source_hash((ROOT/name).read_bytes())
                for name in implementation_sources('C5')})
        validate_family_certification(Fixture(),scope)
        for name in ('atlas_schedules/mixtures.py','scripts/schedule_generator_restaurant_certification.py'):
            with self.subTest(changed_implementation=name):
                original=certificate['implementation_source_sha256'][name]
                certificate['implementation_source_sha256'][name]='0'*64
                with self.assertRaisesRegex(ValueError,'^Family certificate implementation/checker source differs from tested code$'):
                    validate_family_certification(Fixture(),scope)
                certificate['implementation_source_sha256'][name]=original

    def test_restricted_c5_scope_retains_exact_service_links_and_typed_example(self):
        from atlas_schedules.canonical import canonical
        from scripts.schedule_generator_coverage import build_coverage,coverage_errors
        from scripts.schedule_generator_release import _request
        resources=self.source_gate_positive_coverage_fixture()
        scope=resources.get('reference','m1-scope');scope['milestone_id']='C5-source-2013-kitchen'
        scope['cases']=[c for c in scope['cases'] if c['program_id']=='program-76fabb7b85c683f4f7d8c873']
        recipe=resources.get('program',scope['cases'][0]['program_id'])['recipe']
        sid=recipe['required_service_links'][0]['source_service_id'];config=scope['cases'][0]['configuration_id']
        scope['service_cases']=[c for c in scope['service_cases'] if c['source_service_id']==sid and c['source_hoo_configuration_id']==config]
        report=build_coverage(resources,scope)
        self.assertEqual(len(report['cases']),1);self.assertEqual(len(report['service_cases']),1)
        self.assertEqual(coverage_errors(report,resources),[])
        files={'atlas_schedules/data/program/'+scope['cases'][0]['program_id']+'.json':canonical(resources.get('program',scope['cases'][0]['program_id']))}
        case=scope['service_cases'][0];files['atlas_schedules/data/reference/'+case['resource_key']+'.json']=canonical(resources.get('reference',case['resource_key']))
        request=_request(scope,files,'resources-explicit-partial-identity')
        self.assertEqual(request['schema_version'],'1.1.0')
        self.assertEqual(len(request['params']['instances']),2)
        self.assertEqual(request['params']['instances'][0]['service_links'][sid],request['params']['instances'][1]['key'])
        absent=copy.deepcopy(scope);absent['service_cases']=[]
        self.assertTrue(coverage_errors(build_coverage(resources,absent),resources),'A restricted Kitchen cannot discard its active water alias')
        predecessor=resources.get('reference','m1-scope');predecessor['cases']=predecessor['cases'][:1]
        predecessor['service_cases']=[];predecessor['milestone_id']='C5-predecessor-only'
        prior_report=build_coverage(resources,predecessor)
        self.assertEqual(prior_report['service_cases'],[])
        self.assertEqual(prior_report['scope']['service_case_count'],0)
        self.assertEqual(coverage_errors(prior_report,resources),[])

    def test_c5_actual_packaged_native_components_and_projection_close(self):
        import gzip
        from scripts.schedule_generator_release import native_component_files,validate_packaged_native_components
        resources=self.cumulative_resources();files=native_component_files(resources)
        join=resources.get('reference','family-native-join')
        self.assertEqual(len(join['components']),7)
        for component in join['components']:
            self.assertIn(component['lock']['vectors']['source_path'],files)
        validate_packaged_native_components(resources,files)
        path=join['components'][-1]['lock']['vectors']['source_path']
        bad=dict(files);bad[path]=files[path]+b'altered'
        with self.assertRaisesRegex(ValueError,'hash|identity|checksum'):
            validate_packaged_native_components(resources,bad)
        missing=dict(files);missing.pop(path)
        with self.assertRaisesRegex(ValueError,'missing|Missing'):
            validate_packaged_native_components(resources,missing)
        mispointed=copy.deepcopy(join);binding=mispointed['service_bindings'][0]
        reference=binding['private_native_fixtures'][0]
        component=next(c for c in join['components'] if c['reference_resource_key']==reference['reference_resource_key'])
        native=json.loads(gzip.decompress(files[component['lock']['vectors']['source_path']]))
        alternatives=[(i,j) for i,c in enumerate(native['cases']) for j,f in enumerate(c['fixtures'])
            if f['source_service_id']==binding['source_service_id'] and c['source_hoo_configuration_id']!=binding['source_hoo_configuration_id']]
        i,j=alternatives[0];reference['pointer']='/cases/'+str(i)+'/fixtures/'+str(j)
        self.assertNotEqual(reference['pointer'],join['service_bindings'][0]['private_native_fixtures'][0]['pointer'])
        class Mispointed:
            def get(self,kind,key):return mispointed if key=='family-native-join' else resources.get(kind,key)
        with self.assertRaisesRegex(ValueError,'pointer|configuration|case'):
            validate_packaged_native_components(Mispointed(),files)

    def test_actual_separate_restaurant_bundles_merge_group_disclosures_and_rebase_alias(self):
        from atlas_schedules import generate,compose_constituents
        from atlas_schedules.contract import validate_bundle
        from atlas_schedules.errors import GeneratorError
        from scripts.schedule_generator_restaurants import qualification_request
        resources=self.cumulative_resources();complete=qualification_request(self.records)
        kitchen=next(i for i in complete['instances'] if i.get('program_id')=='program-76fabb7b85c683f4f7d8c873')
        config=kitchen['operating_group']
        dining_case=next(c for c in self.records['reference','m1-scope']['cases'][119:] if c['building_type']=='FullServiceRestaurant'
            and c['template']=='90.1-2013' and c['evidence_view']=='source' and 'Dining' in c['name'])
        dining=next(i for i in complete['instances'] if i.get('program_id')==dining_case['program_id'])
        main=next(i for i in complete['instances'] if i['key'] in kitchen['service_links'].values())
        area={'value':100,'unit':'m2','evidence':{'caller':'Explicit programme area, independent of physical fixture extent'}}
        for i in (dining,kitchen):i['basis_bindings']={'extents':{'floor_area':copy.deepcopy(area)}}
        def generated(instances,seed):
            params={'schema_version':'1.1.0','resource_set_id':resources.resource_set_id,'calendar':complete['calendar'],
                'instances':copy.deepcopy(instances)}
            with patch('atlas_schedules.generator.ResourceSet.load',return_value=resources):return generate(params,seed)
        first=generated([dining],42);second=generated([kitchen,main],42)
        mixture={'program_id':'actual-precomputed-restaurant-service','composition_id':None,
            'members':[{'instance_key':dining['key'],'weight':.7},{'instance_key':kitchen['key'],'weight':.3}],
            'result_basis':'floor_area','denominator':{'value':200,'unit':'m2','evidence':{'caller':'Explicit result area'}}}
        actual=compose_constituents([first,second],mixture,complete['calendar']);validate_bundle(actual)
        owners={c['instance_key']:c for c in actual['constituents']};link=owners[kitchen['key']]['service_links'][0]
        local=second['constituents'][0]['service_links'][0]['binding_index']
        self.assertEqual(link['binding_index'],local+len(first['bindings']))
        self.assertIn(link['binding_index'],owners[main['key']]['binding_indices'])
        for source in (first,second):
            for sid,schedule in source['schedules'].items():self.assertEqual(actual['schedules'][sid],schedule)
        group=actual['generation']['operating_groups'][config]
        self.assertEqual([r['instance_key'] for r in group['original_owner_weather_records']],
            [dining['key'],kitchen['key'],main['key']])
        result=actual['constituents'][-1];target=next(b['reference_target']['total'] for b in actual['bindings']
            if b['instance_key']==result['instance_key'] and b['kind']=='load' and b['reference_target']['quantity']=='hot_water_volume')
        source=actual['bindings'][link['binding_index']]['reference_target']['total']
        extent=main['basis_bindings']['extents']['floor_area']['value']
        self.assertTrue(math.isclose(target,source*extent/200,rel_tol=1e-12))
        changed=generated([kitchen,main],51)
        with self.assertRaises(GeneratorError):compose_constituents([first,changed],mixture,complete['calendar'])
        mutations={
            'missing disclosure':lambda r:r.pop(),
            'foreign owner':lambda r:r[0].update(instance_key='foreign-generated-owner'),
            'duplicate owner':lambda r:r.__setitem__(1,copy.deepcopy(r[0])),
            'wrong original weather':lambda r:r[0].update(weather={'unconsumed_but_false':'weather'}),
            'malformed disclosure':lambda r:r.__setitem__(0,None),
        }
        for label,mutate in mutations.items():
            with self.subTest(disclosure=label):
                invalid=copy.deepcopy(second)
                mutate(invalid['generation']['operating_groups'][config]['original_owner_weather_records'])
                with self.assertRaisesRegex(GeneratorError,'weather|Weather|disclosure'):
                    compose_constituents([first,invalid],mixture,complete['calendar'])
        for field,value in [('source_hoo_configuration_id','foreign-config'),('year',2008)]:
            with self.subTest(consumed_context=field):
                invalid=copy.deepcopy(second)
                invalid['generation']['operating_groups'][config]['context'][field]=value
                with self.assertRaisesRegex(GeneratorError,'conflict|differs'):
                    compose_constituents([first,invalid],mixture,complete['calendar'])
        single=copy.deepcopy(mixture);single['members']=single['members'][:1];single['members'][0]['weight']=1
        single['denominator']['value']=100
        for mutation in ('foreign_config','foreign_policy','malformed_context'):
            with self.subTest(single_qualified_owner=mutation):
                invalid=copy.deepcopy(first);receipt=invalid['generation']['operating_groups'][config]
                if mutation=='foreign_config':receipt['context']['source_hoo_configuration_id']='foreign-config'
                elif mutation=='foreign_policy':receipt['context']['occupancy_aggregation']['policy']='foreign-policy'
                else:receipt['context']=None
                with self.assertRaisesRegex(GeneratorError,'conflict|context|configuration'):
                    compose_constituents([invalid],single,complete['calendar'])


if __name__=='__main__':unittest.main()
