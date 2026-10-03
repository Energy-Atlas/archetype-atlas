"""Contracts preventing unsafe runtime extraction and misleading profile output."""
import csv
import hashlib
import importlib
import io
from pathlib import Path
import tarfile
import tempfile
import subprocess
import shutil
import unittest


class ResidentialProfilesTests(unittest.TestCase):
    def module(self, name):
        self.assertIsNotNone(importlib.util.find_spec('scripts.'+name), 'Residential execution support is not implemented')
        return importlib.import_module('scripts.'+name)

    def test_runtime_rejects_corrupt_archive_without_extraction(self):
        runtime = self.module('runtime')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); archive = root/'input.tar.gz'; archive.write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                runtime.extract_verified(archive, '0'*64, root/'output')
            self.assertFalse((root/'output').exists())

    def test_runtime_rejects_archive_path_traversal(self):
        runtime = self.module('runtime')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); archive = root/'input.tar.gz'
            with tarfile.open(archive, 'w:gz') as t:
                info = tarfile.TarInfo('../escape.txt'); info.size = 1
                t.addfile(info, io.BytesIO(b'x'))
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                runtime.extract_verified(archive, hashlib.sha256(archive.read_bytes()).hexdigest(), root/'output')
            self.assertFalse((root/'escape.txt').exists())

    def write_profile(self, root, rows=8760, value='0.5'):
        path = root/'profile.csv'
        path.write_text('occupants,lighting_interior\n'+('0.25,'+value+'\n')*rows)
        return path

    def test_runtime_extracts_only_declared_source_subtree(self):
        runtime = self.module('runtime')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); archive = root/'input.tar.gz'
            with tarfile.open(archive, 'w:gz') as t:
                for name in ['source/measures/run.rb','source/unrelated/ignore.txt']:
                    info=tarfile.TarInfo(name);info.size=1;t.addfile(info,io.BytesIO(b'x'))
            runtime.extract_verified(archive,hashlib.sha256(archive.read_bytes()).hexdigest(),root/'output',
                                     include=['source/measures/'])
            self.assertTrue((root/'output/source/measures/run.rb').exists())
            self.assertFalse((root/'output/source/unrelated').exists())

    def test_profiles_require_full_calendar_and_bounded_finite_fractions(self):
        profiles = self.module('residential_profiles')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            metadata = {'year':2007,'timestep_minutes':60,'columns':{'occupants':'dimensionless','lighting_interior':'dimensionless'}}
            self.assertEqual(profiles.validate_profiles(self.write_profile(root), metadata)['rows'],8760)
            for rows,value in [(8759,'0.5'),(8760,'1.1'),(8760,'nan')]:
                with self.assertRaises(ValueError):
                    profiles.validate_profiles(self.write_profile(root,rows,value),metadata)

    def test_zero_occupants_do_not_silently_receive_generic_occupancy(self):
        profiles = self.module('residential_profiles')
        row = {'id':'residential_archetype-test','source_building_id':'101','occupants':0,
               'selected_options':{'State':'MA','Bedrooms':'3'},'heating_base_C':20,'cooling_base_C':25}
        inputs = profiles.build_inputs([row], {'year':2007,'timestep_minutes':60,
            'reference_location':{'latitude':39.83,'longitude':-104.65,'time_zone_utc_offset':-7}})
        self.assertEqual(inputs[0]['occupants'],0)
        self.assertTrue(inputs[0]['reference_context'])
        self.assertEqual(inputs[0]['seed'],101)

    def test_exact_binding_rejects_unknown_schedule_option(self):
        profiles = self.module('residential_profiles')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'lookup.tsv'
            path.write_text('Dishwasher\tNone\tResStockArguments\tappliance_dishwasher=None\n')
            binding = profiles.option_binding(path, 'Dishwasher', 'None')
            self.assertEqual(binding['arguments']['appliance_dishwasher'], 'None')
            self.assertEqual(binding['line'], 1)
            with self.assertRaisesRegex(ValueError, 'exact'):
                profiles.option_binding(path, 'Dishwasher', 'invented')

    def test_failed_attempts_preserve_previous_output_and_record_failure(self):
        profiles=self.module('residential_profiles')
        from scripts.common import ROOT,load_json
        bundle=ROOT/'data/resolution-releases/v0.1.0'
        index=load_json(bundle/'profile-index.json')
        for partial in [False,True]:
            with self.subTest(partial=partial),tempfile.TemporaryDirectory() as d:
                destination=Path(d);old=destination/'output';old.mkdir()
                previous=(bundle/'profile-index.json').read_bytes()
                (old/'profile-index.json').write_bytes(previous)
                def failing_producer(attempt):
                    if partial:
                        shutil.copyfile(bundle/'profiles'/index[0]['csv_file'],attempt/'output'/index[0]['csv_file'])
                    raise subprocess.CalledProcessError(7,['openstudio'])
                with self.assertRaises(subprocess.CalledProcessError):
                    profiles.run_attempt(destination,failing_producer,[p['record_id'] for p in index])
                latest=load_json(destination/'latest-run.json')
                self.assertEqual(latest['status'],'failed')
                self.assertEqual((old/'profile-index.json').read_bytes(),previous)
                self.assertTrue((destination/latest['attempt']/'run.json').exists())
                with self.assertRaisesRegex(ValueError,'completed'):
                    profiles.completed_output(destination)


if __name__ == '__main__':
    unittest.main()
