"""Public second-bundle source-parent reference closure, using actual archived arrays."""
import copy
import gzip
import json
from pathlib import Path
import unittest
import zipfile

from atlas_schedules import compose_constituents
from atlas_schedules.contract import validate_bundle
from atlas_schedules.errors import GeneratorError
from atlas_schedules.source_compositions import remap_binding_references

ROOT=Path(__file__).resolve().parents[1]


def archived_parent_inputs(target=None):
    with zipfile.ZipFile(target or ROOT/'data/generator-releases/v0.5.0/generator.zip') as archive:
        bundle=json.loads(gzip.decompress(archive.read('references/all-cases-bundle.json.gz')))
    parent=next(c for c in bundle['constituents'] if c['generation'].get('method')=='conserved_source_composition')
    office=next(c for c in bundle['constituents'] if c['program_id']=='program-0e670d8dc556f7f5bdd7f1a9')
    def select(keys):
        owners=[copy.deepcopy(c) for c in bundle['constituents'] if c['instance_key'] in keys]
        indices=[i for c in owners for i in c['binding_indices']]
        mapping={original:local for local,original in enumerate(indices)}
        bindings=[copy.deepcopy(bundle['bindings'][i]) for i in indices]
        for item in owners+bindings:remap_binding_references(item,mapping)
        result={k:copy.deepcopy(bundle[k]) for k in ('schema_version','algorithm_version','metadata')}
        result.update(constituents=owners,bindings=bindings,
            schedules={sid:bundle['schedules'][sid] for c in owners for sid in c['schedule_ids'].values()},
            generation={'method':'actual_archived_complete_owner_selection'})
        validate_bundle(result)
        return result
    return select([office['instance_key']]),select([parent['instance_key']]+[m['instance_key'] for m in parent['generation']['members']])


def explicit_references(value,path=()):
    if isinstance(value,dict):
        if 'binding_index' in value:yield path,value
        for key,child in value.items():yield from explicit_references(child,path+(key,))
    elif isinstance(value,list):
        for i,child in enumerate(value):yield from explicit_references(child,path+(i,))


class PublicParentMergeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.office,cls.parent=archived_parent_inputs()

    def merge(self,office=None,parent=None):
        office=office or self.office;parent=parent or self.parent
        requested_parent=next(c for c in parent['constituents'] if c['generation'].get('method')=='conserved_source_composition')
        mixture={'program_id':'office-and-source-parent','composition_id':None,'members':[
            {'instance_key':office['constituents'][0]['instance_key'],'weight':.5},
            {'instance_key':requested_parent['instance_key'],'weight':.5}]}
        return compose_constituents([office,parent],mixture,office['metadata']['calendar'])

    def assert_closed(self,bundle,value):
        references=list(explicit_references(value));self.assertTrue(references)
        for path,reference in references:
            binding=bundle['bindings'][reference['binding_index']]
            for field in ('instance_key','schedule_id','demand_id'):
                if field in reference:self.assertEqual(binding[field],reference[field],path+(field,))
        return references

    def test_second_archived_parent_rebases_demand_target_and_magnitude_references(self):
        before=copy.deepcopy(self.parent)
        result=self.merge()
        parent=next(c for c in result['constituents'] if c['generation'].get('method')=='conserved_source_composition')
        self.assert_closed(result,parent['demands'])
        for index in parent['binding_indices']:
            binding=result['bindings'][index]
            if binding['kind']=='load':
                self.assert_closed(result,binding['reference_target'])
                self.assert_closed(result,binding['reference_target']['original_magnitude'])
        validate_bundle(result)
        self.assertEqual(self.parent,before)

    def test_second_bundle_retained_service_and_generation_references_rebase(self):
        incoming=copy.deepcopy(self.parent)
        owner=incoming['constituents'][0]
        index=next(i for i in owner['binding_indices'] if incoming['bindings'][i]['kind']=='load')
        binding=incoming['bindings'][index]
        ref={k:binding[k] for k in ('instance_key','schedule_id','demand_id')};ref['binding_index']=index
        owner['shared_services'].append({'source_service_id':'explicit-reference-test-only','bound_reference':copy.deepcopy(ref)})
        incoming['generation']['retained_reference']=copy.deepcopy(ref)
        result=self.merge(parent=incoming)
        shifted=next(c for c in result['constituents'] if c['instance_key']==owner['instance_key'])
        self.assert_closed(result,shifted['shared_services'])
        self.assert_closed(result,result['generation']['input_generation_receipts'][1])

    def test_validator_rejects_mispointed_and_malformed_generated_component_ownership(self):
        for field,value in [('binding_index',True),('binding_index',100000),('binding_index',0),
                            ('instance_key','foreign'),('schedule_id','foreign'),('demand_id','foreign')]:
            broken=copy.deepcopy(self.parent)
            parent=next(c for c in broken['constituents'] if c['generation'].get('method')=='conserved_source_composition')
            part=parent['demands'][0]['evidence']['components'][-1]
            part[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(GeneratorError):validate_bundle(broken)

    def test_validator_rejects_corrupt_binding_target_and_original_magnitude_components(self):
        for subtree in ('evidence','original_magnitude'):
            broken=copy.deepcopy(self.parent)
            parent=next(c for c in broken['constituents'] if c['generation'].get('method')=='conserved_source_composition')
            binding=next(broken['bindings'][i] for i in parent['binding_indices'] if broken['bindings'][i]['kind']=='load')
            target=binding['reference_target'][subtree]
            part=next(ref for path,ref in explicit_references(target));part['schedule_id']='foreign'
            with self.subTest(subtree=subtree),self.assertRaises(GeneratorError):validate_bundle(broken)

    def test_validator_requires_actual_trajectory_component_identity(self):
        for field in ('binding_index','instance_key','schedule_id','demand_id'):
            broken=copy.deepcopy(self.parent)
            parent=next(c for c in broken['constituents'] if c['generation'].get('method')=='conserved_source_composition')
            parent['demands'][0]['evidence']['components'][0].pop(field)
            with self.subTest(field=field),self.assertRaises(GeneratorError):validate_bundle(broken)


if __name__=='__main__':unittest.main()
