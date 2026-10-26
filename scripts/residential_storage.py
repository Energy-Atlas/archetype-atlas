"""Shared pieces of the ADR 0038 residential release tree.

A residential folder is `residential/<family-or-template>/<building-type>/`:
- `programs/<id>.json`: one file per dwelling program;
- `schedules.json`: the folder's ruleset schedules, each day profile once (as the
  commercial folders store them);
- `schedules/<program-id>.json`: one dwelling's annual 8,760-hour series. A value
  array shared by several dwellings of the folder is stored once, in the file of the
  first dwelling (by ID) that uses it; the others cite its value ID;
- `constructions/<id>.json`: construction sets.
Evidence goes to `evidence/residential/<family>/...`, shared texts to the glossary.
"""
import collections
import hashlib
import json

from scripts.atlas_format import canonical, table_bytes

ANNUAL_KEYS = ('annual_values', 'values')  # definition-release series, recovered (Program JSON shaped) series


def value_id(values):
    return 'a-'+hashlib.sha256(canonical(values).encode()).hexdigest()[:12]


def annual_files(folder, owners):
    """Annual schedule files for one folder.

    owners: {program ID: {schedule ID: record with its values}}. Returns {path: bytes}.
    Each record keeps its own metadata; its values become a value ID. Values are stored
    in the first owner's file (owners sorted by program ID) that cites them.
    """
    stored, files = set(), {}
    for program_id in sorted(owners):
        schedules, values = {}, {}
        for sid, record in sorted(owners[program_id].items()):
            key = next(k for k in ANNUAL_KEYS if k in record)
            vid = value_id(record[key])
            schedules[sid] = {**{k: v for k, v in record.items() if k != key}, 'values_key': key, 'values': vid}
            if vid not in stored:
                stored.add(vid)
                values[vid] = record[key]
        files[f'{folder}schedules/{program_id}.json'] = table_bytes({'schedules': schedules, 'values': values}, sections=True)
    return files


def read_annual(files, folder):
    """{schedule ID: record with its values} of every annual schedule file in a folder."""
    tables = [json.loads(data) for path, data in sorted(files.items())
              if path.startswith(folder+'schedules/') and path.endswith('.json')]
    values = {vid: v for t in tables for vid, v in t['values'].items()}
    out = {}
    for table in tables:
        for sid, record in table['schedules'].items():
            record = dict(record)
            key, vid = record.pop('values_key'), record.pop('values')
            out[sid] = {**record, key: values[vid]}
    return out


def folder_of(path):
    """The residential folder (with trailing slash) of a release path."""
    return '/'.join(path.split('/')[:3])+'/'


def program_files(files):
    """{program ID: (folder, program)} for every residential program file."""
    out = {}
    for path, data in files.items():
        if path.startswith('residential/') and '/programs/' in path:
            program = json.loads(data)
            out[program['id']] = (folder_of(path), program)
    return out


def counts(files):
    """Record counts of the residential tree."""
    programs = [p for p, _ in files.items() if p.startswith('residential/') and '/programs/' in p]
    sets = [json.loads(d) for p, d in files.items() if p.startswith('residential/') and '/constructions/' in p]
    folders = {folder_of(p) for p in programs}
    annual = sum(len(json.loads(d)['schedules']) for p, d in files.items()
                 if p.startswith('residential/') and '/schedules/' in p)
    return collections.OrderedDict([
        ('residential_folders', len(folders)), ('residential_programs', len(programs)),
        ('residential_construction_sets', len(sets)),
        ('residential_construction_contexts', sum(len(s['contexts']) for s in sets)),
        ('residential_annual_schedules', annual)])
