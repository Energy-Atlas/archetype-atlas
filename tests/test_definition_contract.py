import copy
import tempfile
import unittest
from pathlib import Path

from scripts import definition_contract as contract


class ContractTests(unittest.TestCase):
    def record(self):
        return {'id': 'program-test', 'kind': 'program', 'name': 'Office',
                'building_type': 'MediumOffice', 'template': '90.1-2019',
                'source_family': 'code_prototype_rules', 'gate': ['nonresidential'],
                'evidence_view': 'source', 'derivation': 'composed',
                'parameters': {'lighting': contract.parameter(None, 'W/m2', 'evidence-test')},
                'evidence_ids': ['evidence-test'], 'required_inputs': []}

    def test_unknown_survives_composed_source_view(self):
        row = self.record()
        contract.validate_record('program', row)
        self.assertIsNone(row['parameters']['lighting']['value'])
        self.assertEqual(row['parameters']['lighting']['status'], 'unknown')

    def test_missing_parameter_evidence_is_rejected(self):
        row = self.record()
        row['parameters']['lighting'] = {'value': 10, 'unit': 'W/m2', 'status': 'known'}
        with self.assertRaises(contract.DefinitionError):
            contract.validate_record('program', row)

    def test_supporting_kind_cannot_be_queried_as_primary(self):
        with self.assertRaises(contract.DefinitionError):
            contract.validate_record('schedule', self.record())

    def test_ids_ignore_dictionary_order(self):
        self.assertEqual(contract.stable_id('component', {'x': 1, 'y': 2}),
                         contract.stable_id('component', {'y': 2, 'x': 1}))

    def test_locked_file_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'input.json'
            path.write_bytes(b'changed')
            with self.assertRaises(contract.DefinitionError):
                contract.verify_locked(path, {'sha256': '0'*64, 'size_bytes': 7})

    def test_evidence_requires_original_and_interpretation(self):
        evidence = {'id': 'evidence-x', 'locator': 'row 1'}
        with self.assertRaises(contract.DefinitionError):
            contract.validate_evidence(evidence)


if __name__ == '__main__':
    unittest.main()
