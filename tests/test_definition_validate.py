import unittest
from scripts.definition_contract import DefinitionBundle, parameter
from scripts.definition_validate import validate


class ValidationTests(unittest.TestCase):
    def test_invalid_schedule_rule_is_rejected(self):
        bundle=DefinitionBundle(schedules=[{'id':'s','rules':[{'day_types':'MoonDay',
            'start_date':'2000-01-01','end_date':'2000-12-31','values':[1]}]}])
        self.assertTrue(validate(bundle).errors)

    def test_duplicate_resources_are_rejected(self):
        bundle=DefinitionBundle(materials=[{'id':'m'},{'id':'m'}])
        self.assertTrue(validate(bundle).errors)


if __name__=='__main__':unittest.main()
