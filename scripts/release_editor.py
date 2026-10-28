"""Edit release 2.0.0 in place: re-derive its content-hashed IDs, add the construction alternates, declare it (ADR 0046 sections 8-10).

python -m scripts.release_editor            # rewrite data/atlas-releases/v2.0.0 and its id-map.json
python -m scripts.release_editor --check    # fail unless the release already equals what the editor writes

Release 2.0.0 was written by the 1.x writers, which left the tree in stage X1.3, so later changes are
edits of the release itself (user decision, milestone B). This edit makes every commercial ID that
hashes content agree with its content, once, under rules a consumer can recompute on any interpreter:
- **library** (`commercial/<template>/library/{materials,assemblies}.json`): `<template>.<origin>.<h6>`
  over the record without `id` and `name`, materials first; assemblies cite materials by their new ID;
- **construction sets** (`commercial/<template>/<type>/constructions/`): `<template>.<type>.<stem>.<h6>`
  over the set without `id` and `name`, every set ID written as one placeholder (sets cite each other);
- **programs** (`commercial/.../programs/`): `<template>.<type>.<mode>.<stem>.<h6>` over the program
  without `id` and `name`, service citations written as one placeholder (scripts.atlas_programs.program_id),
  source programs before the mixes that cite them.
Library and set hashes round every float to nine significant digits first: the fitted unified assemblies
(scripts.construction_equivalence) differ in the last bits between interpreters and math libraries, which
is why their releases needed a pinned CPython (user decision U). Program values come from IEEE arithmetic
on source values and hash exactly, as before. IDs already equal to their rule are kept. Library records that agree to nine significant digits get
one ID and become one record, the one with the lowest earlier ID (57 fitted assemblies at the first edit,
at most 1.04e-9 relative apart).

Every reference in the release follows (program and set files are renamed), the manifest is rewritten, and
`id-map.json` at the release root maps each changed ID to its new one. The residential tree keeps its own
IDs. Running the editor on its output changes nothing (`--check`).
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

from scripts import atlas_constructions, atlas_snapshot
from scripts.atlas_format import canonical, h6, slug, suite_bytes, table_bytes
from scripts.atlas_programs import SERVICE, SERVICE_ID
from scripts.common import ROOT, load_json
from scripts.iecc_commercial_values import layered

ID_MAP = 'id-map.json'
# Milestone B closes with the IDs settled, so the release is declared (stage B5); a later edit makes a new release.
STATUS = 'released'
ALTERNATES = ROOT/'data/program-inputs/construction-alternates-v1.json'
SET = '@set'
DIGITS = 9


def rounded(value):
    """Floats to nine significant digits, so a hash does not depend on the interpreter's last bits."""
    if isinstance(value, bool) or not isinstance(value, (float, dict, list)):
        return value
    if isinstance(value, float):
        return float(format(value, f'.{DIGITS}g'))
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    return [rounded(v) for v in value]


def rehash(old, content):
    return old.rsplit('.', 1)[0]+'.'+h6(content)


class Substitution:
    """Replaces whole IDs in text; an ID may be followed by a dotted or colon suffix (context keys, `:composition`).

    Readable IDs are dotted tokens; each token's longest dotted prefix that is a known ID is replaced.
    """
    TOKEN = re.compile(r'(?<![A-Za-z0-9_.-])[A-Za-z0-9@_-]+(?:\.[A-Za-z0-9_-]+)+')

    def __init__(self, ids):
        self.ids = dict(ids)

    def replace(self, match):
        token = match[0]
        parts = token.split('.')
        for end in range(len(parts), 1, -1):
            head = '.'.join(parts[:end])
            if head in self.ids:
                return self.ids[head] + token[len(head):]
        return token

    def __call__(self, text):
        return self.TOKEN.sub(self.replace, text) if self.ids else text


def library_ids(files):
    ids = {}
    for table in ('materials', 'assemblies'):  # assemblies cite materials, never the reverse
        substitute = Substitution(ids)
        for path in sorted(p for p in files if p.startswith('commercial/') and p.endswith(f'/library/{table}.json')):
            for old, record in json.loads(files[path]).items():
                record = json.loads(substitute(canonical(record)))
                new = rehash(old, rounded({k: v for k, v in record.items() if k not in ('id', 'name')}))
                if new != old:
                    ids[old] = new
    return ids


def set_ids(files, library):
    paths = sorted(p for p in files if p.startswith('commercial/') and '/constructions/' in p)
    sets = [json.loads(files[p])['id'] for p in paths]
    placeholder, substitute = Substitution({s: SET for s in sets}), Substitution(library)
    ids = {}
    for path, old in zip(paths, sets):
        record = json.loads(substitute(canonical(json.loads(files[path]))))
        content = json.loads(placeholder(canonical({k: v for k, v in record.items() if k not in ('id', 'name')})))
        new = rehash(old, rounded(content))
        if new != old:
            ids[old] = new
    return ids


def program_ids(files):
    paths = sorted(p for p in files if p.startswith('commercial/') and '/programs/' in p)
    records = {p: json.loads(files[p]) for p in paths}
    ids = {}

    def hash_pass(composed):
        substitute = Substitution(ids)
        for path in paths:
            record = records[path]
            if (record.get('derivation') == 'composed') != composed:
                continue
            content = json.loads(substitute(canonical({k: v for k, v in record.items() if k not in ('id', 'name')})))
            content = json.loads(SERVICE_ID.sub(json.dumps(SERVICE), canonical(content)))
            new = rehash(record['id'], content)
            if new != record['id']:
                ids[record['id']] = new
            else:
                ids.pop(record['id'], None)
    hash_pass(False)  # source programs cite no program
    for _ in range(10):  # mixes cite members and other mixes: repeat until no ID moves
        before = dict(ids)
        hash_pass(True)
        if ids == before:
            return ids
    raise ValueError('Mix IDs do not settle')


def joins_twins(value, ids):
    """Whether a list names two different IDs that become one (merging them would repeat an entry)."""
    if isinstance(value, dict):
        return any(joins_twins(v, ids) for v in value.values())
    if isinstance(value, list):
        named = {v for v in value if isinstance(v, str) and v in ids}
        return len({ids[v] for v in named}) < len(named) or any(joins_twins(v, ids) for v in value)
    return False


def origin(record):
    """The readable middle of a library ID, as the 1.x construction writer formed it."""
    return slug(str(record.get('name') or record.get('model') or 'record'))[:60].strip('-')


def with_alternates(files, document=None):
    """The release with the PNNL prototype constructions as alternates (stage B3, user decision P1).

    Each role of a 90.1 context whose prototype construction differs by more than 1% from the set's own
    building default gets `alternates.<role>` in its detailed fields: the compared atlas values and every
    prototype variant with its area share, assembly ID and evidence. Every set of a folder is compared on its
    own (the small hotel of 90.1-2007 and 2013 holds a base set and an overlay). The prototype assemblies and
    materials join the template library under rule IDs, their evidence rows the folder's evidence file.
    Applying it again changes nothing.
    """
    from scripts.construction_alternates import atlas_values, differs
    document = document or load_json(ALTERNATES)
    out = dict(files)
    suite = atlas_constructions.read_files(files)
    for template, folders in document['alternates'].items():
        tables = {t: json.loads(out[f'commercial/{template}/library/{t}.json']) for t in ('materials', 'assemblies')}
        ids = {'materials': {}, 'assemblies': {}}

        def add(table, key, record):
            if key not in ids[table]:
                rid = f'{template}.{origin(record)}.{h6(rounded({k: v for k, v in record.items() if k not in ("id", "name")}))}'
                tables[table].setdefault(rid, {**record, 'id': rid})
                ids[table][key] = rid
            return ids[table][key]
        for folder, contexts in folders.items():
            evidence_path = f'evidence/commercial/{template}/{folder}.json'
            evidence = json.loads(out[evidence_path])
            for path in sorted(p for p in out if p.startswith(f'commercial/{template}/{folder}/constructions/')):
                set_alternates(out, path, contexts, document, suite, evidence, add, template, atlas_values, differs)
            out[evidence_path] = table_bytes(evidence)
        for table in ('materials', 'assemblies'):
            out[f'commercial/{template}/library/{table}.json'] = table_bytes(tables[table])
    return out


def set_alternates(out, path, contexts, document, suite, evidence, add, template, atlas_values, differs):
    """The alternates of one construction set, against its own building defaults."""
    record = json.loads(out[path])
    for key, roles in contexts.items():
        if key not in record['contexts']:
            continue
        fields = record['contexts'][key]['detailed']['fields']
        fields.pop('alternates', None)
        atlas_document = suite.export(record['id'], key, 'detailed')
        alternates = {}
        for role, entry in roles.items():
            atlas = atlas_values(atlas_document, role)
            if atlas is None or not any(differs(v['values'].get(f), atlas.get(f)) for v in entry['variants'] for f in v['values']):
                continue
            variants = []
            for variant in entry['variants']:
                source = document['assemblies'][variant['assembly']]
                row = document['evidence'][variant['evidence_id']]
                evidence.setdefault(row['id'], row)
                assembly = {k: v for k, v in source.items() if k != 'layers'}
                if 'layers' in source:
                    layers = []
                    for layer in source['layers']:
                        material = document['materials'][layer['material']]
                        material = {**material, 'property_evidence': {k: row['id'] for k in material['properties']}}
                        layers.append({'material_id': add('materials', layer['material'], material), 'order': layer['order']})
                    assembly.update(layers=layers, status='ready', source_family='pnnl_prototype',
                                    template=template.replace('90-1-', '90.1-'), climate_group=None, applicability={},
                                    source_attributes={'pnnl_construction': source['name']}, source_surface_ids=[],
                                    source_adjacency=[], source_parameters={}, target_adjustment=None)
                    # Simple glazing carries no layer metrics, as the openstudio-standards glazing assemblies.
                    assembly.setdefault('layer_orientation', 'exterior_to_interior')
                    assembly.setdefault('metrics', {})
                assembly['evidence_ids'] = [row['id']]
                variants.append({'construction': variant['construction'], 'area_share': variant['area_share'],
                                 'values': variant['values'], 'assembly_id': add('assemblies', variant['assembly'], assembly),
                                 'evidence_id': row['id']})
            alternates[role] = {'source': 'pnnl_prototype', 'atlas_values': {k: v for k, v in atlas.items() if k != 'assembly_id'},
                                'variants': variants}
        if alternates:
            fields['alternates'] = alternates
    out[path] = (layered(record, 3)+'\n').encode('utf-8')


def edit(files):
    """(edited files, {old ID: new ID})."""
    files = with_alternates(files)
    library = library_ids(files)
    sets = set_ids(files, library)
    programs = program_ids(files)
    ids = {**library, **sets, **programs}
    counts = Counter(library.values())
    twins = {old: new for old, new in library.items() if counts[new] > 1}
    joined = [p for p, d in files.items() if twins and p.endswith('.json') and joins_twins(json.loads(d), twins)]
    if joined:
        raise ValueError('A list names library twins that would merge: '+', '.join(joined[:3]))
    if len(set(sets.values()) | set(programs.values())) != len(sets) + len(programs) or set(ids.values()) & (set(ids) - set(ids.values())):
        raise ValueError('Re-derived set or program IDs collide')
    out, substitute = {}, Substitution(ids)
    for path, data in files.items():
        if path in ('manifest.json', ID_MAP):
            continue
        new_path = '/'.join(ids.get(part[:-5], part[:-5])+'.json' if part.endswith('.json') else part for part in path.split('/'))
        if path.startswith('commercial/') and '/library/' in path:
            table = {}
            for old, record in sorted(json.loads(data).items()):  # twins: the lowest earlier ID's record stays
                table.setdefault(ids.get(old, old), json.loads(substitute(canonical(record))))
            out[new_path] = table_bytes(table)
            continue
        out[new_path] = substitute(data.decode('utf-8')).encode('utf-8') if path.endswith('.json') else data
    previous = json.loads(files[ID_MAP])['ids'] if ID_MAP in files else {}
    chained = {old: ids.get(new, new) for old, new in previous.items()}
    chained.update({old: new for old, new in ids.items() if old not in chained.values()})
    if chained:
        record = {'schema_version': '1.0.0', 'decision': 'docs/adr/0046-release-2-0-0.md',
                  'description': 'IDs of release 2.0.0 as first committed (and of release 1.6.0, which it kept) mapped to their '
                                 're-derived values (ADR 0046 section 8).',
                  'ids': dict(sorted(chained.items()))}
        out[ID_MAP] = (layered(record, 1)+'\n').encode('utf-8')
    return out, ids


def manifest(files, listed):
    listed = json.loads(json.dumps(listed))
    listed['files'] = {p: {'sha256': atlas_snapshot.sha(d), 'bytes': len(d)} for p, d in sorted(files.items())}
    edits = [e for e in listed.get('edited_by', []) if e.get('command') != 'python -m scripts.release_editor']
    listed['edited_by'] = [*edits, {'stages': ['B1', 'B3'], 'command': 'python -m scripts.release_editor', 'id_map': ID_MAP,
                                    'inputs': [ALTERNATES.relative_to(ROOT).as_posix()],
                                    'decision': 'docs/adr/0046-release-2-0-0.md'}]
    listed['status'] = STATUS
    return suite_bytes(listed)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    listed = atlas_snapshot.verify()
    files = atlas_snapshot.files()
    edited, ids = edit(files)
    if args.check:
        if ids:
            raise SystemExit(f'{len(ids)} IDs differ from their rules, e.g. {next(iter(ids))}; run python -m scripts.release_editor')
        stale = [p for p, d in edited.items() if files.get(p) != d] + ([] if listed.get('status') == STATUS else ['manifest.json'])
        if stale:
            raise SystemExit(f'{len(stale)} release files differ from the edit, e.g. {stale[0]}; run python -m scripts.release_editor')
        print('Release 2.0.0 IDs agree with their rules')
        return
    edited['manifest.json'] = manifest(edited, listed)
    target = atlas_snapshot.TARGET
    for path in sorted(set(files) - set(edited)):
        (target/path).unlink()
    for path, data in sorted(edited.items()):
        out = target/path
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.is_file() or out.read_bytes() != data:
            out.write_bytes(data)
    atlas_snapshot.verify()
    print(f'Release 2.0.0 edited: {len(ids)} IDs re-derived; {len(edited)} files')


if __name__ == '__main__':
    main()
