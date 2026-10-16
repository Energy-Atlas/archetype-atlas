"""Hotel generic applicability preserves source variants and inheritance."""
import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.common import ROOT,load_json
from scripts.construction_set_release import load_release,hydrate_context
from scripts.construction_set_validation import BatchValidationCache

SMALL_2019='construction-c6985aaff2845cac856a73ab'
GENERIC='construction-1d0774872c8801caa0afdd44'


class HotelGuestRoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base=load_release()

    def implementation(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_hotel_applicability'),'Hotel applicability implementation is missing')
        from scripts import construction_hotel_applicability as module
        return module

    def prepared(self):
        module=self.implementation();overlay=module.build_overlay(self.base)
        return module,overlay,module.apply_overlay(self.base,overlay)

    def test_native_generic_is_added_without_changing_specific_variants(self):
        module,overlay,current=self.prepared()
        contexts=[c for c in self.base['contexts'].values() if c['construction_set_id']==SMALL_2019]
        cache=BatchValidationCache()
        for c in contexts:
            before=hydrate_context(self.base,c['id'],cache=cache)
            after=hydrate_context(current,c['id'],cache=cache)
            self.assertEqual(before['infiltration'],after['infiltration'])
            for role,component in before['components'].items():
                original=component['assignments'];revised=after['components'][role]['assignments']
                self.assertEqual(revised[:len(original)],original)
            additions=[a for comp in after['components'].values() for a in comp['assignments'] if a['when'].get('space_type')=='GuestRoom']
            self.assertTrue(additions)
            self.assertTrue(all(a['source_definition_id']==GENERIC for a in additions))
            specific={a['when'].get('space_type') for comp in after['components'].values() for a in comp['assignments'] if a['when']['scope']=='space_type'}
            self.assertEqual(specific,{'GuestRoom','GuestRoom123Occ','GuestRoom123Vac','GuestRoom4Occ','GuestRoom4Vac'})
            module.validate_extensions(after)

    def test_older_small_hotels_declare_inheritance_and_preserve_all_rules(self):
        module,overlay,current=self.prepared();count=0;cache=BatchValidationCache()
        for c in self.base['contexts'].values():
            profile=self.base['construction_sets'][c['construction_set_id']]
            if profile['scope']!='building' or profile['source']['building_type']!='SmallHotel' or profile['source']['template']=='90.1-2019':continue
            before=hydrate_context(self.base,c['id'],cache=cache);after=hydrate_context(current,c['id'],cache=cache)
            self.assertEqual(before['components'],after['components'])
            self.assertEqual(before['infiltration'],after['infiltration'])
            marked=[d for d in after['metadata']['selection_decisions'] if 'atlas_added_applicability' in d]
            self.assertTrue(marked)
            self.assertEqual({d['atlas_added_applicability']['mode'] for d in marked},{'inherit_existing_building_story_rules'})
            self.assertTrue(all(d['atlas_added_applicability']['space_type']=='GuestRoom' for d in marked))
            fallbacks=[d for d in after['metadata']['selection_decisions'] if d['scope']['scope'] in {'building_default','story'}]
            self.assertEqual(len(marked),len(fallbacks))
            self.assertTrue(all('atlas_added_applicability' not in d for d in after['metadata']['selection_decisions'] if d['scope']['scope']=='space_type'))
            module.validate_extensions(after);count+=1
        self.assertGreater(count,0)

    def test_no_physics_or_unrelated_context_changes(self):
        module,overlay,current=self.prepared()
        self.assertEqual(current['assemblies'],self.base['assemblies'])
        self.assertEqual(current['materials'],self.base['materials'])
        self.assertEqual(current['construction_sets'],self.base['construction_sets'])
        affected=set(overlay['patches']['contexts'])
        for i,c in self.base['contexts'].items():
            if i not in affected:self.assertEqual(current['contexts'][i],c)
        for i,e in self.base['evidence'].items():self.assertEqual(current['evidence'][i],e)
        for i in ('construction-93cb2afe2fe44c8e084b9b99','construction-0079ce7b163bdb1bd0154dbe','construction-f49ea44a07f08174585b351a'):
            c=next(c for c in self.base['contexts'].values() if c['construction_set_id']==i)
            old=hydrate_context(self.base,c['id']);new=hydrate_context(current,c['id'])
            new['metadata']['source_files']=old['metadata']['source_files'];new['metadata']['input_sha256']=old['metadata']['input_sha256']
            self.assertEqual(new,old)

    def test_extension_has_atlas_origin_and_locked_provenance(self):
        module,overlay,current=self.prepared()
        c=next(c for c in current['contexts'].values() if c['construction_set_id']==SMALL_2019)
        p=hydrate_context(current,c['id']);d=next(d for d in p['metadata']['selection_decisions'] if 'atlas_added_applicability' in d)
        extension=d['atlas_added_applicability'];proof=p['evidence'][extension['evidence_id']]
        self.assertEqual(extension['origin'],'atlas_added_applicability')
        self.assertFalse(extension['source_space_type_instantiated'])
        self.assertIn('GuestRoom',json.dumps(proof['original_value']))
        self.assertEqual(proof['source_file_sha256'],overlay['policy_sha256'])
        del p['evidence'][extension['evidence_id']]
        with self.assertRaises((ValueError,KeyError)):module.validate_extensions(p)

    def test_missing_or_false_origin_declaration_is_rejected(self):
        module,overlay,current=self.prepared()
        c=next(c for c in current['contexts'].values() if c['construction_set_id']==SMALL_2019)
        p=hydrate_context(current,c['id']);d=next(d for d in p['metadata']['selection_decisions'] if 'atlas_added_applicability' in d)
        del d['atlas_added_applicability']
        with self.assertRaises(ValueError):module.validate_extensions(p)
        p=hydrate_context(current,c['id']);d=next(d for d in p['metadata']['selection_decisions'] if 'atlas_added_applicability' in d)
        d['atlas_added_applicability']['source_space_type_instantiated']=True
        with self.assertRaises(ValueError):module.validate_extensions(p)
        p=hydrate_context(current,c['id'])
        p['metadata']['selection_decisions']=[d for d in p['metadata']['selection_decisions'] if d['source_definition_id']!=GENERIC]
        with self.assertRaises(ValueError):module.validate_extensions(p)

    def test_policy_cannot_borrow_another_template_or_omit_a_hotel(self):
        module=self.implementation();policy=load_json(module.POLICY)
        policy['entries'][SMALL_2019]['recipe_construction_id']='construction-200d9d7835b77e2e3d5c9862'
        with self.assertRaisesRegex(ValueError,'recipe|template|hotel'):module.build_overlay(self.base,policy=policy)
        policy=load_json(module.POLICY);del policy['entries'][SMALL_2019]
        with self.assertRaisesRegex(ValueError,'census|missing|policy'):module.build_overlay(self.base,policy=policy)

    def test_geometry_inventory_bytes_are_checked_against_frozen_input(self):
        module=self.implementation();original=module.checksum
        def changed(path):
            return '0'*64 if Path(path).name=='geometry-v1.json' else original(path)
        with patch.object(module,'checksum',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'geometry|checksum'):module.build_overlay(self.base)

    def test_overlay_rejects_unrelated_context_or_material_patch(self):
        module,overlay,current=self.prepared()
        changed=copy.deepcopy(overlay);changed['patches']['materials']={}
        with self.assertRaises(ValueError):module.apply_overlay(self.base,changed)
        changed=copy.deepcopy(overlay)
        c=next(c for c in self.base['contexts'].values() if self.base['construction_sets'][c['construction_set_id']]['source']['building_type']=='MediumOffice')
        changed['patches']['contexts'][c['id']]=c
        with self.assertRaises(ValueError):module.apply_overlay(self.base,changed)

    def test_reproducible_and_browser_hydration_preserves_extension(self):
        module,overlay,current=self.prepared()
        self.assertEqual(overlay,module.build_overlay(self.base))
        from scripts.construction_site import packet_for
        from scripts.construction_mass_release import load_release as load_mass
        from scripts.construction_mass_accounting import upgrade_detailed
        contexts={i:c for i,c in current['contexts'].items() if c['construction_set_id']==SMALL_2019}
        c=next(iter(contexts.values()));p=hydrate_context(current,c['id']);packet=packet_for(current,SMALL_2019,contexts)
        mass=load_mass()
        p=upgrade_detailed(p,mass['contracts'][mass['contexts'][c['id']]['contract_id']])
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'parity.json';path.write_text(json.dumps({'packet':packet,'expected':p}),encoding='utf-8')
            js="const fs=require('node:fs'),assert=require('node:assert/strict'),core=require('./website/assets/construction_core.js'); const d=JSON.parse(fs.readFileSync(process.argv[1]));assert.deepEqual(core.hydrate(d.packet,d.expected.id),d.expected);"
            run=subprocess.run(['node','-e',js,str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr[:1500])


if __name__=='__main__':unittest.main()
