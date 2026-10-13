"""Focused DHW source census, pilots and approved capped programs; no full v3 rebuild.

python -m scripts.validate_program_water_heating [--write]
"""
import argparse

from scripts.common import ROOT, dump_json
from scripts.definition_release import read_bundle
from scripts.definition_contract import canonical
from scripts.common import load_json
from scripts.program_water_heating import ProgramExporter, SOLAR, CAPPED_PROGRAMS, draw_heating_power

PILOTS = {'medium-office': 'program-8c35a40eb0181596e0bfcac4',
          'residential': 'program-0079ce7b163bdb1bd0154dbe',
          'shared-large-office': 'program-0c7698c80e7049e6280f5373',
          'mixed-hotel': 'program-2497c6a2f0f3d35066d45e8c',
          'small-hotel-laundry-2019': 'program-4693cf50f9561a3d33c1823a',
          'small-hotel-support-2019': 'program-41d7c15eaedaab29da77780b'}


def check_temperature(recipe, target, kind, identity, capped):
    result = draw_heating_power(0, target, 0, recipe['stages'], density_kg_m3=1, specific_heat_J_kg_K=1,
                               delivery_policy=recipe.get('delivery_policy'))
    if recipe.get('delivery_policy'):
        capped.append({'kind': kind, 'id': identity, 'demand_id': recipe['demand_id'],
                       'requested_temperature_degC': target,
                       'source_outlet_temperature_degC': recipe['stages'][-1]['outlet_temperature_degC'],
                       'unmet_target_K_at_or_below_source_outlet': result['unmet_target_K'],
                       'policy': recipe['delivery_policy']['method']})


def census(exporter):
    issues, recipes, leaf_demands, residential_demands = [], 0, 0, 0
    capped = []
    attached = {k for p in exporter.base.programs.values() for k in p.get('service_ids', [])}
    detached = []
    for service in exporter.base.services.values():
        try:
            recipe = exporter.recipe({'id': 'service-census'}, service['load'], service['id'])
            target = service['load'].get('target_temperature_degC')
            if target is not None:
                check_temperature(recipe, target, 'service', service['id'], capped)
            recipes += 1
        except (ValueError, KeyError) as exc:
            issues.append({'kind': 'service', 'id': service['id'], 'issue': str(exc)})
        if service['id'] not in attached:
            detached.append({'id': service['id'], 'building_type': service['building_type'],
                             'template': service['template'], 'channel': service['end_use']})
    # Source/context joins, not a claim that all v4 defaulted program exports
    # were rebuilt. Composition identity/scaling is checked by the mixed pilot.
    for source in exporter.base.programs.values():
        if source.get('composition_id') or source['id']==SOLAR:
            continue
        if source.get('scope') == 'whole_dwelling':
            heater = exporter.stage(exporter.residential[source['source_id']])
            for load in exporter.base.recovery[source['source_id']]['loads']:
                if load['type']=='water' and load['value']>0:
                    residential_demands += 1
                    try:
                        draw_heating_power(0, load['target_temperature_degC'], 0, [heater], density_kg_m3=1, specific_heat_J_kg_K=1)
                    except ValueError as exc:
                        issues.append({'kind': 'residential_demand', 'id': source['id'], 'end_use': load['end_use'], 'issue': str(exc)})
        else:
            for draw in source['loads']:
                if draw['quantity'].startswith('hot_water') and draw.get('value') is not None and draw['value']>0:
                    leaf_demands += 1
                    try:
                        recipe = exporter.recipe(source, draw)
                        target = draw.get('target_temperature_degC', 60)
                        check_temperature(recipe, target, 'commercial_demand', source['id'], capped)
                    except (ValueError, KeyError) as exc:
                        issues.append({'kind': 'commercial_demand', 'id': source['id'], 'demand_id': draw['demand_id'], 'issue': str(exc)})
    validated_capped = []
    for p in exporter.base.programs.values():
        if p['id'] in CAPPED_PROGRAMS or any(o['id'] in CAPPED_PROGRAMS for o in exporter.origins(p['id']).values()):
            try:
                out = exporter.export(p['id'])
                validated_capped.append({'id': p['id'], 'name': p['name'], 'template': p['template'],
                    'capped_recipes': sum(bool(r.get('delivery_policy')) for r in out['water_heating']),
                    'validation': 'passed'})
            except (ValueError, KeyError) as exc:
                issues.append({'kind': 'capped_program', 'id': p['id'], 'issue': str(exc)})
    return {'commercial_heater_channels': len(exporter.conversions),
        'commercial_source_resolved_channels': sum(r['status']=='known' for r in exporter.conversions.values()),
        'residential_heaters_with_source_conversion': len(exporter.residential),
        'included_residential_fixtures': len(exporter.residential)-1,
        'skipped_solar_program': SOLAR,
        'commercial_service_recipes_checked': recipes,
        'commercial_leaf_draw_joins_checked': leaf_demands,
        'residential_draw_temperature_checks': residential_demands,
        'known_blocked_temperature_cases': [],
        'potentially_blocked_programs': [],
        'capped_temperature_cases': capped,
        'validated_capped_programs': validated_capped,
        'unexpected_unresolved': issues,
        'services_without_existing_program_attachment': detached,
        'validation_scope': 'All heater conversion/source joins and source draw temperatures; six complete program pilots and all 15 approved capped leaf/mixture exports. No full v3/v4 library regeneration, simulation or site build.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write', action='store_true', help='Write tracked pilots and coverage report')
    mode.add_argument('--check', action='store_true', help='Compare regenerated pilots/report with tracked artifacts')
    args = parser.parse_args()
    exporter = ProgramExporter(read_bundle(ROOT/'data/definition-releases/v0.1.1'))
    report = census(exporter)
    report['pilots'] = {}
    for name, pid in PILOTS.items():
        out = exporter.export(pid)
        report['pilots'][name] = {'program_id': pid, 'water_heating_recipes': len(out['water_heating']), 'validation': 'passed'}
        if args.write:
            dump_json(ROOT/f'docs/examples/program-json-v4/{name}.json', out)
        elif args.check and canonical(out) != canonical(load_json(ROOT/f'docs/examples/program-json-v4/{name}.json')):
            raise SystemExit('DHW pilot differs: '+name)
    if args.write:
        dump_json(ROOT/'docs/reviews/program-water-heating-coverage.json', report)
    elif args.check and canonical(report) != canonical(load_json(ROOT/'docs/reviews/program-water-heating-coverage.json')):
        raise SystemExit('DHW coverage report differs')
    print({k:v for k,v in report.items() if k not in {'services_without_existing_program_attachment','known_blocked_temperature_cases','potentially_blocked_programs','unexpected_unresolved','pilots','capped_temperature_cases','validated_capped_programs'}})
    print('Approved capped cases:', len(report['capped_temperature_cases']), '; complete affected exports:', len(report['validated_capped_programs']))
    print('Source services requiring a separate consumer attachment:', len(report['services_without_existing_program_attachment']))
    if report['unexpected_unresolved']:
        print(report['unexpected_unresolved'])
        raise SystemExit(1)


if __name__ == '__main__':
    main()
