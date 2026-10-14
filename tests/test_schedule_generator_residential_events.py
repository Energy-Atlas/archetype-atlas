import copy
import math
from pathlib import Path
import unittest

from atlas_schedules.budgets import bind_budget, reference_budget
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet, strict_json
from atlas_schedules.residential import generate_residential
from atlas_schedules.residential.activity import simulate_activities
from atlas_schedules.residential.events import _EventRun, _segments, EVENT_SLOTS, generate_events
from atlas_schedules.residential.shapes import shift_and_normalize, normalize
from scripts.schedule_generator_reference import event_capture_inputs, load_event_reference

ROOT = Path(__file__).resolve().parents[1]


def unpack_states(runs):
    return [[state for length, state in resident for _ in range(length)] for resident in runs]


def unpack_minutes(runs, length):
    values = [0.0]*length
    for start, count, value in runs:
        values[start:start+count] = [value]*count
    return values


class ResidentialEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = strict_json((ROOT/'atlas_schedules/data/manifest.json').read_bytes(), 'manifest')
        cls.resources = ResourceSet.load(manifest['resource_set_id'])
        cls.cases = {c['case_id']: c for c in load_event_reference()['cases']}
        cls.activities = {}; cls.generated = {}
        for key, case in cls.cases.items():
            activities = simulate_activities(case['inputs'], case['unit_seed'], cls.resources)
            if 'component_states' in case:
                activities['resident_states'] = unpack_states(case['component_states'])
            cls.activities[key] = activities
            if key not in ('component_no_events', 'component_all_absent'):
                cls.generated[key] = generate_events(activities, case['inputs'], cls.resources)

    def assert_fractions(self, actual, expected):
        self.assertEqual(len(actual), 8760); self.assertEqual(len(expected), 8760)
        for hour, (x, y) in enumerate(zip(actual, expected)):
            self.assertTrue(math.isfinite(x) and 0 <= x <= 1, (hour, x))
            self.assertTrue(math.isclose(x, y, rel_tol=1e-6, abs_tol=1e-8), (hour, x, y))

    def assert_segments(self, actual, expected):
        self.assertEqual(set(actual), set(expected))
        for slot, runs in actual.items():
            self.assertEqual(len(runs), len(expected[slot]), slot)
            for x, y in zip(runs, expected[slot]):
                self.assertEqual(x[:2], y[:2], slot)
                self.assertTrue(math.isclose(x[2], y[2], rel_tol=1e-6, abs_tol=1e-8), (slot, x, y))

    def test_activity_events_match_source_fixture(self):
        for key, result in self.generated.items():
            case = self.cases[key]; activities = self.activities[key]
            with self.subTest(case=key):
                self.assertEqual(activities['resident_states'], unpack_states(case['resident_state_runs']))
                for field in ('occupant_types', 'main_state', 'enduse_states', 'unit_offset_minutes'):
                    self.assertEqual(activities[field], case[field])
                self.assertEqual(set(result['channels']), set(case['channels']) & set(EVENT_SLOTS))
                for slot, values in result['channels'].items():
                    self.assert_fractions(values, case['channels'][slot])
                if activities['simulated_residents']:
                    context = result['source_context']
                    for field in ('event_draws', 'final_rng_states', 'power_rows', 'minute_lengths'):
                        self.assertEqual(context[field], case[field], (key, field))
                    self.assert_segments(context['event_segments'], case['event_segments'])
                    self.assertEqual(context['final_rng_states']['main'], activities['main_state'])

    def test_absent_appliances_and_zero_use(self):
        for key in ('sparse', 'zero', 'without_clothes_washer', 'without_clothes_dryer', 'without_dishwasher', 'without_cooking_range'):
            result = self.generated[key]; context = result['source_context']
            self.assertEqual(set(context['absence_receipts']), set(EVENT_SLOTS)-set(result['channels']))
        self.assertEqual(self.generated['zero']['channels'], {})
        self.assertFalse(self.generated['zero']['source_context']['rng_consumed'])
        self.assertEqual(self.generated['sparse']['channels'].keys(), {'hot_water_fixtures'})
        self.assertIn('clothes_dryer', self.generated['without_clothes_washer']['source_context']['absence_receipts'])
        zero = {'quantity':'energy','unit':'Wh','magnitude_unit':'W','basis':'dwelling_unit',
                'fuel':'electricity','host':'conditioned space','evidence':{'original_value':0},'method':'direct_annual','total':0}
        values = self.generated['one']['channels']['cooking_range']
        bound = bind_budget(zero, values)
        self.assertEqual(bound['effective_magnitude']['value'], 0)
        self.assertGreater(bound['scaling_receipt']['generated_integral'], 0)
        self.assertEqual(bound['reference_target']['evidence'], zero['evidence'])

    def test_end_use_change_matches_upstream_coupling(self):
        base = self.generated['one']; ctx = base['source_context']
        dryer_absent = self.generated['without_clothes_dryer']
        for field in ('event_draws', 'event_segments', 'final_rng_states', 'power_rows'):
            self.assertEqual(ctx[field], dryer_absent['source_context'][field])
        self.assertNotIn('clothes_dryer', dryer_absent['channels'])
        for absent, excluded in [('dishwasher', {'dishwasher','hot_water_dishwasher'}),
                                 ('clothes_washer', {'clothes_washer','clothes_dryer','hot_water_clothes_washer'}),
                                 ('cooking_range', {'cooking_range'})]:
            changed = self.generated['without_'+absent]
            for slot in set(base['channels'])-excluded:
                self.assertEqual(base['channels'][slot], changed['channels'][slot])
            streams = {'dishwasher'} if absent == 'dishwasher' else {'clothes_washer','clothes_dryer'} if absent == 'clothes_washer' else {'cooking'}
            for stream in set(ctx['final_rng_states'])-streams:
                self.assertEqual(ctx['final_rng_states'][stream], changed['source_context']['final_rng_states'][stream])
            for stream in streams:
                self.assertEqual(changed['source_context']['final_rng_states'][stream], self.activities['one']['enduse_states'][stream])
                self.assertNotEqual(ctx['final_rng_states'][stream], changed['source_context']['final_rng_states'][stream])
        # Water generation precedes power on each shared appliance stream.
        draws = ctx['event_draws']
        for stream in ('dishwasher', 'clothes_washer'):
            native = [d for d in draws if d[0] == stream]
            self.assertIsNone(native[0][1])
            self.assertGreater(next(i for i, d in enumerate(native) if d[1] is not None), 2)
        washer = ctx['event_segments']['clothes_washer']; dryer = ctx['event_segments']['clothes_dryer']
        self.assertEqual(len(washer), len(dryer))
        for cw, cd in zip(washer, dryer):
            self.assertEqual(cd[0], cw[0]+cw[1])

    def test_water_normalization_after_shift(self):
        case = self.cases['one']; ctx = self.generated['one']['source_context']
        days = _EventRun(self.activities['one'], case['inputs'], self.resources).days
        components = {}
        for slot in ('shower', 'sink', 'bath'):
            raw = unpack_minutes(case['event_segments'][slot], case['minute_lengths'][slot])
            components[slot] = shift_and_normalize(raw, case['unit_offset_minutes'], days, ctx['monthly_shifts'])
            self.assertEqual(max(components[slot]), 1)
            self.assertTrue(all(0 <= v <= 1 for v in components[slot]))
            self.assertTrue(math.isclose(math.fsum(components[slot]), ctx['fixture_component_integrals'][slot], rel_tol=1e-12))
        fixtures = normalize([math.fsum(v) for v in zip(components['shower'], components['sink'], components['bath'])])
        self.assert_fractions(fixtures, case['channels']['hot_water_fixtures'])
        # A hand-built minute impulse crosses the whole-year and daily boundaries.
        from datetime import date
        raw = [0.0]*1440; raw[0] = 1; raw[1439] = 3
        shifts = {'weekday': {'Jan': 1}, 'weekend': {'Jan': 1}}
        shifted = shift_and_normalize(raw, -1, [date(2007,1,1)], shifts)
        self.assertEqual(shifted, [1/3]+[0.0]*22+[1.0])

    def test_excluded_ev_output_retains_seed_slot(self):
        ctx = self.generated['one']['source_context']
        self.assertEqual(ctx['enduse_seeds']['ev'], 3143890026)
        self.assertEqual(ctx['enduse_seeds']['cooking'], 3348747335)
        self.assertEqual(ctx['final_rng_states']['ev'], self.activities['one']['enduse_states']['ev'])
        self.assertFalse(any(d[0] == 'ev' for d in ctx['event_draws']))
        self.assertFalse(any(slot.startswith('ev') for slot in self.generated['one']['channels']))
        self.assertIn('ev', ctx['excluded'])

    def test_no_event_component_rejects_positive_budget_without_retry(self):
        case = self.cases['component_no_events']; activities = self.activities['component_no_events']
        run = _EventRun(activities, case['inputs'], self.resources); minutes = run.generate_minutes()
        self.assert_segments({k:_segments(v) for k,v in minutes.items()}, case['event_segments'])
        self.assertEqual(run.draws, case['event_draws'])
        self.assertEqual({k:s.rng.getstate() for k,s in run.streams.items()}, case['final_rng_states'])
        self.assertEqual(case['source_error'], 'comparison of Float with NaN failed')
        with self.assertRaises(GeneratorError) as error:
            generate_events(activities, case['inputs'], self.resources)
        self.assertEqual(error.exception.code, 'zero_generated_integral')
        original = strict_json((ROOT/'data/program-inputs/residential-v1.json').read_bytes(), 'original-targets')
        record = original['records']['residential_archetype-16b2dae7d144a14640bf']
        load = next(x for x in record['loads'] if x['end_use'] == 'clothes_washer')
        demand = dict(load, quantity='energy', annual_target={'total':load['evidence']['original_value']['annual_kwh']*1000,
                      'unit':'Wh','evidence':load['evidence']})
        target = reference_budget(demand, [])
        with self.assertRaises(GeneratorError) as error:
            bind_budget(target, [0.0]*8760)
        self.assertEqual(error.exception.code, 'zero_generated_integral')

    def test_exact_six_frozen_cases_compose_and_conserve_original_targets(self):
        original = strict_json((ROOT/'data/program-inputs/residential-v1.json').read_bytes(), 'original-targets')
        selected = [c for c in self.cases.values() if 'program_id' in c]
        self.assertEqual(len(selected), 6)
        for case in selected:
            with self.subTest(case=case['case_id']):
                result = generate_residential(case['inputs'], case['unit_seed'], self.resources)
                self.assertEqual(set(result['channels']), set(case['channels']))
                for slot, values in result['channels'].items():
                    self.assert_fractions(values, case['channels'][slot])
                cfg = self.resources.get('program', case['program_id'])['configuration']
                self.assertEqual(case['inputs']['residents'], cfg['occupants'])
                self.assertEqual(case['unit_seed'], cfg['seed'])
                for key in ('state','latitude','longitude','time_zone_utc_offset','bedrooms'):
                    self.assertEqual(case['inputs'][key], cfg[key])
                self.assertEqual(case['inputs']['weather_id'], cfg['weather']['station_filename'].removesuffix('.epw'))
                for load in original['records'][case['case_id']]['loads']:
                    slot = load['end_use']
                    if slot not in result['channels']:
                        continue
                    evidence = load['evidence']; recovered = evidence['original_value']
                    if load['unit'] == 'm3/s':
                        total = recovered['daily_gallons']*365*0.003785411784; annual_unit = 'm3'; quantity = 'volume'
                    elif 'annual_kwh' in recovered:
                        total = recovered['annual_kwh']*1000; annual_unit = 'Wh'; quantity = 'energy'
                    else:
                        self.fail((slot, recovered))
                    # Task 2 uses 'water' as the volume carrier; this adapter is
                    # separate from the recovered load, which has no fuel field.
                    target = reference_budget(dict(load, quantity=quantity,
                        fuel='water' if annual_unit == 'm3' else load['fuel'], annual_target={
                        'total':total,'unit':annual_unit,'evidence':evidence}), [])
                    bound = bind_budget(target, result['channels'][slot])
                    self.assertTrue(math.isclose(bound['scaling_receipt']['achieved_total'], total,
                        rel_tol=1e-8, abs_tol=1e-12 if annual_unit == 'm3' else 1e-8))
                    self.assertEqual(bound['reference_target']['evidence'], evidence)

    def test_invalid_context_and_dependencies_fail_explicitly(self):
        for change in ({'installed':{}}, {'state':'XX'}, {'year':2009}, {'residents':2}):
            with self.subTest(change=change), self.assertRaises(GeneratorError):
                generate_events(self.activities['one'], dict(self.cases['one']['inputs'], **change), self.resources)
        for field in ('year','residents','installed','state'):
            inputs = copy.deepcopy(self.cases['one']['inputs']);del inputs[field]
            with self.subTest(missing=field), self.assertRaises(GeneratorError):
                generate_events(self.activities['one'], inputs, self.resources)
        changed = copy.deepcopy(self.activities['one']);del changed['enduse_states']['ev']
        with self.assertRaises(GeneratorError):
            generate_events(changed, self.cases['one']['inputs'], self.resources)
        wrong_count = copy.deepcopy(self.activities['one'])
        wrong_count['simulated_residents'] = 2
        wrong_count['resident_states'] *= 2
        wrong_seed = copy.deepcopy(self.activities['one'])
        wrong_seed['enduse_seeds']['cooking'] += 1
        for activities in (wrong_count, wrong_seed):
            with self.subTest(context='mismatched source receipt'), self.assertRaises(GeneratorError):
                generate_events(activities, self.cases['one']['inputs'], self.resources)

    def test_compiled_constants_keep_source_units_and_si_evidence(self):
        fields = self.resources.get('residential', 'event-constants')['fields']
        self.assertEqual(fields['BathDurationMean'].get('si_unit'), 's')
        self.assertEqual(fields['BathDurationMean'].get('si_value'), 339)
        self.assertEqual(fields['SinkFlowRateMean'].get('si_unit'), 'm3/s')
        self.assertTrue(math.isclose(fields['SinkFlowRateMean'].get('si_value'),
                                    1.14*0.003785411784/60, rel_tol=1e-14, abs_tol=0))
        self.assertEqual(fields['SinkFlowRateMean']['value'], 1.14)
        self.assertEqual(fields['SinkFlowRateMean']['provenance']['original_value'], '1.14')

    def test_controlled_calendar_receipts_keep_physical_location_inputs(self):
        for case in self.cases.values():
            for sample in case['calendar_receipt']:
                self.assertEqual(sample['utc_offset'], 0)
                self.assertFalse(sample['dst'])
            self.assertEqual(case['calendar_receipt'][2]['civil_time'], '2007-03-31 23:15')
            self.assertEqual(case['calendar_receipt'][4]['civil_time'], '2007-07-31 23:15')
        case = self.cases['residential_archetype-16b2dae7d144a14640bf']
        generated = generate_residential(case['inputs'], case['unit_seed'], self.resources)
        self.assertEqual(generated['source_context']['shapes']['time_zone_utc_offset'], -9)
        self.assertEqual(generated['source_context']['events']['calendar_variant'],
                         'controlled_no_DST_local_standard_calendar')

    def test_all_absent_component_preserves_sink_attempt_cap(self):
        case = self.cases['component_all_absent']
        run = _EventRun(self.activities['component_all_absent'], case['inputs'], self.resources)
        minutes = run.generate_minutes()
        self.assert_segments({k:_segments(v) for k,v in minutes.items()}, case['event_segments'])
        self.assertEqual(run.draws, case['event_draws'])
        self.assertEqual(len(run.draws), 73010) # 365*200 sink attempts + ten Gaussian draws.
        self.assertEqual(sum(d[0] == 'hygiene' for d in run.draws), 73006)
        self.assertTrue(all(not runs for runs in case['event_segments'].values()))
        with self.assertRaises(GeneratorError) as error:
            generate_events(self.activities['component_all_absent'], case['inputs'], self.resources)
        self.assertEqual(error.exception.code, 'zero_generated_integral')

    def test_frozen_presence_inputs_come_from_arguments_even_on_zero_skip(self):
        cases = {c['case_id']:c for c in event_capture_inputs(self.resources)}
        flags = cases['residential_archetype-28457c00121833f065f2']['inputs']['installed']
        self.assertTrue(flags['dishwasher']); self.assertTrue(flags['cooking_range'])
        self.assertTrue(flags['plug_loads_other']); self.assertTrue(flags['plug_loads_tv'])
        self.assertFalse(flags['clothes_washer']); self.assertFalse(flags['clothes_dryer'])
        self.assertEqual(self.cases['residential_archetype-28457c00121833f065f2']['inputs']['installed'], flags)
