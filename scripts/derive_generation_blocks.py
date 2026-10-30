"""Derive release 2.2.0's generation blocks from the generator 3.0.0 packaged copies (ADR 0051, stage P1/P2).

python -m scripts.derive_generation_blocks            # write the generation.json files and definition-map.json into v2.2.0
python -m scripts.derive_generation_blocks --check    # derive again and repeat the gate without writing

Generator 3.0.0 packaged 1,585 recipes, 186 services, 120 configurations and a schedule table that
repeat release 2.1.0's values (2.0.0's programs; 2.1.0's apartment-unit recipes). This writes what the
release does not already state:
- per program, a `generation` block (method and, per view, the parameters the record cannot give):
  `comstock_hours` (the configuration), `composition` and `fixed` (none), `resstock_unit` (ADR 0047's
  unit characteristics) and `resstock_dwelling` (the dwelling's executed OpenStudio-HPXML inputs);
- per service, the configurations it runs under; per folder, its building configurations, their
  People on the folder's release schedules;
- `definition-map.json`: each packaged definition program ID with its release program and view,
  each definition service ID with its release service.

The gate: every packaged recipe, service and configuration, re-keyed by release ID, equals the one
assembled from the release (atlas_schedules.programmes) as JSON, schedules compared by their rules.
Stated exceptions (ADR 0051 section 3): the 12 hotel corridor compositions no release program holds,
and the 36 90.1 apartment-building fixed recipes, whose legacy form dropped known heat fractions and
kept a zero-density occupancy slot; the release values replace both.

This script reads the packaged copies, which leave the tree with generator 4.0.0 (stage P3); it is
run once, at the commit ADR 0051 names, and `scripts.atlas_delta` carries the files it wrote.
"""
import argparse
from collections import defaultdict
import copy
import json

from atlas_schedules import programmes
from atlas_schedules.release import Release
from scripts.common import ROOT
from scripts.iecc_commercial_values import layered

RELEASES = ROOT/'data/atlas-releases'
BASE = RELEASES/'v2.1.0'
TARGET = RELEASES/'v2.2.0'
DATA = ROOT/'atlas_schedules/data'
SCHEMA = '1.0.0'
METHODS = {'commercial': 'comstock_hours', 'composition': 'composition', 'fixed': 'fixed',
           'apartment_unit': 'resstock_unit', 'residential': 'resstock_dwelling'}
VIEW = {'source': 'source', 'reviewed': 'filled'}
DWELLINGS = 'residential/resstock-sdr'
DECISION = 'docs/adr/0051-generation-parameters-in-the-release.md'


def read(folder):
    return {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in sorted((DATA/folder).glob('*.json'))}


class Packaged:
    """The generator's packaged copies and their release counterparts."""

    def __init__(self, release):
        self.release = release
        self.recipes, self.services, self.configurations = read('recipes'), read('services'), read('configurations')
        self.table = json.loads((DATA/'schedules.json').read_text(encoding='utf-8'))
        # (packaged ID, (release ID, view)) of every recipe with a release program; the department and general
        # corridor mixes of both hotels share one recipe
        self.entries = []
        for path in sorted(release.paths):
            if path.endswith('/generator.json'):
                for rid, views in sorted(release.json(path).items()):
                    for view, recipe in sorted(views.items()):
                        self.entries.append((recipe['program_id'], (rid, VIEW[view])))
        dwellings = {release.json(p)['source_id']: release.json(p)['id']
                     for p in release.paths if p.startswith(DWELLINGS) and '/programs/' in p}
        for pid, recipe in sorted(self.recipes.items()):
            if recipe['kind'] == 'residential':
                self.entries.append((pid, (dwellings[recipe['source']['source_id']], 'source')))
        self.programs = {}   # packaged ID -> (release ID, view); a shared recipe keeps its first release program
        for pid, key in self.entries:
            self.programs.setdefault(pid, key)
        self.orphans = sorted(pid for pid in self.recipes if pid not in self.programs)
        self.folder = {rid: release.program(rid)[0] for _, (rid, _) in self.entries}
        self.services_map = self._services()

    def _services(self):
        pairs = defaultdict(set)
        for pid, (rid, view) in self.entries:
            recipe = self.recipes[pid]
            record = programmes.view_record(self.release.program(rid)[1], view)
            if recipe['kind'] == 'commercial':
                for old, new in zip(recipe['required_services'], programmes.commercial_body(record)['required_services']):
                    pairs[old].add(new)
            if recipe.get('caller_water'):
                pairs[recipe['caller_water']['service_id']].add(programmes.load_of(record, 'hot_water_volume')['service_id'])
        out = {}
        for old, new in pairs.items():
            if len(new) != 1:
                raise ValueError(f'{old} pairs with {sorted(new)}')
            out[old] = next(iter(new))
        # Services no packaged recipe links: the one release service of the configurations' folder with the same
        # volume, schedule rules, target temperature and fractions.
        used = set(out.values())
        for sid, service in sorted(self.services.items()):
            if sid in out:
                continue
            folders = {self.configuration_folder(cid) for cid in service['configurations']}
            if len(folders) != 1:
                raise ValueError(f'{sid}: configurations span {sorted(folders)}')
            folder = folders.pop()
            matches = [rid for rid, s in self.release.services(folder).items()
                       if rid not in used and s['load']['quantity'] == 'hot_water_volume'
                       and isinstance(s['load'].get('target_temperature_degC'), (int, float))
                       and isinstance(s['load']['schedule_id'], str) and self.service_equal(sid, rid, folder)]
            if not matches:
                raise ValueError(f'{sid}: no release service in {folder} matches')
            # Identical services (the strip malls' store water heaters) pair in ID order; any pairing generates
            # the same schedules.
            out[sid] = sorted(matches)[0]
            used.add(matches[0])
        return out

    def configuration_folder(self, cid):
        folders = {self.folder[self.programs[pid][0]] for pid, recipe in self.recipes.items()
                   if pid in self.programs and (recipe.get('commercial') or {}).get('configuration_id') == cid}
        if len(folders) != 1:
            raise ValueError(f'{cid}: used in {sorted(folders)}')
        return folders.pop()

    def service_equal(self, sid, rid, folder):
        generation = {folder: {'services': {rid: {'configurations': sorted(self.services[sid]['configurations'])}}}}
        probe = Release(self.release.store, generation=generation)
        assembled = programmes.assemble_service(probe, rid)
        return self.deref(self.packaged_service(sid, rid), self.table) == self.deref(assembled, probe.schedules(folder))

    def packaged_service(self, sid, rid):
        out = {k: v for k, v in self.services[sid].items() if k != 'source'}
        return {**out, 'service_id': rid}

    @staticmethod
    def deref(value, table):
        """The value with every schedule ID in `table` replaced by its rules, and provenance left out."""
        if isinstance(value, str):
            return {'rules': table[value]['rules']} if value in table else value
        if isinstance(value, dict):
            return {k: Packaged.deref(v, table) for k, v in value.items() if k != 'source'}
        if isinstance(value, list):
            return [Packaged.deref(v, table) for v in value]
        return value

    # ------------------------------------------------------------------ blocks
    def schedule_in_folder(self, old, folder, preferred):
        """The release schedule of `folder` whose rules equal the packaged schedule `old`."""
        rules = self.table[old]['rules']
        table = self.release.schedules(folder)
        if preferred.get(old) and table.get(preferred[old], {}).get('rules') == rules:
            return preferred[old]
        same = sorted(sid for sid, s in table.items() if s['rules'] == rules)
        if not same:
            raise ValueError(f'{old}: no schedule with its rules in {folder}')
        return same[0]

    def generation(self):
        """{folder: generation.json document}, and the definition map."""
        docs = defaultdict(lambda: {'schema_version': SCHEMA, 'programs': {}, 'services': {}, 'configurations': {}})
        preferred = defaultdict(dict)   # folder -> packaged schedule -> release schedule, from recipe slots
        for pid, (rid, view) in self.entries:
            recipe, folder = self.recipes[pid], self.folder[rid]
            kind = recipe['kind']
            block = docs[folder]['programs'].setdefault(rid, {'schema_version': SCHEMA, 'method': METHODS[kind], 'views': {}})
            if block['method'] != METHODS[kind]:
                raise ValueError(f'{rid}: views of methods {block["method"]} and {METHODS[kind]}')
            parameters = {}
            if kind == 'commercial':
                parameters = {'configuration_id': recipe['commercial']['configuration_id']}
                record = programmes.view_record(self.release.program(rid)[1], view)
                for old, new in zip(recipe['slots'], programmes.commercial_body(record)['slots']):
                    if old['schedule'] and new['schedule']:
                        preferred[folder][old['schedule']] = new['schedule']
            elif kind == 'apartment_unit':
                unit = copy.deepcopy(recipe['resstock_unit'])
                water = programmes.load_of(self.release.program(rid)[1], 'hot_water_volume')
                unit['source']['hot_water']['schedule'] = water['schedule_id']
                del unit['source']['release_recipe']
                unit['source']['program'] = self.release.program_paths[rid]
                parameters = {'resstock_unit': unit}
            elif kind == 'residential':
                parameters = {k: recipe[k] for k in programmes.DWELLING_FIELDS}
            block['views'][view] = parameters
        for folder, doc in docs.items():
            doc['programs'] = {rid: {**b, 'views': dict(sorted(b['views'].items()))} for rid, b in sorted(doc['programs'].items())}
        for cid, configuration in sorted(self.configurations.items()):
            folder = self.configuration_folder(cid)
            people = [[self.schedule_in_folder(s, folder, preferred[folder]) if s in self.table else s, n]
                      for s, n in configuration['people']]
            docs[folder]['configurations'][cid] = {'building_type': configuration['building_type'], 'people': people,
                                                   'invert_rule_days': configuration['invert_rule_days']}
        for sid, service in sorted(self.services.items()):
            rid = self.services_map[sid]
            docs[self.release.folder_of(rid)]['services'][rid] = {
                'schema_version': SCHEMA, 'method': 'comstock_hours', 'configurations': sorted(service['configurations'])}
        definition = {
            'schema_version': '1.0.0',
            'decision': DECISION,
            'description': 'Definition program and service IDs the generator took before release 2.2.0 (generator 3.0.0), '
                           'each with its release program and view (values) or release service.',
            'programs': {pid: {'program_id': rid, 'values': view}
                         for pid, (rid, view) in sorted(self.programs.items()) if pid.startswith('program-')},
            'services': {sid: rid for sid, rid in sorted(self.services_map.items()) if sid.startswith('service-')},
            'retired': {pid: 'a hotel corridor composition no release program holds' for pid in self.orphans},
        }
        return {f: {k: v for k, v in d.items() if v} | {'schema_version': SCHEMA} for f, d in sorted(docs.items())}, definition

    # -------------------------------------------------------------------- gate
    def expected(self, pid, rid, view):
        """The packaged recipe re-keyed by release IDs."""
        recipe = copy.deepcopy(self.recipes[pid])
        recipe.update(program_id=rid, values=view)
        recipe['required_services'] = [self.services_map[s] for s in recipe['required_services']]
        if recipe.get('caller_water'):
            recipe['caller_water']['service_id'] = self.services_map[recipe['caller_water']['service_id']]
        if recipe['kind'] == 'composition':
            members = recipe['composition']['members']
            recipe['composition'] = {'composition_id': rid, 'members': [[self.programs[m][0], a] for m, a in members],
                                     'member_values': [self.programs[m][1] for m, _ in members]}
        return recipe

    @staticmethod
    def legacy_fixed(expected, assembled):
        """The 90.1 fixed form against the release values: known heat fractions replace the nulls, and the
        zero-density occupancy slot and control leave. Returns both sides with those differences removed."""
        dropped = [c for c in expected['controls'] if c.get('people', {}).get('density') == 0.0]
        if dropped:
            if [c['slot'] for c in dropped] != ['occupants']:
                raise ValueError(f"{expected['program_id']}: unexpected zero controls")
            expected['slots'] = [s for s in expected['slots'] if s['slot'] != 'occupants']
            expected['controls'] = [c for c in expected['controls'] if c['slot'] != 'occupants']
        for old, new in zip(expected['demands'], assembled['demands']):
            if old['heat_fractions'] is not None:
                raise ValueError(f"{expected['program_id']}: a legacy heat fraction is known")
            old['heat_fractions'] = new['heat_fractions']
        return expected

    def check(self, release):
        """[(what, packaged ID)] that differ; `release` reads the derived blocks."""
        differ, fixed = [], 0
        for pid, (rid, view) in self.entries:
            assembled = programmes.assemble(release, rid, view)
            expected = self.expected(pid, rid, view)
            if expected['kind'] == 'fixed' and pid.startswith('program-'):
                expected = self.legacy_fixed(expected, assembled)
                fixed += 1
            if self.deref(expected, self.table) != self.deref(assembled, release.schedules(self.folder[rid])):
                differ.append(('recipe', pid))
        for sid in self.services:
            rid = self.services_map[sid]
            folder = release.folder_of(rid)
            if self.deref(self.packaged_service(sid, rid), self.table) != \
                    self.deref(programmes.assemble_service(release, rid), release.schedules(folder)):
                differ.append(('service', sid))
        for cid, configuration in self.configurations.items():
            assembled = programmes.assemble_configuration(release, cid)
            folder = release.configurations[cid][0]
            if self.deref(configuration, self.table) != self.deref(assembled, release.schedules(folder)):
                differ.append(('configuration', cid))
        return differ, fixed


def gate(base):
    """Derive the blocks from the packaged copies and prove the equivalence; (packaged, docs, definition map)."""
    packaged = Packaged(base)
    docs, definition = packaged.generation()
    differ, fixed = packaged.check(Release(base.store, generation=docs))
    counts = defaultdict(int)
    for recipe in (packaged.recipes[p] for p, _ in packaged.entries):
        counts[recipe['kind']] += 1
    print(f'{len(packaged.entries)} program views ({dict(counts)}), {len(packaged.services_map)} services, '
          f'{len(packaged.configurations)} configurations assembled from release {base.version}; {fixed} legacy fixed '
          f'forms, {len(packaged.orphans)} recipes without a release program; {len(definition["programs"])} definition '
          f'programs and {len(definition["services"])} definition services mapped')
    if differ:
        raise SystemExit(f'{len(differ)} differ, e.g. {differ[:5]}')
    return packaged, docs, definition


def text(value, depth=3):
    """Compact storage (ADR 0046 P9): one record per line down to `depth` levels."""
    return (layered(value, depth)+'\n').encode('utf-8')


def derived_files(base):
    _, docs, definition = gate(base)
    files = {f'{folder}/generation.json': text(doc) for folder, doc in docs.items()}
    files['definition-map.json'] = text(definition, 2)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    base = Release(BASE)
    files = derived_files(base)
    if args.check:
        stale = [p for p, d in files.items() if not (TARGET/p).is_file() or (TARGET/p).read_bytes() != d]
        if stale:
            raise SystemExit(f'{len(stale)} of {len(files)} derived files differ from v2.2.0, e.g. {stale[:3]}')
        print(f'{len(files)} derived files equal v2.2.0')
        return
    for path, data in files.items():
        (TARGET/path).parent.mkdir(parents=True, exist_ok=True)
        (TARGET/path).write_bytes(data)
    print(f'{len(files)} files written to {TARGET.relative_to(ROOT).as_posix()}; now python -m scripts.atlas_delta --write')


if __name__ == '__main__':
    main()
