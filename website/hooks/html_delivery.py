"""Reduce generated template indentation, retaining literal regions verbatim."""
from html.parser import HTMLParser
import re


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
        self.parts.append(data if self.literal else re.sub(r'\n[ \t]+','\n',data))

    def handle_entityref(self,name):self.parts.append('&'+name+';')
    def handle_charref(self,name):self.parts.append('&#'+name+';')
    def handle_comment(self,data):self.parts.append('<!--'+data+'-->')
    def handle_decl(self,decl):self.parts.append('<!'+decl+'>')
    def handle_pi(self,data):self.parts.append('<?'+data+'>')


def on_post_page(output,*,page,config):
    parser=DeliveryHTML();parser.feed(output);parser.close()
    return ''.join(parser.parts)
