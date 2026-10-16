"""Frozen normalized catalogue and standalone context hydration checks."""
import copy
import importlib
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from scripts.common import ROOT,load_json
from scripts.construction_set_export import LIBRARY,export_set,input_hashes


class ConstructionReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalogue=load_json(LIBRARY/'catalogue.json');hashes=input_hashes()
        medium=next(i for i,p in catalogue['packages'].items() if p['building_type']=='MediumOffice' and p['template']=='90.1-2019' and p['space_type'] is None)
        residential=next(i for i,p in catalogue['enclosures'].items() if p['source_fixture_id']=='residential_archetype-0157cd8578ba44bf8a77')
        cls.examples=[export_set(catalogue,medium,'4A',hashes=hashes),export_set(catalogue,residential,'5A',hashes=hashes)]
        cls.catalogue=catalogue

    def test_normalized_hydration_exactly_reproduces_standalone_documents(self):
        module=importlib.import_module('scripts.construction_set_release')
        builder=module.ReleaseBuilder()
        for p in self.examples:builder.add(p)
        packed=builder.finish()
        self.assertNotIn('packages',packed);self.assertNotIn('enclosures',packed)
        for p in self.examples:self.assertEqual(module.hydrate_context(packed,p['id']),p)

    def test_hydration_retains_resource_and_source_evidence_closure(self):
        module=importlib.import_module('scripts.construction_set_release')
        builder=module.ReleaseBuilder();builder.add(self.examples[0]);p=builder.finish()
        aid=next(iter(p['assemblies']));p['assemblies'].pop(aid)
        with self.assertRaises((ValueError,KeyError)):module.hydrate_context(p,self.examples[0]['id'])

    def test_completeness_rejects_dropped_context_or_assembly(self):
        module=importlib.import_module('scripts.construction_set_release')
        builder=module.ReleaseBuilder()
        for p in self.examples:builder.add(p)
        packed=builder.finish()
        with self.assertRaisesRegex(ValueError,'context|definition'):module.reconcile(packed,self.catalogue)

    def test_duplicate_context_with_different_content_is_rejected(self):
        module=importlib.import_module('scripts.construction_set_release')
        builder=module.ReleaseBuilder();builder.add(self.examples[0])
        p=copy.deepcopy(self.examples[0]);p['infiltration']['natural_ach']['value']*=2
        with self.assertRaisesRegex(ValueError,'identity|collision'):builder.add(p)

    def test_explicit_hydration_matches_direct_policy_and_repeated_story_scopes(self):
        module=importlib.import_module('scripts.construction_set_release')
        hashes=input_hashes()
        cases=[(self.examples[0]['source']['construction_set_id'],'interior_walls',False),
               ('construction-065e2be2332c15d04a224fe3','exterior_skylight',True)]
        hotel=next(i for i,p in self.catalogue['packages'].items() if p['building_type']=='SmallHotel' and p['template']=='90.1-2007' and p['space_type'] is None)
        cases.append((hotel,'interior_walls',False))
        for identity,selector,alternative in cases:
            with self.subTest(identity=identity,selector=selector):
                default=export_set(self.catalogue,identity,'4A',hashes=hashes)
                builder=module.ReleaseBuilder();builder.add(default);packed=builder.finish()
                decision=next(d for d in default['metadata']['selection_decisions'] if d['source_selector']==selector)
                candidates=decision['candidate_element_ids']
                chosen=next(i for i in candidates if i not in decision['resolved_climate_selection']['element_ids']) if alternative else candidates[0]
                choices={decision['source_definition_id']+'/'+selector:chosen}
                expected=export_set(self.catalogue,identity,'4A',variant_selections=choices,hashes=hashes)
                self.assertEqual(module.hydrate_context(packed,default['id'],choices),expected)

    def test_contradictory_receipt_and_assignment_is_rejected_with_and_without_cache(self):
        from scripts.construction_set_validation import validate_set,BatchValidationCache
        default=export_set(self.catalogue,'construction-065e2be2332c15d04a224fe3','4A')
        bad=copy.deepcopy(default)
        d=next(d for d in bad['metadata']['selection_decisions'] if d['source_selector']=='exterior_skylight')
        alternative=next(i for i in d['candidate_element_ids'] if i not in d['resolved_climate_selection']['element_ids'])
        d['resolved_climate_selection']['element_ids']=[alternative]
        bad['metadata']['variant_selections']={d['source_definition_id']+'/'+d['source_selector']:alternative}
        for cache in (None,BatchValidationCache()):
            validate_set(default,cache=cache)
            with self.assertRaisesRegex(ValueError,'receipt|assignment'):validate_set(bad,cache=cache)

    def test_changed_v1_catalogue_is_rejected_before_becoming_migration_baseline(self):
        from scripts import construction_set_export as exporter
        from scripts import construction_set_release as release
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            root=Path(directory)
            (root/'catalogue.json').write_text('{}',encoding='utf-8')
            (root/'manifest.json').write_text(json.dumps({'files':{'catalogue.json':{'sha256':'0'*64}},'input_sha256':{}}),encoding='utf-8')
            with patch.object(exporter,'LIBRARY',root),patch.object(release,'LIBRARY',root):
                with self.assertRaisesRegex(ValueError,'catalogue checksum'):exporter.input_hashes()
                with self.assertRaisesRegex(ValueError,'catalogue checksum'):release.build_release(progress=False)

    def test_table_only_resources_receive_layer_and_material_graph_checks(self):
        from scripts.construction_set_validation import validate_resource_graph
        p=copy.deepcopy(self.examples[0]);a=copy.deepcopy(next(iter(p['assemblies'].values())))
        a['id']='independent-source-recipe';p['assemblies'][a['id']]=a
        validate_resource_graph(p)
        a['layers'][0]['order']=99
        with self.assertRaisesRegex(ValueError,'layer order'):validate_resource_graph(p)


if __name__=='__main__':unittest.main()
