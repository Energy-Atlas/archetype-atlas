"""Focused independent construction contract checks."""
import copy
import importlib
import unittest


class ConstructionExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validation = importlib.import_module('scripts.construction_validation')
        cls.export = importlib.import_module('scripts.construction_export')

    def test_native_glazing_autocalculation_does_not_invent_visible_transmittance(self):
        p = {'model':'SimpleGlazing','u_W_m2_K':2,'shgc':.4,
             'visible_transmittance_mode':'energyplus_autocalculate_from_shgc'}
        self.validation.validate_material(p)
        p.pop('visible_transmittance_mode')
        with self.assertRaisesRegex(ValueError,'transmittance'):
            self.validation.validate_material(p)

    def test_detailed_glazing_requires_conductivity_and_optical_fields(self):
        with self.assertRaisesRegex(ValueError,'conductivity'):
            self.validation.validate_material({'model':'StandardGlazing','thickness_m':.006})

    def test_massless_and_airgap_are_complete_without_fabricated_mass(self):
        p={'model':'MasslessOpaqueMaterial','resistance_m2_K_W':2,'roughness':'Smooth',
           'thermal_absorptance':.9,'solar_absorptance':0,'visible_absorptance':0}
        self.validation.validate_material(p)
        self.validation.validate_material({'model':'AirGap','resistance_m2_K_W':.18})
        metrics=self.export.opaque_metrics([p])
        self.assertEqual(metrics['layer_resistance_m2_K_W'],2)
        self.assertNotIn('areal_heat_capacity_J_m2_K',metrics)

    def test_invalid_numeric_physics_and_fraction_are_rejected(self):
        for shgc in (True,1.1,-.1,float('nan')):
            with self.assertRaises(ValueError):
                self.validation.validate_material({'model':'SimpleGlazing','u_W_m2_K':2,
                    'shgc':shgc,'visible_transmittance':.5})

    def test_climate_groups_preserve_full_labels_and_reject_unrecognized_context(self):
        self.assertTrue(self.export.climate_matches('ClimateZone 3','3C'))
        self.assertFalse(self.export.climate_matches('ClimateZone 3B','3C'))
        self.assertTrue(self.export.climate_matches('ClimateZone 3C','3C'))
        with self.assertRaises(ValueError):
            self.export.climate_matches('ClimateZone 3','3D')

    def test_selector_requires_source_order_policy_for_distinct_physics(self):
        assemblies={'a':{'id':'a','climate_group':'ClimateZone 4','layers':[{'order':0,'material_id':'m1'}]},
                    'b':{'id':'b','climate_group':'ClimateZone 4','layers':[{'order':0,'material_id':'m2'}]}}
        materials={'m1':{'model':'AirGap','properties':{'resistance_m2_K_W':.2}},
                   'm2':{'model':'AirGap','properties':{'resistance_m2_K_W':.3}}}
        selector={'elements':['a','b'],'disposition':'resolved_source_context'}
        with self.assertRaisesRegex(ValueError,'Ambiguous'):
            self.export.resolve_selector(selector,assemblies,materials,'4A')
        selector['source_default_order']=['b','a']
        self.assertEqual(self.export.resolve_selector(selector,assemblies,materials,'4A')['selected_id'],'b')
        selector['elements']=[]
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            self.export.resolve_selector(selector,assemblies,materials,'4A')

    def test_census_cannot_claim_completeness_by_dropping_an_eligible_identity(self):
        with self.assertRaisesRegex(ValueError,'missing'):
            self.validation.validate_inventory({'a'}, {'a','b'})
        with self.assertRaisesRegex(ValueError,'orphan'):
            self.validation.validate_inventory({'a','b'}, {'a'})

    def test_imported_provenance_keeps_referenced_source_evidence_resolvable(self):
        def proof(original):
            return {'source_sha256':'a'*64,'source_locator':'source.rb#method',
                    'source_revision':'pinned','original_value':original,'original_unit':'m',
                    'transformation':'identity','extraction_date':'2026-10-14','interpretation_note':'source'}
        resources=self.export.Resources({'root':proof({'source_layer_evidence_ids':['layer']}),
                                         'layer':proof(1)})
        identity=resources.proof({'evidence_id':'root'})
        refs=resources.evidence[identity]['original_value']['source_layer_evidence_ids']
        self.assertTrue(set(refs)<=set(resources.evidence))

    def test_package_selection_uses_declared_reference_and_rejects_unsupported_context(self):
        # Multiple reference forms must not be silently collapsed to one ACH.
        payload={'packages':{'p':{'id':'p','supported_climates':['4A'],
            'infiltration':{'reference_variants':[{'reference_id':'r1','climates':{}},
                                                {'reference_id':'r2','climates':{}}]}}}}
        with self.assertRaisesRegex(ValueError,'reference variant'):
            self.export.select_package(payload,'p','4A')
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            self.export.select_package(payload,'p','0A','r1')

    def test_readiness_rejects_broken_pilot_dependencies_and_provenance(self):
        from scripts.common import ROOT,load_json
        original=load_json(ROOT/'data/construction-releases/v1.0.0/examples/medium-office.json')
        def missing_slot(p):
            next(iter(p['packages'].values()))['selectors'].pop('exterior_roof')
        def orphan_order(p):
            s=next(iter(p['packages'].values()))['selectors']['exterior_roof']
            s['selection_policy']['source_order'][0]['element_ids']=['missing']
        def orphan_parameter(p):
            a=next(a for a in p['assemblies'].values() if a['source_parameters'])
            next(iter(a['source_parameters'].values()))['evidence_id']='missing'
        def orphan_adjustment(p):
            a=next(a for a in p['assemblies'].values() if a['target_adjustment'])
            a['target_adjustment']['evidence_id']='missing'
        def bad_climate(p):
            next(iter(p['packages'].values()))['supported_climates'].append('9Z')
        def orphan_package_proof(p):
            next(iter(p['packages'].values()))['evidence_ids']=['missing']
        def orphan_deferred_proof(p):
            next(iter(p['packages'].values()))['deferred_selectors']['ground_contact_floor']['evidence_id']='missing'
        for mutation in (missing_slot,orphan_order,orphan_parameter,orphan_adjustment,bad_climate,orphan_package_proof,orphan_deferred_proof):
            with self.subTest(mutation=mutation.__name__):
                p=copy.deepcopy(original);mutation(p)
                with self.assertRaises(ValueError):
                    self.validation.validate_catalogue(p,p['inventory']['eligible_ids'])


if __name__=='__main__':
    unittest.main()
