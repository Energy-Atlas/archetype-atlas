"""Extract the IECC residential prototype family offline into committed definition inputs (ADR 0041).

python -m scripts.iecc_residential --idf-root "<dir with resstd_AllCodes>" [--edition 2021 ...]
    [--out data/program-inputs]

Reads every model of `resstd_AllCodes` (pinned in sources/reference-models-lock.json):
US+<SF|MF>+CZ<climate>+<heating>+<foundation>+IECC_<edition>.idf, and writes
`iecc-residential-<edition>.json`, each under 25 MB:
- programs, one per type (single-family, multifamily per dwelling unit) and appliance
  fuel (gas furnace homes have gas appliances; electric resistance, heat pump and oil
  furnace homes electric ones), whose entries carry `applies_with` where they do not
  hold for every climate code, heating system and foundation of the program;
- construction sets, one per type, with one context per climate code and foundation;
- the schedules (atlas rulesets checked over the full year), materials, assemblies,
  evidence and source files they cite.
The release build (scripts.prototype_dwellings) reads only these files.
"""
import argparse
import json
import re
from multiprocessing import Pool
from pathlib import Path

from scripts.atlas_format import suite_bytes
from scripts.common import ROOT, load_json
from scripts.prototype_programs import EXTRACTION_DATE, Extraction, read_model

FAMILY = 'iecc_residential_prototype'
EDITIONS = ('2006', '2009', '2012', '2015', '2018', '2021', '2024')
NAME = re.compile(r'US\+(SF|MF)\+CZ([0-9A-Z]+)\+(elecres|gasfurnace|hp|oilfurnace)\+(crawlspace|heatedbsmt|slab|unheatedbsmt)\+IECC_(\d{4})\.idf')
TYPES = {'SF': 'SingleFamily', 'MF': 'Multifamily'}
FUEL = {'gasfurnace': 'gas', 'elecres': 'electric', 'hp': 'electric', 'oilfurnace': 'electric'}
AXES = ('climate', 'heating', 'foundation')
LOCK = ROOT/'sources/reference-models-lock.json'
ARCHIVE = 'residential/resstd_AllCodes.zip'
OUT = ROOT/'data/program-inputs'
MAX_BYTES = 25_000_000


def target(edition, out=OUT):
    return Path(out)/f'iecc-residential-{edition}.json'


def models(idf_root, edition):
    """[(path, type code, climate, heating, foundation)] of one edition, sorted."""
    folder = Path(idf_root)/'resstd_AllCodes'
    out = []
    for path in sorted(folder.glob(f'US+*+IECC_{edition}.idf')):
        match = NAME.fullmatch(path.name)
        if not match:
            raise ValueError('Unexpected model name '+path.name)
        out.append((path, *match.groups()[:4]))
    return out


def read(path):
    return read_model(path)


def building_context(extraction, keys):
    """The multifamily building around each dwelling unit, from its models' zones and unit names."""
    units = {u for k in keys for u in extraction.models[k]['units']}
    positions = [re.fullmatch(r'unit(\d+)_(front|back)row_(bottom|middle|top)floor', u) for u in units]
    if not all(positions):
        raise ValueError('Unexpected multifamily unit names')
    zones = sorted({z for k in keys for z in extraction.models[k]['zones']} - {'living'})
    return {'units_in_building': len(units), 'floors': sorted({p[3] for p in positions}),
            'rows': sorted({p[2] for p in positions}), 'units_per_row_and_floor': len({p[1] for p in positions}),
            'non_dwelling_zones': zones,
            'note': 'One per-unit program stands for every unit: the 18 units have identical loads (user decision R4). '
                    'Zones outside the units are building-level (shared services and the construction set).'}


def extract(idf_root, edition, processes=12):
    lock = load_json(LOCK)
    archive = next(f for f in lock['files'] if f['path'] == ARCHIVE)
    found = models(idf_root, edition)
    if len(found) != 592:
        raise ValueError(f'Expected 592 models for IECC {edition}, found {len(found)}')
    with Pool(processes) as pool:
        reads = pool.map(read, [m[0] for m in found], chunksize=4)
    extraction = Extraction(AXES, idf_root, lock)
    versions = set()
    for (path, code, climate, heating, foundation), result in zip(found, reads):
        extraction.add((code, climate, heating, foundation), path, result, archive)
        versions.add(result['version'])
    # Model keys carry the type first; programs and contexts group on the rest.
    typed, typed_paths = extraction.models, extraction.paths
    programs, constructions = [], []
    for code in ('SF', 'MF'):
        extraction.models = {k[1:]: v for k, v in typed.items() if k[0] == code}
        extraction.paths = {k[1:]: v for k, v in typed_paths.items() if k[0] == code}
        for fuel in ('electric', 'gas'):
            keys = sorted(k for k in extraction.models if FUEL[k[1]] == fuel)
            label = f'IECC {edition} {TYPES[code]} {fuel} appliances'
            note = ' Identical in every dwelling unit of the building.' if code == 'MF' else ''
            program = {'building_type': TYPES[code], 'type_code': code,
                       'variant': {'appliance_fuel': fuel, 'heating': sorted({k[1] for k in keys})}, **extraction.program(keys, label, note)}
            if code == 'MF':
                program['building_context'] = building_context(extraction, keys)
            programs.append(program)
        contexts = {}
        for climate, foundation in sorted({(k[0], k[2]) for k in extraction.models}):
            keys = [k for k in extraction.models if (k[0], k[2]) == (climate, foundation)]
            contexts[f'{climate}|{foundation}'] = {'climate': climate, 'foundation': foundation,
                                                   **extraction.context(keys, f'IECC {edition} {TYPES[code]} {climate} {foundation}')}
        constructions.append({'building_type': TYPES[code], 'type_code': code, 'contexts': contexts})
    lib = extraction.library
    return {'schema_version': '1.0.0', 'kind': 'prototype_dwelling_inputs', 'family': FAMILY,
            'template': f'IECC {edition}', 'edition': edition, 'extraction_date': EXTRACTION_DATE,
            'generated_by': f'python -m scripts.iecc_residential --edition {edition}',
            'engine_versions': sorted(versions), 'axes': list(AXES), 'context_axes': ['climate', 'foundation'],
            'archive': {k: archive[k] for k in ('path', 'sha256', 'url', 'size_bytes')},
            'model_count': len(found), 'programs': programs, 'constructions': constructions,
            'schedules': dict(sorted(lib['schedules'].items())), 'materials': dict(sorted(lib['materials'].items())),
            'assemblies': dict(sorted(lib['assemblies'].items())),
            'evidence': dict(sorted(extraction.evidence.items())), 'source_files': dict(sorted(extraction.source_files.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--idf-root', type=Path, required=True, help='folder holding the extracted resstd_AllCodes folder')
    parser.add_argument('--edition', action='append', choices=EDITIONS)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    for edition in args.edition or EDITIONS:
        data = suite_bytes(extract(args.idf_root, edition))
        if len(data) > MAX_BYTES:
            raise SystemExit(f'IECC {edition} input is {len(data)} bytes, over the 25 MB limit')
        target(edition, args.out).write_bytes(data)
        print(f'IECC residential {edition}: {len(data)/1e6:.1f} MB written to {target(edition, args.out)}')


if __name__ == '__main__':
    main()
