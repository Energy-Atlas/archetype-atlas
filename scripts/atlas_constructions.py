"""Write and read ADR 0036 construction suites for commercial template x building-type folders.

Each construction set becomes one file holding, per context, its detailed and
unified documents without their embedded resources; fields equal across the
set's contexts are stored once. Assemblies and materials go to one library per
template, evidence to the evidence tree. Reading the files back reproduces the
current standalone documents (detailed 3.0.0, unified 2.0.0) with readable IDs.

python -m scripts.atlas_constructions --template 90.1-2019 --building-type MediumOffice
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

from scripts.atlas_format import canonical, h6, slug, suite_bytes, table_bytes, translate
from scripts.common import ROOT, load_json

EQUIVALENT = ROOT/'data/construction-equivalent-releases/v1.1.0/catalogue.json'
DETAILED = ROOT/'data/construction-releases/v2.0.0/catalogue.json'
OUTPUT = ROOT/'build/atlas-release/v1.0.0'
RESIDENTIAL = 'ResStock SDR source fixture'
RESOURCES = ('assemblies', 'materials')
REPRESENTATIONS = ('detailed', 'unified')
SET = '@set'  # placeholder for set IDs while content hashes are computed
TOKEN = re.compile(SET+r':(construction-[0-9a-f]{24})')
VALUE = '@v:'  # a list element stored once in the set's value table

Build = collections.namedtuple('Build', 'files ids contexts')  # ids: template slug -> old ID -> new ID


class Sources:
    """The combined construction release and the catalogue of its current sets and contexts."""

    def __init__(self):
        from scripts.construction_foundation_release import load_release
        self.release = load_release()
        catalogue = load_json(EQUIVALENT)
        detailed = load_json(DETAILED)['contexts']
        self.sets = catalogue['construction_sets']
        self.contexts = collections.defaultdict(list)
        for context in catalogue['contexts'].values():
            self.contexts[detailed[context['detailed_context_id']]['construction_set_id']].append(context)


def load_sources():
    return Sources()


def strings(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)
    elif isinstance(value, str):
        yield value


def sorted_ids(value):
    """A sorted list of unique IDs; set tokens are excluded because resolving them reorders the list."""
    return (isinstance(value, list) and all(isinstance(v, str) and not v.startswith(SET) for v in value)
            and value == sorted(set(value)))


def factor(documents):
    """Fields equal across all documents once; for dict fields, equal sub-keys once, and
    for sub-keys holding sorted ID lists, the IDs every document shares once."""
    fields, partial, lists = {}, {}, {}
    for key in sorted(set().union(*documents)):
        first = documents[0].get(key)
        if all(key in d and d[key] == first for d in documents):
            fields[key] = first
        elif all(isinstance(d.get(key), dict) for d in documents):
            shared = {s: v for s, v in first.items() if all(s in d[key] and d[key][s] == v for d in documents)}
            if shared:
                partial[key] = shared
            for sub in first:
                if sub not in shared and all(sorted_ids(d[key].get(sub)) for d in documents):
                    lists.setdefault(key, {})[sub] = sorted(set.intersection(*(set(d[key][sub]) for d in documents)))
    deltas = []
    for d in documents:
        delta = {}
        for key, value in d.items():
            if key in fields:
                continue
            if key in partial or key in lists:
                value = {s: (sorted(set(v)-set(lists[key][s])) if s in lists.get(key, {}) else v)
                         for s, v in value.items() if s not in partial.get(key, {})}
                value = {s: v for s, v in value.items() if v or s not in lists.get(key, {})}
                if not value:
                    continue
            delta[key] = value
        deltas.append(delta)
    return {'fields': fields, 'partial': partial, 'lists': lists}, deltas


def closures(skeleton, tables, evidence):
    """The resources a document embeds, derived from what it and its resources reference."""
    refs = set(strings(skeleton))
    assemblies = sorted(refs & tables['assemblies'].keys())
    refs |= set(strings([tables['assemblies'][a] for a in assemblies]))
    materials = sorted(refs & tables['materials'].keys())
    refs |= set(strings([tables['materials'][m] for m in materials]))
    cited = refs & evidence.keys()
    cited |= set(strings([evidence[e] for e in cited])) & evidence.keys()  # evidence citing evidence, one hop
    return {'assemblies': assemblies, 'materials': materials, 'evidence': sorted(cited)}


def intern(deltas, minimum=64):
    """Store values repeated within a set once: top-level fields, the sub-keys of dict fields,
    and the elements of lists there. A repeated list element becomes the string '@v:<id>'."""
    def candidates(delta):
        for field, value in delta.items():
            if isinstance(value, dict) and value:
                for sub, v in value.items():
                    yield (field, sub), v
            else:
                yield (field,), value
    if any(s.startswith(VALUE) for d in deltas for s in strings(d)):
        raise ValueError('A string starts with the reserved value-reference prefix '+VALUE)
    counts = collections.Counter(canonical(v) for d in deltas for _, v in candidates(d))
    counts.update(canonical(e) for d in deltas for _, v in candidates(d) if isinstance(v, list) for e in v)
    values = {}

    def ref(value):
        text = canonical(value)
        if counts[text] > 1 and len(text) >= minimum:
            vid = 'v-'+hashlib.sha256(text.encode()).hexdigest()[:10]
            if values.setdefault(vid, value) != value:
                raise ValueError('Value ID clash: '+vid)
            return vid
        return None
    out = []
    for delta in deltas:
        fields, refs = {}, {}
        for path, value in candidates(delta):
            vid = ref(value)
            if vid:
                refs['/'.join(path)] = vid
                continue
            if isinstance(value, list):
                value = [VALUE+v if (v := ref(e)) else e for e in value]
            if len(path) == 2:
                fields.setdefault(path[0], {})[path[1]] = value
            else:
                fields[path[0]] = value
        out.append({'fields': fields, 'refs': refs})
    return values, out


def context_keys(contexts):
    """Climate zone alone when it identifies the context within its set, else climate and reference."""
    unique = len({c['climate_zone'] for c in contexts}) == len(contexts)
    return {c['detailed_context_id']: slug(c['climate_zone']) if unique else slug(c['climate_zone'])+'.'+slug(c['reference_id'])
            for c in contexts}


def origin(record):
    return slug(str(record.get('name') or record.get('model') or record.get('role') or 'record'))[:60].strip('-')


def library_ids(library, template):
    """Readable, content-hashed IDs for one template's materials, then assemblies (which cite materials)."""
    ids = {}
    tslug = slug(template)
    for table in ('materials', 'assemblies'):
        for old in sorted(library[table]):
            record = translate(library[table][old], ids)
            new = f'{tslug}.{origin(record)}.{h6({k: v for k, v in record.items() if k not in ("id", "name")})}'
            ids[old] = new
    return ids


def build_folders(sources, folders):
    from scripts.construction_foundation_release import export_pair
    wanted = set(folders)
    if any(template == RESIDENTIAL for template, _ in wanted):
        raise ValueError('Residential construction storage is deferred (ADR 0036)')
    sets = sorted(sid for sid, s in sources.sets.items() if (s['source']['template'], s['source']['building_type']) in wanted)
    missing = wanted - {(sources.sets[s]['source']['template'], sources.sets[s]['source']['building_type']) for s in sets}
    if missing:
        raise ValueError(f'No construction sets for {sorted(missing)}')
    # A resource shared by several templates is copied into each template's library.
    documents, library, evidence = {}, collections.defaultdict(lambda: {t: {} for t in RESOURCES}), {}
    for sid in sets:
        template = sources.sets[sid]['source']['template']
        rows = sorted(sources.contexts[sid], key=lambda c: (c['climate_zone'], c['reference_id']))
        documents[sid] = [(row, *export_pair(row['detailed_context_id'], release=sources.release)) for row in rows]
        for _, *pair in documents[sid]:
            for document in pair:
                for table in RESOURCES:
                    for key, record in document[table].items():
                        if library[template][table].setdefault(key, record) != record:
                            raise ValueError(f'{key} differs between documents')
                for key, record in document['evidence'].items():
                    if evidence.setdefault(key, record) != record:
                        raise ValueError(f'{key} differs between documents')
    ids = {slug(template): library_ids(tables, template) for template, tables in library.items()}
    files, contexts = {}, {}
    library_evidence, translated = collections.defaultdict(set), collections.defaultdict(dict)
    for template, tables in sorted(library.items()):
        tslug = slug(template)
        for table in RESOURCES:
            records = {ids[tslug][k]: translate(v, ids[tslug]) for k, v in tables[table].items()}
            files[f'commercial/{tslug}/library/{table}.json'] = table_bytes(records)
            library_evidence[tslug] |= set(strings(records)) & evidence.keys()
            translated[tslug][table] = records
    # Sets can cite each other (an overlay lists the package it inherits from), so every
    # set and context ID is a token until all sets are hashed, then replaced at once.
    tokens, keys = {}, {}
    for sid in sets:
        keys[sid] = context_keys([row for row, *_ in documents[sid]])
        tokens[sid] = SET+':'+sid
        for row, detailed, unified in documents[sid]:
            key = keys[sid][row['detailed_context_id']]
            tokens[detailed['id']], tokens[unified['id']] = f'{SET}:{sid}.{key}', f'{SET}:{sid}.{key}.unified'
    records, final = {}, {}
    for sid in sets:
        tslug = slug(sources.sets[sid]['source']['template'])
        records[sid], final[sid] = suite(sources, sid, documents[sid], {**ids[tslug], **tokens}, translated[tslug], evidence)
    resolve = lambda text: TOKEN.sub(lambda m: final[m[1]], text)
    folder_evidence = collections.defaultdict(set)
    for sid in sets:
        meta = sources.sets[sid]['source']
        tslug, bslug = slug(meta['template']), slug(meta['building_type'])
        record = json.loads(resolve(json.dumps(records[sid], ensure_ascii=False)))
        files[f'commercial/{tslug}/{bslug}/constructions/{record["id"]}.json'] = suite_bytes(record)
        for row, *_ in documents[sid]:
            contexts[row['detailed_context_id']] = (record['id'], keys[sid][row['detailed_context_id']])
        for _, *pair in documents[sid]:
            folder_evidence[(tslug, bslug)] |= {k for d in pair for k in d['evidence']} - library_evidence[tslug]
    for tslug in ids:
        ids[tslug].update({old: resolve(token) for old, token in tokens.items()})
    for tslug, keys in library_evidence.items():
        files[f'evidence/commercial/{tslug}/library.json'] = table_bytes({k: translate(evidence[k], ids[tslug]) for k in keys})
    for (tslug, bslug), keys in folder_evidence.items():
        files[f'evidence/commercial/{tslug}/{bslug}.json'] = table_bytes({k: translate(evidence[k], ids[tslug]) for k in keys})
    return Build(files, ids, contexts)


def suite(sources, sid, documents, ids, tables, evidence):
    """One set file with set IDs still as tokens, and the set's own content-hashed ID.

    Per-context documents lose their embedded resources, kept as ID lists only where they
    cannot be derived from references; common fields are stored once. The hash treats
    every set ID as the same placeholder, so it depends on content only.
    """
    entry = sources.sets[sid]
    keys = context_keys([row for row, *_ in documents])
    skeletons = {r: [] for r in REPRESENTATIONS}
    for _, *pair in documents:
        for representation, document in zip(REPRESENTATIONS, pair):
            skeleton = translate({k: v for k, v in document.items() if k not in (*RESOURCES, 'evidence')}, ids)
            explicit = {**{t: sorted(ids[k] for k in document[t]) for t in RESOURCES}, 'evidence': sorted(document['evidence'])}
            derived = closures(skeleton, tables, evidence)
            skeleton.update({t: v for t, v in explicit.items() if derived[t] != v})
            skeletons[representation].append(skeleton)
    common, deltas = {}, []
    for representation, docs in skeletons.items():
        common[representation], rows = factor(docs)
        deltas += [(keys[row['detailed_context_id']], representation, delta) for (row, *_), delta in zip(documents, rows)]
    if any('/' in k for _, _, d in deltas for f, v in d.items() for k in [f, *(v if isinstance(v, dict) else [])]):
        raise ValueError('A field name contains "/", which value references reserve: '+sid)
    values, interned = intern([d for _, _, d in deltas])
    per_context = collections.defaultdict(dict)
    for (key, representation, _), delta in zip(deltas, interned):
        per_context[key][representation] = delta
    name = entry['name']
    building_type = entry['source']['building_type']
    stem = name[len(building_type):].strip() if name.startswith(building_type) else name
    record = {'name': name, 'scope': entry['scope'], 'source': translate(entry['source'], ids),
              'common': common, 'values': values, 'contexts': dict(per_context)}
    content = json.loads(TOKEN.sub(SET, json.dumps({k: v for k, v in record.items() if k != 'name'})))
    new = f'{slug(entry["source"]["template"])}.{slug(building_type)}.{slug(stem)}.{h6(content)}'
    return {**record, 'id': ids[sid]}, new


class ConstructionSuite:
    """Written construction files read back into the standalone detailed and unified documents."""

    def __init__(self, files):
        self.sets, self.library, self.evidence = {}, {t: {} for t in RESOURCES}, {}
        for path, data in files.items():
            if '/constructions/' in path:
                record = json.loads(data)
                self.sets[record['id']] = record
            elif '/library/' in path and Path(path).stem in RESOURCES:
                self.library[Path(path).stem].update(json.loads(data))
            elif path.startswith('evidence/') and not path.endswith('glossary.json'):
                self.evidence.update(json.loads(data))

    def export(self, set_id, key, representation):
        record = self.sets[set_id]
        common, stored = record['common'][representation], record['contexts'][key][representation]
        values = record['values']
        expand = lambda v: [values[e[len(VALUE):]] if isinstance(e, str) and e.startswith(VALUE) else e for e in v] if isinstance(v, list) else v
        delta = {f: ({s: expand(x) for s, x in v.items()} if isinstance(v, dict) else expand(v))
                 for f, v in json.loads(json.dumps(stored['fields'])).items()}
        for path, vid in stored['refs'].items():
            field, *sub = path.split('/')
            if sub:
                delta.setdefault(field, {})[sub[0]] = record['values'][vid]
            else:
                delta[field] = record['values'][vid]
        document = dict(common['fields'])
        merged = set(common['partial']) | set(common['lists'])
        for field in merged:
            document[field] = {**common['partial'].get(field, {}), **delta.get(field, {})}
            for sub, shared in common['lists'].get(field, {}).items():
                document[field][sub] = sorted(set(shared) | set(document[field].get(sub, [])))
        document.update({k: v for k, v in delta.items() if k not in merged})
        derived = closures(document, self.library, self.evidence)
        for table in RESOURCES:
            document[table] = {i: self.library[table][i] for i in document.get(table, derived[table])}
        document['evidence'] = {i: self.evidence[i] for i in document.get('evidence', derived['evidence'])}
        return json.loads(json.dumps(document))


def read_files(files):
    return ConstructionSuite(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', required=True)
    parser.add_argument('--building-type', action='append', required=True)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    built = build_folders(load_sources(), [(args.template, b) for b in args.building_type])
    for path, data in built.files.items():
        out = args.output/path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    sets = sum('/constructions/' in p for p in built.files)
    print(f'Wrote {sets} construction sets ({len(built.contexts)} contexts) and {len(built.files)-sets} tables')


if __name__ == '__main__':
    main()
