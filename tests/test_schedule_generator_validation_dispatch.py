"""R63: completed contract scans and strict cold physical graph entry."""
import copy
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
