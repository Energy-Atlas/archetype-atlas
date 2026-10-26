"""The residential tree of release 1.4.0 (ADR 0038, ADR 0041, ADR 0042).

Merges the ResStock SDR fixture dwellings (scripts.resstock_dwellings) and the
code-prototype families, IECC residential and manufactured housing
(scripts.prototype_dwellings), with the upstream notices their sources cite.
scripts.atlas_minor_release adds these files to the commercial release it builds.

python -m scripts.residential_release --output build/residential
"""
import argparse
import json
from pathlib import Path

from scripts import prototype_dwellings, resstock_dwellings
from scripts.atlas_format import merge
from scripts.common import ROOT
from scripts.residential_storage import counts

NOTICES = ROOT/'sources/licenses'
# Notices of the recovered ResStock fillings, whose evidence cites ResStock and OpenStudio-HPXML source code.
RECOVERY_NOTICES = ('resstock.txt', 'openstudio-hpxml.txt')
SCRIPTS = ('scripts/residential_release.py', 'scripts/residential_exports.py')


def inputs():
    return (*resstock_dwellings.INPUTS, *prototype_dwellings.inputs(), *SCRIPTS)


def files(resstock_sources=None):
    built = merge(resstock_dwellings.build(resstock_sources), prototype_dwellings.build())
    glossary = json.loads(built['evidence/glossary.json'])
    cited = {Path(s['license_path']).name for s in glossary['source_files'].values() if s.get('license_path')}
    for name in sorted(cited | set(RECOVERY_NOTICES)):
        built['notices/'+name] = (NOTICES/name).read_bytes()
    return built


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, default=ROOT/'build/residential')
    args = parser.parse_args()
    built = files()
    for path, data in built.items():
        out = args.output/path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    print('Residential tree: '+', '.join(f'{v} {k}' for k, v in counts(built).items()))


if __name__ == '__main__':
    main()
