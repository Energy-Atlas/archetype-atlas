"""Cold, file-independent strict source/evidence primitives for pure authority."""
from datetime import date
import re

from .contract import _finite
from .errors import GeneratorError


def _fail(path, message):
    raise GeneratorError('source_integrity', path, message)


def _exact(value, keys, path):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail(path, 'Missing or unknown source authority fields')
    try:
        _finite(value, path)
    except GeneratorError as error:
        raise GeneratorError('source_integrity', error.path, error.message) from error


def _string(value, path):
    if not isinstance(value, str) or not value:
        _fail(path, 'Nonempty source string required')


def _sha(value, path):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        _fail(path, 'Exact SHA-256 required')


def _source_object(value, path):
    _exact(value, ('path', 'sha256', 'locator', 'value'), path)
    _string(value['path'], path+'/path'); _string(value['locator'], path+'/locator')
    _sha(value['sha256'], path+'/sha256')
    return value


def _field_evidence(value, path):
    if not isinstance(value, list) or not value:
        _fail(path, 'Independent field evidence is required')
    keys=('source_revision','source_path','source_sha256','locator','original_value',
          'original_unit','transformation','extraction_date','interpretation_note')
    for i, item in enumerate(value):
        where=path+'/'+str(i); _exact(item, keys, where)
        for key in ('source_revision','source_path','locator','transformation','interpretation_note'):
            _string(item[key], where+'/'+key)
        _sha(item['source_sha256'], where+'/source_sha256')
        if item['original_unit'] is not None and not isinstance(item['original_unit'], str):
            _fail(where+'/original_unit', 'Original unit must be string or null')
        day=item['extraction_date']
        if not isinstance(day,str) or re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}',day) is None:
            _fail(where+'/extraction_date','ISO extraction date required')
        try:date.fromisoformat(day)
        except ValueError:_fail(where+'/extraction_date','Invalid extraction date')
