"""JSON Schemas of generation.json, the bundle and the release records (ADR 0056), and the 2.3.0 manifest inputs
(ADR 0055): every schema is Draft 2020-12; the published releases validate as they are; the generator refuses
an invalid generation.json; the next release's manifest states the generation coverage by folder class."""
import hashlib
import json
from pathlib import Path
import unittest

import jsonschema

from atlas_schedules.errors import GeneratorError
from atlas_schedules.release import Release
from scripts import atlas_delta, release_schemas, schema_revisions

ROOT = Path(__file__).resolve().parents[1]


class Schemas(unittest.TestCase):
    def test_every_schema_is_draft_2020_12(self):
        for path in schema_revisions.schema_files():
            schema = json.loads((ROOT/path).read_text(encoding='utf-8'))
            with self.subTest(schema=path):
                self.assertEqual(schema['$schema'], 'https://json-schema.org/draft/2020-12/schema')
                jsonschema.Draft202012Validator.check_schema(schema)

    def test_every_schema_matches_its_recorded_revision(self):
        self.assertEqual(schema_revisions.problems(), [])

    def test_published_manifests_and_deltas_validate(self):
        for release in ('2.0.0', '2.1.0', '2.2.0', '2.3.0', '2.4.0', '2.5.0', '2.6.0'):
            folder = atlas_delta.folder_of(release)
            files = {'manifest.json': (folder/'manifest.json').read_bytes()}
            if release != '2.0.0':
                files.update({p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*.json')})
            with self.subTest(release=release):
                self.assertEqual(release_schemas.errors(files), [])

    def test_release_records_validate(self):
        # A fixed sample of the resolved 2.2.0 records (scripts.release_schemas --all checks every one).
        files = atlas_delta.files('2.2.0')
        sample = {p: d for n, (p, d) in enumerate(sorted(files.items()))
                  if release_schemas.schema_for(p) and (n % 11 == 0 or p == 'definition-map.json')}
        kinds = {release_schemas.schema_for(p).name for p in sample}
        self.assertEqual(len(kinds), 5)   # programs, schedules, services, generation, definition map
        self.assertEqual(release_schemas.errors(sample), [])

    def test_an_unknown_value_is_null(self):
        program = json.loads(next(d for p, d in sorted(atlas_delta.files('2.2.0').items()) if '/programs/source/' in p))
        unknown = next(i for i, load in enumerate(program['loads']) if load['status'] == 'unknown')
        program['loads'][unknown]['value'] = 0.0
        self.assertTrue(release_schemas.errors({'commercial/a/b/programs/source/x.json': program}))


class GeneratorBoundary(unittest.TestCase):
    def test_an_invalid_generation_json_is_refused_with_its_path(self):
        release = Release(atlas_delta.folder_of('2.2.0'))
        folder = 'commercial/90-1-2019/medium-office'
        doc = json.loads(json.dumps(release.generation(folder)))
        block = next(iter(doc['programs'].values()))
        block['views']['source'] = {'configuration_id': 'medium_office__90_1_2019__source', 'extra': 1}
        with self.assertRaises(GeneratorError) as raised:
            Release(release.store, generation={folder: doc}).generation(folder)
        self.assertEqual(raised.exception.code, 'release')
        self.assertIn(f'/{folder}/generation.json/programs/', raised.exception.path)


class NextManifest(unittest.TestCase):
    """The 2.3.0 block of scripts/atlas_delta.py, with the zone recipes as the delta's generation files."""

    def test_writer_pin_restores_the_bytes_2_2_0_pinned(self):
        listed = json.loads((atlas_delta.folder_of('2.2.0')/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(atlas_delta.pinned_writer('2.2.0')).hexdigest(),
                         listed['input_sha256']['scripts/atlas_delta.py'])

    def test_deferred_by_folder_class(self):
        # Release 2.3.0 as written (ADR 0059): `atlas_delta --check --release 2.3.0` rebuilds it from its inputs.
        out = atlas_delta.verify('2.3.0')
        generation = [d for d in out['deferred'] if d.startswith('generation blocks')]
        self.assertEqual(len(generation), 4)
        self.assertIn('189 of 255 folders', generation[0])
        self.assertIn('plenums and attics included', generation[0])
        self.assertTrue(any('IECC commercial apartment buildings, 12 folders' in d for d in generation))
        self.assertFalse(any('plenum and residential programs' in d for d in out['deferred']))
        self.assertEqual(out['counts']['generation']['generation_folders'], 189)
        self.assertEqual(out['input_sha256']['scripts/atlas_delta.py'],
                         hashlib.sha256(atlas_delta.pinned_writer('2.3.0')).hexdigest())
        self.assertEqual(release_schemas.errors({'manifest.json': out}), [])


if __name__ == '__main__':
    unittest.main()
