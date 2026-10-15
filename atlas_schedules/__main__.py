"""Strict, offline JSON request/response entry point."""
import argparse
from pathlib import Path

from .canonical import canonical
from .errors import GeneratorError
from .generator import generate
from .resources import strict_json
from .owners import request_version


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate source-backed M1 hourly schedules offline')
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    request = strict_json(args.request.read_bytes(), str(args.request))
    if not isinstance(request, dict) or set(request) != {'schema_version', 'params', 'seed'}:
        raise GeneratorError('invalid_contract', '/', 'Expected the exact schema_version/params/seed request wrapper')
    if request['schema_version']!=request_version(request['params']):
        raise GeneratorError('invalid_contract','/schema_version','Envelope must match explicit/effective params version')
    bundle = generate(request['params'], request['seed'])
    content = canonical(bundle)
    if args.output.exists():
        raise GeneratorError('output_exists', str(args.output), 'Output must not already exist')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(content)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
