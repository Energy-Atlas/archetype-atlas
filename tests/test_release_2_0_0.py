"""Release 2.0.0: the full snapshot of release 1.6.0 (ADR 0046), the only release in the tree."""
import io
import json
import unittest
from unittest import mock

from jsonschema import Draft202012Validator

from scripts import atlas_snapshot
from scripts.atlas_exports import EXPORTER_INPUTS
from scripts.common import ROOT, load_json

FROZEN = ('releases', 'definition-releases', 'resolution-releases', 'water-reporting-releases', 'completion-releases',
          'construction-releases', 'construction-equivalent-releases', 'construction-mass-releases',
          'construction-foundation-releases', 'water-releases')


class Release200Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.listed = atlas_snapshot.verify()
        cls.files = atlas_snapshot.files()

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.listed, cls.files

    def test_full_snapshot_of_1_6_0_and_the_only_release(self):
        self.assertIsNone(self.listed['base_release'])
        self.assertEqual((self.listed['snapshot_of']['release'], self.listed['status']), ('1.6.0', 'released'))
        self.assertEqual(sorted(p.name for p in (ROOT/'data/atlas-releases').iterdir()), ['v2.0.0'])
        self.assertIn(EXPORTER_INPUTS, self.files)

    def test_generator_recipes_for_the_90_1_and_doe_ref_programs(self):
        counts = self.listed['counts']
        self.assertEqual(counts['programs_with_recipes'] + counts['programs_without_recipes'], counts['programs'])
        generators = [p for p in self.files if p.endswith('/generator.json')]
        self.assertTrue(all(p.split('/')[1].startswith(('90-1-', 'doe-ref-')) for p in generators))
        recipes = json.loads(self.files[next(p for p in generators if '/90-1-2019/medium-office/' in p)])
        entry = next(iter(recipes.values()))
        self.assertLessEqual(set(entry), {'source', 'reviewed'})
        self.assertIn('slots', entry.get('source') or entry['reviewed'])
        # DOE Ref recipes are written from the release, under release IDs (stage X1.2)
        doe = json.loads(self.files['commercial/doe-ref-1980-2004/medium-office/generator.json'])
        self.assertTrue(all(set(e) == {'source'} and e['source']['program_id'] == pid for pid, e in doe.items()))

    def test_daylighting_fractions_are_plain_values(self):
        programs = [json.loads(d) for p, d in self.files.items() if p.startswith('commercial/') and '/programs/' in p]
        controls = [p['lighting_controls'] for p in programs if 'lighting_controls' in p]
        self.assertTrue(any(c.get('daylighting') for c in controls))
        self.assertFalse(any('geometry_dependent' in c for c in controls))
        self.assertEqual(self.listed['counts']['plain_daylighting_programs'],
                         sum(1 for c in controls if c['source'] == 'pnnl_prototype' and c['status'] == 'known'))

    def test_exporter_inputs(self):
        carried = json.loads(self.files[EXPORTER_INPUTS])
        self.assertEqual((len(carried['capped_services']), len(carried['capped_programs']), len(carried['inactive_controls'])),
                         (3, 3, 43))

    def test_exports_open_no_frozen_folder(self):
        from scripts.atlas_exports import Release
        release = Release(files=self.files, release='2.0.0')
        opened = []
        real = io.open

        def guarded(file, *args, **kwargs):
            path = str(file).replace('\\', '/')
            if any('/data/'+name+'/' in path for name in FROZEN) or '/data/atlas-releases/v1.' in path:
                opened.append(path)
            return real(file, *args, **kwargs)
        programs = sorted(release.program_ids())
        dwellings = sorted(release.dwellings.program_ids())
        with mock.patch('io.open', guarded), mock.patch('builtins.open', guarded):
            for pid in [*programs[::150], *dwellings[::8]]:
                for version in ('source', 'filled'):
                    try:
                        release.program(pid, version)
                    except ValueError as error:
                        self.assertRegex(str(error), 'source only|water heaters', pid)
            for sid in sorted(release.constructions.sets)[::20]:
                key = sorted(release.constructions.sets[sid]['contexts'])[0]
                release.construction(sid, key, 'unified')
        self.assertEqual(opened, [])

    def test_exports(self):
        from scripts.atlas_exports import Release
        release = Release(files=self.files, release='2.0.0')
        program_id = next(p for p in release.program_ids() if p.startswith('90-1-2019.medium-office.source.whole'))
        document = release.program(program_id, 'filled')
        self.assertEqual((document['schema_version'], document['source']['release']), ('5.4.0', 'atlas-release-2.0.0'))
        self.assertNotIn('geometry_dependent', document.get('lighting_controls', {}))


class AlternateTests(unittest.TestCase):
    """The PNNL prototype constructions recorded as alternates (stage B3, user decision P1)."""

    def test_alternates_export_with_their_assemblies_and_evidence(self):
        from scripts.atlas_exports import Release
        from scripts.construction_alternates import differs
        release = Release()
        sid = next(s for s in sorted(release.constructions.sets) if s.startswith('90-1-2019.medium-office.'))
        document = release.construction(sid, '5-b', 'detailed')
        self.assertEqual(document['schema_version'], '4.3.0')
        wall = document['alternates']['ExteriorWall']
        self.assertEqual([v['construction'] for v in wall['variants']], ['nonres_ext_wall_grd', 'nonres_ext_wall_mid', 'nonres_ext_wall_top'])
        self.assertAlmostEqual(sum(v['area_share'] for v in wall['variants']), 1.0, places=5)
        self.assertTrue(any(differs(v['values']['layer_resistance'], wall['atlas_values']['layer_resistance']) for v in wall['variants']))
        for variant in wall['variants']:
            assembly = document['assemblies'][variant['assembly_id']]
            self.assertEqual(assembly['source_family'], 'pnnl_prototype')
            self.assertTrue(all(layer['material_id'] in document['materials'] for layer in assembly['layers']))
            self.assertIn(variant['evidence_id'], document['evidence'])
        self.assertNotIn('GroundFloor', document['alternates'])  # the F-factors agree (review S3)

    def test_only_the_90_1_templates_carry_alternates(self):
        from scripts.atlas_exports import Release
        release = Release()
        carriers = {sid.split('.')[0] for sid, record in release.constructions.sets.items()
                    if any('alternates' in c.get('detailed', {}).get('fields', {}) for c in record['contexts'].values())}
        self.assertEqual(carriers, {'90-1-2007', '90-1-2013', '90-1-2019'})

    def test_every_prototype_assembly_and_material_is_a_valid_library_record(self):
        schema = load_json(ROOT/'schemas/construction-json-v4.3.schema.json')
        checks = {table: Draft202012Validator({'$ref': f'#/$defs/{definition}', '$defs': schema['$defs']})
                  for table, definition in (('assemblies', 'assembly'), ('materials', 'material'))}
        counted = 0
        for template in ('90-1-2007', '90-1-2013', '90-1-2019'):
            for table, check in checks.items():
                records = load_json(ROOT/f'data/atlas-releases/v2.0.0/commercial/{template}/library/{table}.json')
                prototype = [r for r in records.values() if r.get('source_family') == 'pnnl_prototype'
                             or any(str(e).startswith('construction-evidence-') for e in r.get('property_evidence', {}).values())]
                for record in prototype:
                    self.assertEqual([e.message for e in check.iter_errors(record)], [], record['id'])
                counted += len(prototype)
        self.assertGreater(counted, 1000)


class GroundFloorTests(unittest.TestCase):
    """The IECC adiabatic F-factor slabs are ground floors (BEMGen's report, ADR 0046 section 11)."""

    def test_no_assignment_contradicts_its_target_and_no_slab_is_an_interior_floor(self):
        from scripts.atlas_constructions import ConstructionSuite
        from scripts.release_editor import GROUND_MODELS
        release = ROOT/'data/atlas-releases/v2.0.0'
        evidence = {p.relative_to(release).as_posix(): p.read_text(encoding='utf-8') for p in (release/'evidence/commercial').rglob('*.json')}
        corrected = 0
        for folder in sorted((release/'commercial').glob('iecc-*')):
            files = {p.relative_to(release).as_posix(): p.read_text(encoding='utf-8') for p in folder.rglob('*.json')
                     if '/constructions/' in p.as_posix() or '/library/' in p.as_posix()}
            suite = ConstructionSuite({**files, **evidence})
            ground = {k for k, a in suite.library['assemblies'].items() if a.get('model') in GROUND_MODELS}
            for sid, record in suite.sets.items():
                for key in record['contexts']:
                    document = suite.export(sid, key, 'detailed')
                    for role, component in document['components'].items():
                        allowed = component.get('target', {}).get('boundary_conditions')
                        for assignment in component['assignments']:
                            if allowed and 'boundary_condition' in assignment['when']:
                                self.assertIn(assignment['when']['boundary_condition'], allowed, (sid, key, role))
                    budgets = document['mass_accounting'].get('physical_capacity_budgets', {}).get('InteriorFloor', [])
                    self.assertFalse(any(b['source_assembly_id'] in ground for b in budgets), (sid, key))
                    corrected += sum(d['rule'] == 'source_boundary_correction' for d in document['metadata']['selection_decisions'])
        self.assertEqual(corrected, 6*5*19)  # editions x types x climates, one corrected rule each


class ExportBytesTests(unittest.TestCase):
    """The exports are the same bytes whatever the hash seed (BEMGen's fixture check, D-173)."""

    SCRIPT = '''
import hashlib, json
from scripts.atlas_constructions import ConstructionSuite
from scripts.common import ROOT
release = ROOT/'data/atlas-releases/v2.0.0'
paths = [*(release/'commercial/iecc-2021').rglob('*.json'), *(release/'evidence/commercial').rglob('*.json')]
suite = ConstructionSuite({p.relative_to(release).as_posix(): p.read_text(encoding='utf-8') for p in paths
                           if '/constructions/' in p.as_posix() or '/library/' in p.as_posix() or '/evidence/' in p.as_posix()})
digest = hashlib.sha256()
for sid in sorted(suite.sets):
    for representation in ('detailed', 'unified'):
        digest.update(json.dumps(suite.export(sid, sorted(suite.sets[sid]['contexts'])[0], representation), indent=2).encode())
print(len(suite.sets), digest.hexdigest())
'''

    def test_construction_exports_do_not_follow_the_hash_seed(self):
        import os
        import subprocess
        import sys
        runs = {subprocess.run([sys.executable, '-c', self.SCRIPT], cwd=ROOT, capture_output=True, text=True, check=True,
                               env={**os.environ, 'PYTHONHASHSEED': seed}).stdout for seed in ('1', '2', '3')}
        self.assertEqual(len(runs), 1, runs)
        self.assertGreater(int(next(iter(runs)).split()[0]), 10)


class ExportSchemaTests(unittest.TestCase):
    def test_schemas_are_derived_from_the_previous_majors(self):
        from scripts import atlas_exports
        for name, schema in atlas_exports.derived_schemas().items():
            self.assertEqual(load_json(ROOT/'schemas'/name), schema, name)
            Draft202012Validator.check_schema(schema)

    def test_the_shared_mass_contract_is_the_one_the_constructions_embed(self):
        from scripts.atlas_exports import ALTERNATES, MASS, MINOR
        shared = load_json(ROOT/'schemas'/MASS[0])['$defs']
        self.assertIn('evidence_id', shared['massEntry']['properties'])
        for name in (ALTERNATES['detailed'][0], MINOR['unified'][0]):
            embedded = load_json(ROOT/'schemas'/name)['$defs']
            self.assertEqual({k: embedded[k] for k in shared}, shared, name)

    def test_only_release_2_0_0_reads_from_the_tree(self):
        from scripts.atlas_exports import Release
        with self.assertRaisesRegex(ValueError, 'frozen-data-2026-10-27'):
            Release(release='1.6.0')


if __name__ == '__main__':
    unittest.main()
