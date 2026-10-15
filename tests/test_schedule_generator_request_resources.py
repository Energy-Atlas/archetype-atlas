"""A generating request verifies its snapshot once; public composition stays fresh."""
import copy
import inspect
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from atlas_schedules import generate,compose_constituents
from atlas_schedules.contract import validate_bundle
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet
from tests.schedule_generator_retail_fixtures import retail_candidate_resources


class RequestResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources=retail_candidate_resources()
        scope=cls.resources.get('reference','m1-scope');instances=[]
        for family in ('Warehouse','RetailStandalone'):
            case=next(c for c in scope['cases'] if c['building_type']==family and
                      'source_composition' in cls.resources.get('program',c['program_id'])['recipe'])
            recipe=cls.resources.get('program',case['program_id'])['recipe']
            instances.append({'key':case['case_id'],'owner_kind':'program','program_id':case['program_id'],
                'inputs':dict(copy.deepcopy(recipe['bound_inputs']),composition_basis_mode='source_reference_area_normalized'),
                'basis_bindings':{},'operating_group':case['configuration_id']})
        cls.params={'schema_version':'1.1.0','resource_set_id':cls.resources.resource_set_id,
            'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'instances':instances}
        cls.bundle=None

    def actual_bundle(self):
        if self.__class__.bundle is None:
            with patch.object(ResourceSet,'load',side_effect=lambda rid:ResourceSet(self.resources.root,rid)):
                self.__class__.bundle=generate(self.params,42)
        return self.bundle

    def physical_input(self):
        from atlas_schedules.source_compositions import project_source_members
        bundle=self.actual_bundle()
        parent=next(c for c in bundle['constituents'] if c['generation'].get('method')=='conserved_source_composition')
        receipt=parent['generation']['source_allocation']
        local,_=project_source_members(bundle,parent['generation']['member_instance_keys'])
        mixture={'program_id':parent['program_id'],'composition_id':receipt['composition_id'],
            'members':[{'instance_key':key,'weight':1} for key in parent['generation']['member_instance_keys']],
            'result_basis':'floor_area','denominator':{'value':receipt['source_total_area_m2'],'unit':'m2',
                'evidence':{'test':'actual original source reference area'}}}
        return local,mixture

    def test_two_actual_source_parents_use_one_real_resource_construction(self):
        constructed=[]
        def load(rid):
            result=ResourceSet(self.resources.root,rid);constructed.append(result);return result
        with patch.object(ResourceSet,'load',side_effect=load):bundle=generate(self.params,42)
        self.__class__.bundle=bundle
        validate_bundle(bundle)
        self.assertEqual(sum(c['generation'].get('method')=='conserved_source_composition' for c in bundle['constituents']),2)
        self.assertEqual(len(constructed),1,'Private parent validation must reuse this request verified snapshot')

    def test_public_source_composition_keeps_fresh_verification(self):
        local,mixture=self.physical_input();constructed=[]
        def load(rid):
            result=ResourceSet(self.resources.root,rid);constructed.append(result);return result
        with patch.object(ResourceSet,'load',side_effect=load):
            actual=compose_constituents([local],mixture,local['metadata']['calendar'])
        validate_bundle(actual)
        self.assertEqual(len(constructed),1)
        self.assertEqual(actual['constituents'][-1]['generation']['method'],'conserved_source_composition')
        self.assertEqual(list(inspect.signature(compose_constituents).parameters),['constituents','mixture','calendar'])

    def test_public_composition_detects_corrupted_independent_resources(self):
        local,mixture=self.physical_input()
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'resources';shutil.copytree(self.resources.root,target)
            entry=next(e for e in self.resources.manifest['resources'] if e['kind']=='program')
            with (target/entry['path']).open('ab') as stream:stream.write(b' ')
            with patch.object(ResourceSet,'load',side_effect=lambda rid:ResourceSet(target,rid)):
                with self.assertRaises(GeneratorError) as error:
                    compose_constituents([local],mixture,local['metadata']['calendar'])
            self.assertEqual(error.exception.code,'resource_integrity')

    def test_json_cannot_supply_verified_resource_override(self):
        params=copy.deepcopy(self.params);params['verified_resources']={'resource_set_id':self.resources.resource_set_id}
        with self.assertRaises(GeneratorError) as error:generate(params,42)
        self.assertEqual(error.exception.code,'invalid_contract')

    def private_composer(self):
        from atlas_schedules import mixtures
        method=getattr(mixtures,'_compose_constituents',None)
        self.assertTrue(callable(method),'Private request-scoped composition route is missing')
        return method

    def test_private_snapshot_rejects_nonexact_type_and_foreign_identity(self):
        method=self.private_composer();local,mixture=self.physical_input()
        class ForeignResource(ResourceSet):pass
        subclass=object.__new__(ForeignResource);subclass.resource_set_id=self.resources.resource_set_id
        foreign=copy.copy(self.resources);foreign.resource_set_id='resources-foreign'
        for snapshot in (object(),{},subclass,foreign):
            with self.subTest(snapshot=type(snapshot).__name__),self.assertRaises(GeneratorError) as error:
                method([local],mixture,local['metadata']['calendar'],verified_resources=snapshot)
            self.assertEqual(error.exception.code,'resource_integrity')

    def test_private_snapshot_preserves_actual_public_result_without_reloading(self):
        from atlas_schedules.comparison import compare_bundles
        method=self.private_composer();local,mixture=self.physical_input()
        with patch.object(ResourceSet,'load',side_effect=lambda rid:ResourceSet(self.resources.root,rid)):
            expected=compose_constituents([local],mixture,local['metadata']['calendar'])
        with patch.object(ResourceSet,'load',side_effect=AssertionError('Private verified snapshot must not reload')):
            actual=method([local],mixture,local['metadata']['calendar'],verified_resources=self.resources)
        self.assertEqual(compare_bundles(actual,expected,expected['metadata']['comparison_policy']),[])
        validate_bundle(actual)

    def test_private_snapshot_retains_source_member_and_extent_guards(self):
        method=self.private_composer();original,definition=self.physical_input()
        for mutation in ('order','weight','extent'):
            local=copy.deepcopy(original);mixture=copy.deepcopy(definition)
            if mutation=='order':mixture['members'].reverse()
            if mutation=='weight':mixture['members'][0]['weight']=.5
            if mutation=='extent':local['constituents'][0]['basis_bindings']['extents']['floor_area']['value']*=2
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError) as error:
                method([local],mixture,local['metadata']['calendar'],verified_resources=self.resources)
            self.assertEqual(error.exception.code,'incompatible_source_composition')


if __name__=='__main__':unittest.main()
