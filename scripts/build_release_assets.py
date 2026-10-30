"""Build the release assets with their checksums: the generator wheel and sdist, and the data archive (ADR 0051 section 6).

python -m scripts.build_release_assets --wheel [--check-install]   # build/release/atlas-schedules-v<version>/: wheel, sdist, SHA256SUMS.txt
python -m scripts.build_release_assets --data                      # build/release/v<release>/: atlas-release-<release>.zip, SHA256SUMS.txt

- The wheel and sdist come from `python -m build` (setuptools, pinned in requirements-dev.txt), each
  built from the tree, after `scripts.build_generator_view` wrote the generator view the wheel bundles,
  with SOURCE_DATE_EPOCH at the commit time and the sdist's tar normalised (sorted members, that time,
  no owner), so a rebuild of a commit gives the same bytes.
- The data archive holds the release folder and its base folders as they sit in data/atlas-releases
  (`v2.0.0/`, `v2.1.0/`, `v2.2.0/`), entries sorted with fixed times, after `scripts.atlas_delta --verify`.
- `SHA256SUMS.txt` lists the assets of its folder in `sha256sum -c` form.
`--check-install` makes a venv, installs the wheel alone (its dependencies from the index), and runs the
quick-start request and the sampled catalogue smoke from outside the source tree, first against the
bundled view and then against the extracted data archive through ATLAS_RELEASES.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

from scripts import atlas_delta
from scripts.common import ROOT

OUT = ROOT/'build/release'
EPOCH_ZIP = (1980, 1, 1, 0, 0, 0)
SUMS = 'SHA256SUMS.txt'
QUICK_START = ROOT/'docs/examples/schedule-generator/office-and-retail.json'


def version():
    import atlas_schedules
    return atlas_schedules.__version__


def commit_time():
    return subprocess.run(['git', '-c', 'core.longpaths=true', 'log', '-1', '--format=%ct'], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def sums(folder):
    lines = [f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
             for p in sorted(folder.iterdir()) if p.is_file() and p.name != SUMS]
    (folder/SUMS).write_text(''.join(lines), encoding='utf-8', newline='\n')
    return lines


def fresh(folder):
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    return folder


def wheel():
    """The wheel and sdist of this tree, reproducibly, with the generator view rebuilt first."""
    folder = fresh(OUT/f'atlas-schedules-v{version()}')
    subprocess.run([sys.executable, '-m', 'scripts.build_generator_view'], cwd=ROOT, check=True)
    for stale in (ROOT/'atlas_schedules.egg-info', ROOT/'build/lib', ROOT/'build/bdist.win-amd64'):
        shutil.rmtree(stale, ignore_errors=True)
    env = {**os.environ, 'SOURCE_DATE_EPOCH': commit_time(), 'PYTHONHASHSEED': '0'}
    # Each artefact from the tree itself: a wheel built from the unpacked sdist (build's default) takes the
    # unpacking's file order and times, which SOURCE_DATE_EPOCH does not clamp, and is not reproducible.
    for kind in ('--wheel', '--sdist'):
        shutil.rmtree(ROOT/'atlas_schedules.egg-info', ignore_errors=True)
        subprocess.run([sys.executable, '-m', 'build', kind, '--outdir', str(folder)], cwd=ROOT, check=True, env=env)
    normalise_sdist(next(folder.glob('*.tar.gz')), int(env['SOURCE_DATE_EPOCH']))
    return folder, sums(folder)


def normalise_sdist(path, epoch):
    """Rewrite the sdist with sorted members, the commit time as every mtime, no owner and fixed modes; setuptools
    keeps the checkout's file times in the tar, so two builds of one commit would otherwise differ."""
    members = []
    with tarfile.open(path, 'r:gz') as source:
        for info in source.getmembers():
            data = source.extractfile(info).read() if info.isfile() else None
            info.mtime, info.uid, info.gid, info.uname, info.gname = epoch, 0, 0, '', ''
            info.mode = 0o755 if info.isdir() else 0o644
            info.pax_headers = {}   # setuptools wrote the file time here too
            members.append((info, data))
    members.sort(key=lambda item: item[0].name)
    with open(path, 'wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as compressed,             tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as out:
        for info, data in members:
            out.addfile(info, io.BytesIO(data) if data is not None else None)


def long(path):
    absolute = os.path.abspath(path)
    return '\\\\?\\' + absolute if os.name == 'nt' and not absolute.startswith('\\\\?\\') else absolute


def release_folders(release):
    """The release and its bases, newest first."""
    out = [release]
    while True:
        base = json.loads((atlas_delta.folder_of(out[-1])/'manifest.json').read_bytes()).get('base_release')
        if not base:
            return out
        out.append(base['release'])


def data(release=atlas_delta.RELEASE):
    """`atlas-release-<release>.zip`: the release folder and its bases as they sit in the tree, verified first."""
    atlas_delta.verify(release)
    folder = fresh(OUT/f'v{release}')
    archive = folder/f'atlas-release-{release}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for number in sorted(release_folders(release), key=lambda n: tuple(int(x) for x in n.split('.'))):
            root = atlas_delta.folder_of(number)
            for path in sorted(p for p in root.rglob('*') if p.is_file()):
                info = zipfile.ZipInfo(f'v{number}/'+path.relative_to(root).as_posix(), EPOCH_ZIP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(long(path), 'rb') as handle:
                    out.writestr(info, handle.read(), compresslevel=9)
    return folder, sums(folder)


def check_install(built, archive=None):
    """Install the wheel in a fresh venv and generate from outside the tree: bundled view, then the archive."""
    wheel_path = next(built.glob('*.whl'))
    venv = fresh(OUT/'venv-check')
    subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True)
    python = venv/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    subprocess.run([str(python), '-m', 'pip', 'install', '--quiet', str(wheel_path)], check=True)
    work = Path(tempfile.mkdtemp(prefix='atlas-schedules-check-'))
    shutil.copy(QUICK_START, work/QUICK_START.name)
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'ATLAS_RELEASES')}
    probe = ('import atlas_schedules, json; from atlas_schedules.release import current; r = current(); '
             'print(json.dumps({"package": atlas_schedules.__file__, "version": atlas_schedules.__version__, '
             '"release": r.version, "store": r.store.describe()}))')

    def run(label, extra_env):
        seen = json.loads(subprocess.run([str(python), '-I', '-c', probe], env={**env, **extra_env}, cwd=work, check=True,
                                         capture_output=True, text=True).stdout)
        tree = str((ROOT/'data/atlas-releases').resolve())
        if not Path(seen['package']).resolve().is_relative_to(venv.resolve()) or seen['store'].startswith(tree):
            raise SystemExit(f'The install check read the source tree ({label}): {seen}')
        print(f'{label}:', seen)
        subprocess.run([str(python), '-I', '-m', 'atlas_schedules', QUICK_START.name, '-o', f'bundle-{label}.json'],
                       env={**env, **extra_env}, cwd=work, check=True)
        smoke = f'import runpy, sys; sys.argv = ["smoke_catalogue", "--sample", "1"]; runpy.run_path({str(ROOT/"scripts/smoke_catalogue.py")!r}, run_name="__main__")'
        subprocess.run([str(python), '-I', '-c', smoke], env={**env, **extra_env}, cwd=work, check=True)

    run('bundled-view', {})
    if archive:
        extracted = fresh(work/'releases')
        with zipfile.ZipFile(archive) as source:
            for info in source.infolist():
                target = Path(long(extracted/info.filename))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(info))
        run('data-archive', {'ATLAS_RELEASES': str(extracted)})
        bundles = [(work/f'bundle-{label}.json').read_bytes() for label in ('bundled-view', 'data-archive')]
        if bundles[0] != bundles[1]:
            raise SystemExit('The bundled view and the data archive gave different bundles')
        print('The bundled view and the data archive give the same bundle')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--wheel', action='store_true', help='build the wheel and sdist with SHA256SUMS.txt')
    parser.add_argument('--data', action='store_true', help='build the data archive with SHA256SUMS.txt')
    parser.add_argument('--check-install', action='store_true', help='install the wheel in a fresh venv and generate from outside the tree')
    args = parser.parse_args(argv)
    if not (args.wheel or args.data):
        parser.error('name --wheel, --data or both')
    built = archive = None
    if args.wheel:
        built, lines = wheel()
        print(f'{built.relative_to(ROOT).as_posix()}:', *(line.rstrip() for line in lines), sep='\n  ')
    if args.data:
        folder, lines = data()
        archive = next(folder.glob('*.zip'))
        print(f'{folder.relative_to(ROOT).as_posix()}:', *(line.rstrip() for line in lines), sep='\n  ')
    if args.check_install:
        if built is None:
            parser.error('--check-install needs --wheel')
        check_install(built, archive)


if __name__ == '__main__':
    main()
