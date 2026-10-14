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
    print(f"Source/discrete and numerical reproduction passed: {len(actual['constituents'])} cases, "
          f"{len(actual['schedules'])} schedules")


if __name__ == '__main__':
    main()
