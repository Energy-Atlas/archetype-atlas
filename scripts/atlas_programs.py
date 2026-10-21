"""Write and read ADR 0036 commercial program suites for one template x building-type folder.

The folder is built from the frozen definition release and its resolutions:
one file per program (source twin and reviewed twin become one record whose
fillings are stored inline), one schedules table, one evidence file and the
shared glossary. Reading it back gives the source-backed or filled export.

python -m scripts.atlas_programs --template 90.1-2019 --building-type Hospital
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

from scripts.atlas_format import canonical, h6, slug, suite_bytes, table_bytes, translate
from scripts.common import ROOT, load_json

DEFINITIONS = ROOT/'data/definition-releases/v0.1.1'
RESOLUTIONS = ROOT/'data/resolution-releases/v0.4.0/resolutions.json'
OUTPUT = ROOT/'build/atlas-release/v1.0.0'
MODES = {'SourcePrograms': 'source', 'DepartmentMixes': 'department', 'GeneralMix': 'general'}
DETAILS = {mode: detail for detail, mode in MODES.items()}
IDENTITY = ('id', 'kind', 'evidence_view', 'source_definition_id', 'reviewed_resolution_ids', 'composition_id')
FILLING_BASES = ('research_assumption', 'executed_upstream')  # strictest first
REFERENCE = re.compile(r'"((?:mixed-)?schedule-[0-9a-f]{20,24})"')
EVIDENCE = re.compile(r'(?:evidence|provenance)-[0-9a-f]{20,24}')

Build = collections.namedtuple('Build', 'files ids')


def target(field):
    """The program load or parameter a resolution or unresolved field addresses."""
    if field == 'conditioning':
        return ('parameter', 'conditioning')
    if field == 'service_water_heating_schedule_id':
        return ('load', 'hot_water_volume')
    if field == 'gas_equipment_W_m2':
        return ('load', 'gas_equipment')
    match = re.fullmatch(r'(.+)_schedule_id', field)
    if match:
        return ('load', match[1])
    raise ValueError('Unmapped program field: '+field)


def addressed(field):
    """Every target a resolution fills: additional lighting runs on the lighting schedule."""
    return [target(field), *([('load', 'additional_lighting')] if field == 'lighting_schedule_id' else [])]


def targets(record):
    loads = {('load', l['quantity']): {k: v for k, v in l.items() if k != 'source_components'} for l in record['loads']}
    if len(loads) != len(record['loads']):
        raise ValueError('Repeated load quantity in '+record['id'])
    return {**loads, **{('parameter', k): v for k, v in record['parameters'].items()}}


def fillings(program):
    for entry in [*program['loads'], *program['parameters'].values()]:
        if 'filling' in entry:
            yield entry['filling']


class Sources:
    """The frozen definition release and the resolutions behind its reviewed twins."""

    def __init__(self):
        self.programs = {p['id']: p for p in load_json(DEFINITIONS/'programs.json')}
        self.schedules = {s['id']: s for s in load_json(DEFINITIONS/'schedules.json')}
        self.compositions = {c['id']: c for c in load_json(DEFINITIONS/'compositions.json')}
        self.evidence = {e['id']: e for e in load_json(DEFINITIONS/'provenance.json')}
        self.source_files = {s['id']: s for s in load_json(DEFINITIONS/'source_files.json')}
        self.twins = {p['source_definition_id']: p for p in self.programs.values() if p.get('source_definition_id')}
        resolutions = load_json(RESOLUTIONS)
        self.resolutions = {r['id']: r for r in resolutions['resolutions']}
        self.unresolved = collections.defaultdict(list)
        for row in resolutions['unresolved']:
            self.unresolved[row['record_id']].append(row)


def load_sources():
    return Sources()


def classify_resolved(sources, reviewed, changed):
    """Each changed target of a source program, classified by the resolutions that fill it."""
    found = collections.defaultdict(list)
    for rid in reviewed.get('reviewed_resolution_ids') or []:
        row = sources.resolutions[rid]
        for t in addressed(row['field']):
            found[t].append(row)
    out = {}
    for t in changed:
        if not found[t]:
            raise ValueError(f'No resolution explains {t} in {reviewed["id"]}')
        out[t] = verdict([(r['basis'], r['rule'], r['id']) for r in found[t]])
    return out


def classify_mixed(member_changes, changed, name):
    """Each changed target of a mix, classified by its members' changes (same target first)."""
    out = {}
    for t in changed:
        pool = [c for m in member_changes for c in m.get(t, [])]
        pool = pool or [c for m in member_changes for cs in m.values() for c in cs]
        if not pool:
            raise ValueError(f'No member change explains {t} in {name}')
        out[t] = verdict(pool)
    return out


def verdict(rows):
    """Source zero only when every contributing change is source zero; otherwise the strictest filling."""
    bases = {basis for basis, _, _ in rows}
    if bases == {'source_zero'}:
        return {'basis': 'source_zero', 'rows': rows}
    basis = next(b for b in FILLING_BASES if b in bases)
    return {'basis': basis, 'rows': [r for r in rows if r[0] != 'source_zero']}


def semantic(sources, entry):
    """A mix entry without its view identity: demand and evidence IDs dropped, schedules compared by content."""
    if entry is None:
        return None
    out = {k: v for k, v in entry.items() if k not in ('demand_id', 'evidence_id')}
    for key in ('schedule_id', 'value'):
        if isinstance(out.get(key), str) and out[key] in sources.schedules:
            out[key] = {k: v for k, v in sources.schedules[out[key]].items() if k not in ('id', 'evidence_ids')}
    return out


def split_program(sources, record, changes, glossary):
    """One stored program from a source record and its reviewed twin, if any."""
    reviewed = sources.twins.get(record['id'])
    composed = record['derivation'] == 'composed'
    skip = IDENTITY+('loads', 'parameters', 'evidence_ids', 'detail')+(('source_id',) if composed else ())
    stored = {k: v for k, v in record.items() if k not in skip}
    stored['mode'] = MODES[record['detail']]
    if reviewed and any(reviewed.get(k) != v for k, v in stored.items() if k != 'mode'):
        raise ValueError('Reviewed twin changes record fields of '+record['id'])
    actual, filled = targets(record), targets(reviewed or record)
    # A mix keeps its source view's identity; only semantic differences become changes.
    view = (lambda e: semantic(sources, e)) if composed else (lambda e: e)
    changed = [t for t in {**actual, **filled} if view(actual.get(t)) != view(filled.get(t))]
    if composed:
        stored['composition'] = composition(sources, record, reviewed)
        members = [changes.get(m['program_id'], {}) for m in stored['composition']['members']]
        classes = classify_mixed(members, changed, record['name'])
    else:
        classes = classify_resolved(sources, reviewed, changed) if changed else {}
    evidence = set(record['evidence_ids'])
    filled_evidence = evidence if composed else set((reviewed or record)['evidence_ids'])
    if not evidence <= filled_evidence:
        raise ValueError('Reviewed twin drops evidence of '+record['id'])
    entries, kept = {}, {}
    for t in [*actual, *(t for t in filled if t not in actual)]:
        a, b = actual.get(t), filled.get(t)
        if t not in changed:
            entries[t] = dict(a)
            continue
        sa, sb = view(a) or {}, view(b) or {}
        if set(sa)-set(sb):
            raise ValueError(f'Reviewed twin removes fields of {t} in {record["id"]}')
        verdict_ = classes[t]
        if verdict_['basis'] == 'source_zero':
            entries[t] = {**(a or {}), **{k: v for k, v in b.items() if sa.get(k) != sb.get(k)}} if composed else dict(b)
            evidence |= {b['evidence_id']} if b.get('evidence_id') and not composed else set()
        else:
            kept[t] = verdict_
            change = {k: v for k, v in b.items() if k in sb and sa.get(k) != sb[k]}
            entries[t] = {**(a or {}), 'filling': {
                'set': change, 'basis': verdict_['basis'],
                'rules': sorted({rule for _, rule, _ in verdict_['rows']}),
                'resolutions': sorted({rid for _, _, rid in verdict_['rows']}),
                'evidence': sorted(set(EVIDENCE.findall(json.dumps(change))))}}
    for row in sources.unresolved.get(record.get('source_id'), []) if not composed else []:
        t = target(row['field'])
        key = 'u-'+h6(row['reason'])
        glossary['unresolved'][key] = row['reason']
        if t not in entries:  # no such load at all: the reason stays on the record
            stored.setdefault('unresolved', {})[row['field']] = key
        elif entries[t].get('schedule_id') is not None:
            raise ValueError(f'Unresolved {row["field"]} has a value in {record["id"]}')
        else:
            entries[t]['unresolved'] = key
    changes[record['id']] = {t: v['rows'] for t, v in classes.items()}
    stored['loads'] = [entries[t] for t in entries if t[0] == 'load']
    stored['parameters'] = {t[1]: entries[t] for t in entries if t[0] == 'parameter'}
    stored['evidence_ids'] = sorted(evidence)
    if filled_evidence-evidence:
        stored['filling_evidence_ids'] = sorted(filled_evidence-evidence)
    for verdict_ in kept.values():
        for _, rule, rid in verdict_['rows']:
            glossary['rules'].setdefault(rule, set()).add(sources.resolutions[rid]['note'])
    return stored


def composition(sources, record, reviewed):
    source = sources.compositions[record['composition_id']]
    members = [{k: m[k] for k in ('program_id', 'weight', 'represented_area_m2', 'source_geometry_file_id', 'source_program_id')}
               for m in source['members']]
    if reviewed:
        twin = sources.compositions[reviewed['composition_id']]
        expect = [{**m, 'program_id': sources.twins.get(m['program_id'], {'id': m['program_id']})['id']} for m in members]
        if [{k: m[k] for k in expect[0]} for m in twin['members']] != expect:
            raise ValueError('Reviewed composition differs beyond member twins: '+record['id'])
    return {'method': source['method'], 'members': members}


def stem(name, building_type):
    """A program name without its building-family suffix, e.g. Lobby_Hospital -> Lobby."""
    return name[:-len(building_type)-1] if name.endswith('_'+building_type) else name


def schedule_labels(stored, building_type):
    """A readable label for each referenced schedule: its source name, else the first program slot using it."""
    labels = {}
    for program in stored:
        name = stem(program['name'], building_type)
        slots = [(l['quantity'], l) for l in program['loads']]
        slots += [(k[:-len('_schedule_id')] if k.endswith('_schedule_id') else k, p) for k, p in program['parameters'].items()]
        for slot, entry in slots:
            for ref in REFERENCE.findall(json.dumps(entry)):
                labels.setdefault(ref, name+' '+slot)
    return labels


def constant(schedule):
    """A filling-created always-constant schedule becomes a literal; any other shape is an error."""
    if not str(schedule.get('source_name', '')).startswith('resolution-'):
        return None
    rules = schedule['rules']
    if len(rules) != 1 or len(rules[0]['values']) != 1:
        raise ValueError('Resolution schedule is not constant: '+schedule['id'])
    return {'constant': rules[0]['values'][0]}


def schedule_table(sources, stored, prefix, building_type):
    labels = schedule_labels(stored, building_type)
    literals = {old: constant(sources.schedules[old]) for old in labels}
    tabled = {old: sources.schedules[old] for old, literal in literals.items() if literal is None}
    days, table, ids = tabulate(tabled, labels, prefix)
    return days, table, {**ids, **{old: v for old, v in literals.items() if v is not None}}


def tabulate(schedules, labels, prefix):
    """A folder schedules table: each day profile once, schedules with readable content-hashed IDs."""
    days, table, ids = {}, {}, {}
    for old in sorted(schedules):
        schedule = schedules[old]
        rules = []
        for rule in schedule['rules']:
            day = 'd-'+hashlib.sha256(canonical(rule['values']).encode()).hexdigest()[:8]
            if days.setdefault(day, rule['values']) != rule['values']:
                raise ValueError('Day profile hash clash: '+day)
            rules.append({**{k: v for k, v in rule.items() if k != 'values'}, 'day': day})
        content = {**{k: v for k, v in schedule.items() if k not in ('id', 'rules')}, 'rules': rules}
        origin = slug(schedule.get('source_name') or labels[old])
        new = f'{prefix}.{origin}.{h6(content)}'
        if new in table and {k: v for k, v in table[new].items() if k != 'name'} != content:
            raise ValueError('Schedule ID clash: '+new)
        table[new] = content if 'source_name' in schedule else {**content, 'name': labels[old]}
        ids[old] = new
    return days, table, ids


def encode_evidence(sources, evidence_ids):
    """Definition evidence rows with their repeated texts and source files moved to the glossary."""
    evidence, terms = {}, {'interpretations': {}, 'transformations': {}, 'source_files': {}}
    for eid in sorted(set(evidence_ids)):
        row = sources.evidence[eid]
        interpretation, transformation = 'i-'+h6(row['interpretation']), 't-'+h6(row['transformation'])
        terms['interpretations'][interpretation] = row['interpretation']
        terms['transformations'][transformation] = row['transformation']
        if row.get('source_file_id'):
            terms['source_files'][row['source_file_id']] = {k: v for k, v in sources.source_files[row['source_file_id']].items() if k != 'id'}
        evidence[eid] = {'extraction_date': row['extraction_date'], 'locator': row['locator'],
                         'original_unit': row['original_unit'], 'original_value': row['original_value'],
                         'source_file': row.get('source_file_id'), 'interpretation': interpretation,
                         'transformation': transformation}
    return evidence, terms


def program_id(prefix, program, building_type):
    content = {k: v for k, v in program.items() if k != 'name'}
    return f'{prefix}.{program["mode"]}.{slug(stem(program["name"], building_type))}.{h6(content)}'


def build_folder(sources, template, building_type):
    tslug, bslug = slug(template), slug(building_type)
    prefix = f'{tslug}.{bslug}'
    records = sorted((p for p in sources.programs.values() if p['template'] == template
                      and p['building_type'] == building_type and p['evidence_view'] == 'source'
                      and p['source_family'] != 'existing_stock_source_fixture'),
                     key=lambda p: (p['derivation'] == 'composed', p['name'], p['id']))
    if not records:
        raise ValueError(f'No commercial programs for {template} / {building_type}')
    changes, glossary = {}, {'rules': {}, 'unresolved': {}}
    stored = {p['id']: split_program(sources, p, changes, glossary) for p in records}
    days, table, ids = schedule_table(sources, stored.values(), prefix, building_type)
    files = {}
    for old, program in stored.items():  # source programs first, so mixes can name their members
        program = translate(program, ids)
        new = program_id(prefix, program, building_type)
        if new in files:
            raise ValueError('Program ID clash: '+new)
        program['id'] = new
        ids[old] = new
        if old in sources.twins:
            ids[sources.twins[old]['id']] = new
        files[f'commercial/{tslug}/{bslug}/programs/{program["mode"]}/{new}.json'] = program
    files = {path: suite_bytes(program) for path, program in files.items()}
    files[f'commercial/{tslug}/{bslug}/schedules.json'] = table_bytes({'days': days, 'schedules': table}, sections=True)
    evidence, terms = encode_evidence(sources, EVIDENCE.findall(b''.join(files.values()).decode()))
    files[f'evidence/commercial/{tslug}/{bslug}.json'] = table_bytes(evidence)
    # Notes are content-addressed so folders merge without conflict: a rule's note text varies by record.
    rule_notes = {'n-'+h6([rule, note]): {'rule': rule, 'note': note}
                  for rule, notes in glossary['rules'].items() for note in notes}
    unresolved = {key: {'reason': reason} for key, reason in glossary['unresolved'].items()}
    files['evidence/glossary.json'] = table_bytes({'interpretations': terms['interpretations'],
        'transformations': terms['transformations'], 'source_files': terms['source_files'],
        'rule_notes': rule_notes, 'unresolved': unresolved}, sections=True)
    return Build(files, ids)


class Suite:
    """A written folder read back into source-backed or filled program exports."""

    def __init__(self, files):
        self.programs = {}
        for path, data in files.items():
            if '/programs/' in path:
                program = json.loads(data)
                self.programs[program['id']] = program
        table = json.loads(files[next(p for p in files if p.startswith('commercial/') and p.endswith('/schedules.json'))])
        self.days, self.table = table['days'], table['schedules']
        self._cache = {}

    def schedule(self, schedule_id):
        out = {k: v for k, v in self.table[schedule_id].items() if k not in ('name', 'rules')}
        out['rules'] = [{**{k: v for k, v in r.items() if k != 'day'}, 'values': self.days[r['day']]}
                        for r in self.table[schedule_id]['rules']]
        return out

    @staticmethod
    def entry(entry, filled):
        out = {k: v for k, v in entry.items() if k not in ('filling', 'unresolved')}
        if filled and 'filling' in entry:
            out.update(entry['filling']['set'])
        return out or None

    def export(self, program_id, version):
        if version not in ('source', 'filled'):
            raise ValueError('Unknown export version: '+version)
        key = (program_id, version)
        if key in self._cache:
            return json.loads(json.dumps(self._cache[key]))
        program, filled = self.programs[program_id], version == 'filled'
        out = {k: v for k, v in program.items()
               if k not in ('mode', 'composition', 'loads', 'parameters', 'evidence_ids', 'filling_evidence_ids', 'unresolved')}
        out['detail'] = DETAILS[program['mode']]
        out['evidence_ids'] = sorted({*program['evidence_ids'], *(program.get('filling_evidence_ids', []) if filled else [])})
        out['loads'] = [l for l in (self.entry(e, filled) for e in program['loads']) if l is not None]
        out['parameters'] = {k: p for k, e in program['parameters'].items() if (p := self.entry(e, filled)) is not None}
        if 'composition' in program:
            members = program['composition']['members']
            exports = {m['program_id']: self.export(m['program_id'], version) for m in members}
            for load in out['loads']:
                load['source_components'] = [
                    {'load': ml, 'program_id': m['program_id'], 'weight': m['weight']}
                    for m in members for ml in exports[m['program_id']]['loads'] if ml['quantity'] == load['quantity']]
        self._cache[key] = out
        return json.loads(json.dumps(out))


def read_folder(files):
    return Suite(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', required=True)
    parser.add_argument('--building-type', required=True)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    built = build_folder(load_sources(), args.template, args.building_type)
    for path, data in built.files.items():
        out = args.output/path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    programs = sum('/programs/' in p for p in built.files)
    print(f'Wrote {programs} programs and {len(built.files)-programs} tables for {args.template} / {args.building_type}')


if __name__ == '__main__':
    main()
