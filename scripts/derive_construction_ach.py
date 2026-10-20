"""Build adopted fixed-ACH derivation evidence, without rebuilding frozen releases.

python -m scripts.derive_construction_ach --recover --pilot
python -m scripts.derive_construction_ach --recover
python -m scripts.derive_construction_ach --check
The default/check build reuses the verified native geometry supplement.
"""
import argparse
import copy
import csv
import math
import subprocess
import urllib.request
from pathlib import Path

from scripts.common import ROOT, load_json, dump_json
from scripts.recover_construction_geometry import (sha, canonical_derived, COMMERCIAL_REV,
                                                  OUTPUT as GEOMETRY, CLIMATE_OUTPUT)
from scripts.recover_program_inputs import RUNTIME

DATE = '2026-10-14'
WORK = ROOT / 'build/ach-reference'
STANDARDS = ROOT / 'build/geometry-recovery/standards' / ('openstudio-standards-' + COMMERCIAL_REV)
NIST = 'lib/openstudio-standards/infiltration/data/NISTInfiltrationCorrelations.json'
OUTPUT = ROOT / 'data/construction-inputs/fixed-ach-v1.json'
NATIVE = ROOT / 'data/construction-inputs/commercial-ach-geometry-v1.json'
ENGINE_LOCK = ROOT / 'sources/construction-ach-engine-lock.json'
TERRAIN = {'Country':(.14,270), 'Suburbs':(.22,370), 'City':(.33,460),
           'Ocean':(.10,210), 'Urban':(.22,370)}
EARTH_RADIUS = 6356000


def nonnegative(value, label):
    if not isinstance(value, (int,float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Invalid or missing ' + label)
    return value


def residential_ach(fields, wsf):
    sensitivity = nonnegative(fields.get('annual_ach_per_unit_wsf_per_s', {}).get('value'), 'residential sensitivity')
    return sensitivity * nonnegative(wsf, 'WSF')  # Source sensitivity already includes a_ext.


def residential_forcing(source_climate, climates):
    if source_climate in climates:
        return climates[source_climate],[source_climate]
    if source_climate in ('7AK','8AK'):
        aliases = [source_climate[0]+s for s in ('A','B')]
        rows = [climates[k] for k in aliases]
        if len({(r['wsf'],r['weather_file_sha256']) for r in rows}) == 1:
            return rows[0],aliases
    raise ValueError('Unmapped or ambiguous residential source climate: '+source_climate)


def triangle_area(vertices):
    a,b,c = vertices
    u,v = [[q-p for p,q in zip(a,point)] for point in (b,c)]
    cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    return math.sqrt(sum(x*x for x in cross))/2


def surface_centroid_z(vertices, area):
    """EnergyPlus 25.1 CalcSurfaceCentroid, including >=5 vertex-mean rule."""
    if len(vertices) < 3 or nonnegative(area, 'surface area') == 0:
        raise ValueError('Invalid source surface')
    if len(vertices) != 4:
        return sum(v[2] for v in vertices)/len(vertices)
    triangles = [[vertices[i] for i in indices] for indices in ((0,1,2),(0,2,3))]
    areas = [triangle_area(t) for t in triangles]
    if sum(areas)/area > 1.05:
        triangles = [[vertices[i] for i in indices] for indices in ((0,1,3),(1,2,3))]
        areas = [triangle_area(t) for t in triangles]
        area = sum(areas)
    return sum(a*sum(v[2] for v in t)/3 for a,t in zip(areas,triangles))/area


def wind_factor(height, terrain):
    if terrain not in TERRAIN or not math.isfinite(height):
        raise ValueError('Unsupported source terrain/height')
    exponent,boundary = TERRAIN[terrain]
    return 0 if height <= 0 else (270/10)**.14 * (height/boundary)**exponent


def temperature_offset(height):
    """Weather-station sensor 1.5 m; source lapse rate .0065 K/m."""
    if not math.isfinite(height):
        raise ValueError('Invalid source centroid')
    return .0065*EARTH_RADIUS*1.5/(EARTH_RADIUS+1.5) - (
        .0065*EARTH_RADIUS*height/(EARTH_RADIUS+height) if height > 0 else 0)


def select_coefficients(rows, building_type, climate):
    number = max(1, int(climate[0]))  # Explicit pinned source 0 -> 1 fallback.
    chosen = [r for r in rows if r['building_type'] == building_type and
              int(r['climate_zone']) == number and r['air_barrier'] in ('no',False)]
    by_state = {r['hvac_status']:r for r in chosen}
    if len(chosen) != 2 or set(by_state) != {'on','off'}:
        raise ValueError('Missing/ambiguous NIST coefficients: ' + building_type + '/' + climate)
    off,on = by_state['off'],by_state['on']
    fallback = [k for k in ('a','b','d') if off[k] is None]
    coefficients = {k: on[k] if k in fallback else off[k] for k in ('a','b','d')}
    if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in coefficients.values()):
        raise ValueError('Unresolved source coefficient')
    return {'coefficients':coefficients, 'fallback_fields':fallback,
            'correlation_climate_zone':number, 'original_rows':[on,off]}


def commercial_ach(spaces, weather, terrain, design_rate, coefficients, factor_cache=None, weather_key=None):
    if not spaces or not weather or nonnegative(design_rate,'design rate') == 0:
        raise ValueError('Missing commercial operands')
    a,b,d = (coefficients[k] for k in ('a','b','d'))
    volume,flow = 0,0
    for s in spaces:
        vol = nonnegative(s['volume_m3'],'space volume')
        mult = nonnegative(s['multiplier'],'space multiplier')
        if vol == 0 or mult == 0:
            raise ValueError('Zero source volume/multiplier')
        area = nonnegative(s['exterior_area_m2'],'exterior area')
        volume += vol*mult
        if area == 0:
            continue  # Source interior applicability, not unknown leakage converted to zero.
        height = s['centroid_z_m']
        key = (weather_key, terrain, height, a,b,d)
        if factor_cache is not None and key in factor_cache:
            factor = factor_cache[key]
        else:
            wind2,dt = wind_factor(height,terrain)**2, temperature_offset(height)
            factor = sum(max(0,a+b*abs(22-(t+dt))+d*wind2*w*w) for t,w in weather)/len(weather)
            if factor_cache is not None:
                factor_cache[key] = factor
        flow += design_rate * area * mult * factor
    return {'ach_per_s':flow/volume, 'mean_flow_m3_s':flow, 'reference_volume_m3':volume}


def adopt_mapping(mapping):
    result = copy.deepcopy(mapping)
    result['source_mapping_status'] = mapping['status']
    if not result['reference_ids']:
        if (mapping['package_id'] != 'construction-1d0774872c8801caa0afdd44' or
            mapping.get('status') != 'source_scope_not_instantiated' or
            mapping.get('candidate_reference_ids') != ['90.1-2019/SmallHotel']):
            raise ValueError('Unapproved reference substitution')
        result['reference_ids'] = ['90.1-2019/SmallHotel']
        result['reference_decision'] = 'G1: whole SmallHotel package-level benchmark; exact GuestRoom scope absent'
    return result


def verify_sources(geometry):
    """Fail closed on source/runtime drift; fetch only missing checksum-locked files."""
    from scripts.recover_program_inputs import SOURCE
    runtime_base = ROOT / 'build/runtime/openstudio-windows'
    marker = load_json(runtime_base / '.atlas-extraction.json')
    expected = marker['files'][RUNTIME.relative_to(runtime_base).as_posix()]
    if sha(RUNTIME) != expected or expected != geometry['runtime']['runtime_executable_sha256']:
        raise ValueError('Changed native runtime')
    for path,expected in geometry['input_sha256'].items():
        if sha(ROOT/path) != expected:
            raise ValueError('Stale geometry recovery: '+path)
    for key,proof in geometry['source_files'].items():
        if key.startswith('standards/'):
            path = STANDARDS/key[len('standards/'):]
        else:
            path = SOURCE/key[len('resstock/'):]
            if not path.exists():
                # Two archive-only snippets were separately pinned by the geometry recovery.
                if key not in ('resstock/resources/buildstock.rb','resstock/measures/ResStockArgumentsPostHPXML/measure.rb'):
                    raise ValueError('Missing source ' + key)
                continue
        if sha(path) != proof['sha256']:
            raise ValueError('Changed source ' + key)
    lock = load_json(ENGINE_LOCK)
    for entry in lock['files']:
        path = WORK/'energyplus'/Path(entry['path']).name
        if not path.exists():
            raw = urllib.request.urlopen(entry['url'], timeout=60).read()
            import hashlib
            if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                raise ValueError('Engine download checksum mismatch')
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
        if sha(path) != entry['sha256'] or path.stat().st_size != entry['size_bytes']:
            raise ValueError('Changed engine source ' + entry['path'])
    return lock


def reference_volume(observed, pinned):
    """Keep the accepted reference operand; reject material SDK replay drift.

    Two LargeOffice basement evaluations differed by 1.13e-5 relatively in
    inferred SDK volume with unchanged source geometry. Do not let that
    numerical variability choose a new reference volume on each run.
    """
    if nonnegative(pinned,'pinned volume') == 0 or nonnegative(observed,'observed volume') == 0 or not math.isclose(observed,pinned,rel_tol=2e-5):
        raise ValueError('Native source volume drift exceeds bounded SDK tolerance')
    return pinned


def verify_native_dependencies(native):
    for path,expected in native['input_sha256'].items():
        if sha(ROOT/path) != expected:
            raise ValueError('Stale native supplement: '+path)


def recover_native(geometry, pilot=False):
    cases = geometry['commercial']
    if pilot:
        cases = [c for c in cases if c['id'] == '90.1-2019/MediumOffice']
    WORK.mkdir(parents=True,exist_ok=True)
    dump_json(WORK/'inputs.json', [{'id':c['id'],'template':c['template'],'building_type':c['building_type']} for c in cases])
    subprocess.run([str(RUNTIME), str(ROOT/'scripts/recover_commercial_ach_geometry.rb'),
                    str(STANDARDS), str(WORK/'inputs.json'), str(WORK/'native.json')],
                   cwd=ROOT,check=True,timeout=600)
    rows = load_json(WORK/'native.json')
    by_id = {c['id']:c for c in cases}
    for row in rows:
        source = by_id[row['id']]
        source_spaces = {s['name']:s for s in source['spaces']}
        for space in row['spaces']:
            expected = source_spaces[space['name']]
            space['volume_m3'] = reference_volume(space['volume_m3'],expected['volume_m3'])
            if space['multiplier'] != expected['multiplier']:
                raise ValueError('Native geometry changed: ' + row['id'])
            surfaces = space.pop('surfaces')
            if any(len(s['vertices_m']) > 4 and max(v[2] for v in s['vertices_m'])-min(v[2] for v in s['vertices_m']) > 1e-9 for s in surfaces):
                raise ValueError('Unsupported nonhorizontal 5+ vertex source surface; translate engine geometry first')
            area = sum(s['area_m2'] for s in surfaces)
            space['centroid_z_m'] = sum(surface_centroid_z(s['vertices_m'],s['area_m2'])*s['area_m2'] for s in surfaces)/area
            space['centroid_surface_count'] = len(surfaces)
            space['centroid_surface_area_m2'] = area
            space['source_locator'] = source['geometry_file']+'#OS:Space/name='+space['name']
        if set(row['nist_infiltration_space_names']) != {s['name'] for s in row['spaces'] if s['exterior_area_m2'] > 0}:
            raise ValueError('NIST applicability mismatch: '+row['id'])
        if row['terrain'] != source['source_site_terrain']:
            raise ValueError('Changed source terrain')
        row['geometry_source_locator'] = source['geometry_file']
        row['geometry_source_sha256'] = source['geometry_file_sha256']
        row['source_revision'] = COMMERCIAL_REV
        row['geometry_tweak_source'] = source['geometry_tweak_source']
        row['source_geometry_context'] = source['geometry_context']
        row['source_terrain_defaulted'] = source['site_terrain_defaulted']
        row['source_units'] = 'Coordinates m; surface areas m2; volumes m3; multipliers dimensionless; flow per area m3/s/m2'
        row['transformation'] = 'Gross-area-weighted EnergyPlus surface-centroid equations; source creates one thermal zone per space. Volumes/multipliers retained from pinned geometry-v1 reference; replay volume tolerance 2e-5. NIST native design flow and coefficients; no operating additions.'
        row['extraction_date'] = DATE
    packet = {'schema_version':'1.0.0', 'kind':'commercial_ach_geometry_supplement',
              'extraction_date':DATE, 'references':canonical_derived(rows),
              'input_sha256':{'data/construction-inputs/geometry-v1.json':sha(GEOMETRY),
                              'scripts/derive_construction_ach.py':sha(ROOT/'scripts/derive_construction_ach.py'),
                              'scripts/recover_commercial_ach_geometry.rb':sha(ROOT/'scripts/recover_commercial_ach_geometry.rb')},
              'centroid_algorithm':'EnergyPlus 25.1 SurfaceGeometry.cc/CalcSurfaceCentroid and zone gross-area weighted centroid; triangles/quads/5+ vertex rule retained',
              'height_overrides':'Native geometry checked for unsupported weather-station/height variation objects; absent => pinned EnergyPlus defaults',
              'source_volume_policy':'Pinned geometry-v1 operands retained; native inferred-volume replay compared with relative tolerance 2e-5 (observed two LargeOffice basement deviations 1.13e-5); this does not round or alter the accepted reference volume',
              'centroid_preprocessing_scope':'All source 5+ vertex surfaces are horizontal, so engine collinear-vertex cleanup does not change their height. Reject nonhorizontal 5+ vertex surfaces pending translated geometry recovery.'}
    if pilot:
        dump_json(WORK/'pilot-geometry.json',packet)
    else:
        dump_json(NATIVE,packet)
    return packet


def read_weather(path, expected_sha256):
    if sha(path) != expected_sha256:
        raise ValueError('Changed weather checksum: '+path.name)
    with path.open(encoding='utf-8-sig') as stream:
        lines = list(csv.reader(stream))[8:]
    if len(lines) not in (8760,8784):
        raise ValueError('Unexpected annual weather length')
    result = []
    for r in lines:
        t,w = float(r[6]),float(r[21])
        if not math.isfinite(t) or not -100 < t < 100 or not 0 <= w < 40:
            raise ValueError('Invalid/missing EPW forcing')
        result.append((t,w))
    return result


def build(geometry, native, engine, pilot=False):
    climates = [r for r in load_json(CLIMATE_OUTPUT)['candidates'] if r['source_map_edition'] == '2013']
    for climate in climates:
        climate['adoption_date'] = DATE
        climate['evidence']['interpretation_note'] = 'F1 accepted 2013 reference forcing across vintages; WSF used for residential only. Weather filename is provenance, not an applicability axis. Raw candidate receipt remains unchanged.'
    if len(climates) != 21 or len({r['climate_zone'] for r in climates}) != 21:
        raise ValueError('Incomplete 2013 reference map')
    source_cases = {r['id']:r for r in geometry['commercial']}
    native_cases = {r['id']:r for r in native['references']}
    if not pilot and set(native_cases) != set(source_cases):
        raise ValueError('Incomplete native commercial reference census')
    verify_native_dependencies(native)
    constructions = load_json(ROOT/'data/definition-releases/v0.1.1/constructions.json')
    dwellings = {r['source_id']:r for r in constructions if r.get('role') == 'dwelling_enclosure'}
    by_climate = {r['climate_zone']:r for r in climates}
    residential = []
    for r in geometry['residential']:
        enclosure = dwellings[r['id']]
        climate = enclosure['climate']
        forcing,aliases = residential_forcing(climate,by_climate)
        rate = residential_ach(r['fields'],forcing['wsf'])
        residential.append({'construction_id':enclosure['id'], 'reference_id':r['id'], 'source_climate_label':climate,
            'reference_climate_labels':aliases,
            'natural_ach':{'value':rate,'unit':'1/s'}, 'inspection_ach_per_h':rate*3600,
            'method':'resstock_source_annual_average', 'evidence_id':r['evidence_id'],
            'original_value':{'source_sensitivity_per_s_per_wsf':r['fields']['annual_ach_per_unit_wsf_per_s']['value'], 'wsf':forcing['wsf']},
            'original_unit':'1/s per WSF and dimensionless',
            'transformation':'recovered annual exterior-ACH sensitivity * adopted WSF; exposure is already included',
            'interpretation_note':'Source fixture climate retained; no new residential assembly applicability inferred. Fixed catalogue constant; not hourly AIM-2 parity.'})
    coefficient_rows = load_json(STANDARDS/NIST)['infiltration']
    commercial, cache = [], {}
    for forcing in climates:
        climate = forcing['climate_zone']
        if forcing['weather_file_sha256'] != forcing['evidence']['weather_source_sha256']:
            raise ValueError('Inconsistent weather receipt')
        weather = read_weather(STANDARDS/forcing['evidence']['weather_source_locator'],forcing['weather_file_sha256'])
        for ref_id,g in native_cases.items():
            source = source_cases[ref_id]
            fit = select_coefficients(coefficient_rows,source['nist_inferred_type'],climate)
            rate = g['native_flow_per_exterior_area_m_s']
            expected = 13.8*(4/75)**.65/3600 * g['five_sided_area_m2']/g['energyplus_normalization_area_m2']
            if not math.isclose(rate,expected,rel_tol=2e-8):
                raise ValueError('Native source leakage normalization mismatch: ' + ref_id)
            if climate == '4A' and any(not math.isclose(g['native_off_coefficients'][k],v,rel_tol=2e-8,abs_tol=1e-10) for k,v in fit['coefficients'].items()):
                raise ValueError('Native coefficient mismatch: ' + ref_id)
            result = commercial_ach(g['spaces'],weather,g['terrain'],rate,fit['coefficients'],cache,climate)
            commercial.append({'reference_id':ref_id, 'climate_zone':climate,
                'natural_ach':{'value':result['ach_per_s'],'unit':'1/s'},
                'inspection_ach_per_h':result['ach_per_s']*3600,
                'mean_flow_m3_s':result['mean_flow_m3_s'], 'reference_enclosed_volume_m3':result['reference_volume_m3'],
                'method':'nist_source_passive_envelope_hourly_reference_mean',
                'nist_correlation_type':source['nist_inferred_type'], 'coefficient_evidence':fit,
                'source_surrogate_mapping':source['building_type'] != source['nist_inferred_type'],
                'source_locator':NIST+'#infiltration/'+source['nist_inferred_type']+'/'+str(fit['correlation_climate_zone'])+'/no/off',
                'source_revision':COMMERCIAL_REV,
                'geometry_evidence_locator':'commercial-ach-geometry-v1.json#/references/id='+ref_id,
                'forcing_evidence_locator':'fixed-ach-v1.json#/climate_references/climate_zone='+climate,
                'original_value':{'native_design_rate_m_s':rate,'coefficients':fit['coefficients'],
                                  'whole_enclosed_volume_m3':result['reference_volume_m3']},
                'original_unit':'Native flow per area m3/s/m2; coefficient a dimensionless, b 1/K, d s2/m2; volume m3',
                'transformation':'Sum [native q4/exterior-area * space Outdoors gross area * multiplier * mean(max(0,a+b*abs(22C-height-adjusted EPW dry bulb)+d*height-adjusted wind^2))] / whole source enclosed volume with multipliers',
                'interpretation_note':'Equal-weight hourly EPW samples; schedule=1 for source off correlation, no pressurization/door operation. Includes all source enclosure spaces in denominator, not conditioned-volume claim. No simulation timestep/energy parity claimed.'})
    result = {'schema_version':'1.0.0', 'kind':'adopted_construction_fixed_ach_derivation',
        'status':'validated_derivation_evidence; consumer_construction_release_pending', 'extraction_date':DATE,
        'decisions':{'reference_map':'ASHRAE 169-2013 for all vintages', 'residential':'F2 accepted source annual-average helper',
                     'commercial':'F3 accepted passive envelope, 22C, system-off year round', 'smallhotel':'G1 accepted whole SmallHotel benchmark; exact GuestRoom scope absent',
                     'consumer_use':'Reuse selected constant across consumer geometry/zoning; source reference form remains explicit'},
        'reference_conditions':{'temperature_K':295.15,'pressure_test_Pa':75,'commercial_source_airtightness_m3_s_m2':13.8/3600,
          'pressure_exponent':.65,'pressure_normalization':'5-sided, source unmultiplied gross areas', 'air_barrier':False,
          'commercial_volume_basis':'whole source enclosed air volume with source multipliers, including interior/plenum spaces',
          'commercial_averaging':'Arithmetic mean of nonnegative hourly source correlation volume flows over full EPW year; no design days or timestep interpolation',
          'excluded':['mechanical pressurization','operating door-opening additions','mechanical outdoor/total supply','ground heat transfer','systems'],
          'weather_station':{'wind_sensor_height_m':10,'wind_exponent':.14,'wind_boundary_layer_height_m':270,'temperature_sensor_height_m':1.5},
          'site_temperature_gradient_K_m':.0065,'earth_radius_m':EARTH_RADIUS},
        'climate_references':climates, 'engine_source':engine,
        'source_file_sha256':{NIST:sha(STANDARDS/NIST), 'lib/openstudio-standards/infiltration/nist_infiltration.rb':sha(STANDARDS/'lib/openstudio-standards/infiltration/nist_infiltration.rb'),
            'lib/openstudio-standards/prototypes/common/objects/Prototype.Model.rb':sha(STANDARDS/'lib/openstudio-standards/prototypes/common/objects/Prototype.Model.rb')},
        'input_sha256':{p:sha(ROOT/p) for p in ('data/construction-inputs/geometry-v1.json','data/construction-inputs/climate-factor-candidates-v1.json',
            'data/definition-releases/v0.1.1/constructions.json','scripts/derive_construction_ach.py','sources/construction-ach-engine-lock.json')},
        'residential':residential, 'commercial_reference_benchmarks':commercial,
        'package_reference_mappings':[adopt_mapping(m) for m in geometry['package_mappings']],
        'boundary':'Derivation sidecar only. Commercial reference benchmarks do not create new assembly/climate applicability. Final exporter must resolve assembly selectors and reference variants; no program/system payload dependency.'}
    if not pilot:
        result['input_sha256'][NATIVE.relative_to(ROOT).as_posix()] = sha(NATIVE)
    validate(result,pilot=pilot)
    return result


def validate(packet,pilot=False):
    keys = [(r['reference_id'],r['climate_zone']) for r in packet['commercial_reference_benchmarks']]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate commercial ACH benchmark')
    if not pilot and (len(keys) != 129*21 or len(packet['residential']) != 41 or len(packet['package_reference_mappings']) != 183):
        raise ValueError('Incomplete fixed-ACH census')
    refs = {k[0] for k in keys}
    for m in packet['package_reference_mappings']:
        if not m['reference_ids'] or (not pilot and not set(m['reference_ids']) <= refs):
            raise ValueError('Orphan/empty adopted benchmark mapping')
    for r in packet['residential'] + packet['commercial_reference_benchmarks']:
        v = nonnegative(r['natural_ach']['value'],'fixed ACH')
        if r['natural_ach']['unit'] != '1/s' or not math.isclose(v*3600,r['inspection_ach_per_h'],rel_tol=1e-12):
            raise ValueError('Inconsistent ACH units')
        if not r.get('transformation') or not r.get('interpretation_note'):
            raise ValueError('Missing derivation evidence')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recover',action='store_true')
    parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    if args.pilot and args.check:
        parser.error('--pilot and --check are distinct modes')
    geometry = load_json(GEOMETRY)
    engine = verify_sources(geometry)
    native = recover_native(geometry,args.pilot) if args.recover else load_json(WORK/'pilot-geometry.json' if args.pilot else NATIVE)
    packet = build(geometry,native,engine,args.pilot)
    if args.check:
        if packet != load_json(OUTPUT):
            raise ValueError('Fixed ACH derivation not reproducible')
    else:
        dump_json(WORK/'pilot-ach.json' if args.pilot else OUTPUT,packet)
    print(f"Verified {len(packet['residential'])} residential constants, {len(packet['commercial_reference_benchmarks'])} commercial reference/climate benchmarks and {len(packet['package_reference_mappings'])} package mappings")


if __name__ == '__main__':
    main()
