import unittest
from scripts.definition_compare import compare_elements


class ComparisonTests(unittest.TestCase):
    def test_equal_u_with_different_mass_is_not_identity(self):
        result = compare_elements('construction', {'u': .5, 'layers': [{'density': 10}]},
                                  {'u': .5, 'layers': [{'density': 20}]})
        self.assertFalse(result['identity'])
        self.assertEqual(len(result['differences']), 1)

    def test_unknowns_prevent_identity(self):
        self.assertFalse(compare_elements('hvac_system', {'cop': None}, {'cop': None})['identity'])

    def test_similarity_uses_explicit_tolerance(self):
        report = compare_elements('hvac_system', {'cop': 3}, {'cop': 3.01}, {'cop': .02})
        self.assertFalse(report['identity'])
        self.assertTrue(report['similar'])


if __name__ == '__main__': unittest.main()
