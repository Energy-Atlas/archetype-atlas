"""Date the edits of openstudio-standards rows, for the "newer and documented" rule.

python -m scripts.upstream_history --repo <openstudio-standards clone> --kind schedules|space_types
    --keys <json list of keys> [--out build/reconciliation/history-<kind>.json]

Schedule rows are keyed by name; space-type rows by [template, building_type, space_type].
The trace walks every commit, up to the pinned revision, that touched the current data
file or its predecessor (data/standards/OpenStudio_Standards_*.json, 2015-2019), and
records each commit where a key's rows changed, with date and subject. Notes are
ignored, so a change of wording alone does not count. A partial clone
(git clone --filter=blob:none) is enough; blobs are read with git cat-file, which
avoids Windows path-length limits.
"""
import argparse
import json
import subprocess
from pathlib import Path

from scripts.common import ROOT

PINNED = 'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907'
PATHS = {
    'schedules': ['lib/openstudio-standards/standards/ashrae_90_1/data/ashrae_90_1.schedules.json',
                  'data/standards/OpenStudio_Standards_schedules.json',
                  'openstudio-standards/data/standards/OpenStudio_Standards_schedules.json'],
    'space_types': ['data/standards/OpenStudio_Standards_space_types.json',
                    'openstudio-standards/data/standards/OpenStudio_Standards_space_types.json'],
}
TEMPLATE_FOLDERS = {'DOE Ref Pre-1980': 'doe_ref_pre_1980', 'DOE Ref 1980-2004': 'doe_ref_1980_2004',
                    '90.1-2004': 'ashrae_90_1_2004', '90.1-2007': 'ashrae_90_1_2007',
                    '90.1-2010': 'ashrae_90_1_2010', '90.1-2013': 'ashrae_90_1_2013',
                    '90.1-2019': 'ashrae_90_1_2019'}


def git(repo, *args):
    return subprocess.run(['git', '-c', 'core.longpaths=true', '-C', str(repo), *args],
                          capture_output=True, check=True).stdout


def commits(repo, path):
    out = git(repo, 'log', '--format=%H%x09%cs%x09%s', '--reverse', PINNED, '--', path).decode()
    return [line.split('\t', 2) for line in out.splitlines() if line]


def grouped_rows(blob, kind):
    data = json.loads(blob)
    rows = data.get('schedules' if kind == 'schedules' else 'space_types', [])
    result = {}
    for row in rows:
        key = row.get('name') if kind == 'schedules' else [row.get('template'), row.get('building_type'),
                                                            row.get('space_type')]
        result.setdefault(json.dumps(key), []).append({k: v for k, v in row.items() if k != 'notes'})
    return result


def trace(repo, kind, keys):
    paths = list(PATHS[kind])
    if kind == 'space_types':
        templates = {json.loads(k)[0] for k in keys}
        paths = [f'lib/openstudio-standards/standards/ashrae_90_1/{TEMPLATE_FOLDERS[t]}/data/{TEMPLATE_FOLDERS[t]}.spc_typ.json'
                 for t in sorted(templates) if t in TEMPLATE_FOLDERS] + paths
    timeline = sorted((date, sha, subject, path) for path in paths for sha, date, subject in commits(repo, path))
    history = {k: [] for k in keys}
    last = {}
    for date, sha, subject, path in timeline:
        try:
            rows = grouped_rows(git(repo, 'cat-file', 'blob', f'{sha}:{path}'), kind)
        except (subprocess.CalledProcessError, ValueError, AttributeError):
            continue
        for k in keys:
            if k in rows:
                state = json.dumps(rows[k], sort_keys=True)
                if last.get(k) != state:
                    history[k].append({'date': date, 'commit': sha[:10], 'subject': subject[:120], 'rows': rows[k]})
                    last[k] = state
    return history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--kind', choices=sorted(PATHS), required=True)
    parser.add_argument('--keys', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    keys = [json.dumps(k) for k in json.loads(args.keys.read_text())]
    history = trace(args.repo, args.kind, keys)
    out = args.out or ROOT/f'build/reconciliation/history-{args.kind}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(history, indent=1))
    print(f'Traced {len(keys)} keys; {sum(len(v) for v in history.values())} changes recorded')


if __name__ == '__main__':
    main()
