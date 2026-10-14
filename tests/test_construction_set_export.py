"""Migration checks for unified, selected construction-set review exports."""
import copy
import importlib
import unittest
from scripts.common import ROOT,load_json


class ConstructionSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue=load_json(ROOT/'data/construction-releases/v1.0.0/catalogue.json')
        cls.medium=next(i for i,p in cls.catalogue['packages'].items() if p['building_type']=='MediumOffice' and p['template']=='90.1-2019' and p['space_type'] is None)
        cls.residential=next(i for i,p in cls.catalogue['enclosures'].items() if p['source_fixture_id']=='residential_archetype-0157cd8578ba44bf8a77')

    def export(self,identity=None,climate='4A',reference=None):
        module=importlib.import_module('scripts.construction_set_export')
        return module.export_set(self.catalogue,identity or self.medium,climate,reference)

    def test_one_set_contains_exterior_and_interior_components(self):
        p=self.export()
        self.assertEqual(p['kind'],'construction_set')
        self.assertTrue(p['components']['ExteriorWall']['assignments'])
        self.assertTrue(p['components']['InteriorWall']['assignments'])
        self.assertTrue(p['components']['ExteriorRoof']['assignments'])
        self.assertNotIn('packages',p);self.assertNotIn('enclosures',p)

    def test_header_matches_program_source_semantics(self):
        p=self.export()
        for k in ['schema_version','kind','export_mode','id','name','scope','source','metadata']:
            self.assertIn(k,p)
        self.assertEqual(p['source']['building_type'],'MediumOffice')
        self.assertEqual(p['source']['climate'],{'status':'exact','value':'4A'})
        self.assertEqual(p['source']['vintage']['kind'],'source_template')
        self.assertEqual(p['source']['construction_set_id'],self.medium)

    def test_consumer_contract_has_no_generic_binding_or_deferred_scope_fields(self):
        def walk(node):
            if isinstance(node,dict):
                self.assertNotIn('required_bindings',node);self.assertNotIn('deferred_scope',node)
                for k,v in node.items():
                    if k!='original_value':walk(v)
            elif isinstance(node,list):
                for v in node:walk(v)
        walk(self.export());walk(self.export(self.residential,'5A'))

    def test_selected_physics_and_fixed_ach_are_unchanged(self):
        p=self.export()
        old=self.catalogue['packages'][self.medium]['infiltration']['reference_variants'][0]['climates']['4A']
        self.assertEqual(p['infiltration']['natural_ach'],old)
        for identity,a in p['assemblies'].items():
            original=copy.deepcopy(self.catalogue['assemblies'][identity]);original.pop('required_bindings')
            self.assertEqual(a,original)
        for identity,m in p['materials'].items():
            self.assertEqual(m,self.catalogue['materials'][identity])

    def test_plenum_override_is_inside_building_set(self):
        p=self.export()
        assignments=p['components']['InteriorFloor']['assignments']
        self.assertTrue(any(a['when'].get('space_type')=='Plenum' for a in assignments))
        self.assertTrue(any(a['when'].get('scope')=='building_default' for a in assignments))
        # Compatibility-only Office lookup must not replace the SteelFramed wall.
        walls=p['components']['ExteriorWall']['assignments']
        self.assertEqual(len(walls),1)
        self.assertEqual(walls[0]['assembly_id'],'construction-54616b459dd2d45e52c4f89f')

    def test_residential_uses_same_interface_and_retains_geometry_rules(self):
        p=self.export(self.residential,'5A')
        self.assertEqual(p['scope'],'whole_dwelling')
        self.assertEqual(p['source']['vintage']['kind'],'stock_vintage')
        self.assertEqual(set(p['components']),set(self.export()['components']))
        roofs=p['components']['ExteriorRoof']['assignments']
        self.assertEqual(roofs[0]['geometry']['roof']['source_pitch_rad'],0.4636476090008061)
        partitions=p['components']['InteriorPartition']['assignments']
        self.assertEqual(partitions[0]['geometry']['area']['method'],'source_partition_cfa_scaling')
        windows=p['components']['ExteriorWindow']['assignments']
        self.assertEqual(len(windows),5)
        self.assertTrue(all(a['when']['interior_space_type']=='conditioned space' for a in windows))
        self.assertTrue(all('overhang' in a['geometry'] for a in windows))

    def test_unsupported_context_and_unselected_reference_are_errors(self):
        with self.assertRaises(ValueError):self.export(self.residential,'3D')
        generic=next(i for i,p in self.catalogue['packages'].items() if p['building_type']=='Office' and p['template']=='90.1-2019')
        with self.assertRaisesRegex(ValueError,'reference'):self.export(generic)
        old=next(i for i,p in self.catalogue['packages'].items() if p['building_type']=='MediumOffice' and p['template']=='DOE Ref Pre-1980')
        with self.assertRaisesRegex(ValueError,'climate'):self.export(old,'0A')

    def test_index_preserves_all_source_set_identities(self):
        module=importlib.import_module('scripts.construction_set_export')
        index=module.build_index(self.catalogue)
        self.assertEqual(set(index['construction_sets']),set(self.catalogue['packages'])|set(self.catalogue['enclosures']))
        self.assertEqual(len(index['construction_sets']),224)

    def test_component_targets_are_schema_controlled(self):
        p=self.export()
        self.assertEqual(p['components']['ExteriorWall']['target'],{'surface_type':'Wall','boundary_conditions':['Outdoors']})
        self.assertEqual(p['components']['InteriorWall']['target'],{'surface_type':'Wall','boundary_conditions':['Surface','Adiabatic']})
        p['components']['ExteriorWall']['target']={'surface_type':'Floor','boundary_conditions':['Outdoors']}
        module=importlib.import_module('scripts.construction_set_validation')
        with self.assertRaises(module.ValidationError):module.validate_set(p)

    def test_residential_parent_adjacency_has_source_evidence(self):
        p=self.export(self.residential,'5A')
        a=p['components']['ExteriorWindow']['assignments'][0]
        proofs=[p['evidence'][i] for i in a['evidence_ids']]
        self.assertTrue(any('context' in e['source_locator'] for e in proofs))

    def test_assignment_cannot_move_a_wall_recipe_to_a_roof_component(self):
        p=self.export();misplaced=copy.deepcopy(p['components']['ExteriorWall']['assignments'][0])
        misplaced['id']+=':misplaced';p['components']['ExteriorRoof']['assignments'].append(misplaced)
        module=importlib.import_module('scripts.construction_set_validation')
        with self.assertRaisesRegex(ValueError,'role'):module.validate_set(p)

    def test_generic_and_partial_sources_preserve_selected_scope(self):
        generic=next(i for i,p in self.catalogue['packages'].items() if p['building_type']=='Office' and p['template']=='90.1-2019')
        p=self.export(generic,reference='90.1-2019/MediumOffice')
        self.assertEqual(p['source']['building_type'],'Office')
        self.assertEqual(p['infiltration']['reference_id'],'90.1-2019/MediumOffice')
        partial=next(i for i,p in self.catalogue['packages'].items() if p['building_type']=='Any' and p['space_type']=='Plenum' and p['template']=='90.1-2019')
        p=self.export(partial,reference='90.1-2019/MediumOffice')
        self.assertEqual(p['scope'],'space_type')
        self.assertEqual(p['source']['space_type'],'Plenum')
        self.assertEqual(p['components']['ExteriorWall']['disposition'],'source_absent')

    def test_native_attic_floor_source_role_override_is_supported(self):
        p=self.export('construction-1c483cc0afb7007ae7fb9bd5',reference='90.1-2019/FullServiceRestaurant')
        rules=p['components']['InteriorFloor']['assignments']
        attic=next(a for a in rules if a['when'].get('space_type')=='Attic')
        self.assertEqual(p['assemblies'][attic['assembly_id']]['role'],'ExteriorRoof')
        self.assertEqual(attic['source_selector'],'interior_floors')

    def test_all_source_geometry_conventions_are_protected(self):
        original=self.export(self.residential,'5A')
        module=importlib.import_module('scripts.construction_set_validation')
        def partition(p):p['components']['InteriorPartition']['assignments'][0]['geometry']['area']={'method':'bem_surface_area','unit':'m2'}
        def interstory(p):p['components']['InteriorFloor']['assignments'][0]['geometry']['area']={'method':'bem_surface_area','unit':'m2'}
        def reversal(p):p['components']['InteriorCeiling']['assignments'][0]['geometry']['layers']['source_reference_reversed']=False
        def film(p):p['components']['ExteriorRoof']['assignments'][0]['geometry']['roof']['source_film_rule']='different formula'
        for mutate in (partition,interstory,reversal,film):
            with self.subTest(mutation=mutate.__name__):
                p=copy.deepcopy(original);mutate(p)
                with self.assertRaisesRegex(ValueError,'geometry'):module.validate_set(p)

    def test_schema_requires_space_conditions_and_consistent_root_scope(self):
        from jsonschema import Draft202012Validator,ValidationError
        schema=Draft202012Validator(load_json(ROOT/'schemas/construction-json-v2.schema.json'))
        p=self.export()
        rule=p['components']['InteriorFloor']['assignments'][0]
        rule['when']={'scope':'space_type'}
        with self.assertRaises(ValidationError):schema.validate(p)
        p=self.export(self.residential,'5A');p['scope']='space_type';p['source']['space_type']='Plenum'
        with self.assertRaises(ValidationError):schema.validate(p)

    def test_invalid_component_and_orphan_references_are_rejected(self):
        module=importlib.import_module('scripts.construction_set_validation')
        def missing_component(p):p['components'].pop('InteriorWall')
        def wrong_component(p):p['components']['MysteryWall']=p['components'].pop('InteriorWall')
        def orphan_assembly(p):p['components']['ExteriorWall']['assignments'][0]['assembly_id']='missing'
        def orphan_evidence(p):p['components']['ExteriorWall']['assignments'][0]['evidence_ids']=['missing']
        def binding(p):p['required_bindings']=['climate_zone']
        for mutate in (missing_component,wrong_component,orphan_assembly,orphan_evidence,binding):
            with self.subTest(mutation=mutate.__name__):
                p=self.export();mutate(p)
                with self.assertRaises((ValueError,module.ValidationError)):module.validate_set(p)


if __name__=='__main__':unittest.main()
