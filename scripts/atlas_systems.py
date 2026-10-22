"""Write and read ADR 0036 systems for commercial template x building-type folders.

HVAC systems, their components, services and water-reporting records go to tables
in their folder; performance curves and rules, shared between building types, go
to one library per template. Schedules join the folder schedules table and
evidence the evidence tree. Programs are cited by their new IDs, so a folder's
program build comes first.

python -m scripts.atlas_systems --template 90.1-2019 --building-type Hospital
"""
import argparse
import collections
import json
import re
from pathlib import Path

from scripts import atlas_programs
from scripts.atlas_format import h6, merge, slug, table_bytes, translate
from scripts.common import ROOT, load_json

DEFINITIONS = ROOT/'data/definition-releases/v0.1.1'
WATER = ROOT/'data/water-reporting-releases/v0.1.0/water-reporting.json'
COMPLETION = ROOT/'data/completion-releases/v0.1.0/commercial-completion.json'
OUTPUT = ROOT/'build/atlas-release/v1.0.0'
RESIDENTIAL = 'existing_stock_source_fixture'
LIBRARY = {'performance_curve': 'curves', 'conditional_performance_rule': 'performance-rules'}
COMPONENT = re.compile(r'"((?:component|curve|performance-rule)-[0-9a-f]{20,24})"')
SCHEDULE = re.compile(r'"((?:schedule|water_reporting_schedule)-[0-9a-f]{20,24})"')
EVIDENCE = re.compile(r'(?<![a-z_-])(?:evidence|provenance)-[0-9a-f]{20,24}')
COMPLETION_EVIDENCE = re.compile(r'completion_evidence-[0-9a-f]{20}')
SELF, SYSTEM = '@self', '@system'  # placeholders while content hashes are computed

Build = collections.namedtuple('Build', 'files ids')


class Sources:
    """Definition systems, components and services, water reporting and completion evidence."""

    def __init__(self):
        self.definitions = atlas_programs.load_sources()
        self.hvac = {h['id']: h for h in load_json(DEFINITIONS/'hvac_systems.json')}
        self.components = {c['id']: c for c in load_json(DEFINITIONS/'components.json')}
        self.services = {s['id']: s for s in load_json(DEFINITIONS/'services.json')}
        self.water = load_json(WATER)
        self.completion = load_json(COMPLETION)['evidence']
        self.schedules = {**self.definitions.schedules, **{s['id']: s for s in self.water['schedules']}}


def load_sources():
    return Sources()


def closure(sources, roots):
    """Every component, curve and rule reachable from the given records."""
    todo, seen = set(COMPONENT.findall(json.dumps(roots))) & sources.components.keys(), set()
    while todo:
        c = todo.pop()
        if c not in seen:
            seen.add(c)
            todo |= set(COMPONENT.findall(json.dumps(sources.components[c]))) & sources.components.keys()
    return seen


def origin(record):
    if record.get('role') == 'performance_curve':
        d = record.get('definition') or {}
        text = ' '.join(str(d.get(k) or '') for k in ('category', 'dependent_variable')) or 'curve'
    elif record.get('role') == 'conditional_performance_rule':
        text = record.get('equipment_table') or 'rule'
    elif record.get('kind') == 'hvac_system':
        text = record.get('name') or record.get('system_type') or 'system'
    elif 'end_use' in record:
        text = record['end_use']
    else:
        text = ' '.join(str(record.get(k) or '') for k in ('role', 'technology')) or 'component'
    return slug(text)[:60].strip('-') or 'record'


def assign(records, ids, prefix, placeholders=()):
    """Content-hashed IDs for records whose references are all in `ids` or are placeholders.

    A record's own ID hashes as SELF; IDs listed in `placeholders` hash as SYSTEM.
    """
    pending, out = dict(records), {}
    while pending:
        ready = {k: r for k, r in pending.items()
                 if not (set(COMPONENT.findall(json.dumps(r))) & (pending.keys()-{k}))}
        if not ready:
            raise ValueError('Circular references among '+', '.join(sorted(pending)[:3]))
        for old, record in sorted(ready.items()):
            local = {**ids, old: SELF, **{p: SYSTEM for p in placeholders}}
            content = translate({k: v for k, v in record.items() if k not in ('id', 'name')}, local)
            new = f'{prefix}.{origin(record)}.{h6(content)}'
            if new in out.values():
                raise ValueError('ID clash: '+new)
            out[old] = ids[old] = new
            del pending[old]
    return out


def build_folder(sources, template, building_type, programs):
    """One folder's systems tables; `programs` is the folder's atlas_programs build."""
    tslug, bslug = slug(template), slug(building_type)
    prefix = f'{tslug}.{bslug}'
    here = lambda r: r['template'] == template and r['building_type'] == building_type
    hvac = {k: h for k, h in sources.hvac.items() if here(h) and h['source_family'] != RESIDENTIAL}
    services = {k: s for k, s in sources.services.items() if here(s)}
    water = {section: [r for r in sources.water[section] if here(r)] for section in ('programs', 'services')}
    references = {r['program_id']: sources.water['reference_programs'][r['program_id']]
                  for r in water['programs'] if r['program_id'] in sources.water['reference_programs']}
    if not hvac and not services:
        raise ValueError(f'No commercial systems or services for {template} / {building_type}')
    components = closure(sources, list(hvac.values()))
    library = {c for c in components if sources.components[c]['role'] in LIBRARY}
    # Programs are cited by their upstream source IDs; the program build maps them to new IDs.
    ids = {p['source_id']: programs.ids[p['id']] for p in sources.definitions.programs.values()
           if p['id'] in programs.ids and p.get('source_id')}
    records = [*hvac.values(), *(sources.components[c] for c in components), *services.values(), water, references]
    refs = set(SCHEDULE.findall(json.dumps(records))) & sources.schedules.keys()
    labels = {s: sources.schedules[s].get('source_name') or 'system schedule' for s in refs}
    days, schedules, schedule_ids = atlas_programs.tabulate({s: sources.schedules[s] for s in refs}, labels, prefix)
    ids.update(schedule_ids)
    for role in LIBRARY:  # curves first: rules may cite them
        assign({c: sources.components[c] for c in library if sources.components[c]['role'] == role}, ids, tslug)
    # Ancillary components cite their system, which lists them: systems hash as a placeholder there.
    assign({c: sources.components[c] for c in components - library}, ids, prefix, placeholders=hvac)
    assign(hvac, ids, prefix)
    assign(services, ids, prefix)
    tables = {'systems': hvac, 'components': {c: sources.components[c] for c in components - library},
              'services': services}
    files = {f'commercial/{tslug}/{bslug}/{name}.json': table_bytes({ids[k]: translate(v, ids) for k, v in rows.items()})
             for name, rows in tables.items()}
    for role, name in LIBRARY.items():
        rows = {ids[c]: translate(sources.components[c], ids) for c in library if sources.components[c]['role'] == role}
        files[f'commercial/{tslug}/library/{name}.json'] = table_bytes(rows)
    files[f'commercial/{tslug}/{bslug}/water.json'] = table_bytes({
        'programs': {ids[r['program_id']]: translate(r, ids) for r in water['programs']},
        'references': {ids[k]: translate(v, ids) for k, v in references.items()},
        'services': {r['path_id']: translate(r, ids) for r in water['services']}}, sections=True)
    files[f'commercial/{tslug}/{bslug}/schedules.json'] = table_bytes({'days': days, 'schedules': schedules}, sections=True)
    text = lambda paths: b''.join(files[p] for p in paths).decode()
    library_paths = [p for p in files if '/library/' in p]
    folder_paths = [p for p in files if p.startswith('commercial/') and p not in library_paths]
    library_evidence, terms = atlas_programs.encode_evidence(sources.definitions, EVIDENCE.findall(text(library_paths)))
    folder_evidence, more = atlas_programs.encode_evidence(sources.definitions, EVIDENCE.findall(text(folder_paths)))
    folder_evidence.update({e: sources.completion[e] for e in COMPLETION_EVIDENCE.findall(text(folder_paths))})
    files[f'evidence/commercial/{tslug}/library.json'] = table_bytes(library_evidence)
    files[f'evidence/commercial/{tslug}/{bslug}.json'] = table_bytes(folder_evidence)
    glossary = {section: {**terms[section], **more[section]} for section in terms}
    files['evidence/glossary.json'] = table_bytes(glossary, sections=True)
    return Build(files, ids)


class SystemsSuite:
    """Written folder tables read back by table and new ID."""

    def __init__(self, files):
        self.tables = collections.defaultdict(dict)
        self.days, self.schedules, self.water_sections = {}, {}, collections.defaultdict(dict)
        for path, data in files.items():
            name = Path(path).stem
            if not path.startswith('commercial/'):
                continue
            if name in ('systems', 'components', 'services'):
                self.tables[name].update(json.loads(data))
            elif name in LIBRARY.values():
                self.tables['components'].update(json.loads(data))
            elif name == 'water':
                for section, rows in json.loads(data).items():
                    self.water_sections[section].update(rows)
            elif name == 'schedules':
                table = json.loads(data)
                self.days.update(table['days'])
                self.schedules.update(table['schedules'])

    def record(self, table, record_id):
        return json.loads(json.dumps(self.tables[table][record_id]))

    def water(self, section, key):
        return json.loads(json.dumps(self.water_sections[section][key]))

    def schedule(self, schedule_id):
        stored = self.schedules[schedule_id]
        out = {k: v for k, v in stored.items() if k not in ('name', 'rules')}
        out['rules'] = [{**{k: v for k, v in r.items() if k != 'day'}, 'values': self.days[r['day']]} for r in stored['rules']]
        return out


def read_files(files):
    return SystemsSuite(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', required=True)
    parser.add_argument('--building-type', required=True)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    programs = atlas_programs.build_folder(atlas_programs.load_sources(), args.template, args.building_type)
    built = build_folder(load_sources(), args.template, args.building_type, programs)
    for path, data in merge(programs.files, built.files).items():
        out = args.output/path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    print(f'Wrote {len(built.files)} systems files for {args.template} / {args.building_type}')


if __name__ == '__main__':
    main()
