"""The record edits of data release 2.4.0 (ADR 0060), as a pure function of the resolved release 2.3.0.

python -m scripts.atlas_edits_2_4_0          # what the edits change over release 2.3.0
python -m scripts.atlas_edits_2_4_0 --ids    # also print every ID that moves

`edit(files)` takes `scripts.atlas_delta.files('2.3.0')` and returns a `scripts.atlas_edits.Edited`: the files the edits
change or add, the paths they remove and the IDs that move. The delta writer of release 2.4.0 (stage REL-A2) lays them
over 2.3.0; nothing here writes a release folder. Each edit reads a committed input that a script builds from the source
models (the IDFs stay outside the repository):

1. **Unoccupied lighting cap** (section 1; `scripts.lighting_cap`). Every known `lighting_controls` block gains
   `unoccupied_lighting_cap`: `{rule, evidence_id}`, the PNNL 90.1-2019 rule of the program's zones or null where no
   source model has one, with the evidence row of the EMS programs or of the scan that found none.
2. **Office lighting power** (section 2; `scripts.pnnl_lighting_power`). The 90.1 whole-building office programs take
   the PNNL prototype density, with an evidence row citing the IDF Lights objects and the replaced value.
3. **Elevators and kitchen reach-ins** (section 3; `scripts.pnnl_services`). The PNNL 90.1 objects the atlas did not
   carry become building services of their folder (`services.json`), with their schedules and evidence, as the IECC
   family stores them.

IDs then follow their rules (ADR 0046 section 8, ADR 0051 section 4; `scripts.release_editor`): the programs whose
content changed and the mixes that cite them take new IDs, their files are renamed and every citing file follows,
`generation.json`, `definition-map.json` and `exporter-inputs.json` included. Service IDs are readable and fixed at
creation (`<template>.<type>.<end use>.<h6>`), as the services of earlier releases are.
"""
import argparse
import copy
import hashlib
import json
import math
from collections import Counter

from scripts import atlas_delta, release_editor
from scripts.atlas_edits import Edited, Tree, del_if_untouched, folder_paths, follow_ids, glossary_text, mixed_load
from scripts.atlas_format import canonical, h6, slug
from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id
from scripts.iecc_commercial_values import layered
from scripts.lighting_controls import space_type

BASE = '2.3.0'
RELEASE = '2.4.0'
ADR = 'docs/adr/0060-release-2-4-0-pnnl-prototype-corrections.md'
CAP = ROOT/'data/program-inputs/unoccupied-lighting-cap-v1.json'
LIGHTING_POWER = ROOT/'data/program-inputs/pnnl-lighting-power-exceptions-v1.json'
SERVICES = ROOT/'data/program-inputs/pnnl-building-services-v1.json'
FIELD = 'unoccupied_lighting_cap'


def store_row(tree, folder, eid, row, source_files):
    """Store one program-shaped evidence row (source_file_id, interpretation, transformation as text) under its ID."""
    glossary = tree['evidence/glossary.json']
    source_id = row.get('source_file_id')
    if source_id:
        source = {k: v for k, v in source_files[source_id].items() if k != 'id'}
        if glossary['source_files'].setdefault(source_id, source) != source:
            raise ValueError('Source file clash: '+source_id)
    stored = {'extraction_date': row['extraction_date'], 'locator': row['locator'], 'original_unit': row['original_unit'],
              'original_value': copy.deepcopy(row['original_value']), 'source_file': source_id,
              'interpretation': glossary_text(glossary, 'interpretations', 'i-', row['interpretation']),
              'transformation': glossary_text(glossary, 'transformations', 't-', row['transformation'])}
    evidence = tree[f'evidence/{folder}.json']
    if evidence.setdefault(eid, stored) != stored:
        raise ValueError(f'Evidence ID clash in {folder}: {eid}')
    return eid


def source_paths(tree):
    return sorted(p for p in tree.files if p.startswith('commercial/') and '/programs/source/' in p)


# 1. Unoccupied lighting cap --------------------------------------------------------------------------------

def lighting_cap(tree, document=None):
    """Add `unoccupied_lighting_cap` to every known lighting-controls block; {program ID: 'rule' or 'none'}."""
    document = document or load_json(CAP)
    records = {(r['template'], r['building_type'], r['space_type']): r for r in document['records']}
    templates = document['templates']
    families = {r['template'] for r in document['records']}
    changed, used = {}, set()
    for path in source_paths(tree):
        record = tree[path]
        controls = record.get('lighting_controls')
        if not controls or controls.get('status') != 'known':
            del_if_untouched(tree, path, record)
            continue
        template = record['template']
        if template in templates:
            entry = templates[template]
        elif template in families:
            key = (template, record['building_type'], space_type(record))
            if key not in records:
                raise ValueError(f'{record["id"]}: known lighting controls but no {template} cap record for {key}')
            entry = records[key]
            used.add(key)
        else:
            raise ValueError(f'{record["id"]}: no cap record for template {template}')
        folder = path.split('/programs/')[0]
        eid = store_row(tree, folder, entry['evidence_id'], document['evidence'][entry['evidence_id']], document['source_files'])
        controls[FIELD] = {'rule': copy.deepcopy(entry['rule']), 'evidence_id': eid}
        record['evidence_ids'] = sorted({*record['evidence_ids'], eid})
        changed[record['id']] = 'rule' if entry['rule'] else 'none'
    unused = [k for k in records if k not in used and records[k]['rule']]
    if unused:
        raise ValueError(f'Cap records with a rule that no atlas program takes: {unused}')
    return changed


# 2. Office lighting power ----------------------------------------------------------------------------------

def lighting_power(tree, document=None):
    """Apply the PNNL office lighting densities; {program ID: 'old -> new W/m2'}."""
    document = document or load_json(LIGHTING_POWER)
    changed = {}
    for entry in document['exceptions']:
        folder = entry['folder']
        found = [p for p in folder_paths(tree, folder) if '/programs/source/' in p and tree[p]['name'] == entry['program_name']]
        if len(found) != 1:
            raise ValueError(f'{folder}: {len(found)} source programs named {entry["program_name"]}')
        record = tree[found[0]]
        load = next(l for l in record['loads'] if l['quantity'] == entry['quantity'])
        if load['value'] is None:
            raise ValueError(f'{record["id"]}: unknown lighting')
        source = entry['source_file']
        row = {'source_file_id': source['id'], 'locator': f'Lights {", ".join(entry["objects"])}/{entry["field"]}',
               'original_value': {'watts_per_zone_floor_area_W_m2': entry['value_W_m2'], 'zones': entry['zones'],
                                  'schedule': entry['schedule'], 'program_floor_area_m2': entry['program_floor_area_m2'],
                                  'replaced_value_W_m2': load['value'], 'replaced_evidence_id': load['evidence_id']},
               'original_unit': 'W/m2', 'transformation': document['transformation'],
               'extraction_date': document['extraction_date'], 'interpretation': document['interpretation']}
        eid = store_row(tree, folder, stable_id('evidence', row), row, {source['id']: source})
        if not math.isclose(load['value'], entry['value_W_m2'], rel_tol=1e-12):
            changed[record['id']] = f'{entry["quantity"]} {load["value"]} -> {entry["value_W_m2"]} W/m2'
        load.update(value=entry['value_W_m2'], evidence_id=eid)
        record['evidence_ids'] = sorted({*record['evidence_ids'], eid})
        for path in folder_paths(tree, folder):
            mix = tree[path]
            if 'composition' in mix and record['id'] in {m['program_id'] for m in mix['composition']['members']}:
                value, _, _ = mixed_load(tree, folder, mix, entry['quantity'])
                raise ValueError(f'{mix["id"]} holds {record["id"]}; recompose it ({value} W/m2) before applying the exception')
    return changed


# 3. Elevators and kitchen reach-ins ------------------------------------------------------------------------

def stored_schedule(tree, folder, schedule, source_files, rows):
    """Add a source schedule to the folder table (scripts.atlas_programs.tabulate's rule); its ID."""
    table = tree[folder+'/schedules.json']
    for eid in schedule['evidence_ids']:
        store_row(tree, folder, eid, rows[eid], source_files)
    rules = []
    for rule in schedule['rules']:
        day = 'd-'+hashlib.sha256(canonical(rule['values']).encode()).hexdigest()[:8]
        if table['days'].setdefault(day, rule['values']) != rule['values']:
            raise ValueError('Day profile hash clash: '+day)
        rules.append({**{k: v for k, v in rule.items() if k != 'values'}, 'day': day})
    content = {**{k: v for k, v in schedule.items() if k != 'rules'}, 'rules': rules}
    prefix = folder.split('/', 1)[1].replace('/', '.')
    sid = f'{prefix}.{slug(schedule["source_name"])}.{h6(content)}'
    if table['schedules'].setdefault(sid, content) != content:
        raise ValueError('Schedule ID clash: '+sid)
    return sid


def parameter(value, evidence_id):
    return {'evidence_id': evidence_id, 'required_inputs': [], 'status': 'known', 'unit': '1', 'value': value}


def services(tree, document=None):
    """Add the PNNL 90.1 elevators and reach-ins as building services; {service ID: folder and name}."""
    document = document or load_json(SERVICES)
    rows, files = document['evidence'], document['source_files']
    added = {}
    for entry in document['services']:
        folder, template, building_type = entry['folder'], entry['template'], entry['building_type']
        table = tree[folder+'/services.json']
        beneficiaries = []
        if entry['zone'] is not None:
            name = f'{entry["space_type"]}_{building_type}'
            found = [tree[p]['id'] for p in folder_paths(tree, folder) if '/programs/source/' in p and tree[p]['name'] == name]
            if len(found) != 1:
                raise ValueError(f'{folder}: {len(found)} source programs named {name} for {entry["name"]}')
            beneficiaries = found
        eid = store_row(tree, folder, entry['evidence_id'], rows[entry['evidence_id']], files)
        schedule_id = stored_schedule(tree, folder, document['schedules'][entry['schedule']], files, rows)
        identity = {'template': template, 'building_type': building_type, 'end_use': entry['end_use'], 'name': entry['name'],
                    'zone': entry['zone'], 'source': 'pnnl-ashrae901'}
        sid = f'{slug(template)}.{slug(building_type)}.{slug(entry["end_use"])}.{h6(identity)}'
        load = {'basis': 'absolute', 'demand_id': sid, 'evidence_id': eid, 'fuel': entry['fuel'], 'quantity': 'electric_equipment',
                'required_inputs': [], 'schedule_id': schedule_id, 'scope': 'building_service', 'service_id': sid,
                'status': 'known', 'thermal_effects': {k: parameter(v, eid) for k, v in sorted(entry['fractions'].items())},
                'unit': 'W', 'value': entry['value_W']}
        if entry['zone'] is not None:
            load['source_zone_multiplier'] = entry['source_zone_multiplier']
        evidence_ids = sorted({eid, *document['schedules'][entry['schedule']]['evidence_ids']})
        service = {'assignment': 'consumer_host_when_applicable' if beneficiaries else 'building_level',
                   'beneficiary_program_ids': beneficiaries, 'building_type': building_type, 'end_use': entry['end_use'],
                   'evidence_ids': evidence_ids, 'id': sid, 'load': load, 'name': entry['name'], 'ownership': 'instantiate_once',
                   'path_id': f'{building_type}|{template}|{entry["end_use"]}|{entry["name"]}', 'source_evidence_ids': [],
                   'template': template}
        if sid in table:
            raise ValueError(f'{folder}: service {sid} exists')
        table[sid] = service
        added[sid] = f'{folder} {entry["name"]} {entry["value_W"]} W'
    return added


# The whole edit ---------------------------------------------------------------------------------------------

def edit(files, cap_document=None, lighting_document=None, services_document=None):
    tree = Tree(files)
    summary = {'lighting_cap': lighting_cap(tree, cap_document), 'lighting_power': lighting_power(tree, lighting_document),
               'services': services(tree, services_document)}
    dumped = tree.dump()
    if release_editor.set_ids(dumped, {}):
        raise ValueError('A construction set moved; the 2.4.0 edits touch no construction')
    ids = release_editor.program_ids(dumped)
    if len(set(ids.values())) != len(ids) or set(ids.values()) & (set(dumped) - set(ids)):
        raise ValueError('Moved IDs collide')
    out = follow_ids(dumped, ids)
    changed = {p: d for p, d in out.items() if files.get(p) != d}
    removed = sorted(set(files) - set(out))
    return Edited(changed, removed, dict(sorted(ids.items())), summary)


def id_map_bytes(ids):
    """The ID map a 2.4.0 delta carries: release 2.3.0 IDs to their 2.4.0 IDs."""
    record = {'schema_version': '1.0.0', 'decision': ADR, 'base_release': BASE, 'release': RELEASE,
              'description': 'IDs of release 2.3.0 that move in release 2.4.0 (ADR 0060), mapped to their new values.',
              'ids': dict(sorted(ids.items()))}
    return (layered(record, 1)+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ids', action='store_true', help='print every ID that moves')
    args = parser.parse_args()
    edited = edit(atlas_delta.files(BASE))
    summary = edited.summary
    caps = Counter(summary['lighting_cap'].values())
    print(f'Release {RELEASE} edits over {BASE}: unoccupied lighting cap on {sum(caps.values())} programs ({caps["rule"]} with the '
          f'rule, {caps["none"]} none); lighting power in {len(summary["lighting_power"])} programs; '
          f'{len(summary["services"])} services added')
    for pid, note in summary['lighting_power'].items():
        print(' ', pid, note)
    print(f'{len(edited.files)} files changed or added, {len(edited.removed)} removed, {len(edited.ids)} IDs move')
    if args.ids:
        for old, new in edited.ids.items():
            print(old, '->', new)


if __name__ == '__main__':
    main()
