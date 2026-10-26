"""Build the program definitions for the construction-only folders (ADR 0039).

python -m scripts.construction_only_programs            # write data/program-inputs/construction-only-v1.json
python -m scripts.construction_only_programs --check    # rebuild and compare

51 template x building-type folders had construction sets but no programs. This
generator runs the existing definition code for those types only, offline, from
pinned sources:
- legacy program, schedule, system and mapping records come from scripts.build's
  Builder, reading the new types' geometry and HVAC files
  (sources/construction-only-programs-lock.json) and the templates' space-type rows.
  The generic Office has no geometry file, so its programs come from the Office
  space-type rows directly;
- definition programs and HVAC systems come from scripts.program_definitions and
  scripts.hvac_definitions, limited to the new types. No completion draw or
  resolution applies to them, so their values are source values only;
- mixes come from scripts.program_composition.compose. Every new type gets a general
  mix and no department mixes. Represented areas come from each type's geometry;
  the generic Office borrows the areas of ASHRAELargeOfficeDetailed.osm, whose spaces
  carry the same Office space types. A blank "Part of Total Floor Area" flag takes
  the OS:Space default of its OSM version, "Yes", pinned in
  sources/openstudio-area-default-lock.json.
The output is a committed definition input that the release 1.2.0 overlay reads.
"""
import argparse
import copy
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from scripts.common import ROOT, load_atlas, load_json
from scripts.definition_contract import BuildContext, DefinitionBundle, evidence, load_context, stable_id
from scripts.fetch import verify_file

OUTPUT = ROOT/'data/program-inputs/construction-only-v1.json'
LOCK = ROOT/'sources/construction-only-programs-lock.json'
DEFAULTS = ROOT/'sources/openstudio-area-default-lock.json'
DEFINITIONS = ROOT/'data/definition-releases/v0.1.1'
NINETY_ONE = ('90.1-2007', '90.1-2013', '90.1-2019')
DOE_REF = ('DOE Ref Pre-1980', 'DOE Ref 1980-2004')
GEOMETRY = 'data/geometry/ASHRAE{}.osm'
# building type: (geometry stem, HVAC file stem or None, templates)
TYPES = {
    'College': ('College', 'College', NINETY_ONE + DOE_REF),
    'Courthouse': ('Courthouse', 'Courthouse', NINETY_ONE + DOE_REF),
    'Laboratory': ('Laboratory', 'Laboratory', NINETY_ONE),
    'LargeDataCenterHighITE': ('LargeDataCenterHighITE', 'LargeDataCenter', NINETY_ONE),
    'LargeDataCenterLowITE': ('LargeDataCenterLowITE', 'LargeDataCenter', NINETY_ONE),
    'SmallDataCenterHighITE': ('SmallDataCenterHighITE', 'SmallDataCenter', NINETY_ONE),
    'SmallDataCenterLowITE': ('SmallDataCenterLowITE', 'SmallDataCenter', NINETY_ONE),
    'LargeOfficeDetailed': ('LargeOfficeDetailed', 'LargeOfficeDetailed', NINETY_ONE + DOE_REF),
    'MediumOfficeDetailed': ('MediumOfficeDetailed', 'MediumOfficeDetailed', NINETY_ONE + DOE_REF),
    'SmallOfficeDetailed': ('SmallOfficeDetailed', 'SmallOfficeDetailed', NINETY_ONE + DOE_REF),
    'TallBuilding': ('TallBuildingbase', None, NINETY_ONE),
    'SuperTallBuilding': ('SuperTallBuildingbase', None, NINETY_ONE),
    'Office': (None, None, NINETY_ONE + DOE_REF),
}
OFFICE_AREAS = 'LargeOfficeDetailed'  # the generic Office borrows these represented areas


def wanted():
    return {(template, building_type) for building_type, (_, _, templates) in TYPES.items() for template in templates}


@dataclass
class Context(BuildContext):
    """The definition build context, limited to the construction-only types."""

    def includes(self, row):
        return (row.get('template'), row.get('building_type')) in wanted()


SPREADSHEET_ERRORS = ('#N/A',)


def builder(raw_root):
    """scripts.build's Builder, reading spreadsheet errors in space-type metrics as source nulls."""
    from scripts import build

    class Builder(build.Builder):
        def program(self, t, building, source_building, source_space, rows):
            clean = [{k: (None if k in METRIC_FIELDS and v in SPREADSHEET_ERRORS else v) for k, v in r.items()} for r in rows]
            rid = super().program(t, building, source_building, source_space, clean)
            index, raw = build.unique_match(rows, source_building, source_space)
            record = next(r for r in self.data['programs'] if r['id'] == rid)
            if record['source_attributes'] != raw:
                record['source_attributes'] = raw
                provenance = next(p for p in self.data['provenance'] if p['id'] == record['provenance_id'])
                for field, (original, _) in build.METRICS.items():
                    if raw.get(original) in SPREADSHEET_ERRORS:
                        provenance['fields'][field].update(original_value=raw[original], status='unresolved',
                                                           transformation='source spreadsheet error; stays unknown')
                provenance['fields']['source_attributes']['original_value'] = raw
            return rid

    METRIC_FIELDS = {original for original, _ in build.METRICS.values()}
    return Builder(raw_root)


def legacy_records(raw_root):
    """Legacy atlas records for the new types, from scripts.build's Builder."""
    b = builder(raw_root)
    lock = load_json(LOCK)
    source = {s['source_id']: s for s in lock['sources']}
    for entry in lock['files']:
        verify_file(entry, Path(raw_root))
        meta = source[entry['source_id']]
        b.data['source_files'].append({'id': stable_id_legacy('sourcefile', entry['source_id'], entry['path']), **entry,
                                       'project': meta['project'], 'repository': meta['repository'], 'version': meta['version'],
                                       'license_path': meta['license_path'], 'retrieval_date': lock['retrieval_date']})
    templates = {t['template']: t for t in b.selection['templates']}
    for building_type, (geometry, hvac, names) in TYPES.items():
        for name in names:
            t = templates[name]
            if geometry is None:
                rows = b.read('openstudio-standards', t['space_types'])['space_types']
                for row in rows:
                    if row['building_type'] == building_type:
                        b.program(t, building_type, building_type, row['space_type'], rows)
                continue
            b.model(t, {'building_type': building_type, 'geometry': GEOMETRY.format(geometry),
                        'hvac': f'data/geometry/ASHRAE{hvac}.json' if hvac else None})
    b.data['coverage_gaps'] = b.warnings
    return b.data


def stable_id_legacy(*parts):
    from scripts.common import stable_id as legacy
    return legacy(*parts)


def area_defaults(raw_root):
    """{OSM version: evidence}, the pinned OS:Space default of Part of Total Floor Area."""
    lock = load_json(DEFAULTS)
    out = {}
    for entry in lock['files']:
        verify_file(entry, Path(raw_root))
        if entry['path'] == 'OpenStudio.idd':
            text = (Path(raw_root)/entry['source_id']/entry['path']).read_text(encoding='utf-8', errors='replace').splitlines()
            line = next(i for i, l in enumerate(text) if 'Part of Total Floor Area' in l and l.strip().startswith('A'))
            default = next(l.split('\\default', 1)[1].strip() for l in text[line:line+8] if '\\default' in l)
            out[entry['openstudio_version']] = {'default': default, 'locator': f'{entry["url"]}#L{line + 1}', 'sha256': entry['sha256']}
    return out


def areas(context, raw_root, records, defaults):
    """extract_areas for the new types: represented counted area per legacy program."""
    from scripts.fetch import fetch_file
    from scripts.semantics import osm_objects, spaces
    from scripts.water_reporting import floor_areas
    files = {r['path']: r for r in records['source_files'] if r['source_id'] == 'openstudio-standards'}
    by_key = defaultdict(list)
    for p in records['programs']:
        by_key[(p['building_type'], p['template'])].append(p)
    result, used = {}, set()
    for building_type, (geometry, _, names) in TYPES.items():
        stem = geometry or OFFICE_AREAS
        path = GEOMETRY.format(stem)
        text = fetch_file(files[path], Path(raw_root)).read_text(encoding='utf-8-sig')
        version = next(o['fields']['Version Identifier'] for o in osm_objects(text) if o['kind'] == 'OS:Version')
        ss, area = spaces(text), floor_areas(text)
        if any(s['part_of_total_floor_area'] == '' for s in ss):
            if defaults.get(version, {}).get('default') != 'Yes':
                raise ValueError(f'No pinned Part of Total Floor Area default for OSM version {version} ({path})')
            used.add(version)
            for s in ss:
                if s['part_of_total_floor_area'] == '':
                    s['part_of_total_floor_area'] = 'Yes'
        for name in names:
            lookup = {(p['source_building_type'], p['source_space_type']): p for p in by_key[(building_type, name)]}
            grouped = defaultdict(list)
            for s in ss:
                p = lookup.get((s['source_building_type'], s['source_space_type']))
                if p:
                    grouped[p['id']].append(s)
            rows = []
            for p in by_key[(building_type, name)]:
                matches = grouped[p['id']]
                counted = [s for s in matches if s['part_of_total_floor_area'] == 'Yes']
                rows.append({'program_id': p['id'], 'source_space_type': p['source_space_type'],
                             'source_building_type': p['source_building_type'],
                             'represented_area_m2': math.fsum(area[s['handle']]*s['multiplier'] for s in counted),
                             'area_status': 'derived' if counted else ('non_counted' if matches else 'no_geometry'),
                             'source_file_id': files[path]['id'], 'geometry_path': path,
                             'space_handles': [s['handle'] for s in counted],
                             'uncounted_space_handles': [s['handle'] for s in matches if s not in counted]})
            result[(building_type, name)] = rows
    return result, sorted(used)


def recipe_groups(family, names):
    """Every new type: a general mix over its counted programs, no departments (ADR 0039)."""
    available = sorted(n for n in names if not any(t in n.lower() for t in ('basement', 'attic')))
    return {'departments': {}, 'general': available if len(available) > 1 else []}


def build(raw_root=ROOT/'data/raw'):
    from scripts import program_composition
    from scripts.hvac_definitions import build_hvac
    from scripts.program_definitions import build_programs
    records = legacy_records(raw_root)
    base = load_context(scope='full')
    legacy = load_atlas(ROOT/base.policy['dependencies']['atlas'])
    atlas = copy.deepcopy(legacy)
    for table in ('programs', 'schedules', 'systems', 'mappings', 'provenance', 'source_files'):
        known = {r['id'] for r in atlas[table]}
        atlas[table] += [r for r in records[table] if r['id'] not in known]
    context = Context(base.root, base.scope, atlas, base.policy, base.sources, base.extraction_date, base.dependencies)
    bundle = DefinitionBundle()
    programs = build_programs(context)
    bundle.merge(programs).merge(build_hvac(context))
    defaults = area_defaults(raw_root)
    table, used = areas(context, raw_root, records, defaults)
    saved = (program_composition.extract_areas, program_composition.recipe_groups)
    program_composition.extract_areas = lambda ctx: table
    program_composition.recipe_groups = recipe_groups
    try:
        bundle.merge(program_composition.compose(context, bundle))
    finally:
        program_composition.extract_areas, program_composition.recipe_groups = saved
    # Schedule provenance, as scripts.definitions.build retains it.
    for source in atlas['provenance']:
        if source['id'] in {r.get('provenance_id') for r in bundle['schedules']}:
            bundle['provenance'].append({'id': source['id'], 'source_file_id': source['source_file_id'],
                'locator': source['locator'], 'original_value': source['fields'], 'original_unit': 'mixed source fields',
                'transformation': 'retained schedule provenance; field-specific conversions preserved',
                'extraction_date': source['extraction_date'], 'interpretation': source['notes']})
    existing = {table: {r['id'] for r in load_json(DEFINITIONS/f'{table}.json')}
                for table in ('schedules', 'components', 'provenance', 'source_files')}
    sources = {r['id']: r for r in atlas['source_files']}
    cited = set(json.dumps(bundle).split('"')) & sources.keys()
    out = {
        'schema_version': '1.0.0', 'kind': 'construction_only_program_definitions',
        'adr': 'docs/adr/0039-construction-only-programs.md', 'generated_by': 'python -m scripts.construction_only_programs',
        'definition_release': 'data/definition-releases/v0.1.1',
        'input_sha256': {p: sha(ROOT/p) for p in ('sources/construction-only-programs-lock.json',
                                                   'sources/openstudio-area-default-lock.json', 'sources/lock.json')},
        'area_defaults': {v: defaults[v] for v in used},
        'programs': bundle['programs'], 'compositions': bundle['compositions'], 'hvac_systems': bundle['hvac_systems'],
        'schedules': [r for r in bundle['schedules'] if r['id'] not in existing['schedules']],
        'components': [r for r in bundle['components'] if r['id'] not in existing['components']],
        'provenance': [r for r in bundle['provenance'] if r['id'] not in existing['provenance']],
        'source_files': [r for r in (sources[i] for i in sorted(cited)) if r['id'] not in existing['source_files']],
        'coverage_gaps': sorted(records['coverage_gaps'], key=json.dumps),
    }
    return out


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--raw-root', type=Path, default=ROOT/'data/raw')
    args = parser.parse_args()
    data = encode(build(args.raw_root))
    if args.check:
        if OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.relative_to(ROOT)} does not reproduce; run python -m scripts.construction_only_programs')
        print('Construction-only program definitions reproduce')
        return
    OUTPUT.write_bytes(data)
    document = json.loads(data)
    print(f"{len(document['programs'])} programs, {len(document['compositions'])} compositions, "
          f"{len(document['hvac_systems'])} HVAC systems, {len(document['coverage_gaps'])} unmapped spaces")


if __name__ == '__main__':
    main()
