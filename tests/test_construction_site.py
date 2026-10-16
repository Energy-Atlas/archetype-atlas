"""Frozen construction delivery, consumer parity and presentation isolation."""
import gzip
import hashlib
import html
import importlib.util
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.common import ROOT,load_json
from scripts.construction_set_release import load_release,hydrate_context,ReleaseBuilder
from scripts.definition_contract import DefinitionBundle,record


class ConstructionSiteTests(unittest.TestCase):
    def test_required_publication_delivery_rejects_missing_catalogue(self):
        from scripts.construction_site import verify_delivery
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertEqual(verify_delivery(root),[])
            errors=verify_delivery(root,require_construction=True)
            self.assertTrue(errors,'A publication without construction delivery must fail')
            self.assertIn('Missing required construction delivery',errors[0])

    def test_publication_cli_requires_construction_before_reporting_success(self):
        import sys
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'index.html').write_text('<h1>Fixture</h1>',encoding='utf-8')
            result=subprocess.run([sys.executable,'-m','scripts.site_check','--site',str(root),'--require-construction'],
                                  cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Missing required construction delivery',result.stderr+result.stdout)

    def test_retired_space_recipe_links_point_to_complete_parents(self):
        from scripts import construction_site
        self.assertTrue(hasattr(construction_site,'rewrite_retired_links'))
        retired='construction-1d0774872c8801caa0afdd44'
        parent='construction-c6985aaff2845cac856a73ab'
        original='<li><a href="/archetype-atlas/definitions/'+retired+'/">Partial room</a></li><a href="/program/">Unchanged</a>'
        result=construction_site.rewrite_retired_links(original,{retired:[parent]},{parent:{'name':'Hotel building'}})
        self.assertNotIn('definitions/'+retired+'/',result)
        self.assertIn(retired,result);self.assertIn('definitions/'+parent+'/',result)
        self.assertIn('Hotel building',result);self.assertIn('<a href="/program/">Unchanged</a>',result)

    def test_fresh_generation_retires_partial_raw_blobs(self):
        from scripts.object_site import JSONStore,json_markup
        retired='construction-1d0774872c8801caa0afdd44'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'definitions').mkdir()
            raw=JSONStore(root).put({'id':retired,'scope':'space_type'})
            (root/f'definitions/{retired}.md').write_text(json_markup(raw),encoding='utf-8')
            self.generate(root)
            self.assertFalse((root/raw['href']).exists())

    def test_current_site_retains_only_current_construction_query_snapshot(self):
        from scripts import construction_site
        self.assertTrue(hasattr(construction_site,'prune_construction_history'))
        from scripts.query_v2 import generate_delivery,QueryClient
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle=self.bundle
            before=generate_delivery(bundle,root);program=before['record_types']['program']
            bundle=dict(bundle,constructions=bundle['constructions'][:1])
            after=generate_delivery(bundle,root,only_kind='construction')
            self.assertEqual(len(list((root/'snapshots').glob('*/manifest.json'))),2)
            construction_site.prune_construction_history(root)
            self.assertEqual(len(list((root/'snapshots').glob('*/manifest.json'))),1)
            self.assertEqual(QueryClient(root).manifest['record_types']['program'],program)
            self.assertTrue((root/after['record_types']['construction']['index']['href']).is_file())

    @classmethod
    def setUpClass(cls):
        from scripts.construction_mass_release import load_release as load_mass
        from scripts.construction_mass_accounting import upgrade_detailed
        cls.mass=load_mass()
        full=load_release();builder=ReleaseBuilder();cls.expected={}
        names=('construction-93cb2afe2fe44c8e084b9b99','construction-0079ce7b163bdb1bd0154dbe')
        for identity in names:
            contexts=[c for c in full['contexts'].values() if c['construction_set_id']==identity]
            for c in contexts[:2]:
                p=hydrate_context(full,c['id']);builder.add(p);cls.expected[c['id']]=upgrade_detailed(p,cls.mass['contracts'][cls.mass['contexts'][c['id']]['contract_id']])
        cls.release=builder.finish();cls.bundle=DefinitionBundle()
        for identity,p in cls.release['construction_sets'].items():
            row=record('construction',{'id':identity,**p['source']},p['name']);row['id']=identity
            if p['scope']=='whole_dwelling':row['gate']=['residential']
            cls.bundle['constructions'].append(row)
        cls.bundle['constructions'].append(record('construction',{'id':'old-wall','building_type':'MediumOffice'},'Old single wall'))

    def generate(self,root):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_site'),'Construction site integration is missing')
        from scripts.construction_site import generate_constructions
        return generate_constructions(self.release,self.bundle,root)

    def test_finder_uses_whole_sets_and_preserves_unrelated_program_pages(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'definitions').mkdir();cached=root/'definitions/program-cached.md'
            cached.write_bytes(b'unchanged program page')
            self.generate(root)
            entries=load_json(root/'catalogue/nonresidential/construction/entries.json')
            self.assertEqual({e['id'] for e in entries},{'construction-93cb2afe2fe44c8e084b9b99'})
            self.assertTrue(entries[0]['applicability'])
            self.assertEqual(entries[0]['construction_schema'],'2.1.0')
            self.assertEqual(cached.read_bytes(),b'unchanged program page')
            page=(root/'definitions'/('construction-93cb2afe2fe44c8e084b9b99.md')).read_text(encoding='utf-8')
            self.assertIn('data-construction=',page);self.assertIn('construction-climate',page)
            self.assertNotIn('Copy with defaults',page)
            for gate in ('residential','nonresidential'):
                finder=(root/f'catalogue/{gate}/construction/index.md').read_text(encoding='utf-8')
                self.assertNotIn('data-filter="scope"',finder)
                self.assertNotIn('data-filter="evidence_view"',finder)
                self.assertIn('data-filter="climate"',finder)

    def test_browser_hydration_preserves_complete_frozen_pilot_documents(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.generate(root)
            packets={}
            for identity in self.release['construction_sets']:
                page=(root/'definitions'/(identity+'.md')).read_text(encoding='utf-8')
                descriptor=json.loads(html.unescape(re.search(r'data-construction="([^"]+)"',page)[1]))
                packets[identity]=json.loads(gzip.decompress((root/descriptor['href']).read_bytes()))
            payload=root/'parity.json';payload.write_text(json.dumps({'packets':packets,'expected':self.expected}),encoding='utf-8')
            code="const assert=require('node:assert/strict'),fs=require('node:fs'),core=require('./website/assets/construction_core.js'); const data=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));for(const [id,p] of Object.entries(data.expected)){assert.deepEqual(core.hydrate(data.packets[p.source.construction_set_id],id),p);}assert.throws(()=>core.hydrate(Object.values(data.packets)[0],'unknown'));const packet=Object.values(data.packets)[0],cid=Object.keys(packet.contexts)[0];delete packet.mass_contracts;assert.throws(()=>core.hydrate(packet,cid),/Missing shared mass/);"
            result=subprocess.run(['node','-e',code,str(payload)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr[:2500])

    def test_separate_unified_packet_hydrates_frozen_documents_for_same_contexts(self):
        from scripts.construction_equivalent_release import export_frozen,OUTPUT
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report=self.generate(root)
            self.assertIn('unified_packets',report)
            packets={}
            for identity,descriptor in report['unified_packets'].items():
                page=(root/f'definitions/{identity}.md').read_text(encoding='utf-8')
                self.assertIn('construction-representation',page)
                self.assertIn('construction-copy-unified',page)
                bound=json.loads(html.unescape(re.search(r'data-unified="([^"]+)"',page)[1]))
                self.assertEqual(bound,descriptor)
                self.assertNotEqual(descriptor,report['packets'][identity])
                packets[identity]=json.loads(gzip.decompress((root/descriptor['href']).read_bytes()))
            from scripts.construction_mass_accounting import upgrade_unified
            expected={i:upgrade_unified(export_frozen(OUTPUT,i),self.mass['contracts'][self.mass['contexts'][i]['contract_id']]) for i in self.release['contexts']}
            payload=root/'unified-parity.json'
            payload.write_text(json.dumps({'packets':packets,'expected':expected,'contexts':self.release['contexts']}),encoding='utf-8')
            code="const assert=require('node:assert/strict'),fs=require('node:fs'),core=require('./website/assets/construction_core.js'); const d=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));for(const [id,p] of Object.entries(d.expected)){const packet=d.packets[d.contexts[id].construction_set_id];assert.deepEqual(core.hydrateUnified(packet,id),p);assert.throws(()=>core.hydrateUnified(packet,'unknown'));assert.equal(core.hydrateUnified(packet,id).schema_version,'1.2.0');const broken=structuredClone(packet);delete broken.mass_contracts;assert.throws(()=>core.hydrateUnified(broken,id),/Missing shared mass/);}"
            result=subprocess.run(['node','-e',code,str(payload)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr[:2500])

    def test_verifier_rejects_missing_unified_page_binding(self):
        from scripts.construction_site import verify_delivery
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report=self.generate(root)
            self.assertIn('unified_packets',report)
            identity=next(iter(report['packets']));page=root/f'definitions/{identity}.md'
            page.write_text(re.sub(r' data-unified="[^"]+"','',page.read_text(encoding='utf-8')),encoding='utf-8')
            self.assertTrue(verify_delivery(root,self.release))

    def test_construction_pages_omit_legacy_source_record_but_other_objects_retain_it(self):
        from scripts.object_site import json_markup
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report=self.generate(root)
            for identity in report['packets']:
                page=(root/f'definitions/{identity}.md').read_text(encoding='utf-8')
                self.assertNotIn('data-raw=',page)
                self.assertIn('Copy detailed JSON',page)
                self.assertIn('Copy unified JSON',page)
            # The generic source/default chooser belongs to other object types.
            self.assertIn('data-raw=',json_markup({'href':'source.json'}))

    def test_every_physical_resource_and_provenance_is_accessible(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report=self.generate(root)
            for table in ('assemblies','materials','evidence'):
                self.assertEqual(set(report['resources'][table]),set(self.release[table]))
                for identity,entry in report['resources'][table].items():
                    self.assertTrue((root/entry['path']).exists())
                    descriptor=entry['json']
                    self.assertEqual(json.loads(gzip.decompress((root/descriptor['href']).read_bytes())),self.release[table][identity])

    def test_focus_mode_requires_a_marked_generated_tree(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_site'))
        from scripts.construction_site import update_existing
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'generated|manifest'):update_existing(self.bundle,Path(d),self.release)

    def test_presentation_verifier_rejects_tampered_resources(self):
        from scripts import construction_site
        self.assertTrue(hasattr(construction_site,'verify_delivery'),'Construction presentation verifier is missing')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report=self.generate(root)
            self.assertEqual(construction_site.verify_delivery(root,self.release,require_construction=True),[])
            descriptor=next(iter(report['resources']['assemblies'].values()))['json']
            (root/descriptor['href']).write_bytes(b'corrupted')
            self.assertTrue(construction_site.verify_delivery(root,self.release))

    def test_verifier_binds_packet_to_page_and_rejects_missing_evidence(self):
        from scripts.construction_site import verify_delivery
        from scripts.object_site import JSONStore
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report=self.generate(root)
            identity,descriptor=next(iter(report['packets'].items()))
            path=root/'definitions'/(identity+'.md');original=path.read_text(encoding='utf-8')
            raw=re.search(r'data-unified="([^"]+)"',original)[1]
            path.write_text(re.sub(r'data-construction="[^"]+"',lambda _: 'data-construction="'+raw+'"',original),encoding='utf-8')
            self.assertTrue(verify_delivery(root,self.release),'Wrong page packet must fail')
            packet=json.loads(gzip.decompress((root/descriptor['href']).read_bytes()))
            eid=next(iter(packet['contexts'].values()))['source_evidence_ids'][0]
            del packet['evidence'][eid]
            revised=JSONStore(root).put(packet);report['packets'][identity]=revised
            (root/'construction-site.json').write_text(json.dumps(report),encoding='utf-8')
            path.write_text(re.sub(r'data-construction="[^"]+"',lambda _: 'data-construction="'+html.escape(json.dumps(revised),quote=True)+'"',original),encoding='utf-8')
            self.assertTrue(verify_delivery(root,self.release),'Missing evidence closure must fail')

    def test_program_cache_tracks_exporter_operands(self):
        from scripts.construction_site import program_presentation_inputs
        files=program_presentation_inputs(self.bundle)['files']
        for path in ('data/releases/v0.2.0/programs.json','scripts/semantics.py','scripts/program_json_aggregation.py','scripts/program_composition.py','schemas/program-json-v2.schema.json'):
            self.assertIn(path,files)

    def test_delivered_applicability_manifest_matches_its_files(self):
        from scripts.construction_site import install_contract
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);install_contract(root)
            directory=root/'construction/applicability';manifest=load_json(directory/'manifest.json')
            for name,entry in manifest['files'].items():
                self.assertTrue((directory/name).is_file(),'Manifest names missing download: '+name)
                data=(directory/name).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(),entry['sha256']);self.assertEqual(len(data),entry['bytes'])


if __name__=='__main__':unittest.main()
