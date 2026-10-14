"""Focused construction rendering reuses the verified local site shell."""
import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.common import ROOT,load_json
from scripts.construction_set_release import load_release,hydrate_context,ReleaseBuilder
from scripts.definition_contract import DefinitionBundle,record
from scripts.construction_site import generate_constructions


class ConstructionRefreshTests(unittest.TestCase):
    def implementation(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_site_refresh'),'Focused construction refresh is missing')
        from scripts import construction_site_refresh
        return construction_site_refresh

    def test_rendering_preserves_shell_and_resolves_mkdocs_links(self):
        module=self.implementation()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'guides').mkdir();(root/'guides/contract.md').write_text('# Contract')
            old='<html><head>UNCHANGED</head><body><article class="md-typeset">old</article><script>UNCHANGED</script></body></html>'
            result=module.render_page('# Test\n\n[Contract](../guides/contract.md)\n\n| A | B |\n|---|---|\n| 1 | 2 |',old,'definitions/example.md',root)
            self.assertIn('<head>UNCHANGED</head>',result);self.assertIn('<script>UNCHANGED</script>',result)
            self.assertIn('/archetype-atlas/guides/contract/',result);self.assertIn('<table>',result)
            with self.assertRaises(ValueError):module.render_page('[Bad](../../outside.md)',old,'definitions/example.md',root)

    def test_unmarked_or_nonworkspace_output_is_rejected(self):
        module=self.implementation()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'marked|workspace'):module.refresh(Path(d)/'docs',Path(d)/'site')

    def test_download_links_resolve_from_source_directory(self):
        module=self.implementation()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'construction/applicability').mkdir(parents=True);(root/'contracts').mkdir()
            (root/'construction/applicability/policy.json').write_text('{}');(root/'contracts/schema.json').write_text('{}')
            shell='<html><article>old</article></html>'
            result=module.render_page('[Policy](../construction/applicability/policy.json)',shell,'definitions/example.md',root)
            self.assertIn('href="/archetype-atlas/construction/applicability/policy.json"',result)
            result=module.render_page('[Schema](../contracts/schema.json)',shell,'guides/construction-json.md',root)
            self.assertIn('href="/archetype-atlas/contracts/schema.json"',result)

    def test_focused_link_check_checks_downloads_without_scanning_other_pages(self):
        from scripts.site_check import check_links
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'index.html').write_text('<p>Home</p>')
            page=root/'selected.html';page.write_text('<a href="policy.json">Policy</a>')
            (root/'unrelated.html').write_text('<a href="absent.html">Unrelated broken page</a>')
            self.assertTrue(check_links(root,paths=[page]))
            (root/'policy.json').write_text('{}');self.assertEqual(check_links(root,paths=[page]),[])

    def test_refresh_updates_packets_and_preserves_program_pages(self):
        module=self.implementation();base=load_release();builder=ReleaseBuilder()
        c=next(c for c in base['contexts'].values() if c['construction_set_id']=='construction-93cb2afe2fe44c8e084b9b99')
        builder.add(hydrate_context(base,c['id']));release=builder.finish();bundle=DefinitionBundle()
        p=release['construction_sets'][c['construction_set_id']]
        row=record('construction',{'id':p['id'],**p['source']},p['name']);row['id']=p['id'];bundle['constructions'].append(row)
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as d:
            docs=Path(d)/'docs';site=Path(d)/'site';docs.mkdir()
            generate_constructions(release,bundle,docs)
            (docs/'site-manifest.json').write_text(json.dumps({'objects':0,'counts':{},'default_export_failures':[]}))
            # The contract's linked resources are installed by refresh().
            from scripts.construction_site import install_contract
            install_contract(docs);shutil.copytree(docs,site)
            target=site/f'definitions/{p["id"]}/index.html';target.parent.mkdir(parents=True)
            target.write_text('<html><head>same</head><body><article>'+ (docs/f'definitions/{p["id"]}.md').read_text(encoding='utf-8')+'</article></body></html>',encoding='utf-8')
            guide=site/'guides/construction-json/index.html';guide.parent.mkdir(parents=True);guide.write_text('<html><article>old</article></html>')
            sentinel=site/'program-sentinel.html';sentinel.write_bytes(b'unchanged program')
            revised=copy.deepcopy(release);revised['metadata']['source_files']['test']={'sha256':'a'*64,'source_revision':'test'}
            result=module.refresh(docs,site,release=revised,bundle=bundle)
            self.assertEqual(result['construction_pages'],1);self.assertEqual(sentinel.read_bytes(),b'unchanged program')
            self.assertIn('test',json.loads(__import__('gzip').decompress((site/load_json(site/'construction-site.json')['packets'][p['id']]['href']).read_bytes()))['metadata']['source_files'])


if __name__=='__main__':unittest.main()
