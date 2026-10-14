"""Focused leakage reference geometry checks; no catalogue/site build."""
import copy
import json
from pathlib import Path
import unittest

from scripts.recover_construction_geometry import normalize_residential, package_references, validate, canonical_derived


class GeometryRecoveryTests(unittest.TestCase):
    def test_derived_geometry_canonicalizes_binary_noise_but_preserves_physical_differences(self):
        self.assertEqual(canonical_derived({'area':7084.013168674086}),
                         canonical_derived({'area':7084.013168674087}))
        self.assertNotEqual(canonical_derived({'area':7084.013168674086}),
                            canonical_derived({'area':7084.023168674086}))
        # Native SDK polyhedron accumulation varies more than the area sums.
        self.assertEqual(canonical_derived({'volume':504.6157552134254}),
                         canonical_derived({'volume':504.6157552142088}))

    def test_apartment_height_is_unit_height_and_total_leakage_retains_exposure(self):
        # Catches building storeys used as unit height and missing a_ext conversion.
        raw = {'record_id': 'apartment', 'geometry': {'cfa_ft2': 1000, 'volume_ft3': 8000,
            'infiltration_volume_ft3': 8000, 'infiltration_height_ft': 8,
            'unit_height_above_grade_ft': 0, 'compartment_total_area_ft2': 2500,
            'compartment_exterior_area_ft2': 500, 'a_ext': .2, 'ach50': 5,
            'pressure_pa': 50, 'infiltration_type': 'unit total',
            'conditioned_floors_above_grade': 1, 'source_building_floors': 15}}
        result = normalize_residential(raw, 'proof')
        self.assertAlmostEqual(result['fields']['infiltration_height_m']['value'], 2.4384)
        self.assertAlmostEqual(result['fields']['infiltration_volume_m3']['value'], 226.534772736)
        self.assertEqual(result['fields']['exterior_ach50_per_s']['value'], 1/3600)
        self.assertEqual(result['fields']['a_ext']['value'], .2)
        self.assertEqual(result['fields']['pressure_Pa']['value'], 50)

    def test_generic_reference_matching_does_not_copy_other_template_or_space_scope(self):
        # Catches wildcard substitution of a generic package's space scope.
        package = {'template': '90.1-2019', 'source_set': {'building_type': 'Any',
            'space_type': 'Attic', 'template': '90.1-2019'}}
        query = {'building_type': 'Any', 'space_type': 'Attic', 'template': '90.1-2019'}
        cases = [{'id': 'house', 'template': '90.1-2019', 'selected_sets': [query]},
                 {'id': 'plenum', 'template': '90.1-2019', 'selected_sets': [{**query, 'space_type':'Plenum'}]},
                 {'id': 'old', 'template': '90.1-2007', 'selected_sets': [query]}]
        self.assertEqual(package_references(package, cases), ['house'])

    def test_invalid_exposure_is_rejected_instead_of_clamped(self):
        with self.assertRaisesRegex(ValueError, 'exposure'):
            normalize_residential({'record_id': 'bad', 'geometry': {'a_ext': 1.2}}, 'proof')

    def test_validation_rejects_missing_geometry_and_orphan_mapping(self):
        packet = {'residential': [], 'commercial': [], 'package_mappings': [
            {'package_id': 'p', 'reference_ids': ['missing']}], 'evidence': {}}
        with self.assertRaisesRegex(ValueError, 'Orphan'):
            validate(packet)
        packet['package_mappings'] = []
        packet['residential'] = [{'id': 'r', 'fields': {}, 'evidence_id': 'proof'}]
        packet['evidence']['proof'] = {}
        with self.assertRaisesRegex(ValueError, 'Missing geometry'):
            validate(packet)

    def test_unmapped_package_requires_an_explicit_evidence_backed_disposition(self):
        packet = {'residential': [], 'commercial': [], 'package_mappings': [
            {'package_id':'missing', 'reference_ids':[]}], 'evidence':{}}
        with self.assertRaisesRegex(ValueError, 'Unresolved package'):
            validate(packet)

    def test_recovered_packet_retains_smallhotel_residential_story_override(self):
        packet = json.loads(Path('data/construction-inputs/geometry-v1.json').read_text())
        packages = json.loads(Path('data/definition-releases/v0.1.1/constructions.json').read_text())
        package = next(p for p in packages if p.get('representation') == 'package'
            and p['building_type'] == 'SmallHotel' and p['template'] == '90.1-2007'
            and p.get('space_type') is None and p['source_set'].get('is_residential') == 'Yes')
        mapping = next(m for m in packet['package_mappings'] if m['package_id'] == package['id'])
        self.assertEqual(mapping['reference_ids'], ['90.1-2007/SmallHotel'])

    def test_recovered_packet_preserves_reported_medium_office_terrain(self):
        packet = json.loads(Path('data/construction-inputs/geometry-v1.json').read_text())
        medium = next(c for c in packet['commercial'] if c['id'] == '90.1-2019/MediumOffice')
        self.assertEqual(medium['source_site_terrain'], 'City')


if __name__ == '__main__':
    unittest.main()
