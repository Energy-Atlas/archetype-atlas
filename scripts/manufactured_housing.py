"""Extract the manufactured-housing prototype family offline into a committed definition input (ADR 0042).

python -m scripts.manufactured_housing --idf-root "<dir with manufactured-housing>" [--out data/program-inputs]

Reads the HUD and FinalRule folders of the pinned PNNL manufactured-housing set
(sources/reference-models-lock.json, EnergyPlus 8.0):
<zone>_<City>_{HUD,FinalRule}/<SS|MS>_<City>_<zone>_<HUD|tier1|tier2>_<heating>.idf.
The CompleteSet folders hold the same files; every CompleteSet file is checked by
SHA-256 against its HUD or FinalRule copy and never read otherwise (user decision M1).
Writes `manufactured-housing.json` (under 25 MB):
- templates `hud-code` (the HUD Code baseline) and `doe-final-rule` (the 2022 DOE
  Final Rule: tier 1 for single-section, tier 2 for multi-section homes);
- one program per template and section type (M2), whose entries carry `applies_with`
  where they do not hold for every location and heating system;
- construction sets per template and section type with one context per location:
  the climate zone, and for 3A the city as a sub-context (M3).
"""
import argparse
import hashlib
import re
from multiprocessing import Pool
from pathlib import Path

from scripts.atlas_format import slug, suite_bytes
from scripts.common import ROOT, load_json
from scripts.iecc_residential import LOCK, MAX_BYTES, OUT
from scripts.prototype_programs import EXTRACTION_DATE, Extraction, read_model

FAMILY = 'manufactured_housing_prototype'
NAME = re.compile(r'(SS|MS)_([A-Za-z]+)_([0-9][A-C]?)_(HUD|tier1|tier2)_(electricfurnace|gasfurnace|heatpump|oilfurnace)\.idf')
FOLDER = re.compile(r'([0-9][A-C]?)_([A-Za-z]+)_(HUD|FinalRule|CompleteSet)')
SECTIONS = {'SS': 'SingleSection', 'MS': 'MultiSection'}
TEMPLATES = {'HUD': ('hud-code', 'HUD Code'), 'tier1': ('doe-final-rule', 'DOE Final Rule 2022'),
             'tier2': ('doe-final-rule', 'DOE Final Rule 2022')}
AXES = ('climate', 'location', 'heating')
TARGET = OUT/'manufactured-housing.json'


def context_key(climate, city, cities):
    """'4-a', or '3-a.atlanta' where a climate zone has several locations (3A)."""
    return slug(climate) if len(cities[climate]) == 1 else f'{slug(climate)}.{city.lower()}'


def models(idf_root):
    """[(path, section, city, climate, standard, heating)] of the HUD and FinalRule folders."""
    out = []
    for folder in sorted(Path(idf_root).iterdir()):
        match = FOLDER.fullmatch(folder.name)
        if not match or match[3] == 'CompleteSet':
            continue
        for path in sorted(folder.glob('*.idf')):
            name = NAME.fullmatch(path.name)
            if not name or (name[2], name[3]) != (match[2], match[1]):
                raise ValueError('Unexpected model '+str(path))
            out.append((path, *name.groups()))
    return out


def complete_set_check(idf_root):
    """Every CompleteSet model equals, by SHA-256, the same-named model of its HUD or FinalRule folder."""
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    compared = 0
    for folder in sorted(Path(idf_root).glob('*_CompleteSet')):
        match = FOLDER.fullmatch(folder.name)
        if not match:
            continue
        for path in sorted(folder.glob('*.idf')):
            standard = NAME.fullmatch(path.name)[4]
            twin = Path(idf_root)/f'{match[1]}_{match[2]}_{"HUD" if standard == "HUD" else "FinalRule"}'/path.name
            if digest(path) != digest(twin):
                raise ValueError(f'CompleteSet model differs from its copy: {path.name}')
            compared += 1
    return {'complete_set_models_compared': compared, 'identical': True,
            'note': 'CompleteSet folders duplicate HUD and FinalRule; only those two are read (user decision M1).'}


def read(path):
    return read_model(path)


def extract(idf_root, processes=12):
    lock = load_json(LOCK)
    archives = {Path(f['path']).stem: f for f in lock['files'] if f['family'] == 'manufactured-housing'}
    found = models(idf_root)
    if len(found) != 304:
        raise ValueError(f'Expected 304 HUD and FinalRule models, found {len(found)}')
    check = complete_set_check(idf_root)
    with Pool(processes) as pool:
        reads = pool.map(read, [m[0] for m in found], chunksize=4)
    extraction = Extraction(AXES, idf_root, lock)
    versions = set()
    for (path, section, city, climate, standard, heating), result in zip(found, reads):
        extraction.add((TEMPLATES[standard][0], section, standard, climate, city, heating), path, result,
                       archives[path.parent.name])
        versions.add(result['version'])
    typed, typed_paths = extraction.models, extraction.paths
    cities = {}
    for k in typed:
        cities.setdefault(k[3], set()).add(k[4])
    programs, constructions = [], []
    for template in ('hud-code', 'doe-final-rule'):
        for section in ('SS', 'MS'):
            subset = {k: v for k, v in typed.items() if k[:2] == (template, section)}
            [standard] = {k[2] for k in subset}
            extraction.models = {k[3:]: v for k, v in subset.items()}
            extraction.paths = {k[3:]: typed_paths[k] for k in subset}
            keys = sorted(extraction.models)
            label = f'{TEMPLATES[standard][1]} {SECTIONS[section]} manufactured home'
            programs.append({'template_key': template, 'building_type': SECTIONS[section], 'type_code': section,
                             'tier': None if standard == 'HUD' else standard,
                             'variant': {'heating': sorted({k[2] for k in keys})}, **extraction.program(keys, label)})
            contexts = {}
            for climate, city in sorted({k[:2] for k in keys}):
                group = [k for k in keys if k[:2] == (climate, city)]
                contexts[context_key(climate, city, cities)] = {
                    'climate': climate, 'location': city, **extraction.context(group, f'{label} {climate} {city}')}
            constructions.append({'template_key': template, 'building_type': SECTIONS[section], 'type_code': section,
                                  'tier': None if standard == 'HUD' else standard, 'contexts': contexts})
    lib = extraction.library
    return {'schema_version': '1.0.0', 'kind': 'prototype_dwelling_inputs', 'family': FAMILY,
            'templates': {'hud-code': 'HUD Code', 'doe-final-rule': 'DOE Final Rule 2022'},
            'extraction_date': EXTRACTION_DATE, 'generated_by': 'python -m scripts.manufactured_housing',
            'engine_versions': sorted(versions), 'axes': list(AXES), 'context_axes': ['climate', 'location'],
            'archives': {k: {f: v[f] for f in ('path', 'sha256', 'url', 'size_bytes')} for k, v in sorted(archives.items())
                         if not k.endswith('CompleteSet') and not k.startswith('All')},
            'complete_set_check': check, 'model_count': len(found), 'programs': programs, 'constructions': constructions,
            'schedules': dict(sorted(lib['schedules'].items())), 'materials': dict(sorted(lib['materials'].items())),
            'assemblies': dict(sorted(lib['assemblies'].items())),
            'evidence': dict(sorted(extraction.evidence.items())), 'source_files': dict(sorted(extraction.source_files.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--idf-root', type=Path, required=True, help='the extracted manufactured-housing folder')
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    data = suite_bytes(extract(args.idf_root))
    if len(data) > MAX_BYTES:
        raise SystemExit(f'Manufactured-housing input is {len(data)} bytes, over the 25 MB limit')
    out = Path(args.out)/TARGET.name
    out.write_bytes(data)
    print(f'Manufactured housing: {len(data)/1e6:.1f} MB written to {out}')


if __name__ == '__main__':
    main()
