"""Programs for the plenums ADR 0039 left unmapped, for release 1.5.0 (ADR 0044, plan G1).

python -m scripts.plenum_aliases [--raw-root DIR] [--check]

Reruns the construction-only build (scripts.construction_only_programs) with the alias
table sources/plenum-aliases.json applied to the source spaces: the 90 spaces without
standards tags or without a matching row take the template's Any/Plenum row. The
committed input data/program-inputs/plenum-aliases-v1.json holds only what that adds to
data/program-inputs/construction-only-v1.json (programs, twins, resolutions, unresolved
fields, schedules, evidence and source files), which stays as release 1.2.0 pinned it.
The new plenum programs take the resolution policy's plenum rules, as the 1.0.0 office
plenums do (openstudio-standards applies no internal loads to plenums): no occupancy, no
lighting, no hot water, unconditioned. The build fails if an aliased space counts toward
floor area or if any mix, system or service would change, so the general mixes keep their
weights.
--check rebuilds and compares the committed file.
"""
import argparse
import contextlib
import copy
import json
from pathlib import Path

from scripts.common import ROOT, load_json

ALIASES = ROOT/'sources/plenum-aliases.json'
OUTPUT = ROOT/'data/program-inputs/plenum-aliases-v1.json'
ADDED = ('programs', 'resolutions', 'schedules', 'components', 'provenance', 'source_files')
PLENUM_RULES = ('no_occupancy_program_ids', 'no_lighting_program_ids', 'no_hot_water_program_ids', 'unconditioned_program_ids')
PLENUM_NOTE = ('User decision (ADR 0044, plan G1): an aliased Any/Plenum space. openstudio-standards applies no internal '
               'loads to plenums (Standards.SpaceType.rb space_type_apply_internal_loads), as for the 1.0.0 office plenums.')
UNCHANGED = ('compositions', 'hvac_systems', 'services', 'area_defaults', 'completion_evidence', 'water_paths')


def table(aliases=None):
    """{(building type, space name or None, tag or None): reason}."""
    aliases = aliases or load_json(ALIASES)
    out = {}
    for entry in aliases['aliases']:
        if 'tag' in entry:
            out[(entry['building_type'], None, tuple(entry['tag']))] = entry['reason']
        for name in entry.get('spaces', []):
            out[(entry['building_type'], name, None)] = entry['reason']
    return out, (aliases['target']['standards_building_type'], aliases['target']['space_type'])


@contextlib.contextmanager
def aliased(aliases=None):
    """scripts.build reads the aliased tags for the length of one build; records what it aliased."""
    from scripts import build, resolve
    rules, (target_building, target_space) = table(aliases)
    applied, current = [], {}
    read, model, resolve_records = build.spaces, build.Builder.model, resolve.resolve_records

    def plenum_policy(data, policy, *args, **kwargs):
        plenums = [p['id'] for p in data['programs'] if (p.get('source_building_type'), p.get('source_space_type')) ==
                   (target_building, target_space)]
        policy = {**policy, **{k: sorted({*policy.get(k, []), *plenums}) for k in PLENUM_RULES},
                  'occupancy_notes': {**policy.get('occupancy_notes', {}), **{pid: PLENUM_NOTE for pid in plenums}}}
        return resolve_records(data, policy, *args, **kwargs)

    def spaces(text):
        out = read(text)
        building = current.get('building_type')
        for space in out:
            tag = (space['source_building_type'], space['source_space_type'])
            rule = (building, space['name'], None) if (building, space['name'], None) in rules else (building, None, tag)
            if rule not in rules or (rule[1] and any(tag)):
                continue
            if space['part_of_total_floor_area'] == 'Yes':
                raise ValueError(f'Aliased space {building} {space["name"]} counts toward floor area; the mixes would change')
            applied.append({'template': current['template'], 'building_type': building, 'space': space['name'],
                            'source_tags': list(tag), 'reason': rules[rule]})
            space['source_building_type'], space['source_space_type'] = target_building, target_space
        return out

    def tracked(self, t, entry):
        current.update(template=t['template'], building_type=entry['building_type'])
        return model(self, t, entry)
    build.spaces, build.Builder.model, resolve.resolve_records = spaces, tracked, plenum_policy
    try:
        yield applied
    finally:
        build.spaces, build.Builder.model, resolve.resolve_records = read, model, resolve_records


def build_document(raw_root=ROOT/'data/raw'):
    from scripts import construction_only_programs
    base = load_json(construction_only_programs.OUTPUT)
    with aliased() as applied:
        rebuilt = construction_only_programs.build(raw_root)
    for key in UNCHANGED:
        if rebuilt[key] != base[key]:
            raise ValueError(f'The plenum aliases would change {key} of the construction-only input')
    added = {}
    for key in ADDED:
        known = {r['id']: r for r in base[key]}
        changed = [r['id'] for r in rebuilt[key] if r['id'] in known and r != known[r['id']]]
        lost = known.keys() - {r['id'] for r in rebuilt[key]}
        if changed or lost:
            raise ValueError(f'The plenum aliases would change or drop {key}: {(changed + sorted(lost))[:3]}')
        added[key] = [r for r in rebuilt[key] if r['id'] not in known]
    known = {json.dumps(r, sort_keys=True) for r in base['unresolved']}
    added['unresolved'] = [r for r in rebuilt['unresolved'] if json.dumps(r, sort_keys=True) not in known]
    if len(added['unresolved']) != len(rebuilt['unresolved']) - len(base['unresolved']):
        raise ValueError('The plenum aliases would drop unresolved fields')
    return {
        'schema_version': '1.0.0', 'kind': 'plenum_alias_definitions', 'adr': 'docs/adr/0044-lighting-controls.md',
        'generated_by': 'python -m scripts.plenum_aliases', 'base_input': construction_only_programs.OUTPUT.relative_to(ROOT).as_posix(),
        'input_sha256': {p: construction_only_programs.sha(ROOT/p) for p in
                         ('sources/plenum-aliases.json', 'data/program-inputs/construction-only-v1.json')},
        'aliased_spaces': sorted(applied, key=lambda a: (a['template'], a['building_type'], a['space'])),
        'coverage_gaps': rebuilt['coverage_gaps'], **added}


def apply(programs, document=None):
    """Add the aliased plenum programs and their twins to an atlas_programs.Sources (after the construction-only overlay)."""
    document = document or load_json(OUTPUT)
    clash = {p['id'] for p in document['programs']} & programs.programs.keys()
    if clash:
        raise ValueError('Plenum programs already in the sources: '+', '.join(sorted(clash)[:3]))
    programs.programs.update({p['id']: copy.deepcopy(p) for p in document['programs']})
    programs.schedules.update({s['id']: copy.deepcopy(s) for s in document['schedules']})
    programs.evidence.update({e['id']: copy.deepcopy(e) for e in document['provenance']})
    for source in document['source_files']:
        programs.source_files.setdefault(source['id'], copy.deepcopy(source))
    programs.resolutions.update({r['id']: copy.deepcopy(r) for r in document['resolutions']})
    for row in document['unresolved']:
        programs.unresolved[row['record_id']].append(copy.deepcopy(row))
    programs.twins = {p['source_definition_id']: p for p in programs.programs.values() if p.get('source_definition_id')}


def encode(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--raw-root', type=Path, default=ROOT/'data/raw')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = encode(build_document(args.raw_root))
    if args.check:
        if OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.relative_to(ROOT)} does not reproduce; run python -m scripts.plenum_aliases')
        print('Plenum alias definitions reproduce')
        return
    OUTPUT.write_bytes(data)
    document = json.loads(data)
    print(f"{len(document['aliased_spaces'])} spaces aliased, {len(document['programs'])} programs added, "
          f"{len(document['coverage_gaps'])} unmapped spaces left")


if __name__ == '__main__':
    main()
