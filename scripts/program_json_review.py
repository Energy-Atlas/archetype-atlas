"""Build the program-gap review ledger while preserving user comment blocks.

Run with --refresh for fresh validated raw/defaulted exports; otherwise reuse
only an ignored audit cache whose complete input fingerprints still match.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import re

from scripts.common import ROOT, dump_json, load_json
from scripts.definition_release import read_bundle
from scripts.program_json import ProgramExporter, pointer
from scripts.schedule_json import has_full_coverage

DOCUMENT = ROOT / 'docs/reviews/program-json-missing-data.md'
CACHE = ROOT / 'build/program-json-review-audit.json'
RELEASE = ROOT / 'data/definition-releases/v0.1.1'
BASE = ROOT / 'data/releases/v0.2.0'
DATE = '2026-10-09'
COMMENT = re.compile(r'<!-- user-comments:([^\n]+):begin -->\n(.*?)\n<!-- user-comments:\1:end -->', re.S)


def fingerprints():
    paths = [RELEASE / name for name in ('manifest.json', 'metadata.json', 'programs.json',
             'schedules.json', 'services.json', 'compositions.json', 'provenance.json')]
    paths += [BASE / 'programs.json', BASE / 'residential_archetypes.json']
    paths += [ROOT / name for name in ('schemas/program-json-v2.schema.json',
              'sources/program-json-defaults.json', 'scripts/program_json.py',
              'scripts/schedule_json.py', 'scripts/semantics.py', 'scripts/program_composition.py')]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def cell(value):
    return str(value).replace('|', '&#124;').replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')


def short(value):
    if isinstance(value, dict) and 'type' in value:
        if value['type'] == 'annual':
            return f"annual {value['year']}, {len(value['values'])} hourly values"
        rules = value['rules']
        if len(rules) == 1 and len(rules[0]['values']) == 1:
            return f"constant {rules[0]['values'][0]} {value['unit']}"
        return f"{len(rules)} ordered rules ({value['unit']})"
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def collect(input_hashes):
    bundle = read_bundle(RELEASE)
    exporter = ProgramExporter(bundle)
    source_rows = {r['id']: r for r in load_json(BASE / 'programs.json')}
    dwellings = {r['id']: r for r in load_json(BASE / 'residential_archetypes.json')}
    policy = {r['id']: r for r in load_json(ROOT / 'sources/program-json-defaults.json')['rules']}
    output = []

    def leaves(row):
        recipe = exporter.compositions.get(row.get('composition_id'))
        return [exporter.programs[m['program_id']] for m in recipe['members']] if recipe else [row]

    for number, row in enumerate(bundle['programs'], 1):
        raw = exporter.export(row['id'], 'raw')
        filled = exporter.export(row['id'], 'defaulted')
        gaps = []
        mixed = row.get('composition_id') in exporter.compositions

        def add(category, path, handling, note, kind='unknown', rule=None):
            gaps.append(dict(category=category, path=path, handling=handling, note=note, kind=kind, rule=rule))

        def fallback(path, rule):
            if mixed and path.startswith(('/loads/', '/shared_services/')):
                return ('Apply ' + rule + ' to unresolved source leaves, then rebuild weighted demands; '
                        'known leaf values survive and a raw shared service may become a local leaf demand')
            value = pointer(filled, path)
            if isinstance(value, str) and value in filled['schedules']:
                return short(filled['schedules'][value])
            return short(value)

        control_rules = {
            'heating_enabled': 'unknown-conditioning', 'cooling_enabled': 'unknown-conditioning',
            'heating_setpoint_schedule_id': 'unknown-heating-setpoint',
            'cooling_setpoint_schedule_id': 'unknown-cooling-setpoint',
            'activity_schedule_id': 'unknown-activity',
            'people_radiant_fraction': 'unknown-people-radiant',
            'people_sensible_fraction': 'unknown-people-sensible',
        }
        for name, value in raw['controls'].items():
            if value is None:
                path = '/controls/' + name
                rule = control_rules[name]
                add('control.' + name, path, fallback(path, rule),
                    'Raw operand is null; current experimental default is not source evidence.', rule=rule)

        locations = [('/loads', raw['loads'])] + [
            (f'/shared_services/{i}/loads', service['loads']) for i, service in enumerate(raw['shared_services'])]
        for location, loads in locations:
            for i, load in enumerate(loads):
                prefix = f'{location}/{i}'
                for name, rule in [('value', 'unknown-load'), ('schedule_id', 'unknown-load-schedule'),
                                   ('target_temperature_schedule_id', 'unknown-water-target'),
                                   ('inlet_temperature_schedule_id', 'unknown-water-inlet')]:
                    if name in load and load[name] is None:
                        path = prefix + '/' + name
                        note = f"{load['end_use']}; {load['unit']}; basis {load['basis']}; demand {load['demand_id']}."
                        if name == 'value':
                            note += ' Missing magnitude does not prove absence.'
                        add('load.' + load['end_use'] + '.' + name, path, fallback(path, rule), note, rule=rule)
                missing = [k for k, v in load.get('heat_fractions', {}).items() if v is None]
                if missing:
                    paths = ', '.join(prefix + '/heat_fractions/' + k for k in missing)
                    add('heat.' + load['type'], paths, '0 for each missing fraction; convection is the residual',
                        load['end_use'] + '; missing: ' + ', '.join(missing) +
                        '. Check applicability before treating every null as a physical unknown.', rule='unknown-heat-fraction')

        for sid, schedule in raw['schedules'].items():
            if not has_full_coverage(schedule):
                add('schedule.coverage', '/schedules/' + sid + '/rules',
                    'Prepend lowest-priority Default: 0 for fractions; compatible temperature/activity fallback otherwise',
                    'One or more recurring dates/day selectors lack coverage; includes holiday and separate design-day contexts.',
                    kind='schedule_gap', rule='unknown-schedule-coverage')

        originals = [source_rows[p['source_id']] for p in leaves(row) if p.get('source_id') in source_rows]
        if originals:
            for field in ('ventilation_m3_s_m2', 'ventilation_m3_s_person', 'ventilation_ach',
                          'infiltration_m3_s_m2', 'infiltration_basis'):
                known = [(p['id'], p[field]) for p in originals if p.get(field) is not None]
                if known:
                    values = ', '.join(f'{pid}={short(value)}' for pid, value in known)
                    add('air.' + field, 'Not represented in DTO: ' + field, 'No program-JSON fallback',
                        f'Available in {len(known)}/{len(originals)} source leaves: {values}. Preserve source basis and combination method.',
                        kind='export_omission')
                else:
                    add('air.' + field, 'Not represented in DTO: ' + field, 'No program-JSON fallback',
                        f'Null in all {len(originals)} source leaves. Missing rate/basis is not zero and does not prove inapplicability.',
                        kind='upstream_and_contract_gap')
        else:
            add('air.residential', 'No residential air-exchange fields in DTO', 'No program-JSON fallback',
                'Natural infiltration and outdoor air remain unresolved in separate dwelling enclosure definitions; pressure-test leakage is not natural infiltration.',
                kind='contract_scope')

        if row.get('scope') == 'whole_dwelling':
            fixture = dwellings[row['source_id']]
            # The determined-profile evidence is shared by this dwelling's loads
            # and schedules, so exact evidence IDs bind channels to their fixture.
            profile_ids = {p['evidence_id'] for name, p in row['parameters'].items() if 'setpoint' in name}
            fixture_schedules = {s['source_channel']: s for s in bundle['schedules']
                                if s.get('source_channel') and profile_ids.intersection(s.get('evidence_ids', []))}
            for channel in ('dishwasher', 'hot_water_dishwasher', 'ceiling_fan', 'lighting_garage'):
                if channel in fixture_schedules:
                    add('omitted_channel.' + channel, 'Absent loads[] end_use: ' + channel,
                        'No exported load or magnitude default', 'Known annual profile retained upstream: ' + fixture_schedules[channel]['id'],
                        kind='export_omission')
            for option, channel in [('Cooking Range', 'cooking_range'), ('Clothes Dryer', 'clothes_dryer')]:
                fuel = fixture['selected_options'].get(option)
                if fuel in {'Gas', 'Propane'}:
                    add('fuel.' + channel, 'loads[] ' + channel + '.type', 'Currently electric_equipment',
                        f'Source option {option}={fuel}; exporter classifies by channel rather than source fuel. Magnitude is still unknown.',
                        kind='classification_error')
            for name in ('climate', 'vintage'):
                if row.get(name) is not None:
                    add('metadata.' + name, 'No dedicated DTO source.' + name, 'Context retained only indirectly in evidence',
                        'Canonical context: ' + short(row[name]), kind='export_omission')
        if mixed:
            add('metadata.composition', 'No dedicated DTO composition/member fields',
                'Weighted demands exported; consumer-readable recipe is separate',
                f"Canonical recipe {row['composition_id']}; {len(leaves(row))} distinct members, preserved separately in the source bundle.",
                kind='contract_scope')
        add('provenance.closure', 'No complete operand-to-evidence/source-descriptor map',
            'Program-level evidence retained; source-file revisions/checksums require the pinned archive',
            'Missing self-contained provenance linkage is a contract/export issue; it does not mean the repository lacks pinned evidence.',
            kind='contract_scope')
        if gaps:
            output.append({'id': row['id'], 'name': row['name'], 'building_type': row['building_type'],
                'template': row['template'], 'view': row['evidence_view'], 'detail': row['detail'],
                'scope': row.get('scope', 'program'), 'source_id': row.get('source_id'),
                'source_definition_id': row.get('source_definition_id'), 'composition_id': row.get('composition_id'),
                'members': [p['id'] for p in leaves(row)] if mixed else [],
                'bindings': filled['required_bindings'], 'gaps': gaps})
        if number % 250 == 0:
            print(f'Validated review inputs {number}/{len(bundle["programs"])}', flush=True)
    return {'audit_version': 1, 'date': DATE, 'input_sha256': input_hashes,
            'validated_raw_exports': len(bundle['programs']), 'validated_defaulted_exports': len(bundle['programs']),
            'policy': list(policy.values()), 'records': output}


def comments(text):
    result = {}
    for match in COMMENT.finditer(text):
        if match[1] in result:
            raise ValueError('Duplicate user comment block: ' + match[1])
        result[match[1]] = match[2]
    if text.count('<!-- user-comments:') != 2 * len(result):
        raise ValueError('Malformed comment markers; repair before regeneration')
    return result


def add_water_allocation_gaps(audit):
    """Add absence-of-record evidence without equating absence with zero draw."""
    path = ROOT / 'data/completion-releases/v0.1.0/commercial-completion.json'
    packet = load_json(path)
    audit['input_sha256'][path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    unknown = {p['program_id']: (i, p) for i, p in enumerate(packet['missing_program_evidence'])
               if p['coverage_resolution_status'] == 'allocation_unknown'}
    records = {r['id']: r for r in audit['records']}
    for row in audit['records']:
        leaves = [records[mid] for mid in row['members']] if row['members'] else [row]
        affected = [(leaf['source_id'], *unknown[leaf['source_id']]) for leaf in leaves if leaf['source_id'] in unknown]
        if affected:
            locators = '; '.join(f'{pid}: commercial-completion.json#/missing_program_evidence/{index} '
                f'({proof["source_space_type"]}; {proof["classification"]})' for pid, index, proof in affected)
            row['gaps'].append({'category': 'water.program_allocation', 'path': 'Unresolved source program/service water allocation',
                'handling': 'No new physical allocation inferred; shared services and reporting policies do not prove local fixture placement',
                'note': locators, 'kind': 'upstream_allocation_gap', 'rule': None})


def comment_block(key, saved):
    content = saved.get(key, '**Your comments / proposed resolution:**\n\n\n**Agreed decision:**\n\n\n**Status:** Open')
    return [f'<!-- user-comments:{key}:begin -->', content, f'<!-- user-comments:{key}:end -->', '']


def pattern(category, records):
    count = len(records)
    if category.startswith('control.heating_enabled') or category.startswith('control.cooling_enabled'):
        return 'Broad across commercial programs and all dwellings; flags were not generally extracted. Known disabled states remain distinct.'
    if category.startswith('control.people_'):
        return 'All program types: these operands are not populated by the current adapter, even for programs with occupancy data.'
    if category.startswith('heat.'):
        return 'Broad adapter/source-field coverage issue. Different load types expose different fractions; missing may mean unreported or inapplicable.'
    if category.startswith('air.'):
        return 'Air-exchange semantics are absent from this DTO. Some commercial rates exist upstream; infiltration is unresolved rather than zero.'
    if category.startswith('omitted_channel.'):
        return 'Whole dwellings with a retained profile for this channel; the fixed exporter channel list does not instantiate the matching load.'
    if category.startswith('fuel.'):
        return 'Whole dwellings selecting Gas or Propane; name-based load classification treats the channel as electric.'
    if category == 'water.program_allocation':
        return ('279 distinct commercial source programs have unresolved allocations, concentrated in supermarkets, '
                'hotels, hospitals and schools, with smaller retail/warehouse/restaurant groups. Reviewed variants and '
                'mixtures inherit the source ambiguity; source no-local-draw is not complete service-allocation evidence.')
    if category == 'load.additional_lighting.value':
        return 'Additional lighting is mostly unreported across commercial space types; this is separate from ordinary lighting, which is usually known.'
    if category == 'load.gas_equipment.value' or category == 'load.gas_equipment.schedule_id':
        return 'Most commercial source programs lack a gas end-use entry; reviewed overlays supply reviewed zeros for many cases. Null alone does not prove absence.'
    if category.endswith('inlet_temperature_schedule_id'):
        return 'All exported water-demand categories: inlet temperature is never read into the current DTO and is defaulted regardless of fixture type.'
    if category.startswith('metadata.') or category == 'provenance.closure':
        return 'Export/contract representation gap; context or evidence exists in the pinned definitions rather than as a complete dedicated DTO field.'
    names = [r['name'].lower() for r in records]
    support = sum(any(t in name for t in ('attic', 'plenum', 'data center', 'basement')) for name in names)
    residential = sum(r['scope'] == 'whole_dwelling' for r in records)
    observations = []
    if residential:
        observations.append(f'{residential}/{count} affected records are whole dwellings; schedule-only execution leaves most demand magnitudes unresolved')
    if support:
        observations.append(f'{support}/{count} names identify attic, plenum, basement or data-center programs')
    return '; '.join(observations) + '. Observed pattern, not proof of physical absence.' if observations else 'Spread across the listed building/program types; no narrow pattern established by this scan.'


def record_rows(row):
    """Group paths within one object without combining distinct program records."""
    groups = defaultdict(list)
    for gap in row['gaps']:
        match = re.match(r'^(/loads/\d+|/shared_services/\d+/loads/\d+)/', gap['path'])
        key = match[1] if match else '/controls' if gap['path'].startswith('/controls/') else 'air' if gap['category'].startswith('air.') else gap['category']
        groups[key].append(gap)
    for key, gaps in groups.items():
        if key.startswith(('/loads/', '/shared_services/')) or key == '/controls':
            fields, handling = [], []
            note = ''
            for gap in gaps:
                if '/heat_fractions/' in gap['path']:
                    names = [p.rsplit('/', 1)[1] for p in gap['path'].split(', ')]
                    field = 'heat_fractions.{' + ', '.join(names) + '}'
                    action = ('leaf policy `unknown-heat-fraction`; preserve known leaf shares' if row['members']
                              else 'missing heat fractions=0; convection=residual')
                    if not note:
                        note = gap['note'].split(';', 1)[0] + '; missing heat shares'
                else:
                    field = gap['path'].rsplit('/', 1)[1]
                    action = gap['handling']
                    if row['members'] and key != '/controls':
                        action = 'leaf policy `' + str(gap['rule']) + '`, then recompose'
                fields.append(field)
                handling.append(field + ': ' + action)
                if gap['category'].startswith('load.'):
                    note = gap['note'].split('; demand ')[0].rstrip('.')
            yield key + '/{' + '; '.join(fields) + '}', '; '.join(handling), note or 'Raw operands null; see field patterns.'
        elif key == 'air':
            fields = [g['category'].removeprefix('air.') for g in gaps]
            known = [g['category'].removeprefix('air.') for g in gaps if g['kind'] == 'export_omission']
            unknown = [g['category'].removeprefix('air.') for g in gaps if g['kind'] == 'upstream_and_contract_gap']
            notes = []
            if known:
                notes.append('Known in at least one source leaf: ' + ', '.join(known))
            if unknown:
                notes.append('Null in all source leaves: ' + ', '.join(unknown))
            if not notes:
                notes.append(gaps[0]['note'])
            yield 'Absent DTO air fields: ' + ', '.join(fields), 'No program-JSON fallback', '; '.join(notes)
        else:
            for gap in gaps:
                note = gap['note']
                if key == 'water.program_allocation':
                    indices = re.findall(r'missing_program_evidence/(\d+)', note)
                    note = 'commercial-completion.json#/missing_program_evidence indices: ' + ', '.join(indices)
                if key == 'provenance.closure':
                    note = 'Pinned evidence remains in the frozen archive; see shared provenance decision.'
                yield gap['path'], gap['handling'], note


def render(audit, saved):
    rows = sorted(audit['records'], key=lambda r: (r['building_type'], r['template'], r['view'], r['detail'], r['name'], r['id']))
    categories = defaultdict(dict)
    for row in rows:
        for gap in row['gaps']:
            categories[gap['category']][row['id']] = row
    blocks = {'general'} | {f'field-{k}' for k in categories} | {r['id'] for r in rows}
    orphaned = set(saved) - blocks
    if orphaned:
        raise ValueError('Refusing to remove comment blocks for retired categories/records: ' + ', '.join(sorted(orphaned)))
    out = ['# Program JSON missing-data review', '',
        f'Audit date: {audit["date"]}. Definition release: **v0.1.1**. Program contract: **2.0.0**.', '',
        f'**{len(rows):,} individual program records require review.** All {audit["validated_raw_exports"]:,} raw and '
        f'{audit["validated_defaulted_exports"]:,} defaulted exports were generated and validated. Passing the current schema does not establish complete energy semantics.', '',
        'This is our working review document. Each program has its own entry and comment block, including source and reviewed variants and each mixture; no stock variants are merged. '
        'The universal missing people fractions mean every current program is included. Counts describe records or field occurrences, never population weights.', '',
        '## How to use this document', '',
        'Write shared decisions under the field-pattern sections, and program exceptions under the individual record. Search for an ID or use the building index. '
        'Edit between `user-comments` markers: regeneration preserves those blocks exactly and refuses to discard orphaned blocks. '
        'Keep the markers and record IDs intact. Other sections are generated evidence; make corrections through the generator or source interpretation.', '',
        'Status starts **Open**. A comment or proposed resolution is not approval to change a default. Record an agreed decision before changing scientific assumptions.', '',
        '```powershell', '.venv/Scripts/python.exe -m scripts.program_json_review --refresh',
        '.venv/Scripts/python.exe -m scripts.program_json_review --check', '```', '',
        'The ignored cache at `build/program-json-review-audit.json` is reused only when all input SHA-256 fingerprints match. '
        '`--refresh` re-exports every program. `--check` verifies the committed Markdown against the audited inputs while retaining comments.', '',
        '## Scope and interpretation', '',
        '- **Unknown:** a raw DTO physical operand is null; unknown is never implicitly zero.',
        '- **Schedule gap:** a known ruleset leaves dates or selectors uncovered, including holiday/design-day contexts.',
        '- **Export omission:** upstream information exists but has no corresponding usable DTO field or load.',
        '- **Upstream and contract gap:** source leaves are null and the DTO has no field.',
        '- **Upstream allocation gap:** source program/service water allocation remains unresolved; no local draw is not proof of complete sanitary-service coverage.',
        '- **Classification error:** source appliance fuel conflicts with the exported load category.',
        '- **Contract scope:** a representation/provenance decision is needed; it is not automatically a missing measurement.', '',
        'For mixed programs, the raw aggregate can be unknown even when some leaves are known. Defaulted exports resolve source leaves and rebuild their weighted demands. '
        'Never replace an unknown aggregate by zero and erase known contributions. Braces in paths are shorthand for each named child field, not literal JSON Pointers. '
        'Every child listed in a grouped raw control/load path is null; grouping is only within a record, never between records.', '',
        'Ventilation terms may be alternative/additive source inputs. A missing per-person or ACH term alone does not prove that total ventilation is unknown. '
        'Infiltration needs a stated basis; ACH50 cannot be used as natural infiltration. '
        'No local water-load entry does not prove no water demand: shared services, unresolved allocations and applicability need separate interpretation.', '',
        'Consumer geometry/counts, calendar/holiday bindings and service hosts are listed for context, not counted as missing source measurements. '
        'Envelope and HVAC models remain separate contracts. Residential annual profiles retain their recorded 2007 year and schedule-only/proxy-weather limitations.', '',
        '## General comments and decisions', '']
    out += comment_block('general', saved)
    out += ['## Existing experimental defaults to review', '',
            'These describe current behavior under `atlas-program-defaults-1.0.0`; this ledger does not approve new assumptions.', '',
            '| Rule | Current assumption | Scope |', '| --- | --- | --- |']
    for rule in audit['policy']:
        out.append(f"| `{rule['id']}` | {cell(short(rule['value']))} {cell(rule.get('unit', ''))} | {cell(rule['applies_to'])} |")
    out += ['', '**Highest-impact magnitude gap:** all 41 whole-dwelling records have unknown non-occupancy magnitudes. '
            'Current zero defaults therefore remove lighting, appliance and water demands despite available schedules. '
            'Do not confuse reviewed source absences with generic zero replacements.', '', '## Field patterns and shared comments', '',
            'Affected-program counts count each ID once per category; one record can contain several occurrences. Building counts below are observed associations, not inferred causes.', '']
    for category, affected in sorted(categories.items()):
        records = list(affected.values())
        counts = Counter(r['building_type'] for r in records)
        kinds = Counter(kind for r in records for kind in {
            g['kind'] for g in r['gaps'] if g['category'] == category})
        examples = '; '.join(f"{r['name']} / {r['template']} / {r['view']}" for r in records[:3])
        out += [f'### {category}', '', f'**Affected program records:** {len(records):,}.', '',
                '**Pattern:** ' + pattern(category, records), '',
                '**Gap classes (program counts):** ' + '; '.join(f'{k}: {v}' for k, v in sorted(kinds.items())) + '.', '',
                '**Building types:** ' + '; '.join(f'{k}: {v}' for k, v in sorted(counts.items())) + '.', '',
                '**Examples:** ' + cell(examples) + '.', '']
        upstream_missing = [r for r in records if any(g['category'] == category and
                            g['kind'] == 'upstream_and_contract_gap' for g in r['gaps'])]
        if upstream_missing:
            missing_counts = Counter(r['building_type'] for r in upstream_missing)
            out += ['**Upstream-null subset:** ' + '; '.join(f'{k}: {v}' for k, v in sorted(missing_counts.items())) +
                    '. Null in all constituent leaves; other affected records can retain known terms.', '']
        out += comment_block('field-' + category, saved)
    out += ['## Building index', '', '| Building type | Affected records |', '| --- | ---: |']
    counts = Counter(r['building_type'] for r in rows)
    for building, count in sorted(counts.items()):
        out.append(f'| [{building}](#building-{building.lower()}) | {count} |')
    out += ['', '## Individual program records', '']
    previous = None
    for row in rows:
        if previous != row['building_type']:
            previous = row['building_type']
            out += [f'<a id="building-{previous.lower()}"></a>', '', f'### {previous}', '']
        out += [f'<a id="{row["id"]}"></a>', '', f'#### {cell(row["name"])} — {cell(row["template"])} — {row["view"]} / {row["detail"]}', '',
                f'**Record ID:** `{row["id"]}`. **Scope:** `{row["scope"]}`. '
                f'**Canonical source ID:** `{row["source_id"]}`.', '']
        if row.get('source_definition_id'):
            out += [f'**Source definition:** [{row["source_definition_id"]}](#{row["source_definition_id"]}).', '']
        if row['members']:
            out += [f'**Composition:** `{row["composition_id"]}`. **Distinct member records:** ' +
                    ', '.join(f'[{p}](#{p})' for p in row['members']) + '.', '']
        out += ['**Consumer bindings:** ' + ', '.join(f'`{v}`' for v in row['bindings']) + '.', '',
                '| Missing/omitted field or channel | Current handling | Interpretation / locator |', '| --- | --- | --- |']
        for path, handling, note in record_rows(row):
            out.append(f'| `{cell(path)}` | {cell(handling)} | {cell(note)} |')
        out += ['', '**Comments for this record:**', '']
        out += comment_block(row['id'], saved)
    out += ['## Pinned audit inputs', '',
            'Original values, units, extraction dates, transformations and interpretation evidence remain in the frozen sources. '
            'This ledger records unresolved operands and export gaps; it introduces no new physical values.', '',
            '| Input | SHA-256 |', '| --- | --- |']
    for name, digest in sorted(audit['input_sha256'].items()):
        out.append(f'| [{name}](../../{name}) | `{digest}` |')
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    inputs = fingerprints()
    audit = load_json(CACHE) if CACHE.exists() and not args.refresh else None
    if not audit or audit.get('input_sha256') != inputs or audit.get('audit_version') != 1:
        audit = collect(inputs)
        dump_json(CACHE, audit)
    add_water_allocation_gaps(audit)
    existing = DOCUMENT.read_text(encoding='utf-8') if DOCUMENT.exists() else ''
    result = render(audit, comments(existing))
    if args.check:
        if result != existing:
            raise SystemExit('Review document differs; regenerate while preserving user comments')
        print(f'Review ledger verified: {len(audit["records"])} individual records; comments retained')
    else:
        DOCUMENT.parent.mkdir(parents=True, exist_ok=True)
        DOCUMENT.write_text(result, encoding='utf-8', newline='\n')
        print(f'Wrote {DOCUMENT}: {len(audit["records"])} records; {len(result.encode())} bytes')


if __name__ == '__main__':
    main()
