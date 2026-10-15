"""R63: completed contract scans and strict cold physical graph entry."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from atlas_schedules import generate
from atlas_schedules import contract, service_graph
from atlas_schedules.errors import GeneratorError


class ValidationDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_schedule_generator_apartment_family import ApartmentFamily
        from tests.test_schedule_generator_v1_2_integration import PublicV12IntegrationTests
        ApartmentFamily.setUpClass()
        helper=ApartmentFamily();helper.resources=ApartmentFamily.resources
        prior=PublicV12IntegrationTests();prior.resources=helper.resources
        kitchen,physical=prior.restaurant()
        params=helper.request(n=0)
        params['instances']=[prior.stock('actual-whole-residential'),kitchen,*physical,*params['instances']]
        with patch('atlas_schedules.generator.ResourceSet.load',return_value=helper.resources):
            cls.bundle=generate(params,42)
        cls.params=params

    def trace(self,entry):
        calls={'finite':0,'schema':0,'generated_references':0,'physical_proof':0}
        finite=contract._finite;schema=contract._schema_errors
        references=contract._validate_generated_binding_references
        physical=service_graph._validate_physical_graph
        def count_finite(value,path=''):
            if path=='':calls['finite']+=1
            return finite(value,path)
        def count_schema(*args,**kwargs):
            calls['schema']+=1;return schema(*args,**kwargs)
        def count_references(*args,**kwargs):
            calls['generated_references']+=1;return references(*args,**kwargs)
        def count_physical(*args,**kwargs):
            calls['physical_proof']+=1;return physical(*args,**kwargs)
        with (patch.object(contract,'_finite',new=count_finite),
              patch.object(contract,'_schema_errors',new=count_schema),
              patch.object(contract,'_validate_generated_binding_references',new=count_references),
              patch.object(service_graph,'_validate_physical_graph',new=count_physical)):
            entry(self.bundle)
        return calls

    def test_completed_contract_checks_execute_once(self):
        self.assertEqual(self.trace(contract.validate_bundle),
            {'finite':1,'schema':1,'generated_references':1,'physical_proof':1})

    def test_direct_cold_graph_entry_retains_all_strict_checks(self):
        from atlas_schedules.resources import ResourceSet
        with (patch.object(ResourceSet,'get',side_effect=AssertionError('cold incoming resource get')),
              patch.object(ResourceSet,'load',side_effect=AssertionError('cold incoming resource load'))):
            self.assertEqual(self.trace(service_graph.validate_physical_graph),
                {'finite':1,'schema':1,'generated_references':1,'physical_proof':1})

    def test_malformed_proofs_rejected_by_both_entries(self):
        for entry in (contract.validate_bundle,service_graph.validate_physical_graph):
            for kind in ('nonfinite','schema','generated_reference','mandatory_control','native_proof'):
                bundle=copy.deepcopy(self.bundle)
                water=next(c for c in bundle['constituents'] if c.get('physical_binding_kind')==
                           'caller_unit_prototype_density_fixed_dhw')
                if kind=='nonfinite':next(iter(bundle['schedules'].values()))['values'][0]=float('inf')
                elif kind=='schema':bundle['foreign_top_level_field']=True
                elif kind=='generated_reference':water['binding_indices'][0]=len(bundle['bindings'])
                elif kind=='mandatory_control':water['binding_indices'].pop()
                else:
                    from tests.test_schedule_generator_apartment_family import ApartmentFamily
                    ApartmentFamily.erase_proof(bundle)
                    ApartmentFamily.rehash(bundle)
                with self.subTest(entry=entry.__name__,kind=kind),self.assertRaises(GeneratorError):
                    entry(bundle)

    @staticmethod
    def previous_walker():
        root=Path(__file__).resolve().parents[1]
        path=root/'data/schedule-generator/apartment/qualification-code/a5-r63-current-then/atlas_schedules/contract.py'
        if hashlib.sha256(path.read_bytes()).hexdigest()!='f5246178c3f93346245d5b1ae57f068bdb0d96d420290f2dc1246dad611aea9b':
            raise AssertionError('Exact retained R63 contract required')
        spec=importlib.util.spec_from_file_location('atlas_schedules._r63_reference_contract',path)
        module=importlib.util.module_from_spec(spec)
        exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
        return module._validate_generated_binding_references

    def test_nested_reference_indices_and_parent_guards(self):
        # Structural probes inside a genuine retained graph exercise this
        # reference scanner, rather than asserting qualification of extra data.
        source=self.bundle['bindings'][0]
        reference={k:source[k] for k in ('instance_key','schedule_id','owner_kind','program_id')}
        reference['binding_index']=0
        foreign=next(i for i,b in enumerate(self.bundle['bindings'])
                     if b['instance_key']!=source['instance_key'])
        for walker in (self.previous_walker(),contract._validate_generated_binding_references):
            valid=copy.deepcopy(self.bundle)
            valid['generation']['retained_probe']=[0,None,['literal',reference]]
            walker(valid)
            bad=copy.deepcopy(valid);bad['generation']['retained_probe'][2][1]['binding_index']=foreign
            with self.assertRaises(GeneratorError) as caught:walker(bad)
            self.assertEqual(caught.exception.path,'/generation/retained_probe/2/1/instance_key')
            for probe,path in [({'binding_indices':[True]},'/binding_indices/0'),
                               ({'binding_indices':[[0]]},'/binding_indices/0'),
                               ({'method':'actual_generated_bound_trajectory_sum','components':[1.0]},'/components')]:
                bad=copy.deepcopy(self.bundle)
                bad['generation']['retained_probe']=[None,['prefix',{'nested':[False,probe]}]]
                with self.subTest(walker=walker.__module__,probe=probe),self.assertRaises(GeneratorError) as caught:
                    walker(bad)
                self.assertEqual(caught.exception.path,'/generation/retained_probe/1/1/nested/1'+path)

    def test_bounded_actual_old_new_walker_timing(self):
        from atlas_schedules.canonical import canonical
        blob=canonical(self.bundle);before=hashlib.sha256(blob).hexdigest()
        measurements={}
        for name,walker in (('retained_r63',self.previous_walker()),
                            ('r64',contract._validate_generated_binding_references)):
            started=time.perf_counter();walker(self.bundle)
            measurements[name]={'elapsed_seconds':time.perf_counter()-started}
        self.assertEqual(hashlib.sha256(canonical(self.bundle)).hexdigest(),before)
        report={'schema_version':'1.0.0','interpretation':'Bounded diagnostic on the same genuine mixed public graph; no timing acceptance threshold and no scientific values changed',
                'bundle_sha256':before,'serialized_bytes':len(blob),'constituents':len(self.bundle['constituents']),
                'schedules':len(self.bundle['schedules']),'bindings':len(self.bundle['bindings']),
                'measurements':measurements}
        path=Path(__file__).resolve().parents[1]/'build/task-10/apartment-a5/r64-walker-timing.json'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(report))
