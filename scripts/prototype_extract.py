"""Read one residential code-prototype EnergyPlus model as dwelling semantics (ADR 0041, ADR 0042).

Shared by the IECC residential (EnergyPlus 23.1) and manufactured-housing (8.0)
extractors. A model gives:
- load instances: People, Lights, ElectricEquipment, GasEquipment, Exterior:Lights and
  WaterUse:Equipment, each with its host zone kind, the dwelling unit it belongs to (the
  multifamily models repeat every unit load per unit) and its schedules as checked
  atlas rulesets;
- controls: thermostat setpoint and activity schedules, people fractions;
- mechanical ventilation: ZoneVentilation:DesignFlowRate and Fan:ZoneExhaust fields;
- envelope: constructions by surface class, windows, doors, internal mass, window
  shading control, and infiltration (AirflowNetwork surface leakage or zone effective
  leakage area);
- window-to-wall ratios of the dwelling zones by orientation.
Field layouts: EnergyPlus 8.0 and 23.1 agree for every class read here except Window,
which lost its Shading Control Name field in 9.0, and BuildingSurface:Detailed and
InternalMass, which gained Space fields in 9.6 (scripts.idf_reader).
"""
import hashlib
import re

from scripts import idf_reader
from scripts.idf_schedules import Schedules, calendar_days

POSITION = re.compile(r'_(front|back)row_(bottom|middle|top)floor$', re.I)
DAYS = calendar_days([])
LOAD_CLASSES = ('people', 'lights', 'electricequipment', 'gasequipment', 'exterior:lights', 'wateruse:equipment')
TYPES = {'people': 'occupancy', 'lights': 'lighting', 'electricequipment': 'electric_equipment',
         'gasequipment': 'gas_equipment', 'exterior:lights': 'exterior_lighting', 'wateruse:equipment': 'hot_water'}
SCHEDULE_KINDS = {'fraction': ('fraction', 'dimensionless'), 'temperature': ('temperature', 'C'),
                  'activity': ('activity', 'W/person'), 'any': ('number', 'dimensionless')}


def digest(value):
    import json
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def number(value):
    return idf_reader.number(value)


def stem(name):
    """An object name without its unit, position and counter suffixes: 'IECC_Adj1' -> 'IECC_Adj'."""
    text = POSITION.sub('', name)
    text = re.sub(r'_unit\d+$', '', text, flags=re.I)
    return re.sub(r'\d+$', '', text)


def zone_kind(zone):
    """'living_unit2_BackRow_TopFloor' -> 'living'; 'garage1' -> 'garage'; 'Breezeway' -> 'breezeway'."""
    text = POSITION.sub('', zone.lower())
    text = re.sub(r'_unit\d+$', '', text)
    return re.sub(r'\d+$', '', text)


def unit_of(zone):
    """The dwelling unit a living zone belongs to: 'unit2_backrow_topfloor', or None outside a unit."""
    match = re.search(r'unit(\d+)(_(front|back)row_(bottom|middle|top)floor)?$', zone.lower())
    return match[0] if match and zone_kind(zone) == 'living' else None


class Model:
    """One prototype IDF read as data."""

    def __init__(self, path):
        self.reader = idf_reader.Model(path)
        self.objects = self.reader.objects
        self.schedules = Schedules(self.objects)
        self._rules = {}

    def all(self, cls):
        return self.reader.all(cls)

    def schedule(self, name):
        """{'name', 'type_limits', 'rules'} of a referenced schedule, its rules checked over the full year."""
        if not name:
            return None
        key = name.lower()
        if key not in self._rules:
            fields = self.schedules.fields(name)
            limits = fields[1] if self.schedules.cls(name) != 'schedule:year' or len(fields) > 1 else ''
            self._rules[key] = {'name': fields[0], 'type_limits': limits,
                                'rules': self.schedules.checked_ruleset(name, DAYS)}
        return self._rules[key]

    def loads(self):
        """Every internal-gain, exterior-light and hot-water object as a load instance."""
        out = []
        for cls in LOAD_CLASSES:
            for f in self.all(cls):
                out.append(self.load(cls, f))
        return out

    def load(self, cls, f):
        item = {'class': cls, 'object': f[0], 'stem': stem(f[0]), 'type': TYPES[cls]}
        if cls == 'exterior:lights':
            item.update(zone=None, unit=None, schedule=self.schedule(f[1]), method='DesignLevel',
                        value=number(f[2]), source_unit='W', control=f[3] if len(f) > 3 else '',
                        subcategory=f[4] if len(f) > 4 else '')
            return item
        if cls == 'wateruse:equipment':
            zone = f[7] if len(f) > 7 else ''
            item.update(zone=zone_kind(zone) if zone else None, unit=None, subcategory=f[1], method='PeakFlowRate',
                        value=number(f[2]), source_unit='m3/s', schedule=self.schedule(f[3]),
                        target_temperature=self.schedule(f[4]) if len(f) > 4 else None,
                        hot_supply_temperature=self.schedule(f[5]) if len(f) > 5 and f[5] else None,
                        cold_supply_temperature=self.schedule(f[6]) if len(f) > 6 and f[6] else None,
                        sensible_fraction=self.schedule(f[8]) if len(f) > 8 and f[8] else None,
                        latent_fraction=self.schedule(f[9]) if len(f) > 9 and f[9] else None)
            return item
        zones = self.reader.zone_names(f[1])
        if len(zones) != 1:
            raise ValueError(f'{f[0]} applies to a zone list; dwelling loads name one zone')
        zone = self.reader.zones[zones[0]]['name']
        method = f[3].lower()
        position = {'people': 4, 'lights': 4, 'electricequipment': 4, 'gasequipment': 4}[cls]
        slot = {'people': 0, 'equipmentlevel': 0, 'lightinglevel': 0, 'watts/area': 1, 'watts/person': 2,
                'people/area': 1, 'area/person': 2}[method]
        units = {'people': ('person', 'person/m2', 'm2/person')[slot]}.get(cls, ('W', 'W/m2', 'W/person')[slot])
        item.update(zone=zone_kind(zone), unit=unit_of(zone), schedule=self.schedule(f[2]), method=f[3],
                    value=number(f[position+slot]), source_unit=units)
        if cls == 'people':
            item.update(fraction_radiant=number(f[7]), sensible_fraction=f[8] if f[8].lower() == 'autocalculate' else number(f[8]),
                        activity=self.schedule(f[9]))
        elif cls == 'lights':
            item.update(fractions={'return_air': number(f[7]), 'radiant': number(f[8]), 'visible': number(f[9]),
                                   'replaceable': number(f[10]) if len(f) > 10 else None},
                        subcategory=f[11] if len(f) > 11 else '')
        else:
            item.update(fractions={'latent': number(f[7]), 'radiant': number(f[8]), 'lost': number(f[9])},
                        subcategory=f[10] if cls == 'electricequipment' and len(f) > 10 else f[11] if len(f) > 11 else '')
        return item

    def thermostats(self):
        """{zone kind and unit: (heating schedule, cooling schedule)} of dual-setpoint thermostats."""
        setpoints = {f[0].lower(): f for f in self.all('thermostatsetpoint:dualsetpoint')}
        out = []
        for f in self.all('zonecontrol:thermostat'):
            zone = self.reader.zones[self.reader.zone_names(f[1])[0]]['name']
            controls = [setpoints[f[i + 1].lower()] for i in range(3, len(f) - 1, 2)
                        if f[i].lower() == 'thermostatsetpoint:dualsetpoint' and f[i + 1].lower() in setpoints]
            for c in controls:
                out.append({'zone': zone_kind(zone), 'unit': unit_of(zone), 'heating': self.schedule(c[1]),
                            'cooling': self.schedule(c[2]), 'control_type': self.schedule(f[2])})
        return out

    def ventilation(self):
        """Mechanical ventilation objects of the dwelling zones."""
        out = []
        for f in self.all('zoneventilation:designflowrate'):
            zone = self.reader.zones[self.reader.zone_names(f[1])[0]]['name']
            out.append({'zone': zone_kind(zone), 'unit': unit_of(zone), 'object': stem(f[0]), 'schedule': self.schedule(f[2]),
                        'method': f[3], 'design_flow_rate_m3_s': number(f[4]), 'flow_per_area_m3_s_m2': number(f[5]),
                        'flow_per_person_m3_s': number(f[6]), 'air_changes_per_hour': number(f[7]),
                        'ventilation_type': f[8], 'fan_pressure_rise_Pa': number(f[9]),
                        'fan_total_efficiency': number(f[10]), 'coefficients': [number(v) for v in f[11:15]]})
        for f in self.all('fan:zoneexhaust'):
            out.append({'zone': None, 'unit': None, 'object': stem(f[0]), 'schedule': self.schedule(f[1]),
                        'method': 'Fan:ZoneExhaust', 'fan_total_efficiency': number(f[2]),
                        'fan_pressure_rise_Pa': number(f[3]), 'maximum_flow_rate_m3_s': number(f[4]),
                        'end_use_subcategory': f[7] if len(f) > 7 else ''})
        exchangers = {f[0].lower(): f for f in self.all('heatexchanger:airtoair:sensibleandlatent')}
        fans = {f[0].lower(): f for c in ('fan:onoff', 'fan:constantvolume', 'fan:systemmodel') for f in self.all(c)}
        for f in self.all('zonehvac:energyrecoveryventilator'):
            exchanger, supply, exhaust = exchangers.get(f[2].lower()), fans.get(f[5].lower()), fans.get(f[6].lower())
            out.append({'zone': None, 'unit': None, 'object': stem(f[0]), 'schedule': self.schedule(f[1]),
                        'method': 'ZoneHVAC:EnergyRecoveryVentilator', 'supply_air_flow_rate_m3_s': number(f[3]),
                        'exhaust_air_flow_rate_m3_s': number(f[4]),
                        'heat_exchanger_effectiveness': [number(v) for v in exchanger[3:11]] if exchanger else None,
                        'supply_fan': {'fan_total_efficiency': number(supply[2]), 'fan_pressure_rise_Pa': number(supply[3])} if supply else None,
                        'exhaust_fan': {'fan_total_efficiency': number(exhaust[2]), 'fan_pressure_rise_Pa': number(exhaust[3])} if exhaust else None})
        return out

    # Envelope

    def material(self, name):
        key = name.lower()
        for cls, fields in self.objects:
            if fields and fields[0].lower() == key and cls in ('material', 'material:nomass', 'material:airgap',
                                                               'windowmaterial:simpleglazingsystem', 'windowmaterial:glazing',
                                                               'windowmaterial:gas', 'windowmaterial:blind',
                                                               'windowmaterial:shade'):
                return material_record(cls, fields)
        raise ValueError('Unknown material '+name)

    def construction(self, name):
        """{'name', 'layers': [material records, outside first]} of a Construction."""
        key = name.lower()
        fields = next((f for c, f in self.objects if c == 'construction' and f[0].lower() == key), None)
        if fields is None:
            raise ValueError('Unknown construction '+name)
        return {'name': fields[0], 'layers': [self.material(m) for m in fields[1:] if m]}

    def envelope(self):
        """Constructions by surface class, sub-surfaces, internal mass and window shading control."""
        surfaces = self.reader.surfaces()
        hosts = {s['name'].lower(): s for s in surfaces}
        groups = {}
        for s in surfaces:
            fields = next(f for f in self.all('buildingsurface:detailed') if f[0] == s['name'])
            boundary = s['boundary']
            other = fields[6 if self.reader.version >= (9, 6) else 5] if boundary == 'zone' else ''
            klass = (s['type'], zone_kind(s['zone']), boundary_class(boundary, other), s['construction'])
            groups.setdefault(klass, 0.0)
            groups[klass] += idf_reader.area(s['vertices'])
        components = [{'surface_type': t, 'zone': z, 'boundary': b, 'construction': c, 'area_m2': round(a, 6)}
                      for (t, z, b, c), a in sorted(groups.items())]
        windows, doors = {}, {}
        old = self.reader.version < (9, 0)
        for f in self.all('window'):
            host = hosts[f[2].lower()]
            multiplier = number(f[5 if old else 4]) or 1.0
            length, height = number(f[8 if old else 7]), number(f[9 if old else 8])
            key = (zone_kind(host['zone']), f[1], host['boundary'])
            windows[key] = windows.get(key, 0.0) + length * height * multiplier
        for cls, offset in (('door', 0), ('door:interzone', 1)):
            for f in self.all(cls):
                host = hosts[f[2].lower()]
                multiplier = number(f[3 + offset]) or 1.0
                length, height = number(f[6 + offset]), number(f[7 + offset])
                key = (zone_kind(host['zone']), f[1], 'zone:'+zone_kind(f[3]) if offset else host['boundary'])
                doors[key] = doors.get(key, 0.0) + length * height * multiplier
        mass = {}
        for item in self.reader.internal_mass():
            key = (zone_kind(item['zones'][0]), item['construction'])
            mass[key] = mass.get(key, 0.0) + (item['area'] or 0.0)
        shading = []
        for cls in ('windowshadingcontrol', 'windowproperty:shadingcontrol'):
            for f in self.all(cls):
                if cls == 'windowshadingcontrol':
                    record = {'shading_type': f[3], 'shaded_construction': f[4], 'control_type': f[5], 'schedule': self.schedule(f[6])}
                else:
                    record = {'shading_type': f[1], 'shaded_construction': f[2], 'control_type': f[3], 'schedule': self.schedule(f[4])}
                shading.append(record)
        return {'components': components,
                'windows': [{'zone': z, 'construction': c, 'boundary': b, 'area_m2': round(a, 6)} for (z, c, b), a in sorted(windows.items())],
                'doors': [{'zone': z, 'construction': c, 'boundary': b, 'area_m2': round(a, 6)} for (z, c, b), a in sorted(doors.items())],
                'internal_mass': [{'zone': z, 'construction': c, 'area_m2': round(a, 6)} for (z, c), a in sorted(mass.items())],
                'window_shading': sorted(shading, key=digest)}

    def infiltration(self):
        """The source infiltration method: AirflowNetwork surface leakage or zone effective leakage areas."""
        out = {}
        components = {f[0].lower(): f for f in self.all('airflownetwork:multizone:surface:effectiveleakagearea')}
        if components:
            control = self.reader.first('airflownetwork:simulationcontrol', [])
            linked = {}
            surfaces = {s['name'].lower(): s for s in self.reader.surfaces()}
            for f in self.all('airflownetwork:multizone:surface'):
                surface = surfaces.get(f[0].lower())
                kind = (zone_kind(surface['zone']), surface['type']) if surface else ('subsurface', '')
                linked.setdefault(f[1].lower(), {}).setdefault(kind, 0)
                linked[f[1].lower()][kind] += 1
            out['airflow_network'] = {
                'control': control[1] if len(control) > 1 else None,
                'components': [{'name': f[0], 'effective_leakage_area_m2': number(f[1]), 'discharge_coefficient': number(f[2]),
                                'reference_pressure_difference_Pa': number(f[3]), 'flow_exponent': number(f[4]),
                                'surfaces': [{'zone': z, 'surface_type': t, 'count': n}
                                             for (z, t), n in sorted(linked.get(key, {}).items())]}
                               for key, f in sorted(components.items())],
                'zones': [{'zone': zone_kind(f[0]), 'ventilation_control': f[1],
                           'venting_schedule': self.schedule(f[8]) if len(f) > 8 and f[8] else None}
                          for f in self.all('airflownetwork:multizone:zone')]}
        ela = self.all('zoneinfiltration:effectiveleakagearea')
        if ela:
            out['effective_leakage_area'] = [
                {'zone': zone_kind(f[1]), 'unit': unit_of(f[1]), 'object': stem(f[0]), 'schedule': self.schedule(f[2]),
                 'effective_air_leakage_area_cm2': number(f[3]), 'stack_coefficient': number(f[4]),
                 'wind_coefficient': number(f[5])} for f in ela]
        flow = self.all('zoneinfiltration:designflowrate')
        if flow:
            out['design_flow_rate'] = [{'zone': zone_kind(f[1]), 'object': stem(f[0]), 'schedule': self.schedule(f[2]),
                                        'method': f[3], 'values': [number(v) for v in f[4:8]],
                                        'coefficients': [number(v) for v in f[8:12]]} for f in flow]
        return out

    def fenestration(self, zones=('living',)):
        """Window over gross exterior wall area by orientation for the dwelling zones (Outdoors walls only)."""
        walls, glass = {o: 0.0 for o in 'NESW'}, {o: 0.0 for o in 'NESW'}
        north = self.reader.north_axis
        hosts = {}
        for s in self.reader.surfaces():
            if s['type'] == 'wall' and s['boundary'] == 'outdoors' and zone_kind(s['zone']) in zones:
                o = idf_reader.orientation(s['vertices'], north)
                walls[o] += idf_reader.area(s['vertices'])
                hosts[s['name'].lower()] = o
        old = self.reader.version < (9, 0)
        for f in self.all('window'):
            o = hosts.get(f[2].lower())
            if o:
                multiplier = number(f[5 if old else 4]) or 1.0
                glass[o] += number(f[8 if old else 7]) * number(f[9 if old else 8]) * multiplier
        return {o: (round(glass[o] / walls[o], 6) if walls[o] else None) for o in 'NESW'}


def boundary_class(boundary, other):
    if boundary == 'zone':
        return 'zone:'+zone_kind(other)
    if boundary == 'surface':
        return 'surface'
    return boundary


def material_record(cls, f):
    """A material's SI properties under readable keys."""
    n = number
    if cls == 'material':
        return {'model': 'StandardOpaqueMaterial', 'name': f[0], 'roughness': f[1], 'thickness_m': n(f[2]),
                'conductivity_W_m_K': n(f[3]), 'density_kg_m3': n(f[4]), 'specific_heat_J_kg_K': n(f[5]),
                'thermal_absorptance': n(f[6]) if len(f) > 6 else None, 'solar_absorptance': n(f[7]) if len(f) > 7 else None,
                'visible_absorptance': n(f[8]) if len(f) > 8 else None}
    if cls == 'material:nomass':
        return {'model': 'NoMassMaterial', 'name': f[0], 'roughness': f[1], 'thermal_resistance_m2_K_W': n(f[2]),
                'thermal_absorptance': n(f[3]) if len(f) > 3 else None, 'solar_absorptance': n(f[4]) if len(f) > 4 else None,
                'visible_absorptance': n(f[5]) if len(f) > 5 else None}
    if cls == 'material:airgap':
        return {'model': 'AirGap', 'name': f[0], 'thermal_resistance_m2_K_W': n(f[1])}
    if cls == 'windowmaterial:simpleglazingsystem':
        return {'model': 'SimpleGlazing', 'name': f[0], 'u_factor_W_m2_K': n(f[1]),
                'solar_heat_gain_coefficient': n(f[2]), 'visible_transmittance': n(f[3]) if len(f) > 3 else None}
    return {'model': cls, 'name': f[0], 'fields': [n(v) if n(v) is not None else v for v in f[1:]]}


def layer_resistance(construction):
    """Sum of the layers' thermal resistances (m2K/W), without air films; None if a layer has none."""
    total = 0.0
    for m in construction['layers']:
        if m['model'] == 'StandardOpaqueMaterial' and m['thickness_m'] and m['conductivity_W_m_K']:
            total += m['thickness_m'] / m['conductivity_W_m_K']
        elif m['model'] in ('NoMassMaterial', 'AirGap'):
            total += m['thermal_resistance_m2_K_W']
        else:
            return None
    return total
