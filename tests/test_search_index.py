"""Search indexes each suite page once by its summary; guides keep full text (ADR 0043)."""
import json
import tempfile
import unittest
from pathlib import Path

from website.hooks.search_index import compact, on_post_build


class SearchIndexTests(unittest.TestCase):
    def test_suite_pages_become_one_summary_entry(self):
        index = {'config': {}, 'docs': [{'location': 'catalogue/a/', 'title': 'A', 'text': 'long table text'},
                                        {'location': 'catalogue/a/#section-loads', 'title': 'Loads', 'text': 'more'},
                                        {'location': 'guides/selection/', 'title': 'Guide', 'text': 'kept'}]}
        out = compact(index, {'catalogue/a/': 'A · a-id · program', 'catalogue/b/': 'B <b> · b-id'})
        self.assertEqual([d['location'] for d in out['docs']], ['catalogue/a/', 'guides/selection/', 'catalogue/b/'])
        self.assertEqual(out['docs'][0]['text'], 'A · a-id · program')
        self.assertEqual(out['docs'][1]['text'], 'kept')
        self.assertEqual(out['docs'][2]['title'], 'B &lt;b&gt;')
        self.assertEqual(index['docs'][0]['text'], 'long table text')

    def test_the_hook_rewrites_the_built_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            docs, site = root/'docs', root/'site'
            docs.mkdir()
            (docs/'search-summaries.json').write_text(json.dumps({'catalogue/p/': 'Whole dwelling · p'}), encoding='utf-8')
            index = site/'search/search_index.json'
            index.parent.mkdir(parents=True)
            index.write_text(json.dumps({'docs': [{'location': 'catalogue/p/', 'title': 'Whole dwelling', 'text': ''},
                                                  {'location': 'guides/definitions/', 'title': 'Guide', 'text': 'Contract'}]}),
                             encoding='utf-8')
            on_post_build({'docs_dir': docs, 'site_dir': site})
            result = json.loads(index.read_text(encoding='utf-8'))['docs']
            self.assertEqual(result, [{'location': 'catalogue/p/', 'title': 'Whole dwelling', 'text': 'Whole dwelling · p'},
                                      {'location': 'guides/definitions/', 'title': 'Guide', 'text': 'Contract'}])


if __name__ == '__main__':
    unittest.main()
