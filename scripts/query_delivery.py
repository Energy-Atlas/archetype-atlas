"""Build a generic, immutable static read layer over frozen atlas releases."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from jsonschema import Draft202012Validator
from scripts.common import ROOT, load_atlas, load_json

SCHEMA_VERSION = '1.0.0'
MAX_PACKET_BYTES = 131072
TABLE_TYPES = {
    'programs': 'program', 'schedules': 'schedule',
    'envelope_components': 'envelope_component', 'systems': 'system',
    'mappings': 'mapping', 'efficiency_rules': 'efficiency_rule',
    'residential_options': 'residential_option', 'commercial_options': 'commercial_option',
    'residential_archetypes': 'residential_archetype', 'specialized_rules': 'specialized_rule',
}
GROUP_FIELDS = ('source_family', 'building_type', 'template', 'climate_zone_set')
DETAIL_FIELDS = {'source_attributes', 'selected_options', 'unit_interpretations'}
SCHEMA_FILES = ('query-artifact.schema.json', 'query-request.schema.json', 'query-response.schema.json')


def json_bytes(value):
    """Canonical transport bytes: sorted keys, compact UTF-8, finite JSON, LF."""
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def safe_path(root, href):
    """Only literal publication-root-relative paths are admissible."""
    if (not isinstance(href, str) or not href or re.search(r'[:\\?#%\x00-\x20]', href)
            or any(p in {'', '.', '..'} for p in href.split('/'))):
        raise ValueError('Unsafe resource path')
    root = Path(root).resolve()
    path = (root/href).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Resource path escape')
    return path


def checked_target(target):
    target = Path(target).resolve()
    if target == ROOT or any(target.is_relative_to(ROOT/p) for p in
                             ('data', 'sources', 'schemas', 'scripts', 'tests', 'website', 'docs', '.git')):
        raise ValueError('Delivery target is protected research/source storage')
    if target.exists() and any(target.iterdir()) and not (target/'latest.json').is_file():
        raise ValueError('Delivery target contains unrelated files')
    return target


def descriptor(href, content):
    return {'href': href, 'sha256': sha(content), 'size_bytes': len(content)}


def check_reference(root, ref):
    path = safe_path(root, ref['href'])
    content = path.read_bytes()
    if len(content) != ref['size_bytes'] or sha(content) != ref['sha256']:
        raise ValueError('Resource checksum/size mismatch: ' + ref['href'])
    return content


def decode_reference(content, ref):
    """Decode the explicit file encoding after checking the transport checksum."""
    if ref.get('encoding') == 'gzip':
        limit = ref['decoded_size_bytes']
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as stream:
            decoded = stream.read(limit + 1)
        if len(decoded) != limit:
            raise ValueError('Decoded resource size mismatch')
        return decoded
    return content


def references(value):
    """Find typed resource descriptors without interpreting source text as paths."""
    if isinstance(value, dict):
        if {'href', 'sha256', 'size_bytes'} <= set(value) <= {'href', 'sha256', 'size_bytes', 'encoding', 'decoded_size_bytes'}:
            yield value
        else:
            for v in value.values():
                yield from references(v)
    elif isinstance(value, list):
        for v in value:
            yield from references(v)


def generate_delivery(target, data, dependencies, supplement=None, reporting=None,
                      profile_root=None, notices=None, completion=None):
    """Generate and verify before replacing only an owned delivery directory.

    Callers supply validated immutable inputs. Source values are never mutated.
    Relative hrefs resolve against this directory, never the referring document.
    """
    target = checked_target(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as work:
        stage = Path(work)/'delivery'
        stage.mkdir()
        manifest = _generate(stage, data, dependencies, supplement, reporting, profile_root, notices, completion)
        errors = validate_delivery(stage)
        if errors:
            raise ValueError('Invalid delivery: ' + '; '.join(errors[:8]))
        # Retain previously advertised immutable resources and snapshots on rebuild.
        # A clean publisher uses restore_history before generation (see CLI/site).
        if target.exists():
            retained_errors = validate_delivery(target) if (target/'latest.json').exists() else []
            if retained_errors:
                raise ValueError('Invalid retained delivery: ' + '; '.join(retained_errors[:4]))
            for source in sorted(target.rglob('*')):
                if source.is_file() and source.relative_to(target).parts[0] in {'resources', 'snapshots'}:
                    dest = stage/source.relative_to(target)
                    if dest.exists() and dest.read_bytes() != source.read_bytes():
                        raise ValueError('Immutable delivery path collision')
                    if not dest.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source, dest)
            backup = Path(work)/'previous'
            target.rename(backup)
            try:
                stage.rename(target)
            except OSError:
                backup.rename(target)
                raise
        else:
            stage.rename(target)
    return manifest


def _generate(root, data, dependencies, supplement, reporting, profile_root, notices, completion):
    def resource(value):
        content = json_bytes(value)
        decoded_size = len(content)
        if decoded_size > 512:
            # Fixed timestamp and header OS byte make the gzip envelope portable.
            content = gzip.compress(content, compresslevel=9, mtime=0)
            content = content[:9] + bytes([255]) + content[10:]
            suffix = '.json.gz'
        else:
            suffix = '.json'
        href = 'resources/' + sha(content) + suffix
        path = root/href
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(content)
        ref = descriptor(href, content)
        if suffix.endswith('.gz'):
            ref.update(encoding='gzip', decoded_size_bytes=decoded_size)
        return ref

    def payload(kind, record, representation=None, evidence=None):
        packet = {'schema_version': SCHEMA_VERSION, 'kind': kind, 'record': record}
        if representation:
            packet['representation'] = representation
        if evidence:
            packet['evidence'] = evidence
        return resource(packet)

    provenance = {r['id']: r for r in data.get('provenance', [])}
    source_files = {r['id']: r for r in data.get('source_files', [])}
    resolutions = {}
    for row in (supplement or {}).get('resolutions', []):
        key = (row['record_table'], row['record_id'])
        fields = resolutions.setdefault(key, {})
        if row['field'] in fields:
            raise ValueError('Duplicate field resolution')
        fields[row['field']] = row

    def evidence(row, table):
        prov = provenance.get(row.get('provenance_id'))
        return resource({'schema_version': SCHEMA_VERSION, 'kind': 'evidence', 'record': row,
                         'provenance': prov, 'resolutions': resolutions.get((table, row['id']), {}),
                         'source_files': [source_files[prov['source_file_id']]] if prov else []})

    schedules = {}
    for row in data.get('schedules', []):
        schedules[row['id']] = payload('schedule', row, 'rules', evidence(row, 'schedules'))
    if reporting:
        for row in reporting['schedules']:
            if row['id'] in schedules:
                raise ValueError('Duplicate schedule ID')
            schedules[row['id']] = payload('schedule', row, 'rules', evidence(row, 'water_schedule'))
    if completion:
        for item in completion['schedules']:
            for field in ('source_schedule', 'equivalent_schedule'):
                row = item[field]
                details = resource({'schema_version': SCHEMA_VERSION, 'kind': 'evidence',
                                    'record': item, 'provenance': None, 'resolutions': {},
                                    'source_files': []})
                ref = payload('schedule', row, 'rules', details)
                if row['id'] in schedules and ref != schedules[row['id']]:
                    raise ValueError('Conflicting schedule ID')
                schedules[row['id']] = ref

    profiles = {}
    fixed = None

    def resolved_field(row):
        nonlocal fixed
        value = copy.deepcopy(row['resolved_value'])
        ref = None
        if isinstance(value, dict) and 'constant_value' in value:
            record = {'value': value['constant_value'], 'units': row['unit'],
                      'calendar_independent': value['calendar_independent']}
            ref = payload('schedule', record, 'constant')
            value = 'derived-' + ref['sha256']
        elif isinstance(value, dict) and 'profile_file' in value:
            if profile_root is None:
                raise ValueError('Profile root required for residential resolutions')
            path = safe_path(profile_root, value['profile_file'])
            if path not in profiles:
                profiles[path] = load_json(path)
            profile = profiles[path]
            series = profile['series'][value['column']]
            if len(series) != 8760:
                raise ValueError('Annual series must retain 8760 source hours')
            ref = payload('schedule', {'metadata': profile['metadata'], 'column': value['column'],
                                       'units': row['unit'], 'values': series}, 'annual_series')
            value = 'derived-' + ref['sha256']
        elif isinstance(value, dict) and 'fixed_schedule_id' in value:
            if profile_root is None:
                raise ValueError('Profile root required for fixed resolutions')
            if fixed is None:
                fixed = load_json(safe_path(profile_root, value['schedule_file']))
            ref = payload('schedule', fixed['schedules'][value['fixed_schedule_id']], 'fixed_profiles')
            value = 'derived-' + ref['sha256']
        result = {'value': value, 'unit': row['unit'], 'status': 'reviewed',
                  'evidence_pointer': '/resolutions/' + pointer_token(row['field'])}
        if ref:
            result['resource'] = ref
        return result

    type_rows = {}
    for table, kind in TABLE_TYPES.items():
        type_rows[kind] = (table, data.get(table, []))
    if reporting:
        type_rows['water_reporting'] = ('water_reporting', [dict(r, id=r['program_id']) for r in reporting['programs']])
        type_rows['water_service'] = ('water_service', [dict(r, id=r['path_id']) for r in reporting['services']])
    if completion:
        type_rows['water_draw'] = ('water_draw', [dict(r, id=r['path_id']) for r in completion['draw_paths']])

    types = {}
    for kind, (table, rows) in type_rows.items():
        field_names, filter_fields, groups, ids = set(), {'id'}, {}, set()
        for row in sorted(rows, key=lambda r: r['id']):
            if row['id'] in ids:
                raise ValueError('Duplicate record ID in ' + kind)
            ids.add(row['id'])
            prov = provenance.get(row.get('provenance_id'))
            if table in TABLE_TYPES and prov is None:
                raise ValueError('Missing provenance: ' + row['id'])
            reviewed = resolutions.get((table, row['id']), {})
            evidence_ref = evidence(row, table)
            fields = {}
            for field, value in row.items():
                if field in {'id', 'provenance_id'} | DETAIL_FIELDS:
                    continue
                pointer = '/provenance/fields/' + pointer_token(field) if prov else '/record/' + pointer_token(field)
                field_unit = data.get('units', {}).get(field)
                field_unit = field_unit or {'occupants': 'person/unit', 'occupants_per_unit': 'person/unit', 'heating_base_C': 'C',
                                           'cooling_base_C': 'C', 'conditioned_floor_area_m2': 'm2',
                                           'reference_reporting_peak_flow_m3_s': 'm3/s',
                                           'reference_rated_flow_m3_s': 'm3/s',
                                           'reference_area_m2': 'm2', 'target_temperature_degC': 'C'}.get(field)
                if field in {'rated_flow_m3_s', 'equivalent_peak_flow_m3_s'}:
                    field_unit = 'm3/s'
                elif field in {'rated_flow_per_area_m3_s_m2', 'equivalent_peak_flow_per_area_m3_s_m2'}:
                    field_unit = 'm3/s/m2'
                fields[field] = {'value': value, 'unit': field_unit,
                                 'status': 'unknown' if value is None else 'source',
                                 'evidence_pointer': pointer}
                if field.endswith('_schedule_id') and value in schedules:
                    fields[field]['resource'] = schedules[value]
            # Explicit source-context labels, not a climate compatibility inference.
            if table == 'residential_archetypes':
                for name, key in [('reported_climate_zone', 'ASHRAE IECC Climate Zone 2004'), ('stock_vintage', 'Vintage')]:
                    fields[name] = {'value': row.get('source_context', {}).get(key), 'unit': None,
                                    'status': 'source' if row.get('source_context', {}).get(key) is not None else 'unknown',
                                    'evidence_pointer': '/record/source_context/' + pointer_token(key)}
            overrides = {field: resolved_field(r) for field, r in sorted(reviewed.items())}
            field_names.update(fields)
            field_names.update(overrides)
            for field, dto in {**fields, **overrides}.items():
                if not isinstance(dto['value'], (dict, list)):
                    filter_fields.add(field)
            record = {'id': row['id'], 'fields': fields, 'reviewed': overrides, 'evidence': evidence_ref}
            grouping = {field: row[field] for field in GROUP_FIELDS if field in row}
            if kind == 'schedule':
                grouping = {'id': row['id']}
            key = json_bytes(grouping)
            groups.setdefault(key, (grouping, []))[1].append(record)

        routes = []
        for key, (selectors, records) in sorted(groups.items()):
            packets, current, packet_ids = [], [], []
            for record in records:
                candidate = {'schema_version': SCHEMA_VERSION, 'kind': 'packet',
                             'record_type': kind, 'records': current + [record]}
                if len(json_bytes(candidate)) > MAX_PACKET_BYTES and current:
                    packets.append(resource({'schema_version': SCHEMA_VERSION, 'kind': 'packet',
                                             'record_type': kind, 'records': current}))
                    packet_ids.append([r['id'] for r in current])
                    current = []
                single = {'schema_version': SCHEMA_VERSION, 'kind': 'packet', 'record_type': kind, 'records': [record]}
                if len(json_bytes(single)) > MAX_PACKET_BYTES:
                    raise ValueError('Single record exceeds delivery packet bound: ' + record['id'])
                current.append(record)
            if current:
                packets.append(resource({'schema_version': SCHEMA_VERSION, 'kind': 'packet',
                                         'record_type': kind, 'records': current}))
                packet_ids.append([r['id'] for r in current])
            routes.extend({'selectors': selectors, 'record_ids': ids, 'packets': [ref]}
                          for ref, ids in zip(packets, packet_ids))
        index = resource({'schema_version': SCHEMA_VERSION, 'kind': 'index', 'record_type': kind, 'routes': routes})
        types[kind] = {'record_count': len(rows), 'fields': sorted(field_names),
                       'filter_fields': sorted(filter_fields), 'index': index}

    schemas = {}
    for name in SCHEMA_FILES:
        content = (ROOT/'schemas'/name).read_bytes()
        dest = root/'schemas'/name
        dest.parent.mkdir(exist_ok=True)
        dest.write_bytes(content)
        immutable = 'resources/' + sha(content) + '.schema.json'
        (root/immutable).write_bytes(content)
        schemas[name] = descriptor(immutable, content)
    licenses = []
    for name, content in sorted((notices or {'LICENSE': (ROOT/'LICENSE').read_bytes()}).items()):
        href = 'resources/' + sha(content) + '.txt'
        path = root/href; path.parent.mkdir(exist_ok=True); path.write_bytes(content)
        licenses.append({'name': name, 'resource': descriptor(href, content)})
    manifest = {'schema_version': SCHEMA_VERSION, 'kind': 'manifest', 'dependencies': dependencies,
                'record_types': types, 'schemas': schemas, 'notices': licenses,
                'max_packet_bytes': MAX_PACKET_BYTES, 'views': ['source', 'reviewed']}
    manifest['snapshot_id'] = sha(json_bytes(manifest))
    content = json_bytes(manifest)
    href = 'snapshots/' + manifest['snapshot_id'] + '/manifest.json'
    path = root/href; path.parent.mkdir(parents=True); path.write_bytes(content)
    (root/'latest.json').write_bytes(json_bytes({'schema_version': SCHEMA_VERSION, 'kind': 'latest',
                                              'snapshot_id': manifest['snapshot_id'],
                                              'manifest': descriptor(href, content)}))
    return manifest


def pointer_token(value):
    return value.replace('~', '~0').replace('/', '~1')


def validate_delivery(root):
    """Verify transitive advertised bytes, wire schema, IDs and count inventory."""
    errors, seen = [], set()
    root = Path(root)
    validator = Draft202012Validator(load_json(ROOT/'schemas/query-artifact.schema.json'))
    try:
        latest = load_json(Path(root)/'latest.json')
        validator.validate(latest)
        current = json.loads(check_reference(root, latest['manifest']))
        validator.validate(current)
        if current['snapshot_id'] != latest['snapshot_id']:
            raise ValueError('Snapshot identity mismatch')
        if latest['manifest']['href'] != 'snapshots/' + current['snapshot_id'] + '/manifest.json':
            raise ValueError('Unexpected snapshot manifest path')
        # The publisher promises every historical URL, not only today's closure.
        for path in (root/'resources').rglob('*'):
            if path.is_file():
                if (not re.fullmatch(r'[a-f0-9]{64}\.(?:json(?:\.gz)?|schema\.json|txt)', path.name)
                        or path.parent != root/'resources'):
                    raise ValueError('Invalid content-addressed retained resource path')
                if sha(path.read_bytes()) != path.name[:64]:
                    raise ValueError('Retained resource checksum mismatch')
        for path in (root/'snapshots').rglob('*'):
            if path.is_file():
                rel = path.relative_to(root/'snapshots')
                if len(rel.parts) != 2 or rel.name != 'manifest.json' or not re.fullmatch(r'[a-f0-9]{64}', rel.parts[0]):
                    raise ValueError('Invalid retained snapshot path')
                manifest = load_json(path)
                validator.validate(manifest)
                if manifest['kind'] != 'manifest' or manifest['snapshot_id'] != rel.parts[0]:
                    raise ValueError('Retained snapshot identity mismatch')
                unsigned = {k: v for k, v in manifest.items() if k != 'snapshot_id'}
                if sha(json_bytes(unsigned)) != manifest['snapshot_id']:
                    raise ValueError('Snapshot identity mismatch')
                _validate_manifest(root, manifest, validator, seen)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    except Exception as exc:
        # jsonschema's rich validation errors are data diagnostics, not instructions.
        errors.append(type(exc).__name__ + ': ' + str(exc).splitlines()[0])
    return errors


def _validate_manifest(root, manifest, validator, seen):
    pending = list(references(manifest))
    while pending:
        ref = pending.pop()
        key = json_bytes(ref)
        if key in seen:
            continue
        seen.add(key)
        content = check_reference(root, ref)
        if ref['href'].endswith(('.json', '.json.gz')) and not ref['href'].endswith('.schema.json'):
            decoded = decode_reference(content, ref)
            packet = json.loads(decoded)
            validator.validate(packet)
            if packet['kind'] == 'packet' and len(decoded) > manifest['max_packet_bytes']:
                raise ValueError('Packet exceeds byte bound')
            pending.extend(references(packet))
    for kind, info in manifest['record_types'].items():
        index = json.loads(decode_reference(check_reference(root, info['index']), info['index']))
        if index['kind'] != 'index' or index['record_type'] != kind:
            raise ValueError('Index record_type mismatch')
        records = []
        for route in index['routes']:
            routed = []
            for ref in route['packets']:
                packet = json.loads(decode_reference(check_reference(root, ref), ref))
                if packet['kind'] != 'packet' or packet['record_type'] != kind:
                    raise ValueError('Packet record_type mismatch')
                routed.extend(packet['records'])
            if sorted(route['record_ids']) != sorted(r['id'] for r in routed):
                raise ValueError('Route ID inventory mismatch')
            for record in routed:
                for field, value in route['selectors'].items():
                    actual = record['id'] if field == 'id' else record['fields'][field]['value']
                    if type(actual) is not type(value) or actual != value:
                        raise ValueError('Route selector mismatch')
            records.extend(routed)
        if len(records) != info['record_count'] or len({r['id'] for r in records}) != len(records):
            raise ValueError('Record inventory mismatch: ' + kind)


def frozen_inputs():
    """Reuse the repository's independent frozen-release validators."""
    from scripts.release import verify_release
    from scripts.resolve import validate_bundle
    from scripts.water_reporting import validate_bundle as validate_reporting
    paths = {'atlas': ROOT/'data/releases/v0.2.0',
             'resolution': ROOT/'data/resolution-releases/v0.4.0',
             'completion': ROOT/'data/completion-releases/v0.1.0',
             'water_reporting': ROOT/'data/water-reporting-releases/v0.1.0'}
    errors = verify_release(paths['atlas'])
    if errors:
        raise ValueError('Base release invalid: ' + '; '.join(errors[:4]))
    supplement = validate_bundle(paths['resolution'], paths['atlas'])
    reporting = validate_reporting(paths['water_reporting'])
    dependencies = {name: {'version': path.name[1:], 'manifest_sha256': sha((path/'manifest.json').read_bytes())}
                    for name, path in paths.items()}
    notices = {'LICENSE': (ROOT/'LICENSE').read_bytes()}
    for path in paths.values():
        for file in sorted((path/'sources/licenses').glob('*.txt')):
            name = file.name
            if name in notices and notices[name] != file.read_bytes():
                raise ValueError('Conflicting upstream license notices')
            notices[name] = file.read_bytes()
    return (load_atlas(paths['atlas']), dependencies, supplement, reporting, paths['resolution'],
            notices, load_json(paths['completion']/'commercial-completion.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=ROOT/'build/query-delivery')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        errors = validate_delivery(args.target)
        if errors:
            raise SystemExit('; '.join(errors))
        print('Query delivery verified')
    else:
        data, deps, supplement, reporting, profiles, notices, completion = frozen_inputs()
        result = generate_delivery(args.target, data, deps, supplement, reporting, profiles, notices, completion)
        print('Generated query snapshot ' + result['snapshot_id'])


if __name__ == '__main__':
    main()
