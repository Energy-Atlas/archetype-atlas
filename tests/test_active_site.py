import importlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.definition_contract import DefinitionBundle, record, parameter


def pilot_bundle():
    source = {'id': 'source', 'building_type': 'MediumOffice', 'template': '90.1-2019', 'source_family': 'code_prototype_rules'}
    program = record('program', source, 'Office')
    program.update(id='program-pilot', detail='SourcePrograms', available_details=['SourcePrograms'],
                   loads=[{'demand_id': 'lighting-pilot', 'quantity': 'lighting', 'unit': 'W/m2', 'basis': 'floor_area',
                           'value': None, 'schedule_id': 'schedule-pilot', 'thermal_effects': {}, 'scope': 'program'}])
    construction = record('construction', source, 'Wall')
    construction.update(id='construction-pilot', layers=[{'material_id': 'material-pilot', 'properties': {'name': 'Brick'}}])
    system = record('hvac_system', source, 'Fan system')
    system.update(id='system-pilot', component_ids=['component-pilot'], system_type='Fan')
    return DefinitionBundle(programs=[program], constructions=[construction], hvac_systems=[system],
        materials=[{'id': 'material-pilot', 'name': 'Brick', 'density_kg_m3': 1800}],
        components=[{'id': 'component-pilot', 'role': 'fan', 'schedule_ids': ['schedule-pilot']}],
        schedules=[{'id': 'schedule-pilot', 'source_name': 'Office week', 'units': 'dimensionless', 'schedule_type': 'fraction',
                    'time_resolution_minutes': 60, 'rules': [{'day_types': 'Default', 'start_date': '2000-01-01', 'end_date': '2000-12-31', 'values': [1]}]}])


class ActiveSiteTests(unittest.TestCase):
    def test_active_output_checker_rejects_retired_routes_search_and_incomplete_exports(self):
        from scripts import site_check
        self.assertTrue(hasattr(site_check, 'check_active'), 'Active publication checks are missing')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.generator()(pilot_bundle(), root, publish=False)
            # The publication checker consumes rendered routes, not Markdown inputs.
            for page in list(root.glob('definitions/*.md')) + list(root.glob('objects/*.md')):
                output = page.with_suffix('') / 'index.html';output.parent.mkdir()
                output.write_text(page.read_text())
            (root / 'search').mkdir();search = root / 'search/search_index.json'
            search.write_text(json.dumps({'docs': [{'location': 'definitions/program-pilot/'}]}))
            self.assertEqual(site_check.check_active(root), [])
            (root / 'downloads').mkdir()
            search.write_text(json.dumps({'docs': [{'location': 'releases/v0.2.0/catalogue/'}]}))
            program = root / 'definitions/program-pilot/index.html'
            program.write_text(program.read_text().replace('data-defaulted=', 'data-disabled='))
            errors = site_check.check_active(root)
            self.assertTrue(any('downloads' in e for e in errors), errors)
            self.assertTrue(any('search' in e for e in errors), errors)
            self.assertTrue(any('defaulted' in e for e in errors), errors)

    def generator(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.active_site'), 'Current-only site generator is missing')
        return importlib.import_module('scripts.active_site').generate_active_site

    def test_current_build_does_not_emit_legacy_content(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'site-docs'
            result = self.generator()(pilot_bundle(), root, publish=False)
            self.assertEqual(result['counts']['programs'], 1)
            for retired in ('releases', 'downloads', 'downloads.md', 'delivery/v1', 'resolution-supplements', 'commercial-completion', 'water-reporting'):
                self.assertFalse((root / retired).exists(), retired)
            self.assertNotIn('releases/', (root / 'index.md').read_text())
            self.assertTrue((root / 'notices').exists())

    def test_nested_references_open_designated_object_pages(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.generator()(pilot_bundle(), root, publish=False)
            program = (root / 'definitions/program-pilot.md').read_text()
            self.assertIn('../objects/schedule-pilot.md', program)
            construction = (root / 'definitions/construction-pilot.md').read_text()
            self.assertIn('../objects/material-pilot.md', construction)
            component = (root / 'objects/component-pilot.md').read_text()
            self.assertIn('/objects/schedule-pilot/', component)
            schedule = (root / 'objects/schedule-pilot.md').read_text(encoding='utf-8')
            self.assertIn('schedule-viewer', schedule)
            self.assertIn('Unique day', schedule)
            self.assertIn('Annual', schedule)
            self.assertIn('schedule-static', schedule)
            self.assertIn('00:00–01:00', schedule)

    def test_every_object_has_expandable_json_and_program_default_descriptor(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.generator()(pilot_bundle(), root, publish=False)
            for path in list((root / 'definitions').glob('*.md')) + list((root / 'objects').glob('*.md')):
                content = path.read_text()
                self.assertIn('object-json', content)
                self.assertIn('Copy JSON', content)
                self.assertIn('data-raw=', content)
            page = (root / 'definitions/program-pilot.md').read_text()
            self.assertIn('data-defaulted=', page)
            self.assertIn('Unknown', page)
            self.assertIn('default: 0', page)
            manifest = json.loads((root / 'object-index.json').read_text())
            self.assertIn('schedule-pilot', manifest)


if __name__ == '__main__': unittest.main()
