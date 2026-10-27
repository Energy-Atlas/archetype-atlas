"""Migrate the 41 ResStock SDR fixture dwellings into the ADR 0038 residential tree (S12a).

Each dwelling becomes one program file under `residential/resstock-sdr/<building-type>/`,
with its annual series in `schedules/<program-id>.json` and one construction set of
one context. Values move unchanged from the frozen sources:
- the definition record (data/definition-releases/v0.1.1): loads, parameters and
  annual schedules, with their evidence;
- its fillings: the recovered magnitudes, controls and fixed background schedules of
  data/program-inputs/residential-v1.json, with the resolution rows of
  data/resolution-releases/v0.4.0 that select and justify them;
- its construction set, from the combined construction release.
Only identifiers change: schedules, programs and construction sets take readable,
content-hashed IDs. The filled reading is the frozen exporters' whole-dwelling path.

python -m scripts.resstock_dwellings --output build/residential
"""
import argparse
import collections
import json
import re
from pathlib import Path

from scripts import atlas_constructions, atlas_programs
from scripts.atlas_format import canonical, h6, slug, suite_bytes, table_bytes, translate
from scripts.common import ROOT, load_json
from scripts.residential_storage import annual_files

FAMILY = 'resstock-sdr'
TEMPLATE = 'ResStock SDR source fixture'
SOURCE_FAMILY = 'existing_stock_source_fixture'
RECOVERY = ROOT/'data/program-inputs/residential-v1.json'
INPUTS = ('data/program-inputs/residential-v1.json', 'scripts/residential_storage.py', 'scripts/resstock_dwellings.py')
FILLING_BASES = atlas_programs.FILLING_BASES
# The DOE Ref and 90.1 apartment programs stay commercial (ADR 0038 section 8); the dwellings cite their folders.
APARTMENTS = {'MidriseApartment': 'midrise-apartment', 'HighriseApartment': 'highrise-apartment'}
COMMERCIAL_TEMPLATES = ('90-1-2007', '90-1-2013', '90-1-2019', 'doe-ref-1980-2004', 'doe-ref-pre-1980')
RESERVED = ('id', 'kind', 'evidence_view', 'detail')
FOLDERS = {'SingleFamilyDetached': 'single-family-detached', 'SingleFamilyAttached': 'single-family-attached',
           'MultiFamily2To4': 'multifamily-2-to-4', 'MultiFamily5PlusLowRise': 'multifamily-5-plus-low-rise',
           'ManufacturedHome': 'manufactured-home', 'MidriseApartment': 'midrise-apartment',
           'HighriseApartment': 'highrise-apartment'}


class Sources:
    """The frozen definition, resolution, recovery and construction sources of the fixture."""

    def __init__(self, definitions=None, constructions=None):
        self.definitions = definitions or atlas_programs.load_sources()
        self.records = sorted((p for p in self.definitions.programs.values()
                               if p['source_family'] == SOURCE_FAMILY and p['evidence_view'] == 'source'),
                              key=lambda p: p['id'])
        self.recovery = load_json(RECOVERY)
        rows = load_json(atlas_programs.RESOLUTIONS)['resolutions']
        self.resolutions = collections.defaultdict(list)
        for row in rows:
            if row['record_table'] == 'residential_archetypes':
                self.resolutions[row['record_id']].append(row)
        self.constructions = constructions or atlas_constructions.load_sources()
        self.sets = {s['source']['source_fixture_id']: sid for sid, s in self.constructions.sets.items()
                     if s['source']['template'] == TEMPLATE}


def load_sources():
    return Sources()


def area_bin(recovered):
    return recovered['metadata']['original_selected_options']['Geometry Floor Area']


def dwelling_key(record, recovered):
    """Climate, vintage, floor-area bin and source building, e.g. 5a-pre1940-2000-2499ft2-b101526."""
    building = re.fullmatch(r'Whole dwelling / source_building_(\d+)', record['name'])[1]
    vintage = record['vintage'].replace('<', 'pre')
    area = area_bin(recovered).replace('+', 'plus')
    return f'{record["climate"].lower()}-{slug(vintage)}-{slug(area)}ft2-b{building}'


def building_context(recovered):
    """The source's geometry options other than floor area and type (units, stories, position, foundation)."""
    options = recovered['metadata']['original_selected_options']
    return {k: v for k, v in sorted(options.items())
            if k.startswith('Geometry ') and k not in ('Geometry Floor Area', 'Geometry Building Type RECS')}


def schedule_refs(record, recovered):
    refs = [l['schedule_id'] for l in record['loads'] if l.get('schedule_id')]
    refs += [p['value'] for p in record['parameters'].values()
             if isinstance(p.get('value'), str) and p['value'].startswith('residential-schedule-')]
    refs += [l['schedule_id'] for l in recovered['loads'] if l.get('schedule_id')]
    if any('schedule' in l for l in recovered['loads']):
        raise ValueError('Inline recovered schedules are not expected')
    return list(dict.fromkeys(refs))


def annual(sources, old):
    """A definition-release series or a recovered fixed background series, without its ID."""
    record = sources.definitions.schedules.get(old) or sources.recovery['schedules'].get(old)
    if record is None:
        raise ValueError('Unknown annual schedule '+old)
    return {k: v for k, v in record.items() if k != 'id'}


def filling(sources, record, recovered, ids):
    """The dwelling's fillings: recovered loads and controls, cited by the resolution rows that select them."""
    rows = sorted(sources.resolutions[record['source_id']], key=lambda r: r['id'])
    by_column = collections.defaultdict(list)
    for row in rows:
        by_column[row['field'].split(':', 1)[-1]].append(row['id'])
    loads = []
    for load in recovered['loads']:
        load = translate(load, ids)
        loads.append({**load, 'resolutions': by_column.get(load['end_use'], [])})
    bases = {r['basis'] for r in rows}
    return {'basis': next((b for b in FILLING_BASES if b in bases), 'source_zero'),
            'rules': sorted({r['rule'] for r in rows}), 'resolutions': [r['id'] for r in rows],
            'source': RECOVERY.relative_to(ROOT).as_posix(), 'loads': loads,
            **{k: recovered[k] for k in ('controls', 'climate', 'vintage', 'unresolved', 'metadata')}}


def construction_rows(sources, record):
    """The dwelling's construction context: the construction release expanded labels 7 and 8 into
    A and B contexts with identical documents, so the first stands for the dwelling's own label."""
    sid = sources.sets[record['source_id']]
    rows = sorted(sources.constructions.contexts[sid], key=lambda c: (c['climate_zone'], c['reference_id']))
    return sid, [{**rows[0], 'climate_zone': record['climate']}]


def build(sources=None, ids=None):
    """Every residential/resstock-sdr file, its evidence and glossary entries, as {path: bytes}.

    `ids`, when given, receives every old-to-new identifier: library resources, construction
    sets and their context documents, schedules (per dwelling) and programs.
    """
    from scripts.construction_foundation_release import export_pair
    sources = sources or load_sources()
    ids = {} if ids is None else ids
    definitions = sources.definitions
    # Constructions first: each program cites its set.
    documents, library, evidence = {}, {t: {} for t in atlas_constructions.RESOURCES}, {}
    for record in sources.records:
        sid, rows = construction_rows(sources, record)
        documents[sid] = [(row, *export_pair(row['detailed_context_id'], release=sources.constructions.release)) for row in rows]
        for _, *pair in documents[sid]:
            for document in pair:
                for table in atlas_constructions.RESOURCES:
                    for key, value in document[table].items():
                        if library[table].setdefault(key, value) != value:
                            raise ValueError(f'{key} differs between documents')
                for key, value in document['evidence'].items():
                    if evidence.setdefault(key, value) != value:
                        raise ValueError(f'{key} differs between documents')
    lib_ids = {}
    for table in ('materials', 'assemblies'):
        for old in sorted(library[table]):
            value = translate(library[table][old], lib_ids)
            lib_ids[old] = f'{FAMILY}.{atlas_constructions.origin(value)}.{h6({k: v for k, v in value.items() if k not in ("id", "name")})}'
    files, translated, library_evidence = {}, {}, set()
    for table in atlas_constructions.RESOURCES:
        records = {lib_ids[k]: translate(v, lib_ids) for k, v in library[table].items()}
        files[f'residential/{FAMILY}/library/{table}.json'] = table_bytes(records)
        library_evidence |= set(atlas_constructions.strings(records)) & evidence.keys()
        translated[table] = records
    set_ids, set_map, folder_evidence = {}, {}, collections.defaultdict(set)
    for record in sources.records:
        recovered = sources.recovery['records'][record['source_id']]
        sid, _ = construction_rows(sources, record)
        tokens = {sid: atlas_constructions.SET+':'+sid}
        for row, detailed, unified in documents[sid]:
            key = slug(row['climate_zone'])
            tokens[detailed['id']], tokens[unified['id']] = f'{tokens[sid]}.{key}', f'{tokens[sid]}.{key}.unified'
        stored, _ = atlas_constructions.suite(sources.constructions, sid, documents[sid], {**lib_ids, **tokens}, translated, evidence)
        content = json.loads(atlas_constructions.TOKEN.sub(atlas_constructions.SET, json.dumps(
            {k: v for k, v in stored.items() if k not in ('id', 'name')})))
        bslug = FOLDERS[record['building_type']]
        new = f'{FAMILY}.{bslug}.{dwelling_key(record, recovered)}.{h6(content)}'
        resolved = json.loads(atlas_constructions.TOKEN.sub(lambda m: new, json.dumps(stored, ensure_ascii=False)))
        set_map.update({old: atlas_constructions.TOKEN.sub(lambda m: new, token) for old, token in tokens.items()})
        files[f'residential/{FAMILY}/{bslug}/constructions/{new}.json'] = suite_bytes(resolved)
        set_ids[record['id']] = new
        for _, *pair in documents[sid]:
            folder_evidence[bslug] |= {k for d in pair for k in d['evidence']} - library_evidence
    # Programs and their annual series.
    owners, glossary_terms, program_evidence = collections.defaultdict(dict), [], collections.defaultdict(set)
    for record in sources.records:
        recovered = sources.recovery['records'][record['source_id']]
        bslug = FOLDERS[record['building_type']]
        folder = f'residential/{FAMILY}/{bslug}/'
        local = {}
        series = {}
        for old in schedule_refs(record, recovered):
            content = annual(sources, old)
            origin = content.get('source_channel') or content.get('name')
            local[old] = f'{FAMILY}.{bslug}.{slug(origin)}.{h6(content)}'
            series[local[old]] = content
        program = {k: v for k, v in record.items() if k not in RESERVED}
        program = translate(program, local)
        program.update(floor_area_bin=area_bin(recovered), building_context=building_context(recovered),
                       construction_set_id=set_ids[record['id']], filling=filling(sources, record, recovered, local))
        if record['building_type'] in APARTMENTS:
            program['commercial_counterparts'] = [f'commercial/{t}/{APARTMENTS[record["building_type"]]}/'
                                                  for t in COMMERCIAL_TEMPLATES]
        new = f'{FAMILY}.{bslug}.{dwelling_key(record, recovered)}.{h6(program)}'
        program['id'] = new
        ids[record['id']] = new
        ids[record['id']+':schedules'] = local
        files[f'{folder}programs/{new}.json'] = suite_bytes(program)
        owners[folder][new] = series
        cited = set(atlas_programs.EVIDENCE.findall(canonical([program, list(series.values())])))
        program_evidence[bslug] |= {e for e in cited if e in definitions.evidence}
    for folder, owned in owners.items():
        files.update(annual_files(folder, owned))
    # Evidence: definition provenance per folder, construction evidence per folder and library, resolution rows.
    glossary = {'interpretations': {}, 'transformations': {}, 'source_files': {}}
    for bslug in sorted(program_evidence):
        rows, terms = atlas_programs.encode_evidence(definitions, program_evidence[bslug])
        for section, table in terms.items():
            glossary[section].update(table)
        rows.update({k: translate(evidence[k], {**lib_ids, **set_map}) for k in folder_evidence[bslug]})
        files[f'evidence/residential/{FAMILY}/{bslug}.json'] = table_bytes(rows)
    files[f'evidence/residential/{FAMILY}/library.json'] = table_bytes({k: translate(evidence[k], {**lib_ids, **set_map})
                                                                        for k in library_evidence})
    resolutions = {}
    for record in sources.records:
        for row in sources.resolutions[record['source_id']]:
            resolutions[row['id']] = {k: v for k, v in row.items() if k != 'id'}
    files[f'evidence/residential/{FAMILY}/resolutions.json'] = table_bytes(resolutions)
    ids.update({**lib_ids, **set_map})
    files['evidence/glossary.json'] = table_bytes({**glossary, 'rule_notes': {}, 'unresolved': {}}, sections=True)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, default=ROOT/'build/residential')
    args = parser.parse_args()
    files = build()
    for path, data in files.items():
        out = args.output/path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    programs = sum('/programs/' in p for p in files)
    print(f'Wrote {programs} ResStock dwellings and {len(files)-programs} other files to {args.output}')


if __name__ == '__main__':
    main()
