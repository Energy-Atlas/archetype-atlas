import importlib
import unittest


class CardIconTests(unittest.TestCase):
    def renderer(self):
        module = importlib.import_module('website.hooks.card_icons')
        return module.on_page_content

    def test_decoration_preserves_link_and_accessible_name(self):
        render = self.renderer()
        source = '<p><span class="ea-card-icon" data-icon="program"></span><a href="program/">Programs</a></p>'
        result = render(source, page=None, config=None, files=None)
        self.assertEqual(result.count('<svg '), 2)
        self.assertEqual(result.count('aria-hidden="true"'), 2)
        self.assertIn('<a href="program/">Programs</a>', result)
        self.assertNotIn('data-icon=', result)

    def test_missing_icon_stops_build(self):
        with self.assertRaises(FileNotFoundError):
            self.renderer()('<span class="ea-card-icon" data-icon="missing"></span>', page=None, config=None, files=None)

    def test_other_content_is_unchanged(self):
        source = '<pre>&lt;svg&gt;</pre><span class="other">Unknown</span>'
        self.assertEqual(self.renderer()(source, page=None, config=None, files=None), source)
