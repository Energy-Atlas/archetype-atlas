"""Presentation indentation may shrink; literal data and scripts must survive."""
import importlib.util
from pathlib import Path
import unittest


class HtmlDeliveryTests(unittest.TestCase):
    def test_archived_axis_shell_keeps_section_links_with_only_required_head_assets(self):
        from types import SimpleNamespace
        path=Path(__file__).resolve().parents[1]/'website/hooks/html_delivery.py'
        spec=importlib.util.spec_from_file_location('html_delivery',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        original='<html><head><title>Axis</title><meta name="generator" content="repeated"><link rel="stylesheet" href="../assets/site.css"><script>__md_scope=1;</script></head><body><nav>repeated navigation</nav><article><h1 id="axis">Axis</h1><a href="../programs/p/">Program</a></article></body></html>'
        result=module.on_post_page(original,page=SimpleNamespace(file=SimpleNamespace(src_uri='releases/v0.2.0/axes/building/b.md')),config={'site_url':'https://energy-atlas.github.io/archetype-atlas/'})
        self.assertNotIn('repeated navigation',result)
        self.assertNotIn('__md_scope',result)
        self.assertIn('id="axis"',result)
        self.assertIn('../programs/p/',result)
        self.assertIn('../assets/site.css',result)
    def test_literal_text_quotes_compact_without_changing_text_or_attribute_safety(self):
        from html.parser import HTMLParser
        path=Path(__file__).resolve().parents[1]/'website/hooks/html_delivery.py'
        spec=importlib.util.spec_from_file_location('html_delivery',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        original='<pre>{&quot;name&quot;:&quot;&lt;tag&gt; &amp; &#x27;value&#x27;&quot;}</pre><a data-id="&quot;safe&quot;">Link</a><script>const s="&quot;";</script>'
        result=module.on_post_page(original,page=None,config=None)
        self.assertIn('<pre>{"name":"&lt;tag&gt; &amp; \'value\'"}</pre>',result)
        self.assertIn('data-id="&quot;safe&quot;"',result)
        self.assertIn('<script>const s="&quot;";</script>',result)
        class Text(HTMLParser):
            def __init__(self):super().__init__();self.text=[]
            def handle_data(self,data):self.text.append(data)
        a=Text();a.feed(original);b=Text();b.feed(result)
        self.assertEqual(a.text,b.text)
    def test_record_shell_keeps_content_and_assets_without_repeated_navigation(self):
        from types import SimpleNamespace
        path=Path(__file__).resolve().parents[1]/'website/hooks/html_delivery.py'
        spec=importlib.util.spec_from_file_location('html_delivery',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        original='<html><head><title>Record</title><link href="../assets/site.css"></head><body><nav>repeated sidebar</nav><article class="md-content__inner md-typeset"><h1>Record</h1><pre>original  value</pre></article><script src="../assets/core.js"></script><script src="../assets/site.js"></script></body></html>'
        result=module.on_post_page(original,page=SimpleNamespace(file=SimpleNamespace(src_uri='releases/v0.2.0/programs/p.md')),config={'site_url':'https://energy-atlas.github.io/archetype-atlas/'})
        self.assertNotIn('repeated sidebar',result)
        self.assertIn('<pre>original  value</pre>',result)
        self.assertIn('../assets/site.js',result)
        self.assertIn('/archetype-atlas/catalogue/',result)
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
