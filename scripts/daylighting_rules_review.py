"""Evidence report: the 90.1 daylighting records against the openstudio-standards rules (plan stage B2, L-2).

python -m scripts.daylighting_rules_review           # write docs/reviews/daylighting-rules-90-1.md
python -m scripts.daylighting_rules_review --check   # fail if the report differs

The 90.1 `lighting_controls` records of release 2.0.0 come from the PNNL prototypes (ADR 0044
agent decision 1). openstudio-standards builds the same controls at run time; its rules at the
pinned revision (sources/daylighting-rules-lock.json, with the space-type tables of
sources/lock.json) are compared with the records where they need no geometry:
- whether a template requires controls at all (the base rule requires none; 90.1-2010 on
  overrides it);
- the control settings: type, stepped-control steps, minimum input-power and light-output
  fractions;
- the illuminance setpoint: the space-type table's target, 375 lux where it gives none, and no
  controls where it says `na`;
- the office whole-building programs: the controlled fraction within the non-geometry caps
  (primary plus secondary sidelit share).
Which zones get controls and the controlled fractions follow from window geometry (daylit areas,
the 150 W and 300 W and 20 ft² thresholds) and are not recomputed here. Values do not change.
"""
import argparse
import json
from collections import Counter, defaultdict

from scripts import atlas_snapshot
from scripts.common import ROOT, load_json

REPORT = ROOT/'docs/reviews/daylighting-rules-90-1.md'
RAW = ROOT/'data/raw/openstudio-standards'
LIB = 'lib/openstudio-standards/standards'
# What each template's rules state, with the source lines that state it; the lines are checked in the pinned files.
RULES = {
    '90.1-2007': {'required': False, 'evidence': [(f'{LIB}/Standards.Space.rb', 'req_top_ctrl = false')]},
    '90.1-2013': {'required': True, 'control_type': 'stepped', 'steps': 3, 'minimum_input_power_fraction': 0.3,
                  'evidence': [(f'{LIB}/ashrae_90_1/ashrae_90_1_2013/ashrae_90_1_2013.Space.rb', 'req_top_ctrl = true'),
                               (f'{LIB}/Standards.Space.rb', "return 'Stepped'"),
                               (f'{LIB}/Standards.Space.rb', 'return 0.3'),
                               (f'{LIB}/Standards.Space.rb', "setNumberofSteppedControlSteps(3) unless space_daylighting_control_type(space) != 'Stepped'")]},
    '90.1-2019': {'required': True, 'control_type': 'continuous_off', 'minimum_input_power_fraction': 0.2,
                  'evidence': [(f'{LIB}/ashrae_90_1/ashrae_90_1_2019/ashrae_90_1_2019.Space.rb', 'req_top_ctrl = true'),
                               (f'{LIB}/ashrae_90_1/ashrae_90_1_2019/ashrae_90_1_2019.Space.rb', "return 'ContinuousOff'"),
                               (f'{LIB}/ashrae_90_1/ashrae_90_1_2019/ashrae_90_1_2019.Space.rb', 'return 0.2')]},
}
COMMON = [(f'{LIB}/Standards.Space.rb', 'setMinimumLightOutputFractionforContinuousDimmingControl(0.2)'),
          (f'{LIB}/Standards.Space.rb', 'daylight_stpt_lux = 375'),
          (f'{LIB}/Standards.Space.rb', "if daylight_stpt_lux == 'na'"),
          (f'{LIB}/Standards.Space.rb', 'sensor_1_frac *= psa_nongeo_frac unless psa_nongeo_frac.nil?')]
TYPES = {'stepped': 'Stepped', 'continuous_off': 'ContinuousOff', 'continuous': 'Continuous'}


def check_sources():
    lock = {e['path']: e for e in load_json(ROOT/'sources/daylighting-rules-lock.json')['files']}
    for path, text in COMMON + [e for r in RULES.values() for e in r['evidence']]:
        if path not in lock:
            raise ValueError('Rule source not pinned: '+path)
        if text not in (RAW/path).read_text(encoding='utf-8'):
            raise ValueError(f'Rule no longer stated in {path}: {text}')


def space_types(template):
    year = template.split('-')[1]
    rows = load_json(RAW/f'{LIB}/ashrae_90_1/ashrae_90_1_{year}/data/ashrae_90_1_{year}.spc_typ.json')['space_types']
    return rows


def records(files):
    """(template, folder, program name, building type, lighting_controls block, climate) per 90.1 source program and climate."""
    out = []
    for path, data in sorted(files.items()):
        if not (path.startswith('commercial/90-1-') and '/programs/source/' in path):
            continue
        program = json.loads(data)
        block = program.get('lighting_controls')
        if not block or block['status'] != 'known':
            continue
        folder = path.split('/programs/')[0].split('/', 1)[1]
        out.append((program['template'], folder, program['name'], block, None, block.get('daylighting')))
        for climate, value in sorted((block.get('daylighting_by_climate') or {}).items()):
            out.append((program['template'], folder, program['name'], block, climate, value))
    return out


def review(files):
    check_sources()
    findings, counts = defaultdict(list), Counter()
    caps = {}
    for template in RULES:
        for row in space_types(template):
            if row.get('psa_nongeometry_fraction') is not None:
                caps[(template, row['space_type'])] = (row['psa_nongeometry_fraction'] or 0) + (row['ssa_nongeometry_fraction'] or 0)
    for template, folder, name, block, climate, value in records(files):
        rule = RULES[template]
        where = f'`{folder}` {name}' + (f' ({climate})' if climate else '')
        counts[(template, 'with controls' if value else 'without controls')] += 1
        standards = block.get('standards_rule') or {}
        if not value:
            continue
        if not rule['required']:
            findings['controls the template does not require'].append(where)
            continue
        if value['control_type'] != rule['control_type']:
            findings['control type'].append(f"{where}: {value['control_type']}, rule {rule['control_type']}")
        if rule.get('steps') and value.get('stepped_control_steps') != rule['steps']:
            findings['stepped-control steps'].append(f"{where}: {value.get('stepped_control_steps')}, rule {rule['steps']}")
        if value['minimum_input_power_fraction'] != rule['minimum_input_power_fraction']:
            findings['minimum input-power fraction'].append(f"{where}: {value['minimum_input_power_fraction']}, rule {rule['minimum_input_power_fraction']}")
        if value['minimum_light_output_fraction'] != 0.2:
            findings['minimum light-output fraction'].append(f"{where}: {value['minimum_light_output_fraction']}, rule 0.2")
        if standards:
            if standards.get('daylighting_appropriate') is False:
                findings['controls where the space type says `na`'].append(where)
            else:
                target = standards.get('target_illuminance_setpoint_lux')
                kind = 'illuminance setpoint' if target else 'illuminance setpoint against the 375 lux default (no space-type target)'
                target = target or 375.0
                if abs(value['illuminance_setpoint_lux'] - target) > 0.5:
                    findings[kind].append(f"{where}: {value['illuminance_setpoint_lux']:g} lux, rule {target:g} lux")
        else:
            counts[(template, 'without a space-type rule')] += 1
        space_type = name.rsplit('_', 1)[0]
        if space_type.startswith('WholeBuilding') and (template, space_type) in caps:
            cap = caps[(template, space_type)]
            counts[(template, 'office caps checked')] += 1
            if value['controlled_lighting_fraction'] > cap + 1e-3:
                findings['office fraction above the non-geometry caps'].append(
                    f"{where}: {value['controlled_lighting_fraction']:g}, caps sum {cap:g}")
    return findings, counts


def report(findings, counts):
    lines = ['# 90.1 daylighting records vs the openstudio-standards rules', '',
             'Evidence only (plan stage B2, user decision L-2). Generated by `python -m scripts.daylighting_rules_review` '
             'from release 2.0.0 and the openstudio-standards rules at the pinned revision '
             '(`sources/daylighting-rules-lock.json`); no value changes.', '',
             '## What is compared', '',
             '- **Records:** the `lighting_controls` of every 90.1 source program with a known record, and its '
             '`daylighting_by_climate` variants. They come from the PNNL prototypes (ADR 0044 agent decision 1).',
             '- **Rules:** whether the template requires controls (`space_daylighting_control_required?`), the control '
             'type, stepped-control steps, minimum input-power and light-output fractions, and the illuminance setpoint '
             '(the space-type target, 375 lux where none, no controls where `na`).',
             '- **Office whole-building programs:** the controlled lighting fraction against the non-geometry caps '
             '(`psa_nongeometry_fraction` plus `ssa_nongeometry_fraction`).',
             '- **Not compared:** which zones get controls and the controlled fractions otherwise. They follow from the '
             'window geometry (daylit areas, the 150 W, 300 W and 20 ft² thresholds) and are geometry-dependent.', '',
             '| Template | Rule | Records with controls | Records without | Office caps checked |', '| --- | --- | ---: | ---: | ---: |']
    for template, rule in RULES.items():
        text = ('no controls required' if not rule['required'] else
                f"{TYPES[rule['control_type']]}" + (f", {rule['steps']} steps" if rule.get('steps') else '')
                + f", minimum input power {rule['minimum_input_power_fraction']:g}, light output 0.2")
        lines.append(f"| {template} | {text} | {counts[(template, 'with controls')]} | {counts[(template, 'without controls')]} | "
                     f"{counts[(template, 'office caps checked')]} |")
    lines += ['', '## Findings', '']
    if not findings:
        lines.append('Every compared field agrees with the rules.')
    for kind in sorted(findings):
        items = findings[kind]
        lines.append(f'**{kind}** ({len(items)}):')
        lines.append('')
        lines += [f'- {i}' for i in items]
        lines.append('')
    lines += ['## Reading', '',
              '- The PNNL prototypes and openstudio-standards are separate implementations of the same code rules; a '
              'difference here is a difference between the two sources, not an atlas error. The records keep the PNNL '
              'values (ADR 0044); this report is evidence for a consumer choosing between them.',
              '- `stepped_control_steps` matters only for stepped control. The 2019 records carry the IDF field, which '
              'continuous-off control ignores.', '']
    return ('\n'.join(lines).rstrip('\n')+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = report(*review(atlas_snapshot.files()))
    if args.check:
        if REPORT.read_bytes() != data:
            raise SystemExit('Daylighting review is stale; rerun python -m scripts.daylighting_rules_review')
    else:
        REPORT.write_bytes(data)
    print(f'Daylighting rules review {"matches" if args.check else "written"}: {REPORT.relative_to(ROOT).as_posix()}')


if __name__ == '__main__':
    main()
