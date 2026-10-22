"""Canonical files, readable IDs and merging for ADR 0036 release folders.

Suite files (one program or construction set) are indented JSON with sorted keys.
Tables hold one record per line, optionally inside named sections. Every file is
UTF-8 with LF line endings and a trailing newline.
"""
import hashlib
import json
import re

SECTIONED = ('glossary.json', 'schedules.json', 'water.json')  # tables grouped into named sections


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '-', text).lower()).strip('-')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def h6(value):
    """The first six hex digits of the SHA-256 of a value's canonical JSON."""
    return hashlib.sha256(canonical(value).encode()).hexdigest()[:6]


def suite_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n').encode()


def table_bytes(records, sections=False):
    """One record per line, optionally grouped into named sections."""
    def rows(table):
        return [json.dumps(k, ensure_ascii=False)+':'+canonical(v)+(',' if i < len(table)-1 else '')
                for i, (k, v) in enumerate(sorted(table.items()))]
    if not sections:
        return ('\n'.join(['{', *rows(records), '}'])+'\n').encode()
    lines = ['{']
    for i, (name, table) in enumerate(sorted(records.items())):
        lines += [json.dumps(name)+': {', *rows(table), '},' if i < len(records)-1 else '}']
    return ('\n'.join(lines+['}'])+'\n').encode()


def translate(value, ids):
    """Replace every string (value or key) that is an old ID with its new reference."""
    if isinstance(value, dict):
        return {ids.get(k, k) if isinstance(ids.get(k, k), str) else k: translate(v, ids) for k, v in value.items()}
    if isinstance(value, list):
        return [translate(v, ids) for v in value]
    return ids.get(value, value) if isinstance(value, str) else value


def merge(*builds):
    """Combine folder builds: identical files once, tables unioned record by record."""
    out = {}
    for files in builds:
        for path, data in files.items():
            if path not in out or out[path] == data:
                out[path] = data
                continue
            if '/programs/' in path or '/constructions/' in path:
                raise ValueError('Suite file written twice with different content: '+path)
            sections = path.endswith(SECTIONED)
            old, new = json.loads(out[path]), json.loads(data)
            tables = [(old, new)] if not sections else [(old.setdefault(k, {}), v) for k, v in new.items()]
            for target, source in tables:
                for key, record in source.items():
                    if target.setdefault(key, record) != record:
                        raise ValueError(f'Conflicting record {key} in {path}')
            out[path] = table_bytes(old, sections=sections)
    return out
