"""C6 release request order, explicit service denominator and code authority."""
import copy
import hashlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from atlas_schedules.canonical import canonical
from tests.schedule_generator_retail_fixtures import retail_candidate_resources
from atlas_schedules.resources import ResourceSet,write_resources

ROOT=Path(__file__).resolve().parents[1]


class RetailReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources=retail_candidate_resources()
        cls.scope=cls.resources.get('reference','m1-scope');cls.scope['milestone_id']='C6'

    def test_restricted_coverage_retains_filtered_authoritative_request_order(self):
        from scripts.schedule_generator_coverage import build_coverage,coverage_errors
        records={(e['kind'],e['key']):self.resources.get(e['kind'],e['key']) for e in self.resources.manifest['resources']}
        scope=copy.deepcopy(self.scope)
        for case in scope['cases']:
            case['source_gate_status']='passed';records['program',case['program_id']]['case']=copy.deepcopy(case)
        for case in scope['service_cases']:case['source_gate_status']='passed'
        records['reference','m1-scope']=scope
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifest=write_resources(root,records,{'scope':'synthetic-positive-source-gate-coverage-fixture-not-certificate'})
            resources=ResourceSet(root,manifest['resource_set_id'])
            selected=copy.deepcopy(scope);selected['milestone_id']='C6-restricted-retail-source'
            selected['cases']=[next(c for c in scope['cases'] if c['building_type']=='RetailStandalone' and
                c['template']=='90.1-2013' and c['evidence_view']=='source' and 'source_composition' not in records['program',c['program_id']]['recipe'])]
            selected['service_cases']=[next(c for c in scope['service_cases'] if c['building_type']=='RetailStandalone' and
                c['template']=='90.1-2013' and c['hoo_evidence_view']=='source')]
            keys={c['case_id'] for c in selected['cases']+selected['service_cases']}
            selected['qualification_request_order']=[key for key in scope['qualification_request_order'] if key in keys]
            report=build_coverage(resources,selected)
            self.assertEqual((report['scope']['case_count'],report['scope']['service_case_count']),(1,1))
            self.assertEqual(coverage_errors(report,resources),[])

    def test_release_examples_preserve_exact_authoritative_order_and_retail_mix(self):
        from scripts.schedule_generator_retail import qualification_request,mixed_qualification_request
        from scripts.schedule_generator_release import _request,_mixed_request
        records={('reference','m1-scope'):self.scope};files={}
        pairs=[('program',c['program_id']) for c in self.scope['cases']]
        pairs.extend(('reference',c['resource_key']) for c in self.scope['service_cases'])
        for pair in pairs:
            records[pair]=self.resources.get(*pair)
            files['atlas_schedules/data/'+pair[0]+'/'+pair[1]+'.json']=canonical(records[pair])
        expected=qualification_request(records);expected['resource_set_id']=self.resources.resource_set_id
        actual=_request(self.scope,files,self.resources.resource_set_id)
        self.assertEqual(actual,{'schema_version':'1.1.0','params':expected,'seed':42})
        self.assertEqual(_mixed_request(self.scope,self.resources),mixed_qualification_request(records,self.resources.resource_set_id))

    def test_c6_certificate_requires_exact_denominator_and_changed_current_checker(self):
        from scripts.schedule_generator_release import (validate_family_certification,certification_dependency_hash,
            implementation_sources,implementation_source_hash)
        scope=copy.deepcopy(self.scope);resource=self.resources
        native={'vectors':{'fixture':'checker-contract-only, never actual certification'},
                'fixture_order':[c['configuration_id'] for c in scope['cases']]}
        certificate={'status':'passed','case_ids':[c['case_id'] for c in scope['cases']],
            'service_case_ids':[c['case_id'] for c in scope['service_cases']],
            'scope_sha256':hashlib.sha256(canonical(scope)).hexdigest(),
            'dependency_sha256':certification_dependency_hash(resource.manifest),
            'native_source_discrete_numerical_passed':True,'annual_target_invariance_passed':True,
            'temporal_variation_and_fixed_channels_passed':True,'master_seeds':[42,51],
            'native_reference':native['vectors'],'declared_owned_slot_count':1738,
            'required_service_link_count':10,'source_service_definition_count':16,
            'family_qualifications':{family:{
                'programme_case_ids':[c['case_id'] for c in scope['cases'] if c['building_type']==family],
                'service_case_ids':[c['case_id'] for c in scope['service_cases'] if c['building_type']==family],
                'master_seeds':[42,51],'native_source_discrete_numerical_passed':True,'bound_public_examples_passed':True}
                for family in ('FullServiceRestaurant','QuickServiceRestaurant','RetailStandalone')},
            'implementation_source_sha256':{name:implementation_source_hash((ROOT/name).read_bytes()) for name in implementation_sources('C6')}}
        class Fixture:
            manifest=resource.manifest
            def get(self,kind,key):
                if key=='family-certification':return copy.deepcopy(certificate)
                if key=='family-native-lock':return copy.deepcopy(native)
                return resource.get(kind,key)
        # Source/native associations have their own actual-capture tests. This
        # fixture isolates denominator/code authority; it cannot certify a release.
        with patch('scripts.schedule_generator_release.validate_native_join'):
            validate_family_certification(Fixture(),scope)
            certificate['declared_owned_slot_count']=1370
            with self.assertRaisesRegex(ValueError,'denominator'):validate_family_certification(Fixture(),scope)
            certificate['declared_owned_slot_count']=1738
            for name in ('atlas_schedules/contract.py','scripts/schedule_generator_native_codec.py',
                         'scripts/schedule_generator_retail_certification.py'):
                certificate['implementation_source_sha256'][name]='0'*64
                with self.subTest(source=name),self.assertRaisesRegex(ValueError,'implementation/checker source differs'):
                    validate_family_certification(Fixture(),scope)
                certificate['implementation_source_sha256'][name]=implementation_source_hash((ROOT/name).read_bytes())


if __name__=='__main__':unittest.main()
