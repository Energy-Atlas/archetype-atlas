"""Recover pinned reference geometry/exposure; no catalogue/site or systems build.

python -m scripts.recover_construction_geometry [--check]
Output is construction derivation evidence, not a final natural-ACH contract.
"""
import argparse
import hashlib
import math
import re
import subprocess
import tarfile
from pathlib import Path

from scripts.common import ROOT, load_json, dump_json
from scripts.recover_program_inputs import SOURCE, RUNTIME, REVISION

DATE = '2026-10-13'
WORK = ROOT / 'build/geometry-recovery'
OUTPUT = ROOT / 'data/construction-inputs/geometry-v1.json'
CLIMATE_OUTPUT = ROOT / 'data/construction-inputs/climate-factor-candidates-v1.json'
COMMERCIAL_REV = 'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907'
FT = .3048
FT2 = .09290304
FT3 = .028316846592


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_derived(value):
    """Stabilize computed SDK geometry only; never round literal source tables."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('Nonfinite derived geometry')
        return float(format(value, '.9g'))
    if isinstance(value, dict):
        return {k: canonical_derived(v) for k,v in value.items()}
    if isinstance(value, list):
        return [canonical_derived(v) for v in value]
    return value


def normalize_residential(raw, evidence_id):
    g = raw['geometry']
    if not isinstance(g.get('a_ext'), (float, int)) or not 0 <= g['a_ext'] <= 1:
        raise ValueError('Invalid source exterior exposure')
    specs = {
        'cfa_m2': ('cfa_ft2', 'ft2', 'm2', FT2),
        'conditioned_volume_m3': ('volume_ft3', 'ft3', 'm3', FT3),
        'infiltration_volume_m3': ('infiltration_volume_ft3', 'ft3', 'm3', FT3),
        'infiltration_height_m': ('infiltration_height_ft', 'ft', 'm', FT),
        'unit_height_above_grade_m': ('unit_height_above_grade_ft', 'ft', 'm', FT),
        'compartment_total_area_m2': ('compartment_total_area_ft2', 'ft2', 'm2', FT2),
        'compartment_exterior_area_m2': ('compartment_exterior_area_ft2', 'ft2', 'm2', FT2),
        'a_ext': ('a_ext', '1', '1', 1),
        'ach50_per_s': ('ach50', '1/h', '1/s', 1/3600),
        'pressure_Pa': ('pressure_pa', 'Pa', 'Pa', 1),
        'annual_ach_per_unit_wsf_per_s': ('annual_ach_per_unit_wsf', '1/h', '1/s', 1/3600),
    }
    fields = {}
    for out, (key, native, unit, factor) in specs.items():
        value = g.get(key)
        if value is not None and (not math.isfinite(value) or (value < 0 and key != 'unit_height_above_grade_ft')):
            raise ValueError('Invalid geometry operand: ' + key)
        fields[out] = {'value': None if value is None else value * factor, 'unit': unit,
            'evidence_id': evidence_id, 'original_field': key, 'original_value': value,
            'original_unit': native, 'transformation': f'value * {factor:.15g}'}
    ach50 = g.get('ach50')
    fields['exterior_ach50_per_s'] = {'value': None if ach50 is None else ach50 * g['a_ext'] / 3600,
        'unit': '1/s', 'evidence_id': evidence_id,
        'original_value': {'ach50': ach50, 'a_ext': g['a_ext']}, 'original_unit': '1/h and 1',
        'transformation': 'source normalized ACH50 * source a_ext / 3600'}
    return {'id': raw['record_id'], 'fields': fields, 'evidence_id': evidence_id,
        'source_context': {k: v for k, v in g.items() if k not in {s[0] for s in specs.values()}},
        'neighbors': [{'azimuth_rad': n['azimuth'] * math.pi / 180,
            'distance_m': n['distance_ft'] * FT,
            'height_m': None if n['height_ft'] is None else n['height_ft'] * FT,
            'original_value': n, 'original_unit': 'degree and ft', 'evidence_id': evidence_id,
            'transformation': 'azimuth*pi/180; lengths*0.3048'} for n in raw.get('neighbors', [])],
        'warnings': raw.get('warnings', []),
        'status': 'reference_geometry_recovered; climate_conversion_policy_pending'}


def package_references(package, cases):
    source = package['source_set']
    keys = [k for k in source if k not in {'id', 'source_family', 'source_building_type'}]
    original = dict(source, building_type=source.get('source_building_type', source['building_type']))
    return sorted(c['id'] for c in cases if c['template'] == package['template'] and any(
        all(s.get(k) == original.get(k) for k in keys) for s in c['selected_sets']))


def validate(packet):
    ids = {r['id'] for r in packet['commercial']}
    if len(ids) != len(packet['commercial']):
        raise ValueError('Duplicate commercial reference')
    for m in packet['package_mappings']:
        if not set(m['reference_ids']) <= ids:
            raise ValueError('Orphan commercial reference mapping')
        if not m['reference_ids'] and (m.get('status') != 'source_scope_not_instantiated' or
                not m.get('evidence') or not m.get('candidate_reference_ids')):
            raise ValueError('Unresolved package reference: '+m['package_id'])
        if not set(m.get('candidate_reference_ids', [])) <= ids:
            raise ValueError('Orphan candidate reference mapping')
    for r in packet['residential']:
        required = ['cfa_m2', 'infiltration_volume_m3', 'infiltration_height_m', 'a_ext', 'ach50_per_s', 'pressure_Pa']
        if any(r['fields'].get(k, {}).get('value') is None for k in required):
            raise ValueError('Missing geometry for ' + r['id'])
        if r['evidence_id'] not in packet['evidence']:
            raise ValueError('Orphan residential geometry evidence')
        if any(r['fields'][k]['value'] <= 0 for k in required if k != 'a_ext'):
            raise ValueError('Invalid pressure-boundary geometry')
    for c in packet['commercial']:
        if not c['spaces'] or any(s['volume_m3'] <= 0 or s['multiplier'] <= 0 for s in c['spaces']):
            raise ValueError('Invalid commercial source space geometry')


def climate_candidates(source, receipts):
    map_path = 'lib/openstudio-standards/weather/information.rb'
    matches = re.findall(r"ASHRAE 169-(2006|2013)-([0-8][ABC])[^=]*=> '([^']+\.epw)'", (source/map_path).read_text())
    inputs = [{'edition': ed, 'climate_zone': cz, 'path': str(source/'data/weather'/name),
               'sha256': receipts['standards/data/weather/'+name]['sha256']} for ed,cz,name in matches]
    dump_json(WORK/'climate-inputs.json', inputs)
    subprocess.run([str(RUNTIME), str(ROOT/'scripts/recover_climate_factor_candidates.rb'), str(SOURCE),
                    str(WORK/'climate-inputs.json'), str(WORK/'climate-results.json')], check=True, cwd=ROOT, timeout=90)
    native = load_json(WORK/'climate-results.json')
    weather = {i['sha256']: i for i in inputs}
    for row in native:
        proof = weather[row['weather_file_sha256']]
        row['evidence'] = {'source_map_locator': map_path+'#climate_zone_weather_file_map/'+row['source_map_edition']+'/'+row['climate_zone'],
            'source_map_sha256': receipts['standards/'+map_path]['sha256'],
            'weather_source_locator': Path(proof['path']).relative_to(source).as_posix(),
            'weather_source_sha256': proof['sha256'], 'source_revision': COMMERCIAL_REV,
            'wsf_helper_locator': 'resources/hpxml-measures/HPXMLtoOpenStudio/resources/weather.rb#calc_ashrae_622_wsf',
            'wsf_helper_revision': REVISION,
            'wsf_helper_sha256': receipts['resstock/resources/hpxml-measures/HPXMLtoOpenStudio/resources/weather.rb']['sha256'],
            'wsf_table_sha256': receipts['resstock/resources/hpxml-measures/HPXMLtoOpenStudio/resources/data/ashrae622_wsf.csv']['sha256'],
            'extraction_date': DATE, 'original_value': {k: row[k] for k in ('wsf','hours','mean_absolute_delta_T_at_22C_K','mean_wind_speed_m_s','mean_weather_wind_squared_m2_s2')},
            'original_unit': 'WSF dimensionless; temperature K; weather-file wind m/s and m2/s2',
            'transformation': 'Pinned station lookup or WSF calculation; arithmetic means of abs(22C-db), weather wind and squared weather wind. No zone-height wind conversion.',
            'interpretation_note': 'Unadopted reference forcing candidates. Weather filenames exist only as provenance; no location applicability axis. These moments are not commercial ACH factors.'}
    result = {'schema_version': '1.0.0', 'status': 'proposal_only', 'extraction_date': DATE, 'candidates': native,
        'input_sha256': {'scripts/recover_climate_factor_candidates.rb': sha(ROOT/'scripts/recover_climate_factor_candidates.rb')},
        'boundary': 'Candidate climate forcing/WSF evidence only; no construction scalar ACH generated or policy adopted.'}
    return result


def prepare_sources():
    WORK.mkdir(parents=True, exist_ok=True)
    marker = load_json(SOURCE.parent / '.atlas-extraction.json')
    rs_archive = ROOT / 'build/runtime/rs.tar.gz'
    if sha(rs_archive) != marker['archive_sha256']:
        raise ValueError('Modified residential archive')
    # Verify all already-extracted residential Ruby/option dependencies.
    receipts = {}
    for p in SOURCE.rglob('*'):
        if p.is_file() and p.suffix in {'.rb', '.tsv', '.csv'}:
            name = p.relative_to(SOURCE).as_posix()
            if sha(p) != marker['files'].get(SOURCE.name + '/' + name):
                raise ValueError('Modified residential dependency: ' + name)
            receipts['resstock/' + name] = {'sha256': sha(p), 'source_revision': REVISION}
    with tarfile.open(rs_archive) as tar:
        for name, output in [('resources/buildstock.rb', 'register-value.rb'),
                             ('measures/ResStockArgumentsPostHPXML/measure.rb', 'post-hpxml.rb')]:
            raw = tar.extractfile(SOURCE.name + '/' + name).read()
            receipts['resstock/' + name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'source_revision': REVISION}
            if output == 'register-value.rb':
                start = raw.index(b'def register_value(')
                raw = raw[start:raw.index(b'\nend', start) + 4]
            (WORK / output).write_bytes(raw)
    runtime_base = ROOT / 'build/runtime/openstudio-windows'
    runtime = load_json(runtime_base / '.atlas-extraction.json')
    if sha(RUNTIME) != runtime['files'][RUNTIME.relative_to(runtime_base).as_posix()]:
        raise ValueError('Modified runtime executable')
    entry = next(e for e in load_json(ROOT / 'sources/commercial-runtime-lock.json')['archives'] if e['name'] == 'standards-controls')
    archive = ROOT / 'build/commercial-runtime/standards-controls.tar.gz'
    if sha(archive) != entry['sha256']:
        raise ValueError('Modified commercial archive')
    target = WORK / 'standards'
    target.mkdir(exist_ok=True)
    with tarfile.open(archive) as tar:
        for m in tar.getmembers():
            if not m.isfile() or not any(m.name.startswith(entry['root'] + '/' + d) for d in ('lib/', 'data/')):
                continue
            relative = m.name[len(entry['root']) + 1:]
            raw = tar.extractfile(m).read()
            p = target / m.name
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists() and p.read_bytes() != raw:
                raise ValueError('Modified commercial dependency: ' + relative)
            if not p.exists():
                p.write_bytes(raw)
            receipts['standards/' + relative] = {'sha256': hashlib.sha256(raw).hexdigest(), 'source_revision': COMMERCIAL_REV}
    return target / entry['root'], receipts, {'residential_archive_sha256': marker['archive_sha256'],
        'commercial_archive_sha256': entry['sha256'], 'runtime_executable_sha256': sha(RUNTIME)}


def recover():
    commercial_source, receipts, runtime = prepare_sources()
    rows = load_json(ROOT / 'data/releases/v0.2.0/residential_archetypes.json')
    options = {r['id']: r for r in load_json(ROOT / 'data/releases/v0.2.0/residential_options.json')}
    inputs = [{'record_id': r['id'], 'arguments': {k: v for oid in r['option_ids'] for k,v in options[oid]['arguments'].items()}} for r in rows]
    dump_json(WORK / 'inputs.json', inputs)
    subprocess.run([str(RUNTIME), str(ROOT / 'scripts/recover_construction_geometry.rb'), str(SOURCE),
        str(WORK / 'inputs.json'), str(WORK / 'residential.json'), str(WORK / 'register-value.rb'),
        str(WORK / 'post-hpxml.rb')], cwd=ROOT, check=True, timeout=120)
    packages = [r for r in load_json(ROOT / 'data/definition-releases/v0.1.1/constructions.json') if r.get('representation') == 'package']
    templates = {p['template'] for p in packages}
    families = {p['building_type'] for p in packages} - {'Any', 'Office'}
    cases = set()
    for p in commercial_source.rglob('*.prototype_inputs.json'):
        for r in load_json(p).get('prototype_inputs', []):
            if r.get('template') in templates and r.get('building_type') in families and r.get('geometry_osm'):
                cases.add((r['template'], r['building_type']))
    # Medium Office pilot first, then the remaining source cases.
    ordered = sorted(cases, key=lambda c: (c != ('90.1-2019', 'MediumOffice'), c))
    dump_json(WORK / 'commercial-inputs.json', [{'template': t, 'building_type': b} for t,b in ordered])
    subprocess.run([str(RUNTIME), str(ROOT / 'scripts/recover_commercial_geometry.rb'), str(commercial_source),
        str(WORK / 'commercial-inputs.json'), str(WORK / 'commercial.json')], cwd=ROOT, check=True, timeout=420)
    residential_raw = load_json(WORK / 'residential.json')
    commercial = load_json(WORK / 'commercial.json')['results']
    evidence = {}
    residential = []
    for r in residential_raw['results']:
        r['geometry'] = canonical_derived(r['geometry'])
        eid = 'residential/' + r['record_id']
        relevant = ['measures/ResStockArguments/measure.rb', 'resources/hpxml-measures/BuildResidentialHPXML/measure.rb',
            'measures/ResStockArgumentsPostHPXML/measure.rb', 'resources/hpxml-measures/HPXMLtoOpenStudio/resources/defaults.rb',
            'resources/hpxml-measures/HPXMLtoOpenStudio/resources/airflow.rb']
        evidence[eid] = {'source_project': 'ResStock', 'source_revision': REVISION, 'extraction_date': DATE,
            'source_locators': ['measures/ResStockArguments/measure.rb#run; CFA/attached-walls/unit-type/floor-ceiling rules',
                'resources/hpxml-measures/BuildResidentialHPXML/measure.rb#create_geometry_envelope; set_building_construction; set_air_infiltration_measurements',
                'measures/ResStockArgumentsPostHPXML/measure.rb#379-388',
                'resources/hpxml-measures/HPXMLtoOpenStudio/resources/defaults.rb#apply_infiltration; get_infiltration_height_and_volume; get_compartmentalization_boundary_areas',
                'resources/hpxml-measures/HPXMLtoOpenStudio/resources/airflow.rb#get_infiltration_SLA_from_ACH50; get_infiltration_ACH_from_SLA'],
            'source_file_sha256': {p: receipts['resstock/' + p]['sha256'] for p in relevant},
            'original_value': r['geometry'], 'original_unit': 'native source fields; explicit units on each normalized field',
            'transformation': 'Execute geometry and leakage source methods only; report derived runtime geometry at 9 significant digits to remove SDK accumulation noise; SI fields retain those native-unit operands. WSF=1 coefficient is a candidate sensitivity, not released natural ACH.',
            'interpretation_note': 'Whole pressure boundary is retained, including foundation adjacency needed for leakage reference; no ground heat-transfer model or system export is built.'}
        residential.append(normalize_residential(r, eid))
    mappings = [{'package_id': p['id'], 'source_building_type': p['building_type'], 'space_scope': p.get('space_type'),
        'template': p['template'], 'reference_ids': package_references(p, commercial)} for p in packages]
    for mapping in mappings:
        mapping['status'] = 'source_lookup_reference_recovered' if mapping['reference_ids'] else 'unresolved'
        if mapping['reference_ids']:
            continue
        candidates = [c for c in commercial if c['template'] == mapping['template'] and c['building_type'] == mapping['source_building_type']]
        if candidates and mapping['space_scope'] and all(mapping['space_scope'] not in {s['standards_space_type'] for s in c['spaces']} for c in candidates):
            mapping.update(status='source_scope_not_instantiated', candidate_reference_ids=[c['id'] for c in candidates],
                evidence={'source_locator': 'data/definition-releases/v0.1.1/constructions.json#id='+mapping['package_id'],
                    'source_file_sha256': sha(ROOT/'data/definition-releases/v0.1.1/constructions.json'),
                    'reference_source_geometry': [{ 'source_locator': c['geometry_file'],
                        'sha256': receipts['standards/'+c['geometry_file']]['sha256'],
                        'observed_space_types': sorted({s['standards_space_type'] or '<unset>' for s in c['spaces']})} for c in candidates],
                    'extraction_date': DATE, 'original_value': mapping['space_scope'], 'original_unit': 'source space selector',
                    'transformation': 'Exact scope census, no replacement geometry',
                    'interpretation_note': 'Source set exists but its exact space type is absent from the pinned reference model. Candidate whole-building reference retained for discussion; not assigned as room geometry or ready ACH.'})
    for c in commercial:
        c['spaces'] = canonical_derived(c['spaces'])
        path = c['geometry_file']
        c['geometry_file_sha256'] = receipts['standards/' + path]['sha256']
        file, line = c.pop('geometry_tweak_source')
        rel = Path(file).relative_to(commercial_source).as_posix()
        c['geometry_tweak_source'] = {'source_locator': rel + '#line=' + str(line),
            'sha256': receipts['standards/' + rel]['sha256']}
        c['reference_totals'] = {'floor_area_m2': sum(s['floor_area_m2']*s['multiplier'] for s in c['spaces'] if s['part_of_total_floor_area']),
            'all_space_volume_m3': sum(s['volume_m3']*s['multiplier'] for s in c['spaces']),
            'height_span_m': max(s['z_max_m'] for s in c['spaces']) - min(s['z_min_m'] for s in c['spaces'])}
        c['evidence'] = {'source_project': 'OpenStudio Standards', 'source_revision': COMMERCIAL_REV, 'extraction_date': DATE,
            'source_locator': path+'#OS:Space/OS:Surface/OS:ThermalZone', 'source_file_sha256': c['geometry_file_sha256'],
            'original_unit': 'm2, m3, m and dimensionless multipliers',
            'transformation': 'Pinned SDK Space.floorArea/volume and transformed surface vertex heights; report derived geometry at 9 significant digits; apply source zone multiplier once for summary totals. Literal source construction-set parameters remain unchanged.',
            'interpretation_note': 'All-space volume includes plenums and unconditioned scopes; totals are inspection evidence, not a ready conditioned-volume denominator.'}
        for s in c['spaces']:
            s['source_locator'] = path+'#OS:Space/name='+s['name']
        c['terrain_evidence'] = {'source_locator': path+'#OS:Site/Terrain',
            'source_file_sha256': c['geometry_file_sha256'], 'source_revision': COMMERCIAL_REV,
            'extraction_date': DATE, 'original_value': c['source_site_terrain'], 'original_unit': 'source terrain category',
            'transformation': 'Read pinned SDK Site.terrain after loading the source OSM; preserve default flag',
            'interpretation_note': 'Pinned SDK default' if c['site_terrain_defaulted'] else 'Explicit source OSM terrain'}
        c['interpretation_note'] = 'Source OSM plus source geometry tweaks; retain multipliers once and original space scopes. Compatibility Office lookup is separate from instantiated default. No loads, HVAC, ground solver or EnergyPlus execution.'
    used_geometry = {c['geometry_file'] for c in commercial}
    # Compact receipts: all Ruby/JSON code plus the geometry blobs actually used.
    selected_receipts = {k:v for k,v in receipts.items() if k.startswith('resstock/') or
        k.endswith(('.rb', '.json')) or k.removeprefix('standards/') in used_geometry}
    packet = {'schema_version': '1.0.0', 'kind': 'construction_reference_geometry_recovery',
        'extraction_date': DATE, 'runtime': {**runtime, 'version': residential_raw['runtime_version']},
        'reproducibility_precision': 'Derived SDK geometry: 9 significant digits; literal source tables preserved without rounding.',
        'boundary': 'Above-ground construction derivation evidence only; fixed catalogue scalar conversion/climate policy pending. Ground and systems delivery deferred.',
        'input_sha256': {p: sha(ROOT/p) for p in ['data/releases/v0.2.0/residential_archetypes.json',
            'data/releases/v0.2.0/residential_options.json', 'data/definition-releases/v0.1.1/constructions.json',
            'scripts/recover_construction_geometry.py', 'scripts/recover_construction_geometry.rb', 'scripts/recover_commercial_geometry.rb']},
        'source_files': selected_receipts, 'evidence': evidence, 'residential': residential,
        'commercial': commercial, 'package_mappings': mappings}
    validate(packet)
    return packet, climate_candidates(commercial_source, receipts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    packet, climate = recover()
    if args.check:
        if packet != load_json(OUTPUT):
            raise ValueError('Reference geometry recovery is not reproducible')
        if climate != load_json(CLIMATE_OUTPUT):
            raise ValueError('Candidate climate recovery is not reproducible')
    else:
        dump_json(OUTPUT, packet)
        dump_json(CLIMATE_OUTPUT, climate)
    mapped = sum(bool(m['reference_ids']) for m in packet['package_mappings'])
    print(f"Verified {len(packet['residential'])} residential and {len(packet['commercial'])} commercial references; {mapped}/{len(packet['package_mappings'])} package reference matches, remainder explicitly uninstantiated")


if __name__ == '__main__':
    main()
