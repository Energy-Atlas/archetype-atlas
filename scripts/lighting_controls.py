"""Extract the lighting controls of the source models for release 1.5.0 (ADR 0044).

python -m scripts.lighting_controls [--prototype-root DIR] [--doe-root DIR] [--check]

Reads the PNNL prototypes pinned in sources/reference-models-lock.json (IECC commercial
2006-2021 and ASHRAE 90.1 2007, 2013 and 2019, 16 types x 19 locations each) and scans
the 768 DOE reference IDFs, and writes the committed input
data/program-inputs/lighting-controls-v1.json, which `apply` adds to the release
writers' sources without the IDFs:
- per template, building type and standards space type (the zones of the program, as
  scripts.iecc_commercial_values groups them), the `Daylighting:Controls` of the zones:
  the floor fraction of zones with controls, the fraction of the program's lighting
  power the reference points control, and the control settings, weighted by zone
  lighting power. A record that differs by location keeps the most common one and lists
  the others in `daylighting_by_climate`;
- for the 90.1 templates, the openstudio-standards rule inputs of the space type
  (target illuminance and the office non-geometry fractions);
- the scan counts: no DOE reference, IECC residential or manufactured-housing model has
  daylighting controls, so DOE Ref programs record a source zero and dwellings none.
Occupancy-sensor credits are already in the lighting schedules and are not repeated.
--check rebuilds and compares the committed file.
"""
import argparse
import copy
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

from scripts import idf_reader
from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id
from scripts.iecc_commercial_values import encode, modal, rounded, sha256, zone_objects, zones
from scripts.iecc_commercial_zones import BASE_CITY, CITIES, EDITIONS, TYPES, Lookup, geometry_tags, normalize

OUTPUT = ROOT/'data/program-inputs/lighting-controls-v1.json'
LOCK = ROOT/'sources/reference-models-lock.json'
SPC_TYP = 'lib/openstudio-standards/standards/ashrae_90_1/ashrae_90_1_{0}/data/ashrae_90_1_{0}.spc_typ.json'
EXTRACTION_DATE = '2026-10-27'
ADR = 'docs/adr/0044-lighting-controls.md'
ASHRAE_YEARS = ('2007', '2013', '2019')
FAMILIES = {
    'commercial-iecc': {'prefix': 'IECC', 'years': EDITIONS, 'template': 'IECC {}',
                        'project': 'DOE/PNNL Prototype Building Models (IECC commercial)'},
    'commercial-ashrae901': {'prefix': 'ASHRAE901', 'years': ASHRAE_YEARS, 'template': '90.1-{}',
                             'project': 'DOE/PNNL Prototype Building Models (ASHRAE 90.1)'}}
DOE_TEMPLATES = {'pre1980': 'DOE Ref Pre-1980', 'post1980': 'DOE Ref 1980-2004'}
CONTROL_TYPES = {'continuous': 'continuous', 'stepped': 'stepped', 'continuousoff': 'continuous_off'}
METHODS = {'splitflux': 'split_flux', 'delight': 'delight'}
# Daylighting:Controls fields (EnergyPlus 22.1): name, zone, method, availability schedule, control type,
# minimum input power fraction, minimum light output fraction, stepped steps, reset probability,
# glare point, glare azimuth, maximum glare index, DElight gridding, then (point, fraction, setpoint) triples.
POINTS = 13
UNKNOWN = ('No PNNL prototype zone carries this space type, and the pinned openstudio-standards cache holds the '
           'space-type data but not the template daylighting rules, so the controls are unknown (ADR 0044).')


def prototype_root():
    return Path(os.environ.get('ATLAS_PROTOTYPE_ROOT', 'D:/Prototype Building Models'))


def doe_root():
    return Path(os.environ.get('ATLAS_DOE_IDF_ROOT', 'D:/Reference Building Models/v1.4_7.2'))


class Extract:
    """Source files and evidence of the whole input."""

    def __init__(self, root):
        self.root = Path(root)
        self.lock = load_json(LOCK)
        self.archives = {e['path']: e for e in self.lock['files']}
        self.source_files, self.evidence = {}, {}

    def add_source(self, row):
        key = stable_id('sourcefile', row)[:len('sourcefile-')+20]
        self.source_files[key] = {'id': key, **row}
        return key

    def prototype_file(self, family, path):
        relative = Path(path).relative_to(self.root/family).as_posix()
        archive = self.archives[f'{family}/{relative.split("/")[0]}.zip']
        return self.add_source({
            'source_id': 'pnnl-prototypes', 'project': FAMILIES[family]['project'],
            'version': 'energycodes.gov 2023-10 bundles, EnergyPlus 22.1', 'path': relative,
            'archive_path': archive['path'], 'archive_sha256': archive['sha256'], 'url': archive['url'],
            'retrieval_date': self.lock['retrieval_date'], 'sha256': sha256(path), 'size_bytes': Path(path).stat().st_size,
            'license_path': 'sources/licenses/pnnl-prototypes.txt'})

    def doe_file(self, path, idf_root):
        relative = Path(path).relative_to(idf_root).as_posix()
        archive = self.archives['v1.4_7.2/'+relative.split('/')[0]+'.zip']
        return self.add_source({
            'source_id': 'doe-reference', 'project': 'DOE Commercial Reference Buildings', 'version': 'v1.4_7.2',
            'path': relative, 'archive_path': archive['path'], 'archive_sha256': archive['sha256'], 'url': archive['url'],
            'retrieval_date': self.lock['retrieval_date'], 'sha256': sha256(path), 'size_bytes': Path(path).stat().st_size,
            'license_path': 'sources/licenses/doe-reference.txt'})

    def cite(self, source_file, locator, value, unit, transformation, note):
        row = {'source_file_id': source_file, 'locator': locator, 'original_value': value, 'original_unit': unit,
               'transformation': transformation, 'extraction_date': EXTRACTION_DATE, 'interpretation': note}
        key = stable_id('evidence', row)
        self.evidence[key] = {'id': key, **row}
        return key


def availability(model, name):
    """The availability schedule as a descriptor; only the always-on-but-design-days form is known."""
    fields = next((f for f in model.all('schedule:compact') if f[0].lower() == name.lower()), None)
    if fields is None:
        raise ValueError(f'No Schedule:Compact {name} in {model.path.name}')
    body = [f.strip().lower().replace(' ', '') for f in fields[2:]]
    if body == ['through:12/31', 'for:summerdesigndaywinterdesignday', 'until:24:00', '0', 'for:allotherdays', 'until:24:00', '1']:
        return 'all_days_except_design_days', fields
    raise ValueError(f'Unrecognized daylighting availability schedule {name} in {model.path.name}: {fields}')


def controls(model):
    """{zone: settings and controlled fraction} for every Daylighting:Controls of a model."""
    out = {}
    for f in model.all('daylighting:controls'):
        zone = f[1].lower()
        if zone in out:
            raise ValueError(f'Several Daylighting:Controls in zone {f[1]} ({model.path.name})')
        points = [f[i:i+3] for i in range(POINTS, len(f), 3) if f[i].strip()]
        setpoints = sorted({float(p[2]) for p in points})
        if len(setpoints) != 1:
            raise ValueError(f'Reference points of {f[0]} have several setpoints {setpoints} ({model.path.name})')
        state, schedule = availability(model, f[3])
        out[zone] = {
            'object': f[0], 'fraction': math.fsum(float(p[1]) for p in points), 'points': len(points),
            'settings': {'method': METHODS[f[2].strip().lower()], 'control_type': CONTROL_TYPES[f[4].strip().lower()],
                         'availability': state, 'illuminance_setpoint_lux': setpoints[0],
                         'minimum_input_power_fraction': float(f[5]), 'minimum_light_output_fraction': float(f[6]),
                         'stepped_control_steps': int(float(f[7]))},
            'source': {'fields': f, 'availability': schedule}}
    return out


class TypeModels:
    """The 19 location models of one family, type and year, reduced to what the controls need."""

    def __init__(self, extract, family, pnnl, year, tags):
        spec = FAMILIES[family]
        self.template, self.building_type = spec['template'].format(year), TYPES[pnnl]
        self.cities, self.files = {}, {}
        for city in CITIES:
            path = extract.root/family/f'{spec["prefix"]}_{pnnl}'/f'{spec["prefix"]}_{pnnl}_STD{year}_{city}.idf'
            model = idf_reader.Model(path)
            geometry = zones(model)
            objects, _ = zone_objects(model, geometry)
            self.cities[city] = {'geometry': geometry, 'controls': controls(model),
                                 'lighting': {z: (objects[z].get('lighting') or {}).get('value', 0.0) for z in geometry}}
            self.files[city] = extract.prototype_file(family, path)
        base = self.cities[BASE_CITY]['geometry']
        for city, found in self.cities.items():
            if {k: (g['multiplier'], round(g['floor_m2'], 6)) for k, g in found['geometry'].items()} != \
                    {k: (g['multiplier'], round(g['floor_m2'], 6)) for k, g in base.items()}:
                raise ValueError(f'Zone geometry differs between {BASE_CITY} and {city} for {pnnl} {self.template}')
        self.space = {z: tags(self.building_type, g['name']) for z, g in base.items()}
        self.groups = defaultdict(list)
        for z in sorted(base):
            self.groups[self.space[z][1]].append(z)

    def area(self, zone):
        g = self.cities[BASE_CITY]['geometry'][zone]
        return g['floor_m2']*g['multiplier']


def program_controls(models, zones_, city):
    """The daylighting record of one program in one location, or None where no zone has controls."""
    found = models.cities[city]
    area = math.fsum(models.area(z) for z in zones_)
    power = {z: models.area(z)*found['lighting'][z] for z in zones_}
    weights = power if math.fsum(power.values()) > 0 else {z: models.area(z) for z in zones_}
    total = math.fsum(weights.values())
    controlled = [z for z in zones_ if z in found['controls']]
    if not controlled or not area:
        return None
    settings = Counter()
    for z in controlled:
        settings[json.dumps(found['controls'][z]['settings'], sort_keys=True)] += weights[z] or models.area(z)
    chosen = json.loads(max(sorted(settings), key=lambda k: settings[k]))
    record = {'controlled_floor_fraction': rounded(math.fsum(models.area(z) for z in controlled)/area),
              'controlled_lighting_fraction': rounded(math.fsum(weights[z]*found['controls'][z]['fraction'] for z in controlled)/total)
              if total else 0.0,
              'controlled_zones': len(controlled), 'zones': len(zones_), **chosen}
    if len(settings) > 1:
        record['settings_conflict'] = True
    return record


def program_record(extract, models, space_type, zones_, standards_rule):
    per_city = {city: program_controls(models, zones_, city) for city in CITIES}
    value, exceptions, city = modal(per_city)
    zone_list = ', '.join(models.cities[BASE_CITY]['geometry'][z]['name'] for z in zones_)

    def cite(c):
        found = models.cities[c]['controls']
        fields = {found[z]['object']: found[z]['source']['fields'][2:] for z in zones_ if z in found}
        return extract.cite(models.files[c], f'Daylighting:Controls in zones {zone_list}', fields or None, 'lux; fractions',
                            'zones with controls over program floor area; reference-point fractions weighted by zone lighting power; '
                            'settings of the power-dominant zone',
                            f'PNNL prototype daylighting controls, climate zone {CITIES[c][0]} ({c}); absent objects are a source zero '
                            '(ADR 0044). The fractions hold for the prototype geometry.')
    block = {'status': 'known', 'source': 'pnnl_prototype', 'geometry_dependent': True, 'daylighting': value,
             'evidence_id': cite(city)}
    if exceptions:
        block['daylighting_by_climate'] = exceptions
        block['climate_evidence_ids'] = {c: cite(next(k for k, v in CITIES.items() if v[1] == c)) for c in exceptions}
    if standards_rule:
        block['standards_rule'] = standards_rule
    return block


def standards_rules(extract, year, sources):
    """{(standards building type, space type): openstudio-standards daylighting inputs} of one 90.1 template."""
    path = SPC_TYP.format(year)
    row = next(r for r in sources.values() if r['path'] == path)
    source_file = extract.add_source({k: v for k, v in row.items() if k != 'id'})
    rows = load_json(ROOT/'data/raw/openstudio-standards'/path)['space_types']
    out = {}
    for r in rows:
        if r.get('template') not in (None, f'90.1-{year}'):
            continue
        setpoint = r.get('target_illuminance_setpoint')
        rule = {'target_illuminance_setpoint_lux': None if setpoint in (None, 'na') else float(setpoint),
                'daylighting_appropriate': setpoint != 'na'}
        for key, name in (('psa_nongeometry_fraction', 'primary_sidelit_nongeometry_fraction'),
                          ('ssa_nongeometry_fraction', 'secondary_sidelit_nongeometry_fraction')):
            if r.get(key) is not None:
                rule[name] = float(r[key])
        rule['evidence_id'] = extract.cite(
            source_file, f'space_types {r["building_type"]} / {r["space_type"]}',
            {k: r.get(k) for k in ('target_illuminance_setpoint', 'psa_nongeometry_fraction', 'ssa_nongeometry_fraction')},
            'lux; fractions', 'as written; "na" is daylighting not appropriate, null is the 375 lux default of space_add_daylighting_controls',
            f'openstudio-standards 90.1-{year} space-type daylighting inputs (ADR 0044); the template rules that decide whether '
            'controls are required are not in the pinned cache.')
        out[(r['building_type'], r['space_type'])] = rule
    return out


def template_tags(year):
    """The 90.1 template's own geometry tags, the IECC lookup's aliases for names its geometry lacks."""
    tags, lookup = geometry_tags(), Lookup()

    def tag(building_type, zone):
        found = tags.get((building_type, normalize(zone)), {}).get(f'90.1-{year}')
        return found or lookup(building_type, zone)
    return tag


def doe_scan(extract, idf_root):
    """The DOE reference IDFs and their daylighting controls, with one cited file per atlas DOE Ref template."""
    counts, cited = Counter(), {}
    for path in sorted(Path(idf_root).glob('*/*.idf')):
        vintage = next((v for v in DOE_TEMPLATES if f'_{v}_' in path.parent.name), 'new2004')
        model = idf_reader.Model(path)
        counts[vintage, 'models'] += 1
        counts[vintage, 'with_controls'] += bool(model.all('daylighting:controls'))
        if vintage in DOE_TEMPLATES and vintage not in cited and 'mediumoffice' in path.parent.name and '5A' in path.name:
            cited[vintage] = extract.doe_file(path, idf_root)
    out = {}
    for vintage, template in DOE_TEMPLATES.items():
        models, found = counts[vintage, 'models'], counts[vintage, 'with_controls']
        if found:
            raise ValueError(f'{found} DOE reference {vintage} models have daylighting controls; ADR 0044 assumes none')
        out[template] = {'status': 'known', 'source': 'doe_reference', 'daylighting': None, 'evidence_id': extract.cite(
            cited[vintage], 'Daylighting:Controls (none)', {'models_scanned': models, 'with_controls': found}, 'count',
            'absence in every complete DOE reference model of the vintage',
            f'No DOE reference {vintage} model (all 16 types x 16 locations) has daylighting controls: a source zero (ADR 0044).')}
    return out, {f'doe-reference-{v}': {'models': counts[v, 'models'], 'with_controls': counts[v, 'with_controls']}
                 for v in ('pre1980', 'post1980', 'new2004')}


def build(root=None, idf_root=None):
    from scripts import atlas_programs
    root, idf_root = Path(root or prototype_root()), Path(idf_root or doe_root())
    extract = Extract(root)
    sources = atlas_programs.load_sources().source_files
    records, scan = [], {}
    for family, spec in FAMILIES.items():
        for year in spec['years']:
            ashrae = family == 'commercial-ashrae901'
            tags = template_tags(year) if ashrae else Lookup()
            rules = standards_rules(extract, year, sources) if ashrae else {}
            with_controls = models_read = 0
            for pnnl in TYPES:
                models = TypeModels(extract, family, pnnl, year, tags)
                models_read += len(models.cities)
                with_controls += sum(bool(c['controls']) for c in models.cities.values())
                for space_type, zones_ in sorted(models.groups.items()):
                    standards_building_type = models.space[zones_[0]][0]
                    rule = rules.get((standards_building_type, space_type)) if ashrae else None
                    records.append({'template': models.template, 'building_type': models.building_type, 'space_type': space_type,
                                    'standards_building_type': standards_building_type,
                                    'lighting_controls': program_record(extract, models, space_type, zones_, rule)})
            scan[spec['template'].format(year)] = {'models': models_read, 'with_controls': with_controls}
    absent, doe = doe_scan(extract, idf_root)
    scan.update(doe)
    for folder in ('residential', 'manufactured-housing'):
        paths = sorted((root/folder).rglob('*.idf'))
        found = sum(b'daylighting:controls' in p.read_bytes().lower() for p in paths)
        if found:
            raise ValueError(f'{found} {folder} prototypes have daylighting controls; ADR 0044 records none for dwellings')
        scan[f'{folder}-prototypes'] = {'models': len(paths), 'with_controls': found}
    return {
        'schema_version': '1.0.0', 'kind': 'lighting_controls_definitions', 'adr': ADR,
        'generated_by': 'python -m scripts.lighting_controls', 'extraction_date': EXTRACTION_DATE,
        'input_sha256': {p: sha256(ROOT/p) for p in ('sources/reference-models-lock.json', 'sources/iecc-commercial-zone-aliases.json',
                                                       'data/construction-inputs/geometry-v1.json')},
        'scan': dict(sorted(scan.items())), 'unknown_reason': UNKNOWN,
        'source_files': [extract.source_files[k] for k in sorted(extract.source_files)],
        'provenance': [extract.evidence[k] for k in sorted(extract.evidence)],
        'templates_without_controls': absent,
        'records': sorted(records, key=lambda r: (r['template'], r['building_type'], r['space_type']))}


# ---------------------------------------------------------------- overlay

def space_type(program):
    suffix = '_'+program['building_type']
    return program['name'][:-len(suffix)] if program['name'].endswith(suffix) else program['name']


def apply(programs, document=None):
    """Add `lighting_controls` to every commercial source program and twin (not mixes) of an atlas_programs.Sources.

    The records of a template, building type and space type go on the programs of that name;
    the DOE Ref templates take the scanned absence, and 90.1 and IECC programs that no prototype
    zone carries are unknown. Their evidence and source files join the sources."""
    document = document or load_json(OUTPUT)
    records = {(r['template'], r['building_type'], r['space_type']): r['lighting_controls'] for r in document['records']}
    absent = document['templates_without_controls']
    for source in document['source_files']:
        programs.source_files.setdefault(source['id'], copy.deepcopy(source))
    programs.evidence.update({e['id']: copy.deepcopy(e) for e in document['provenance']})
    families = {r['template'] for r in document['records']}
    added = Counter()
    for program in programs.programs.values():
        template = program.get('template')
        if program.get('derivation') == 'composed':
            continue  # mixes: consumers read the controls of their members
        if template in absent:
            block = absent[template]
        elif template in families:
            block = records.get((template, program['building_type'], space_type(program)))
            block = block or {'status': 'unknown', 'source': 'pnnl_prototype', 'reason': document['unknown_reason']}
        else:
            continue
        program['lighting_controls'] = copy.deepcopy(block)
        cited = [block.get('evidence_id'), *block.get('climate_evidence_ids', {}).values(),
                 (block.get('standards_rule') or {}).get('evidence_id')]
        program['evidence_ids'] = sorted({*program.get('evidence_ids', []), *(e for e in cited if e)})
        added[block['status']] += 1
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--prototype-root', type=Path)
    parser.add_argument('--doe-root', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = encode(build(args.prototype_root, args.doe_root))
    if args.check:
        if OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.name} does not reproduce; rerun python -m scripts.lighting_controls')
        print(f'{OUTPUT.name} reproduces')
        return
    OUTPUT.write_bytes(data)
    document = json.loads(data)
    states = Counter('none' if r['lighting_controls']['daylighting'] is None else 'controls' for r in document['records'])
    print(f'Lighting controls: {len(document["records"])} program records ({dict(states)}), '
          f'{len(document["provenance"])} evidence rows; scan: '
          + ', '.join(f'{t} {s["with_controls"]}/{s["models"]}' for t, s in document['scan'].items()))


if __name__ == '__main__':
    main()
