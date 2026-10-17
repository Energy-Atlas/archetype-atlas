"""S1: Stripmall ordered multi-group People HOO against the original 2013 SOURCE native pilot.

Expected arrays come from the tracked, hash-locked extract of the original pilot
(data/schedule-generator/stripmall/pilot-2013-source-carrier.json.gz); nothing
here runs native code or claims family readiness.
"""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import unittest

from atlas_schedules.commercial import parametric
from atlas_schedules.errors import GeneratorError

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'strip_mall__90_1_2013__source'
TYPE_PROGRAMMES = {'Type1': 'program-f9034faffb02f5e77056c6cf', 'Type2': 'program-75cf4ec07b0c6053a2e1ba6d',
                   'Type3': 'program-e44fc2ec3f865c660176b600'}


def pilot():
    lock = json.loads((ROOT/'sources/schedule-generator-stripmall-pilot-carrier-lock.json').read_text(encoding='utf-8'))
    blob = (ROOT/lock['extract']['path']).read_bytes()
    assert hashlib.sha256(blob).hexdigest() == lock['extract']['sha256'] and len(blob) == lock['extract']['size_bytes']
    payload = gzip.decompress(blob)
    assert hashlib.sha256(payload).hexdigest() == lock['extract']['decoded_sha256']
    return json.loads(payload)


def frozen():
    programmes = {p['id']: p for p in json.loads((ROOT/'data/definition-releases/v0.1.1/programs.json').read_text(encoding='utf-8'))}
    schedules = {s['id']: s for s in json.loads((ROOT/'data/definition-releases/v0.1.1/schedules.json').read_text(encoding='utf-8'))}
    return programmes, schedules


def people_context(case, programmes, schedules):
    """Literal pilot carrier operands in native space order, with the frozen original Rulesets."""
    parts = []; native = {p['handle']: p for p in case['people_objects']}
    for op in case['carrier']['operands']:
        kind = op['schedule_name'].split()[-1].split('_')[0]  # 'Type1_OCC_SCH' -> 'Type1'
        programme = programmes[TYPE_PROGRAMMES[kind]]
        load = next(l for l in programme['loads'] if l['quantity'] == 'occupancy')
        parts.append({'source_space_name': op['space_name'], 'source_space_handle': op['space_handle'],
                      'native_people_object_handle': op['people_handle'], 'schedule_identity': op['schedule_handle'],
                      'schedule': copy.deepcopy(schedules[load['schedule_id']]), 'nominal_people': op['actual_carrier_operand_people'],
                      'residential': False, 'program_id': programme['id'], 'source_program_id': programme['source_id'],
                      'source_floor_area_m2': op['floor_area_m2'], 'source_density_person_m2': load['value'],
                      'evidence': {'source_people_definition': copy.deepcopy(load), 'origin': op['origin'],
                                   'excluded_source_multiplier': op['excluded_source_multiplier'],
                                   'native_people_object': copy.deepcopy(native[op['people_handle']])}})
    return {'year': 2007, 'holidays': [], 'configuration_id': CONFIG, 'source_hoo_configuration_id': CONFIG,
            'standards_version': '0.8.6', 'steps_per_hour': 6,
            'source_clock': {'TZ': 'UTC', 'variant': 'controlled_no_DST_local_standard_calendar'},
            'parametric_apply': {'error_on_out_of_order': False, 'source_method': 'create_typical.rb:766'},
            'occupancy_aggregation': {'policy': 'explicit_source_model_nonresidential_people', 'source_hoo_configuration_id': CONFIG,
                'evidence_view': 'source', 'constituents': parts,
                'source_model_scope': {'model_family': 'RetailStripmall', 'method': 'explicit_view_specific_model_hoo_reference',
                    'population_or_whole_prototype_equivalent': False,
                    'native_sorted_space_order': [op['space_name'] for op in case['carrier']['operands']]}}}


class StripmallPeopleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pilot = pilot(); cls.programmes, cls.schedules = frozen()
        cls.case = cls.pilot['cases'][0]
        cls.context = people_context(cls.case, cls.programmes, cls.schedules)

    def assertCode(self, code, fn, *args):
        with self.assertRaises(GeneratorError) as caught: fn(*args)
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_ruby_float_sum_is_kahan_babuska(self):
        self.assertEqual(parametric._ruby_float_sum([0.1, 0.2, 0.3]), 0.6)  # naive left sum gives 0.6000000000000001
        self.assertEqual(parametric._ruby_float_sum([]), 0.0)
        self.assertEqual(parametric._ruby_float_sum([1e16, 1.0, -1e16]), 1.0)
        # Derived from array.c ary_sum, not observed Ruby output (no Ruby here). The
        # pilot data cannot separate the algorithms, so this vector pins them:
        # left fold 0.0, math.fsum 1.0000000000000002, Kahan-Babuska 1.0.
        self.assertEqual(parametric._ruby_float_sum([1e100, 1.0, 2**-53, 2**-80, -1e100]), 1.0)

    def test_groups_weights_and_combined_fraction_match_pilot_exactly(self):
        groups, total = parametric.stripmall_people_groups(self.context)
        expected = self.case['carrier']['schedules']
        self.assertEqual([g['schedule_identity'] for g in groups], [g['schedule_handle'] for g in expected])
        self.assertEqual([g['weight'] for g in groups], [g['design_people_without_multiplier'] for g in expected])
        self.assertEqual(total, self.case['carrier']['total_design_people_without_multiplier'])
        fraction = parametric.stripmall_combined_fraction(self.context)
        self.assertEqual(len(fraction), 8760)
        self.assertEqual(fraction, self.case['carrier']['combined_hourly_fraction'])

    def test_daily_hoo_matches_pilot_for_every_day_category(self):
        result = parametric._infer(self.context)
        observed = self.case['whole_model_original_hoo']
        for key, expected in observed.items():
            day = expected['days_used'][0]
            actual = result['daily_hoo'][day-1]
            with self.subTest(category=key):
                self.assertEqual({k: actual[k] for k in ('hoo_start', 'hoo_end', 'hoo_hours')},
                                 {k: expected[k] for k in ('hoo_start', 'hoo_end', 'hoo_hours')})
                self.assertEqual(actual['days_used'], expected['days_used'])
        self.assertEqual(result['source_model_people_receipt']['groups'][0]['schedule_identity'],
                         self.case['carrier']['schedules'][0]['schedule_handle'])

    def test_second_seed_shares_original_carrier(self):
        other = people_context(self.pilot['cases'][1], self.programmes, self.schedules)
        self.assertEqual(parametric.stripmall_combined_fraction(other), self.pilot['cases'][1]['carrier']['combined_hourly_fraction'])

    def test_changed_grouping_order_and_scope_reject(self):
        def regroup(c):  # SMstore4 claims the Type1 Ruleset identity but keeps its Type2 schedule body
            part = next(p for p in c['occupancy_aggregation']['constituents'] if p['source_space_name'] == 'SMstore4')
            part['schedule_identity'] = c['occupancy_aggregation']['constituents'][0]['schedule_identity']
        def reorder(c):
            parts = c['occupancy_aggregation']['constituents']; parts[0], parts[1] = parts[1], parts[0]
        def residential(c): c['occupancy_aggregation']['constituents'][3]['residential'] = True
        def zero(c): c['occupancy_aggregation']['constituents'][2]['nominal_people'] = 0
        def unqualified(c):
            for k in ('configuration_id', 'source_hoo_configuration_id'): c[k] = 'strip_mall__90_1_2007__source'
            c['occupancy_aggregation']['source_hoo_configuration_id'] = 'strip_mall__90_1_2007__source'
        def leap(c): c['year'] = 2008
        def reviewed(c):
            for k in ('configuration_id', 'source_hoo_configuration_id'): c[k] = 'strip_mall__90_1_2013__reviewed'
            c['occupancy_aggregation'].update(source_hoo_configuration_id='strip_mall__90_1_2013__reviewed', evidence_view='reviewed')
        def part(c): return c['occupancy_aggregation']['constituents'][2]
        def nominal(c): part(c)['nominal_people'] = part(c)['nominal_people']*(1+2**-50)
        def programme(c): part(c)['program_id'] = TYPE_PROGRAMMES['Type2']
        def definition_schedule(c): part(c)['evidence']['source_people_definition']['schedule_id'] = 'schedule-other'
        def native_ruleset(c): part(c)['evidence']['native_people_object']['schedule_handle'] = '{other}'
        def native_missing(c): del part(c)['evidence']['native_people_object']
        def native_density(c):  # internally consistent nominal, but a density the definition does not carry
            native = part(c)['evidence']['native_people_object']; native['density_person_m2'] *= 1.001
            part(c)['nominal_people'] = part(c)['source_floor_area_m2']*native['density_person_m2']
        cases = [(regroup, 'invalid_commercial_context'), (reorder, 'invalid_commercial_context'),
                 (residential, 'invalid_commercial_context'), (zero, 'invalid_commercial_context'),
                 (unqualified, 'requires_binding'), (reviewed, 'requires_binding'), (leap, 'invalid_commercial_context'),
                 (nominal, 'invalid_commercial_context'), (programme, 'invalid_commercial_context'),
                 (definition_schedule, 'invalid_commercial_context'), (native_ruleset, 'invalid_commercial_context'),
                 (native_missing, 'invalid_commercial_context'), (native_density, 'invalid_commercial_context')]
        for change, code in cases:
            context = copy.deepcopy(self.context); change(context)
            with self.subTest(change=change.__name__):
                self.assertCode(code, parametric._infer, context)

    def test_single_profile_path_cannot_stand_in_for_stripmall(self):
        context = copy.deepcopy(self.context)
        context['occupancy_aggregation']['policy'] = 'explicit_single_nonresidential_reference_carrier'
        self.assertCode('invalid_commercial_context', parametric._infer, context)


def water_context(case, programmes, schedules, schedule_handle):
    """Local first-registration water carrier for one shared water Ruleset, from pilot operands only."""
    receipts = {f['handle']: f for f in case['fixture_receipts']}
    order = [f['handle'] for f in case['actual_native_fixture_sort']]
    sharing = [h for h in order if receipts[h]['schedule_handle'] == schedule_handle]
    first = receipts[sharing[0]]
    model = people_context(case, programmes, schedules)
    from atlas_schedules.commercial.source_models import LOCAL_HOO_RESOLUTION
    services = {s['id']: s for s in json.loads((ROOT/'data/definition-releases/v0.1.1/services.json').read_text(encoding='utf-8'))}
    rules = schedules[services[first['source_service_id']]['load']['schedule_id']]
    context = {k: copy.deepcopy(model[k]) for k in ('year', 'holidays', 'configuration_id', 'source_hoo_configuration_id',
                                                     'standards_version', 'steps_per_hour', 'source_clock')}
    context.update(parametric_apply=dict(model['parametric_apply'], source_member={'path': 'source/create_typical.rb', 'labelled': 'pilot'}),
        slot_sources={'hot_water_volume': copy.deepcopy(rules)}, slot_modes={'hot_water_volume': 'hours'},
        occupancy_adjustment={'peak_occ_frac': .231, 'source_key': 'comstock__resources__options_lookup_tsv',
                              'source_options': ['baseline_hvac_sizing=autosize', 'baseline_hvac_sizing=hardsize']},
        occupancy_aggregation={'policy': 'explicit_source_local_space_people', 'source_hoo_configuration_id': CONFIG,
            'evidence_view': 'source', 'space': first['attached_space_name'],
            'resolution': copy.deepcopy(LOCAL_HOO_RESOLUTION), 'model_aggregation': copy.deepcopy(model['occupancy_aggregation']),
            'registration': {'schedule_identity': schedule_handle, 'fixtures': [receipts[h]['physical_fixture_id'] for h in sharing],
                             'source_schedule_id': rules['id'], 'first_registered_fixture': first['physical_fixture_id'], 'first_registered_space': first['attached_space_name'],
                             'native_fixture_order': [receipts[h]['physical_fixture_id'] for h in order],
                             'fixture_spaces': {receipts[h]['physical_fixture_id']: receipts[h]['attached_space_name'] for h in order}}})
    return context


class StripmallWaterCarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pilot = pilot(); cls.programmes, cls.schedules = frozen()
        # Native handles regenerate per run, so each case names its own water Rulesets.
        cls.water = {c['case_id']: [h for h, v in c['channels'].items() if v[0]['kind'] == 'WaterUseEquipment'] for c in cls.pilot['cases']}

    def assertCode(self, code, fn, *args):
        with self.assertRaises(GeneratorError) as caught: fn(*args)
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_first_registration_and_local_hoo_match_pilot(self):
        firsts = {}
        for case in self.pilot['cases']:
            for handle in self.water[case['case_id']]:
                context = water_context(case, self.programmes, self.schedules, handle)
                registration = context['occupancy_aggregation']['registration']
                firsts[case['original'][handle]['name']] = registration['first_registered_space']
                observed = case['registration'][handle]['hoo_inputs']
                inferred = parametric._infer(context)['daily_hoo']
                for key, expected in observed.items():
                    with self.subTest(case=case['case_id'], schedule=handle, category=key):
                        actual = inferred[expected['days_used'][0]-1]
                        self.assertEqual((actual['hoo_start'], actual['hoo_end'], actual['days_used']),
                                         (expected['hoo_start'], expected['hoo_end'], expected['days_used']))
        self.assertEqual(firsts, {'RetailStripmall Type1_SWH_SCH': 'LGstore1', 'RetailStripmall Type3_SWH_SCH': 'LGstore2',
                                  'RetailStripmall Type2_SWH_SCH': 'SMstore2'})

    def test_transformed_water_arrays_match_native_final(self):
        for case in self.pilot['cases']:
            for handle in self.water[case['case_id']]:
                context = water_context(case, self.programmes, self.schedules, handle)
                channels = {'hot_water_volume': case['original'][handle]['values']}
                result = parametric.transform_commercial(channels, case['operating'], context)
                actual = result['channels']['hot_water_volume']; expected = case['final'][handle]['values']
                with self.subTest(case=case['case_id'], schedule=case['original'][handle]['name']):
                    self.assertEqual(len(actual), 8760)
                    self.assertEqual(actual, expected)

    def test_water_must_use_the_explicit_local_first_registration_carrier(self):
        case = self.pilot['cases'][0]; handle = self.water[case['case_id']][0]
        base = water_context(case, self.programmes, self.schedules, handle)
        model = people_context(case, self.programmes, self.schedules)
        borrowed = copy.deepcopy(base); borrowed['occupancy_aggregation'] = copy.deepcopy(model['occupancy_aggregation'])
        def later_fixture(c):  # the shared Ruleset's second fixture cannot claim first registration
            r = c['occupancy_aggregation']['registration']; r['first_registered_fixture'] = r['fixtures'][1]
        def wrong_space(c):
            c['occupancy_aggregation']['space'] = 'SMstore4'
        def missing_route(c):
            c['occupancy_aggregation']['resolution'] = dict(c['occupancy_aggregation']['resolution'], route='model_equal_values')
        def other_ruleset(c):
            c['occupancy_aggregation']['registration']['source_schedule_id'] = 'schedule-other'
        def unhashable(c):
            c['occupancy_aggregation']['registration']['native_fixture_order'].append(['fixture'])
        def extra_slot(c):
            c['slot_sources']['occupancy'] = copy.deepcopy(c['slot_sources']['hot_water_volume']); c['slot_modes']['occupancy'] = 'hours'
        channels = {'hot_water_volume': case['original'][handle]['values']}
        self.assertCode('invalid_commercial_context', parametric.transform_commercial, channels, case['operating'], borrowed)
        for change in (later_fixture, wrong_space, missing_route, other_ruleset, unhashable):
            context = copy.deepcopy(base); change(context)
            with self.subTest(change=change.__name__):
                self.assertCode('invalid_commercial_context', parametric.transform_commercial, channels, case['operating'], context)
        pending = copy.deepcopy(base)
        for k in ('configuration_id', 'source_hoo_configuration_id'): pending[k] = 'strip_mall__90_1_2019__source'
        pending['occupancy_aggregation']['source_hoo_configuration_id'] = 'strip_mall__90_1_2019__source'
        self.assertCode('requires_binding', parametric.transform_commercial, channels, case['operating'], pending)
        self.assertCode('requires_binding', parametric._infer, pending)
        context = copy.deepcopy(base); extra_slot(context)
        self.assertCode('invalid_commercial_context', parametric.transform_commercial,
                        dict(channels, occupancy=channels['hot_water_volume']), case['operating'], context)


if __name__ == '__main__': unittest.main()
