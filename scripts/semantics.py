"""Unit conversions, source lookups, and schedule-rule inspection."""
import datetime as dt
import re

FT2_TO_M2 = 0.09290304
CFM_TO_M3_S = 0.0004719474432
BTUH_TO_W = 0.2930710701722222
FACTORS = {
    'W/ft2': 1 / FT2_TO_M2,
    'people/1000 ft2': 1 / (1000 * FT2_TO_M2),
    'cfm/ft2': CFM_TO_M3_S / FT2_TO_M2,
    'cfm/person': CFM_TO_M3_S,
    'Btu/h-ft2': BTUH_TO_W / FT2_TO_M2,
    'Btu/h-ft2-F': BTUH_TO_W / FT2_TO_M2 * 1.8,
    '1/h': 1,
    'dimensionless': 1,
}
DAY_TYPES = {'Default', 'Wkdy', 'Wknd', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri',
             'Sat', 'Sun', 'Hol', 'WntrDsn', 'SmrDsn', 'DummySmrDsn'}


def convert(value, unit):
    if unit != 'F' and unit not in FACTORS:
        raise ValueError(f'Unsupported units: {unit}')
    if value is None:
        return None
    return (value - 32) / 1.8 if unit == 'F' else value * FACTORS[unit]


def profile(rules, day_type, month_day):
    """Inspect hourly rules; last source rule wins among specific matches.

    This is a validation/inspection helper, not a simulation calendar adapter.
    Constant source values expand to 24 hours without interpolation.
    """
    if day_type not in DAY_TYPES:
        raise ValueError(f'Unknown day type: {day_type}')
    dt.date.fromisoformat('2000-' + month_day)
    specific, default = None, None
    for r in rules:
        start, end = r['start_date'][5:10], r['end_date'][5:10]
        applies = start <= month_day <= end if start <= end else month_day >= start or month_day <= end
        tokens = set(r['day_types'].split('|'))
        if not tokens <= DAY_TYPES:
            raise ValueError('Unsupported schedule day types')
        # Standards.Model.rb uses include?('SmrDsn'), so the source school
        # DummySmrDsn label sets the summer design profile. Retain the original
        # label in canonical evidence, but match the generator during inspection.
        if 'DummySmrDsn' in tokens:
            tokens.add('SmrDsn')
        if not applies:
            continue
        values = r['values'] * 24 if len(r['values']) == 1 else r['values']
        if len(values) != 24:
            raise ValueError('Expected constant or 24-hour schedule')
        if 'Default' in tokens:
            default = values
        matches = day_type in tokens
        matches |= day_type in {'Mon', 'Tue', 'Wed', 'Thu', 'Fri'} and 'Wkdy' in tokens
        matches |= day_type in {'Sat', 'Sun'} and 'Wknd' in tokens
        if matches:
            specific = values
    result = specific if specific is not None else default
    if result is None:
        raise ValueError(f'No profile for {day_type} on {month_day}')
    return result


def osm_objects(text):
    """Read tagged text OSM objects. No code evaluation or geometry generation."""
    # These pinned OSMs use unquoted fields and !- field labels. Fail on quotes
    # rather than pretend to support a general IDF/OSM grammar.
    if '"' in text:
        raise ValueError('Quoted OSM fields require a dedicated parser')
    objects = []
    kind, fields = None, {}
    for line in text.splitlines():
        body, _, comment = line.partition('!')
        body = body.strip()
        if not body:
            continue
        if kind is None:
            if body.startswith('OS:') and body.endswith(','):
                kind = body[:-1]
                fields = {}
            continue
        if ',' in body or ';' in body:
            value = re.split('[,;]', body, maxsplit=1)[0].strip()
            label = comment.lstrip('- ').strip()
            if label:
                fields[label] = value
            if ';' in body:
                objects.append({'kind': kind, 'fields': fields})
                kind = None
    if kind is not None:
        raise ValueError('Unterminated OSM object')
    return objects


def spaces(text):
    objs = osm_objects(text)
    types = {o['fields']['Handle']: o['fields'] for o in objs if o['kind'] == 'OS:SpaceType'}
    zones = {o['fields']['Handle']: o['fields'] for o in objs if o['kind'] == 'OS:ThermalZone'}
    result = []
    for o in objs:
        if o['kind'] != 'OS:Space':
            continue
        f = o['fields']
        typ = types.get(f.get('Space Type Name'), {})
        zone = zones.get(f.get('Thermal Zone Name'), {})
        result.append({
            'name': f['Name'], 'handle': f['Handle'],
            'source_building_type': typ.get('Standards Building Type', ''),
            'source_space_type': typ.get('Standards Space Type', ''),
            'part_of_total_floor_area': f.get('Part of Total Floor Area', ''),
            'zone': f.get('Thermal Zone Name', ''),
            'multiplier': float(zone.get('Multiplier', '') or 1),
        })
    if not result:
        raise ValueError('No OS:Space objects found')
    return result


def unique_match(rows, building_type, space_type):
    matches = [(i, r) for i, r in enumerate(rows)
               if r['building_type'] == building_type and r['space_type'] == space_type]
    if len(matches) != 1:
        raise ValueError(f'Expected one program for {building_type}/{space_type}; found {len(matches)}')
    return matches[0]


def option_rows(text):
    """Expand TSV continuation context without dropping secondary measures."""
    parameter, option, context_line = None, None, None
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        cols = line.split('\t')
        if len(cols) < 3:
            continue
        if cols[0]:
            parameter, option, context_line = cols[0], cols[1], line_number
        elif cols[1]:
            option, context_line = cols[1], line_number
        elif parameter is None:
            raise ValueError('TSV continuation before parameter/option definition')
        cols[0], cols[1] = parameter, option
        yield line_number, cols, context_line
