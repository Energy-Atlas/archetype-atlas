"""Actual locked native fixed/getter/water association proof, never a recapture."""
import copy
import hashlib
import importlib
import importlib.util
import json
import unittest

from atlas_schedules.canonical import canonical
from atlas_schedules.companions import _native_constant
from atlas_schedules.errors import GeneratorError
from atlas_schedules.physical_sets import _source, _typed
from scripts.common import ROOT
from scripts.schedule_generator_apartments import compile_apartment_sources


class ApartmentReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = json.loads((ROOT / 'sources/schedule-generator-apartment-scope.json').read_text())
        cls.sources = compile_apartment_sources(cls.scope)

    def reference(self):
        name = 'scripts.schedule_generator_apartment_reference'
        self.assertIsNotNone(importlib.util.find_spec(name),
                             'Missing independently captured apartment fixed source proof/loader')
        module = importlib.import_module(name)
        self.assertTrue((ROOT / 'sources/schedule-generator-apartment-fixed-reference-lock.json').is_file(),
                        'Missing independently captured apartment fixed source lock')
        return module, module.load_apartment_fixed_reference()

    def test_water_source_association_matrix(self):
        module, ref = self.reference()
        inputs = module.apartment_fixed_capture_inputs(self.scope, self.sources)
        self.assertEqual(canonical(inputs), canonical(ref['inputs']))
        self.assertEqual(len(inputs['schedules']), 90)
        self.assertEqual(len(inputs['water_paths']), 20)
        self.assertEqual(sum(len(p['programme_ids']) for p in inputs['water_paths']), 40)
        self.assertEqual(len({p['schedule_id'] for p in inputs['water_paths']}), 2)
        self.assertEqual([s['id'] for s in inputs['schedules']],
                         list(self.sources['source_objects']['schedules']))
        self.assertEqual(len(ref['native']['schedules']), 90)
        self.assertEqual(len(ref['native']['water_paths']), 20)
        original = [s for s in inputs['schedules'] if s['construction_kind'] == 'original_c8_named_ruleset']
        overlays = [s for s in inputs['schedules'] if s['construction_kind'] == 'reviewed_zero_overlay_native_representation']
        self.assertEqual((len(original), len(overlays)), (46, 44))
        for item in overlays:
            self.assertEqual(item['rows'], [])
            self.assertEqual(item['original_explicit_special_day_selectors'], [])
            self.assertEqual(item['source']['value']['rules'][0]['values'], [0])
            self.assertTrue(item['overlay_provenance'])
            for evidence in item['overlay_provenance']:
                self.assertIsNone(evidence['value']['source_file_id'])
        for path in inputs['water_paths']:
            self.assertEqual(len(path['programme_ids']), 2)
            for pid in path['programme_ids']:
                req = self.sources['requirements'][pid]
                self.assertEqual(path['service'], req['service_definition'])
                self.assertEqual(path['schedule_id'], req['source_ruleset']['value']['id'])
                self.assertEqual(req['service_definition']['value']['load'],
                                 dict(req['original_demand']['value'], scope='building_service'))
        comparison = module.compare_apartment_fixed(self.sources, ref)
        self.assertEqual(comparison['counts'], {'fixed_rulesets': 90, 'water_paths': 20,
                         'alternative_views': 40, 'synthetic_area_probes': 40,
                         'source_created_control_associations': 120})
        self.assertTrue(comparison['passed'])
        self.assertEqual(comparison['fixed_hourly_max_abs_error'], 0)
        self.assertEqual(comparison['discrete_mismatches'], [])

    def test_independent_qualifications_and_exact_control_preimages(self):
        module, ref = self.reference()
        resources = module.compile_apartment_qualifications(self.sources, ref)
        qualifications = {key: v for (kind, key), v in resources.items()
                          if key.startswith('caller-water-qualification__')}
        pools = {key: v for (kind, key), v in resources.items()
                 if key.startswith('caller-water-qualification-set__')}
        self.assertEqual(len(qualifications), 40)
        self.assertEqual(len(pools), 8)
        self.assertEqual(sum(k.startswith('apartment-fixed-programme__') for _, k in resources), 84)
        seen = set()
        for pool in pools.values():
            _source(pool, '/pool')
            members = pool['value']['qualifications']
            self.assertEqual(members, sorted(members,
                key=lambda q: int(q['value']['requirement']['programme']['locator'][1:])))
            for q in members:
                pid = q['value']['programme_id']
                self.assertNotIn(pid, seen); seen.add(pid)
                self.assertEqual(q, qualifications['caller-water-qualification__' + pid])
        self.assertEqual(seen, set(self.sources['requirements']))
        for pid in self.sources['requirements']:
            q = qualifications['caller-water-qualification__' + pid]
            _source(q, '/qualification')
            self.assertEqual(set(q['value']), {'qualification_id', 'qualification_scope',
                'programme_id', 'requirement', 'association', 'fixed_controls', 'evidence'})
            _typed(q['value']['requirement'], 'caller_requirement', '/requirement')
            entries = [e for e in q['value']['evidence'] if e['locator'] == '/native_control_schedules']
            self.assertEqual(len(entries), 1)
            entry = entries[0]; value = entry['original_value']
            self.assertEqual(set(value), {'programme_id', 'requirement_id', 'association',
                'fixed_controls', 'reference_calendar', 'rules', 'evidence'})
            self.assertEqual(entry['original_unit'], None)
            blob = (ROOT / entry['source_path']).read_bytes()
            self.assertEqual(blob, canonical({'native_control_schedules': value}))
            self.assertEqual(hashlib.sha256(blob).hexdigest(), entry['source_sha256'])
            obj = {'path': entry['source_path'], 'sha256': entry['source_sha256'],
                   'locator': '/native_control_schedules', 'value': value}
            self.assertEqual(obj, resources['reference', 'caller-water-native-controls__' + pid])
            self.assertEqual(value['reference_calendar'], {'year': 2007, 'clock': 'local_standard_time', 'holidays': []})
            self.assertEqual(value['association'], q['value']['association'])
            self.assertEqual(value['fixed_controls'], q['value']['fixed_controls'])
            self.assertEqual(set(value['rules']), {'water_target_temperature',
                'water_sensible_fraction', 'water_latent_fraction'})
            for slot, rule in value['rules'].items():
                values = _native_constant(slot, rule)
                self.assertEqual(len(values), 8760)
                self.assertEqual(set(values), {60.0 if slot == 'water_target_temperature'
                                 else .2 if slot == 'water_sensible_fraction' else .05})

    def test_changed_source_or_capture_never_qualifies(self):
        module, ref = self.reference()
        # Each mutation breaks an independently captured original association,
        # even if another programme uses an equal numeric vector.
        changes = [
            lambda r: r['native']['water_paths'][0].__setitem__('path_id', 'wrong'),
            lambda r: r['native']['water_paths'][0]['probes'][0].__setitem__('native_peak_flow_m3_s', 3.48),
            lambda r: r['native']['water_paths'][0]['probes'][0]['controls']['target_temperature']['values'].__setitem__(0, 43.3),
            lambda r: r['native']['water_paths'][0]['probes'][0].__setitem__('floor_area_m2', 950),
            lambda r: r['native']['water_paths'][0]['probes'][0].__setitem__('is_flow_per_area', False),
            lambda r: r['native']['water_paths'][0]['probes'][0].__setitem__('source_density_gal_h_ft2', .003),
            lambda r: r['native']['water_paths'][0]['service']['value'].__setitem__('id', 'wrong-SID'),
            lambda r: r['native']['water_paths'][0]['programme_ids'].reverse(),
            lambda r: r['native']['schedules'][0]['values'].__setitem__(0, .12345),
            lambda r: r['native']['schedules'][0]['special_profiles'].__setitem__('SmrDsn', [[24, .7]]),
            lambda r: r['native'].__setitem__('reference_calendar', {'year': 2008, 'clock': 'local_standard_time', 'holidays': []}),
            lambda r: r['inputs']['water_paths'][0]['row']['value'].__setitem__('service_water_heating_target_temperature', 110),
            lambda r: r['inputs']['water_paths'][0]['row']['value'].__setitem__('service_water_heating_peak_flow_per_area', 3.48),
            lambda r: next(s for s in r['inputs']['schedules'] if s['overlay_provenance'])['source']['value']['rules'][0].__setitem__('values', [1]),
            lambda r: next(s for s in r['native']['schedules'] if s['overlay_provenance']).__setitem__('construction_kind', 'original_c8_named_ruleset'),
            lambda r: next(s for s in r['inputs']['schedules'] if s['overlay_provenance']).__setitem__('overlay_provenance', []),
            lambda r: next(s for s in r['inputs']['schedules'] if s['overlay_provenance'])['overlay_provenance'][0]['value'].__setitem__('source_file_id', 'forged-upstream'),
        ]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                bad = copy.deepcopy(ref); change(bad)
                # Exercise semantic checks beyond the immutable-byte gate too;
                # the real loader separately rejects any forged lock identity.
                bad['lock']['native_canonical_sha256'] = hashlib.sha256(canonical(bad['native'])).hexdigest()
                with self.assertRaises(GeneratorError):
                    module.compile_apartment_qualifications(self.sources, bad)
        bad = copy.deepcopy(self.sources)
        next(iter(bad['requirements'].values()))['original_demand']['value']['value'] *= 2
        with self.assertRaises(GeneratorError):
            module.apartment_fixed_capture_inputs(self.scope, bad)
        bad = copy.deepcopy(self.sources)
        next(iter(bad['requirements'].values()))['original_demand']['value']['unit'] = 'US gal/h/ft2'
        with self.assertRaises(GeneratorError):
            module.apartment_fixed_capture_inputs(self.scope, bad)

    def test_forged_lock_and_unused_pool_member_rejected(self):
        module, ref = self.reference()
        for field in ('inputs', 'vectors'):
            bad = copy.deepcopy(ref['lock']); bad[field]['payload_sha256'] = '0' * 64
            with self.assertRaises(GeneratorError): module.load_apartment_fixed_reference(bad)
        resources = module.compile_apartment_qualifications(self.sources, ref)
        for action in ('missing', 'changed', 'duplicate'):
            bad = copy.deepcopy(resources)
            pool = next(v for (_, k), v in bad.items() if k.startswith('caller-water-qualification-set__'))
            if action == 'missing': pool['value']['qualifications'].pop()
            elif action == 'changed': pool['value']['qualifications'][-1]['value']['programme_id'] = 'foreign'
            else: pool['value']['qualifications'].append(copy.deepcopy(pool['value']['qualifications'][0]))
            with self.assertRaises(GeneratorError):
                module.verify_apartment_qualifications(self.sources, ref, bad)

    def test_unknown_or_missing_native_fields_reject(self):
        module, ref = self.reference()
        for change in (
            lambda r: r['native']['water_paths'][0]['probes'][0].__setitem__('foreign_field', True),
            lambda r: r['native']['schedules'][0].pop('values'),
            lambda r: r['native']['schedules'][0]['day_rule_indices'].__setitem__(0, False),
            lambda r: r['native']['water_paths'][0]['probes'][0].__setitem__('space_multiplier', True),
        ):
            bad = copy.deepcopy(ref); change(bad)
            bad['lock']['native_canonical_sha256'] = hashlib.sha256(canonical(bad['native'])).hexdigest()
            try:
                module.compare_apartment_fixed(self.sources, bad)
            except Exception as error:
                self.assertIsInstance(error, GeneratorError)
            else:
                self.fail('Unknown or missing actual-native proof field qualified')


if __name__ == '__main__': unittest.main()
