"""Unconditioned attics in the unified constructions (ADR 0065): roles, the attic-omitted roof, the inventory."""
import collections
import hashlib
import json
import math
import unittest

from scripts import atlas_contracts, atlas_exports, attic_boundary

SMALL_OFFICE = '90-1-2019.small-office-detailed.construction-package.7eee9d'
# The release 2.5.0 package BEMGen consumed (zoning sweep inputs), byte for byte.
FIXTURE_SHA256 = 'e75d30ac282c1f0ca1e7d1e0608f02b85b041cc8a744dafced81566590a1da0b'
DECK, FLOOR, SOFFIT = ('90-1-2019.typical-uninsulated-wood-joist-attic-roof.c5b0de',
                       '90-1-2019.typical-wood-joist-attic-floor.fe2a18', '90-1-2019.typical-attic-soffit.f07970')
CEILING = '90-1-2019.typical-interior-ceiling.e4b01c'
SMALL_OFFICE_ERAS = ('90-1-2019.small-office-detailed.construction-package.7eee9d',
                     '90-1-2007.small-office-detailed.construction-package.b1ba8a',
                     'doe-ref-1980-2004.small-office-detailed.construction-package.8575fa',
                     'doe-ref-pre-1980.small-office-detailed.construction-package.db34c2')
# Contexts with a recognised attic in release 2.5.0, by family (attic_inventory, 2026-11-09).
COUNTS = {'openstudio_standards_rules': 568, 'pnnl_idf': 342, 'resstock': 16}


class AtticBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = atlas_exports.Release(release='2.5.0')
        cls.unified = cls.release.construction(SMALL_OFFICE, '4-a', 'unified')
        cls.detailed = cls.release.constructions.export(SMALL_OFFICE, '4-a', 'detailed')
        cls.document, cls.found = attic_boundary.augment(cls.detailed, cls.unified)

    def test_unified_4_0_0_export_is_the_consumed_fixture(self):
        self.assertEqual(hashlib.sha256(attic_boundary.document_bytes(self.unified)).hexdigest(), FIXTURE_SHA256)

    def test_small_office_roles(self):
        fam, found = attic_boundary.recognise(self.detailed, self.unified)
        self.assertEqual((fam, sorted(found)), ('openstudio_standards_rules', ['Attic']))
        parts = found['Attic']
        self.assertEqual([r['assembly_id'] for r in parts['exterior']['ExteriorRoof']], [DECK])
        self.assertEqual([r['assembly_id'] for r in parts['exterior']['ExteriorFloor']], [SOFFIT])
        self.assertEqual(list(parts['conditioned_boundary']), ['InteriorFloor'])
        self.assertEqual([r['assembly_id'] for r in parts['conditioned_boundary']['InteriorFloor']], [FLOOR])
        attic, = self.document['attics']
        self.assertEqual(attic['conditioned_boundary']['zone_side'], {'orientation': 'reverse_layers', 'zone_role': 'InteriorCeiling'})
        self.assertAlmostEqual(attic['area_ratio_roof_to_boundary'], 598.76168/511.15624589999993, places=12)
        roof_note, = self.document['components']['ExteriorRoof']['attics']
        self.assertEqual((roof_note['part'], roof_note['share_of_component_reference_area']), ('exterior', 1.0))
        # The source rule for a roof over an occupied space is the attic floor construction (zero reference area).
        self.assertEqual(attic['source_default_exterior_roof']['assembly_id'], FLOOR)

    def test_interior_ceiling_correction(self):
        correction, = self.document['export_corrections']
        self.assertEqual(correction['status'], 'corrected')
        self.assertEqual(correction['stored'], self.unified['components']['InteriorCeiling']['derivation'])
        self.assertEqual(self.document['components']['InteriorCeiling']['derivation'],
                         {'contributors': [{'assembly_id': CEILING, 'weight': 1., 'reference_area_m2': 0.}],
                          'source_reference_area_m2': 0., 'weight_basis': 'unique_source_recipe_without_reference_exposure'})
        # The recipe and every other component are the stored ones.
        self.assertEqual(self.document['components']['InteriorCeiling']['assembly_id'],
                         self.unified['components']['InteriorCeiling']['assembly_id'])
        for role in ('FloorDistributedMass', 'InteriorFloor', 'ExteriorRoof'):
            stored = {k: v for k, v in self.unified['components'][role].items()}
            self.assertEqual({k: v for k, v in self.document['components'][role].items() if k != 'attics'}, stored)

    def test_attic_omitted_roof_against_hand_calculation(self):
        attic, = self.document['attics']
        eq = attic['attic_omitted_roof']
        assembly = self.document['assemblies'][eq['assembly_id']]
        # Source layers (openstudio-standards 90.1-2019, climate zone 4).
        shingles = (0.00319999999999998/0.04, 0.00319999999999998*1120.*1260.)
        plywood = (0.0159/0.12, 0.0159*543.999999999999*1210.)
        gypsum = (0.0159/0.159999999999999, 0.0159*799.999999999999*1090.)
        insulation = 8.09838632642688
        n = 598.76168/511.15624589999993
        u_roof = 1/(shingles[0]+plywood[0]+0.04+0.13)
        u_ceiling = 1/(insulation+gypsum[0]+0.13+0.13)
        u = 1/(1/u_ceiling+1/(n*u_roof))   # ASHRAE ceiling-roof combination
        c = n*(shingles[1]+plywood[1])+gypsum[1]
        self.assertTrue(math.isclose(assembly['targets']['u_reference_W_m2_K'], u, rel_tol=1e-12))
        self.assertTrue(math.isclose(assembly['targets']['capacity_J_m2_K'], c, rel_tol=1e-12))
        self.assertTrue(math.isclose(u, 0.1138394978, rel_tol=1e-9))
        fitted = assembly['layers']
        self.assertTrue(math.isclose(math.fsum(l['R'] for l in fitted)+0.17, 1/u, rel_tol=1e-12))
        self.assertTrue(math.isclose(math.fsum(l['C'] for l in fitted), c, rel_tol=1e-12))
        bounds = eq['u_bounds_W_m2_K']
        self.assertTrue(math.isclose(bounds['boundary_only_attic_at_outdoor_temperature'], u_ceiling, rel_tol=1e-12))
        self.assertLess(bounds['equivalent_sealed_roof_only'], bounds['sealed_all_exterior_parts'])
        self.assertLess(bounds['sealed_all_exterior_parts'], bounds['boundary_only_attic_at_outdoor_temperature'])
        self.assertEqual(assembly['surface_properties']['exterior']['roughness'], 'VeryRough')   # the shingles outermost
        self.assertEqual(assembly['fit']['films_m2_K_W'], [0.04, 0.13])
        self.assertIn(assembly['quality'], ('within_initial_screen', 'approximation_review'))

    def test_schema_4_1_0_is_additive(self):
        self.assertEqual(self.document['schema_version'], '4.1.0')
        self.assertEqual(atlas_exports.schema_errors(atlas_contracts.UNIFIED_ATTICS[0], self.document), [])
        plain = dict(self.unified, schema_version='4.1.0')
        self.assertEqual(atlas_exports.schema_errors(atlas_contracts.UNIFIED_ATTICS[0], plain), [])

    def test_every_small_office_era(self):
        for sid in SMALL_OFFICE_ERAS:
            for key in ('4-a', '7-a'):
                with self.subTest(sid=sid, key=key):
                    document, found = attic_boundary.export(self.release, sid, key)
                    attic, = document['attics']
                    self.assertEqual(attic['attic_omitted_roof']['status'], 'ready')
                    self.assertEqual(document['export_corrections'][0]['status'], 'corrected')
                    bounds = attic['attic_omitted_roof']['u_bounds_W_m2_K']
                    self.assertLess(bounds['equivalent_sealed_roof_only'], bounds['boundary_only_attic_at_outdoor_temperature'])

    def test_contexts_without_an_attic_are_unchanged(self):
        sid = '90-1-2019.medium-office-detailed.construction-package.'
        sid = next(s for s in self.release.constructions.sets if s.startswith(sid))
        unified = self.release.construction(sid, '4-a', 'unified')
        detailed = self.release.constructions.export(sid, '4-a', 'detailed')
        document, found = attic_boundary.augment(detailed, unified)
        self.assertEqual(found, {})
        self.assertEqual(dict(document, schema_version=unified['schema_version']), unified)


class AtticInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = atlas_exports.Release(release='2.5.0')
        cls.candidates = attic_boundary.candidates(cls.release)

    def test_counts_by_family(self):
        stored = self.release.constructions
        counts = collections.Counter(attic_boundary.family(stored.export(s, k, 'detailed')) for s, k in self.candidates)
        self.assertEqual(dict(counts), COUNTS)

    def test_every_attic_rule_with_a_roof_is_inventoried(self):
        """Independent of recognise(): an Attic-space-type, attic-named or attic-adjacent ExteriorRoof rule whose assembly
        has reference area in the unified ExteriorRoof is in the inventory, and nothing else is."""
        stored = self.release.constructions
        expected = set()
        for sid, key in attic_boundary.contexts(self.release):
            detailed = stored.export(sid, key, 'detailed')
            unified = stored.export(sid, key, 'unified')
            areas = {r['assembly_id']: r['reference_area_m2'] for r in
                     ((unified['components'].get('ExteriorRoof') or {}).get('derivation') or {}).get('contributors', [])}
            for a in detailed['components']['ExteriorRoof']['assignments']:
                w = a['when']
                named = 'attic' in (detailed['assemblies'][a['assembly_id']].get('name') or '').lower() and sid.startswith('iecc-')
                if (w.get('space_type') == 'Attic' or named or str(w.get('interior_space_type')).startswith('attic')) \
                        and areas.get(a['assembly_id'], 0) > 0:
                    expected.add((sid, key))
        self.assertEqual(set(self.candidates), expected)

    def test_inventory_rows_for_the_small_office_fixture(self):
        rows = attic_boundary.inventory_rows(self.release, lambda s, k: s == SMALL_OFFICE and k == '4-a')
        row, = rows
        self.assertEqual(row['package_sha256_4_0_0'], FIXTURE_SHA256)
        self.assertEqual((row['roof_assembly_ids'], row['boundary_assembly_ids'], row['boundary_role']), (DECK, FLOOR, 'InteriorFloor'))
        self.assertTrue(math.isclose(row['roof_u_W_m2_K'], 2.614379084967324, rel_tol=1e-12))
        self.assertTrue(math.isclose(row['boundary_u_W_m2_K'], 0.11823459676917443, rel_tol=1e-12))
        self.assertEqual(json.loads(json.dumps(row)), row)


if __name__ == '__main__':
    unittest.main()
