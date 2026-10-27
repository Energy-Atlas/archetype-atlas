"""Regressions from the one fresh whole-implementation review."""
import copy
import unittest

from scripts.definition_contract import DefinitionBundle, parameter, record, evidence, BuildContext, load_context
from scripts.definition_validate import validate
from scripts.program_definitions import build_programs
from scripts.program_composition import compose


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
