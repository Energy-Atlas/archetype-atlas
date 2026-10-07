import unittest
from scripts.definition_contract import load_context
from scripts.definitions import build
from scripts.definition_validate import validate


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=build(load_context())

    def test_three_primary_kinds_are_populated_and_valid(self):
        for table in ('programs','constructions','hvac_systems'):
            self.assertTrue(self.bundle[table])
        self.assertEqual(validate(self.bundle).errors, [])

    def test_invalid_evidence_reference_is_rejected(self):
        import copy
        bundle=copy.deepcopy(self.bundle)
        bundle['programs'][0]['loads'][0]['evidence_id']='missing'
        self.assertTrue(validate(bundle).errors)


if __name__=='__main__': unittest.main()
