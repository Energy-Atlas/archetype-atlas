"""Opt-in Program JSON 4: source-backed draw-only fuel energy recipes.

python -m scripts.program_water_heating --program PROGRAM_ID --output FILE
No fixed climate, fluid properties, geometry or annual energy is assumed.
"""
import argparse
import copy
import math
import hashlib
from collections import Counter

from jsonschema import Draft202012Validator

from scripts.common import ROOT, load_json, dump_json
from scripts.definition_contract import stable_id
from scripts.definition_release import read_bundle
from scripts.program_json_v3 import ProgramExporter as V3Exporter

SOLAR = 'program-1a9bafb870d938bc1ff6a0ee'
CAPPED_SERVICES = frozenset({'service-0b40d91aad2dfcc14415d797', 'service-1ddcebc06abc0a3b5240f918',
                             'service-d3d5674fbfeb86395d91631d'})
CAPPED_PROGRAMS = frozenset({'program-48033f4bc7ec6fc7b024e233', 'program-ddd1850c0fa5cbf5282f50c0',
                             'program-4693cf50f9561a3d33c1823a'})
EXCLUSIONS = ['standby_losses', 'heater_auxiliaries', 'pilot_consumption', 'solar_credit']
FUEL = {'electricity': 'electricity', 'natural gas': 'natural gas', 'propane': 'propane',
        'fuel oil': 'fuel oil', 'wood': 'wood', 'coal': 'coal'}


def positive(value, label, zero=False):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0 or (not zero and value == 0):
        raise ValueError('Invalid '+label)
    return value


def draw_heating_power(flow_m3_s, target_degC, mains_degC, stages, *, density_kg_m3, specific_heat_J_kg_K,
                       delivery_policy=None):
    """Instantaneous absolute W after consumer scaling and schedule evaluation.

    For mixed draws below the heater outlet, hot-water mixing cancels the extra
    tank temperature lift. Stage lifts stop at the delivered draw temperature.
    The main preheats booster draws; it never heats that draw from mains twice.
    """
    positive(flow_m3_s, 'flow', zero=True)
    positive(density_kg_m3, 'water density')
    positive(specific_heat_J_kg_K, 'water specific heat')
    if not all(isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t) for t in (target_degC, mains_degC)):
        raise ValueError('Invalid water temperature')
    if not stages:
        raise ValueError('Missing conversion stages')
    previous_outlet = -math.inf
    for stage in stages:
        eta = positive(stage.get('conversion_efficiency'), 'conversion efficiency')
        if eta > 1 or stage.get('fuel') not in FUEL:
            raise ValueError('Invalid fuel/conversion efficiency')
        outlet = stage.get('outlet_temperature_degC')
        if not isinstance(outlet, (int, float)) or not math.isfinite(outlet) or outlet <= previous_outlet:
            raise ValueError('Invalid stage temperature order')
        previous_outlet = outlet
    if delivery_policy is not None and (delivery_policy.get('method') != 'cap_at_source_outlet'
                                       or delivery_policy.get('report_unmet_target') is not True):
        raise ValueError('Unsupported water delivery policy')
    if target_degC > previous_outlet + 1e-8 and delivery_policy is None:
        raise ValueError('Draw target exceeds source heater outlet; unresolved temperature semantics')
    delivery_target = min(target_degC, previous_outlet) if delivery_policy else target_degC
    capacity_rate = flow_m3_s*density_kg_m3*specific_heat_J_kg_K
    inlet = mains_degC
    fuel_input = {}
    for stage in stages:
        outlet = max(inlet, min(delivery_target, stage['outlet_temperature_degC']))
        heat = capacity_rate*(outlet-inlet)
        fuel = stage['fuel']
        fuel_input[fuel] = fuel_input.get(fuel, 0)+heat/stage['conversion_efficiency']
        inlet = outlet
    unmet = max(target_degC-inlet, 0)
    return {'delivered_heat_W': capacity_rate*max(delivery_target-mains_degC, 0), 'fuel_input_W': fuel_input,
            'requested_temperature_degC': target_degC, 'delivered_temperature_degC': inlet,
            'unmet_target_K': unmet, 'unmet_heat_W': capacity_rate*unmet}


def evaluate_recipe(recipe, flow_fraction, target_degC, mains_degC, bindings):
    """Evaluate a recipe after its embedded schedules/weather have been evaluated."""
    positive(flow_fraction, 'flow schedule fraction', zero=True)
    if flow_fraction > 1:
        raise ValueError('Flow schedule fraction exceeds one')
    draw = recipe['draw']
    binding = {'floor_area': 'floor_area_m2', 'dwelling_unit': 'dwelling_unit_count',
               'person': 'person_count', 'absolute': None}[draw['basis']]
    scale = positive(bindings[binding], 'draw scale', zero=True) if binding else 1
    return draw_heating_power(draw['value']*flow_fraction*scale, target_degC, mains_degC,
        recipe['stages'], density_kg_m3=bindings['water_density_kg_m3'],
        specific_heat_J_kg_K=bindings['water_specific_heat_J_kg_K'], delivery_policy=recipe.get('delivery_policy'))


class ProgramExporter:
    def __init__(self, bundle, conversions=None, systems=None):
        self.base = V3Exporter(bundle)
        self.validator = Draft202012Validator(load_json(ROOT/'schemas/program-json-v4.schema.json'))
        artifact = conversions if conversions is not None else load_json(ROOT/'data/program-inputs/dhw-conversion-v1.json')
        self.conversion_artifact = artifact
        self.conversions = artifact['records']
        self.systems = systems if systems is not None else load_json(ROOT/'data/system-inputs/source-v1.json')
        if systems is None and hashlib.sha256((ROOT/'data/system-inputs/source-v1.json').read_bytes()).hexdigest() != artifact['input_sha256']['data/system-inputs/source-v1.json']:
            raise ValueError('DHW recovery is stale relative to detailed system inputs')
        self.commercial = {}
        for key, row in self.conversions.items():
            c = row['source_context']
            selector = c['building_type'], c['template'], c['channel']
            if selector in self.commercial:
                raise ValueError('Ambiguous commercial heater '+repr(selector))
            self.commercial[selector] = key
        self.residential = {}
        for key, row in self.systems['water_heaters'].items():
            if row['role']=='water_heater' and key.startswith('recovered-equipment-'):
                sid = row['source_id']
                if sid in self.residential:
                    raise ValueError('Ambiguous residential heater '+sid)
                self.residential[sid] = key
        self._origins = {}
        lock = load_json(ROOT/'sources/dhw-conversion-evidence-lock.json')
        water_use = next(f for f in lock['files'] if f['path']=='src/EnergyPlus/WaterUse.cc')
        self.delivery_policy = {'method': 'cap_at_source_outlet', 'report_unmet_target': True,
            'decision': 'ADR 0018; user approved 2026-10-12',
            'evidence': {'source_project': 'EnergyPlus', 'source_revision': water_use['source_revision'],
                'source_locator': 'src/EnergyPlus/WaterUse.cc: CalcEquipmentFlowRates, lines 1041-1136',
                'source_file_sha256': water_use['sha256'],
                'original_value': 'TargetTemp >= HotTemp: all hot flow; actual mixed temperature and unmet-target warning',
                'original_unit': 'degC', 'transformation': 'Limit ideal draw delivery to final source outlet; retain requested target',
                'extraction_date': lock['retrieval_date'],
                'interpretation_note': 'Approved only for three SmallHotel main-loop laundry demands and their mixtures. '
                    'Source outlet is an ideal available supply; dynamic tank/capacity effects remain excluded.'}}

    def origins(self, program_id):
        """Join mixture identities without regenerating all v3 exports."""
        if program_id not in self._origins:
            source = self.base.programs[program_id]
            composition = self.base.compositions.get(source.get('composition_id'))
            result = {}
            if composition:
                for member in composition['members']:
                    for demand, origin in self.origins(member['program_id']).items():
                        identity = stable_id('mixed-demand', {'parent': program_id, 'member': member['program_id'], 'demand': demand})
                        result[identity] = origin
            else:
                for load in source['loads']:
                    if load['quantity'].startswith('hot_water'):
                        result[load['demand_id']] = source
            self._origins[program_id] = result
        return self._origins[program_id]

    def stage(self, heater_id):
        if heater_id in self.conversions:
            row = self.conversions[heater_id]
            if row['status'] != 'known':
                raise ValueError('Unresolved source conversion: '+heater_id)
            temperature = row['nominal_operands']['service_water_temperature']
            return {'heater_id': heater_id, 'fuel': row['fuel'], 'conversion_efficiency': row['conversion_efficiency'],
                'outlet_temperature_degC': temperature['value'], 'conversion_evidence': copy.deepcopy(row['evidence']),
                'temperature_evidence': copy.deepcopy(temperature['evidence']),
                'fuel_evidence': copy.deepcopy(row['nominal_operands']['water_heater_fuel']['evidence'])}
        row = self.systems['water_heaters'][heater_id]
        fields = row['fields']
        eta = fields['heating_input_conversion_efficiency']
        temperature = fields['temperature']
        if eta['status']!='known' or temperature['status']!='known':
            raise ValueError('Unresolved residential conversion/temperature: '+heater_id)
        fuel = fields['fuel_type']['value']
        if fuel not in FUEL:
            raise ValueError('Unsupported residential water-heating fuel: '+str(fuel))
        return {'heater_id': heater_id, 'fuel': FUEL[fuel], 'conversion_efficiency': eta['value'],
            'outlet_temperature_degC': temperature['value'], 'conversion_evidence': copy.deepcopy(eta['evidence']),
            'temperature_evidence': copy.deepcopy(temperature['evidence']),
            'fuel_evidence': copy.deepcopy(fields['fuel_type']['evidence'])}

    def recipe(self, source, draw, service_id=None):
        capped = False
        if source.get('scope') == 'whole_dwelling':
            stages = [self.stage(self.residential[source['source_id']])]
        else:
            service = self.base.services.get(service_id or draw['demand_id'])
            origin = service or self.origins(source['id']).get(draw['demand_id'])
            if origin is None:
                raise ValueError('Unresolved water demand origin: '+draw['demand_id'])
            capped = (service['id'] in CAPPED_SERVICES if service else
                      origin['id'] in CAPPED_PROGRAMS and
                      any(l['demand_id'] in CAPPED_SERVICES for l in origin['loads']
                          if l['quantity'].startswith('hot_water')))
            channel = service['end_use'] if service else 'main'
            channels = ['main', 'booster'] if channel == 'booster' else [channel]
            stages = []
            for role in channels:
                selector = origin['building_type'], origin['template'], role
                if selector not in self.commercial:
                    raise ValueError('Unresolved source heater selector: '+repr(selector))
                stages.append(self.stage(self.commercial[selector]))
        recipe = {'demand_id': draw['demand_id'], 'method': 'draw_only', 'draw': copy.deepcopy(draw),
            'stages': stages, 'output_unit': 'W', 'zone_heat_gains': 'excluded',
            'exclusions': EXCLUSIONS[:], 'ownership': 'instantiate_once' if service_id else 'per_program_instance',
            'service_id': service_id, 'alternative_to': 'explicit_equipment_heating_for_same_demand'}
        if capped:
            recipe['delivery_policy'] = copy.deepcopy(self.delivery_policy)
        return recipe

    def export(self, program_id):
        if program_id == SOLAR:
            raise ValueError('solar fixture out of scope for simplified water-heating energy: '+program_id)
        source = self.base.programs[program_id]
        out = self.base.export(program_id, 'defaulted')
        out['schema_version'] = '4.0.0'
        out['id'] += ':draw-only-v1'
        out['water_heating'] = []
        for load in out['loads']:
            if load['type']=='hot_water':
                out['water_heating'].append(self.recipe(source, load))
        out['loads'] = [l for l in out['loads'] if l['type']!='hot_water']
        for service in out['shared_services']:
            for load in service['loads']:
                if load['type']=='hot_water':
                    out['water_heating'].append(self.recipe(source, load, service['id']))
            service['loads'] = [l for l in service['loads'] if l['type']!='hot_water']
        out['shared_services'] = [s for s in out['shared_services'] if s['loads']]
        if out['water_heating']:
            out['required_bindings'] += ['water_density_kg_m3', 'water_specific_heat_J_kg_K']
        out['metadata']['water_heating'] = {'decision': 'ADR 0018', 'method': 'draw_only',
            'conversion_input': 'data/program-inputs/dhw-conversion-v1.json',
            'conversion_input_sha256': hashlib.sha256((ROOT/'data/program-inputs/dhw-conversion-v1.json').read_bytes()).hexdigest(),
            'system_input_sha256': self.conversion_artifact['input_sha256']['data/system-inputs/source-v1.json'],
            'solar_fixture': 'skipped; v3 and detailed source evidence retained',
            'fluid_properties': 'consumer inputs; no Atlas constant defaults',
            'double_counting': 'Use these fuel recipes OR explicit heater equipment for the same demand, never both.'}
        if 'dhw_distribution_and_system_effects' in out['metadata']['excluded_scope']:
            out['metadata']['excluded_scope'].remove('dhw_distribution_and_system_effects')
            out['metadata']['excluded_scope'] += ['dhw_distribution', 'standby_losses', 'heater_auxiliaries', 'pilot_consumption']
        errors = self.validate(out)
        if errors:
            raise ValueError(program_id+': '+'; '.join(errors[:6]))
        return out

    def validate(self, out):
        errors = [str(e.message) for e in self.validator.iter_errors(out)]
        if errors:
            return errors
        base = copy.deepcopy(out)
        base['schema_version'] = '3.0.0'
        recipes = base.pop('water_heating')
        base['required_bindings'] = [k for k in base['required_bindings'] if not k.startswith('water_')]
        expected_inventory = {}
        program_id = out['source']['program_id']
        if program_id == SOLAR:
            errors.append('solar fixture out of scope for simplified water-heating energy')
        try:
            original = self.base.export(program_id, 'defaulted')
            groups = [(None, original['loads'])] + [(s['id'], s['loads']) for s in original['shared_services']]
            for sid, loads in groups:
                for draw in loads:
                    if draw['type']=='hot_water':
                        expected_inventory[draw['demand_id']] = self.recipe(self.base.programs[program_id], draw, sid)
            if Counter(r['demand_id'] for r in recipes) != Counter(expected_inventory.keys()):
                errors.append('Water recipe inventory differs from active source demands')
            if Counter(r['service_id'] for r in recipes if r['service_id']) != Counter(
                    r['service_id'] for r in expected_inventory.values() if r['service_id']):
                errors.append('Shared water service inventory/ownership differs from source')
        except (KeyError, ValueError) as exc:
            errors.append('Unresolved original program water inventory: '+str(exc))
        # The unchanged v3 validator checks schedule coverage, provenance,
        # physical units, binding requirements and shared demand identities.
        for recipe in recipes:
            draw = recipe['draw']
            expected = expected_inventory.get(recipe['demand_id'])
            if expected != recipe:
                errors.append('Water recipe differs from source demand, assignment or ownership')
            elif any(out['schedules'].get(draw[k]) != original['schedules'].get(draw[k])
                     for k in ('schedule_id', 'target_temperature_schedule_id')):
                errors.append('Water schedule differs from original program schedule')
            if recipe['demand_id'] != draw['demand_id']:
                errors.append('Energy/draw demand identity mismatch')
            try:
                expected_recipe = self.recipe(self.base.programs[out['source']['program_id']], draw, recipe['service_id'])
                if expected_recipe['stages'] != recipe['stages']:
                    errors.append('Wrong heater/channel assignment for demand')
            except (KeyError, ValueError) as exc:
                errors.append('Unresolved source assignment: '+str(exc))
            for stage in recipe['stages']:
                try:
                    expected = self.stage(stage['heater_id'])
                except (KeyError, ValueError):
                    errors.append('Unknown/unresolved heater '+stage['heater_id'])
                    continue
                if expected != stage:
                    errors.append('Stage differs from recovered source performance')
            target = out['schedules'].get(draw['target_temperature_schedule_id'])
            if target is not None:
                values = target.get('values', []) if target['type']=='annual' else [v for r in target['rules'] for v in r['values']]
                try:
                    for value in set(values):
                        draw_heating_power(0, value, 0, recipe['stages'], density_kg_m3=1, specific_heat_J_kg_K=1,
                                           delivery_policy=recipe.get('delivery_policy'))
                except ValueError as exc:
                    errors.append(str(exc))
            sid = recipe['service_id']
            if sid:
                service = next((s for s in base['shared_services'] if s['id']==sid), None)
                if service is None:
                    service = {'id': sid, 'ownership': 'instantiate_once', 'host_assignment': 'consumer_selected_zone', 'loads': []}
                    base['shared_services'].append(service)
                service['loads'].append(draw)
            else:
                base['loads'].append(draw)
        if recipes and not {'water_density_kg_m3', 'water_specific_heat_J_kg_K', 'weather_file'} <= set(out['required_bindings']):
            errors.append('Missing water physics/weather bindings')
        errors.extend(self.base.validate(base))
        return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--program', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    exporter = ProgramExporter(read_bundle(ROOT/'data/definition-releases/v0.1.1'))
    dump_json(ROOT/args.output, exporter.export(args.program))
    print('Validated draw-only program export: '+args.program)


if __name__ == '__main__':
    main()
