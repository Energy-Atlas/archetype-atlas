"""The record edits of data release 2.5.0 (ADR 0063), as a pure function of the resolved release 2.4.0.

python -m scripts.atlas_edits_2_5_0          # what the edits change over release 2.4.0
python -m scripts.atlas_edits_2_5_0 --ids    # also print every ID that moves

`edit(files)` takes `scripts.atlas_delta.files('2.4.0')` and returns a `scripts.atlas_edits.Edited`. The delta writer
of release 2.5.0 lays it over 2.4.0. The edits read one committed input, `data/program-inputs/conditioning-sides-v1.json`
(`scripts.conditioning_sides`, built from the pinned openstudio-standards HVAC maps):

1. **Conditioning sides** (ADR 0063 section 1). A 90.1 or DOE Ref source program whose source equipment serves no
   heating (or no cooling) gets that side as an explicit null: the setpoint parameter is `known` with value null, and
   `parameters.conditioning` states `{heating_enabled, cooling_enabled}`, both citing a new evidence row with the
   systems and spaces of the HVAC map and the replaced schedule (its ID, source name and range), which stays in the
   folder's `schedules.json`. Programs that already carry the unconditioned treatment (a conditioning filling of
   ADR 0016 or ADR 0037: plenums, attics, elevator cores) are kept as they are; the input must agree with them. A
   program whose spaces are served differently (`mixed`) is left unchanged and listed.
2. **Per-side mixes** (section 2, amending ADR 0012). Every commercial mix records `composition.setpoint_coverage`,
   the represented-area share of its members that have each side. A member has a side when its setpoint is known, and
   lacks it when its record states the side is not conditioned (`parameters.conditioning`, stored value or the stored
   unconditioned filling); otherwise the side is unknown, and so is the mix's (null is not zero). Where every member has
   the side the mixed schedule is unchanged; where only some have it, it is mixed over them with the weights
   renormalised (w_i = A_i / sum of A_j over the members with the side); where none has it, the side is a known null.
   The mix states `parameters.conditioning` from its coverage. Other mixed values do not change.

IDs then follow their rules (ADR 0046 section 8, ADR 0051 section 4; `scripts.release_editor`), and every citing file
follows, as in release 2.4.0.
"""
import argparse
import copy
import math
from collections import Counter

from scripts import atlas_delta, release_editor
from scripts.atlas_edits import (Edited, Tree, del_if_untouched, drop_unused_schedules, follow_ids, program_path,
                                 schedule_of, table_schedule)
from scripts.atlas_edits_2_4_0 import store_row
from scripts.atlas_programs import stem
from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id
from scripts.iecc_commercial_values import layered
from scripts.lighting_controls import space_type

BASE = '2.4.0'
RELEASE = '2.5.0'
ADR = 'docs/adr/0063-conditioning-sides-and-per-side-mixes.md'
SIDES_INPUT = ROOT/'data/program-inputs/conditioning-sides-v1.json'
SIDES = ('heating', 'cooling')
FIELD = {'heating': 'heating_setpoint_schedule_id', 'cooling': 'cooling_setpoint_schedule_id'}
DATE = '2026-11-04'
MIX_TRANSFORMATION = ('per side: w_i = A_i / sum(A_j, members with the side); T_side(t) = sum(w_i * T_i(t)); '
                      'coverage = sum(A_i, members with the side) / sum(A_i)')
MIX_NOTE = ('ADR 0063 amends ADR 0012: each setpoint side of a mix is averaged over the members that have that side, '
            'with the weights renormalised; the coverage is the represented-area share of those members; a side no member '
            'has is a known null. A member lacks a side its record states is not conditioned.')


def degrees(tree, folder, schedule_id):
    table = tree[folder+'/schedules.json']
    entry = table['schedules'][schedule_id]
    values = [v for rule in entry['rules'] for v in table['days'][rule['day']]]
    return entry, [min(values), max(values)]


def conditioning_state(parameters):
    """The stored conditioning state of a record ({side_enabled: bool}), from its value or its unconditioned filling."""
    entry = parameters.get('conditioning')
    if not entry:
        return None
    if 'status' in entry:
        return entry['value'] if entry['status'] == 'known' else None
    return entry['filling']['set']['value']


# 1. Conditioning sides -------------------------------------------------------------------------------------

def conditioning(tree, document=None):
    """Not-served sides of source programs as known nulls; {'changed': {program ID: sides}, 'kept': [...], 'mixed': [...]}."""
    document = document or load_json(SIDES_INPUT)
    rows, source_files = document['evidence'], document['source_files']
    changed, kept, mixed = {}, [], []
    for entry in document['records']:
        states = {side: entry[side] for side in SIDES}
        if all(s == 'served' for s in states.values()):
            continue
        folder = entry['folder']
        found = [p for p in tree.files if p.startswith(folder+'/programs/source/') and space_type(tree[p]) == entry['space_type']]
        if len(found) != 1:
            raise ValueError(f'{folder}: {len(found)} source programs of space type {entry["space_type"]}')
        path = found[0]
        record = tree[path]
        if 'mixed' in states.values():
            mixed.append({'program_id': record['id'], **states,
                          **{f'{s}_served_area_share': entry[f'{s}_served_area_share'] for s in SIDES if states[s] == 'mixed'}})
            del_if_untouched(tree, path, record)
            continue
        parameters = record['parameters']
        stated = conditioning_state(parameters)
        if stated is not None:
            # The unconditioned treatment the record already holds (ADR 0016, ADR 0037 R-UNCONTROLLED): kept.
            for side in SIDES:
                if stated[f'{side}_enabled'] != (states[side] == 'served'):
                    raise ValueError(f'{record["id"]}: the record conditions {side} {stated[f"{side}_enabled"]}, the source '
                                     f'equipment says {states[side]}')
            kept.append(record['id'])
            del_if_untouched(tree, path, record)
            continue
        row = copy.deepcopy(rows[entry['evidence_id']])
        replaced = {}
        for side in SIDES:
            if states[side] != 'not_served':
                continue
            parameter = parameters[FIELD[side]]
            if parameter.get('status') != 'known' or parameter.get('value') is None:
                raise ValueError(f'{record["id"]}: {FIELD[side]} is {parameter}; a not-served side to null must have a schedule')
            schedule, span = degrees(tree, folder, parameter['value'])
            replaced[FIELD[side]] = {'schedule_id': parameter['value'], 'source_name': schedule.get('source_name') or schedule.get('name'),
                                     'degC': span, 'evidence_id': parameter['evidence_id']}
        row['original_value'] = {**row['original_value'], 'replaced_schedules': replaced}
        nulls = ', '.join(f'{field.split("_")[0]} (source schedule {r["source_name"]!r}, {format_range(r["degC"])})'
                          for field, r in replaced.items())
        row['interpretation'] += (f' The setpoint of each side with no equipment is an explicit null; the source thermostat schedule '
                                  f'stays in the evidence and in the folder schedules: {nulls}.')
        eid = store_row(tree, folder, stable_id('evidence', row), row, source_files)
        for side in SIDES:
            if states[side] == 'not_served':
                parameters[FIELD[side]] = {'evidence_id': eid, 'required_inputs': [], 'status': 'known',
                                           'unit': 'schedule reference', 'value': None}
        parameters['conditioning'] = {'evidence_id': eid, 'required_inputs': [], 'status': 'known', 'unit': 'state',
                                      'value': {f'{side}_enabled': states[side] == 'served' for side in SIDES}}
        record['evidence_ids'] = sorted({*record['evidence_ids'], eid})
        changed[record['id']] = {side: 'not_conditioned' for side in SIDES if states[side] == 'not_served'}
    return {'changed': changed, 'kept': sorted(kept), 'mixed': mixed}


def format_range(span):
    low, high = (float(f'{v:.4g}') for v in span)
    return f'{low} degC' if low == high else f'{low} to {high} degC'


# 2. Per-side mixes ----------------------------------------------------------------------------------------

def member_side(record, side):
    """'yes', 'no' or 'unknown': whether a member has a setpoint side."""
    parameter = record['parameters'].get(FIELD[side]) or {}
    stated = conditioning_state(record['parameters'])
    enabled = None if stated is None else stated.get(f'{side}_enabled')
    if parameter.get('value') is not None:
        if enabled is False:
            raise ValueError(f'{record["id"]}: a {side} setpoint on a side its record does not condition')
        return 'yes'
    return 'no' if enabled is False else 'unknown'


def mixes(tree):
    """Record each mix's per-side coverage and mix its setpoint sides over the members that have them."""
    out = {}
    paths = sorted(p for p in tree.files if p.startswith('commercial/') and '/programs/' in p and '/programs/source/' not in p)
    for path in paths:
        mix = tree[path]
        folder = path.split('/programs/')[0]
        members = mix['composition']['members']
        records = [tree[program_path(tree, m['program_id'])] for m in members]
        areas = [m['represented_area_m2'] for m in members]
        coverage, sides, rows = {}, {}, {}
        for side in SIDES:
            states = [member_side(r, side) for r in records]
            parameter = mix['parameters'][FIELD[side]]
            if 'unknown' in states:
                if parameter.get('value') is not None:
                    raise ValueError(f'{mix["id"]}: a known {side} setpoint from a member whose side is unknown')
                coverage[side], sides[side] = None, 'unknown'
                continue
            having = [i for i, s in enumerate(states) if s == 'yes']
            if len(having) == len(members):
                if parameter.get('value') is None:
                    raise ValueError(f'{mix["id"]}: every member has the {side} side but the mix has none')
                coverage[side], sides[side] = 1.0, 'all'
                continue
            coverage[side] = math.fsum(areas[i] for i in having) / math.fsum(areas)
            rows[side] = {'members': [{'source_program_id': m['source_program_id'], 'represented_area_m2': m['represented_area_m2'],
                                       'has_side': s == 'yes'} for m, s in zip(members, states)],
                          'coverage': coverage[side]}
            if not having:
                sides[side] = 'none'
                continue
            total = math.fsum(areas[i] for i in having)
            weights = [areas[i] / total for i in having]
            refs = [records[i]['parameters'][FIELD[side]]['value'] for i in having]
            from scripts.program_composition import mix_schedule
            mixed = mix_schedule([schedule_of(tree, folder, ref) for ref in refs], weights)
            if mixed is None:
                raise ValueError(f'{mix["id"]}: the {side} setpoints of {refs} do not mix on their rule calendars')
            rows[side]['weights'] = weights
            sides[side] = mixed
        if rows:
            row = {'extraction_date': DATE, 'locator': f'{ADR}#2-per-side-mixes', 'original_unit': 'm2; dimensionless',
                   'original_value': {side: rows[side] for side in sorted(rows)}, 'source_file_id': None,
                   'interpretation': MIX_NOTE, 'transformation': MIX_TRANSFORMATION}
            eid = store_row(tree, folder, stable_id('evidence', {**row, 'mix': mix['name'], 'folder': folder}), row, {})
            mix['evidence_ids'] = sorted({*mix['evidence_ids'], eid})
            label = stem(mix['name'], mix['building_type'])
            old = []
            for side, result in sides.items():
                if side not in rows:
                    continue
                parameter = mix['parameters'][FIELD[side]]
                if parameter.get('value') is not None:
                    old.append(parameter['value'])
                value = None if result == 'none' else table_schedule(tree, folder, result, f'{label} {side}_setpoint', [eid])
                mix['parameters'][FIELD[side]] = {'evidence_id': eid, 'required_inputs': [], 'status': 'known',
                                                  'unit': 'schedule reference', 'value': value}
            table = tree[folder+'/schedules.json']['schedules']
            drop_unused_schedules(tree, folder, [s for s in old if table[s].get('derivation') == 'composed'])
        else:
            eid = mix['parameters'][FIELD['heating']]['evidence_id']
        mix['composition']['setpoint_coverage'] = coverage
        if None not in coverage.values():
            mix['parameters']['conditioning'] = {'evidence_id': eid, 'required_inputs': [], 'status': 'known', 'unit': 'state',
                                                 'value': {f'{side}_enabled': coverage[side] > 0 for side in SIDES}}
        out[mix['id']] = {side: (coverage[side], sides[side] if isinstance(sides[side], str) else 'some') for side in SIDES}
    return out


# The whole edit ---------------------------------------------------------------------------------------------

def edit(files, sides_document=None):
    tree = Tree(files)
    summary = {'conditioning': conditioning(tree, sides_document), 'mixes': mixes(tree)}
    dumped = tree.dump()
    if release_editor.set_ids(dumped, {}):
        raise ValueError('A construction set moved; the 2.5.0 edits touch no construction')
    ids = release_editor.program_ids(dumped)
    if len(set(ids.values())) != len(ids) or set(ids.values()) & (set(dumped) - set(ids)):
        raise ValueError('Moved IDs collide')
    out = follow_ids(dumped, ids)
    changed = {p: d for p, d in out.items() if files.get(p) != d}
    removed = sorted(set(files) - set(out))
    return Edited(changed, removed, dict(sorted(ids.items())), summary)


def id_map_bytes(ids):
    """The ID map a 2.5.0 delta carries: release 2.4.0 IDs to their 2.5.0 IDs."""
    record = {'schema_version': '1.0.0', 'decision': ADR, 'base_release': BASE, 'release': RELEASE,
              'description': 'IDs of release 2.4.0 that move in release 2.5.0 (ADR 0063), mapped to their new values.',
              'ids': dict(sorted(ids.items()))}
    return (layered(record, 1)+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ids', action='store_true', help='print every ID that moves')
    args = parser.parse_args()
    edited = edit(atlas_delta.files(BASE))
    summary = edited.summary
    sides = Counter(s for v in summary['conditioning']['changed'].values() for s in v)
    print(f'Release {RELEASE} edits over {BASE}: {len(summary["conditioning"]["changed"])} source programs with a side not '
          f'conditioned ({dict(sides)}); {len(summary["conditioning"]["kept"])} unconditioned programs kept; '
          f'{len(summary["conditioning"]["mixed"])} programs with mixed service left unchanged')
    for pid, change in summary['conditioning']['changed'].items():
        print(' ', pid, change)
    for entry in summary['conditioning']['mixed']:
        print('  mixed', entry)
    kinds = Counter(f'{v["heating"][1]}/{v["cooling"][1]}' for v in summary['mixes'].values())
    print(f'{len(summary["mixes"])} mixes (heating/cooling: {dict(kinds)})')
    for pid, v in summary['mixes'].items():
        if v['heating'][1] != 'all' or v['cooling'][1] != 'all':
            print(f'  {pid} heating {v["heating"]} cooling {v["cooling"]}')
    print(f'{len(edited.files)} files changed or added, {len(edited.removed)} removed, {len(edited.ids)} IDs move')
    if args.ids:
        for old, new in edited.ids.items():
            print(old, '->', new)


if __name__ == '__main__':
    main()
