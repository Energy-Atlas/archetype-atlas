"""The record edits of data release 2.6.0 (ADR 0065 section 3, ADR 0066), as a pure function of the resolved release 2.5.0.

python -m scripts.atlas_edits_2_6_0          # what the edits change over release 2.5.0
python -m scripts.atlas_edits_2_6_0 --ids    # also print every ID that moves

`edit(files)` takes `scripts.atlas_delta.files('2.5.0')` and returns a `scripts.atlas_edits.Edited`. The delta writer
of release 2.6.0 lays it over 2.5.0. The edit reads no new input: it applies the ADR 0065 section 3 rule
(`scripts.attic_boundary`) to the stored records.

**The InteriorCeiling of the openstudio-standards attic contexts.** In a 90.1 or DOE Ref set, OpenStudio gives the
occupied zones' ceilings paired with the `Attic` space type's floor the attic floor reversed (search distance 2 against
the building default's 4; `ForwardTranslator::resolveMatchedSurfaceConstructionConflicts`, pinned in
`sources/construction-interzone-lock.json`), not the building-default interior ceiling. The unified record counted
those ceilings under `InteriorCeiling`. For every unified context with an openstudio-standards attic whose
`InteriorCeiling` has one non-space-type contributor (`attic_boundary._ceiling_correction` status `corrected`), the
stored `components.InteriorCeiling.derivation` becomes the corrected one (the attic-paired area removed; zero reference
area becomes `unique_source_recipe_without_reference_exposure`), and `provenance.interior_ceiling_correction` keeps the
derivation it replaced, the paired area, the reason, the evidence and this decision (`attic_boundary.record_correction`).
The OpenStudio evidence row joins the template's construction evidence (`evidence/commercial/<template>/library.json`)
and the context's evidence list. The recipe, its assembly, the detailed rules and every other component are unchanged.
A context the rule reports `unresolved` would be left as it is and listed (none in release 2.5.0).

Values follow the set's storage (ADR 0036 section 6): a component or provenance member shared by every unified context
of the set stays in the set's common part; otherwise each context gets its own value, through the set's value table.
Construction set IDs then follow their rule (ADR 0046 section 8; `scripts.release_editor.set_ids`), and every citing file
follows (`scripts.atlas_edits.follow_ids`), as in release 2.3.0. No program, schedule, service or library record changes.
"""
import argparse
import hashlib
import json

from scripts import atlas_constructions, atlas_delta, attic_boundary, release_editor
from scripts.atlas_edits import Edited, Tree, del_if_untouched, follow_ids
from scripts.atlas_format import canonical
from scripts.iecc_commercial_values import layered

BASE = '2.5.0'
RELEASE = '2.6.0'
ADR = 'docs/adr/0066-release-2-6-0.md'
ROLE = 'InteriorCeiling'
CARRIED = attic_boundary.CARRIED


def interzone_row():
    """The OpenStudio interzone-resolution evidence row the correction cites ({id: row}), as scripts.attic_boundary forms it."""
    rows, ids = attic_boundary.evidence_rows('openstudio_standards_rules', True)
    return ids[-1], rows[ids[-1]]


def corrections(tree, suite, evidence_id):
    """{set path: {context key: export correction}} of the stored unified contexts the rule corrects; and the unresolved."""
    out, unresolved = {}, []
    for path in sorted(p for p in tree.files if p.startswith('commercial/') and '/constructions/' in p):
        record = tree[path]
        for key in sorted(record['contexts']):
            if 'unified' not in record['contexts'][key]:
                continue
            detailed = suite.export(record['id'], key, 'detailed')
            unified = suite.export(record['id'], key, 'unified')
            fam, found = attic_boundary.recognise(detailed, unified)
            if fam != 'openstudio_standards_rules' or not found:
                continue
            if CARRIED in (unified.get('provenance') or {}):
                raise ValueError(f'{record["id"]} {key}: the record already carries an InteriorCeiling correction')
            correction = attic_boundary._ceiling_correction(fam, unified, detailed, found, evidence_id)
            if correction is None:
                continue
            if correction['status'] != 'corrected':
                unresolved.append({'set_id': record['id'], 'context': key, 'reason': correction['reason']})
                continue
            out.setdefault(path, {})[key] = correction
    return out, unresolved


def value_id(value):
    return 'v-'+hashlib.sha256(canonical(value).encode()).hexdigest()[:10]  # the 1.x writer's value-table rule


def put(record, key, field, sub, value, shared):
    """A context's own value of `field/sub` (or of the list `field` when `sub` is None): through the value table when
    another context of the set holds the same value, else in the context's fields; where it already sits, it stays."""
    member = record['contexts'][key]['unified']
    path = field if sub is None else f'{field}/{sub}'
    in_fields = (field in member['fields']) if sub is None else (sub in member['fields'].get(field, {}))
    if path in member['refs'] or (shared and not in_fields):
        vid = value_id(value)
        if record['values'].setdefault(vid, value) != value:
            raise ValueError('Value ID clash: '+vid)
        member['refs'][path] = vid
        if in_fields:
            if sub is None:
                del member['fields'][field]
            else:
                del member['fields'][field][sub]
    elif sub is None:
        member['fields'][field] = value
    else:
        member['fields'].setdefault(field, {})[sub] = value


def overridden(record, key, field, sub):
    member = record['contexts'][key]['unified']
    return f'{field}/{sub}' in member['refs'] or sub in member['fields'].get(field, {})


def correct_set(record, fixes, evidence_id):
    """Write the corrected derivation, the carried correction and the evidence citation into one set record."""
    unified_keys = sorted(k for k, c in record['contexts'].items() if 'unified' in c)
    partial = record['common']['unified']['partial']
    notes = {k: attic_boundary.record_correction(c, ADR) for k, c in fixes.items()}
    derivations = {k: c['corrected'] for k, c in fixes.items()}
    common = (set(fixes) == set(unified_keys) and len({canonical(v) for v in derivations.values()}) == 1
              and len({canonical(v) for v in notes.values()}) == 1 and ROLE in partial.get('components', {})
              and 'provenance' in partial and not any(overridden(record, k, 'components', ROLE) for k in unified_keys)
              and not any(overridden(record, k, 'provenance', CARRIED) for k in unified_keys))
    before = set(record['values'])
    used_before = used_values(record)
    if common:
        partial['components'][ROLE] = {**partial['components'][ROLE], 'derivation': next(iter(derivations.values()))}
        partial['provenance'] = dict(sorted({**partial['provenance'], CARRIED: next(iter(notes.values()))}.items()))
    else:
        component_counts = _counts({k: {**release_editor.stored(record, k, 'unified', 'components', ROLE), 'derivation': derivations[k]}
                                    for k in fixes})
        note_counts = _counts(notes)
        for key in sorted(fixes):
            component = {**release_editor.stored(record, key, 'unified', 'components', ROLE), 'derivation': derivations[key]}
            put(record, key, 'components', ROLE, component, component_counts[canonical(component)] > 1)
            put(record, key, 'provenance', CARRIED, notes[key], note_counts[canonical(notes[key])] > 1)
    for key in sorted(fixes):
        member = record['contexts'][key]['unified']
        if 'evidence' in member['refs']:
            stored = record['values'][member['refs']['evidence']]
        elif 'evidence' in member['fields']:
            stored = member['fields']['evidence']
        else:
            raise ValueError(f'{record["id"]} {key}: the unified evidence list is not stored with the context')
        stored = [record['values'][e[len(atlas_constructions.VALUE):]] if isinstance(e, str) and e.startswith(atlas_constructions.VALUE)
                  else e for e in stored]
        put(record, key, 'evidence', None, sorted({*stored, evidence_id}), False)
    # Drop the value-table entries this edit left unused, and only those.
    for vid in (used_before - used_values(record)) & before:
        del record['values'][vid]
    return common


def _counts(values):
    out = {}
    for value in values.values():
        out[canonical(value)] = out.get(canonical(value), 0) + 1
    return out


def used_values(record):
    used = {v for c in record['contexts'].values() for m in c.values() for v in m['refs'].values()}
    used |= {s[len(atlas_constructions.VALUE):] for s in atlas_constructions.strings(record) if s.startswith(atlas_constructions.VALUE)}
    return used


def edit(files):
    tree = Tree(files)
    suite = atlas_constructions.read_files({p: d for p, d in files.items()
                                            if p.startswith(('commercial/', 'evidence/commercial/')) and not p.endswith('.md')})
    evidence_id, row = interzone_row()
    found, unresolved = corrections(tree, suite, evidence_id)
    summary = {'interior_ceiling': {}, 'unresolved': unresolved, 'common': [], 'evidence_id': evidence_id}
    templates = set()
    for path, fixes in found.items():
        record = tree[path]
        if correct_set(record, fixes, evidence_id):
            summary['common'].append(record['id'])
        summary['interior_ceiling'][record['id']] = sorted(fixes)
        templates.add(path.split('/')[1])
    for template in sorted(templates):
        library = tree[f'evidence/commercial/{template}/library.json']
        if library.setdefault(evidence_id, row) != row:
            raise ValueError(f'{template}: evidence {evidence_id} is stored with other content')
    for path in sorted(p for p in tree.files if p.startswith('commercial/') and '/constructions/' in p):
        if path not in found and path in tree.values:
            del_if_untouched(tree, path, tree.values[path])
    dumped = tree.dump()
    if release_editor.program_ids(dumped):
        raise ValueError('A program moved; the 2.6.0 edits touch no program')
    ids = release_editor.set_ids(dumped, {})
    if set(ids) != set(summary['interior_ceiling']):
        raise ValueError(f'The sets that move ({len(ids)}) are not the corrected sets ({len(summary["interior_ceiling"])})')
    if len(set(ids.values())) != len(ids) or set(ids.values()) & (set(dumped) - set(ids)):
        raise ValueError('Moved IDs collide')
    out = follow_ids(dumped, ids)
    changed = {p: d for p, d in out.items() if files.get(p) != d}
    removed = sorted(set(files) - set(out))
    return Edited(changed, removed, dict(sorted(ids.items())), summary)


def id_map_bytes(ids):
    """The ID map a 2.6.0 delta carries: release 2.5.0 IDs to their 2.6.0 IDs."""
    record = {'schema_version': '1.0.0', 'decision': ADR, 'base_release': BASE, 'release': RELEASE,
              'description': 'IDs of release 2.5.0 that move in release 2.6.0 (ADR 0066: the construction sets whose unified '
                             'InteriorCeiling derivation is corrected, ADR 0065 section 3), mapped to their new values.',
              'ids': dict(sorted(ids.items()))}
    return (layered(record, 1)+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ids', action='store_true', help='print every ID that moves')
    args = parser.parse_args()
    edited = edit(atlas_delta.files(BASE))
    summary = edited.summary
    contexts = sum(len(v) for v in summary['interior_ceiling'].values())
    print(f'Release {RELEASE} edits over {BASE}: InteriorCeiling corrected in {contexts} unified contexts of '
          f'{len(summary["interior_ceiling"])} construction sets ({len(summary["common"])} in the set\'s common part); '
          f'{len(summary["unresolved"])} unresolved; evidence {summary["evidence_id"]}')
    for entry in summary['unresolved']:
        print('  unresolved', entry)
    print(f'{len(edited.files)} files changed or added, {len(edited.removed)} removed, {len(edited.ids)} IDs move')
    if args.ids:
        for old, new in edited.ids.items():
            print(old, '->', new)


if __name__ == '__main__':
    main()
