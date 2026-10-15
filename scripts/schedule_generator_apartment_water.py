"""Build-only adapter for independently locked apartment water source objects."""
import hashlib
import json

from atlas_schedules.caller_unit_water import compile_requirement
from atlas_schedules.errors import GeneratorError
from scripts.common import ROOT


def _verify_original(obj):
    """Check original file bytes and locator, leaving derived proof files separate."""
    path=obj['path']
    if not path.startswith(('data/definition-releases/v0.1.1/',
                            'data/raw/openstudio-standards/')):
        raise GeneratorError('source_integrity','/path','Original source path required')
    source=ROOT/path
    data=source.read_bytes()
    if hashlib.sha256(data).hexdigest()!=obj['sha256']:
        raise GeneratorError('source_integrity','/sha256','Original source file bytes differ')
    value=json.loads(data)
    locator=obj['locator']
    if not locator.startswith('/'):
        raise GeneratorError('source_integrity','/locator','JSON pointer required')
    for token in locator.lstrip('/').split('/'):
        token=token.replace('~1','/').replace('~0','~')
        value=value[int(token)] if isinstance(value,list) else value[token]
    if value!=obj['value']:
        raise GeneratorError('source_integrity','/value','Original whole source value differs')


def compile_apartment_water_requirement(programme: dict, service: dict,
                                        ruleset: dict, evidence: dict) -> dict:
    """Compile unqualified source authority; a candidate is never an allowlist."""
    result=compile_requirement(programme,service,ruleset,evidence)
    for obj in (programme,service,ruleset,evidence['source_system_type']):
        _verify_original(obj)
    for helper in evidence['fixed_controls']['value']['source_helpers']:
        path=helper['path']
        if (not path.startswith('data/raw/openstudio-standards/') or
                helper['locator']!='/' or
                hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=helper['sha256'] or
                (ROOT/path).read_text(encoding='utf-8')!=helper['value']):
            raise GeneratorError('source_integrity','/fixed_controls/source_helpers',
                                 'Original helper source file bytes differ')
    return result
