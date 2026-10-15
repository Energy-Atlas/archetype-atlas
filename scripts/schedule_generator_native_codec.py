"""Strict development decoding of hash-locked native evidence containers."""
import gzip
import hashlib
import lzma

from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import safe_path

LEGACY_GZIP_COMPONENTS=frozenset({'residential-native-lock','commercial-native-lock',
    'small-office-native-lock','warehouse-native-lock','restaurant-programme-native-lock',
    'restaurant-water-native-lock','restaurant-water-public-native-lock','retail-context-native-lock'})
# Exact immutable v0.6.0 resource identity. This historical prose is not a codec
# prefix or a format guessing rule; no other lock/path may use it.
LEGACY_WATER_LOCK='2d3203d06c9f6cb5cb8f999d3d6ce0e88cf2f825c4ae545e55d02e26846e3a61'
LEGACY_WATER_PATH='data/schedule-generator/reference/restaurant-water-native.json.gz'


def decode_native_component(content,component,field='vectors'):
    """Verify compressed and raw byte identity, then return unchanged raw bytes."""
    key=component.get('reference_resource_key') if isinstance(component,dict) else None
    path='/native_components/'+str(key)+'/'+str(field)
    def fail(message):raise GeneratorError('source_integrity',path,message)
    try:
        if field not in {'inputs','vectors'}:fail('Exact native input/vector field required')
        lock=component['lock'];identity=hashlib.sha256(canonical(lock)).hexdigest()
        if component['reference_resource_sha256']!=identity:fail('Native source-lock identity differs')
        entry=lock[field];name=str(safe_path(entry['source_path']));fmt=entry.get('format')
        if key=='retail-programme-native-lock':
            expected='data/schedule-generator/reference/retail-programme-'+('inputs' if field=='inputs' else 'native')+'.json.xz'
            if fmt!='xz-json' or name!=expected:fail('New Retail native requires explicit xz-json and exact matching path')
            decode=lzma.decompress
        elif key in LEGACY_GZIP_COMPONENTS:
            if fmt=='gzip JSON actual native output':
                if (key!='restaurant-water-native-lock' or field!='vectors' or
                        identity!=LEGACY_WATER_LOCK or name!=LEGACY_WATER_PATH):
                    fail('Historical gzip label is outside its exact original lock/path identity')
            elif fmt not in {None,'gzip-json'}:fail('Unknown legacy native format')
            if not name.endswith('.json.gz'):fail('Legacy gzip format and native extension differ')
            decode=gzip.decompress
        else:fail('Unqualified native component codec identity')
        for size in ('size_bytes','payload_size_bytes'):
            if type(entry[size]) is not int or entry[size]<=0:fail('Positive exact native byte sizes required')
        for digest in ('sha256','payload_sha256'):
            value=entry[digest]
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                fail('Exact lowercase SHA256 receipts required')
        if not isinstance(content,bytes) or len(content)!=entry['size_bytes'] or hashlib.sha256(content).hexdigest()!=entry['sha256']:
            fail('Compressed native body differs from locked size/hash')
        payload=decode(content)
        if len(payload)!=entry['payload_size_bytes'] or hashlib.sha256(payload).hexdigest()!=entry['payload_sha256']:
            fail('Raw native body differs from original size/hash')
        return payload
    except GeneratorError:raise
    except (KeyError,TypeError,ValueError,OSError,EOFError,lzma.LZMAError) as error:
        raise GeneratorError('source_integrity',path,'Missing, malformed or corrupt native container: '+str(error)) from error
