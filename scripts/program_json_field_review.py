"""Summarize missing program-JSON fields by load type, retaining annotations."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import re

from scripts.common import ROOT, dump_json, load_json
from scripts.definition_release import read_bundle
from scripts.program_json import ProgramExporter
from scripts.schedule_json import has_full_coverage

DOC = ROOT / 'docs/reviews/program-json-field-review.md'
CACHE = ROOT / 'build/program-json-field-review.json'
RELEASE = ROOT / 'data/definition-releases/v0.1.1'
BASE = ROOT / 'data/releases/v0.2.0'
DATE = '2026-10-09'
BLOCK = re.compile(r'<!-- annotation:([^\n]+):begin -->\n(.*?)\n<!-- annotation:\1:end -->', re.S)
LABELS = {'occupancy': 'Occupancy', 'lighting': 'Lighting', 'electric_equipment': 'Electric equipment',
          'gas_equipment': 'Gas equipment', 'hot_water': 'Hot water', 'controls': 'Controls',
          'source.evidence': 'Source evidence', 'schedules': 'Schedules'}


def hashes():
    paths = [RELEASE / n for n in ('manifest.json', 'programs.json', 'schedules.json', 'services.json',
                                  'compositions.json', 'provenance.json', 'metadata.json')]
    paths += [BASE / n for n in ('programs.json', 'residential_archetypes.json')]
    paths += [ROOT / n for n in ('schemas/program-json-v2.schema.json', 'sources/program-json-defaults.json',
                                 'scripts/program_json.py', 'scripts/schedule_json.py')]
    paths += [ROOT / 'data/completion-releases/v0.1.0/commercial-completion.json']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def collect(inputs):
    bundle = read_bundle(RELEASE)
    exporter = ProgramExporter(bundle)
    rows = exporter.programs
    stats = defaultdict(lambda: {'eligible': 0, 'missing': 0, 'program_ids': set(), 'end_uses': Counter(), 'locations': Counter()})
    seen_schedules = {}

    def observe(section, field, value, row, end_use=None, location=None):
        s = stats[section + ':' + field]
        s['eligible'] += 1
        if value is None:
            s['missing'] += 1
            s['program_ids'].add(row['id'])
            if end_use:
                s['end_uses'][end_use] += 1
            if location:
                s['locations'][location] += 1

    for number, row in enumerate(bundle['programs'], 1):
        raw = exporter.export(row['id'], 'raw')
        for field, value in raw['controls'].items():
            observe('controls', field, value, row)
        for evidence in raw['source']['evidence']:
            for field in ('source_file_id', 'original_value', 'original_unit'):
                observe('source.evidence', field, evidence[field], row)
        demands = [('loads[]', load) for load in raw['loads']]
        demands += [('shared_services[].loads[]', load) for service in raw['shared_services'] for load in service['loads']]
        for location, load in demands:
            for field in ('value', 'schedule_id', 'target_temperature_schedule_id', 'inlet_temperature_schedule_id'):
                if field in load:
                    observe(load['type'], field, load[field], row, load['end_use'], location)
            for field, value in load.get('heat_fractions', {}).items():
                observe(load['type'], 'heat_fractions.' + field, value, row, load['end_use'], location)
        for sid, schedule in raw['schedules'].items():
            if schedule['type'] == 'ruleset':
                if sid not in seen_schedules:
                    seen_schedules[sid] = has_full_coverage(schedule)
                    observe('schedules', 'rules coverage', True if seen_schedules[sid] else None, row)
                if not seen_schedules[sid]:
                    stats['schedules:rules coverage']['program_ids'].add(row['id'])
        if number % 250 == 0:
            print(f'Inspected raw exports {number}/{len(rows)}', flush=True)

    result = []
    for key, stat in sorted(stats.items()):
        if not stat['missing']:
            continue
        affected = [rows[identity] for identity in sorted(stat.pop('program_ids'))]
        stat['programs'] = len(affected)
        stat['building_types'] = dict(Counter(r['building_type'] for r in affected))
        stat['views'] = dict(Counter(r['evidence_view'] for r in affected))
        stat['residential'] = sum(r.get('scope') == 'whole_dwelling' for r in affected)
        stat['support'] = sum(any(t in r['name'].lower() for t in ('attic', 'plenum', 'basement', 'data center')) for r in affected)
        stat['examples'] = list(dict.fromkeys(r['name'] for r in affected))[:4]
        stat['end_uses'] = dict(stat['end_uses'])
        stat['locations'] = dict(stat['locations'])
        result.append({'key': key, **stat})
    source = load_json(BASE / 'programs.json')
    omitted_air = []
    for field in ('ventilation_m3_s_m2', 'ventilation_m3_s_person', 'ventilation_ach', 'infiltration_m3_s_m2', 'infiltration_basis'):
        missing = [r for r in source if r.get(field) is None]
        omitted_air.append({'field': field, 'known': len(source) - len(missing), 'missing': len(missing),
                            'buildings': dict(Counter(r['building_type'] for r in missing)),
                            'examples': list(dict.fromkeys(r['source_space_type'] for r in missing))[:6]})
    fixture_profiles = Counter()
    for row in bundle['programs']:
        if row.get('scope') != 'whole_dwelling':
            continue
        proof = {p['evidence_id'] for name, p in row['parameters'].items() if 'setpoint' in name}
        channels = {s['source_channel'] for s in bundle['schedules'] if s.get('source_channel') and proof.intersection(s.get('evidence_ids', []))}
        fixture_profiles.update(channels.intersection({'dishwasher', 'hot_water_dishwasher', 'ceiling_fan', 'lighting_garage'}))
    dwellings = load_json(BASE / 'residential_archetypes.json')
    fuel = {field: dict(Counter(r['selected_options'].get(field) for r in dwellings)) for field in ('Cooking Range', 'Clothes Dryer')}
    water = load_json(ROOT / 'data/completion-releases/v0.1.0/commercial-completion.json')
    unallocated = [r for r in water['missing_program_evidence'] if r['coverage_resolution_status'] == 'allocation_unknown']
    return {'audit_version': 1, 'date': DATE, 'input_sha256': inputs, 'raw_exports_validated': len(rows),
            'fields': result, 'air': omitted_air, 'omitted_channels': dict(fixture_profiles), 'fuel': fuel,
            'water_allocation': {'missing': len(unallocated), 'buildings': dict(Counter(r['building_type'] for r in unallocated))}}


def annotations(text):
    blocks = {}
    for match in BLOCK.finditer(text):
        if match[1] in blocks:
            raise ValueError('Duplicate annotation: ' + match[1])
        blocks[match[1]] = match[2]
    if text.count('<!-- annotation:') != len(blocks) * 2:
        raise ValueError('Malformed annotation markers')
    return blocks


def escape(value):
    return str(value).replace('|', '&#124;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', ' ')


def counted(values):
    return '; '.join(f'{escape(k)} ({v})' for k, v in sorted(values.items(), key=lambda item: (-item[1], item[0])))


def field_pattern(section, field, stat):
    notes = []
    if section == 'source.evidence':
        return 'Evidence metadata can legitimately be null for unknown source values or derived records. Keep those unknowns; do not fill evidence with simulation defaults.'
    if section == 'schedules':
        return 'Five distinct rulesets lack complete date/day-selector coverage, including special days. A known schedule reference does not guarantee complete coverage.'
    if field.startswith('heat_fractions.'):
        notes.append('Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares.')
    if section == 'controls' and field.startswith('people_'):
        notes.append('Missing across every program type: the adapter does not populate these people heat-partition operands.')
    elif section == 'controls' and field.endswith('_enabled'):
        notes.append('Missing broadly across commercial programs and all dwellings; explicit disabled states exist only in selected reviewed support programs.')
    if field == 'inlet_temperature_schedule_id':
        notes.append('Every water-demand entry lacks inlet temperature; the exporter currently does not ingest it.')
    if section == 'lighting' and field == 'value':
        notes.append('Most gaps are additional lighting, not ordinary lighting: commercial source leaves lack 741/768 additional-lighting magnitudes versus 10/768 ordinary-lighting magnitudes. All 41 dwelling lighting magnitudes are unresolved.')
    if section == 'gas_equipment' and field in {'value', 'schedule_id'}:
        notes.append('713/768 commercial source leaves lack a gas end-use magnitude/reference. Many reviewed overlays supply reviewed zeros; a raw null alone does not prove absence.')
    if section == 'electric_equipment' and field == 'value':
        notes.append('All 205 exported residential appliance/plug-load magnitudes are unresolved; 33/768 commercial source equipment magnitudes are also missing.')
    if section == 'hot_water' and field == 'value':
        notes.append('All 82 residential water magnitudes are unresolved. Existing commercial local/shared demand magnitudes are present; unknown allocations are a separate gap below.')
    if stat['residential'] and not field.startswith('heat_fractions.'):
        notes.append(f'{stat["residential"]}/{stat["programs"]} affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude.')
    if stat['support']:
        notes.append(f'{stat["support"]}/{stat["programs"]} affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.')
    return ' '.join(notes) or 'Gaps span the building/program types listed below; no narrower pattern was established by this scan.'


def handling(section, field):
    if section == 'source.evidence':
        return 'Preserve null; no experimental defaults apply to evidence.'
    if section == 'schedules':
        return 'Prepend a lowest-priority Default rule: 0 for fractions, 120 W/person for activity, or a compatible temperature fallback; preserve all source rules.'
    if field.startswith('heat_fractions.'):
        return '0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.'
    return {
        'value': '0 in the declared unit for an unknown source-leaf magnitude; rebuild mixtures from leaves and preserve known contributions.',
        'schedule_id': 'Missing schedule: constant 0 for zero magnitude, constant 1 for a known positive magnitude. Preserve existing profiles.',
        'target_temperature_schedule_id': '60 degC nominal; preserve known target temperatures and keep target at or above known inlet.',
        'inlet_temperature_schedule_id': '10 degC nominal; if target is known, use min(10, minimum target).',
        'heating_enabled': 'true when unknown; preserve known false.', 'cooling_enabled': 'true when unknown; preserve known false.',
        'heating_setpoint_schedule_id': '20 degC nominal; if cooling is known, use min(20, minimum cooling - 2).',
        'cooling_setpoint_schedule_id': '26 degC nominal; if heating is known, use max(26, maximum heating + 2).',
        'activity_schedule_id': 'Constant 120 W/person.', 'people_radiant_fraction': '0.3 of people sensible heat.',
        'people_sensible_fraction': 'autocalculate: simulation engine determines sensible/latent split.',
    }[field]


def render(audit, saved):
    lines = ['# Program JSON field review', '', f'Audit date: {audit["date"]}. Program JSON schema: **2.0.0**. Definitions: **v0.1.1**.', '',
             'This working document has **one review entry per JSON field and load type**, aggregated across all program definitions. '
             'It contains no individual program-record entries. Each field has its own annotation area.', '',
             f'Coverage uses {audit["raw_exports_validated"]:,} validated raw exports, before the experimental program-default policy. '
             'Source records, reviewed variants and mixtures are counted separately; these are not population weights. '
             'Missing counts are field occurrences; affected-program counts deduplicate program IDs within that field.', '',
             'Hot-water counts include local and shared-service loads. Shared references are not additional physical services. '
             'Only applicable fields enter a denominator; absent inapplicable properties are not treated as missing. '
             'Null means unknown/unreported, not zero. Passing the current schema does not establish complete program semantics.', '',
             'Write in each **Your annotations / proposed approach** area and keep its markers intact. '
             'Regeneration preserves annotations and refuses to discard orphaned blocks. The stated defaults describe existing behavior; they are not new decisions.', '',
             '```powershell', '.venv/Scripts/python.exe -m scripts.program_json_field_review --refresh',
             '.venv/Scripts/python.exe -m scripts.program_json_field_review --check', '```', '',
             '## Load and control fields with missing data', '']
    keys = set()

    def entry(key, title, body):
        keys.add(key)
        lines.extend(['### ' + title, '', *body, '', f'<!-- annotation:{key}:begin -->',
                      saved.get(key, '**Your annotations / proposed approach:**\n\n\n**Agreed decision:**\n\n\n**Status:** Open'),
                      f'<!-- annotation:{key}:end -->', ''])

    for stat in audit['fields']:
        section, field = stat['key'].split(':', 1)
        path = f'controls.{field}' if section == 'controls' else f'source.evidence[].{field}' if section == 'source.evidence' else 'schedules[].rules' if section == 'schedules' else f'loads[].{field} (type={section})'
        if section == 'hot_water':
            path += '; also shared_services[].loads[]'
        body = [f'**JSON field:** `{path}`.', '',
                f'**Missing:** {stat["missing"]:,}/{stat["eligible"]:,} applicable field occurrences; **affected programs:** {stat["programs"]:,}.', '',
                '**Pattern / shared program types:** ' + field_pattern(section, field, stat), '',
                '**Affected building types:** ' + counted(stat['building_types']) + '.', '',
                '**Current handling:** ' + handling(section, field)]
        if stat['end_uses']:
            body += ['', '**Missing occurrences by end use:** ' + counted(stat['end_uses']) + '.']
        if section == 'hot_water':
            body += ['', '**Missing occurrences by scope:** ' + counted(stat['locations']) + '.']
        entry(stat['key'], LABELS[section] + ' — `' + field + '`', body)

    lines += ['## Missing or omitted information without a usable DTO field', '',
              'These are contract/export gaps, kept separate from null operands in existing fields. Their annotation areas can record whether and how to add them.', '']
    for stat in audit['air']:
        body = [f'**Field to review:** `{stat["field"]}`; not represented in program JSON.', '',
                f'**Upstream commercial coverage:** {stat["known"]}/768 present; {stat["missing"]}/768 unknown.', '',
                '**Pattern:** Known outdoor-air terms are omitted by the DTO. Missing per-area/per-person/ACH terms may be alternative inputs; do not infer total ventilation from one term alone. '
                'Infiltration rate and basis remain unresolved across the commercial source selection.', '',
                '**Building types with upstream nulls:** ' + counted(stat['buildings']) + '.', '',
                '**Example source space types with nulls:** ' + ', '.join(escape(n) for n in stat['examples']) + '.', '',
                '**Current handling:** No program-JSON fallback. Preserve source bases and distinguish ventilation from infiltration.']
        entry('omitted:' + stat['field'], '`' + stat['field'] + '` — air requirements', body)
    for channel, count in sorted(audit['omitted_channels'].items()):
        entry('omitted:' + channel, '`loads[].end_use=' + channel + '` — absent demand channel',
              [f'**Coverage gap:** {count}/41 dwelling configurations retain this channel\'s annual profile upstream but have no corresponding exported load.', '',
               '**Pattern:** Whole-dwelling records; the fixed exporter channel list omits this end use. A retained profile does not establish its missing magnitude.', '',
               '**Current handling:** No load created and no magnitude fallback applied to this omitted channel.'])
    for option, channel in [('Cooking Range', 'cooking_range'), ('Clothes Dryer', 'clothes_dryer')]:
        fuels = audit['fuel'][option]
        count = fuels.get('Gas', 0) + fuels.get('Propane', 0)
        entry('classification:' + channel, '`loads[].type` — ' + channel + ' fuel',
              [f'**Gap:** {count}/41 source configurations select Gas or Propane, but this channel is labelled `electric_equipment`.', '',
               '**Pattern:** Residential ' + option.lower() + '; source-option counts: ' + counted(fuels) + '.', '',
               '**Current handling:** Category is inferred from the channel name rather than source fuel; magnitudes remain unknown. No correction applied by this review.'])
    water = audit['water_allocation']
    entry('omitted:water_allocation', 'Hot water — program/service allocation',
          [f'**Missing:** {water["missing"]} distinct commercial source-program allocations remain unresolved.', '',
           '**Pattern / building types:** ' + counted(water['buildings']) + '. Concentrated in supermarkets, hotels, hospitals and schools.', '',
           '**Current handling:** Shared services and reporting allocations do not prove local fixture placement. Keep source unknowns distinct from the 206 reviewed no-modeled-draw cases.'])
    for key, title, body in [
        ('omitted:residential_air', 'Residential — natural infiltration and outdoor air', 'All 41 dwelling DTOs omit these operands. Separate enclosure definitions retain unresolved natural infiltration/outdoor air; pressure-test leakage such as ACH50 requires a conversion model, geometry and weather.'),
        ('omitted:source_climate', '`source.climate` — dedicated context field', 'Residential climate context exists in canonical definitions/evidence but has no dedicated DTO field. Program data are not duplicated by climate merely to fill a Cartesian table.'),
        ('omitted:source_vintage', '`source.vintage` — dedicated context field', 'Residential stock vintage exists upstream but has no dedicated DTO field. Keep existing-stock vintages distinct from code/prototype templates.'),
        ('omitted:composition', 'Composition — members and weights', 'The 378 mixture definitions lack dedicated DTO recipe/member fields. Weighted demand trajectories are exported, while recipe membership/weights remain in the pinned definitions. Resolve missing source leaves before recomposition.'),
        ('omitted:provenance', 'Provenance — operand links and source descriptors', 'All programs retain program-level evidence, but lack a complete self-contained operand-to-evidence map and upstream revision/checksum descriptors. The repository retains pinned source evidence; this is an export representation gap.'),
    ]:
        entry(key, title, ['**Pattern / missing information:** ' + body, '', '**Current handling:** No new fields or defaults added by this review.'])
    if set(saved) - keys:
        raise ValueError('Refusing to discard annotations: ' + ', '.join(sorted(set(saved) - keys)))
    lines += ['## Scope boundaries and pinned inputs', '',
              'Geometry, area/count scaling, calendar/holiday bindings, service hosts, envelope and HVAC/sizing remain separate consumer inputs/contracts. '
              'Residential annual profiles retain their recorded 2007 calendar and schedule-only/proxy-weather limitations. '
              'Identity, type, unit and scaling-basis fields have no missing values in this audit. Raw `default_policy_id=null` and `assumptions=[]` are intentional mode semantics. '
              'Source evidence may legitimately remain null even in defaulted exports. No original physical data or default policy changes are made by this document.', '',
              'Counts are derived from the following SHA-256-pinned inputs. Original values, units, source locators, transformations, extraction dates and interpretation notes remain in the frozen evidence.', '',
              '| Input | SHA-256 |', '| --- | --- |']
    for path, digest in sorted(audit['input_sha256'].items()):
        lines.append(f'| [{path}](../../{path}) | `{digest}` |')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    inputs = hashes()
    audit = load_json(CACHE) if CACHE.exists() and not args.refresh else None
    if not audit or audit.get('input_sha256') != inputs or audit.get('audit_version') != 1:
        audit = collect(inputs)
        dump_json(CACHE, audit)
    current = DOC.read_text(encoding='utf-8') if DOC.exists() else ''
    result = render(audit, annotations(current))
    if args.check:
        if current != result:
            raise SystemExit('Field review differs from audited inputs; regenerate while retaining annotations')
        print('Field review verified; annotations retained')
    else:
        DOC.write_text(result, encoding='utf-8', newline='\n')
        print(f'Wrote {DOC}: {len(annotations(result))} field annotation areas; {len(result.encode())} bytes')


if __name__ == '__main__':
    main()
