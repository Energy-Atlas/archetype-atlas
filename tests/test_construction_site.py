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
    @classmethod
    def setUpClass(cls):
        full=load_release();builder=ReleaseBuilder();cls.expected={}
        names=('construction-93cb2afe2fe44c8e084b9b99','construction-0079ce7b163bdb1bd0154dbe')
        for identity in names:
            contexts=[c for c in full['contexts'].values() if c['construction_set_id']==identity]
            for c in contexts[:2]:
                p=hydrate_context(full,c['id']);builder.add(p);cls.expected[c['id']]=p
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
            self.assertEqual(entries[0]['construction_schema'],'2.0.0')
            self.assertEqual(cached.read_bytes(),b'unchanged program page')
            page=(root/'definitions'/('construction-93cb2afe2fe44c8e084b9b99.md')).read_text(encoding='utf-8')
            self.assertIn('data-construction=',page);self.assertIn('construction-climate',page)
            self.assertNotIn('Copy with defaults',page)

    def test_browser_hydration_preserves_complete_frozen_pilot_documents(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.generate(root)
            packets={}
            for identity in self.release['construction_sets']:
                page=(root/'definitions'/(identity+'.md')).read_text(encoding='utf-8')
                descriptor=json.loads(html.unescape(re.search(r'data-construction="([^"]+)"',page)[1]))
                packets[identity]=json.loads(gzip.decompress((root/descriptor['href']).read_bytes()))
            payload=root/'parity.json';payload.write_text(json.dumps({'packets':packets,'expected':self.expected}),encoding='utf-8')
            code="const assert=require('node:assert/strict'),fs=require('node:fs'),core=require('./website/assets/construction_core.js'); const data=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));for(const [id,p] of Object.entries(data.expected)){assert.deepEqual(core.hydrate(data.packets[p.source.construction_set_id],id),p);}assert.throws(()=>core.hydrate(Object.values(data.packets)[0],'unknown'));"
            result=subprocess.run(['node','-e',code,str(payload)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr[:2500])

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
            self.assertEqual(construction_site.verify_delivery(root,self.release),[])
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
            raw=re.search(r'data-raw="([^"]+)"',original)[1]
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
