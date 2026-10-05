"""Presentation indentation may shrink; literal data and scripts must survive."""
import importlib.util
from pathlib import Path
import unittest


class HtmlDeliveryTests(unittest.TestCase):
    def test_redundant_blank_lines_shrink_but_literal_blank_lines_and_inline_spaces_survive(self):
        path=Path(__file__).resolve().parents[1]/'website/hooks/html_delivery.py'
        spec=importlib.util.spec_from_file_location('html_delivery',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        literal='<pre>first\n\n\nsecond</pre>'
        original='<p>first <em>second</em> third</p>\n\n\n'+literal+'\n\n\n<p>end</p>'
        compact=module.on_post_page(original,page=None,config=None)
        self.assertIn(literal,compact)
        self.assertIn('<p>first <em>second</em> third</p>',compact)
        self.assertNotIn('</p>\n\n',compact)
        self.assertLess(len(compact),len(original))

    def test_indentation_is_reduced_without_altering_literal_regions_or_links(self):
        path=Path(__file__).resolve().parents[1]/'website/hooks/html_delivery.py'
        self.assertTrue(path.exists(),'Delivery hook must exist')
        spec=importlib.util.spec_from_file_location('html_delivery',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        literal='<pre>  original\n    indented &lt;value&gt;</pre><script>\n    const x = "  literal";\n</script>'
        original='<html>\n    <body>\n        <a href="../value/#part">Source &amp; zero</a>\n        '+literal+'\n    </body>\n</html>'
        compact=module.on_post_page(original,page=None,config=None)
        self.assertLess(len(compact),len(original))
        self.assertIn(literal,compact)
        self.assertIn('<a href="../value/#part">Source &amp; zero</a>',compact)
        self.assertIn('\n<body>\n<a',compact)
        self.assertEqual(module.on_post_page(compact,page=None,config=None),compact)


if __name__=='__main__':unittest.main()
