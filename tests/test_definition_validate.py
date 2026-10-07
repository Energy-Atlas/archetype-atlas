import unittest
from scripts.definition_contract import DefinitionBundle, parameter
from scripts.definition_validate import validate


class ValidationTests(unittest.TestCase):
    def test_annual_profile_length_and_material_physics_are_checked(self):
        bundle=DefinitionBundle(schedules=[{'id':'s','annual_values':[1]*23,'calendar':{'year':2007}}],
            materials=[{'id':'m','thickness_m':-1}])
        errors=validate(bundle).errors
        self.assertTrue(any('annual' in e for e in errors))
        self.assertTrue(any('material' in e for e in errors))
    def test_invalid_schedule_rule_is_rejected(self):
        bundle=DefinitionBundle(schedules=[{'id':'s','rules':[{'day_types':'MoonDay',
            'start_date':'2000-01-01','end_date':'2000-12-31','values':[1]}]}])
        self.assertTrue(validate(bundle).errors)

    def test_duplicate_resources_are_rejected(self):
        bundle=DefinitionBundle(materials=[{'id':'m'},{'id':'m'}])
        self.assertTrue(validate(bundle).errors)


if __name__=='__main__':unittest.main()
