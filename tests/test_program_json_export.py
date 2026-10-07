import copy
import importlib
import unittest

from scripts.common import ROOT
from scripts.definition_contract import canonical
from scripts.definition_release import read_bundle


class ProgramExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = read_bundle(ROOT / 'data/definition-releases/v0.1.1')
        cls.office = next(p for p in cls.bundle['programs'] if p['building_type'] == 'MediumOffice'
                          and p['template'] == '90.1-2019' and p['detail'] == 'SourcePrograms'
                          and p['evidence_view'] == 'reviewed' and 'plenum' not in p['name'].lower())

    def exporter(self, bundle=None):
        self.assertIsNotNone(importlib.util.find_spec('scripts.program_json'), 'Program exporter is missing')
        return importlib.import_module('scripts.program_json').ProgramExporter(bundle or self.bundle)

    def test_raw_preserves_unknowns_and_closes_schedules(self):
        exporter = self.exporter()
        raw = exporter.export(self.office['id'], 'raw')
        self.assertIsNone(next(l for l in raw['loads'] if l['end_use'] == 'additional_lighting')['value'])
        self.assertEqual(raw['assumptions'], [])
        self.assertTrue(all(l['schedule_id'] is None or l['schedule_id'] in raw['schedules'] for l in raw['loads']))
        self.assertEqual(exporter.validate(raw), [])

    def test_defaults_preserve_known_values_and_source_bundle(self):
        original = canonical(self.bundle)
        exporter = self.exporter()
        out = exporter.export(self.office['id'], 'defaulted')
        self.assertEqual(exporter.validate(out), [])
        for before in self.office['loads']:
            after = next(l for l in out['loads'] if l['demand_id'] == before['demand_id'])
            self.assertEqual(after['value'], before['value'] if before['value'] is not None else 0)
        lighting = next(l for l in out['loads'] if l['end_use'] == 'lighting')
        self.assertEqual(lighting['heat_fractions']['radiant'], .7)
        water = next(l for l in out['loads'] if l['type'] == 'hot_water')
        self.assertNotIn('Experimental default', out['schedules'][water['target_temperature_schedule_id']]['name'])
        self.assertNotEqual(out['id'], self.office['id'])
        self.assertTrue(out['assumptions'])
        self.assertEqual(canonical(self.bundle), original)
        out['loads'].clear()
        self.assertTrue(exporter.export(self.office['id'], 'defaulted')['loads'])

    def test_residential_calendar_and_count_basis_retained(self):
        row = next(p for p in self.bundle['programs'] if p.get('scope') == 'whole_dwelling')
        out = self.exporter().export(row['id'], 'defaulted')
        annual = [s for s in out['schedules'].values() if s['type'] == 'annual']
        self.assertTrue(annual)
        self.assertTrue(all(s['year'] == 2007 and len(s['values']) == 8760 for s in annual))
        self.assertTrue(all(l['basis'] == 'dwelling_unit' for l in out['loads']))
        self.assertNotIn('floor_area_m2', out['required_bindings'])

    def test_shared_services_are_not_duplicated_as_local_demands(self):
        exporter = self.exporter()
        out = exporter.export(self.office['id'], 'defaulted')
        local = {l['demand_id'] for l in out['loads']}
        self.assertTrue(all(s['id'] not in local for s in out['shared_services']))
        self.assertEqual(len(out['shared_services']), len({s['id'] for s in out['shared_services']}))

    def test_mixture_preserves_positive_leaf_when_aggregate_unknown(self):
        bundle = copy.deepcopy(self.bundle)
        a, b, mixed = (copy.deepcopy(self.office) for _ in range(3))
        a['id'], b['id'], mixed['id'] = 'leaf-a', 'leaf-b', 'mixed-test'
        a['loads'] = [copy.deepcopy(next(l for l in a['loads'] if l['quantity'] == 'lighting'))]
        b['loads'] = [copy.deepcopy(a['loads'][0])]
        a['loads'][0]['value'] = 10
        b['loads'][0]['value'] = None
        mixed.update(composition_id='recipe-test', loads=[dict(a['loads'][0], value=None, schedule_id=None)])
        bundle['programs'] += [a, b, mixed]
        bundle['compositions'].append({'id': 'recipe-test', 'members': [
            {'program_id': a['id'], 'weight': .25}, {'program_id': b['id'], 'weight': .75}]})
        out = self.exporter(bundle).export(mixed['id'], 'defaulted')
        lighting = [l for l in out['loads'] if l['type'] == 'lighting']
        self.assertAlmostEqual(sum(l['value'] for l in lighting), 2.5)
        self.assertEqual(len({l['demand_id'] for l in lighting}), 2)
        self.assertTrue(all(l['heat_fractions']['radiant'] == .7 for l in lighting))

    def test_explicit_disabled_conditioning_is_retained(self):
        row = next(p for p in self.bundle['programs'] if p.get('parameters', {}).get('conditioning', {}).get('value') ==
                   {'heating_enabled': False, 'cooling_enabled': False})
        out = self.exporter().export(row['id'], 'defaulted')
        self.assertFalse(out['controls']['heating_enabled'])
        self.assertFalse(out['controls']['cooling_enabled'])

    def test_semantic_validation_rejects_orphans_and_unit_mismatch(self):
        exporter = self.exporter()
        out = exporter.export(self.office['id'], 'defaulted')
        out['loads'][0]['schedule_id'] = 'missing'
        self.assertTrue(exporter.validate(out))
        out = exporter.export(self.office['id'], 'defaulted')
        out['schedules'][out['loads'][0]['schedule_id']]['unit'] = 'degC'
        self.assertTrue(exporter.validate(out))

    def test_existing_positive_schedule_gap_uses_zero_not_missing_schedule_one(self):
        exporter = self.exporter()
        out = exporter.export('program-0d0d5461f1cee89d04d148eb', 'defaulted')
        equipment = next(l for l in out['loads'] if l['end_use'] == 'electric_equipment')
        self.assertGreater(equipment['value'], 200)
        schedule = out['schedules'][equipment['schedule_id']]
        self.assertEqual(schedule['rules'][0]['day_types'], ['Default'])
        self.assertEqual(schedule['rules'][0]['values'], [0])
        missing = copy.deepcopy(self.office);missing['id'] = 'positive-missing-schedule'
        missing['loads'] = [dict(missing['loads'][0], value=10, schedule_id=None)]
        bundle = dict(self.bundle, programs=self.bundle['programs'] + [missing])
        other = self.exporter(bundle).export(missing['id'], 'defaulted')
        self.assertEqual(other['schedules'][other['loads'][0]['schedule_id']]['rules'][0]['values'], [1])

    def test_raw_mixture_does_not_repeat_constituent_water_as_shared_services(self):
        identity = 'program-1edef15460d778bd5c7741c8'
        source = next(r for r in self.bundle['programs'] if r['id'] == identity)
        represented = {component['load']['demand_id'] for load in source['loads']
                       for component in load.get('source_components', [])}
        self.assertTrue(represented.intersection(source['service_ids']))
        out = self.exporter().export(identity, 'raw')
        self.assertTrue(any(l['type'] == 'hot_water' and l['value'] > 0 for l in out['loads']))
        self.assertFalse(represented.intersection(s['id'] for s in out['shared_services']))

    def test_mixture_assumptions_resolve_to_exact_exported_values(self):
        exporter = self.exporter()
        out = exporter.export('program-00781e0b526174a15665721b', 'defaulted')
        def pointer(value, path):
            for token in path.split('/')[1:]:
                key = token.replace('~1', '/').replace('~0', '~')
                value = value[int(key)] if isinstance(value, list) else value[key]
            return value
        self.assertTrue(out['assumptions'])
        for assumption in out['assumptions']:
            self.assertEqual(pointer(out, assumption['path']), assumption['replacement_value'], assumption['path'])
        loads = next(a for a in out['assumptions'] if a['path'] == '/loads')
        self.assertEqual(loads['original_value'], exporter.export('program-00781e0b526174a15665721b', 'raw')['loads'])


if __name__ == '__main__':
    unittest.main()
