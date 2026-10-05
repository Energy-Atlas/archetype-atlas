"""Derived search size may shrink without dropping records or guide search."""
import unittest
from website.hooks.search_index import compact_records


class SearchIndexTests(unittest.TestCase):
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
