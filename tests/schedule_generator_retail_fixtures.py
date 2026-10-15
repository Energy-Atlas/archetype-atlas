"""Portable test-only current Retail resource assembly from the immutable C5 ZIP."""
import atexit
import json
from functools import lru_cache
from pathlib import Path
import tempfile
import zipfile

from atlas_schedules.resources import ResourceSet,write_resources

ROOT=Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def retail_candidate_resources():
    from scripts.schedule_generator_retail import compile_cumulative_records
    directory=tempfile.TemporaryDirectory(prefix='atlas-retail-test-')
    atexit.register(directory.cleanup)
    root=Path(directory.name);previous=root/'previous'
    with zipfile.ZipFile(ROOT/'data/generator-releases/v0.6.0/generator.zip') as archive:
        for name in archive.namelist():
            if name.startswith('atlas_schedules/data/'):
                target=previous/name.removeprefix('atlas_schedules/data/')
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
    manifest=json.loads((previous/'manifest.json').read_bytes())
    records=compile_cumulative_records(ResourceSet(previous,manifest['resource_set_id']))
    target=root/'candidate'
    manifest=write_resources(target,records,{'scope':'portable-source-gate-test-fixture-not-certification'})
    return ResourceSet(target,manifest['resource_set_id'])
