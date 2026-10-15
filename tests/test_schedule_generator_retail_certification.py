"""Actual C6 native source associations, including real ordered parent members."""
import copy
import unittest
from tests.schedule_generator_retail_fixtures import retail_candidate_resources


class RetailCertificationTests(unittest.TestCase):
    def test_current_packaged_operands_reproduce_all_336_native_arrays_and_profiles(self):
        from scripts.schedule_generator_retail_certification import compare_native_programmes
        resources=retail_candidate_resources()
        result=compare_native_programmes(resources)
        self.assertEqual(result['tested_cases'],336)
        self.assertEqual(result['hourly_values_compared'],16433760)
        self.assertEqual(result['daily_special_profiles_compared'],688492)
        self.assertEqual(result['differences'],[])
        self.assertEqual(result['status'],'passed')

    def test_actual_native_join_closes_229_programmes_32_services_and_parent_members(self):
        from scripts.schedule_generator_retail_certification import build_native_join,validate_native_associations
        resources=retail_candidate_resources()
        records={(e['kind'],e['key']):resources.get(e['kind'],e['key']) for e in resources.manifest['resources']}
        join=build_native_join(records)
        class ActualResources:
            def get(self,kind,key):return copy.deepcopy(records[kind,key])
        actual=ActualResources();report=validate_native_associations(actual,join)
        self.assertEqual((len(join['fixture_bindings']),len(join['service_bindings']),len(join['components'])),(229,32,9))
        self.assertEqual((report['programme_native_cases'],report['physical_fixture_observations'],report['parent_member_observations']),(336,12,116))
        for mutation in ('missing','duplicate','foreign_component','member','service_pointer'):
            changed=copy.deepcopy(join)
            if mutation=='missing':changed['fixture_bindings'].pop()
            elif mutation=='duplicate':changed['components'].append(copy.deepcopy(changed['components'][-1]))
            elif mutation=='foreign_component':next(b for b in changed['fixture_bindings'][165:] if 'native_members' in b)['native_members'][0]['reference_resource_key']='commercial-native-lock'
            elif mutation=='member':next(b for b in changed['fixture_bindings'][165:] if 'native_members' in b)['native_members'][0]['program_id']='foreign-programme'
            else:changed['service_bindings'][-1]['public_native_contexts'][0]['pointer']='/cases/0'
            self.assertNotEqual(changed,join)
            with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,'association|pointer|component|scope'):
                validate_native_associations(actual,changed)

    def test_coherently_rebuilt_join_cannot_reassign_inherited_native_programmes(self):
        from scripts.schedule_generator_retail_certification import build_native_join,validate_native_associations
        resources=retail_candidate_resources()
        records={(e['kind'],e['key']):resources.get(e['kind'],e['key']) for e in resources.manifest['resources']}
        prior=records['reference','c5-family-native-join']['fixture_bindings']
        self.assertNotEqual(prior[0]['native_case_id'],prior[1]['native_case_id'])
        prior[0]['native_case_id']=prior[1]['native_case_id']
        join=build_native_join(records)
        class ActualResources:
            def get(self,kind,key):return copy.deepcopy(records[kind,key])
        with self.assertRaisesRegex(ValueError,'[Ii]nherited'):
            validate_native_associations(ActualResources(),join)


if __name__=='__main__':unittest.main()
