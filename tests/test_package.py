"""The atlas-schedules package: its version is the generator's, and it ships the data the generator reads (ADR 0049, ADR 0051)."""
import json
import re
import tempfile
import tomllib
import unittest
from pathlib import Path

import yaml

import atlas_schedules
from atlas_schedules.release import Release, TreeStore, ViewStore, VIEW_INDEX, set_releases
from scripts import atlas_delta, build_generator_view
from scripts.common import ROOT

RELEASE_VERSION = re.compile(r'^\d+\.\d+\.\d+$')
QUICK_START = ROOT/'docs/examples/schedule-generator/office-and-retail.json'


def pyproject():
    return tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))


def workflow(name):
    return yaml.load((ROOT/'.github/workflows'/name).read_text(encoding='utf-8'), Loader=yaml.BaseLoader)


def commands(flow):
    return '\n'.join(s.get('run', '') for j in flow['jobs'].values() for s in j['steps'])


class PackageTests(unittest.TestCase):
    def test_package_version_is_the_generator_version(self):
        project = pyproject()
        self.assertEqual(project['project']['name'], 'atlas-schedules')
        self.assertIn('version', project['project']['dynamic'])
        self.assertEqual(project['tool']['setuptools']['dynamic']['version'], {'attr': 'atlas_schedules.__version__'})
        self.assertRegex(atlas_schedules.__version__, RELEASE_VERSION)  # a tagged release, not a dev build
        self.assertEqual(atlas_schedules.__version__, atlas_delta.GENERATOR[atlas_delta.RELEASE]['version'])

    def test_bundles_name_the_package_version_and_the_release(self):
        from atlas_schedules.generator import generate
        request = {'schema_version': '4.0.0', 'seed': 1, 'instances': [
            {'key': 'office', 'program_id': '90-1-2013.medium-office.source.whole-building-md-office.672bf4', 'extent': {'floor_area': 100},
             'operating_group': 'building', 'service_links': {'90-1-2013.medium-office.main.87f1fd': 'water'}},
            {'key': 'water', 'service_id': '90-1-2013.medium-office.main.87f1fd', 'physical_id': 'heater',
             'configuration_id': 'medium_office__90_1_2013__reviewed', 'extent': {'floor_area': 100}, 'operating_group': 'building'}]}
        bundle = generate(request)
        self.assertEqual(bundle['generator_version'], atlas_schedules.__version__)
        self.assertEqual(bundle['schema_version'], atlas_schedules.REQUEST_SCHEMA_VERSION)
        self.assertEqual(bundle['release']['version'], atlas_delta.RELEASE)
        self.assertEqual(bundle['owners'][0]['values'], 'filled')

    def test_runtime_requirements_and_entry_points(self):
        project = pyproject()['project']
        self.assertEqual(project['requires-python'], '>=3.11')
        self.assertEqual(sorted(d.split('>=')[0] for d in project['dependencies']), ['jsonschema', 'numpy'])
        self.assertTrue(all('>=' in d for d in project['dependencies']))
        pinned = {line.split('==')[0] for line in (ROOT/'requirements.txt').read_text(encoding='utf-8').split()}
        self.assertTrue({'numpy', 'jsonschema'} <= pinned)
        self.assertEqual(project['scripts'], {'atlas-schedules': 'atlas_schedules.__main__:main'})
        self.assertEqual(project['license'], 'MIT')
        dev = (ROOT/'requirements-dev.txt').read_text(encoding='utf-8')
        self.assertRegex(dev, r'(?m)^build==')
        self.assertNotIn('build', (ROOT/'requirements.txt').read_text(encoding='utf-8'))

    def test_package_data_covers_every_file_the_generator_reads(self):
        patterns = pyproject()['tool']['setuptools']['package-data']['atlas_schedules']
        package = ROOT/'atlas_schedules'
        shipped = {p.relative_to(package).as_posix() for pattern in patterns for p in package.glob(pattern) if p.is_file()}
        present = {p.relative_to(package).as_posix() for folder in ('data', 'schemas') for p in (package/folder).rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts}
        self.assertEqual(present - shipped, set())
        self.assertFalse(any(p.startswith(('data/recipes/', 'data/services/', 'data/configurations/')) for p in present))
        self.assertTrue(any(p.startswith('data/residential/characteristics/') and p.endswith('.gz') for p in shipped))
        self.assertIn('schemas/request-v4.schema.json', shipped)
        self.assertNotIn('schemas/request-v3.schema.json', present)
        self.assertTrue(any(p.startswith('data/notices/') for p in shipped))
        # The generator view is built before the wheel; its files match the package-data globs once built.
        view = f'data/atlas-release/{VIEW_INDEX}'
        self.assertTrue(any(Path(view).match(pattern) for pattern in patterns), patterns)
        self.assertIn('atlas_schedules/data/atlas-release/', (ROOT/'.gitignore').read_text(encoding='utf-8'))

    def test_generator_view_equals_the_release_tree(self):
        """The view the wheel bundles reads as the release does: same records, same provenance, same bundle."""
        from atlas_schedules import programmes
        from atlas_schedules.generator import generate
        tree = Release(TreeStore(atlas_delta.folder_of(atlas_delta.RELEASE)))
        files = build_generator_view.build(tree)
        index = json.loads(files[VIEW_INDEX])
        self.assertEqual((index['kind'], index['release'], index['manifest_sha256']),
                         ('atlas_release_generator_view', tree.version, tree.manifest_sha256))
        self.assertEqual(index['base_releases'], ['2.1.0', '2.0.0'])
        self.assertEqual(len(index['folders']), 90)
        with tempfile.TemporaryDirectory() as temporary:
            build_generator_view.write(files, Path(temporary))
            view = Release(ViewStore(Path(temporary)))
            self.assertEqual(view.provenance(), tree.provenance())
            self.assertEqual(set(view.program_paths), set(view.program_paths) & set(tree.program_paths))
            catalogue = [(rid, v) for folder in tree.generation_folders()
                         for rid, block in tree.generation(folder)['programs'].items() for v in block['views']]
            for rid, values in catalogue[::53]:
                self.assertEqual(programmes.assemble(view, rid, values), programmes.assemble(tree, rid, values), rid)
            self.assertEqual(view.json('definition-map.json'), tree.json('definition-map.json'))
            request = json.loads(QUICK_START.read_text(encoding='utf-8'))
            try:
                set_releases(temporary)
                from_view = json.dumps(generate(request), sort_keys=True)
            finally:
                set_releases(None)
            self.assertEqual(from_view, json.dumps(generate(request), sort_keys=True))

    def test_release_workflow_builds_the_wheel_for_a_matching_tag(self):
        flow = workflow('atlas-schedules-release.yml')
        self.assertEqual(flow['on']['push']['tags'], ['atlas-schedules-v*'])
        run = commands(flow)
        for command in ('requirements-dev.txt', 'scripts.build_generator_view', 'scripts.build_release_assets --wheel',
                        'atlas_schedules.__version__', 'SHA256SUMS.txt', 'gh release'):
            self.assertIn(command, run)
        self.assertEqual(flow['jobs']['wheel']['permissions'], {'contents': 'write'})

    def test_data_release_workflow_attaches_the_archive_for_a_matching_tag(self):
        flow = workflow('atlas-data-release.yml')
        self.assertEqual(flow['on']['push']['tags'], ['v*'])
        run = commands(flow)
        for command in ('scripts.atlas_delta --verify', 'scripts.build_release_assets --data', 'SHA256SUMS.txt', 'gh release'):
            self.assertIn(command, run)
        self.assertEqual(flow['jobs']['archive']['permissions'], {'contents': 'write'})


if __name__ == '__main__':
    unittest.main()
