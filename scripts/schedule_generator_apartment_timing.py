"""Compile the locked, selected apartment timing domain and test resources.

This is a build-only source compiler. It never reads the installed M1 resource
directory and never fetches missing archive bytes.
"""
import gzip
import hashlib
from pathlib import Path

from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet, strict_json, write_resources
from scripts.common import ROOT
from scripts.schedule_generator_sources import _archive_members, _fetch, _verify, compile_member


# Appendix B, in first positive M1 then R1 encounter order. The whole tuple is
# the controlled regression domain; its coordinate columns are not independent.
EXPECTED_LOCATIONS = (
    ('NC',35.741,-81.389,-5), ('CA',35.741,-81.389,-5),
    ('NC',61.21,-149.85,-9), ('AK',61.2169,-149.868,-9),
    ('TN',36.0389,-86.6391,-6), ('CA',37.4486,-121.859,-8),
    ('UT',40.5144,-112.033,-7), ('NC',35.7628,-81.3219,-5),
    ('MA',42.5209,-71.7716,-5), ('TX',30.4821,-96.3027,-6),
    ('VT',44.4872,-73.2278,-5), ('OH',41.6504,-83.6702,-5),
    ('CA',33.8878,-117.453,-8), ('OR',45.4813,-122.599,-8),
    ('HI',21.3175,-157.843,-10), ('WI',44.7924,-88.6722,-6),
    ('AK',56.9471,-135.043,-9), ('FL',26.9089,-82.0431,-5),
    ('FL',25.9339,-80.1467,-5), ('PA',39.9842,-75.6084,-5),
    ('NY',40.8129,-73.3611,-5), ('NY',40.6463,-73.9564,-5),
    ('CA',34.608,-120.365,-8), ('CA',38.7844,-121.388,-8),
    ('SC',34.7447,-82.2574,-5), ('NJ',39.8266,-75.1276,-5),
    ('IL',41.7654,-88.3772,-6), ('AK',65.0735,-148.449,-9),
    ('FL',28.304,-82.7021,-5), ('NV',39.4944,-119.747,-8),
    ('AZ',34.6071,-112.317,-7), ('AZ',33.8418,-114.1,-7),
    ('MI',42.2256,-83.2685,-5), ('AK',61.772,-148.182,-9),
    ('AR',35.2662,-91.8491,-6), ('MO',37.1074,-94.5218,-6),
    ('TX',32.5215,-97.3032,-6),
)
FIELDS = ('state', 'latitude', 'longitude', 'time_zone_utc_offset')
UNITS = ('USPS postal state', 'degrees north', 'degrees east', 'hours from UTC')


def _locked_bytes(path: Path, sha256: str) -> bytes:
    try:
        content = Path(path).read_bytes()
    except OSError as error:
        raise GeneratorError('missing_source', str(path), 'Locked local source is absent') from error
    if hashlib.sha256(content).hexdigest() != sha256:
        raise GeneratorError('source_integrity', str(path), 'Locked source bytes differ')
    return content


def _verify_lock(locks):
    if (not isinstance(locks, dict) or locks.get('schema_version') != '1.0.0' or
            locks.get('method') != 'unit_occupancy_interior_lighting' or
            len(locks.get('residential_resources', {})) != 32):
        raise GeneratorError('source_integrity', '/apartment_timing_lock', 'Exact selected timing lock required')
    source_lock = strict_json(_locked_bytes(ROOT/locks['source_lock_path'],
                                            locks['source_lock_sha256']), locks['source_lock_path'])
    archive = next((x for x in source_lock['archives']
                    if x['cache_path'] == locks['source_archive']['cache_path']), None)
    if (archive is None or archive['sha256'] != locks['source_archive']['sha256'] or
            archive['size_bytes'] != locks['source_archive']['size_bytes'] or
            archive['source_revision'] != locks['source_revision']):
        raise GeneratorError('source_integrity', '/source_archive', 'ResStock source cut differs')
    return archive


def compile_apartment_timing_domain(m1_vectors: Path, r1_vectors: Path, locks: dict) -> dict:
    """Compile exact positive 2007 native argument tuples and field evidence."""
    _verify_lock(locks)
    cases = []
    for label, path in (('M1', m1_vectors), ('R1', r1_vectors)):
        vector_lock = locks['vectors'][label]
        reference = strict_json(_locked_bytes(ROOT/vector_lock['reference_lock_path'],
                                                vector_lock['reference_lock_sha256']),
                                vector_lock['reference_lock_path'])
        if reference['vectors']['sha256'] != vector_lock['sha256']:
            raise GeneratorError('source_integrity', str(path), 'Native reference lock differs')
        content = _locked_bytes(path, vector_lock['sha256'])
        if label == 'R1':
            content = gzip.decompress(content)
            if hashlib.sha256(content).hexdigest() != vector_lock['payload_sha256']:
                raise GeneratorError('source_integrity', str(path), 'R1 payload differs')
        source = strict_json(content, str(path))
        for index, case in enumerate(source['cases']):
            args = case['inputs']
            raw_n = args['residents']
            if (args['year'] != 2007 or isinstance(raw_n, bool) or
                    not isinstance(raw_n, (int, float)) or raw_n <= 0 or int(raw_n) <= 0 or
                    not all(key in case['channels'] and len(case['channels'][key]) == 8760
                            for key in ('occupants', 'lighting_interior'))):
                continue
            cases.append((label, index, case))
    if (sum(label == 'M1' for label, _, _ in cases),
            sum(label == 'R1' for label, _, _ in cases)) != (6, 48):
        raise GeneratorError('source_integrity', '/cases', 'Expected 6 M1 and 48 R1 positive targets')
    locations = []
    by_tuple = {}
    for label, index, case in cases:
        args = case['inputs']
        values = tuple(args[key] for key in FIELDS)
        if values not in by_tuple:
            location = {'location_id': f'L{len(locations)+1:02d}',
                        **{key: args[key] for key in FIELDS}, 'evidence': []}
            locations.append(location)
            by_tuple[values] = location
        vector_lock = locks['vectors'][label]
        locator = f"{vector_lock['path']}#/cases/{index}/inputs"
        evidence = {'native_case_locator': f"{vector_lock['path']}#/cases/{index}",
                    'native_case_id': case['case_id'],
                    'native_file_sha256': vector_lock['sha256'],
                    'source_revision': locks['source_revision'],
                    'fields': {key: {'source_locator': locator+'/'+key,
                                     'original_value': args[key], 'original_unit': unit,
                                     'transformation': 'Exact native argument; no unit conversion',
                                     'extraction_date': locks['extraction_date'],
                                     'interpretation_note': 'Controlled selected-method regression argument; no prototype or stock default'}
                               for key, unit in zip(FIELDS, UNITS)}}
        by_tuple[values]['evidence'].append(evidence)
    if len(locations) != 37 or tuple(tuple(location[key] for key in FIELDS)
                                     for location in locations) != EXPECTED_LOCATIONS:
        raise GeneratorError('source_integrity', '/locations', 'Native tuples differ from Appendix B')
    return {'schema_version': '1.0.0', 'method': 'unit_occupancy_interior_lighting',
            'calendar': {'year': 2007, 'clock': 'local_standard_time', 'holidays': []},
            'locations': locations,
            'evidence': [{'source_locator': locks['vectors'][label]['path']+'#/cases',
                          'sha256': locks['vectors'][label]['sha256'],
                          'reference_lock': locks['vectors'][label]['reference_lock_path'],
                          'reference_lock_sha256': locks['vectors'][label]['reference_lock_sha256'],
                          'source_revision': locks['source_revision'],
                          'extraction_date': locks['extraction_date'],
                          'interpretation_note': 'Positive 2007 native selected-channel arguments only'}
                         for label in ('M1', 'R1')]}


def build_apartment_timing_test_resources(destination: Path, domain: dict,
                                          source_lock: dict, cache_root: Path) -> ResourceSet:
    """Recompile 32 archive members and one timing domain into an isolated set."""
    archive = _verify_lock(source_lock)
    if domain != compile_apartment_timing_domain(ROOT/source_lock['vectors']['M1']['path'],
                                                  ROOT/source_lock['vectors']['R1']['path'],
                                                  source_lock):
        raise GeneratorError('source_integrity', '/apartment-timing-domain', 'Domain differs from locked native arguments')
    durable = source_lock['domain_artifact']
    if strict_json(_locked_bytes(ROOT/durable['path'], durable['sha256']), durable['path']) != domain:
        raise GeneratorError('source_integrity', durable['path'], 'Durable timing domain differs')
    destination = Path(destination).resolve()
    allowed = (ROOT/'build/task-10/apartment-a1').resolve()
    if not destination.is_relative_to(allowed):
        raise GeneratorError('unsafe_resource_path', str(destination), 'Selected test resources belong under own build path')
    selected = source_lock['residential_resources']
    entries = {entry['key']: entry for entry in archive['members'] if entry['kind'] == 'residential'}
    if set(selected) - set(entries):
        raise GeneratorError('missing_resource', '/residential_resources', 'Locked source member is absent')
    raw_archive = _fetch(archive, cache_root, verify_only=True)
    members = _archive_members(raw_archive, archive['format'],
                               {entries[key]['path'] for key in selected})
    records = {}
    for key, expected_hash in selected.items():
        entry = entries[key]
        raw = members.get(entry['path'])
        if raw is None:
            raise GeneratorError('missing_source', entry['path'], 'Locked archive member is absent')
        _verify(raw, entry)
        record = compile_member(raw, entry, archive)
        if hashlib.sha256(canonical(record)).hexdigest() != expected_hash:
            raise GeneratorError('source_integrity', entry['path'], 'Canonical residential record differs')
        records['residential', key] = record
    domain_hash = hashlib.sha256(canonical(domain)).hexdigest()
    records['reference', 'apartment-timing-domain'] = {
        'schema_version': '1.0.0', 'format': 'source_domain', 'value': domain,
        'provenance': {'source_revision': source_lock['source_revision'],
                       'source_lock_sha256': source_lock['source_lock_sha256'],
                       'native_capture_sha256': {label: source_lock['vectors'][label]['sha256']
                                                 for label in ('M1', 'R1')},
                       'extraction_date': source_lock['extraction_date'],
                       'upstream_notices': source_lock['notices'],
                       'interpretation_note': 'Selected-method controlled timing domain only'}}
    manifest = write_resources(destination, records, {
        'scope': 'selected_method_component_test',
        'source_lock_sha256': hashlib.sha256(canonical(source_lock)).hexdigest(),
        'domain_sha256': domain_hash, 'upstream_notices': source_lock['notices']})
    return ResourceSet(destination, manifest['resource_set_id'])
