"""Keep record titles searchable without duplicating full canonical evidence."""
import json
import html
from pathlib import Path


def compact_records(index,record_titles):
    docs=[];seen=set()
    for entry in index['docs']:
        location=entry['location'].split('#',1)[0]
        if location in record_titles:
            if location in seen:
                continue
            seen.add(location)
            docs.append({**entry,'location':location,'text':''})
        else:
            docs.append(entry)
    # Some existing detail kinds intentionally opt out of full-text indexing.
    # Their exact generated page names still provide safe, small title entries.
    for location,title in sorted(record_titles.items()):
        if location not in seen:
            docs.append({'location':location,'title':html.escape(title),'text':''})
    return {**index,'docs':docs}


def on_post_build(config):
    path=Path(config['site_dir'])/'search/search_index.json'
    record_titles={}
    for catalogue in (Path(config['docs_dir'])/'releases').glob('*/catalogue.json'):
        packet=json.loads(catalogue.read_text(encoding='utf-8'))
        record_titles.update({entry['path'].removesuffix('.md')+'/':entry['name'] for entry in packet['entries']})
    index=json.loads(path.read_text(encoding='utf-8'))
    result=compact_records(index,record_titles)
    indexed={entry['location'].split('#',1)[0] for entry in result['docs']}
    if not set(record_titles)<=indexed:
        raise ValueError('Derived search index lacks one or more catalogue record titles')
    path.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',
                    encoding='utf-8',newline='\n')


# MkDocs' public event-priority attribute keeps this hook after search generation.
# Avoid a MkDocs import so pure data checks run with the base research dependencies.
on_post_build.mkdocs_priority=-100
