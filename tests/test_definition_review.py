"""Regressions from the one fresh whole-implementation review."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.definition_contract import DefinitionBundle, parameter, record, evidence, BuildContext, load_context
from scripts.definition_validate import validate
from scripts.program_definitions import build_programs
from scripts.program_composition import compose
from scripts.construction_definitions import build_constructions
from scripts.query_v2 import QueryClient, generate_delivery


def program(identity='p', **values):
    row=record('program',{'id':identity,'building_type':'MediumOffice','template':'90.1-2019',
                          'source_family':'code_prototype_rules'},identity)
    row.update(id=identity,detail='SourcePrograms',available_details=['SourcePrograms'],loads=[],**values)
    return row


class ReviewedCompositionTests(unittest.TestCase):
    def test_reviewed_recipes_retain_all_source_members_and_areas(self):
        context=load_context(scope='full')
        bundle=compose(context,build_programs(context))
        key=lambda r:(r['building_type'],r['template'],r['mode'],r['name'])
        source={key(r):r for r in bundle['compositions'] if r['evidence_view']=='source'}
        for r in bundle['compositions']:
            if r['evidence_view']!='reviewed':continue
            members=lambda recipe:{m['source_program_id']:(m['represented_area_m2'],m['weight']) for m in recipe['members']}
            self.assertEqual(members(r),members(source[key(r)]),key(r))


class SelectiveQueryTests(unittest.TestCase):
    def test_impossible_scalar_filters_fetch_no_packets(self):
        row=program(climate='CZ1',system_type='x',role='x',representation='x')
        with tempfile.TemporaryDirectory() as temp:
            generate_delivery(DefinitionBundle(programs=[row]),Path(temp))
            client=QueryClient(Path(temp)); original=client.fetch
            for key in ('climate','detail','gate','system_type','role','representation','derivation'):
                fetched=[]
                def fetch(ref):
                    value=original(ref);fetched.append(value['kind']);return value
                with patch.object(client,'fetch',side_effect=fetch):
                    self.assertEqual(client.query('program',{key:'impossible'},['name'])['match_count'],0)
                self.assertNotIn('packet',fetched,key)

    def test_reviewed_exact_source_id_is_empty_after_replacement(self):
        source=program(); overlay=program('p2',evidence_view='reviewed',source_definition_id='p')
        with tempfile.TemporaryDirectory() as temp:
            generate_delivery(DefinitionBundle(programs=[source,overlay]),Path(temp))
            client=QueryClient(Path(temp))
            self.assertEqual(client.query('program',{'id':'p'},['name'],view='reviewed')['records'],[])
            self.assertEqual(client.query('program',{'id':'p2'},['name'],view='reviewed')['match_count'],1)
            self.assertEqual(client.query('program',{},['name'],view='reviewed')['match_count'],1)

    def test_shared_constructions_are_found_through_source_package_context(self):
        context=load_context(scope='full')
        result=build_constructions(context,build_programs(context))
        with tempfile.TemporaryDirectory() as temp:
            generate_delivery(result,Path(temp));client=QueryClient(Path(temp))
            rows=client.query('construction',{'building_type':'FullServiceRestaurant',
                'template':'90.1-2019','climate':'ClimateZone 7'},['role','representation','building_type'])['records']
            self.assertTrue(any(r['fields']['role']=='ExteriorWall' for r in rows))
            self.assertTrue(any(r['fields']['representation']=='package' for r in rows))
            self.assertTrue(any(r['fields']['building_type'] is None for r in rows))
            self.assertEqual(client.query('construction',{'building_type':'FullServiceRestaurant',
                'template':'90.1-2019','climate':'impossible'},['name'])['match_count'],0)


class ValidationReviewTests(unittest.TestCase):
    def bundle(self):
        ev=evidence(BuildContext(),None,'test',1,'W/m2','identity','test fixture')
        row=program();row['evidence_ids']=[ev['id']]
        row['parameters']={'lighting':parameter(10,'W/m2',ev['id'])}
        return DefinitionBundle(programs=[row],provenance=[ev])

    def test_unsupported_root_schema_rejected(self):
        bundle=self.bundle();bundle['schema_version']='unsupported'
        self.assertTrue(validate(bundle).errors)

    def test_unknown_physical_units_rejected(self):
        bundle=self.bundle();bundle['programs'][0]['parameters']['lighting']['unit']='bananas'
        self.assertTrue(validate(bundle).errors)

    def test_negative_physical_value_rejected(self):
        bundle=self.bundle();bundle['programs'][0]['parameters']['lighting']['value']=-100
        self.assertTrue(validate(bundle).errors)

    def test_orphan_provenance_source_file_rejected(self):
        bundle=self.bundle();bundle['provenance'][0]['source_file_id']='missing'
        self.assertTrue(validate(bundle).errors)

    def test_orphan_component_rules_curves_and_schedules_rejected(self):
        for key in ('performance_rule_ids','curve_ids','schedule_ids'):
            with self.subTest(key=key):
                bundle=self.bundle();bundle['components']=[{'id':'c',key:['missing']}]
                self.assertTrue(validate(bundle).errors)

    def test_fraction_schedule_bounds_rejected(self):
        bundle=self.bundle();bundle['schedules']=[{'id':'s','schedule_type':'fraction','units':'1',
            'rules':[{'day_types':'Default','start_date':'2000-01-01','end_date':'2000-12-31','values':[-1]}]}]
        self.assertTrue(validate(bundle).errors)

    def test_valid_minimal_bundle_is_accepted(self):
        self.assertEqual(validate(self.bundle()).errors,[])
