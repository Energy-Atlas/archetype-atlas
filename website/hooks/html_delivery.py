"""Reduce generated template indentation, retaining literal regions verbatim."""
from html.parser import HTMLParser
import re
from scripts.site_asset_versions import version_asset_urls


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
    parser=DeliveryHTML();parser.feed(version_asset_urls(output));parser.close()
    return ''.join(parser.parts)
