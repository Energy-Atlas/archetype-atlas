"""Regenerate and compare the reference using this extracted release's own code/data."""
import gzip
from pathlib import Path

from .comparison import compare_bundles
from .generator import generate
from .resources import strict_json


def main():
    root = Path(__file__).resolve().parents[1]
    request = strict_json((root / 'references/all-cases-request.json').read_bytes(), 'references/all-cases-request.json')
    expected = strict_json(gzip.decompress((root / 'references/all-cases-bundle.json.gz').read_bytes()),
                           'references/all-cases-bundle.json.gz')
    actual = generate(request['params'], request['seed'])
    differences = compare_bundles(actual, expected, expected['metadata']['comparison_policy'])
    if differences:
        raise SystemExit('\n'.join(differences[:30]))
    count=len(request['params']['instances'])
    detail=f"; {len(actual['constituents'])} indexed actual/derived constituents" if actual['generation'].get('source_compositions') else ''
    print(f"Source/discrete and numerical reproduction passed: {count} cases, "
          f"{len(actual['schedules'])} schedules{detail}")
    mixed_request=root/'references/mixed-family-request.json'
    mixed_reference=root/'references/mixed-family-bundle.json.gz'
    if mixed_request.exists()!=mixed_reference.exists():
        raise SystemExit('Incomplete mixed-family reference pair')
    if mixed_request.exists():
        request=strict_json(mixed_request.read_bytes(),'mixed-family request')
        expected=strict_json(gzip.decompress(mixed_reference.read_bytes()),'mixed-family reference')
        actual=generate(request['params'],request['seed'])
        differences=compare_bundles(actual,expected,expected['metadata']['comparison_policy'])
        if differences: raise SystemExit('\n'.join(differences[:30]))
        print(f"Mixed-family own-runtime reproduction passed: {len(actual['constituents'])} constituents, {len(actual['schedules'])} schedules")


if __name__ == '__main__':
    main()
