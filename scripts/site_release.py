"""The release a site build reads (ADR 0043) and the records it publishes.

The newest folder under data/atlas-releases is read unless a release is named. The
release is resolved and exported through scripts.atlas_exports.Release, never parsed
on its own; this module only indexes the resolved files for the pages: folders,
programs, construction sets, schedules, library tables, folder tables and evidence.
"""
import json
import re

from scripts import atlas_exports
from scripts.common import ROOT
from scripts.residential_storage import read_annual

RELEASES = ROOT/'data/atlas-releases'
H6 = re.compile(r'\.[0-9a-f]{6}$')
FOLDER_TABLES = ('services', 'systems', 'components', 'water')
FAMILIES = {'commercial': 'Non residential', 'residential': 'Residential'}


def number(name):
    return tuple(int(part) for part in name.removeprefix('v').split('.'))


def releases():
    """Release numbers under data/atlas-releases, oldest first."""
    names = [p.name for p in RELEASES.iterdir() if p.is_dir() and re.fullmatch(r'v\d+\.\d+\.\d+', p.name)]
    return [name[1:] for name in sorted(names, key=number)]


def newest():
    return releases()[-1]


def folder_of(path):
    """`<family>/<template>/<building type>/` of a record path, or None outside a building folder."""
    parts = path.split('/')
    if parts[0] not in FAMILIES or len(parts) < 4 or parts[2] == 'library':
        return None
    return '/'.join(parts[:3])+'/'


def page_slug(record_id, folder):
    """A record ID without its folder prefix and content hash, as URL segments."""
    prefix = '.'.join(folder.split('/')[1:3])+'.'
    rest = H6.sub('', record_id)
    rest = rest[len(prefix):] if rest.startswith(prefix) else rest
    return '/'.join(segment for segment in rest.split('.') if segment)


class Folder:
    def __init__(self, path):
        self.path = path
        self.family, self.template, self.building_type = path.strip('/').split('/')
        self.programs, self.sets = [], []
        self.tables = {}
        self.schedule_table = None
        self.generation = None  # the folder's generation.json (ADR 0051), or None where the release has none


def space_type(record):
    """The space type of a program named `<space type>_<building type>` (every commercial program), else None (ADR 0052)."""
    name, building_type = record.get('name') or '', record.get('building_type') or ''
    suffix = '_'+building_type
    return name[:-len(suffix)] if building_type and len(name) > len(suffix) and name.endswith(suffix) else None


class SiteRelease:
    """One resolved release, indexed for the site."""

    def __init__(self, release=None):
        self.number = release or newest()
        self.exports = atlas_exports.Release(release=self.number)
        self.files = self.exports.files
        self.manifest = json.loads((RELEASES/f'v{self.number}/manifest.json').read_bytes())
        self.glossary = json.loads(self.files['evidence/glossary.json'])
        self.folders, self.programs, self.sets, self.library = {}, {}, {}, {}
        self.schedules, self._annual, self._evidence = {}, {}, None
        for path in sorted(self.files):
            folder = folder_of(path)
            if path.split('/')[2:3] == ['library'] and path.endswith('.json'):
                table = path.rsplit('/', 1)[1][:-5]
                for rid, row in json.loads(self.files[path]).items():
                    self.library[rid] = (table, path.rsplit('/library/', 1)[0]+'/', row)
            if folder is None:
                continue
            entry = self.folders.setdefault(folder, Folder(folder))
            rest = path[len(folder):]
            if rest.startswith('programs/'):
                record = json.loads(self.files[path])
                mode = rest.split('/')[1] if rest.count('/') > 1 else 'dwelling'
                self.programs[record['id']] = (folder, mode, record)
                entry.programs.append(record['id'])
            elif rest.startswith('constructions/'):
                record = json.loads(self.files[path])
                self.sets[record['id']] = (folder, record)
                entry.sets.append(record['id'])
            elif rest == 'schedules.json':
                table = json.loads(self.files[path])
                entry.schedule_table = table
                for sid in table['schedules']:
                    self.schedules[sid] = folder
            elif rest == 'generation.json':
                entry.generation = json.loads(self.files[path])
            elif rest.startswith('schedules/'):
                for sid in json.loads(self.files[path])['schedules']:
                    self.schedules[sid] = folder
            elif rest[:-5] in FOLDER_TABLES and rest.endswith('.json'):
                entry.tables[rest[:-5]] = json.loads(self.files[path])

    def schedule(self, schedule_id):
        """A schedule as stored: rules with their day profiles, or an annual series."""
        folder = self.folders[self.schedules[schedule_id]]
        if folder.schedule_table and schedule_id in folder.schedule_table['schedules']:
            row = folder.schedule_table['schedules'][schedule_id]
            days = folder.schedule_table['days']
            return {**row, 'id': schedule_id, 'days': {r['day']: days[r['day']] for r in row.get('rules', []) if 'day' in r}}
        if folder.path not in self._annual:
            self._annual[folder.path] = read_annual(self.files, folder.path)
        return {**self._annual[folder.path][schedule_id], 'id': schedule_id}

    @property
    def evidence(self):
        """{evidence ID: stored row} of every evidence file."""
        if self._evidence is None:
            self._evidence = {}
            for path in sorted(self.files):
                if path.startswith('evidence/') and path != 'evidence/glossary.json':
                    self._evidence.update(json.loads(self.files[path]))
        return self._evidence

    def evidence_row(self, evidence_id):
        """An evidence row with its glossary texts written out."""
        return atlas_exports.decode(evidence_id, self.evidence[evidence_id], self.glossary)

    def program(self, program_id, version):
        return self.exports.program(program_id, version)

    def construction(self, set_id, key, representation):
        return self.exports.construction(set_id, key, representation)

    def counts(self):
        return {'programs': len(self.programs), 'construction_sets': len(self.sets), 'folders': len(self.folders),
                'contexts': sum(len(record.get('contexts', {})) for _, record in self.sets.values())}
