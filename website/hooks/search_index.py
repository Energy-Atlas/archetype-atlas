"""Index each suite page once, by its summary, so search stays small (ADR 0043).

The generator writes `search-summaries.json` ({page location: summary}) beside the pages.
Their section entries are dropped and the page entry's text becomes the summary: the
name, ID, template, building type and kind. Guides keep MkDocs' full-text entries.
"""
import html
import json
from pathlib import Path


def compact(index, summaries):
    docs, seen = [], set()
    for entry in index['docs']:
        location = entry['location'].split('#', 1)[0]
        if location not in summaries:
            docs.append(entry)
            continue
        if location in seen or '#' in entry['location']:
            continue
        seen.add(location)
        docs.append({**entry, 'location': location, 'text': html.escape(summaries[location])})
    for location in sorted(set(summaries) - seen):
        docs.append({'location': location, 'title': html.escape(summaries[location].split(' · ', 1)[0]),
                     'text': html.escape(summaries[location])})
    return {**index, 'docs': docs}


def on_post_build(config):
    summaries_path = Path(config['docs_dir'])/'search-summaries.json'
    if not summaries_path.exists():
        return
    summaries = json.loads(summaries_path.read_text(encoding='utf-8'))
    path = Path(config['site_dir'])/'search/search_index.json'
    index = compact(json.loads(path.read_text(encoding='utf-8')), summaries)
    path.write_bytes((json.dumps(index, ensure_ascii=False, allow_nan=False, separators=(',', ':'))+'\n').encode('utf-8'))


# MkDocs' public event-priority attribute keeps this hook after search generation.
# Avoid a MkDocs import so pure data checks run with the base research dependencies.
on_post_build.mkdocs_priority = -100
