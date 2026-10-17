"""Retail/Office P1: exact source records, independent role census, original selectors and nulls."""
import copy
import json
import unittest

from atlas_schedules.errors import GeneratorError
from scripts import schedule_generator_commercial_followup_sources as sources
from scripts.schedule_generator_physical_sets import compile_exact_inventory, compile_exact_requirements


class FollowupSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = sources.load_inputs()
        cls.strip = sources.extract_family_source_records('RetailStripmall', cls.inputs)
        cls.office = sources.extract_family_source_records('LargeOffice', cls.inputs)

    def config(self, artifact, template, view):
        return next(c for c in artifact['configurations'] if c['template'] == template and c['evidence_view'] == view)

    def mutated(self, name, change):
        inputs = copy.deepcopy(self.inputs); change(inputs[name]['value']); return inputs

    def test_exact_76_ids_10_compositions_26_services(self):
        scope = self.inputs['scope']['value']
        self.assertEqual(len(self.strip['programme_ids']) + len(self.office['programme_ids']), 76)
        self.assertEqual(sorted(self.strip['programme_ids'] + self.office['programme_ids']), sorted(p['id'] for p in scope['programmes']))
        self.assertEqual(len(self.strip['composition_ids']), 10); self.assertEqual(self.office['composition_ids'], [])
        self.assertEqual((len(self.strip['service_ids']), len(self.office['service_ids'])), (21, 5))
        self.assertEqual(len(self.strip['configurations']) + len(self.office['configurations']), 20)
        members = sum(len(c['source_records']['compositions'][0]['value']['members'])
                      for c in self.strip['configurations'] if c['source_records'] and c['source_records']['compositions'])
        self.assertEqual(members, 18)  # six code parents x three members carry records; DOE parents have no inventory
        self.assertEqual(sum(len(c['composition_ids']) for c in self.strip['configurations']), 10)

    def test_independent_complete_role_census(self):
        strip_roles = {c['template']: c['source_records']['ordered_fixture_roles'] for c in self.strip['configurations']
                       if c['source_records'] and c['evidence_view'] == 'source'}
        self.assertEqual(sorted(strip_roles), ['90.1-2007', '90.1-2013', '90.1-2019'])
        for template, roles in strip_roles.items():
            self.assertEqual(sorted(r['source_space']['name'] for r in roles),
                             ['LGstore1', 'LGstore2', 'SMstore1', 'SMstore2', 'SMstore3', 'SMstore5', 'SMstore6'])
            self.assertTrue(all(r['source_space']['handle'].startswith('{') for r in roles))
        office_roles = {c['template']: c['source_records']['ordered_fixture_roles'] for c in self.office['configurations']
                        if c['evidence_view'] == 'source'}
        self.assertEqual(len(office_roles), 5)
        for roles in office_roles.values():
            self.assertEqual([r['source_space']['name'] for r in roles], ['Core_bottom', 'Core_mid', 'Core_top'])
            self.assertEqual([r['geometry_operands']['zone_multiplier'] for r in roles], [1.0, 10.0, 1.0])
        self.assertEqual(sum(len(r) for r in strip_roles.values()) * 2, 42)
        self.assertEqual(sum(len(r) for r in office_roles.values()) * 2, 30)
        for artifact in (self.strip, self.office):
            for c in artifact['configurations']:
                if not c['source_records']: continue
                inventory = compile_exact_inventory(c['source_records'])
                self.assertTrue(all(r['consumed_extent'] == {'value': 1, 'unit': '1', 'evidence': r['geometry_operands']['evidence']}
                                    for r in inventory['payload']['roles']))
                self.assertTrue(all(r['geometry_operands']['floor_area_m2'] is None for r in inventory['payload']['roles']))

    def test_original_selectors_dates_views_and_nulls(self):
        c = self.config(self.office, '90.1-2013', 'reviewed')
        records = c['source_records']
        self.assertEqual(records['evidence_view'], 'reviewed')
        self.assertTrue(all(p['value']['evidence_view'] == 'reviewed' and p['value']['template'] == '90.1-2013' for p in records['programmes']))
        for obj in records['programmes']:
            original = self.inputs['programs']['value'][int(obj['locator'][1:])]
            self.assertEqual(obj['value'], original)
            self.assertEqual(obj['sha256'], self.inputs['programs']['sha256'])
        rules = records['ordered_fixture_roles'][0]['schedule_authority']['canonical_schedule']['value']
        self.assertEqual(rules['id'], records['ordered_fixture_roles'][0]['service_definition']['value']['load']['schedule_id'])
        self.assertTrue(all(c['absence']['status'] == 'no_frozen_service_path' and c['source_records'] is None
                            for c in self.strip['configurations'] if c['template'].startswith('DOE')))
        # Frozen status counts stated in the subplan; gaps stay in the denominator.
        strip = {f'{v}|{q}|known': 20 for v in ('source', 'reviewed') for q in ('occupancy', 'lighting', 'electric_equipment')}
        strip.update({'source|additional_lighting|known': 12, 'source|additional_lighting|unknown': 8,
                      'reviewed|additional_lighting|known': 12, 'reviewed|additional_lighting|unknown': 8,
                      'source|gas_equipment|unknown': 20, 'reviewed|gas_equipment|known': 20})
        self.assertEqual(self.strip['load_status'], dict(sorted(strip.items())))
        office = {}
        for v in ('source', 'reviewed'):
            office.update({f'{v}|occupancy|known': 7, f'{v}|occupancy|unknown': 11, f'{v}|lighting|known': 13,
                           f'{v}|lighting|unknown': 5, f'{v}|electric_equipment|known': 13,
                           f'{v}|electric_equipment|unknown': 5, f'{v}|additional_lighting|unknown': 18})
        office.update({'source|gas_equipment|unknown': 18, 'reviewed|gas_equipment|known': 18})
        self.assertEqual(self.office['load_status'], dict(sorted(office.items())))

    @staticmethod
    def labelled_methods(records):
        """Test-only structural method references; never written to an artifact or qualified."""
        from tests.test_schedule_generator_physical_authority_v1_2 import consumed, evidence, source
        records = copy.deepcopy(records)
        records['method_references'] = [source({'program_id': p['value']['id'], 'source_hoo_configuration_id': 'labelled-structural-context',
            'context_evidence_view': p['value']['evidence_view'], 'method_consumed_context': consumed(),
            'original_method': source({'labelled': 'structural only'}), 'evidence': evidence()}) for p in records['programmes']]
        return records

    def test_parent_alias_does_not_create_role(self):
        c = self.config(self.strip, '90.1-2013', 'source')
        records = c['source_records']; inventory = compile_exact_inventory(records)
        parent_sids = next(p['value']['service_ids'] for p in records['programmes'] if p['value'].get('composition_id'))
        self.assertEqual(len(inventory['payload']['roles']), 7); self.assertEqual(len(parent_sids), 7)
        # The P1 boundary: no method is compiled yet, so requirements stop at the first water programme.
        with self.assertRaises(GeneratorError) as caught: compile_exact_requirements(records, inventory)
        self.assertEqual(caught.exception.code, 'requires_binding')
        self.assertTrue(caught.exception.path.startswith('/method_references/'))
        records = self.labelled_methods(records)
        leaves = copy.deepcopy(records)
        leaves['programmes'] = [p for p in records['programmes'] if not p['value'].get('composition_id')]
        leaves['method_references'] = [m for m in records['method_references']
                                       if any(m['value']['program_id'] == p['value']['id'] for p in leaves['programmes'])]
        leaves['compositions'] = []
        requirements = compile_exact_requirements(leaves, inventory)
        self.assertEqual(len(requirements), 7)
        self.assertTrue(all(r['kind'] == 'original_service_reference' and len(r['expected_role_ids']) == 1 for r in requirements))
        # Until the reviewed reference-union kind exists, the parent keeps today's rejection path.
        with self.assertRaises(GeneratorError) as caught: compile_exact_requirements(records, inventory)
        self.assertEqual((caught.exception.code, caught.exception.path), ('source_integrity', '/source_requirements'))

    def test_changed_sources_and_fabrications_reject(self):
        def drop_fixture(c):
            row = next(r for r in c['draw_paths'] if r['path_id'] == 'RetailStripmall|90.1-2013|main|SMstore1')
            row['physical_fixture_locations'] = []; row['flow_instance_count'] = 0
        def swap_view(p):
            next(x for x in p if x.get('building_type') == 'LargeOffice')['evidence_view'] = 'reviewed-alt'
        def fabricated_service(s):
            extra = copy.deepcopy(next(x for x in s if x.get('building_type') == 'LargeOffice')); extra['id'] = 'service-fabricated'
            s.append(extra)
        def flow(c):
            next(r for r in c['draw_paths'] if r['building_type'] == 'LargeOffice')['rated_flow_m3_s'] *= 2
        cases = [('completion', drop_fixture, 'RetailStripmall'), ('programs', swap_view, 'LargeOffice'),
                 ('services', fabricated_service, 'LargeOffice'), ('completion', flow, 'LargeOffice')]
        for name, change, family in cases:
            with self.subTest(change=change.__name__), self.assertRaises(GeneratorError):
                artifact = sources.extract_family_source_records(family, self.mutated(name, change))
                for c in artifact['configurations']:
                    if c['source_records']: compile_exact_inventory(c['source_records'])
        inputs = copy.deepcopy(self.inputs); inputs['stripmall_geometry']['raw'] = inputs['stripmall_geometry']['raw'].replace(b'SMstore1', b'SMstoreX')
        with self.assertRaises(GeneratorError): sources.extract_family_source_records('RetailStripmall', inputs)

    def test_geometry_census_is_a_locked_file_and_roles_follow_census_order(self):
        import hashlib, re
        for artifact in (self.strip, self.office):
            census = artifact['geometry_census']; blob = (sources.ROOT/census['path']).read_bytes()
            self.assertEqual({'sha256': hashlib.sha256(blob).hexdigest(), 'size_bytes': len(blob)},
                             {k: census[k] for k in ('sha256', 'size_bytes')})
            document = json.loads(blob)
            for c in artifact['configurations']:
                if not c['source_records']: continue
                geometry = c['source_records']['geometry']
                self.assertEqual((geometry['path'], geometry['sha256']), (census['path'], census['sha256']))
                self.assertEqual(document[geometry['locator'][1:]], geometry['value'])
        # Stripmall roles follow the completion census (draw path) order, the same as Appendix B.
        appendix = [s['fixture_locations'][0] for s in self.inputs['scope']['value']['services']
                    if s['family'] == 'RetailStripmall' and s['template'] == '90.1-2013']
        roles = self.config(self.strip, '90.1-2013', 'source')['source_records']['ordered_fixture_roles']
        self.assertEqual([r['source_space']['name'] for r in roles], appendix)
        # Handles agree with an independent parse of the locked OSM.
        text = (sources.ROOT/sources.INPUTS['stripmall_geometry']).read_text(encoding='utf-8')
        independent = dict((name, handle) for handle, name in re.findall(r'OS:Space,\s*\n\s*(\{[0-9a-f-]+\}),[^\n]*\n\s*([^,]+),', text))
        self.assertTrue(all(independent[r['source_space']['name']] == r['source_space']['handle'] for r in roles))
        # All 40 Stripmall programme objects and 10 compositions are carried, DOE included.
        self.assertEqual((len(self.strip['programmes']), len(self.strip['compositions'])), (40, 10))
        self.assertTrue(all(o['value'] == self.inputs['programs']['value'][int(o['locator'][1:])] for o in self.strip['programmes']))

    def test_geometry_bytes_are_rehashed_and_wrong_roles_reject(self):
        inputs = copy.deepcopy(self.inputs)
        inputs['stripmall_geometry']['raw'] = inputs['stripmall_geometry']['raw'].replace(b'{6d54358c', b'{6d54358d', 1)
        with self.assertRaises(GeneratorError): sources.extract_family_source_records('RetailStripmall', inputs)
        def wrong_store(c):  # equal-count wrong role: SMstore1 replaced by the unlisted SMstore4
            next(r for r in c['draw_paths'] if r['path_id'] == 'RetailStripmall|90.1-2013|main|SMstore1')['physical_fixture_locations'] = ['SMstore4']
        def extra_store(c):
            next(r for r in c['draw_paths'] if r['path_id'] == 'RetailStripmall|90.1-2013|main|SMstore1')['physical_fixture_locations'].append('SMstore4')
        for change in (wrong_store, extra_store):
            with self.subTest(change=change.__name__), self.assertRaises(GeneratorError):
                sources.extract_family_source_records('RetailStripmall', self.mutated('completion', change))

    def test_written_artifacts_match_extraction(self):
        for family, slug in sources.FAMILIES.items():
            with self.subTest(family=family):
                written = json.loads((sources.ROOT/'data/schedule-generator'/slug/'source-inventory.json').read_text(encoding='utf-8'))
                self.assertEqual(written, json.loads(json.dumps(sources.extract_family_source_records(family, self.inputs))))
                lock = json.loads((sources.ROOT/'sources'/f'schedule-generator-{slug}-lock.json').read_text(encoding='utf-8'))
                blob = (sources.ROOT/lock['artifact']['path']).read_bytes()
                import hashlib
                self.assertEqual(lock['artifact']['sha256'], hashlib.sha256(blob).hexdigest())
                self.assertEqual(lock['producer']['sha256'], hashlib.sha256((sources.ROOT/lock['producer']['path']).read_bytes()).hexdigest())


if __name__ == '__main__': unittest.main()
