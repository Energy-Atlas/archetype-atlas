"""Extract the DOE reference components the load and schedule comparisons do not cover.

Used by scripts.reconciliation_register. Per DOE reference model (scripts.idf_reader.Model):
- water-use draws (zone, peak flow, schedules, gain fractions);
- building services: elevator and exhaust-fan equipment, exterior lights and fuel
  equipment, refrigeration cases and compressor racks;
- humidistats;
- window-to-wall ratios per program (zones grouped by their mapped space type) and the
  15 whole-building values (N, E, S, W and roof over conditioned, unconditioned and all
  zone surfaces), weighted by zone multipliers. A direction without wall is None;
- internal mass and infiltration per zone;
- thermostats, the zones each schedule serves, zone floor areas, and the schedule of
  each program slot (the area-dominant DOE schedule over the program's zones).
"""
from collections import defaultdict

from scripts import idf_reader
from scripts.reference_loads import NON_SPACE_TYPE_PLUG

DIRECTIONS = ('N', 'E', 'S', 'W', 'roof')
# DOE program slot: (atlas entry kind, load quantity or parameter, schedule kind)
SLOTS = {'occupancy': ('load', 'occupancy', 'fraction'), 'activity': ('parameter', 'activity_schedule_id', 'activity'),
         'lighting': ('load', 'lighting', 'fraction'), 'electric_equipment': ('load', 'electric_equipment', 'fraction'),
         'gas_equipment': ('load', 'gas_equipment', 'fraction'), 'hot_water': ('load', 'hot_water_volume', 'fraction'),
         'heating': ('parameter', 'heating_setpoint_schedule_id', 'temperature'),
         'cooling': ('parameter', 'cooling_setpoint_schedule_id', 'temperature'),
         'humidifying': ('parameter', 'humidifying_setpoint_schedule_id', 'humidity'),
         'dehumidifying': ('parameter', 'dehumidifying_setpoint_schedule_id', 'humidity')}


def schedule_values(model, name):
    """Distinct numbers of a compact schedule, for constant fractions and temperatures."""
    fields = model.schedules().get((name or '').lower())
    if not fields:
        return None
    values = sorted({idf_reader.number(v) for v in fields[2:] if idf_reader.number(v) is not None})
    return values[0] if len(values) == 1 else values


def water_draws(model):
    result = []
    for f in model.all('wateruse:equipment'):
        result.append({'name': f[0], 'zone': f[7] if len(f) > 7 else '', 'peak_flow_m3_s': idf_reader.number(f[2]),
                       'flow_schedule': f[3], 'target_temperature_C': schedule_values(model, f[4]),
                       'hot_supply_temperature_C': schedule_values(model, f[5]) if len(f) > 5 else None,
                       'sensible_fraction': schedule_values(model, f[8]) if len(f) > 8 else None,
                       'latent_fraction': schedule_values(model, f[9]) if len(f) > 9 else None})
    return result


def services(model):
    result = []
    for item in model.loads('electricequipment'):
        if item['subcategory'].lower() in NON_SPACE_TYPE_PLUG:
            end_use = 'elevator' if 'elevator' in item['subcategory'].lower() else 'exhaust_fan'
            result.append({'end_use': end_use, 'name': item['name'], 'zones': item['zones'], 'method': item['method'],
                           'values': item['values'], 'schedule': item['schedule'], 'fractions': item['fractions']})
    for f in model.all('exterior:lights'):
        result.append({'end_use': 'exterior_lighting', 'name': f[0], 'schedule': f[1],
                       'design_level_W': idf_reader.number(f[2]), 'control': f[3] if len(f) > 3 else ''})
    for f in model.all('exterior:fuelequipment'):
        end_use = 'elevator' if 'elevator' in f[0].lower() else 'exterior_equipment'
        result.append({'end_use': end_use, 'name': f[0], 'fuel': f[1], 'schedule': f[2],
                       'design_level_W': idf_reader.number(f[3])})
    for f in model.all('refrigeration:case'):
        result.append({'end_use': 'refrigeration_case', 'name': f[0], 'zone': f[2], 'availability': f[1],
                       'capacity_W_m': idf_reader.number(f[5]), 'latent_heat_ratio': idf_reader.number(f[6]),
                       'runtime_fraction': idf_reader.number(f[7]), 'length_m': idf_reader.number(f[8]),
                       'operating_temperature_C': idf_reader.number(f[9]),
                       'fan_power_W_m': idf_reader.number(f[13]), 'lighting_power_W_m': idf_reader.number(f[14]),
                       'lighting_schedule': f[16]})
    for f in model.all('refrigeration:compressorrack'):
        result.append({'end_use': 'refrigeration_rack', 'name': f[0], 'heat_rejection': f[1].lower(),
                       'cop': idf_reader.number(f[2]), 'condenser_fan_W': idf_reader.number(f[4])})
    return result


def humidistats(model):
    return [{'zone': f[1], 'humidifying': schedule_values(model, f[2]), 'dehumidifying': schedule_values(model, f[3])}
            for f in model.all('zonecontrol:humidistat')]


def zone_fenestration(model):
    """{zone: wall and window area by orientation, roof and skylight area}, unmultiplied."""
    zones = defaultdict(lambda: {'wall': defaultdict(float), 'window': defaultdict(float)})
    hosts = {}
    for s in model.surfaces():
        if s['boundary'] != 'outdoors' or s['type'] not in ('wall', 'roof'):
            continue
        key = s['zone'].lower()
        direction = idf_reader.orientation(s['vertices'], model.north_axis) if s['type'] == 'wall' else 'roof'
        zones[key]['wall'][direction] += idf_reader.area(s['vertices'])
        hosts[s['name'].lower()] = (key, direction)
    for w in model.fenestration():
        host = hosts.get(w['host'].lower())
        if host and w['type'] in ('window', 'glassdoor'):
            zones[host[0]]['window'][host[1]] += idf_reader.area(w['vertices']) * w['multiplier']
    return zones


def ratios(wall, window):
    return {d: round(window[d] / wall[d], 4) if wall[d] > 0.01 else None for d in DIRECTIONS}


def fenestration(model, zone_programs):
    """Per-program and whole-building window ratios; zone_programs maps zone -> space type or None."""
    zones = zone_fenestration(model)
    groups = defaultdict(lambda: (defaultdict(float), defaultdict(float)))
    building = {c: (defaultdict(float), defaultdict(float)) for c in ('conditioned', 'unconditioned', 'all')}
    for key, z in zones.items():
        multiplier = model.zones[key]['multiplier']
        unconditioned = any(w in key for w in ('plenum', 'attic'))
        targets = [building['unconditioned' if unconditioned else 'conditioned'], building['all']]
        if zone_programs.get(key):
            targets.append(groups[zone_programs[key]])
        for wall, window in targets:
            for d in DIRECTIONS:
                wall[d] += z['wall'][d] * multiplier
                window[d] += z['window'][d] * multiplier
    return {'programs': {k: ratios(*v) for k, v in sorted(groups.items())},
            'building': {k: ratios(*v) for k, v in building.items()}}


def zone_thermostats(model):
    """{zone: (heating schedule, cooling schedule)} through ZoneControl:Thermostat and dual setpoints."""
    dual = {f[0].lower(): (f[1], f[2]) for f in model.all('thermostatsetpoint:dualsetpoint')}
    result = {}
    for f in model.all('zonecontrol:thermostat'):
        found = next((dual[v.lower()] for v in f[3:] if v.lower() in dual), None)
        if found:
            for zone in model.zone_names(f[1]):
                result[zone] = found
    return result


def schedule_zones(model):
    """{schedule (lower case): zones whose loads, thermostats, draws or infiltration use it}."""
    result = defaultdict(set)
    for cls in ('people', 'lights', 'electricequipment', 'gasequipment'):
        for item in model.loads(cls):
            result[item['schedule'].lower()].update(item['zones'])
    for zone, schedules in zone_thermostats(model).items():
        for name in schedules:
            result[name.lower()].add(zone)
    for d in water_draws(model):
        result[d['flow_schedule'].lower()].add(d['zone'].lower())
    for item in model.infiltration():
        result[item['schedule'].lower()].update(item['zones'])
    return result


def zone_floors(model):
    """{zone: floor area}, unmultiplied."""
    result = defaultdict(float)
    for s in model.surfaces():
        if s['type'] == 'floor':
            result[s['zone'].lower()] += idf_reader.area(s['vertices'])
    return result


def zone_slots(model):
    """{zone: {slot: schedule name}} from the DOE objects; service equipment excluded."""
    slots = defaultdict(dict)
    for item in model.loads('people'):
        for z in item['zones']:
            slots[z]['occupancy'] = item['schedule']
            if item['activity_schedule']:
                slots[z]['activity'] = item['activity_schedule']
    for cls, slot in (('lights', 'lighting'), ('electricequipment', 'electric_equipment'), ('gasequipment', 'gas_equipment')):
        for item in model.loads(cls):
            if cls == 'electricequipment' and item['subcategory'].lower() in NON_SPACE_TYPE_PLUG:
                continue
            for z in item['zones']:
                slots[z][slot] = item['schedule']
    for z, (heating, cooling) in zone_thermostats(model).items():
        slots[z]['heating'], slots[z]['cooling'] = heating, cooling
    for d in water_draws(model):
        slots[d['zone'].lower()]['hot_water'] = d['flow_schedule']
    for f in model.all('zonecontrol:humidistat'):
        for z in model.zone_names(f[1]):
            slots[z]['humidifying'] = f[2]
            if len(f) > 3 and f[3]:
                slots[z]['dehumidifying'] = f[3]
    return slots


def slot_choices(model, zone_programs, floors):
    """{program: {slot: schedule name}}, the area-dominant DOE schedule per program slot, and the conflicts."""
    names = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    for zone, slots in zone_slots(model).items():
        if zone in zone_programs:
            for slot, name in slots.items():
                names[zone_programs[zone]][slot][name] += floors.get(zone, 0.0)
    choices, conflicts = defaultdict(dict), []
    for program, slots in sorted(names.items()):
        for slot, areas in sorted(slots.items()):
            choices[program][slot] = max(sorted(areas), key=lambda n: areas[n])
            if len(areas) > 1:
                conflicts.append({'program': program, 'slot': slot, 'schedules': dict(sorted(areas.items())),
                                  'chosen': choices[program][slot]})
    return choices, conflicts
