"""Compile checksum-locked public evidence without executing upstream code."""
import argparse
import csv
import hashlib
import io
import math
from pathlib import Path
import tarfile
import urllib.parse
import urllib.request
import zipfile

from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import safe_path, strict_json, write_resources
from scripts.common import ROOT


def _verify(content, entry):
    if len(content) != entry['size_bytes'] or hashlib.sha256(content).hexdigest() != entry['sha256']:
        raise GeneratorError('source_integrity', entry.get('path', entry.get('cache_path', '/')), 'Locked source bytes differ')


def _fetch(entry, cache_root, verify_only=False):
    name = entry['cache_path']
    safe_path(name)
    target = (Path(cache_root)/name).resolve()
    if not target.is_relative_to(Path(cache_root).resolve()):
        raise GeneratorError('unsafe_resource_path', name, 'Cache path escapes root')
    if not target.exists():
        if verify_only:
            raise GeneratorError('missing_source', name, 'Locked cache member is absent')
        url = urllib.parse.urlsplit(entry['url'])
        if url.scheme != 'https' or url.hostname not in {'raw.githubusercontent.com', 'codeload.github.com', 'rubygems.org', 'data.nlr.gov', 'api.github.com'} or url.username or url.password:
            raise GeneratorError('unsafe_source_url', name, 'Source must be public official HTTPS')
        with urllib.request.urlopen(entry['url'], timeout=60) as response:
            content = response.read(entry['size_bytes'] + 1)
        _verify(content, entry)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(content)
    content = target.read_bytes()
    _verify(content, entry)
    return content


def _archive_members(content, format, selected=None):
    result = {}
    seen = set()
    if format == 'zip':
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for member in archive.infolist():
                safe_path(member.filename.rstrip('/'))
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise GeneratorError('unsafe_resource_path', member.filename, 'Archive symlink is forbidden')
                if not member.is_dir():
                    if member.filename in seen:
                        raise GeneratorError('source_integrity', member.filename, 'Duplicate archive member')
                    seen.add(member.filename)
                    if selected is None or member.filename in selected:
                        result[member.filename] = archive.read(member)
    elif format in {'tar', 'gem'}:
        with tarfile.open(fileobj=io.BytesIO(content)) as archive:
            for member in archive:
                safe_path(member.name.rstrip('/'))
                if not member.isfile() and not member.isdir():
                    raise GeneratorError('unsafe_resource_path', member.name, 'Archive links/devices are forbidden')
                if member.isfile():
                    if member.name in seen:
                        raise GeneratorError('source_integrity', member.name, 'Duplicate archive member')
                    seen.add(member.name)
                    if format == 'gem' and member.name == 'data.tar.gz' or format != 'gem' and (selected is None or member.name in selected):
                        result[member.name] = archive.extractfile(member).read()
        if format == 'gem':
            return _archive_members(result['data.tar.gz'], 'tar', selected)
    else:
        raise GeneratorError('unsupported_resource', format, 'Unsupported archive format')
    return result


def _probabilities(values, path, tolerance=1e-6):
    try:
        numbers = [float(v) for v in values]
    except (ValueError, TypeError) as error:
        raise GeneratorError('invalid_probability', path, 'Incomplete/nonnumeric probability') from error
    if not numbers or any(not math.isfinite(x) or x < 0 or x > 1 for x in numbers) or abs(math.fsum(numbers)-1) > tolerance:
        raise GeneratorError('invalid_probability', path, 'Probability distribution is malformed')
    return numbers


def compile_member(content: bytes, entry: dict, source: dict) -> dict:
    """Preserve ordered original cells; cell locators are row/column coordinates."""
    path = entry['path']
    provenance = {'source_id': source['source_id'], 'source_revision': source['source_revision'],
                  'source_url': source['url'], 'source_path': path, 'source_sha256': entry['sha256'],
                  'extraction_date': entry['extraction_date'], 'original_unit': entry['original_unit'],
                  'transformation': 'Ordered UTF-8 table; original cells retained; finite numeric cells parsed without rounding',
                  'interpretation_note': entry.get('interpretation_note', 'Source order retained; no population-equivalence claim'),
                  'field_locator': 'source_path#row=<1-based source line>/column=<1-based column>; original value in original_values'}
    format = entry['format']
    text = content.decode('utf-8-sig')
    record = {'schema_version': '1.0.0', 'format': format, 'provenance': provenance}
    if format == 'conditional_tsv':
        table = list(csv.reader(io.StringIO(text), delimiter='\t'))
        header = table[0]
        deps = [h[11:] for h in header if h.startswith('Dependency=')]
        options = [h[7:] for h in header if h.startswith('Option=')]
        if len(set(header)) != len(header) or not options or len(deps)+len(options) != len(header):
            raise GeneratorError('invalid_probability', path, 'Invalid distribution columns')
        rows, seen = [], set()
        for index, cells in enumerate(table[1:], 2):
            if len(cells) != len(header) or any(not cells[header.index('Dependency='+d)] for d in deps):
                raise GeneratorError('invalid_probability', path, 'Incomplete distribution row')
            selectors = {d: cells[header.index('Dependency='+d)] for d in deps}
            if any(selectors.get(d) != value for d, value in entry.get('fixed_selectors', {}).items()):
                continue
            selector_tuple = tuple(selectors.items())
            if selector_tuple in seen:
                raise GeneratorError('invalid_probability', path, 'Ambiguous conditional row')
            seen.add(selector_tuple)
            original = [cells[header.index('Option='+o)] for o in options]
            rows.append({'source_row': index, 'selectors': selectors, 'original_values': original,
                         'probabilities': _probabilities(original, path)})
        if not rows:
            raise GeneratorError('missing_resource', path, 'No rows match explicit locked selectors')
        record.update(dependencies=deps, options=options, columns=header, rows=rows,
                      fixed_selectors=entry.get('fixed_selectors', {}))
        provenance['transformation'] += '; rows filtered only by explicit locked fixed_selectors'
        if 'option_quantity' in entry:
            quantity = entry['option_quantity']
            record['option_values'] = [None if option == 'NA' else float(option)*quantity['multiplier'] for option in options]
            record['option_unit'] = quantity['unit']
            record['option_provenance'] = {'original_values': options, 'original_unit': quantity['original_unit'],
                                         'transformation': f"Multiply by {quantity['multiplier']} to {quantity['unit']}; NA remains null",
                                         'source_locator': path+'#header/Option columns', 'extraction_date': entry['extraction_date'],
                                         'interpretation_note': 'Source option strings are used for conditioning; normalized quantities are SI'}
    elif format in {'csv', 'probability_csv'}:
        rows = list(csv.reader(io.StringIO(text)))
        numerical = []
        for cells in rows:
            parsed = []
            for cell in cells:
                try:
                    value = float(cell)
                except ValueError:
                    parsed.append(None)
                else:
                    if not math.isfinite(value):
                        raise GeneratorError('invalid_probability', path, 'Nonfinite numerical resource')
                    parsed.append(value)
            numerical.append(parsed)
        # The lock names actual probability axes, never guesses from filename.
        if format == 'probability_csv':
            spec = entry['probability_axis']
            required_columns = spec['columns'] if spec['mode'] == 'columns' else spec.get('group_columns', []) + [spec['column']]
            if any(len(cells) <= max(required_columns) for cells in rows[spec.get('skip_rows', 0):]):
                raise GeneratorError('invalid_probability', path, 'Incomplete probability-axis row')
            if spec['mode'] == 'columns':
                for cells in rows[spec.get('skip_rows', 0):]:
                    _probabilities([cells[c] for c in spec['columns']], path, spec.get('tolerance', 1e-6))
            elif spec['mode'] == 'grouped_rows':
                groups = {}
                for cells in rows[spec.get('skip_rows', 0):]:
                    key = tuple(cells[c] for c in spec.get('group_columns', []))
                    groups.setdefault(key, []).append(cells[spec['column']])
                for values in groups.values():
                    _probabilities(values, path, spec.get('tolerance', 1e-6))
        record.update(original_values=rows, numerical_values=numerical,
                      first_source_row=1, probability_axis=entry.get('probability_axis'))
        if 'column_quantities' in entry:
            quantities = entry['column_quantities']
            normalized = []
            for row in numerical:
                normalized.append([None if value is None else value*quantities.get(str(index), quantities.get('*', {})).get('multiplier', 1)
                                   for index, value in enumerate(row)])
            record.update(normalized_values=normalized, column_quantities=quantities)
    elif format == 'json':
        record['value'] = strict_json(content, path)
    elif format == 'epw':
        lines = text.splitlines()
        header = next(csv.reader([lines[0]]))
        rows = list(csv.reader(lines[8:]))
        if len(rows) != 8760 or header[0] != 'LOCATION':
            raise GeneratorError('source_integrity', path, 'Expected a non-leap 8760-hour EPW')
        original = [r[6] for r in rows]
        temperatures = [float(v) for v in original]
        if any(not math.isfinite(v) or v >= 99.9 for v in temperatures):
            raise GeneratorError('source_integrity', path, 'EPW drybulb input is missing/nonfinite')
        record.update(station_header=header, latitude=float(header[6]), longitude=float(header[7]),
                      time_zone_utc_offset=float(header[8]), elevation_m=float(header[9]),
                      drybulb_C=temperatures, original_values=original, first_source_row=9,
                      source_column=7, variant=entry['variant'])
    elif format == 'text':
        record['text'] = text
    elif format == 'receipt':
        provenance['transformation'] = 'Byte-verified provenance receipt only; upstream body is not redistributed in packaged resources'
    else:
        raise GeneratorError('unsupported_resource', path, 'Unsupported member format')
    return record


def extract_sources(lock: dict, cache_root: Path, destination: Path) -> dict:
    records = {}
    for source in lock.get('archives', []) + lock.get('files', []):
        content = _fetch(source, cache_root)
        members = _archive_members(content, source['format'], {e['path'] for e in source['members']}) if 'members' in source else {source['path']: content}
        for entry in source.get('members', [source]):
            safe_path(entry['path'])
            if entry['path'] not in members:
                raise GeneratorError('missing_resource', entry['path'], 'Locked archive member is absent')
            raw = members[entry['path']]
            _verify(raw, entry)
            pair = (entry['kind'], entry['key'])
            if pair in records:
                raise GeneratorError('source_integrity', entry['path'], 'Duplicate resource key')
            records[pair] = compile_member(raw, entry, source)
    for entry in lock.get('required_resources', []):
        if (entry['kind'], entry['key']) not in records:
            raise GeneratorError('missing_resource', f"{entry['kind']}/{entry['key']}", 'Required evidence is absent')
    # Resolve the selected table dependency graph without importing the sampler.
    graph = {key: record['dependencies'] for (kind, key), record in records.items()
             if kind == 'commercial' and record['format'] == 'conditional_tsv'}
    visiting, resolved = set(), set(lock.get('external_selectors', []))
    def visit(key):
        if key in resolved:
            return
        if key in visiting:
            raise GeneratorError('dependency_cycle', key, 'Unsupported distribution cycle')
        if key not in graph:
            raise GeneratorError('missing_resource', key, 'Unbound conditional dependency')
        visiting.add(key)
        for dependency in graph[key]:
            visit(dependency)
        visiting.remove(key)
        resolved.add(key)
    for key in graph:
        visit(key)
    return write_resources(destination, records, {'scope': 'source_evidence',
                           'dependency_inventory': lock.get('required_resources', []), 'blocked_families': lock.get('blocked_families', [])})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, default=ROOT/'sources/schedule-generator-lock.json')
    parser.add_argument('--cache-root', type=Path, default=ROOT/'data/raw')
    parser.add_argument('--destination', type=Path, default=ROOT/'build/generator-source-resources')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    lock = strict_json(args.lock.read_bytes(), str(args.lock))
    if args.verify_only:
        for source in lock.get('archives', []) + lock.get('files', []):
            raw = _fetch(source, args.cache_root, True)
            members = _archive_members(raw, source['format'], {e['path'] for e in source['members']}) if 'members' in source else {source['path']: raw}
            for entry in source.get('members', [source]):
                if entry['path'] not in members:
                    raise GeneratorError('missing_resource', entry['path'], 'Locked member absent')
                _verify(members[entry['path']], entry)
        print('Verified locked source and member bytes')
    else:
        manifest = extract_sources(lock, args.cache_root, args.destination)
        print(f"Compiled {len(manifest['resources'])} resources: {manifest['resource_set_id']}")


if __name__ == '__main__':
    main()
