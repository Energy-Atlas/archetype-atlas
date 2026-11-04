"""Which conditioning sides (heating, cooling) the source HVAC equipment serves, per commercial source program
(ADR 0063).

python -m scripts.conditioning_sides           # write data/program-inputs/conditioning-sides-v1.json
python -m scripts.conditioning_sides --check   # rebuild it and fail unless the committed file equals it

The 90.1 and DOE Ref templates take their programs from the openstudio-standards prototypes, so their equipment
is the prototype's HVAC map (`data/geometry/<prototype>.json`, the file the template's `prototype_inputs.json` names
as `hvac_json`): a list of systems, each with a `type` and the `space_names` it serves. Every file is read through
its checksum lock (`sources/*.json`) from the pinned openstudio-standards revision, fetched into `data/raw`.

- **What a system type serves** is what the source builds for it, not the map's `cooling_type` field (a PVAV record
  has none, yet PVAV cools): `Prototype.Model.hvac.rb#model_add_hvac` dispatches each type to a builder in
  `Prototype.hvac_systems.rb`, and the builder's coil objects are its sides. `SYSTEMS` names the builder of each type
  and its sides; the build checks both against the pinned code (the dispatch calls that builder, and the builder
  creates heating coils exactly where a heating side is declared and cooling coils exactly where a cooling side is).
  Exhaust fans, zone ventilation and refrigeration systems condition no side.
- **A space is served on a side** when a system that serves that side names a space of its thermal zone
  (OpenStudio matches names without regard to case, so `LGSTORE1` serves `LGstore1`). Each space belongs to the atlas
  program of its standards space type, as the compositions read it (`scripts.program_composition`); the DOE Ref zones
  ADR 0037 gave programs of their own keep them (`scripts.reconciliation_register.NEW_PROGRAMS`).
- **A program's side** is `served` when every space of the program is served on it, `not_served` when none is, and
  `mixed` otherwise (reported with the served floor-area share and left to the owner; the edits change nothing there).

The IECC templates take their programs from the PNNL IECC prototype IDFs, whose thermostats already give each program
its sides (`parameters.conditioning`, ADR 0040 item 4); `--review` checks them against the IDFs' zone equipment.
Folders whose prototype names no HVAC map that exists (the tall and super-tall buildings) are listed as such.
"""
import argparse
import copy
import glob
import json
import math
import re
from collections import Counter, defaultdict

from scripts.atlas_format import slug
from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id
from scripts.fetch import fetch_file
from scripts.program_composition import floor_areas
from scripts.semantics import spaces

OUTPUT = ROOT/'data/program-inputs/conditioning-sides-v1.json'
ADR = 'docs/adr/0063-conditioning-sides-and-per-side-mixes.md'
EXTRACTION_DATE = '2026-11-04'
RELEASE = '2.4.0'   # the release whose programs the records name
CACHE = ROOT/'data/raw'
DISPATCH = 'lib/openstudio-standards/prototypes/common/objects/Prototype.Model.hvac.rb'
BUILDERS = 'lib/openstudio-standards/prototypes/common/objects/Prototype.hvac_systems.rb'
SIDES = ('heating', 'cooling')
# System type: (builder in Prototype.hvac_systems.rb or None, heating, cooling). A side given as a field name is
# served when the system record gives that field (the builder makes the coil of that type); every map in scope gives
# them. Types with no builder condition no side.
SYSTEMS = {
    'PSZ-AC': ('model_add_psz_ac', 'heating_type', 'cooling_type'),
    'PTAC': ('model_add_ptac', 'heating_type', 'cooling_type'),
    'SAC': ('model_add_split_ac', 'heating_type', 'cooling_type'),
    'PVAV': ('model_add_pvav', True, True),
    'VAV': ('model_add_vav_reheat', True, True),
    'CAV': ('model_add_cav', True, True),
    'DC': ('model_add_data_center_hvac', True, True),
    'DOAS Cold Supply': ('model_add_doas_cold_supply', True, True),
    'Packaged DOAS': ('model_add_doas', True, True),
    'CRAC': ('model_add_crac', False, True),
    'CRAH': ('model_add_crah', False, True),
    'WSHP': ('model_add_water_source_hp', True, True),
    'PTHP': ('model_add_pthp', True, True),
    'Baseboards': ('model_add_baseboard', True, False),
    'UnitHeater': ('model_add_unitheater', True, False),
    'Exhaust Fan': ('model_add_exhaust_fan', False, False),
    'Zone Ventilation': ('model_add_zone_ventilation', False, False),
    'Refrigeration_system': ('model_add_refrigeration_system', False, False),
}
HEATING_COIL = re.compile(r'create_coil_heating_|CoilHeating\w*\.new|ZoneHVACBaseboard\w*\.new')
COOLING_COIL = re.compile(r'create_coil_cooling_|CoilCooling\w*\.new')
# DOE Ref programs whose DOE reference file (the authority of the DOE Ref templates, ADR 0037 section 1) serves spaces
# the openstudio-standards DOE Ref HVAC map leaves out. The DOE file's side holds; `--review` re-reads the IDFs.
DOE_FILE_SIDES = {
    (template, 'Hospital', 'Basement'): {
        'heating': 'served', 'cooling': 'served',
        'source_file': {'path': f'refbldg_hospital_{vintage}_v1-4_7-2/RefBldgHospital{label}_v1.4_7.2_5A_USA_IL_CHICAGO-OHARE.idf',
                        'sha256': sha, 'archive_path': f'v1.4_7.2/refbldg_hospital_{vintage}_v1-4_7-2.zip'},
        'locator': 'ZoneHVAC:EquipmentConnections Basement / ZoneHVAC:EquipmentList Basement Equipment',
        'note': 'The DOE file serves the basement from VAV_1 (AirTerminal:SingleDuct:VAV:Reheat; the air loop has cooling '
                'and heating coils) in all 16 climates; DOERefHospital.json names no system for it. The DOE file holds.'}
    for template, vintage, label, sha in (
        ('DOE Ref Pre-1980', 'pre1980', 'Pre1980', '580bcc9f96917a8bd15e461ce85e0bd56259d0ecb92b89ecf4d2e715509545af'),
        ('DOE Ref 1980-2004', 'post1980', 'Post1980', 'b741ac1a46a0de72c46262d5f5855314eaeb626fc0b17a0e7c6c25bc24c86183'))}
TRANSFORMATION = ('system type to conditioning sides by the builder Prototype.Model.hvac.rb dispatches it to and the '
                  'coils that builder creates (Prototype.hvac_systems.rb); space to program by its standards space type')


# Locked sources -------------------------------------------------------------------------------------------

def locked():
    """{path: lock entry} of every pinned openstudio-standards file in `sources/*.json`."""
    out = {}
    for name in sorted(glob.glob(str(ROOT/'sources/*.json'))):
        document = load_json(name)
        rows = document.get('files') if isinstance(document, dict) else None
        for entry in rows or []:
            if isinstance(entry, dict) and entry.get('source_id') == 'openstudio-standards' and entry.get('url'):
                if out.setdefault(entry['path'], entry)['sha256'] != entry['sha256']:
                    raise ValueError(f'Two locks pin {entry["path"]} differently')
    return out


class Sources:
    def __init__(self):
        self.lock = locked()
        self.used = {}

    def text(self, path):
        if path not in self.lock:
            raise SystemExit(f'{path} has no checksum lock in sources/; add it before reading it')
        entry = self.lock[path]
        self.used[path] = entry
        return fetch_file(entry, CACHE).read_text(encoding='utf-8-sig')

    def json(self, path):
        return json.loads(self.text(path))

    def file_id(self, path):
        entry = self.used[path]
        row = {k: entry[k] for k in ('path', 'sha256', 'size_bytes', 'url')}
        return stable_id('sourcefile', row)[:len('sourcefile-')+20]

    def source_files(self):
        out = {}
        for path, entry in sorted(self.used.items()):
            out[self.file_id(path)] = {
                'license_path': 'sources/licenses/openstudio-standards.txt', 'path': path, 'project': 'openstudio-standards',
                'repository': 'https://github.com/NatLabRockies/openstudio-standards',
                'retrieval_date': entry.get('retrieval_date') or '2026-10-02', 'sha256': entry['sha256'],
                'size_bytes': entry['size_bytes'], 'source_id': 'openstudio-standards', 'url': entry['url'],
                'version': entry['url'].split('/openstudio-standards/')[1].split('/')[0]}
        return out


# What each system type serves ---------------------------------------------------------------------------

def blocks(text, start):
    """{name: (first line, last line)} of the Ruby blocks opened by `start` (a regex with one group)."""
    lines = text.splitlines()
    heads = [(i, m[1]) for i, line in enumerate(lines, 1) for m in [re.match(start, line)] if m]
    out = {}
    for (first, name), (after, _) in zip(heads, heads[1:] + [(len(lines) + 1, None)]):
        out.setdefault(name, (first, after - 1))
    return out, lines


def system_types(sources):
    """{type: {builder, heating, cooling, dispatch_lines, builder_lines, heating_coil_lines, cooling_coil_lines}},
    each declared side checked against the pinned dispatch and builder code."""
    dispatch, dispatch_lines = blocks(sources.text(DISPATCH), r"^      when '([^']+)'")
    builders, builder_lines = blocks(sources.text(BUILDERS), r'^  def (model_add_\w+)\(')
    out = {}
    for kind, (builder, heating, cooling) in SYSTEMS.items():
        if kind not in dispatch:
            raise ValueError(f'Prototype.Model.hvac.rb dispatches no system type {kind!r}')
        first, last = dispatch[kind]
        calls = [i for i in range(first, last + 1) if re.search(rf'\b{builder}\(', dispatch_lines[i - 1])]
        if not calls:
            raise ValueError(f'The {kind} dispatch does not call {builder}')
        entry = {'builder': builder, 'heating': heating, 'cooling': cooling, 'dispatch_lines': [first, last]}
        if builder in builders:
            start, end = builders[builder]
            body = builder_lines[start - 1:end]
            entry['builder_lines'] = [start, end]
            entry['heating_coil_lines'] = [start + i for i, line in enumerate(body) if HEATING_COIL.search(line)]
            entry['cooling_coil_lines'] = [start + i for i, line in enumerate(body) if COOLING_COIL.search(line)]
        else:
            entry['builder_lines'] = None   # defined elsewhere (the exhaust and refrigeration builders): no coil
            entry['heating_coil_lines'] = entry['cooling_coil_lines'] = []
        for side in SIDES:
            declared = entry[side] is not False
            if declared != bool(entry[f'{side}_coil_lines']):
                raise ValueError(f'{kind}: {side} declared {entry[side]!r}, but {builder} creates '
                                 f'{len(entry[side + "_coil_lines"])} {side} coils')
        out[kind] = entry
    return out


def sides_of(system, types):
    """(heating, cooling) a map record serves."""
    kind = system['type']
    if kind not in types:
        raise ValueError(f'Unmapped system type {kind!r}; add it to SYSTEMS with its builder')
    out = []
    for side in SIDES:
        rule = types[kind][side]
        if isinstance(rule, str):
            if not system.get(rule):
                raise ValueError(f'{kind} {system.get("name")}: no {rule}; its {side} side is not stated')
            out.append(True)
        else:
            out.append(rule)
    return tuple(out)


# Programs ----------------------------------------------------------------------------------------------

def release_programs(files):
    """{folder: {space type: record}} of the 90.1 and DOE Ref source programs of a resolved release."""
    from scripts.lighting_controls import space_type
    out = defaultdict(dict)
    for path in sorted(files):
        if path.startswith('commercial/') and '/programs/source/' in path:
            record = json.loads(files[path])
            if record['source_family'] in ('code_prototype_rules', 'existing_stock_benchmark'):
                key = space_type(record)
                if key in out[path.split('/programs/')[0]]:
                    raise ValueError(f'Two programs of space type {key} in {path}')
                out[path.split('/programs/')[0]][key] = record
    return out


def retagged(template):
    """{space name (lower case): program space type} of the DOE Ref zones ADR 0037 gave programs of their own."""
    from scripts.reconciliation_register import NEW_PROGRAMS
    if not template.startswith('DOE Ref'):
        return {}
    return {zone.lower(): name for (_, name), entry in NEW_PROGRAMS.items() for zone in entry['zones']}


def program_sides(names, served, areas, multipliers):
    """{side: status, ...} of one program's spaces."""
    out = {'spaces': len(names)}
    total = math.fsum(areas[n] * multipliers[n] for n in names)
    for index, side in enumerate(SIDES):
        hit = [n for n in names if served[n][index]]
        share = math.fsum(areas[n] * multipliers[n] for n in hit) / total if total else None
        out[side] = 'served' if len(hit) == len(names) else 'not_served' if not hit else 'mixed'
        if out[side] == 'mixed':
            out[f'{side}_served_area_share'] = share
    return out


def build(files=None):
    from scripts import atlas_delta
    files = files if files is not None else atlas_delta.files(RELEASE)
    sources = Sources()
    types = system_types(sources)
    selection = load_json(ROOT/'sources/selection.json')
    programs = release_programs(files)
    records, evidence, folders = [], {}, {}
    for template in selection['templates']:
        models = {m['building_type']: m for m in template['models']}
        for prototype in sources.json(template['prototype_inputs'])['prototype_inputs']:
            building_type = prototype['building_type']
            folder = f'commercial/{slug(template["template"])}/{slug(building_type)}'
            if folder not in programs or not prototype.get('geometry_osm'):
                continue
            geometry = models.get(building_type, {}).get('geometry') or 'data/geometry/'+prototype['geometry_osm']
            if geometry != 'data/geometry/'+prototype['geometry_osm']:
                raise ValueError(f'{folder}: selection geometry {geometry} is not the prototype\'s {prototype["geometry_osm"]}')
            hvac = 'data/geometry/'+prototype['hvac_json']
            if building_type in models and models[building_type]['hvac'] != hvac:
                raise ValueError(f'{folder}: selection HVAC map {models[building_type]["hvac"]} is not the prototype\'s {hvac}')
            if hvac not in sources.lock:
                folders[folder] = {'status': 'no_hvac_map', 'hvac_map': hvac,
                                   'note': f'The prototype inputs name {prototype["hvac_json"]}, which openstudio-standards does '
                                           'not have at this revision; the sides are not decided from equipment.'}
                continue
            text = sources.text(geometry)
            osm = spaces(text)
            areas = floor_areas(text)
            systems = sources.json(hvac)
            by_name = {s['name'].lower(): s for s in osm}
            zone_of = {s['name']: s['zone'] for s in osm}
            zone_systems = defaultdict(list)
            for index, system in enumerate(systems):
                for name in system.get('space_names') or []:
                    if name.lower() not in by_name:
                        raise ValueError(f'{hvac}: system {index} names a space {name!r} that {geometry} lacks')
                    zone_systems[zone_of[by_name[name.lower()]['name']]].append(index)
            served = {s['name']: tuple(any(sides_of(systems[i], types)[k] for i in zone_systems[s['zone']]) for k in range(2))
                      for s in osm}
            space_area = {s['name']: areas.get(s['handle'], 0.0) for s in osm}
            multiplier = {s['name']: s['multiplier'] for s in osm}
            tags = retagged(template['template'])
            grouped = defaultdict(list)
            for s in osm:
                key = tags.get(s['name'].lower()) or s['source_space_type'] or 'Plenum'
                grouped[key].append(s['name'])
            folder_programs = programs[folder]
            missing = sorted(set(folder_programs) - set(grouped))
            if missing:
                raise ValueError(f'{folder}: programs with no space in {geometry}: {missing}')
            file_id = None
            for key in sorted(folder_programs):
                names = sorted(grouped[key])
                entry = {'template': template['template'], 'building_type': building_type, 'space_type': key,
                         'folder': folder, **program_sides(names, served, space_area, multiplier)}
                override = DOE_FILE_SIDES.get((template['template'], building_type, key))
                if override:
                    entry['hvac_map'] = {side: entry[side] for side in SIDES}
                    entry.update({side: override[side] for side in SIDES}, doe_file=override)
                if any(entry[side] != 'served' for side in SIDES):
                    file_id = file_id or sources.file_id(hvac)
                    used = sorted({i for n in names for i in zone_systems[zone_of[n]]})
                    value = {'systems': [{'index': i, **{k: systems[i][k] for k in ('type', 'name', 'heating_type', 'cooling_type')
                                                        if k in systems[i]},
                                          'sides': dict(zip(SIDES, sides_of(systems[i], types)))} for i in used],
                             'spaces': [{'name': n, 'zone_systems': zone_systems[zone_of[n]],
                                         **dict(zip(SIDES, served[n]))} for n in names]}
                    row = {'source_file_id': file_id, 'locator': ', '.join(f'/{i}' for i in used) or '(no system names these spaces)',
                           'original_value': value, 'original_unit': None, 'transformation': TRANSFORMATION,
                           'extraction_date': EXTRACTION_DATE, 'interpretation': interpretation(entry, value, hvac)}
                    eid = stable_id('evidence', row)
                    evidence[eid] = row
                    entry['evidence_id'] = eid
                records.append(entry)
            folders[folder] = {'status': 'decided', 'hvac_map': hvac, 'geometry': geometry, 'programs': len(folder_programs)}
    return {'schema_version': '1.0.0', 'decision': ADR, 'extraction_date': EXTRACTION_DATE, 'release': RELEASE,
            'description': 'Which conditioning sides the source HVAC equipment serves, per 90.1 and DOE Ref source program: '
                           'the openstudio-standards prototype HVAC maps, each system type read as its builder makes it.',
            'system_types': types, 'folders': dict(sorted(folders.items())), 'records': records,
            'evidence': dict(sorted(evidence.items())), 'source_files': sources.source_files()}


def interpretation(entry, value, hvac):
    kinds = Counter(s['type'] for s in value['systems'])
    equipment = ', '.join(f'{n} x {k}' if n > 1 else k for k, n in sorted(kinds.items())) or 'no system'
    parts = []
    for side in SIDES:
        if entry[side] == 'not_served':
            parts.append(f'no {side} equipment')
        elif entry[side] == 'mixed':
            parts.append(f'{side} equipment in only {entry[side + "_served_area_share"]:.3f} of the floor area')
    return (f'{entry["space_type"]} ({entry["spaces"]} source space{"s" if entry["spaces"] != 1 else ""}): served by '
            f'{equipment} in {hvac.rsplit("/", 1)[1]}; {", ".join(parts)}. A side no equipment serves is not conditioned, '
            'whatever setpoint the space type gives it (ADR 0063).')


def encode(document):
    return json.dumps(document, indent=1, ensure_ascii=False, sort_keys=True) + '\n'


# Review against the prototype IDFs (outside the repository) ------------------------------------------------

REVIEW = ROOT/'docs/reviews/conditioning-sides-idf-check.md'
HEATING_EQUIPMENT = ('zonehvac:baseboard', 'zonehvac:unitheater', 'zonehvac:hightemperatureradiant', 'zonehvac:lowtemperatureradiant')


def idf_sides(path):
    """{zone: (heating, cooling, [equipment], thermostat)} of an IDF: the zone equipment list, an air terminal by the coils
    of the air loop that feeds it (branches and unitary systems expanded), a zone unit by its own coils."""
    from scripts import idf_reader
    objects = idf_reader.parse(open(path, errors='replace').read())
    by = defaultdict(list)
    for kind, fields in objects:
        by[kind].append(fields)
    named = {(kind, f[0].lower()): f for kind, rows in by.items() for f in rows if f}

    def pairs(fields):
        return [(v.lower(), fields[i + 1].lower()) for i, v in enumerate(fields[:-1]) if ':' in v]

    def coils(kind, name, depth=0):
        found = {kind}
        fields = named.get((kind, name))
        if fields and depth < 3:
            for inner, inner_name in pairs(fields):
                if inner.startswith(('coil', 'airloophvac:unitary', 'coilsystem')):
                    found |= coils(inner, inner_name, depth + 1)
        return found

    branches = {f[0].lower(): f for f in by['branch']}
    lists = {f[0].lower(): f for f in by['branchlist']}
    loops = {}
    for f in by['airloophvac']:
        found = set()
        for branch in lists.get(f[4].lower(), [])[1:]:
            for kind, name in pairs(branches.get(branch.lower(), [])):
                found |= coils(kind, name)
        loops[f[8].lower()] = found   # by the demand-side inlet node
    node_coils = {}
    splitters = {f[0].lower(): [x.lower() for x in f[2:]] for f in by['airloophvac:zonesplitter']}
    plenums = {f[0].lower(): [x.lower() for x in f[4:]] for f in by['airloophvac:supplyplenum']}
    for f in by['airloophvac:supplypath']:
        found = loops.get(f[1].lower(), set())
        for kind, name in zip(f[2::2], f[3::2]):
            for node in (splitters if kind.lower() == 'airloophvac:zonesplitter' else plenums).get(name.lower(), []):
                node_coils[node] = found
    units = {f[0].lower(): (f[2].lower(), f[3].lower()) for f in by['zonehvac:airdistributionunit']}
    equipment = {f[0].lower(): f for f in by['zonehvac:equipmentlist']}
    thermostats = {f[1].lower() for f in by['zonecontrol:thermostat']}
    zone_lists = {f[0].lower(): [z.lower() for z in f[1:]] for f in by['zonelist']}
    for name in list(thermostats):
        thermostats |= set(zone_lists.get(name, []))
    out = {}
    for f in by['zonehvac:equipmentconnections']:
        heating = cooling = False
        kinds = []
        for kind, name in pairs(equipment.get(f[1].lower(), [])):
            if kind == 'zonehvac:airdistributionunit':
                kind, name = units.get(name, (kind, name))
            if kind.startswith('airterminal:'):
                terminal = named.get((kind, name), [])
                found = next((node_coils[v.lower()] for v in terminal if v.lower() in node_coils), set()) | coils(kind, name)
                heating |= 'reheat' in kind or any(c.startswith('coil:heating') for c in found)
                cooling |= any(c.startswith(('coil:cooling', 'coilsystem:cooling')) for c in found)
            else:
                found = coils(kind, name)
                heating |= kind.startswith(HEATING_EQUIPMENT) or any(c.startswith('coil:heating') for c in found) or \
                    kind in ('zonehvac:packagedterminalairconditioner', 'zonehvac:packagedterminalheatpump')
                cooling |= any(c.startswith('coil:cooling') for c in found) or \
                    kind in ('zonehvac:packagedterminalairconditioner', 'zonehvac:packagedterminalheatpump')
            kinds.append(kind)
        out[f[0].lower()] = (heating, cooling, kinds, f[0].lower() in thermostats)
    for f in by['zone']:
        out.setdefault(f[0].lower(), (False, False, [], f[0].lower() in thermostats))
    return out


def review():
    """docs/reviews/conditioning-sides-idf-check.md: the zones of each prototype IDF whose equipment does not serve both
    sides, in the base climate of each family (PNNL Buffalo 5A, DOE Chicago 5A)."""
    from scripts.lighting_controls import doe_root, prototype_root
    families = [(f'PNNL ASHRAE 90.1-{y}', sorted((prototype_root()/'commercial-ashrae901').glob(f'*/*_STD{y}_Buffalo.idf'))) for y in
                ('2007', '2013', '2019')]
    families += [(f'PNNL IECC {y}', sorted((prototype_root()/'commercial-iecc').glob(f'*/*_STD{y}_Buffalo.idf'))) for y in
                 ('2006', '2009', '2012', '2015', '2018', '2021')]
    families += [(f'DOE reference {v}', sorted(doe_root().glob(f'*_{v}_*/*_5A_USA_IL_CHICAGO-OHARE.idf'))) for v in ('pre1980', 'post1980')]
    lines = ['# Conditioning sides in the prototype IDFs (ADR 0063)', '',
             'Written by `python -m scripts.conditioning_sides --review` from the PNNL and DOE prototype IDFs outside the',
             'repository (`ATLAS_PROTOTYPE_ROOT`, `ATLAS_DOE_IDF_ROOT`; checksums in `sources/reference-models-lock.json`),',
             'base climate of each family. Each zone takes the sides of its zone equipment: an air terminal those of the air',
             'loop that feeds it (its branches, unitary systems expanded), a zone unit its own coils. Listed: every zone',
             'whose equipment does not serve both sides, with whether it has a thermostat. Plenums and attics are listed',
             'under one line per model.', '']
    for family, paths in families:
        if not paths:
            lines += [f'## {family}', '', 'Not on this machine.', '']
            continue
        lines += [f'## {family}', '', '| Model | Zone | Heating | Cooling | Thermostat | Equipment |', '| --- | --- | --- | --- | --- | --- |']
        for path in paths:
            sides = idf_sides(path)
            model = path.stem.split('_')[1] if path.stem.startswith(('ASHRAE901_', 'IECC_')) else path.stem.split('_')[0]
            skipped = sorted(z for z, s in sides.items() if not (s[0] and s[1]) and ('plenum' in z or 'attic' in z))
            for zone, (heating, cooling, kinds, thermostat) in sorted(sides.items()):
                if (heating and cooling) or zone in skipped:
                    continue
                lines.append(f'| {model} | {zone} | {"yes" if heating else "no"} | {"yes" if cooling else "no"} | '
                             f'{"yes" if thermostat else "no"} | {", ".join(sorted(set(kinds))) or "none"} |')
            if skipped:
                lines.append(f'| {model} | {len(skipped)} plenum or attic zones | no | no | – | none |')
        lines.append('')
    REVIEW.write_bytes(('\n'.join(lines).rstrip() + '\n').encode('utf-8'))
    print(f'Wrote {REVIEW.relative_to(ROOT)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='fail unless the committed input equals a rebuild')
    parser.add_argument('--review', action='store_true', help='write the IDF review (needs the prototype IDFs) and stop')
    args = parser.parse_args()
    if args.review:
        review()
        return
    document = build()
    text = encode(document)
    counts = Counter((r[side]) for r in document['records'] for side in SIDES)
    print(f'{len(document["records"])} programs in {sum(f["status"] == "decided" for f in document["folders"].values())} '
          f'folders; sides {dict(counts)}')
    for r in document['records']:
        if any(r[s] != 'served' for s in SIDES):
            print(f'  {r["template"]:18} {r["building_type"]:22} {r["space_type"]:22} heating {r["heating"]:10} cooling {r["cooling"]}')
    for folder, entry in document['folders'].items():
        if entry['status'] != 'decided':
            print(f'  {folder}: {entry["status"]}')
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding='utf-8') != text:
            raise SystemExit(f'{OUTPUT.relative_to(ROOT)} differs from a rebuild; run python -m scripts.conditioning_sides')
        print('conditioning sides: OK')
        return
    OUTPUT.write_bytes(text.encode("utf-8"))


if __name__ == '__main__':
    main()
