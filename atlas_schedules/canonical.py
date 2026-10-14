"""Strict canonical resource bytes and collision-free scoped schedule references."""
import json
from urllib.parse import quote

from .errors import GeneratorError


def canonical(value: object) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                           separators=(',', ':')) + '\n').encode('utf-8')
    except (ValueError, TypeError, UnicodeError) as error:
        raise GeneratorError('invalid_json', '/', str(error)) from error


def schedule_id(instance_key: str, slot: str) -> str:
    if not isinstance(instance_key, str) or not instance_key or not isinstance(slot, str) or not slot:
        raise GeneratorError('invalid_reference', '/', 'Instance key and slot must be nonempty strings')
    return 'schedule:' + quote(instance_key, safe='') + ':' + quote(slot, safe='')
