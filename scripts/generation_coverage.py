"""Which release folders carry generation blocks, by folder class, and why the others do not (ADR 0055).

python -m scripts.generation_coverage [--release 2.2.0]

A folder carries a `generation.json` when the generator can generate its programs. Within such a folder
every program has a block, plenums and attics included: an unconditioned program with no loads
generates as inactive, so the block says nothing about a plenum's conditioning. The folders without
one fall into the classes below, each with its reason. `deferred(release)` states them as the release
manifest's `deferred` entries from release 2.3.0 (they replace 2.2.0's entry, which named "plenum"
programs as a class and an empty DOE Ref class); `unexplained(release)` lists folders that are in no
class, which the tests require to be empty.
"""
import argparse
from collections import defaultdict

from atlas_schedules.programmes import SAMPLING

APARTMENTS = ('MidriseApartment', 'HighriseApartment')
# (class, label, reason): the folder classes without generation blocks, in manifest order.
CLASSES = (
    ('no_sampling_type', 'commercial types without a ComStock sampling building type',
     'the generator samples ComStock operating hours for 15 building types (atlas_schedules.programmes.SAMPLING); '
     'college, courthouse, laboratory, the data centres, the generic office and the tall and super-tall '
     'buildings have none, so their programs have no comstock_hours configuration (ADR 0039, ADR 0055)'),
    ('iecc_apartments', 'IECC commercial apartment buildings',
     "an apartment is a ResStock unit drawn under the folder's heating and cooling systems "
     '(scripts.build_apartment_units, ADR 0047), and the IECC commercial systems are deferred (ADR 0040 item 10)'),
    ('residential_prototypes', 'residential code-prototype dwellings (IECC residential, manufactured housing)',
     'PNNL and DOE EnergyPlus prototypes with no ResStock dwelling inputs to draw from and no generator family '
     '(ADR 0041, ADR 0042; ADR 0046 plan X-3)'),
)


def folder_class(family, template, building_type):
    """The class of a folder without generation blocks, or None when its programs are generated."""
    if family == 'residential':
        return None if template == 'resstock-sdr' else 'residential_prototypes'
    if building_type in APARTMENTS:
        return 'iecc_apartments' if template.startswith('iecc-') else None
    return None if building_type in SAMPLING else 'no_sampling_type'


def folders(release):
    """{folder: (family, template, building type of its programs)} of every building folder with programs."""
    out = {}
    for path in release.program_paths.values():
        folder = path.split('/programs/')[0]
        if folder not in out:
            family, template, _ = folder.split('/')
            out[folder] = (family, template, release.json(path)['building_type'])
    return dict(sorted(out.items()))


def coverage(release):
    """{class or 'generated': [folder]}; a folder whose state does not match its class is listed under
    'unexplained'."""
    generated = set(release.generation_folders())
    out = defaultdict(list)
    for folder, (family, template, building_type) in folders(release).items():
        expected = folder_class(family, template, building_type)
        if (folder in generated) == (expected is None):
            out[expected or 'generated'].append(folder)
        else:
            out['unexplained'].append(folder)
    return dict(out)


def unexplained(release):
    return coverage(release).get('unexplained', [])


def describe(group):
    """`90-1-2007, 90-1-2013, 90-1-2019: college, courthouse; doe-ref-...: ...` for a list of folders."""
    by_types = defaultdict(list)
    for folder in group:
        _, template, building_type = folder.split('/')
        by_types[template].append(building_type)
    rows = defaultdict(list)
    for template, types in sorted(by_types.items()):
        rows[', '.join(sorted(types))].append(template)
    return '; '.join(f"{', '.join(templates)}: {types}" for types, templates in rows.items())


def deferred(release):
    """The manifest's generation entries, by folder class."""
    groups = coverage(release)
    if groups.get('unexplained'):
        raise ValueError(f"Folders whose generation state matches no class: {groups['unexplained'][:5]}")
    total = sum(len(v) for v in groups.values())
    lines = [f"generation blocks: {len(groups.get('generated', []))} of {total} folders carry generation.json, with a "
             'block for every program, plenums and attics included (an unconditioned program without loads generates '
             'as inactive); the other folders, by class (ADR 0055):']
    for key, label, reason in CLASSES:
        group = groups.get(key, [])
        if group:
            lines.append(f'generation blocks of {label}, {len(group)} folders ({describe(group)}): none, because {reason}')
    return lines


def main():
    from atlas_schedules.release import Release
    from scripts import atlas_delta
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--release', default=atlas_delta.RELEASE)
    args = parser.parse_args()
    release = Release(atlas_delta.folder_of(args.release))
    for key, group in coverage(release).items():
        print(f'{key}: {len(group)}')
    for line in deferred(release) if not unexplained(release) else []:
        print('-', line)


if __name__ == '__main__':
    main()
