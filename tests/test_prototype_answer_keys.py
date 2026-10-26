"""Answer keys: the IECC residential and manufactured-housing release files against their source IDFs.

Set ATLAS_PROTOTYPE_ROOT to the folder holding the extracted `residential/resstd_AllCodes`
and `manufactured-housing/<location>_{HUD,FinalRule}` models (sources/reference-models-lock.json);
the tests skip otherwise. Samples (user decision G4): every IECC edition in climate codes 4A and
1AWH, all types, heating systems and foundations; every manufactured-housing location under the
HUD Code. Tolerances follow ADR 0035: values and hourly fractions 1e-6, annual totals 0.01 %.
"""
import json
import math
import os
import unittest
from pathlib import Path

from scripts import idf_reader, idf_schedules
from scripts.idf_schedules import calendar_days

ROOT = os.environ.get('ATLAS_PROTOTYPE_ROOT')
DAYS = calendar_days([])
TOLERANCE = 1e-6


def close(a, b, tolerance=TOLERANCE):
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance)


@unittest.skipUnless(ROOT and Path(ROOT, 'residential', 'resstd_AllCodes').is_dir()
                     and Path(ROOT, 'manufactured-housing').is_dir(),
                     'set ATLAS_PROTOTYPE_ROOT to the extracted PNNL prototype models')
class PrototypeAnswerKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import prototype_dwellings
        from scripts.residential_storage import program_files
        cls.files = prototype_dwellings.build()
        cls.programs = program_files(cls.files)
        cls.sets = {json.loads(d)['id']: json.loads(d) for p, d in cls.files.items()
                    if p.startswith('residential/') and '/constructions/' in p}

    def folder_programs(self, folder):
        return [p for f, p in self.programs.values() if f == folder]

    def schedule_values(self, folder, schedule_id):
        table = json.loads(self.files[folder+'schedules.json'])
        rules = table['schedules'][schedule_id]['rules']
        return idf_schedules.evaluate_ruleset(rules, lambda r: table['days'][r['day']] * (24 // len(table['days'][r['day']])), DAYS)

    def assertSchedule(self, folder, schedule_id, model, name, label):
        checked = model.__dict__.setdefault('_answer_keys', set())
        if (folder, schedule_id, name) in checked:
            return
        checked.add((folder, schedule_id, name))
        got = self.schedule_values(folder, schedule_id)
        expected = model.schedules.evaluate(name, DAYS)
        for key in DAYS:
            self.assertTrue(idf_schedules.same(expected[key], got[key]), f'{label}: {name} on {key}')
        total = lambda values: sum(sum(v) for k, v in values.items() if k[0].isdigit())
        self.assertTrue(close(total(got), total(expected), 1e-4), f'{label}: annual total of {name}')

    def check_model(self, path, folder, program, context, label):
        """Every load of the model has one stored entry that holds in its context, and back."""
        from scripts.prototype_dwellings import select
        from scripts.prototype_extract import Model
        from scripts.prototype_programs import object_unit, quantity
        model = Model(path)
        loads = select(program['loads'], context)
        services = select(program['services'], context)
        seen = {}
        for load in model.loads():
            unit = load['unit'] or (object_unit(load['object']) if load['zone'] is None else None)
            pool = loads if unit else services
            key = (load['class'], quantity(load['stem']), load['zone'])
            matches = [e for e in pool if (e['source_class'], e['quantity'], e['host_zone'] if e['type'] != 'exterior_lighting'
                                           else None) == key]
            self.assertEqual(len(matches), 1, f'{label}: {key}')
            entry = matches[0]
            seen[id(entry)] = entry
            self.assertTrue(close(entry['value'], load['value']), f'{label}: {key} value')
            if 'fractions' in load:
                for name, value in load['fractions'].items():
                    self.assertTrue(close(entry['fractions'][name], value), f'{label}: {key} {name}')
            schedule = model.reader.all(load['class'])
            source = next(f for f in schedule if f[0] == load['object'])
            name = source[1] if load['class'] == 'exterior:lights' else source[3] if load['class'] == 'wateruse:equipment' else source[2]
            self.assertSchedule(folder, entry['schedule_id'], model, name, f'{label} {key}')
        self.assertEqual(len(seen), len(loads) + len(services), f'{label}: stored entries without a source load')
        [thermostat] = select(program['controls'], context)
        [control] = [c for c in model.thermostats() if c['unit']][:1]
        self.assertSchedule(folder, thermostat['heating_setpoint_schedule_id'], model, control['heating']['name'], label)
        self.assertSchedule(folder, thermostat['cooling_setpoint_schedule_id'], model, control['cooling']['name'], label)
        return model

    def check_envelope(self, model, construction, key, tslug, label):
        """Assemblies carry the source layer U-factor and glazing properties; areas and leakage match."""
        context = construction['contexts'][key]
        library = json.loads(self.files[f'residential/{tslug}/library/assemblies.json'])
        reader = idf_reader.Model(model.reader.path)
        materials = reader.materials()
        constructions = reader.constructions()
        checked = 0
        for part in ('components', 'windows', 'doors', 'internal_mass'):
            for item in context[part]:
                assembly = library[item['assembly_id']]
                resistance = reader.layer_resistance(assembly['name'])
                if resistance:
                    self.assertTrue(close(assembly['layer_u_factor_W_m2_K'], 1/resistance), f'{label}: {assembly["name"]} U')
                    checked += 1
                layers = constructions[assembly['name'].lower()]['layers']
                glazing = [materials[m] for m in layers if materials.get(m, {}).get('kind') == 'simple_glazing']
                if glazing:
                    self.assertTrue(close(assembly['u_factor_W_m2_K'], glazing[0]['u_factor']), f'{label}: window U')
                    self.assertTrue(close(assembly['solar_heat_gain_coefficient'], glazing[0]['shgc']), f'{label}: SHGC')
                    checked += 1
        self.assertGreater(checked, 3, label)
        leakage = sum(r['effective_air_leakage_area_cm2'] for r in context['infiltration'].get('effective_leakage_area', []))
        source = sum(idf_reader.number(f[3]) for f in reader.all('zoneinfiltration:effectiveleakagearea'))
        self.assertTrue(close(leakage, source), f'{label}: effective leakage area')
        network = context['infiltration'].get('airflow_network', {}).get('components', [])
        source = {f[0]: idf_reader.number(f[1]) for f in reader.all('airflownetwork:multizone:surface:effectiveleakagearea')}
        self.assertEqual({c['name']: c['effective_leakage_area_m2'] for c in network}, source, f'{label}: AFN leakage')

    def test_iecc_residential_every_edition_in_4a_and_1awh(self):
        from scripts import iecc_residential, prototype_dwellings
        root = Path(ROOT, 'residential')
        checked = 0
        for edition in iecc_residential.EDITIONS:
            for path, code, climate, heating, foundation in iecc_residential.models(root, edition):
                if climate not in ('4A', '1AWH'):
                    continue
                building_type = iecc_residential.TYPES[code]
                tslug, bslug = f'iecc-{edition}', prototype_dwellings.TYPE_FOLDERS[building_type]
                folder = f'residential/{tslug}/{bslug}/'
                [program] = [p for p in self.folder_programs(folder) if heating in p['variant']['heating']]
                context = {'climate': climate, 'foundation': foundation, 'heating': heating}
                label = path.name
                model = self.check_model(path, folder, program, context, label)
                construction = self.sets[program['construction_set_id']]
                key = f'{prototype_dwellings.slug(climate)}.{foundation}'
                self.check_envelope(model, construction, key, tslug, label)
                checked += 1
        self.assertEqual(checked, 7 * 2 * 2 * 16)

    def test_manufactured_housing_every_location_under_hud(self):
        from scripts import manufactured_housing, prototype_dwellings
        root = Path(ROOT, 'manufactured-housing')
        found = manufactured_housing.models(root)
        cities = {}
        for _, _, city, climate, _, _ in found:
            cities.setdefault(climate, set()).add(city)
        checked = 0
        for path, section, city, climate, standard, heating in found:
            if standard != 'HUD':
                continue
            building_type = manufactured_housing.SECTIONS[section]
            folder = f'residential/hud-code/{prototype_dwellings.TYPE_FOLDERS[building_type]}/'
            [program] = self.folder_programs(folder)
            context = {'climate': climate, 'location': city, 'heating': heating}
            model = self.check_model(path, folder, program, context, path.name)
            construction = self.sets[program['construction_set_id']]
            self.check_envelope(model, construction, manufactured_housing.context_key(climate, city, cities), 'hud-code', path.name)
            checked += 1
        self.assertEqual(checked, 19 * 2 * 4)


if __name__ == '__main__':
    unittest.main()
