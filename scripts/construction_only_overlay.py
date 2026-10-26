"""Add the construction-only folders' program definitions to the release writers' sources (ADR 0039).

`apply(programs, systems)` adds the records of data/program-inputs/construction-only-v1.json
to an atlas_programs.Sources and an atlas_systems.Sources: source programs and
their general mixes, schedules, evidence and source files, and the HVAC systems
of the new types. It runs after the DOE reference reconciliation overlay, which
recomposes the DOE Ref mixes of the 83 original folders only.
"""
import copy

from scripts.common import ROOT, load_json

INPUT = ROOT/'data/program-inputs/construction-only-v1.json'


def apply(programs, systems, document=None):
    document = document or load_json(INPUT)
    clash = {p['id'] for p in document['programs']} & programs.programs.keys()
    if clash:
        raise ValueError('Construction-only programs already in the sources: '+', '.join(sorted(clash)[:3]))
    programs.programs.update({p['id']: copy.deepcopy(p) for p in document['programs']})
    programs.compositions.update({c['id']: copy.deepcopy(c) for c in document['compositions']})
    programs.schedules.update({s['id']: copy.deepcopy(s) for s in document['schedules']})
    programs.evidence.update({e['id']: copy.deepcopy(e) for e in document['provenance']})
    for source in document['source_files']:
        programs.source_files.setdefault(source['id'], copy.deepcopy(source))
    programs.twins = {p['source_definition_id']: p for p in programs.programs.values() if p.get('source_definition_id')}
    systems.definitions = programs
    systems.hvac.update({h['id']: copy.deepcopy(h) for h in document['hvac_systems']})
    systems.components.update({c['id']: copy.deepcopy(c) for c in document['components']})
    systems.schedules = {**programs.schedules, **{s['id']: s for s in systems.water['schedules']}}
