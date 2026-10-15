"""Freeze/check the additive equivalent release; no site/program/CI generation."""
import argparse
import copy
import hashlib
import math
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator
from scripts.common import ROOT, load_json
from scripts.construction_distribution import load_current_release
from scripts.construction_equivalent_export import export_equivalent
from scripts.construction_weighting import encoded, sha, load_profiles
from scripts.definition_contract import stable_id

OUTPUT = ROOT/'data/construction-equivalent-releases/v1.0.0'
SCHEMA = ROOT/'schemas/construction-equivalent-v1.schema.json'
VALIDATOR = Draft202012Validator(load_json(SCHEMA))
README = '''# Additive building-level construction equivalents 1.0.0

Precomputed source-archetype shares resolve one assembly per applicable semantic.
Detailed construction v2.2.0 and its historical sources/exports remain unchanged.
Ground, systems and BEMGen translation are outside this release.

Use python -m scripts.construction_equivalent_release --context-id ID --output selected.json
to obtain a standalone document. Source context IDs are retained for selection.
Use --check to rebuild from frozen inputs and compare exact UTF-8/LF bytes.
Construction-only generation; no annual schedules, website or CI/CD build.

catalogue.json stores context metadata, component_sets.json shared semantic recipes
and quantity rules, assemblies.json their thermal/optical data. completeness.json
records source gaps and approximation flags; blocked is never interpreted as zero.
Supporting program-library profiles live in data/program-support/construction-weighting-v1/.
Recover those once with python -m scripts.construction_weighting --recover --check;
this executes pinned geometry and source mass rules, not an annual energy model.

Opaque fitting uses two massive layers and one massless resistance (or source-
proven massless construction), two fitted parameters and no complexity escalation.
Conserve reference-film U and capacity; keep measured response errors even when
the approximation is poor. Analytical checks/small material smoke runs establish
numerical/input consistency, not annual building-energy accuracy. Systematic
construction-versus-zoning error validation is deferred to the journal work.

Mass quantities describe additional source mass or a residual physical capacity
budget, never an instruction to add slabs already represented by surfaces.
BEMGen reconciles actual geometry; consumer geometry is not a blending input.
Natural ACH is copied unchanged from the selected detailed reference context.

Preserve LICENSE and sources/licenses upstream notices. Original Atlas work is
unlicensed by user choice. Local research artefact; no production publication.
'''


def validate_document(document, source, profiles):
    VALIDATOR.validate(document)
    c = source['contexts'][document['detailed_context_id']]
    if document['infiltration'] != c['infiltration']:
        raise ValueError('Changed source reference infiltration')
    primary = source['construction_sets'][c['construction_set_id']]
    if document['source'] != primary['source']:
        raise ValueError('Changed source metadata')
    used = set()
    allowed = set(source['assemblies']) | set(profiles['mass_recipes'])
    for component in document['components'].values():
        if component['status'] != 'ready':
            continue
        aid = component['assembly_id']
        if aid not in document['assemblies']:
            raise ValueError('Orphan equivalent assembly reference')
        used.add(aid)
        rows = component['derivation']['contributors']
        if not rows or not math.isclose(sum(r['weight'] for r in rows), 1, abs_tol=1e-8):
            raise ValueError('Incomplete source weight coverage')
        if any(r['assembly_id'] not in allowed for r in rows):
            raise ValueError('Orphan source derivation reference')
    if used != set(document['assemblies']):
        raise ValueError('Unused equivalent assembly reference')
    for a in document['assemblies'].values():
        if a['model'] != 'opaque_layers':
            continue
        layers, target = a['layers'], a['targets']
        r, c = sum(l['R'] for l in layers), sum(l['C'] for l in layers)
        if not math.isclose(c, target['capacity_J_m2_K'], rel_tol=1e-6, abs_tol=1e-8):
            raise ValueError('Equivalent capacity is not conserved')
        if not math.isclose(r, target['resistance_m2_K_W'], rel_tol=1e-6, abs_tol=1e-10):
            raise ValueError('Equivalent resistance is not conserved')
        u = 1/(r+sum(a['fit']['films_m2_K_W']))
        if not math.isclose(u, target['u_reference_W_m2_K'], rel_tol=1e-6):
            raise ValueError('Equivalent reference U is not conserved')
        for l in layers:
            if l['model'] == 'Material':
                capacity = l['thickness_m']*l['density_kg_m3']*l['specific_heat_J_kg_K']
                if not math.isclose(capacity, l['C'], rel_tol=1e-6):
                    raise ValueError('Material layer capacity is inconsistent')
                if not math.isclose(l['thickness_m']/l['conductivity_W_m_K'], l['R'], rel_tol=1e-6):
                    raise ValueError('Material layer resistance is inconsistent')
                if l['conductivity_W_m_K']/(l['density_kg_m3']*l['specific_heat_J_kg_K']) > 1e-5:
                    raise ValueError('Material exceeds diffusivity search bound')
    expected_status = 'blocked' if any(v['status']=='blocked' for v in document['components'].values()) else 'ready'
    if document['status'] != expected_status:
        raise ValueError('Invalid aggregate readiness')
    # JSON encoding rejects nonfinite values in all metadata and metrics, too.
    encoded(document)


def artifacts(source=None, profiles=None, context_ids=None):
    source = source if source is not None else load_current_release()
    profiles = profiles if profiles is not None else load_profiles()
    ids = sorted(context_ids if context_ids is not None else source['contexts'])
    if not set(ids) <= set(source['contexts']):
        raise ValueError('Unsupported detailed context selection')
    contexts, settings, assemblies, examples = {}, {}, {}, {}
    counts, qualities, semantic_counts, gaps = Counter(), Counter(), Counter(), defaultdict(list)
    for identity in ids:
        d = export_equivalent(source, identity, profiles)
        validate_document(d, source, profiles)
        counts[d['status']] += 1
        for role,v in d['components'].items():
            semantic_counts[role+'/'+v['status']] += 1
            if v['status'] == 'blocked':
                gaps[role+'/'+v['reason']].append(identity)
        for a in d['assemblies'].values():
            qualities[a['quality']] += 1
        if d['reference_id']=='90.1-2019/MediumOffice' and d['climate_zone']=='3B' and d['source']['building_type']=='MediumOffice':
            examples['examples/medium-office-2019-3B.json'] = encoded(d)
        if d['scope']=='whole_dwelling' and 'examples/residential.json' not in examples:
            examples['examples/residential.json'] = encoded(d)
        body = {k: d[k] for k in ('components','consumer_inputs','mass_accounting')}
        sid = stable_id('equivalent-component-set', body)
        settings[sid] = body
        contexts[identity] = {k:v for k,v in d.items() if k not in (*body, 'assemblies')}
        contexts[identity]['component_set_id'] = sid
        assemblies.update(d['assemblies'])
    selected_sets = {source['contexts'][i]['construction_set_id'] for i in ids}
    coverage = {'construction_sets': len(selected_sets), 'contexts': len(ids), 'ready_contexts': counts['ready'],
                'blocked_contexts': counts['blocked'], 'component_status_counts': dict(sorted(semantic_counts.items())),
                'quality_counts_per_context_recipe': dict(sorted(qualities.items())),
                'blocked_context_ids_by_reason': dict(sorted(gaps.items())),
                'interpretation': 'Quality review flags do not add layers or imply measured annual energy error.'}
    catalogue = {'schema_version': '1.0.0', 'kind': 'construction_equivalent_catalogue', 'source_release': 'v2.2.0',
                 'construction_sets': {i:source['construction_sets'][i] for i in sorted(selected_sets)}, 'contexts': contexts}
    files = {'catalogue.json': encoded(catalogue), 'component_sets.json': encoded(settings),
             'assemblies.json': encoded(assemblies), 'completeness.json': encoded(coverage),
             'README.md': README.encode('utf-8'), **examples}
    inputs = ['scripts/construction_equivalence.py', 'scripts/construction_equivalent_export.py',
              'scripts/construction_equivalent_release.py', 'schemas/construction-equivalent-v1.schema.json',
              'data/program-support/construction-weighting-v1/profiles.json',
              'data/program-support/construction-weighting-v1/manifest.json',
              *[f'data/construction-releases/{v}/manifest.json' for v in ('v2.0.0','v2.1.0','v2.2.0')]]
    manifest = {'schema_version': '1.0.0', 'kind': 'construction_equivalent_release', 'release': '1.0.0',
                'input_sha256': {p: sha(ROOT/p) for p in inputs},
                'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for name,data in sorted(files.items())},
                'coverage': {k:coverage[k] for k in ('construction_sets','contexts','ready_contexts','blocked_contexts')}}
    files['manifest.json'] = encoded(manifest)
    return files


def export_frozen(directory, context_id):
    directory = Path(directory)
    manifest = load_json(directory/'manifest.json')
    if manifest.get('kind') != 'construction_equivalent_release' or manifest.get('release') != '1.0.0':
        raise ValueError('Invalid equivalent release')
    for name, row in manifest['files'].items():
        if sha(directory/name) != row['sha256'] or (directory/name).stat().st_size != row['bytes']:
            raise ValueError('Equivalent release checksum mismatch: '+name)
    header = copy.deepcopy(load_json(directory/'catalogue.json')['contexts'][context_id])
    sid = header.pop('component_set_id')
    body = load_json(directory/'component_sets.json')[sid]
    header.update(body)
    all_assemblies = load_json(directory/'assemblies.json')
    used = {v['assembly_id'] for v in body['components'].values() if v['status']=='ready'}
    header['assemblies'] = {aid: all_assemblies[aid] for aid in sorted(used)}
    VALIDATOR.validate(header)
    return header


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--context-id')
    args = parser.parse_args()
    if args.context_id:
        if args.output is None:
            parser.error('--context-id requires --output')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(encoded(export_frozen(OUTPUT, args.context_id)))
        return
    for name,data in artifacts().items():
        path = OUTPUT/name
        if args.check:
            if path.read_bytes() != data:
                raise ValueError('Equivalent release differs: '+name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(load_json(OUTPUT/'manifest.json')['coverage'])


if __name__ == '__main__':
    main()
