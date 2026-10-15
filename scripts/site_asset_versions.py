"""Bind generated HTML to exact first-party interaction/style asset bytes."""
import hashlib
import html
import re
from pathlib import Path
from urllib.parse import parse_qsl,urlencode,urlsplit,urlunsplit

from scripts.common import ROOT


def version_asset_urls(text,assets=ROOT/'website/assets'):
    def replace(match):
        url=urlsplit(html.unescape(match[2]))
        if url.scheme or url.netloc:return match[0]
        local=re.fullmatch(r'(?:/archetype-atlas/|(?:\.\./)*)assets/([A-Za-z0-9_.-]+)',url.path)
        if not local:return match[0]
        path=Path(assets)/local[1]
        if not path.is_file():return match[0]
        digest=hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        query=[(k,v) for k,v in parse_qsl(url.query,keep_blank_values=True) if k!='v']
        query.append(('v',digest))
        updated=urlunsplit(('', '',url.path,urlencode(query),url.fragment))
        return match[1]+'="'+html.escape(updated,quote=True)+'"'
    return re.sub(r'\b(href|src)="([^"]+)"',replace,text)
