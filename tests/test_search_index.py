"""Derived search size may shrink without dropping records or guide search."""
import unittest
from website.hooks.search_index import compact_records


class SearchIndexTests(unittest.TestCase):
    def test_definition_titles_are_indexed_without_repeated_record_fields(self):
        import json
        import tempfile
        from pathlib import Path
        from website.hooks.search_index import on_post_build
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);docs=root/'docs';site=root/'site'
            finder=docs/'catalogue/residential/program/entries.json';finder.parent.mkdir(parents=True)
            finder.write_text(json.dumps([{'id':'p','name':'Whole dwelling'}]),encoding='utf-8')
            index=site/'search/search_index.json';index.parent.mkdir(parents=True)
            index.write_text(json.dumps({'docs':[
                {'location':'definitions/p/','title':'Whole dwelling','text':'repeated full fields'},
                {'location':'definitions/p/#loads','title':'Loads','text':'repeated loads'},
                {'location':'guides/definitions/','title':'Guide','text':'Complete contract'}]}),encoding='utf-8')
            on_post_build({'docs_dir':docs,'site_dir':site})
            result=json.loads(index.read_text(encoding='utf-8'))['docs']
            self.assertEqual(result,[{'location':'definitions/p/','title':'Whole dwelling','text':''},
                {'location':'guides/definitions/','title':'Guide','text':'Complete contract'}])
    def test_record_titles_and_full_guide_text_survive_without_duplicate_sections(self):
        paths={'releases/v0.2.0/programs/p/':'Medium Office',
               'releases/v0.2.0/systems/s/':'System <safe>'}
        index={'config':{'lang':['en']},'docs':[
            {'location':'releases/v0.2.0/programs/p/#medium-office','title':'Medium Office','text':'Full raw proof'},
            {'location':'releases/v0.2.0/programs/p/#provenance','title':'Provenance','text':'Repeated proof'},
            {'location':'guides/selection/','title':'Selection','text':'Use the climate filter'}]}
        result=compact_records(index,paths)
        self.assertEqual(result['docs'],[
            {'location':'releases/v0.2.0/programs/p/','title':'Medium Office','text':''},
            {'location':'guides/selection/','title':'Selection','text':'Use the climate filter'},
            {'location':'releases/v0.2.0/systems/s/','title':'System &lt;safe&gt;','text':''}])
        self.assertEqual(index['docs'][0]['text'],'Full raw proof')


if __name__=='__main__':
    unittest.main()
