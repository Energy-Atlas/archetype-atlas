"""Names that tell same-named records apart, from their source distinction: the input of release 2.3.0's names (ADR 0053 section 4).

python -m scripts.distinguishing_names           # write data/program-inputs/distinguishing-names-v1.json
python -m scripts.distinguishing_names --check   # rebuild and fail unless the committed file equals it

Release 2.2.0 has programs that share a name with another program of the same folder and aggregation mode
(three `Corridor_SuperTallBuilding` in 90.1-2007), and construction sets that share a name with another set of
the folder (two `SmallHotel construction package` in 90.1-2007 and 2013). Each such record gets a name that
says what the source distinguishes:
- a program takes the openstudio-standards building type of its space-type row (`/space_types/<i>` of the
  record's evidence), as `Corridor (LargeHotel)_SuperTallBuilding`; the tall buildings draw their space types
  from the rows of other building types;
- a construction set takes its openstudio-standards row's `is_residential` (`/construction_sets/<i>` of its
  selector evidence), as `SmallHotel construction package (residential)`.
A name is outside every ID (ADR 0046 section 8), so no program ID moves; a set's name is also inside its stored
documents, so the set's ID moves with it. The space-type rows are read from the pinned openstudio-standards
files (`scripts.fetch` cache, `data/raw` or `ATLAS_RAW_ROOT`), so `--check` needs that cache or the network; the release edit reads the committed file.
"""
import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

from scripts.atlas_programs import stem
from scripts.common import ROOT
from scripts.fetch import fetch_file

OUTPUT = ROOT/'data/program-inputs/distinguishing-names-v1.json'
ADR = 'docs/adr/0053-release-2-3-0-data-corrections.md'
BASE = '2.2.0'
ROW = '/space_types/'


def raw_root():
    """The pinned source cache (`scripts.fetch`); `ATLAS_RAW_ROOT` points a worktree at another checkout's cache."""
    return Path(os.environ.get('ATLAS_RAW_ROOT', ROOT/'data/raw'))


def collisions(groups):
    return {key: ids for key, ids in groups.items() if len(ids) > 1}


def program_names(files, glossary):
    """{release 2.2.0 program ID: {'name', 'basis'}} for programs sharing a folder, mode and name."""
    groups, records = defaultdict(list), {}
    for path, data in files.items():
        if path.startswith('commercial/') and '/programs/' in path:
            record = json.loads(data)
            records[record['id']] = (path, record)
            groups[(path.split('/programs/')[0], record['mode'], record['name'])].append(record['id'])
    tables, out = {}, {}
    for (folder, _, name), ids in sorted(collisions(groups).items()):
        evidence = json.loads(files['evidence/'+folder+'.json'])
        labels = {}
        for pid in sorted(ids):
            record = records[pid][1]
            rows = {(evidence[e]['source_file'], evidence[e]['locator'].split('/')[2]) for e in record['evidence_ids']
                    if e in evidence and evidence[e]['locator'].startswith(ROW)}
            if len(rows) != 1:
                raise ValueError(f'{pid}: expected one openstudio-standards space-type row, found {sorted(rows)}')
            source_file, index = rows.pop()
            if source_file not in tables:
                entry = {**glossary['source_files'][source_file], 'id': source_file}
                tables[source_file] = json.loads(fetch_file(entry, raw_root()).read_text(encoding='utf-8'))
            row = tables[source_file]['space_types'][int(index)]
            labels[pid] = row['building_type']
        if len(set(labels.values())) != len(labels):
            raise ValueError(f'{folder} {name}: the source building types do not tell the programs apart: {labels}')
        building_type = records[ids[0]][1]['building_type']
        for pid, label in labels.items():
            out[pid] = {'name': f'{stem(name, building_type)} ({label})_{building_type}', 'previous_name': name,
                        'basis': f'openstudio-standards space-type row building_type {label}'}
    return out


def set_names(files):
    """{release 2.2.0 set ID: {'name', 'basis'}} for construction sets sharing a folder and name."""
    from scripts import atlas_constructions
    suite = atlas_constructions.read_files({p: d for p, d in files.items() if p.startswith(('commercial/', 'evidence/commercial/'))})
    groups = defaultdict(list)
    for sid, record in suite.sets.items():
        groups[(sid.rsplit('.', 2)[0], record['name'])].append(sid)
    out = {}
    for (_, name), ids in sorted(collisions(groups).items()):
        labels = {}
        for sid in sorted(ids):
            key = sorted(suite.sets[sid]['contexts'])[0]
            document = suite.export(sid, key, 'detailed')
            rows = {json.dumps(document['evidence'][d['evidence_id']]['original_value'].get('is_residential'))
                    for d in document['metadata']['selection_decisions'] if d['source_definition_id'] == sid}
            if len(rows) != 1:
                raise ValueError(f'{sid}: expected one openstudio-standards construction-set row, found {rows}')
            labels[sid] = {'"Yes"': 'residential', '"No"': 'nonresidential'}[rows.pop()]
        if len(set(labels.values())) != len(labels):
            raise ValueError(f'{name}: the source rows do not tell the sets apart: {labels}')
        for sid, label in labels.items():
            out[sid] = {'name': f'{name} ({label})', 'previous_name': name,
                        'basis': f'openstudio-standards construction-set row is_residential {"Yes" if label == "residential" else "No"}'}
    return out


def build():
    from scripts import atlas_delta
    files = atlas_delta.files(BASE)
    glossary = json.loads(files['evidence/glossary.json'])
    return {'schema_version': '1.0.0', 'decision': ADR, 'base_release': BASE,
            'description': 'Names of release records that share a name with another record of their folder (and, for '
                           'programs, aggregation mode), from the source distinction; keyed by release 2.2.0 ID.',
            'programs': program_names(files, glossary), 'construction_sets': set_names(files)}


def encode(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False)+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = encode(build())
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.relative_to(ROOT)} differs from its sources; run python -m scripts.distinguishing_names')
        print(f'{OUTPUT.relative_to(ROOT).as_posix()} reproduces from release {BASE} and openstudio-standards')
        return
    OUTPUT.write_bytes(data)
    document = json.loads(data)
    print(f'Wrote {OUTPUT.relative_to(ROOT).as_posix()}: {len(document["programs"])} programs, {len(document["construction_sets"])} sets')


if __name__ == '__main__':
    main()
