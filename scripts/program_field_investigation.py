"""Reproduce the grouped evidence behind the program-field annotation responses.

This reads frozen data and locked local source archives; it changes no releases.
The local runtime and standards archives must already have been retrieved.
"""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import tarfile

from scripts.common import ROOT, dump_json, load_json

OUTPUT = ROOT / 'docs/reviews/program-json-investigation-evidence.json'
INSPECTION_DATE = '2026-10-11'


def investigation_group(key):
    section, field = key.split(':', 1)
    if section == 'controls':
        if field == 'activity_schedule_id': return 'people-activity'
        if field.startswith('people_'): return 'people-heat'
        return 'conditioning'
    if field.startswith('heat_fractions.'):
        return 'lighting-heat' if section == 'lighting' else 'equipment-heat'
    if section == 'gas_equipment': return 'gas-presence'
    if section == 'hot_water':
        return 'water-inlet' if field == 'inlet_temperature_schedule_id' else 'water-demands'
    if section in {'electric_equipment', 'lighting', 'occupancy'}: return 'load-coverage'
    if section == 'schedules': return 'schedule-coverage'
    if section == 'source.evidence' or field == 'provenance': return 'provenance'
    if section == 'classification' or field in {'ceiling_fan', 'dishwasher', 'hot_water_dishwasher', 'lighting_garage'}:
        return 'residential-channels'
    if field in {'ventilation_m3_s_m2', 'ventilation_m3_s_person', 'ventilation_ach',
                 'infiltration_m3_s_m2', 'infiltration_basis', 'residential_air'}: return 'air-requirements'
    return {'water_allocation': 'water-allocation', 'source_climate': 'context',
            'source_vintage': 'context', 'composition': 'composition'}[field]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_inventory():
    result = []
    locks = [('sources/runtime-lock.json', 'build/runtime'),
             ('sources/commercial-runtime-lock.json', 'build/commercial-runtime')]
    for lock_name, local in locks:
        for item in load_json(ROOT / lock_name)['archives']:
            archive = ROOT / local / (item['name'] + '.tar.gz')
            if digest(archive) != item['sha256']:
                raise ValueError('Archive checksum mismatch: ' + archive.name)
            base = ROOT / local / item['name'] / item['root']
            if item['name'] == 'rs':
                prefix = 'resources/hpxml-measures/'
                paths = [prefix + 'HPXMLtoOpenStudio/resources/' + n + '.rb' for n in
                         ('internal_gains', 'defaults', 'model', 'misc_loads', 'lighting',
                          'hotwater_appliances', 'schedules', 'unit_conversions')]
                paths += [prefix + 'BuildResidentialScheduleFile/measure.rb']
                repo, revision = 'resstock', item['version']
            elif item['name'] == 'standards-controls':
                paths = ['lib/openstudio-standards/standards/Standards.' + n + '.rb'
                         for n in ('SpaceType', 'People', 'Model')]
                repo, revision = 'openstudio-standards', item['source_revision']
            else:
                paths = ['EnergyPlus/Energy+.idd']
                repo, revision = 'OpenStudio', item['version']
            # Compare inspected bytes directly to the immutable, checksum-locked archive.
            with tarfile.open(archive) as source:
                for path in paths:
                    member = source.extractfile(item['root'] + '/' + path)
                    if member is None or member.read() != (base / path).read_bytes():
                        raise ValueError('Extracted source differs from locked archive: ' + path)
                    url = ('https://github.com/NatLabRockies/' + repo + '/blob/' + revision + '/' + path
                           if repo != 'OpenStudio' else item['url'])
                    result.append({'project': repo, 'revision': revision, 'path': path,
                                   'sha256': digest(base / path), 'url': url, 'archive_lock': lock_name,
                                   'archive_sha256': item['sha256'], 'inspection_date': INSPECTION_DATE,
                                   'transformation': 'read-only source inspection; byte comparison to locked archive',
                                   'interpretation': 'Generator rules/engine defaults, not observed dwelling measurements'})
    return result


def inspect_schedule_gaps(definitions):
    """Report missing date/day selectors and evaluate the proposed explicit completion."""
    import copy
    from scripts.schedule_json import DAYS, date_mask, has_full_coverage, normalize_schedule
    schedules = load_json(ROOT / 'data/definition-releases/v0.1.1/schedules.json')
    first = dt.date(2000, 1, 1)
    result = []
    for source in schedules:
        schedule = normalize_schedule(source)
        if has_full_coverage(schedule):
            continue
        users = [p for p in definitions if any(l.get('schedule_id') == source['id'] for l in p['loads'])
                 or any(v.get('value') == source['id'] for v in p.get('parameters', {}).values())]
        if not users:
            continue
        coverage = {d: 0 for d in DAYS}
        for rule in schedule['rules']:
            tokens = set(rule['day_types'])
            for day in DAYS:
                if ('Default' in tokens or day in tokens or day in DAYS[:5] and 'Wkdy' in tokens
                        or day in {'Sat', 'Sun'} and 'Wknd' in tokens):
                    coverage[day] |= date_mask(rule['start_date'], rule['end_date'])
        gaps = {day: [(first + dt.timedelta(days=i)).strftime('%m-%d') for i in range(366)
                      if not (mask >> i) & 1] for day, mask in coverage.items()}
        gaps = {day: dates for day, dates in gaps.items() if dates}
        proposed = copy.deepcopy(schedule)
        if set(gaps) == {'Hol'}:
            sunday = next(r for r in schedule['rules'] if r['day_types'] == ['Sun'])
            proposed['rules'].append({**copy.deepcopy(sunday), 'day_types': ['Hol']})
            proposal = 'Copy this schedule\'s Sunday profile to the missing holiday selector only'
            values = sunday['values']
        elif all(dates == ['02-29'] for dates in gaps.values()):
            values = {}
            for rule in proposed['rules']:
                if rule['start_date'] == '02-01' and rule['end_date'] == '02-28':
                    rule['end_date'] = '02-29'
                    values['|'.join(rule['day_types'])] = rule['values']
            proposal = 'Extend each February rule through February 29; preserve selector-specific values'
        else:
            raise ValueError('New schedule gap needs investigation: ' + source['id'])
        if not has_full_coverage(proposed):
            raise ValueError('Proposed schedule completion is incomplete')
        # Independently evaluate every covered date/selector to show no existing value changes.
        def at(s, day, date):
            default = specific = None
            bit = 1 << (date - first).days
            for r in s['rules']:
                if not date_mask(r['start_date'], r['end_date']) & bit:
                    continue
                t = set(r['day_types'])
                if 'Default' in t:
                    default = r['values']
                if day in t or day in DAYS[:5] and 'Wkdy' in t or day in {'Sat', 'Sun'} and 'Wknd' in t:
                    specific = r['values']
            return specific if specific is not None else default
        checked = 0
        for day in DAYS:
            for i in range(366):
                date = first + dt.timedelta(days=i)
                before = at(schedule, day, date)
                if before is not None:
                    if before != at(proposed, day, date):
                        raise ValueError('Proposal changes a covered source interval')
                    checked += 1
        result.append({'schedule_id': source['id'], 'source_name': schedule['name'], 'unit': schedule['unit'],
                       'provenance_id': source.get('provenance_id'), 'affected_programs': len(users),
                       'building_types': dict(Counter(p['building_type'] for p in users)),
                       'templates': sorted({p['template'] for p in users}),
                       'missing_selectors': {day: {'date_count': len(dates), 'first': dates[0], 'last': dates[-1]}
                                             for day, dates in gaps.items()},
                       'proposal': proposal, 'proposed_values': values,
                       'proposal_status': 'discussion pending; not applied to releases or export defaults',
                       'proposal_has_full_coverage': True, 'covered_date_selectors_preserved': checked})
    return result


def collect():
    from scripts.program_json_field_review import DOC, annotations, hashes
    saved = annotations(DOC.read_text(encoding='utf-8'))
    rows = load_json(ROOT / 'data/releases/v0.2.0/programs.json')
    fields = ['heating_setpoint_schedule_id', 'cooling_setpoint_schedule_id', 'activity_schedule_id',
              'people_per_m2', 'occupancy_schedule_id', 'lighting_W_m2', 'additional_lighting_W_m2',
              'lighting_schedule_id', 'electric_equipment_W_m2', 'electric_equipment_schedule_id',
              'gas_equipment_W_m2', 'gas_equipment_schedule_id']
    commercial = {}
    for field in fields:
        missing = [r for r in rows if r[field] is None]
        stats = {'eligible': len(rows), 'missing': len(missing),
                 'space_types': dict(sorted(Counter(r['source_space_type'] for r in missing).items()))}
        magnitude = {'occupancy_schedule_id': 'people_per_m2', 'lighting_schedule_id': 'lighting_W_m2',
                     'electric_equipment_schedule_id': 'electric_equipment_W_m2',
                     'gas_equipment_schedule_id': 'gas_equipment_W_m2'}.get(field)
        if magnitude:
            stats['missing_schedule_magnitudes'] = dict(Counter('unknown' if r[magnitude] is None
                                                        else 'zero' if r[magnitude] == 0 else 'positive'
                                                        for r in missing))
        commercial[field] = stats
    root = ROOT / 'data/resolution-releases/v0.4.0'
    fixtures = load_json(ROOT / 'data/releases/v0.2.0/residential_archetypes.json')
    profiles = {r['record_id']: r for r in load_json(root / 'profile-index.json')}
    resolutions = load_json(root / 'resolutions.json')['resolutions']
    resolved = {(r['record_id'], r['field']): r for r in resolutions if r['record_table'] == 'residential_archetypes'}
    residential = {}
    for channel in ('plug_loads_other', 'plug_loads_tv', 'lighting_interior', 'clothes_washer',
                    'clothes_dryer', 'hot_water_clothes_washer', 'cooking_range', 'hot_water_fixtures'):
        missing = [r for r in fixtures if channel not in profiles[r['id']]['columns']]
        applicable = [resolved.get((r['id'], 'profile:' + channel)) for r in missing]
        residential[channel] = {'eligible': len(fixtures), 'missing_original_profile': len(missing),
                                'zero_occupants': sum(r['occupants'] == 0 for r in missing),
                                'frozen_resolution_rules': dict(Counter(r['rule'] if r else 'unresolved'
                                                                       for r in applicable))}
        if any(r is None for r in applicable):
            raise ValueError('A missing residential profile has no frozen resolution: ' + channel)
    additional = ['data/resolution-releases/v0.4.0/manifest.json',
                  'data/resolution-releases/v0.4.0/resolutions.json',
                  'data/resolution-releases/v0.4.0/profile-index.json',
                  'scripts/residential_definitions.py', 'scripts/program_definitions.py',
                  'scripts/program_composition.py', 'scripts/program_field_investigation.py',
                  'scripts/run_residential_profiles.rb', 'sources/runtime-lock.json',
                  'sources/commercial-runtime-lock.json', 'docs/reviews/program-json-followup-source-lock.json']
    definitions = load_json(ROOT / 'data/definition-releases/v0.1.1/programs.json')
    schedule_gaps = {}
    for quantity in ('additional_lighting', 'lighting', 'electric_equipment', 'gas_equipment'):
        missing = [(r, l) for r in definitions for l in r['loads']
                   if l['quantity'] == quantity and l['schedule_id'] is None]
        schedule_gaps[quantity] = {'missing': len(missing),
            'by_derivation_and_view': dict(sorted(Counter(r['derivation'] + '/' + r['evidence_view']
                                                        for r, _ in missing).items())),
            'composed_unknown_magnitudes': sum(r['derivation'] == 'composed' and l['value'] is None
                                               for r, l in missing)}
    water = [(r, l) for r in definitions if 'residential' not in r['gate'] for l in r['loads']
             if l['quantity'].startswith('hot_water') and l.get('target_temperature_degC') is None]
    water_stats = {'missing_aggregate_targets': len(water),
                   'derivations': dict(Counter(r['derivation'] for r, _ in water)),
                   'building_types': dict(Counter(r['building_type'] for r, _ in water)),
                   'all_component_targets_known': all(l.get('source_components') and
                       all(c['load'].get('target_temperature_degC') is not None for c in l['source_components'])
                       for _, l in water),
                   'component_target_values_degC': sorted({c['load']['target_temperature_degC']
                       for _, l in water for c in l.get('source_components', [])})}
    from scripts.fetch import fetch_file
    followup_lock = load_json(ROOT / 'docs/reviews/program-json-followup-source-lock.json')
    for descriptor in followup_lock['files']:
        fetch_file(descriptor, ROOT / 'build/reviews/program-comments-2026-10-11')
    activity_missing = [r for r in rows if r['activity_schedule_id'] is None]
    return {'inspection_date': INSPECTION_DATE, 'scope': 'field/type aggregates; no individual program entries',
            'input_sha256': {**hashes(), **{p: digest(ROOT / p) for p in additional}},
            'field_groups': {k: investigation_group(k) for k in saved},
            'commercial_source_leaves': commercial, 'residential_source_profiles': residential,
            'commercial_load_schedule_gaps': schedule_gaps,
            'commercial_water_target_aggregation': water_stats,
            'commercial_missing_activity_occupancy': dict(Counter('unknown' if r['people_per_m2'] is None
                else 'zero' if r['people_per_m2'] == 0 else 'positive' for r in activity_missing)),
            'schedule_coverage_followup': inspect_schedule_gaps(definitions),
            'followup_documentation_lock': followup_lock,
            'inspected_sources': source_inventory()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = collect()
    if args.check:
        if load_json(OUTPUT) != result:
            raise SystemExit('Investigation evidence differs from inspected sources')
        print(f'Investigation evidence verified: {len(result["field_groups"])} field mappings, locked sources, frozen resolution coverage')
    else:
        dump_json(OUTPUT, result)
        print('Wrote ' + str(OUTPUT))


if __name__ == '__main__':
    main()
