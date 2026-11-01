"""The record edits of data release 2.3.0 (ADR 0053), as a pure function of the resolved release 2.2.0.

python -m scripts.atlas_edits             # what the edits change over release 2.2.0
python -m scripts.atlas_edits --ids       # also print every ID that moves

`edit(files)` takes `scripts.atlas_delta.files('2.2.0')` and returns an `Edited`: the files the edits change
or add (`files`, path to bytes, in each file's storage format), the paths they remove (`removed`) and the IDs
that move (`ids`, old to new). The delta writer of release 2.3.0 lays them over 2.2.0; nothing here writes a
release folder. The edits, each in ADR 0053:

1. **Internal mass** (section 1). The unified `InternalMass` of a building-scope set counts its whole
   additional-mass inventory: the quantity is the sum of `mass_accounting.additional_mass.entries`, the
   source-scope entries and the DOE-only furnishings release 1.1.0 added alike, and the contributors and fit
   follow (`construction_equivalent_export.internal_mass_from_inventory`). 8 DOE Ref sets, 152 contexts.
2. **PNNL point loads** (section 2). The 90.1 small-hotel `Elec/MechRoom` electric equipment is the PNNL
   prototype elevator motor over its zone (`data/program-inputs/pnnl-point-load-exceptions-v1.json`), with an
   evidence row citing the IDF object; the department mixes that hold it are recomputed (value and mixed
   schedule, as `program_composition.compose` forms them).
3. **Accepted absence** (section 3). Every commercial load that is unknown with no filling gets its reason on
   the record (`unresolved`, a glossary reason ID) and a stored filling of the ADR 0016 accepted absence (known
   0 in the filled view), which the program exporter used to apply by a name rule.
4. **Distinguishing names** (section 4). Records that share a name in their folder take the name of their
   source distinction (`data/program-inputs/distinguishing-names-v1.json`).

IDs then follow their rules (ADR 0046 section 8, ADR 0051 section 4; `scripts.release_editor`): programs whose
content changed and the mixes that cite them, and construction sets whose content changed, take new IDs; their
files are renamed and every citing file follows, including the 2.2.0 `generation.json` blocks and
`definition-map.json`. Names are outside the program ID, so a renamed program keeps its ID.
"""
import argparse
import hashlib
import json
import math
from collections import Counter

from scripts import atlas_constructions, atlas_delta, release_editor
from scripts.atlas_format import canonical, h6, slug, table_bytes
from scripts.atlas_programs import stem
from scripts.common import ROOT, load_json
from scripts.construction_equivalent_export import internal_mass_from_inventory, mass_agrees
from scripts.definition_contract import stable_id
from scripts.iecc_commercial_values import layered

BASE = '2.2.0'
RELEASE = '2.3.0'
DATE = '2026-11-01'
ADR = 'docs/adr/0053-release-2-3-0-data-corrections.md'
POINT_LOADS = ROOT/'data/program-inputs/pnnl-point-load-exceptions-v1.json'
NAMES = ROOT/'data/program-inputs/distinguishing-names-v1.json'
ABSENCE_RULE = 'accepted_absence'
ABSENCE_NOTE = ('User-approved (ADR 0016): an unknown additional-lighting load, an unknown load of a support space '
                '(attic, plenum, elevator, electrical or mechanical room, shaft) and the unknown occupancy of a data '
                'center are absent in the filled view (known 0); the source value stays unknown. Stored on the record '
                'from release 2.3.0 (ADR 0053 section 3); the program exporter applied it by name before.')
ABSENCE_TRANSFORMATION = 'unknown (null) taken as absent: 0 in the filled view only'
SUPPORT = ('attic', 'plenum', 'elevator', 'elec/mech', 'electrical', 'mechanical', 'shaft')
# Reasons of the unknowns that had none on the record (ADR 0053 section 3), kept once in the glossary.
REASONS = {
    'additional_lighting': 'The source gives no additional lighting: the openstudio-standards space-type row leaves '
                           'additional_lighting_per_area blank (the DOE Ref construction-only programs read the same table). '
                           'Unknown, not zero.',
    'support': 'The source gives no value for this support-space load (a blank openstudio-standards space-type field). '
               'Unknown, not zero.',
    'blank': 'The source gives no value for this load (a blank openstudio-standards space-type field). Unknown, not zero; '
             'a stored filling gives the filled version its value.',
    'mix': 'A member program\'s value is unknown, so the area-weighted mix is unknown (ADR 0012: a required unknown '
           'propagates).',
}


def encode(path, value):
    """A release file in its storage format (ADR 0036 section 8, ADR 0046 P9, ADR 0051)."""
    name = path.rsplit('/', 1)[-1]
    if '/programs/' in path or '/constructions/' in path:
        return (layered(value, 3)+'\n').encode('utf-8')
    if name == 'generation.json':
        return atlas_delta.layered_bytes(value)
    if name == 'definition-map.json':
        return atlas_delta.layered_bytes(value, 2)
    if name == 'exporter-inputs.json':
        return atlas_delta.layered_bytes(value, 1)
    if name in ('glossary.json', 'schedules.json', 'water.json'):
        return table_bytes(value, sections=True)
    return table_bytes(value)


class Tree:
    """Release files with decoded values to edit; `dump()` re-encodes the edited ones."""

    def __init__(self, files):
        self.files = dict(files)
        self.values = {}

    def __getitem__(self, path):
        if path not in self.values:
            self.values[path] = json.loads(self.files[path])
        return self.values[path]

    def __setitem__(self, path, value):
        self.values[path] = value

    def dump(self):
        return {**self.files, **{p: encode(p, v) for p, v in self.values.items()}}


class Edited:
    def __init__(self, files, removed, ids, summary):
        self.files, self.removed, self.ids, self.summary = files, removed, ids, summary

    def resolved(self, base):
        """The release the edits make: the base with the changed files laid over and the removed ones gone."""
        out = {p: d for p, d in base.items() if p not in self.removed}
        out.update(self.files)
        return out


def evidence_id(row):
    return stable_id('evidence', row)


def glossary_text(glossary, section, prefix, text):
    key = prefix+h6(text)
    if glossary[section].setdefault(key, text) != text:
        raise ValueError('Glossary key clash: '+key)
    return key


def reason_id(glossary, text):
    key = 'u-'+h6(text)
    if glossary['unresolved'].setdefault(key, {'reason': text}) != {'reason': text}:
        raise ValueError('Reason key clash: '+key)
    return key


# 1. Internal mass ------------------------------------------------------------------------------------------

def internal_mass(tree):
    """Rewrite each unified InternalMass that disagrees with its inventory; (set IDs, contexts) changed."""
    suite = atlas_constructions.read_files({p: d for p, d in tree.files.items()
                                            if p.startswith(('commercial/', 'evidence/commercial/')) and not p.endswith('.md')})
    changed = {}
    for path in sorted(p for p in tree.files if p.startswith('commercial/') and '/constructions/' in p):
        record = tree[path]
        if 'common' not in record:
            continue
        fixes = {}
        for key in sorted(record['contexts']):
            if 'unified' not in record['contexts'][key]:
                continue
            document = suite.export(record['id'], key, 'unified')
            if mass_agrees(document):
                continue
            component, fit = internal_mass_from_inventory(document['mass_accounting'])
            old = document['components']['InternalMass']
            assembly = document['assemblies'][old['assembly_id']]
            if release_editor.rounded(fit) != release_editor.rounded({k: v for k, v in assembly.items() if k != 'id'}):
                raise ValueError(f'{record["id"]} {key}: the inventory changes the fitted InternalMass assembly; '
                                 'add the new fit to the template library first')
            fixes[key] = {**component, 'assembly_id': old['assembly_id']}
        if not fixes:
            del_if_untouched(tree, path, record)
            continue
        partial = record['common']['unified']['partial'].get('components', {})
        stored_in_context = [k for k in fixes if 'InternalMass' in record['contexts'][k]['unified']['fields'].get('components', {})
                             or 'components/InternalMass' in record['contexts'][k]['unified']['refs']]
        unified = [k for k in record['contexts'] if 'unified' in record['contexts'][k]]
        values = {canonical(v) for v in fixes.values()}
        if 'InternalMass' in partial and not stored_in_context and len(values) == 1 and set(fixes) == set(unified):
            partial['InternalMass'] = next(iter(fixes.values()))
        else:
            for key, component in fixes.items():
                release_editor.restore(record, key, 'unified', 'components', 'InternalMass', component)
        changed[record['id']] = sorted(fixes)
    return changed


# 2. PNNL point loads ---------------------------------------------------------------------------------------

def folder_paths(tree, folder):
    return sorted(p for p in tree.files if p.startswith(folder+'/programs/'))


def program_path(tree, program_id):
    return next(p for p in tree.files if p.endswith(f'/programs/{program_id.split(".")[2]}/{program_id}.json'))


def schedule_of(tree, folder, reference):
    """A folder schedule (or a constant literal) in definition form, for program_composition.mix_schedule."""
    if isinstance(reference, dict):
        return {'rules': [{'day_types': 'Default', 'start_date': '2000-01-01', 'end_date': '2000-12-31',
                           'values': [reference['constant']]}], 'units': 'dimensionless', 'schedule_type': 'fraction'}
    if reference is None:
        return None
    table = tree[folder+'/schedules.json']
    entry = table['schedules'][reference]
    return {**{k: v for k, v in entry.items() if k not in ('name', 'rules')},
            'rules': [{**{k: v for k, v in r.items() if k != 'day'}, 'values': table['days'][r['day']]} for r in entry['rules']]}


def filled_entry(entry, filled):
    """A stored load as one view reads it: the filled view applies its filling (ADR 0036 section 4)."""
    if filled and 'filling' in entry:
        return {**{k: v for k, v in entry.items() if k != 'filling'}, **entry['filling']['set']}
    return entry


def mixed_load(tree, folder, mix, quantity, filled=False):
    """(value, schedule definition, member loads) of one quantity of a mix from its members in one view, as
    program_composition.compose forms it; (None, None, loads) when a member is unknown."""
    from scripts.program_composition import mix_schedule
    members = mix['composition']['members']
    loads = []
    for member in members:
        record = tree[program_path(tree, member['program_id'])]
        found = [l for l in record['loads'] if l['quantity'] == quantity]
        if len(found) != 1:
            raise ValueError(f'{mix["id"]}: member {member["program_id"]} has {len(found)} {quantity} loads')
        loads.append(found[0])
    weights = [m['weight'] for m in members]
    entries = [filled_entry(l, filled) for l in loads]
    values = [e['value'] for e in entries]
    if any(v is None for v in values):
        return None, None, loads
    density = math.fsum(w*d for w, d in zip(weights, values))
    mixed = mix_schedule([schedule_of(tree, folder, e.get('schedule_id')) for e in entries], weights, values, density or 1)
    return density, mixed, loads


def table_schedule(tree, folder, mixed, name, evidence_ids):
    """Add a mixed schedule to the folder table (scripts.atlas_programs.tabulate's rule); its new ID."""
    table = tree[folder+'/schedules.json']
    rules = []
    for rule in mixed['rules']:
        day = 'd-'+hashlib.sha256(canonical(rule['values']).encode()).hexdigest()[:8]  # atlas_programs.tabulate's day rule
        if table['days'].setdefault(day, rule['values']) != rule['values']:
            raise ValueError('Day profile hash clash: '+day)
        rules.append({**{k: v for k, v in rule.items() if k != 'values'}, 'day': day})
    content = {**{k: v for k, v in mixed.items() if k not in ('id', 'rules')}, 'evidence_ids': evidence_ids, 'rules': rules}
    content['units'] = {'1': 'dimensionless'}.get(content.get('units'), content.get('units'))
    prefix = folder.split('/', 1)[1].replace('/', '.')
    new = f'{prefix}.{slug(name)}.{h6(content)}'
    if table['schedules'].setdefault(new, {**content, 'name': name}) != {**content, 'name': name}:
        raise ValueError('Schedule ID clash: '+new)
    return new


def drop_unused_schedules(tree, folder, candidates):
    text = ''.join(tree.files[p].decode('utf-8') if p not in tree.values else canonical(tree.values[p])
                   for p in folder_paths(tree, folder))
    text += canonical(tree[folder+'/services.json']) + canonical(tree[folder+'/systems.json'])
    table = tree[folder+'/schedules.json']
    for sid in candidates:
        if sid not in text:
            del table['schedules'][sid]
    used = {r['day'] for s in table['schedules'].values() for r in s['rules']}
    for day in set(table['days']) - used:
        del table['days'][day]


def point_loads(tree, document=None):
    """Apply the PNNL point-load exceptions and recompute the mixes that hold them; {program ID: note}."""
    document = document or load_json(POINT_LOADS)
    glossary = tree['evidence/glossary.json']
    changed = {}
    for entry in document['exceptions']:
        folder, pid = entry['folder'], entry['program_id']
        record = tree[program_path(tree, pid)]
        load = next(l for l in record['loads'] if l['quantity'] == entry['quantity'])
        evidence = tree[f'evidence/{folder}.json']
        source = {k: v for k, v in entry['source_file'].items() if k != 'id'}
        if glossary['source_files'].setdefault(entry['source_file']['id'], source) != source:
            raise ValueError('Source file clash: '+entry['source_file']['id'])
        row = {'extraction_date': document['extraction_date'], 'locator': f'{entry["object"]}/{entry["field"]}',
               'original_unit': 'W; m2',
               'original_value': {'design_level_W': entry['design_level_W'], 'zone': entry['zone'],
                                  'zone_floor_area_m2': entry['zone_floor_area_m2'], 'schedule': entry['schedule'],
                                  'end_use_subcategory': entry['end_use_subcategory'],
                                  'replaced_value_W_m2': load['value'], 'replaced_evidence_id': load['evidence_id']},
               'source_file': entry['source_file']['id'],
               'interpretation': glossary_text(glossary, 'interpretations', 'i-', document['interpretation']),
               'transformation': glossary_text(glossary, 'transformations', 't-', document['transformation'])}
        eid = evidence_id(row)
        evidence[eid] = row
        if not math.isclose(load['value'], entry['value_W_m2'], rel_tol=1e-12):
            changed[pid] = f'{entry["quantity"]} {load["value"]} -> {entry["value_W_m2"]} W/m2'
        load.update(value=entry['value_W_m2'], evidence_id=eid)
        record['evidence_ids'] = sorted({*record['evidence_ids'], eid})
        for path in folder_paths(tree, folder):
            mix = tree[path]
            if 'composition' not in mix or pid not in {m['program_id'] for m in mix['composition']['members']}:
                del_if_untouched(tree, path, mix)
                continue
            target = next(l for l in mix['loads'] if l['quantity'] == entry['quantity'])
            value, mixed, _ = mixed_load(tree, folder, mix, entry['quantity'])
            if value is None:  # another member is unknown, so the mix stays unknown
                if target['value'] is not None:
                    raise ValueError(f'{mix["id"]}: known {entry["quantity"]} from members with an unknown')
                del_if_untouched(tree, path, mix)
                continue
            old = target['schedule_id']
            name = tree[folder+'/schedules.json']['schedules'][old]['name']
            target.update(value=value, schedule_id=table_schedule(tree, folder, mixed, name, [target['evidence_id']]))
            changed[mix['id']] = f'{entry["quantity"]} recomputed from its members: {value} W/m2'
            drop_unused_schedules(tree, folder, [old])
    return changed


def del_if_untouched(tree, path, value):
    if path in tree.values and encode(path, value) == tree.files[path]:
        del tree.values[path]


# 3. Accepted absence ---------------------------------------------------------------------------------------

def absent_allowed(record, load):
    """The ADR 0016 accepted absence, as the program exporter's name rule read it (scripts.program_json_v3)."""
    name = record['name'].lower()
    if load['quantity'] in ('additional_lighting', 'gas_equipment'):
        return True
    if any(k in name for k in SUPPORT):
        return True
    return load['quantity'] == 'occupancy' and 'data' in name and 'center' in name


def absence(tree):
    """Store the accepted-absence fillings and the reasons of the unknowns; {program ID: [quantities]}.

    Source programs first: each unknown load takes its reason and the filling. Then the mixes, whose filled
    values come from their members' filled values (ADR 0036 section 4): each unknown mix load takes the mix
    reason and, where every member is then known in the filled view, a filling with the area-weighted value and
    mixed schedule, classified by the members' rules.
    """
    glossary = tree['evidence/glossary.json']
    reasons = {kind: reason_id(glossary, text) for kind, text in REASONS.items()}
    note = 'n-'+h6([ABSENCE_RULE, ABSENCE_NOTE])
    glossary['rule_notes'][note] = {'rule': ABSENCE_RULE, 'note': ABSENCE_NOTE}
    interpretation = glossary_text(glossary, 'interpretations', 'i-', ABSENCE_NOTE)
    transformation = glossary_text(glossary, 'transformations', 't-', ABSENCE_TRANSFORMATION)
    changed, rows = {}, {}
    paths = sorted(p for p in tree.files if p.startswith('commercial/') and '/programs/' in p)
    for path in (p for p in paths if '/programs/source/' in p):
        record = tree[path]
        folder = path.split('/programs/')[0]
        quantities = []
        for load in record['loads']:
            # A stored filling that sets only the schedule (reviewed_no_occupancy, reviewed_no_lighting) left the value
            # to the name rule; it takes the absence too.
            partial = 'filling' in load and load['filling']['set'].get('value') is None
            if load.get('value') is not None:
                continue
            if 'filling' in load and not partial:
                if 'unresolved' not in load:   # filled already (e.g. reviewed_no_gas_equipment): the reason only
                    load['unresolved'] = reasons['blank']
                    quantities.append(load['quantity'])
                continue
            if not absent_allowed(record, load):
                raise ValueError(f'{record["id"]}: unknown {load["quantity"]} outside the accepted absence')
            if folder not in rows:
                row = {'extraction_date': DATE, 'locator': f'{ADR}#3-accepted-absence', 'original_unit': None,
                       'original_value': None, 'source_file': None, 'interpretation': interpretation,
                       'transformation': transformation}
                rows[folder] = evidence_id({**row, 'folder': folder})
                tree[f'evidence/{folder}.json'][rows[folder]] = row
            eid = rows[folder]
            if 'unresolved' not in load:
                load['unresolved'] = reasons['additional_lighting' if load['quantity'] == 'additional_lighting' else 'support']
            if partial:
                filling = load['filling']
                filling['set'].update(evidence_id=eid, status='known', value=0)
                filling['rules'] = sorted({*filling['rules'], ABSENCE_RULE})
                filling['evidence'] = sorted({*filling['evidence'], eid})
            else:
                load['filling'] = {'basis': 'research_assumption', 'evidence': [eid], 'resolutions': [], 'rules': [ABSENCE_RULE],
                                   'set': {'evidence_id': eid, 'status': 'known', 'value': 0}}
            record['filling_evidence_ids'] = sorted({*record.get('filling_evidence_ids', []), eid})
            quantities.append(load['quantity'])
        if quantities:
            changed[record['id']] = quantities
        else:
            del_if_untouched(tree, path, record)
    for path in (p for p in paths if '/programs/source/' not in p):
        record = tree[path]
        folder = path.split('/programs/')[0]
        quantities = []
        for load in record['loads']:
            if load.get('value') is not None:
                continue
            if 'filling' in load:
                if 'unresolved' not in load:
                    load['unresolved'] = reasons['mix']
                    quantities.append(load['quantity'])
                continue
            load.setdefault('unresolved', reasons['mix'])
            value, mixed, members = mixed_load(tree, folder, record, load['quantity'], filled=True)
            # A member schedule without design days or holidays (the Courthouse, ADR 0039 F3) does not mix on its
            # rule calendar; the mix keeps its reason, and the exporter mixes the members it completes.
            if value is not None and (mixed is not None or not value):
                fillings = [m['filling'] for m in members if 'filling' in m]
                bases = {f['basis'] for f in fillings}
                filled = {'status': 'known', 'value': value}
                if value:
                    label = f'{stem(record["name"], record["building_type"])} {load["quantity"]}'
                    filled['schedule_id'] = table_schedule(tree, folder, mixed, label, list(record['evidence_ids']))
                load['filling'] = {'basis': 'research_assumption' if 'research_assumption' in bases or not bases else sorted(bases)[0],
                                   'evidence': sorted({e for f in fillings for e in f['evidence']}),
                                   'resolutions': sorted({r for f in fillings for r in f['resolutions']}),
                                   'rules': sorted({r for f in fillings for r in f['rules']}), 'set': filled}
                record['filling_evidence_ids'] = sorted({*record.get('filling_evidence_ids', []), *load['filling']['evidence']})
            quantities.append(load['quantity'])
        if quantities:
            changed[record['id']] = quantities
        else:
            del_if_untouched(tree, path, record)
    return changed


# 4. Distinguishing names -----------------------------------------------------------------------------------

def names(tree, document=None):
    document = document or load_json(NAMES)
    changed = {}
    for pid, entry in document['programs'].items():
        record = tree[program_path(tree, pid)]
        if record['name'] != entry['previous_name']:
            raise ValueError(f'{pid}: named {record["name"]}, not {entry["previous_name"]}')
        record['name'] = entry['name']
        changed[pid] = entry['name']
    for sid, entry in document['construction_sets'].items():
        path = next(p for p in tree.files if p.endswith(f'/constructions/{sid}.json'))
        record = tree[path]
        record['name'] = entry['name']
        for representation, suffix in (('detailed', ''), ('unified', ' / building-level equivalent')):
            fields = record['common'][representation]['fields']
            if fields.get('name') != entry['previous_name']+suffix:
                raise ValueError(f'{sid}: {representation} name {fields.get("name")}')
            fields['name'] = entry['name']+suffix
        changed[sid] = entry['name']
    return changed


# IDs ------------------------------------------------------------------------------------------------------

def follow_ids(files, ids):
    """Rename the files of moved IDs and substitute every citation; files re-encoded in their storage format."""
    substitute = release_editor.Substitution(ids)
    out = {}
    for path, data in files.items():
        new_path = '/'.join(ids.get(part[:-5], part[:-5])+'.json' if part.endswith('.json') else part for part in path.split('/'))
        if not path.endswith('.json') or path.startswith('residential/') or path == 'id-map.json' or '/library/' in path:
            out[new_path] = data
            continue
        text = data.decode('utf-8')
        replaced = substitute(text)
        out[new_path] = data if replaced == text else encode(new_path, json.loads(replaced))
    return out


def edit(files, point_load_document=None, name_document=None):
    tree = Tree(files)
    summary = {'internal_mass': internal_mass(tree), 'point_loads': point_loads(tree, point_load_document),
               'accepted_absence': absence(tree), 'names': names(tree, name_document)}
    dumped = tree.dump()
    sets = release_editor.set_ids(dumped, {})
    programs = release_editor.program_ids(dumped)
    ids = {**sets, **programs}
    if len(set(ids.values())) != len(ids) or set(ids.values()) & (set(dumped) - set(ids)):
        raise ValueError('Moved IDs collide')
    out = follow_ids(dumped, ids)
    changed = {p: d for p, d in out.items() if files.get(p) != d}
    removed = sorted(set(files) - set(out))
    return Edited(changed, removed, dict(sorted(ids.items())), summary)


def id_map_bytes(ids):
    """The ID map a 2.3.0 delta carries: release 2.2.0 IDs to their 2.3.0 IDs."""
    record = {'schema_version': '1.0.0', 'decision': ADR, 'base_release': BASE, 'release': RELEASE,
              'description': 'IDs of release 2.2.0 that move in release 2.3.0 (ADR 0053), mapped to their new values.',
              'ids': dict(sorted(ids.items()))}
    return (layered(record, 1)+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ids', action='store_true', help='print every ID that moves')
    args = parser.parse_args()
    files = atlas_delta.files(BASE)
    edited = edit(files)
    summary = edited.summary
    kinds = Counter('construction set' if '.construction-' in i else 'program' for i in edited.ids)
    print(f'Release {RELEASE} edits over {BASE}: internal mass in {len(summary["internal_mass"])} sets '
          f'({sum(len(v) for v in summary["internal_mass"].values())} contexts); point loads in {len(summary["point_loads"])} programs; '
          f'accepted absence stored on {sum(len(v) for v in summary["accepted_absence"].values())} loads of '
          f'{len(summary["accepted_absence"])} programs; {len(summary["names"])} records renamed')
    print(f'{len(edited.files)} files changed or added, {len(edited.removed)} removed, {len(edited.ids)} IDs move ({dict(kinds)})')
    if args.ids:
        for old, new in edited.ids.items():
            print(old, '->', new)


if __name__ == '__main__':
    main()
