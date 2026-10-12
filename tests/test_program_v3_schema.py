"""The standalone v3 schema must reject unresolved executable operands."""
import copy
import unittest

from jsonschema import Draft202012Validator

from scripts.common import ROOT, load_json


class ProgramV3SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_json(ROOT / 'schemas/program-json-v3.schema.json')
        cls.validator = Draft202012Validator(cls.schema)
        cls.ready = load_json(ROOT / 'docs/examples/program-json-v3/medium-office.defaulted.json')
        cls.raw = load_json(ROOT / 'docs/examples/program-json-v3/medium-office.raw.json')

    def invalid(self, value):
        self.assertTrue(list(self.validator.iter_errors(value)), 'Invalid ready DTO was accepted')

    def valid(self, value):
        self.assertEqual([e.message for e in self.validator.iter_errors(value)], [])

    def test_real_medium_office_examples_validate(self):
        Draft202012Validator.check_schema(self.schema)
        self.valid(self.ready)
        self.valid(self.raw)

    def test_ready_native_heat_fractions_cannot_be_null_or_missing(self):
        for load in self.ready['loads']:
            if 'heat_fractions' not in load:
                continue
            for field in load['heat_fractions']:
                for omit in (False, True):
                    with self.subTest(type=load['type'], field=field, omit=omit):
                        value = copy.deepcopy(self.ready)
                        target = next(l for l in value['loads'] if l['demand_id'] == load['demand_id'])
                        if omit:
                            del target['heat_fractions'][field]
                        else:
                            target['heat_fractions'][field] = None
                        self.invalid(value)

    def test_enabled_controls_require_schedule_and_disabled_controls_omit_it(self):
        for mode in ('heating', 'cooling'):
            for missing in (False, True):
                with self.subTest(mode=mode, missing=missing):
                    value = copy.deepcopy(self.ready)
                    if missing:
                        del value['controls'][mode + '_setpoint_schedule_id']
                    else:
                        value['controls'][mode + '_setpoint_schedule_id'] = None
                    self.invalid(value)
            value = copy.deepcopy(self.ready)
            value['controls'][mode + '_enabled'] = False
            value['controls']['conditioning_state'] = 'cooling_only' if mode == 'heating' else 'heating_only'
            self.invalid(value)
            del value['controls'][mode + '_setpoint_schedule_id']
            self.valid(value)

    def test_conditioning_state_exactly_matches_flags(self):
        states = [(False, False, 'unconditioned'), (True, False, 'heating_only'),
                  (False, True, 'cooling_only'), (True, True, 'heating_and_cooling')]
        for h, c, state in states:
            value = copy.deepcopy(self.ready)
            value['controls'].update(heating_enabled=h, cooling_enabled=c, conditioning_state=state)
            for mode, enabled in (('heating', h), ('cooling', c)):
                if not enabled:
                    value['controls'].pop(mode + '_setpoint_schedule_id', None)
            with self.subTest(state=state):
                self.valid(value)
                for wrong in {s[2] for s in states} - {state} | {'unknown'}:
                    bad = copy.deepcopy(value)
                    bad['controls']['conditioning_state'] = wrong
                    self.invalid(bad)

    def test_water_requires_target_and_complete_weather_instruction(self):
        for field, replacement in [('target_temperature_schedule_id', None),
                                   ('inlet_temperature', {'method': 'unresolved'}),
                                   ('inlet_temperature', {'method': 'CorrelationFromWeatherFile'})]:
            value = copy.deepcopy(self.ready)
            water = next(l for l in value['loads'] if l['type'] == 'hot_water')
            water[field] = replacement
            with self.subTest(field=field, value=replacement):
                self.invalid(value)
                del water[field]
                self.invalid(value)

    def test_shared_services_use_same_ready_load_constraints(self):
        for field, replacement in [('value', None), ('value', 0), ('schedule_id', None),
                                   ('inlet_temperature', {'method': 'unresolved'})]:
            value = copy.deepcopy(self.ready)
            water = next(l for l in value['loads'] if l['type'] == 'hot_water')
            value['loads'].remove(water)
            value['shared_services'] = [{'id': 'test-shared-water', 'ownership': 'instantiate_once',
                                        'host_assignment': 'consumer_selected_zone', 'loads': [water]}]
            self.valid(value)
            water[field] = replacement
            with self.subTest(field=field, value=replacement):
                self.invalid(value)

    def test_activity_can_be_per_occupancy_load_but_is_required_for_each(self):
        value = copy.deepcopy(self.ready)
        people = [l for l in value['loads'] if l['type'] == 'occupancy']
        self.assertTrue(people)
        sid = value['controls'].pop('activity_schedule_id', None) or people[0]['activity_schedule_id']
        for load in people:
            load.pop('activity_schedule_id', None)
        self.invalid(value)
        for load in people:
            load['activity_schedule_id'] = sid
        self.valid(value)
        second = copy.deepcopy(people[0])
        second['demand_id'] += '-second'
        del second['activity_schedule_id']
        value['loads'].append(second)
        self.invalid(value)
        value['controls']['activity_schedule_id'] = sid
        self.valid(value)

    def test_activity_is_not_an_equipment_field(self):
        value = copy.deepcopy(self.ready)
        lights = next(l for l in value['loads'] if l['type'] == 'lighting')
        people = next(l for l in value['loads'] if l['type'] == 'occupancy')
        lights['activity_schedule_id'] = value['controls'].get('activity_schedule_id') or people['activity_schedule_id']
        self.invalid(value)

    def test_shared_occupancy_requires_activity_and_people_heat_operands(self):
        value = copy.deepcopy(self.ready)
        people = next(l for l in value['loads'] if l['type'] == 'occupancy')
        sid = value['controls'].pop('activity_schedule_id', None) or people['activity_schedule_id']
        people['activity_schedule_id'] = sid
        value['loads'].remove(people)
        value['shared_services'] = [{'id': 'test-shared-occupancy', 'ownership': 'instantiate_once',
                                    'host_assignment': 'consumer_selected_zone', 'loads': [people]}]
        self.valid(value)
        for field in ('people_radiant_fraction', 'people_sensible_fraction'):
            bad = copy.deepcopy(value)
            del bad['controls'][field]
            with self.subTest(field=field):
                self.invalid(bad)
        del people['activity_schedule_id']
        self.invalid(value)

    def test_raw_retains_unknown_controls_and_native_fractions(self):
        value = copy.deepcopy(self.raw)
        value['controls'].update(heating_enabled=None, cooling_enabled=None, conditioning_state='unknown',
                                 heating_setpoint_schedule_id=None, cooling_setpoint_schedule_id=None)
        lights = next(l for l in value['loads'] if l['type'] == 'lighting')
        lights['heat_fractions']['radiant'] = None
        self.valid(value)


if __name__ == '__main__':
    unittest.main()
