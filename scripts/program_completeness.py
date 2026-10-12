"""Validate every v3 export and reproduce a compact completeness receipt."""
import argparse
from collections import Counter
import hashlib
from pathlib import Path

from scripts.common import ROOT, dump_json, load_json
from scripts.definition_contract import canonical
from scripts.definition_release import read_bundle, verify
from scripts.program_json_v3 import ProgramExporter, POLICY

REPORT = ROOT / 'docs/reviews/program-json-completeness.json'


def validate_programs(bundle, ids=None, output=None):
    before = hashlib.sha256(canonical(bundle)).hexdigest()
    exporter = ProgramExporter(bundle)
    rows = [p for p in bundle['programs'] if ids is None or p['id'] in ids]
    failures, hashes, types, resolutions, decisions, accepted = [], {}, Counter(), Counter(), {}, {}
    for source in rows:
        try:
            # Both contracts must be valid; only the ready form requires active completeness.
            exporter.export(source['id'], 'raw')
            out = exporter.export(source['id'], 'defaulted')
            hashes[source['id']] = hashlib.sha256(canonical(out)).hexdigest()
            types.update(l['type'] for l in exporter._all_loads(out))
            resolutions.update(r['rule'] for r in out['metadata']['resolutions'] if 'rule' in r)
            for decision in out['metadata'].get('pending_decisions', []) + out['metadata'].get('unresolved_source_effects', []):
                decisions.setdefault(decision, []).append(source['id'])
            for decision in out['metadata'].get('accepted_decisions', []):
                accepted.setdefault(decision, []).append(source['id'])
            if output:
                dump_json(Path(output) / (source['id'] + '.json'), out)
        except ValueError as error:
            failures.append({'program_id': source['id'], 'name': source['name'], 'template': source.get('template'),
                             'source_id': source.get('source_id'), 'reason': str(error)})
        # A full-library pass should not retain 1,900 large payloads in memory.
        exporter._ready_cache.pop((source['id'], 'raw'), None)
        exporter.historical._cache.clear()
    unchanged = hashlib.sha256(canonical(bundle)).hexdigest() == before
    if not unchanged:
        raise ValueError('Exporter mutated canonical source bundle')
    return {'schema_version': '1.0.0', 'program_schema_version': '3.0.0', 'default_policy_id': POLICY,
            'status': 'incomplete' if failures else 'included_operands_complete_with_open_decisions' if decisions else 'complete',
            'eligible': len(rows), 'ready': len(hashes), 'open_decisions': decisions, 'accepted_decision_programs': accepted,
            'source_bundle_unchanged': unchanged, 'source_bundle_sha256': before,
            'export_set_sha256': hashlib.sha256(canonical(hashes)).hexdigest(),
            'active_load_types': dict(sorted(types.items())), 'resolution_counts': dict(sorted(resolutions.items())),
            'checks': ['JSON Schema', 'active operand completeness', 'physical fractions and units',
                       'schedule/reference closure', 'calendar and special-day coverage',
                       'conditioning/setpoint consistency', 'physical demand identity', 'source immutability'],
            'limits': ['Program scope excludes air requirements and EV as documented.',
                       'User-approved program scope excludes residential general-water-use signed heat gains and DHW distribution/system effects; they are not assumed zero.',
                       'User-approved ruleset heat-weighting reference calendar is 2007 without holidays; source simulation rules remain intact.',
                       'Weather mains and model geometry/HVAC are evaluated when assembling the simulation.',
                       'No EnergyPlus simulation was run by this validator.'], 'failures': failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare to the committed receipt')
    parser.add_argument('--output', type=Path, help='Also write ready JSON files to a new directory')
    parser.add_argument('--report', type=Path, default=REPORT)
    parser.add_argument('--examples', action='store_true', help='Regenerate the versioned raw/ready examples')
    args = parser.parse_args()
    release = ROOT / 'data/definition-releases/v0.1.1'
    verification = verify(release)
    if verification.errors:
        raise SystemExit('\n'.join(verification.errors[:10]))
    if args.output:
        args.output.mkdir(parents=True, exist_ok=False)
    bundle = read_bundle(release)
    report = validate_programs(bundle, output=args.output)
    if args.examples:
        exporter = ProgramExporter(bundle)
        examples = [('medium-office', 'program-8c35a40eb0181596e0bfcac4', 'raw'),
                    ('medium-office', 'program-8c35a40eb0181596e0bfcac4', 'defaulted'),
                    ('residential', 'program-0079ce7b163bdb1bd0154dbe', 'defaulted')]
        for name, pid, mode in examples:
            dump_json(ROOT / f'docs/examples/program-json-v3/{name}.{mode}.json', exporter.export(pid, mode))
    inputs = ['scripts/program_json_v3.py', 'scripts/program_json_aggregation.py', 'scripts/program_completeness.py',
              'schemas/program-json-v3.schema.json', 'data/program-inputs/residential-v1.json',
              'data/program-inputs/er-triage-v1.json', 'sources/program-json-defaults-v2.json']
    report['input_sha256'] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs}
    if args.check:
        if load_json(args.report) != report:
            raise SystemExit('Completeness receipt is stale; regenerate and review')
    else:
        dump_json(args.report, report)
    print(f"Program completeness: {report['ready']}/{report['eligible']} ready; {len(report['failures'])} failures")
    if report['failures']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
