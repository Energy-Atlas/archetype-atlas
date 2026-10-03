"""Freeze validated canonical tables, contracts and licenses with SHA-256 hashes."""
import argparse
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from scripts.common import ROOT, TABLES, VERSION, dump_json, load_atlas, load_json, table_names
from scripts.validate import validate_atlas


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze_release(processed, target):
    processed, target = Path(processed), Path(target)
    if target.exists():
        raise FileExistsError(f'Release already exists: {target.name}')
    data = load_atlas(processed)
    errors = validate_atlas(data)
    if errors:
        raise ValueError('Cannot release invalid atlas: ' + '; '.join(errors[:5]))
    covered = {r['building_type'] for r in data['programs']}
    if not {'MediumOffice', 'RetailStandalone', 'MidriseApartment'} <= covered:
        raise ValueError('Release requires commercial and multifamily coverage')
    from scripts.coverage import coverage_report
    coverage = coverage_report(data)
    if coverage['errors']:
        raise ValueError('Cannot release incomplete typology coverage: ' + '; '.join(coverage['errors']))
    # Structural validity alone cannot establish scientific source accuracy or
    # complete selected coverage. Both are required before creating a snapshot.
    from scripts.compare import compare_sources
    from scripts.reproduce import check_rebuild
    comparison = compare_sources(data)
    if comparison['errors']:
        raise ValueError('Cannot release source drift: ' + '; '.join(comparison['errors'][:5]))
    mismatches = check_rebuild(processed)
    if mismatches:
        raise ValueError('Cannot release non-reproducible/incomplete tables: ' + ', '.join(mismatches))
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as scratch:
        stage = Path(scratch)/'snapshot'
        stage.mkdir()
        for name in ['metadata.json'] + [t+'.json' for t in TABLES]:
            shutil.copyfile(processed/name, stage/name)
        for path in ['schemas/atlas.schema.json', 'sources/lock.json', 'sources/selection.json', 'LICENSE', 'README.md']:
            dst = stage/path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/path, dst)
        shutil.copytree(ROOT/'sources/licenses', stage/'sources/licenses')
        dump_json(stage/'docs/validation/coverage.json', coverage)
        for path in ['docs/schema.md', 'docs/coverage.md', 'docs/source_inventory.md',
                     'docs/pilot-validation.md', 'docs/reproducibility.md', 'docs/review.md',
                     'sources/inventory.json', 'sources/parameter_matrix.csv']:
            if (ROOT/path).is_file():
                dst = stage/path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/path, dst)
        for path in [f'docs/review-v{VERSION}.md', f'docs/validation/verification-v{VERSION}.json',
                     'docs/validation/source-comparison.json',
                     'docs/adr/0002-typology-coverage-and-residential-configurations.md']:
            if (ROOT/path).is_file():
                dst = stage/path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/path, dst)
        notes = ROOT/f'docs/release-notes/v{VERSION}.md'
        if notes.exists():
            shutil.copyfile(notes, stage/'RELEASE_NOTES.md')
        files = {p.relative_to(stage).as_posix(): {'sha256': sha256(p), 'size_bytes': p.stat().st_size}
                 for p in sorted(stage.rglob('*')) if p.is_file()}
        manifest = {'release_version': VERSION, 'schema_version': data['schema_version'],
                    'release_date': '2026-10-02', 'files': files,
                    'counts': {t: len(data[t]) for t in TABLES},
                    'agent': 'Codex / OpenAI GPT-6; exact runtime identifier unavailable',
                    'generator_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                    'source_lock_sha256': sha256(ROOT/'sources/lock.json')}
        dump_json(stage/'manifest.json', manifest)
        stage.rename(target)
    return target


def verify_release(target):
    target = Path(target)
    manifest = load_json(target/'manifest.json')
    errors = []
    for name, entry in manifest['files'].items():
        path = (target/name).resolve()
        if not path.is_relative_to(target.resolve()):
            errors.append('Manifest path escapes release')
            continue
        if not path.is_file() or path.stat().st_size != entry['size_bytes'] or sha256(path) != entry['sha256']:
            errors.append(f'Release integrity failure: {name}')
    actual = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
    if actual != set(manifest['files']) | {'manifest.json'}:
        errors.append('Release file inventory mismatch')
    if not errors:
        data = load_atlas(target)
        if manifest.get('counts') != {t: len(data[t]) for t in table_names(data['schema_version'])}:
            errors.append('Release manifest record counts mismatch')
        if manifest.get('schema_version') != data['schema_version']:
            errors.append('Release manifest schema version mismatch')
        if manifest.get('source_lock_sha256') != sha256(target/'sources/lock.json'):
            errors.append('Release manifest source lock hash mismatch')
        errors.extend(validate_atlas(data, target))
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify', action='store_true')
    p.add_argument('--processed', type=Path, default=ROOT/'data/processed')
    p.add_argument('--target', type=Path, default=ROOT/f'data/releases/v{VERSION}')
    args = p.parse_args()
    if args.verify:
        errors = verify_release(args.target)
        if errors:
            raise SystemExit('\n'.join(errors))
        print('Release file inventory, checksums and frozen schema validation passed')
    else:
        freeze_release(args.processed, args.target)
        print(f'Created immutable release {args.target.name}')


if __name__ == '__main__':
    main()
