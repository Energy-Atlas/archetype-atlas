"""Reduce generated template indentation, retaining literal regions verbatim."""
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit


class DeliveryHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts=[]
        self.literal=[]

    def handle_starttag(self,tag,attrs):
        self.parts.append(self.get_starttag_text())
        if tag in {'pre','code','textarea','script','style','svg','math'}:
            self.literal.append(tag)

    def handle_startendtag(self,tag,attrs):
        self.parts.append(self.get_starttag_text())

    def handle_endtag(self,tag):
        self.parts.append('</'+tag+'>')
        if self.literal and tag==self.literal[-1]:
            self.literal.pop()

    def handle_data(self,data):
        if not self.literal:
            data=re.sub(r'\n[ \t]+','\n',data)
            data=re.sub(r'\n{2,}','\n',data)
        self.parts.append(data)

    def handle_entityref(self,name):
        # Quotes are ordinary HTML text in literal text elements. Attribute
        # escaping and script/style bytes remain untouched; < and & stay escaped.
        self.parts.append('"' if name=='quot' and self.literal and self.literal[-1] in {'pre','code','textarea'} else '&'+name+';')
    def handle_charref(self,name):
        quoted={'34':'"','x22':'"','39':"'",'x27':"'"}
        self.parts.append(quoted[name.lower()] if name.lower() in quoted and self.literal and
            self.literal[-1] in {'pre','code','textarea'} else '&#'+name+';')
    def handle_comment(self,data):self.parts.append('<!--'+data+'-->')
    def handle_decl(self,decl):self.parts.append('<!'+decl+'>')
    def handle_pi(self,data):self.parts.append('<?'+data+'>')


def on_post_page(output,*,page,config):
    # Thousands of archived detail pages need content and charts, without a full
    # copy of the global tab/sidebar/search markup on each immutable record URL.
    src=page.file.src_uri if page is not None else ''
    detail=src.startswith(('definitions/','objects/')) or bool(re.match(r'releases/v[^/]+/(programs|schedules|systems|mappings|envelope_components|efficiency_rules|commercial_options|residential_options|specialized_rules|residential_archetypes|buildings|axes)/.*\.md$',src))
    if detail:
        head=re.search(r'<head\b[^>]*>.*?</head>',output,re.S)
        article=re.search(r'<article\b[^>]*>.*?</article>',output,re.S)
        if head and article:
            # The compact shell does not load Material's navigation runtime.
            # Retain title, viewport, canonical/icon links and shared styles.
            retained=re.findall(r'<title\b[^>]*>.*?</title>|<meta\b[^>]*(?:charset|name="viewport")[^>]*>|<link\b[^>]*>',head[0],re.S)
            compact_head='<head>'+''.join(retained)+'</head>'
            prefix=urlsplit(config['site_url']).path.rstrip('/')+'/'
            scripts=re.findall(r'<script\b[^>]*src="[^"]*(?:assets/(?:core|site|definition|definition_core|object|schedule|schedule_core)\.js|plotly[^"/]*)"[^>]*>.*?</script>',output,re.S)
            output='<!doctype html><html lang="en">'+compact_head+'<body><header class="definition-header"><a href="'+prefix+'">Energy Archetype Atlas</a> · <a href="'+prefix+'catalogue/">Catalogue</a> · <a href="'+prefix+'sources/">Sources</a></header><main class="definition-document">'+article[0]+'</main>'+''.join(scripts)+'</body></html>'
    parser=DeliveryHTML();parser.feed(output);parser.close()
    return ''.join(parser.parts)
