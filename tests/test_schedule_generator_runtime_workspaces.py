"""Real locked caller proof and incoming-only workspace regression checks."""
import ast
import copy
import hashlib
import json
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from atlas_schedules import caller_unit_water as caller, service_graph as graph
from atlas_schedules import generate
from atlas_schedules.canonical import canonical
from atlas_schedules.contract import validate_bundle
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet, write_resources

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'data/schedule-generator/apartment'
PID = 'program-23458a6e125b4cee7f62bb42'
CLOCK = {'year':2007,'clock':'local_standard_time','holidays':[]}


def locked_caller_resources(destination):
    """Decode checked-in fixed preimages, with no compiler or qualification stub."""
    manifest=json.loads((BASE/'fixed-qualification-manifest.json').read_bytes())
    records={}
    for key,entry in manifest['proof_files'].items():
        blob=(ROOT/entry['source_path']).read_bytes()
        assert len(blob)==entry['size_bytes'] and hashlib.sha256(blob).hexdigest()==entry['sha256']
        value=json.loads(blob)
        if key.startswith('caller-water-requirement__'):record=value
        else:
            locator='/native_control_schedules' if key.startswith('caller-water-native-controls__') else '/'
            record={'path':entry['source_path'],'sha256':entry['sha256'],'locator':locator,
                    'value':value if locator=='/' else value['native_control_schedules']}
        records['reference',key]=record
    # The existing shipped scope is used verbatim. Caller owners are prepared
    # through their separately qualified declaration, before legacy scope lookup.
    shipped=json.loads((ROOT/'atlas_schedules/data/manifest.json').read_bytes())
    original=ResourceSet(ROOT/'atlas_schedules/data',shipped['resource_set_id'])
    records['reference','m1-scope']=original.get('reference','m1-scope')
    records['reference','comparison-policy']=original.get('reference','comparison-policy')
    records['reference','catalogue-index']=original.get('reference','catalogue-index')
    qualification_path=BASE/('authority/apartment-programme-qualification__'+PID+'.json')
    blob=qualification_path.read_bytes();q=json.loads(blob)
    records['reference','apartment-programme-qualification__'+PID]={
        'path':qualification_path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(blob).hexdigest(),
        'locator':'/','value':q}
    for field,key in (('original_sources','apartment-originals__'+PID),
                      ('compiled_recipe','apartment-programme-recipe__'+PID),
                      ('selected_timing','apartment-selected-timing')):
        records['reference',key]=copy.deepcopy(q[field])
    records['program',PID]=copy.deepcopy(q['compiled_recipe']['value'])
    from atlas_schedules.apartment_authority import validate_apartment_authority
    validate_apartment_authority(PID,records['program',PID],records['reference','apartment-programme-qualification__'+PID])
    # Same catalogue assembly as build_apartment_resources after real per-ID
    # validation. This lookup status never bypasses any source/native qualifier.
    next(row for row in records['reference','catalogue-index']['programs'] if row['id']==PID).update(
        status='compiled',reason='Reviewed A1/A3 per-ID apartment method association; A5 release certification separate')
    timing=q['selected_timing']['value'];lock=timing['timing_lock']['value']
    records['reference','apartment-timing-domain']={
        'schema_version':'1.0.0','format':'source_domain','value':copy.deepcopy(timing['domain']['value']),
        'provenance':{'source_revision':lock['source_revision'],'source_lock_sha256':lock['source_lock_sha256'],
                      'native_capture_sha256':{label:lock['vectors'][label]['sha256'] for label in ('M1','R1')},
                      'extraction_date':lock['extraction_date'],'upstream_notices':copy.deepcopy(lock['notices']),
                      'interpretation_note':'Selected-method controlled timing domain only'}}
    for key,sha in timing['residential_resources'].items():
        value=original.get('residential',key)
        assert hashlib.sha256(canonical(value)).hexdigest()==sha
        records['residential',key]=value
    result=write_resources(destination,records,{'scope':'locked fixed caller regression'})
    return ResourceSet(destination,result['resource_set_id'])


def caller_request(resources):
    req=resources.get('reference','caller-water-requirement__'+PID)
    # Caller facts are explicit test geometry, never upstream/source authority.
    facts={'building_realization_id':'runtime-building','unit_inventory_id':'runtime-inventory',
           'units':[{'unit_id':'u','physical_id':'draw','source_service_id':req['source_service_id'],
                     'source_beneficiary_id':req['source_beneficiary_id'],'programme_ids':[PID],
                     'water_authority_programme_id':PID,'floor_area_m2':80.0}]}
    digest=hashlib.sha256(canonical(facts)).hexdigest()
    def evidence(locator,value,unit=None):
        return {'source_revision':'explicit-caller-test-facts','source_path':'caller/runtime-facts.json',
                'source_sha256':digest,'locator':locator,'original_value':copy.deepcopy(value),
                'original_unit':unit,'transformation':'Retain explicit caller fact',
                'extraction_date':'2026-10-15','interpretation_note':'Caller test geometry, not source geometry'}
    u=copy.deepcopy(facts['units'][0]);u['multiplicity']=1
    u['area_evidence']=[evidence('/units/0/floor_area_m2',80.0,'m2')]
    u['identity_evidence']=[evidence('/'+k,facts[k]) for k in ('building_realization_id','unit_inventory_id')]
    u['identity_evidence'] += [evidence('/units/0/'+k,v) for k,v in facts['units'][0].items() if k!='floor_area_m2']
    inventory={'authority':'caller_declared_units','units':[u]}
    real={'mode':caller.MODE,'building_realization_id':facts['building_realization_id'],
          'building_type':req['family'],'template':req['template'],'unit_inventory_id':facts['unit_inventory_id'],
          'unit_inventory':inventory,'unit_inventory_sha256':hashlib.sha256(canonical(inventory)).hexdigest()}
    owner={'key':'runtime-owner','owner_kind':'physical_service','physical_binding_kind':caller.MODE,
           'building_realization_id':facts['building_realization_id'],'unit_id':'u','physical_id':'draw',
           'source_service_id':req['source_service_id'],'operating_group':None,
           'inputs':{'water_method':caller.METHOD,'source_geometry_departure':'caller_unit_area'},
           'basis_bindings':{'multiplicity':1,'extents':{'floor_area':{'value':80.0,'unit':'m2',
                                                                     'evidence':copy.deepcopy(u['area_evidence'])}}}}
    programme={'key':'runtime-programme','owner_kind':'program','program_id':PID,
               'building_realization_id':facts['building_realization_id'],'unit_id':'u','operating_group':None,
               'inputs':{'apartment_method':'unit_occupancy_interior_lighting','N':0},
               'basis_bindings':copy.deepcopy(owner['basis_bindings'])}
    programme['basis_bindings']['extents']['floor_area']['evidence']={'field_evidence':copy.deepcopy(u['area_evidence'])}
    return {'schema_version':'1.2.0','resource_set_id':resources.resource_set_id,
            'calendar':copy.deepcopy(CLOCK),'building_realizations':[real],'instances':[owner,programme]}


class RuntimeWorkspaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.resources=locked_caller_resources(Path(cls.temp.name)/'resources')
        with patch('atlas_schedules.generator.ResourceSet.load',return_value=cls.resources):
            cls.bundle=generate(caller_request(cls.resources),42)
        historical=BASE/'qualification-code/a5-r70-current-then/atlas_schedules/service_graph.py'
        namespace=dict(graph.__dict__)
        exec(compile(historical.read_bytes(),str(historical),'exec'),namespace)
        cls.original_physical=staticmethod(namespace['validate_physical_graph'])
        cls.original_low_graph=staticmethod(namespace['_validate_physical_graph'])

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def original_entry(self,entry,bundle):
        if entry is validate_bundle:
            # Replay the same unchanged public contract ordering with its exact
            # retained original physical implementation, not another entrypoint.
            with patch.object(graph,'_validate_physical_graph',self.original_low_graph):entry(bundle)
        else:self.original_physical(bundle)

    def assertIncoming(self,entry,bundle,accept=True,path=None):
        before=canonical(bundle)
        original_open=io.open
        def incoming_open(file,*args,**kwargs):
            target=Path(file).resolve()
            runtime=ROOT/'atlas_schedules'
            if not (target.is_relative_to(runtime) and
                    (target.suffix in {'.py','.pyc'} or target.parent==runtime/'schemas')):
                raise AssertionError('incoming non-code/schema read: '+str(target))
            return original_open(file,*args,**kwargs)
        with (patch.object(ResourceSet,'get',side_effect=AssertionError('incoming resource lookup')),
              patch.object(ResourceSet,'load',side_effect=AssertionError('incoming resource load')),
              patch('subprocess.Popen',side_effect=AssertionError('incoming subprocess')),
              patch('socket.socket',side_effect=AssertionError('incoming network')),
              patch.object(io,'open',side_effect=incoming_open)):
            if accept:
                entry(bundle)
                self.original_entry(entry,bundle)
            else:
                with self.assertRaises(GeneratorError) as caught:entry(bundle)
                if path:self.assertEqual(caught.exception.path,path)
                with self.assertRaises(GeneratorError) as original:self.original_entry(entry,bundle)
                self.assertEqual((caught.exception.code,caught.exception.path,caught.exception.message),
                                 (original.exception.code,original.exception.path,original.exception.message))
        self.assertEqual(canonical(bundle),before)

    def test_cold_real_caller_both_strict_entries_and_rejections_are_nonmutating(self):
        programme=next(o for o in self.bundle['constituents'] if o['owner_kind']=='program')
        self.assertTrue(programme['service_set_projections'])
        for entry in (validate_bundle,graph.validate_physical_graph):
            self.assertIncoming(entry,copy.deepcopy(self.bundle))
            for mutation in ('control','foreign_owner','foreign_projection','qualification','unused'):
                value=copy.deepcopy(self.bundle);owner=value['constituents'][0]
                real=value['metadata']['building_realizations'][0]
                if mutation=='control':owner['binding_indices'].pop()
                elif mutation=='foreign_owner':owner['physical_id']='foreign'
                elif mutation=='foreign_projection':
                    next(o for o in value['constituents'] if o['owner_kind']=='program')['service_set_projections'][0]['physical']['binding_index']=1
                elif mutation=='qualification':real['method_qualification']['value']['family']='foreign'
                else:
                    pool=real['method_qualification']['value']['qualifications']
                    unused=next(q for q in pool if q['value']['programme_id'] not in real['unit_inventory']['units'][0]['programme_ids'])
                    self.assertNotEqual(unused['value']['programme_id'],PID)
                    unused['value']['association']['value']['service_definition']['value']['id']='foreign'
                self.assertIncoming(entry,value,False)

    def test_workspace_copies_only_actual_write_paths_and_preserves_aliases(self):
        original=copy.deepcopy(self.bundle)
        owner=original['constituents'][0];owner['service_set_projections']=[]
        original['diagnostic_alias']=[owner['source'],owner['source']]
        before=copy.deepcopy(original)
        legacy=graph._validation_workspace(original,'legacy')
        candidate=graph._validation_workspace(original,'caller')
        for result in (legacy,candidate):
            self.assertIsNot(result,original)
            self.assertIsNot(result['constituents'],original['constituents'])
            self.assertIsNot(result['constituents'][0],owner)
            self.assertIs(result['schedules'],original['schedules'])
            self.assertIs(result['diagnostic_alias'][0],result['diagnostic_alias'][1])
        legacy['constituents'][0].pop('physical_binding_kind')
        legacy['bindings'][0].pop('physical_binding_kind')
        candidate['constituents'][0]['generation']['water_method_receipt']={}
        candidate['constituents'][0]['service_set_projections'].append({'new':'projection'})
        candidate['metadata']['building_realizations'].append({})
        self.assertIs(candidate['bindings'],original['bindings'])
        self.assertIsNot(legacy['bindings'],original['bindings'])
        self.assertEqual(original,before)

    def test_source_walk_keeps_all_container_order_and_original_error_indices(self):
        pool=self.bundle['metadata']['building_realizations'][0]['method_qualification']
        real=pool['value']['qualifications'][0]
        source={'ordered':[0,'lead',None,{'nested':[False,{},[],copy.deepcopy(real)]},[],{}],
                'again':copy.deepcopy(real)}
        graph._source_consistency(source)
        bad=copy.deepcopy(source);bad['ordered'][3]['nested'][3]['sha256']='invalid'
        with self.assertRaises(GeneratorError) as caught:graph._source_consistency(bad)
        self.assertEqual(caught.exception.path,'/ordered/3/nested/3/sha256')
        for change in ('value','revision'):
            bad=copy.deepcopy(source)
            if change=='value':bad['again']['value']['diagnostic_conflict']='changed'
            else:bad['again']['sha256']='f'*64
            with self.assertRaises(GeneratorError):graph._source_consistency(bad)
        visits=[]
        def trace(frame,event,arg):
            if event=='call' and frame.f_code.co_name=='walk' and frame.f_code.co_filename==graph.__file__:
                visits.append((frame.f_locals['path'],type(frame.f_locals['current'])))
        sys.setprofile(trace)
        try:graph._source_consistency(source)
        finally:sys.setprofile(None)
        self.assertTrue(all(t in (dict,list) for _,t in visits))
        self.assertIn(('/ordered/3/nested/1',dict),visits)
        self.assertIn(('/ordered/3/nested/2',list),visits)
        historical=BASE/'qualification-code/a5-r70-current-then/atlas_schedules/service_graph.py'
        tree=ast.parse(historical.read_bytes())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_source_consistency')
        namespace=dict(graph.__dict__)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(historical),'exec'),namespace)
        original_visits=[]
        def original_trace(frame,event,arg):
            if event=='call' and frame.f_code.co_name=='walk' and frame.f_code.co_filename==str(historical):
                original_visits.append((frame.f_locals['path'],type(frame.f_locals['current'])))
        sys.setprofile(original_trace)
        try:namespace['_source_consistency'](source)
        finally:sys.setprofile(None)
        self.assertEqual(visits,[r for r in original_visits if r[1] in (dict,list)])

    def test_public_finite_schema_and_generated_reference_guards_remain(self):
        for entry in (validate_bundle,graph.validate_physical_graph):
            for change in ('finite','schema','reference'):
                value=copy.deepcopy(self.bundle)
                if change=='finite':next(iter(value['schedules'].values()))['values'][2]=float('nan')
                elif change=='schema':value['constituents'][0]['binding_indices'][0]=True
                else:value['generation']['diagnostic']=[0,None,'lead',{'binding_index':0,'instance_key':'foreign'}]
                with self.assertRaises(GeneratorError):entry(value)


if __name__=='__main__':unittest.main()
