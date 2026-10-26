"""Add the IECC commercial family (ADR 0040) to the release writers' sources.

`apply(programs, systems)` adds the records of data/program-inputs/iecc-commercial-<edition>.json
for the six editions to an atlas_programs.Sources and an atlas_systems.Sources: source
programs and their mixes, schedules, evidence, source files, and the hot-water and
building services. The programs are source values only, so no resolution, twin or
unresolved row is added. `Documents` (scripts.iecc_commercial_documents) adds the
construction sets and serves their documents through the construction export hook.
"""
import copy

from scripts.common import ROOT, load_json
from scripts.iecc_commercial_documents import INPUT, Documents
from scripts.iecc_commercial_zones import EDITIONS

INPUTS = tuple(INPUT.format(e) for e in EDITIONS)
SCRIPTS = ('scripts/iecc_commercial_overlay.py', 'scripts/iecc_commercial_documents.py', 'scripts/iecc_commercial_zones.py')


def inputs():
    return {e: load_json(ROOT/INPUT.format(e)) for e in EDITIONS}


def apply(programs, systems, documents=None):
    documents = documents or inputs()
    for edition, document in sorted(documents.items()):
        clash = {p['id'] for p in document['programs']} & programs.programs.keys()
        if clash:
            raise ValueError(f'IECC {edition} programs already in the sources: '+', '.join(sorted(clash)[:3]))
        programs.programs.update({p['id']: copy.deepcopy(p) for p in document['programs']})
        programs.compositions.update({c['id']: copy.deepcopy(c) for c in document['compositions']})
        programs.schedules.update({s['id']: copy.deepcopy(s) for s in document['schedules']})
        programs.evidence.update({e['id']: copy.deepcopy(e) for e in document['provenance']})
        for source in document['source_files']:
            programs.source_files.setdefault(source['id'], copy.deepcopy(source))
        clash = {s['id'] for s in document['services']} & systems.services.keys()
        if clash:
            raise ValueError(f'IECC {edition} services already in the sources: '+', '.join(sorted(clash)[:3]))
        systems.services.update({s['id']: copy.deepcopy(s) for s in document['services']})
    programs.twins = {p['source_definition_id']: p for p in programs.programs.values() if p.get('source_definition_id')}
    systems.definitions = programs
    systems.schedules = {**programs.schedules, **{s['id']: s for s in systems.water['schedules']}}


def constructions(documents=None):
    return Documents(documents)
