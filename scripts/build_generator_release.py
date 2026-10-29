"""Build the generator release and the data archive, each with SHA256SUMS (ADR 0049 section 5, stage P4).

python -m scripts.build_generator_release                 # build into build/release/
python -m scripts.build_generator_release --check-install # also install the wheel in a fresh venv and smoke it

- `generator-v<version>/`: the wheel and sdist of `atlas_schedules`, built by the pinned flit_core of
  requirements-build.txt (its wheel checked against the pinned hash and imported from the file), with
  SOURCE_DATE_EPOCH at the commit time so a rebuild of a commit gives the same bytes;
- `v<release>/`: `atlas-release-<release>.zip`, holding the release folder and its base folders as they
  sit in data/atlas-releases (`v2.0.0/`, `v2.1.0/`), entries sorted with fixed times.
The install check makes a venv, installs the wheel and the pinned dependencies of requirements.txt,
extracts the data archive to a short folder (past MAX_PATH on Windows), and runs the catalogue smoke
with `ATLAS_RELEASES` set to it, outside the source tree.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from scripts.common import ROOT

OUT = ROOT/'build/release'
FLIT = ROOT/'build/pip-flit/flit_core-3.12.0-py3-none-any.whl'
RELEASES = ROOT/'data/atlas-releases'
EPOCH_ZIP = (1980, 1, 1, 0, 0, 0)
CHECK_DATA = Path(os.environ.get('ATLAS_CHECK_ROOT', Path.home()/'art'/'atlas-check'))


def version():
    text = (ROOT/'atlas_schedules/__init__.py').read_text(encoding='utf-8')
    return re.search(r'__version__ = "([^"]+)"', text)[1]


def commit_time():
    return subprocess.run(['git', '-c', 'core.longpaths=true', 'log', '-1', '--format=%ct'], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def pinned_flit():
    pin = re.search(r'--hash=sha256:([0-9a-f]{64})', (ROOT/'requirements-build.txt').read_text(encoding='utf-8'))[1]
    if not FLIT.is_file():
        raise SystemExit(f'Download it first: python -m pip download flit_core==3.12.0 --no-deps --only-binary=:all: '
                         f'-d {FLIT.parent}')
    if hashlib.sha256(FLIT.read_bytes()).hexdigest() != pin:
        raise SystemExit(f'{FLIT.name} differs from the hash pinned in requirements-build.txt')
    return FLIT


def sums(folder):
    lines = [f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
             for p in sorted(folder.iterdir()) if p.is_file() and p.name != 'SHA256SUMS']
    (folder/'SHA256SUMS').write_text(''.join(lines), encoding='utf-8', newline='\n')
    return lines


def generator(number):
    """Wheel and sdist through flit_core, in a child interpreter with the pinned backend on its path."""
    folder = OUT/f'generator-v{number}'
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    code = ('import sys; from flit_core import buildapi; '
            'print(buildapi.build_wheel(sys.argv[1])); print(buildapi.build_sdist(sys.argv[1]))')
    env = {**os.environ, 'SOURCE_DATE_EPOCH': commit_time(), 'PYTHONPATH': str(pinned_flit())}
    subprocess.run([sys.executable, '-c', code, str(folder)], cwd=ROOT, check=True, env=env)
    return folder, sums(folder)


def long(path):
    absolute = os.path.abspath(path)
    return '\\\\?\\' + absolute if os.name == 'nt' and not absolute.startswith('\\\\?\\') else absolute


def release_folders(release):
    """The release folder and its bases, newest first."""
    out = [release]
    while True:
        base = json.loads((RELEASES/f'v{out[-1]}/manifest.json').read_bytes()).get('base_release')
        if not base:
            return out
        out.append(base['release'])


def data(release):
    folder = OUT/f'v{release}'
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    archive = folder/f'atlas-release-{release}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for number in sorted(release_folders(release)):
            root = RELEASES/f'v{number}'
            for path in sorted(p for p in root.rglob('*') if p.is_file()):
                name = f'v{number}/'+path.relative_to(root).as_posix()
                info = zipfile.ZipInfo(name, EPOCH_ZIP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(long(path), 'rb') as handle:
                    out.writestr(info, handle.read(), compresslevel=9)
    return folder, sums(folder)


def check_install(wheel, archive):
    venv = OUT/'venv-check'
    shutil.rmtree(venv, ignore_errors=True)
    subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True)
    python = venv/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    subprocess.run([str(python), '-m', 'pip', 'install', '--quiet', '-r', str(ROOT/'requirements.txt')], check=True)
    subprocess.run([str(python), '-m', 'pip', 'install', '--quiet', '--no-deps', str(wheel)], check=True)
    shutil.rmtree(long(CHECK_DATA), ignore_errors=True)
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            target = Path(long(CHECK_DATA/info.filename))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read(info))
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH',)} | {'ATLAS_RELEASES': str(CHECK_DATA)}
    probe = ('import atlas_schedules, json; from atlas_schedules.release import current; r = current(); '
             'print(json.dumps({"package": atlas_schedules.__file__, "version": atlas_schedules.__version__, '
             '"release": r.version, "folder": str(r.folder)}))')
    seen = json.loads(subprocess.run([str(python), '-I', '-c', probe], env=env, cwd=CHECK_DATA, check=True,
                                     capture_output=True, text=True).stdout)
    if not Path(seen['package']).resolve().is_relative_to(venv.resolve()) or not seen['folder'].startswith(str(CHECK_DATA)):
        raise SystemExit(f'The install check read the source tree: {seen}')
    print('installed:', seen)
    smoke = ('import runpy, sys; sys.argv = ["smoke_catalogue"]; '
             f'runpy.run_path({str(ROOT/"scripts/smoke_catalogue.py")!r}, run_name="__main__")')
    subprocess.run([str(python), '-I', '-c', smoke], env=env, cwd=CHECK_DATA, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check-install', action='store_true')
    args = parser.parse_args()
    number = version()
    release = json.loads((RELEASES/'v2.1.0/manifest.json').read_bytes())['release']
    built, lines = generator(number)
    print(f'{built.relative_to(ROOT).as_posix()}:', *(line.rstrip() for line in lines), sep='\n  ')
    archived, lines = data(release)
    print(f'{archived.relative_to(ROOT).as_posix()}:', *(line.rstrip() for line in lines), sep='\n  ')
    if args.check_install:
        check_install(next(built.glob('*.whl')), next(archived.glob('*.zip')))


if __name__ == '__main__':
    main()
