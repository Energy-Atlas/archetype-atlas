"""Keep the schema revision register (docs/schema-versioning.md, ADR 0056).

python -m scripts.schema_revisions --check                        # every schema matches its last revision
python -m scripts.schema_revisions --write --change "<what>"      # record the schemas changed since, bumping each

Every JSON Schema the repository publishes (`schemas/*.json`, `atlas_schedules/schemas/*.json`) carries a
revision marker, `"$comment": "revision <n> (<date>). ..."`, and `schemas/revisions.json` lists each
revision with its date, SHA-256, change class and change, and the commit for those before the register.
A schema file whose bytes differ from its last recorded revision fails `--check` (and
tests/test_release_schemas.py): every edit, however small, is a new revision with a stated class.
`--write` gives each changed or new schema its next revision: it rewrites the marker (inserted after
`$id`, or after `$schema` when there is none), then records the new bytes. Schemas another project owns
(`EXTERNAL`) are recorded by hash but carry their owner's marker.
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess

from scripts.common import ROOT

REGISTER = ROOT/'schemas/revisions.json'
FOLDERS = ('schemas', 'atlas_schedules/schemas')
EXTERNAL = {'schemas/lod-recommendations-v1.schema.json': 'BEMGen-docs (ADR 0050); its owner versions it'}
CLASSES = ('created', 'editorial', 'patch', 'minor', 'major')
MARKER = re.compile(r'"\$comment": "revision (\d+) \((\d{4}-\d{2}-\d{2})\)\. [^"]*"')
NOTE = 'Versioning: docs/schema-versioning.md; revisions and hashes: schemas/revisions.json.'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def schema_files():
    return sorted(p.relative_to(ROOT).as_posix() for folder in FOLDERS for p in (ROOT/folder).glob('*.schema.json'))


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout


def history(path):
    """[(commit, date, subject, sha256)] of every committed version of the file at this exact path, oldest first."""
    rows = git('log', '--reverse', '--format=%H%x09%ad%x09%s', '--date=short', '--', path).decode('utf-8').splitlines()
    out = []
    for row in rows:
        commit, date, subject = row.split('\t', 2)
        try:
            blob = git('show', f'{commit}:{path}')
        except subprocess.CalledProcessError:
            continue   # the commit deleted the file
        out.append((commit[:8], date, subject, sha(blob)))
    return out


def marker(revision, date):
    return f'"$comment": "revision {revision} ({date}). {NOTE}"'


def with_marker(text, revision, date):
    """The schema text with its revision marker set, inserted after `$id` (or `$schema`) when it has none."""
    if MARKER.search(text):
        return MARKER.sub(marker(revision, date), text, count=1)
    indent = re.match(r'\{[ \t]*\n([ \t]*)"', text).group(1)   # the top-level keys' indentation
    for key in ('"$id"', '"$schema"'):
        match = re.search(r'^' + re.escape(indent + key) + r'[^\n]*,[ \t]*\n', text, re.M)
        if match:
            return text[:match.end()] + f'{indent}{marker(revision, date)},\n' + text[match.end():]
    raise ValueError('No top-level $id or $schema line to put the revision marker after')


def load():
    return json.loads(REGISTER.read_text(encoding='utf-8')) if REGISTER.is_file() else {'schemas': {}}


def problems(register=None):
    """[message] for every schema that differs from its last recorded revision or lacks its marker."""
    register = register or load()
    found = []
    listed = register['schemas']
    for path in schema_files():
        entry = listed.get(path)
        data = (ROOT/path).read_bytes()
        if entry is None:
            found.append(f'{path}: not in {REGISTER.name}')
            continue
        last = entry['revisions'][-1]
        if sha(data) != last['sha256']:
            found.append(f'{path}: changed since revision {last["revision"]}; record it with --write --change')
        if path in EXTERNAL:
            continue
        match = MARKER.search(data.decode('utf-8'))
        if not match or int(match[1]) != last['revision']:
            found.append(f'{path}: marker says revision {match[1] if match else None}, register {last["revision"]}')
    found += [f'{p}: listed but missing' for p in sorted(set(listed) - set(schema_files()))]
    return found


def write(change, change_class, date):
    """Record every changed or new schema as its next revision; the first record of an existing schema also
    lists its committed history."""
    register = load()
    for path in schema_files():
        entry = register['schemas'].get(path)
        data = (ROOT/path).read_bytes()
        if entry is not None and sha(data) == entry['revisions'][-1]['sha256']:
            continue
        if entry is None:
            past = history(path)
            entry = {'revisions': [{'revision': n, 'date': d, 'commit': c, 'class': 'created' if n == 1 else None,
                                    'change': s, 'sha256': h} for n, (c, d, s, h) in enumerate(past, 1)]}
            if past and past[-1][3] == sha(data) and path in EXTERNAL:
                register['schemas'][path] = {**entry, 'external': EXTERNAL[path]}
                continue
        revision = len(entry['revisions']) + 1
        if path in EXTERNAL:
            entry['external'] = EXTERNAL[path]
        else:
            text = with_marker(data.decode('utf-8'), revision, date)
            (ROOT/path).write_bytes(text.encode('utf-8'))
            data = text.encode('utf-8')
        cls = 'created' if revision == 1 else change_class
        entry['revisions'].append({'revision': revision, 'date': date, 'commit': None, 'class': cls, 'change': change,
                                   'sha256': sha(data)})
        schema = json.loads(data)
        entry['id'] = schema.get('$id')
        register['schemas'][path] = entry
    register['schemas'] = dict(sorted(register['schemas'].items()))
    register['policy'] = 'docs/schema-versioning.md'
    register['description'] = ('Every revision of every published JSON Schema: revision number, date, commit (null for the '
                               'commit that recorded it), change class (created, editorial, patch, minor, major; null where '
                               'the history predates the policy), change and SHA-256 of the file.')
    REGISTER.write_text(json.dumps(register, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--write', action='store_true')
    parser.add_argument('--change', help='what changed (with --write)')
    parser.add_argument('--class', dest='change_class', choices=CLASSES[1:], default='editorial')
    parser.add_argument('--date', default=datetime.date.today().isoformat())
    args = parser.parse_args()
    if args.write:
        if not args.change:
            parser.error('--write needs --change')
        write(args.change, args.change_class, args.date)
    found = problems()
    if found:
        raise SystemExit('\n'.join(found))
    print(f'{len(schema_files())} schemas match their last recorded revision')


if __name__ == '__main__':
    main()
