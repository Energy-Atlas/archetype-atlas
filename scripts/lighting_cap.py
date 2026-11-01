"""The unoccupied lighting cap of the PNNL prototypes: the input of the release 2.4.0 field (ADR 0060 section 1).

python -m scripts.lighting_cap           # write data/program-inputs/unoccupied-lighting-cap-v1.json from the IDFs
python -m scripts.lighting_cap --check   # rebuild from the IDFs and fail unless the committed file equals it

PNNL's ASHRAE 90.1-2016 to 2022 prototypes (header comment `LPD_Ctrl = 0.02`) give each controlled zone one EMS
program, called at `BeginTimestepBeforePredictor` (`AfterPredictorAfterHVACManagers` in the large office):

    SET Z_LSr_IP = 0.093*Z_LSr/Z_Area                     ! Zone Lights Electricity Rate per zone floor area, W/ft2
    IF (Z_Occ_Sensor <= 0) && (Z_LSr_IP >= 0.02)          ! People Occupant Count of the zone's People object
      SET Z_Light_Actuator = 0.02*Z_Area/0.09290304        ! the zone's Lights object, Electricity Rate: 0.02 W/ft2
    ELSE
      SET Z_Light_Actuator = NULL
    ENDIF

The atlas holds 90.1-2019 of that series. This script reads every 90.1-2019 prototype (16 types, 19 locations each),
groups the zones by space type as the lighting controls do (ADR 0044), and records for each program whose zones
carry the rule its parameters (cap and threshold in W/m2, the condition, the comparison, the calling point, zone
exceptions), or that none of its zones carries it. It scans the 90.1-2007, 90.1-2013 and IECC 2006-2021 prototypes
(304 models each) and the DOE reference models, none of which has such a program, and records that absence per
template. Each record cites the Buffalo IDF and its EMS programs; every location must agree.
"""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

from scripts import idf_reader
from scripts.common import ROOT
from scripts.iecc_commercial_zones import BASE_CITY, CITIES, EDITIONS, TYPES
from scripts.lighting_controls import DOE_TEMPLATES, doe_root
from scripts.pnnl_901 import ADR, EXTRACTION_DATE, Extract, FAMILY, Models, same_everywhere

OUTPUT = ROOT/'data/program-inputs/unoccupied-lighting-cap-v1.json'
YEAR = '2019'
FT2 = 0.09290304   # m2 per ft2, as the IDF writes it
SET_RATE = re.compile(r'^SET (\w+)_LSr_IP\s*=\s*([0-9.]+)\*(\w+)_LSr/(\w+)_Area$')
TEST = re.compile(r'^IF \((\w+)_Occ_Sensor <= 0\) && \((\w+)_LSr_IP >= ([0-9.]+)\)$')
SET_CAP = re.compile(r'^SET (\w+)_Light_Actuator = ([0-9.]+)\*(\w+)_Area/([0-9.]+)$')
SET_ALLOWANCE = re.compile(r'^SET (\w+)_Light_ALLOWANCE_Actuator = 0$')
TRANSFORMATION = ('EMS program lines as written; cap = 0.02 W/ft2 / 0.09290304 m2/ft2; threshold = 0.02 / 0.093 (the program '
                  'converts W/m2 to W/ft2 with 0.093); zones counted over the program\'s zone group')
INTERPRETATION = ('PNNL ASHRAE 90.1-2019 prototype unoccupied lighting cap (ADR 0060 section 1): in each listed zone, at every '
                  'timestep, when the occupant count is 0 and the zone lighting power is at least the threshold, the zone\'s '
                  'Lights object is set to the cap; otherwise the scheduled lighting applies. The same in all 19 locations.')


def ems(model):
    """{program name: lines}, sensors, actuators and calling points of a model's EMS."""
    programs = {f[0]: [x for x in f[1:] if x] for f in model.all('energymanagementsystem:program')}
    sensors = {f[0].lower(): (f[1], f[2]) for f in model.all('energymanagementsystem:sensor')}
    actuators = {f[0].lower(): (f[1], f[2], f[3]) for f in model.all('energymanagementsystem:actuator')}
    variables = {f[0].lower(): (f[1], f[2]) for f in model.all('energymanagementsystem:internalvariable')}
    points = {p.lower(): f[1] for f in model.all('energymanagementsystem:programcallingmanager') for p in f[2:] if p}
    return programs, sensors, actuators, variables, points


def rules(model):
    """{zone key: rule as read} for every unoccupied-lighting EMS program of one model."""
    programs, sensors, actuators, variables, points = ems(model)
    people = {p['name'].lower(): p['zones'] for p in model.loads('people')}
    lights = {p['name'].lower(): p['zones'] for p in model.loads('lights')}
    out = {}
    for name, lines in programs.items():
        found = TEST.match(lines[1]) if len(lines) > 1 else None
        if not found:
            continue
        rate = SET_RATE.match(lines[0])
        if rate is None:
            raise ValueError(f'{model.path.name} {name}: unexpected first line {lines[0]!r}')
        stem, factor = rate[1], float(rate[2])
        occupancy, threshold = found[1], float(found[3])
        lsr = sensors[f'{stem}_lsr'.lower()]
        if lsr[1].lower() != 'zone lights electricity rate':
            raise ValueError(f'{name}: sensor {lsr}')
        zone = lsr[0].lower()
        if variables[f'{stem}_area'.lower()] != (lsr[0], 'Zone Floor Area'):
            raise ValueError(f'{name}: area variable {variables[f"{stem}_area".lower()]}')
        occ = sensors[f'{occupancy}_occ_sensor'.lower()]
        if occ[1].lower() != 'people occupant count':
            raise ValueError(f'{name}: occupancy sensor {occ}')
        sensed = people[occ[0].lower()]
        if len(sensed) != 1:
            raise ValueError(f'{name}: People object {occ[0]} spans {sensed}')
        caps = [SET_CAP.match(l) for l in lines]
        caps = [c for c in caps if c]
        if not caps or any(c[1] != stem or c[3] != stem for c in caps) or len({(c[2], c[4]) for c in caps}) != 1:
            raise ValueError(f'{name}: cap lines {[c[0] for c in caps]}')
        actuator = actuators[f'{stem}_light_actuator'.lower()]
        if actuator[1:] != ('Lights', 'Electricity Rate') or lights[actuator[0].lower()] != [zone]:
            raise ValueError(f'{name}: actuator {actuator}')
        allowance = [l for l in lines if SET_ALLOWANCE.match(l)]
        # The common body is six lines; the rest are the zone's extra conditions and the allowance actuator.
        body = {lines[0], lines[1], *(c[0] for c in caps), *allowance, 'ELSE', f'SET {stem}_Light_Actuator = NULL',
                f'SET {stem}_Light_ALLOWANCE_Actuator = NULL', 'ENDIF'}
        extra = [l for l in lines[2:] if l not in body]
        out[zone] = {'program': name, 'lines': lines, 'calling_point': points[name.lower()], 'factor': factor,
                     'threshold_ip': threshold, 'cap_ip': float(caps[0][2]), 'ft2': float(caps[0][4]),
                     'people': occ[0], 'people_zone': sensed[0], 'lights': actuator[0],
                     'allowance': bool(allowance), 'extra': extra}
    return out


def extra_condition(extra, model):
    """The extra condition of a zone's program as one expression, with the sensors it reads."""
    conditions = [re.sub(r'^(ELSE)?IF ', '', l) for l in extra if l.startswith(('IF ', 'ELSEIF '))]
    if not conditions or any(not l.startswith(('IF ', 'ELSEIF ', 'SET ', 'ELSE', 'ENDIF')) for l in extra):
        raise ValueError(f'Unexpected extra lines {extra}')
    out = {'condition': conditions[0] if len(conditions) == 1 else ' || '.join(f'({c})' for c in conditions)}
    sensors = {f[0]: (f[1], f[2]) for f in model.all('energymanagementsystem:sensor')}
    used = sorted(s for s in sensors if any(re.search(rf'\b{s}\b', c) for c in conditions))
    if used:
        out['sensors'] = {s: f'{sensors[s][1]} of {sensors[s][0]}' for s in used}
    return out


def header(path):
    text = Path(path).read_text(errors='replace')
    found = re.search(r'LPD_Ctrl *= *([0-9.]+)', text)
    return found[1] if found else None


def program_rule(models, zones_, per_city):
    """The record of one program's zones, from the rules read in every location."""
    found = {city: {z: r for z, r in read.items() if z in zones_} for city, read in per_city.items()}
    comparable = {c: {z: {k: v for k, v in r.items() if k != 'program'} for z, r in f.items()} for c, f in found.items()}
    base = same_everywhere(comparable, f'{models.building_type} {models.template} rule in {zones_}')
    names = [models.name(z) for z in zones_]
    if not base:
        return None, names, {}
    forms = {(r['factor'], r['threshold_ip'], r['cap_ip'], r['ft2'], r['calling_point'], r['allowance'],
              r['people_zone'] == z) for z, r in base.items()}
    if len(forms) != 1:
        raise ValueError(f'{models.building_type} {zones_}: several rule forms {forms}')
    factor, threshold, cap, ft2, point, allowance, own = forms.pop()
    if (factor, threshold, cap, ft2) != (0.093, 0.02, 0.02, FT2):
        raise ValueError(f'{models.building_type}: unexpected constants {(factor, threshold, cap, ft2)}')
    rule = {'cap_W_m2': cap/ft2, 'lighting_threshold_W_m2': threshold/factor,
            'source_values': {'cap': cap, 'threshold': threshold, 'unit': 'W/ft2', 'cap_conversion_m2_per_ft2': ft2,
                              'threshold_conversion_m2_per_ft2': factor},
            'comparison': 'zone_lighting_power_density_at_least_threshold', 'action': 'set_lights_to_cap',
            'calling_point': point, 'zones': len(zones_), 'controlled_zones': len(base)}
    if own:
        rule['condition'] = 'zone_occupant_count_zero'
    else:
        sensed = {models.geometry[r['people_zone']]['name'] for r in base.values()}
        if len(sensed) != 1:
            raise ValueError(f'{models.building_type} {zones_}: occupancy read from {sensed}')
        rule['condition'] = 'other_zone_occupant_count_zero'
        rule['condition_zone'] = sensed.pop()
    if allowance:
        rule['additional_lighting_when_capped_W_m2'] = 0.0
    exceptions = [{'zone': models.name(z), **extra_condition(r['extra'], models.base)} for z, r in sorted(base.items()) if r['extra']]
    if exceptions:
        rule['zone_conditions'] = exceptions
    programs = {found[BASE_CITY][z]['program']: found[BASE_CITY][z]['lines'] for z in sorted(base)}
    return rule, names, programs


def build_2019(extract):
    records, scan = [], Counter()
    for pnnl in TYPES:
        models = Models(extract, pnnl, YEAR)
        per_city = {city: rules(model) for city, model in models.models.items()}
        ctrl = same_everywhere({c: header(m.path) for c, m in models.models.items()}, f'{pnnl} LPD_Ctrl')
        scan['models'] += len(models.models)
        scan['with_rule'] += sum(bool(r) for r in per_city.values())
        for space_type, zones_ in sorted(models.groups.items()):
            rule, names, programs = program_rule(models, zones_, per_city)
            if rule:
                locator = f'EnergyManagementSystem:Program {", ".join(sorted(programs))}'
                note = INTERPRETATION
                value, unit = programs, 'EMS lines (W, m2, W/ft2)'
            else:
                anywhere = bool(per_city[BASE_CITY])
                locator = f'EnergyManagementSystem:Program (none acting on the Lights of zones {", ".join(names)})'
                value, unit = {'LPD_Ctrl_header': ctrl, 'zones': names, 'rule_in_other_zones_of_the_model': anywhere}, None
                note = (('The PNNL ASHRAE 90.1-2019 prototype has the unoccupied lighting cap in other zones but in none of these '
                         'zones: none (a source zero for this program).') if anywhere else
                        ('The PNNL ASHRAE 90.1-2019 prototype of this type has no unoccupied lighting cap program in any zone '
                         f'(header LPD_Ctrl = {ctrl}): none (a source zero).'))
            evidence = {'source_file_id': models.file, 'locator': locator, 'original_value': value, 'original_unit': unit,
                        'transformation': TRANSFORMATION if rule else 'absence of the EMS program in the complete model',
                        'extraction_date': EXTRACTION_DATE, 'interpretation': note}
            records.append({'template': models.template, 'building_type': models.building_type, 'space_type': space_type,
                            'zones': names, 'rule': rule, 'evidence': evidence})
    return records, dict(scan)


def scan_template(extract, family, prefix, year, template):
    """The absence of the rule in every model of one PNNL template, with one cited file."""
    root = extract.root/family
    models = with_rule = 0
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith(prefix+'_')):
        for city in CITIES:
            path = folder/f'{folder.name}_STD{year}_{city}.idf'
            models += 1
            if b'_occ_sensor' in path.read_bytes().lower():   # parse only a file that could hold the rule
                with_rule += bool(rules(idf_reader.Model(path)))
    if with_rule or models != 16*len(CITIES):
        raise ValueError(f'{template}: {with_rule} of {models} models have the unoccupied lighting cap')
    cited = root/f'{prefix}_OfficeMedium'/f'{prefix}_OfficeMedium_STD{year}_{BASE_CITY}.idf'
    source_file = extract.prototype_file(family, cited)
    return {'rule': None, 'scan': {'models': models, 'with_rule': 0}, 'evidence': {
        'source_file_id': source_file, 'locator': 'EnergyManagementSystem:Program (none acting on Lights)',
        'original_value': {'LPD_Ctrl_header': header(cited), 'models_scanned': models, 'with_rule': 0}, 'original_unit': 'count',
        'transformation': 'absence of the EMS program in every complete model of the template',
        'extraction_date': EXTRACTION_DATE,
        'interpretation': f'No PNNL {template} prototype (16 types x 19 locations) has an unoccupied lighting cap program (the '
                          f'medium office header gives LPD_Ctrl = {header(cited)}): none (a source zero).'}}


def scan_doe(extract, idf_root):
    """No DOE reference model has an EMS program; one cited file per atlas DOE Ref template."""
    counts, cited, out = Counter(), {}, {}
    for path in sorted(Path(idf_root).glob('*/*.idf')):
        vintage = next((v for v in DOE_TEMPLATES if f'_{v}_' in path.parent.name), 'new2004')
        counts[vintage] += 1
        if b'energymanagementsystem:' in path.read_bytes().lower():
            raise ValueError(f'{path.name} has EMS programs; ADR 0060 records none for DOE Ref')
        if vintage in DOE_TEMPLATES and vintage not in cited and 'mediumoffice' in path.parent.name and '5A' in path.name:
            cited[vintage] = extract.doe_file(path, idf_root)
    for vintage, template in DOE_TEMPLATES.items():
        out[template] = {'rule': None, 'scan': {'models': counts[vintage], 'with_rule': 0}, 'evidence': {
            'source_file_id': cited[vintage], 'locator': 'EnergyManagementSystem:Program (none)',
            'original_value': {'models_scanned': counts[vintage], 'with_ems_programs': 0}, 'original_unit': 'count',
            'transformation': 'absence of any EMS program in every complete model of the vintage',
            'extraction_date': EXTRACTION_DATE,
            'interpretation': f'No DOE Commercial Reference Building {vintage} model (16 types x 16 locations) has an EMS program, so '
                              'none caps unoccupied lighting: none (a source zero).'}}
    return out


def build(root=None, idf_root=None):
    extract = Extract(root)
    records, scan = build_2019(extract)
    templates = {}
    for year in ('2007', '2013'):
        templates[f'90.1-{year}'] = scan_template(extract, FAMILY, 'ASHRAE901', year, f'ASHRAE 90.1-{year}')
    for edition in EDITIONS:
        templates[f'IECC {edition}'] = scan_template(extract, 'commercial-iecc', 'IECC', edition, f'IECC {edition}')
    templates.update(scan_doe(extract, Path(idf_root or doe_root())))
    for entry in [*records, *templates.values()]:
        row = entry.pop('evidence')
        entry['evidence_id'] = extract.cite(row['source_file_id'], row['locator'], row['original_value'], row['original_unit'],
                                            row['transformation'], row['interpretation'])
    rows = {k: {f: v for f, v in extract.evidence[k].items() if f != 'id'} for k in sorted(extract.evidence)}
    files = sorted({r['source_file_id'] for r in rows.values()})
    return {'schema_version': '1.0.0', 'decision': ADR, 'extraction_date': EXTRACTION_DATE,
            'description': 'The unoccupied lighting cap of the source models, per 90.1-2019 program and per template where no '
                           'model has it (release 2.4.0).',
            'scan': {'90.1-2019': scan, **{t: e.pop('scan') for t, e in templates.items()}},
            'records': sorted(records, key=lambda r: (r['building_type'], r['space_type'])),
            'templates': dict(sorted(templates.items())), 'evidence': rows,
            'source_files': {k: {f: v for f, v in extract.source_files[k].items() if f != 'id'} for k in files}}


def encode(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False)+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = encode(build())
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.relative_to(ROOT)} differs from the source models; run python -m scripts.lighting_cap')
        print(f'{OUTPUT.relative_to(ROOT).as_posix()} reproduces from the source models')
        return
    OUTPUT.write_bytes(data)
    document = json.loads(data)
    capped = Counter(r['building_type'] for r in document['records'] if r['rule'])
    print(f'Wrote {OUTPUT.relative_to(ROOT).as_posix()}: {len(document["records"])} 90.1-2019 programs, {sum(capped.values())} with the '
          f'cap ({dict(capped)}); {len(document["templates"])} templates without it')


if __name__ == '__main__':
    main()
