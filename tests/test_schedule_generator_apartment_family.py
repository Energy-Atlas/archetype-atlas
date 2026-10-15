"""Actual public apartment authority and mandatory physical controls."""
import copy
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from atlas_schedules import generate
from atlas_schedules.contract import validate_bundle
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet,write_resources
from atlas_schedules.canonical import canonical
from tests import test_schedule_generator_caller_water_v1_2 as facts

ROOT=Path(__file__).resolve().parents[1]
PID='program-23458a6e125b4cee7f62bb42'
CALENDAR={'year':2007,'clock':'local_standard_time','holidays':[]}


class ApartmentFamily(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.schedule_generator_apartment_authority import build_apartment_resources
        root=ROOT/'build/task-10/apartment-a4/resources'
        if not (root/'manifest.json').is_file():build_apartment_resources(root)
        manifest=json.loads((root/'manifest.json').read_bytes())
        cls.resources=ResourceSet(root,manifest['resource_set_id'])

    def request(self,n=2,area=80,programmes=True,pid=PID):
        req=self.resources.get('reference','caller-water-requirement__'+pid)
        real=facts.realization([facts.unit('u','draw',[req],area=area)],req['family'],req['template'])
        instances=[i for i,r in facts.pairs(real,{pid:req},programmes)]
        for instance in instances:
            if instance['owner_kind']=='program':
                instance['inputs']={'apartment_method':'unit_occupancy_interior_lighting','N':n}
                if n>0:instance['inputs'].update(state='NC',latitude=35.741,longitude=-81.389,time_zone_utc_offset=-5)
        return {'schema_version':'1.2.0','resource_set_id':self.resources.resource_set_id,
                'calendar':copy.deepcopy(CALENDAR),'building_realizations':[real],'instances':instances}

    def generate(self,params,seed=42):
        with patch('atlas_schedules.generator.ResourceSet.load',return_value=self.resources):
            return generate(params,seed)

    def test_real_qualifications_only(self):
        bundle=self.generate(self.request(n=0))
        self.assertEqual(bundle['generation']['physical_unit_seed_sequence'][0]['stochastic_action'],'skip_n0')
        self.assertEqual(len(bundle['constituents'][0]['binding_indices']),4)
        validate_bundle(bundle)

    def test_caller_native_controls_emitted_exactly_once(self):
        bundle=self.generate(self.request(programmes=False))
        self.assertEqual(len(bundle['schedules']),4)
        self.assertEqual(len(bundle['bindings']),4)
        self.assertEqual(bundle['generation']['physical_unit_seed_sequence'],[])
        controls={b['slot']:bundle['schedules'][b['schedule_id']] for b in bundle['bindings'] if b['kind']=='control'}
        self.assertEqual(set(controls),{'water_target_temperature','water_sensible_fraction','water_latent_fraction'})
        self.assertEqual({k:set(v['values']) for k,v in controls.items()},
            {'water_target_temperature':{60.0},'water_sensible_fraction':{.2},'water_latent_fraction':{.05}})
        precision=bundle['constituents'][0]['generation']['companions']['companion_receipts']['water_target_temperature']['native_getter_precision']
        self.assertEqual(precision['original_canonical_value'],60.0)
        self.assertEqual(precision['source_operand']['value'],140)
        self.assertEqual(precision['actual_native_stored_value'],60.0000000000001)
        self.assertEqual(precision['actual_native_source_profile'],[[24.0,60.0000000000001]])
        self.assertEqual(precision['hourly_value'],60.0)
        self.assertFalse(precision['canonical_value_is_native_stored_value'])

    def test_unpatched_public_package_load(self):
        # No ResourceSet.load/private predicate patch in the actual copied package.
        # Keep native Windows paths below260characters for the long static-pool keys.
        with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='a4-public-') as directory:
            root=Path(directory);package=root/'atlas_schedules'
            shutil.copytree(ROOT/'atlas_schedules',package,ignore=shutil.ignore_patterns('data','__pycache__'))
            shutil.copytree(self.resources.root,package/'data')
            (root/'request.json').write_bytes(canonical({'schema_version':'1.2.0','params':self.request(n=0),'seed':42}))
            result=subprocess.run([sys.executable,'-m','atlas_schedules','--request',str(root/'request.json'),
                '--output',str(root/'bundle.json')],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            bundle=json.loads((root/'bundle.json').read_bytes())
            self.assertEqual(len(bundle['constituents'][0]['binding_indices']),4)
            (ROOT/'build/task-10/apartment-a4/unpatched-public-result.json').write_bytes(canonical({
                'command':result.args,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
                'resource_set_id':self.resources.resource_set_id,'bundle_sha256':hashlib.sha256(canonical(bundle)).hexdigest(),
                'binding_count':len(bundle['bindings']),'schedule_count':len(bundle['schedules'])}))

    def test_apartment_preflight_before_rng(self):
        variants=[{'N':True},{'N':2.0},{'N':-1},{'weather':'foreign'},{'source_context':{}},
                  {'seed':42},{'residents':2},{'fan':True},{'events':{}},{'HOO':{}},
                  {'latitude':35.742},{'longitude':-80},{'apartment_method':'source_fixed_apartment_programme'}]
        for mutation in variants:
            params=self.request();params['instances'][1]['inputs'].update(mutation)
            with (self.subTest(mutation=mutation),patch('atlas_schedules.generator.sample_operating_parameters',side_effect=AssertionError('COM RNG')),
                    patch('atlas_schedules.residential.activity.source_streams',side_effect=AssertionError('RES RNG'))):
                with self.assertRaises(GeneratorError):self.generate(params)
        for n in (0,2):
            params=self.request(n=n);params['instances'][1]['inputs'].pop('N')
            with self.assertRaises(GeneratorError):self.generate(params)
        params=self.request(n=0);params['instances'][1]['inputs']['state']='NC'
        with self.assertRaises(GeneratorError):self.generate(params)
        # Real valid commercial owners precede the invalid dwelling: COM is the earlier RNG seam.
        from tests.test_schedule_generator_v1_2_integration import PublicV12IntegrationTests
        helper=PublicV12IntegrationTests();helper.resources=self.resources
        kitchen,physical=helper.restaurant()
        for owner in physical:owner['physical_binding_kind']='legacy_whole'
        params=self.request();params['instances'][1]['inputs']['latitude']=35.742
        params['instances']=[kitchen,*physical,*params['instances']]
        with (patch('atlas_schedules.generator.sample_operating_parameters',side_effect=AssertionError('COM RNG')),
              patch('atlas_schedules.residential.activity.source_streams',side_effect=AssertionError('RES RNG'))):
            with self.assertRaises(GeneratorError):self.generate(params)

    def test_cold_pure_authority_and_coherent_source_rewrites(self):
        from atlas_schedules.apartment_authority import validate_apartment_authority
        from atlas_schedules.caller_unit_water import _caller_control_obligations,_native_control_source
        q=self.resources.get('reference','apartment-programme-qualification__'+PID)
        record=self.resources.get('program',PID)
        water=self.resources.get('reference','caller-water-qualification__'+PID)
        with (patch('atlas_schedules.contract._load_schema',side_effect=AssertionError('schema IO')),
                patch.object(Path,'read_bytes',side_effect=AssertionError('source IO')),
                patch.object(ResourceSet,'get',side_effect=AssertionError('resources'))):
            validate_apartment_authority(PID,record,q)
            _caller_control_obligations(water['value']['requirement'],water['value']['fixed_controls'])
            _native_control_source(water)
            changed=copy.deepcopy(q);p=changed['value']['original_sources']['value']['programme']['value']
            p['loads'][1]['value']*=2
            self.rehash(changed)
            rewritten=copy.deepcopy(record);rewritten['definition']=copy.deepcopy(p)
            with self.assertRaises(GeneratorError):validate_apartment_authority(PID,rewritten,changed)
        # Supplied receipts never establish production qualification.
        from atlas_schedules.programs import _resolve_program_record
        with self.assertRaises(GeneratorError):_resolve_program_record(PID,{'year':2007,'N':0},record,'compiled')

    @staticmethod
    def rehash(value):
        if isinstance(value,dict):
            for child in value.values():ApartmentFamily.rehash(child)
            if set(value)=={'path','sha256','locator','value'} and value['path'].startswith('data/schedule-generator/apartment/'):
                payload=value['value'] if value['locator']=='/' else {'native_control_schedules':value['value']}
                value['sha256']=hashlib.sha256(canonical(payload)).hexdigest()
        elif isinstance(value,list):
            for child in value:ApartmentFamily.rehash(child)

    @staticmethod
    def erase_proof(value):
        if isinstance(value,dict):
            for key in ('native_control_source','companion_rules'):
                value.pop(key,None)
            for child in value.values():ApartmentFamily.erase_proof(child)
        elif isinstance(value,list):
            value[:]=[x for x in value if not isinstance(x,dict) or x.get('locator')!='/native_control_schedules']
            for child in value:ApartmentFamily.erase_proof(child)

    def test_caller_whole_control_obligation_erasure_rejected(self):
        valid=self.generate(self.request(programmes=False))
        for outputs in (False,True):
            changed=copy.deepcopy(valid)
            if not outputs:
                changed['bindings']=[b for b in changed['bindings'] if b['kind']=='load']
                owner=changed['constituents'][0];owner['binding_indices']=[0];owner['controls']=[]
                owner['slots']=[s for s in owner['slots'] if s['slot']=='hot_water_volume']
                owner['schedule_ids']={k:v for k,v in owner['schedule_ids'].items() if k=='hot_water_volume'}
                changed['schedules']={k:v for k,v in changed['schedules'].items() if k in owner['schedule_ids'].values()}
            self.erase_proof(changed);self.rehash(changed)
            with (patch.object(ResourceSet,'get',side_effect=AssertionError('incoming resources')),
                    patch.object(Path,'read_bytes',side_effect=AssertionError('incoming source'))):
                with self.assertRaises(GeneratorError) as caught:validate_bundle(changed)
            if not outputs:self.assertEqual((caught.exception.code,caught.exception.path),('invalid_reference','/constituents/owner-u'))

    def test_caller_control_proof_and_indices_tamper(self):
        valid=self.generate(self.request(programmes=False))
        for kind in ('remove','duplicate','value','unit','year','foreign_index','second_load','native'):
            changed=copy.deepcopy(valid);owner=changed['constituents'][0];index=owner['binding_indices'][1]
            binding=changed['bindings'][index];schedule=changed['schedules'][binding['schedule_id']]
            if kind=='remove':owner['binding_indices'].remove(index)
            elif kind=='duplicate':owner['binding_indices'][-1]=index
            elif kind=='value':schedule['values'][0]+=1
            elif kind=='unit':schedule['unit']='fraction'
            elif kind=='year':schedule['year']=2008
            elif kind=='foreign_index':binding['physical_id']='foreign'
            elif kind=='second_load':binding['kind']='load'
            else:self.erase_proof(changed);self.rehash(changed)
            with self.subTest(kind=kind),self.assertRaises(GeneratorError):validate_bundle(changed)

    def test_indexed_area_envelope_and_unit_claims(self):
        for kind in ('array','extra','missing','foreign_value','locator','sha','A'):
            params=self.request(n=0);area=params['instances'][1]['basis_bindings']['extents']['floor_area']
            if kind=='array':area['evidence']=area['evidence']['field_evidence']
            elif kind=='extra':area['evidence']['extra']=True
            elif kind=='missing':area['evidence']={}
            elif kind=='foreign_value':area['evidence']['field_evidence'][0]['original_value']=120
            elif kind=='locator':area['evidence']['field_evidence'][0]['locator']='/units/1/floor_area_m2'
            elif kind=='sha':area['evidence']['field_evidence'][0]['source_sha256']='a'*64
            else:area['value']=120
            with self.subTest(kind=kind),patch('atlas_schedules.residential.activity.source_streams',side_effect=AssertionError('RNG')):
                with self.assertRaises(GeneratorError):self.generate(params)

    def test_n0_position_and_water_insertion(self):
        from atlas_schedules.generator import collect_physical_unit_actors,build_physical_unit_generation
        from atlas_schedules.programs import resolve_program
        from atlas_schedules.apartment_authority import bind_apartment_unit_context
        pairs=[]
        for index,n in enumerate((2,0,3)):
            params=self.request(n=n);i=params['instances'][1];i['key']='a'+str(index);i['unit_id']='u'+str(index)
            r=resolve_program(PID,dict(i['inputs'],year=2007,holidays=[]),self.resources)
            bind_apartment_unit_context(i,r);pairs.append((i,r))
        for master,expected in ((42,[42,84,252]),(51,[51,102,306]),(0,[0,0,0])):
            sequence=build_physical_unit_generation(master,pairs)['physical_unit_seed_sequence']
            self.assertEqual([a['unit_seed'] for a in sequence],expected)
            self.assertEqual(sequence[1]['stochastic_action'],'skip_n0')
        with self.assertRaises(GeneratorError):collect_physical_unit_actors([pairs[0],pairs[0]],'1.2.0')

    def test_all_original_targets_and_people_controls(self):
        from atlas_schedules.programs import resolve_program
        from atlas_schedules.apartment_authority_pins import SCOPE_ROWS
        from atlas_schedules.budgets import bind_budget
        for row in SCOPE_ROWS:
            pid=row['id'];record=self.resources.get('program',pid);method=record['recipe']['source_context']['method']
            inputs={'year':2007,'holidays':[],'apartment_method':method}
            if row['role']=='dwelling':inputs['N']=0
            resolved=resolve_program(pid,inputs,self.resources)
            self.assertEqual(resolved['inputs']['reference_budgets'].keys(),{d['demand_id'] for d in resolved['demands']})
            for d in resolved['demands']:
                target=resolved['inputs']['reference_budgets'][d['demand_id']]
                self.assertGreater(target['total'],0)
                bound=bind_budget(target,resolved['inputs']['reference_channels'][d['slot']])
                self.assertAlmostEqual(bound['scaling_receipt']['achieved_total'],target['total'])
        # All40 actual public per-ID outputs, two stochastic realizations each.
        # Caller A and N are independent; no test-local qualification predicate.
        for row in SCOPE_ROWS:
            if row['role']!='dwelling':continue
            pid=row['id']
            bundles=[self.generate(self.request(n=n,area=a,pid=pid),seed)
                     for n,a,seed in ((1,80,42),(2,120,51))]
            for bundle,n,area in zip(bundles,(1,2),(80,120)):
                owner=bundle['constituents'][1];receipt=owner['generation']['source_inputs']['prototype_temporal_adaptation']
                rho=receipt['source_density']['original_load']['value']
                self.assertEqual((receipt['reference_design_people'],receipt['chain_residents']),(rho*area,n))
                self.assertNotIn('residents',owner['inputs']);self.assertEqual(owner['generation']['operating_group'],None)
                self.assertEqual(owner['source']['evidence_view'],row['view'])
                activity=bundle['schedules'][owner['schedule_ids']['activity']]['values']
                self.assertEqual(set(activity),{120.0} if row['template'].startswith('DOE') else {95.0})
            targets=[{b['slot']:b['reference_target']['total'] for b in bundle['bindings'] if b['kind']=='load'} for bundle in bundles]
            self.assertEqual(targets[0],targets[1])
            owners=[bundle['constituents'][1] for bundle in bundles]
            for slot in owners[0]['schedule_ids']:
                if slot in {'occupants','lighting_interior','additional_lighting'}:continue
                self.assertEqual(bundles[0]['schedules'][owners[0]['schedule_ids'][slot]]['values'],
                                 bundles[1]['schedules'][owners[1]['schedule_ids'][slot]]['values'])

    def test_positive_target_zero_generated_integral_has_no_redraw(self):
        controlled={'channels':{'occupants':[.5]*8760,'lighting_interior':[0.0]*8760},
                    'source_context':{'method':'contract_structure_only_zero_lighting'}}
        with patch('atlas_schedules.residential.selected.generate_unit_occupancy_interior_lighting',return_value=controlled) as kernel:
            with self.assertRaises(GeneratorError) as caught:self.generate(self.request())
        self.assertEqual(caught.exception.code,'zero_generated_integral');self.assertEqual(kernel.call_count,1)

    def test_common_fixed_has_no_group_or_actor(self):
        from atlas_schedules.apartment_authority_pins import SCOPE_ROWS
        row=next(x for x in SCOPE_ROWS if x['role']=='support_office')
        params={'schema_version':'1.2.0','resource_set_id':self.resources.resource_set_id,'calendar':copy.deepcopy(CALENDAR),
            'building_realizations':[],'instances':[{'key':'office','owner_kind':'program','program_id':row['id'],
             'operating_group':None,'inputs':{'apartment_method':'source_fixed_apartment_programme'},'basis_bindings':{}}]}
        with (patch('atlas_schedules.generator.sample_operating_parameters',side_effect=AssertionError('COM RNG')),
                patch('atlas_schedules.residential.activity.source_streams',side_effect=AssertionError('RES RNG'))):
            bundle=self.generate(params)
        self.assertEqual(bundle['generation']['physical_unit_seed_sequence'],[])
        self.assertEqual(bundle['generation']['operating_groups'],{})

    def test_caller_water_public_graph_and_tamper(self):
        from atlas_schedules import compose_constituents
        from atlas_schedules.comparison import compare_bundles
        req=self.resources.get('reference','caller-water-requirement__'+PID)
        real=facts.realization([facts.unit('u80','draw80',[req],80),facts.unit('u120','draw120',[req],120)])
        params=self.request(programmes=False);params['building_realizations']=[real]
        params['instances']=[i for i,r in facts.pairs(real,{PID:req},False)]
        with patch('atlas_schedules.residential.activity.source_streams',side_effect=AssertionError('water RNG')):
            bundle=self.generate(params)
        self.assertEqual((len(bundle['schedules']),len(bundle['bindings']),len(bundle['constituents'])),(8,8,2))
        self.assertTrue(all(c['owner_kind']=='physical_service' for c in bundle['constituents']))
        descriptors=[c['shared_services'][0] for c in bundle['constituents']]
        b=descriptors[0]['source_basis_target']['total']
        self.assertEqual([d['source_basis_target']['total'] for d in descriptors],[b,b])
        self.assertEqual([d['whole_input_target']['total'] for d in descriptors],[b*80,b*120])
        second=self.request(programmes=False,area=120)
        real2=facts.realization([facts.unit('u2','draw2',[req],120)],building='building-2')
        second['building_realizations']=[real2];second['instances']=[i for i,r in facts.pairs(real2,{PID:req},False)]
        first=self.generate(self.request(programmes=False,area=80));other=self.generate(second)
        mixture={'program_id':'combined','composition_id':None,'members':[],
            'service_members':[{'instance_key':'owner-u'},{'instance_key':'owner-u2'}],
            'result_basis':'floor_area','denominator':{'value':200,'unit':'m2','evidence':{'caller':'independent root denominator'}}}
        with (patch.object(ResourceSet,'get',side_effect=AssertionError('incoming get')),
              patch.object(ResourceSet,'load',side_effect=AssertionError('incoming load')),
              patch.object(Path,'read_bytes',side_effect=AssertionError('incoming source'))):
            validate_bundle(bundle)
            self.assertEqual(compare_bundles(bundle,copy.deepcopy(bundle),bundle['metadata']['comparison_policy']),[])
            composed=compose_constituents([first,other],mixture,CALENDAR);validate_bundle(composed)
        root=composed['constituents'][-1]
        loads=[composed['bindings'][i] for i in root['binding_indices'] if composed['bindings'][i]['kind']=='load']
        self.assertAlmostEqual(loads[0]['reference_target']['total'],b)

    def test_coherent_static_pool_erasure_before_rng(self):
        from atlas_schedules.apartment_authority import CALENDAR as CLOCK
        context={'family':'HighriseApartment','template':'90.1-2013','reference_calendar':CLOCK}
        key='caller-water-qualification-set__'+hashlib.sha256(canonical(context)).hexdigest()
        for mutation in ('unused','native'):
            group=self.resources.get('reference',key)
            originals=copy.deepcopy(group['value']['qualifications'])
            if mutation=='unused':group['value']['qualifications'].pop()
            else:self.erase_proof(group)
            self.rehash(group)
            # Real coherent replacement bytes and manifest, not an in-memory ready flag.
            with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='a4-pool-') as directory:
                records={('reference','m1-scope'):self.resources.get('reference','m1-scope'),('reference',key):group}
                for original in originals:
                    pid=original['value']['programme_id']
                    for kind in ('requirement','controls','association','qualification','native-controls'):
                        name='caller-water-'+kind+'__'+pid
                        records['reference',name]=self.resources.get('reference',name)
                for q in group['value']['qualifications']:
                    records['reference','caller-water-qualification__'+q['value']['programme_id']]=copy.deepcopy(q)
                manifest=write_resources(Path(directory),records,{})
                changed=ResourceSet(Path(directory),manifest['resource_set_id']);params=self.request(programmes=False)
                params['resource_set_id']=changed.resource_set_id
                with (patch('atlas_schedules.generator.ResourceSet.load',return_value=changed),
                      patch('atlas_schedules.generator.sample_operating_parameters',side_effect=AssertionError('COM RNG')),
                      patch('atlas_schedules.residential.activity.source_streams',side_effect=AssertionError('RES RNG'))):
                    with self.assertRaises(GeneratorError) as caught:generate(params,42)
                self.assertEqual(caught.exception.code,'requires_binding')

    def test_actual_source_stream_records_are_independent_authority(self):
        from atlas_schedules.programs import resolve_program
        keys=['apartment-programme-qualification__'+PID,'apartment-originals__'+PID,
              'apartment-programme-recipe__'+PID,'apartment-fixed-programme__'+PID,
              'apartment-selected-timing','catalogue-index']
        records={('reference',k):self.resources.get('reference',k) for k in keys}
        records['program',PID]=self.resources.get('program',PID)
        timing=records['reference','apartment-selected-timing']['value']
        for key in timing['residential_resources']:records['residential',key]=self.resources.get('residential',key)
        first=next(iter(timing['residential_resources']));records['residential',first]['forged_source_operand']=0
        with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='a4-source-') as directory:
            manifest=write_resources(Path(directory),records,{})
            changed=ResourceSet(Path(directory),manifest['resource_set_id'])
            inputs=dict(self.request()['instances'][1]['inputs'],year=2007,holidays=[])
            with patch('atlas_schedules.residential.activity.source_streams',side_effect=AssertionError('source RNG')):
                with self.assertRaises(GeneratorError) as caught:resolve_program(PID,inputs,changed)
            self.assertEqual(caught.exception.path,'/residential/'+first)

    def test_live_domain_preflight_before_any_rng(self):
        # Real mixed public positive records exactly the resources it consumes.
        # Mutations below change actual files and coherent manifest identities.
        from tests.test_schedule_generator_v1_2_integration import PublicV12IntegrationTests
        helper=PublicV12IntegrationTests();helper.resources=self.resources
        kitchen,physical=helper.restaurant()
        params=self.request(n=1)
        params['instances']=[kitchen,*physical,*params['instances']]
        consumed=set();actual_get=ResourceSet.get
        def retain(resource_set,kind,key):
            consumed.add((kind,key));return actual_get(resource_set,kind,key)
        with patch.object(ResourceSet,'get',new=retain):
            valid=self.generate(params)
        self.assertEqual(valid['constituents'][-1]['inputs']['N'],1)
        self.assertTrue(valid['generation']['operating_groups'])
        genuine={key:actual_get(self.resources,*key) for key in consumed}
        for mutation in ('missing','evidence','locations','wrapper','provenance'):
            records=copy.deepcopy(genuine);key=('reference','apartment-timing-domain')
            if mutation=='missing':records.pop(key)
            elif mutation=='evidence':records[key]['value']['evidence'][0]['source_revision']='foreign'
            elif mutation=='locations':records[key]['value']['locations'][0]['latitude']+=.001
            elif mutation=='wrapper':records[key]['format']='foreign'
            else:records[key]['provenance']['source_revision']='foreign'
            with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='a4-domain-') as directory:
                manifest=write_resources(Path(directory),records,{})
                changed=ResourceSet(Path(directory),manifest['resource_set_id'])
                request=copy.deepcopy(params);request['resource_set_id']=changed.resource_set_id
                with (self.subTest(mutation=mutation),
                      patch('atlas_schedules.generator.ResourceSet.load',return_value=changed),
                      patch('atlas_schedules.generator.sample_operating_parameters',side_effect=AssertionError('COM RNG')),
                      patch('atlas_schedules.residential.activity.source_streams',side_effect=AssertionError('RES RNG'))):
                    with self.assertRaises(GeneratorError) as caught:generate(request,42)
                    self.assertIn('apartment-timing-domain',caught.exception.path)
                    self.assertEqual(caught.exception.code,'requires_binding' if mutation=='missing' else 'source_integrity')


if __name__=='__main__':unittest.main()
