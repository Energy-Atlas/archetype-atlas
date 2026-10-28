"""Read ADR 0036 construction suites for commercial template x building-type folders.

Each construction set is one file holding, per context, its detailed and unified documents
without their embedded resources; fields equal across the set's contexts are stored once.
Assemblies and materials sit in one library per template, evidence in the evidence tree.
Reading the files back gives the standalone documents (detailed 3.0.0, unified 2.0.0) with
readable IDs. The writer read the frozen construction releases and left with them in stage
X1.3 (ADR 0046 section 7; readable at the tag `frozen-data-2026-10-27`).
"""
import json
from pathlib import Path

RESOURCES = ('assemblies', 'materials')
VALUE = '@v:'  # a list element stored once in the set's value table


def strings(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)
    elif isinstance(value, str):
        yield value


def closures(skeleton, tables, evidence):
    """The resources a document embeds, derived from what it and its resources reference."""
    refs = set(strings(skeleton))
    assemblies = sorted(refs & tables['assemblies'].keys())
    refs |= set(strings([tables['assemblies'][a] for a in assemblies]))
    materials = sorted(refs & tables['materials'].keys())
    refs |= set(strings([tables['materials'][m] for m in materials]))
    cited = refs & evidence.keys()
    cited |= set(strings([evidence[e] for e in cited])) & evidence.keys()  # evidence citing evidence, one hop
    return {'assemblies': assemblies, 'materials': materials, 'evidence': sorted(cited)}


class ConstructionSuite:
    """Written construction files read back into the standalone detailed and unified documents."""

    def __init__(self, files):
        self.sets, self.library, self.evidence = {}, {t: {} for t in RESOURCES}, {}
        for path, data in files.items():
            if '/constructions/' in path:
                record = json.loads(data)
                self.sets[record['id']] = record
            elif '/library/' in path and Path(path).stem in RESOURCES:
                self.library[Path(path).stem].update(json.loads(data))
            elif path.startswith('evidence/') and not path.endswith('glossary.json'):
                self.evidence.update(json.loads(data))

    def export(self, set_id, key, representation):
        record = self.sets[set_id]
        common, stored = record['common'][representation], record['contexts'][key][representation]
        values = record['values']
        expand = lambda v: [values[e[len(VALUE):]] if isinstance(e, str) and e.startswith(VALUE) else e for e in v] if isinstance(v, list) else v
        delta = {f: ({s: expand(x) for s, x in v.items()} if isinstance(v, dict) else expand(v))
                 for f, v in json.loads(json.dumps(stored['fields'])).items()}
        for path, vid in stored['refs'].items():
            field, *sub = path.split('/')
            if sub:
                delta.setdefault(field, {})[sub[0]] = record['values'][vid]
            else:
                delta[field] = record['values'][vid]
        document = dict(common['fields'])
        merged = set(common['partial']) | set(common['lists'])
        for field in merged:
            document[field] = {**common['partial'].get(field, {}), **delta.get(field, {})}
            for sub, shared in common['lists'].get(field, {}).items():
                document[field][sub] = sorted(set(shared) | set(document[field].get(sub, [])))
        document.update({k: v for k, v in delta.items() if k not in merged})
        derived = closures(document, self.library, self.evidence)
        for table in RESOURCES:
            document[table] = {i: self.library[table][i] for i in document.get(table, derived[table])}
        document['evidence'] = {i: self.evidence[i] for i in document.get('evidence', derived['evidence'])}
        return json.loads(json.dumps(document))


def read_files(files):
    return ConstructionSuite(files)
