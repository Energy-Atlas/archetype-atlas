"""Read EnergyPlus input files as data, for the DOE reference and PNNL prototype models.

Covers the field layouts of EnergyPlus 5.0 and 7.2 (DOE reference v1.3 and v1.4)
and 9.x to 22.x (PNNL prototypes):
- BuildingSurface:Detailed gained a Space Name field after Zone Name in 9.6;
- FenestrationSurface:Detailed lost its Shading Control Name field in 9.0.
Vertex lists are read as the trailing numbers of an object, so the "Number of
Vertices" field may be a count, blank or autocalculate. Zone origins apply when
GlobalGeometryRules says coordinates are relative. Files are parsed as text and
never executed.
"""
import math
import re
from pathlib import Path

ORIENTATIONS = ('N', 'E', 'S', 'W')
LOAD_CLASSES = ('people', 'lights', 'electricequipment', 'gasequipment', 'hotwaterequipment',
                'steamequipment', 'otherequipment')


def parse(text):
    """Return [(class in lower case, [fields])] in file order, comments removed."""
    text = re.sub(r'!.*', '', text)
    result = []
    for chunk in text.split(';'):
        fields = [f.strip() for f in chunk.split(',')]
        if fields and fields[0]:
            result.append((fields[0].lower(), fields[1:]))
    return result


def number(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def vertices(fields, first):
    values = [float(v) for v in fields[first:] if number(v) is not None]
    return [tuple(values[i:i + 3]) for i in range(0, len(values) - 2, 3)]


def newell(points):
    n = [0.0, 0.0, 0.0]
    for i, (x1, y1, z1) in enumerate(points):
        x2, y2, z2 = points[(i + 1) % len(points)]
        n[0] += (y1 - y2) * (z1 + z2)
        n[1] += (z1 - z2) * (x1 + x2)
        n[2] += (x1 - x2) * (y1 + y2)
    return n


def area(points):
    return 0.5 * math.sqrt(sum(c * c for c in newell(points)))


def orientation(points, north_axis_deg=0.0):
    """Compass orientation (N, E, S, W) of a wall's outward normal."""
    nx, ny, _ = newell(points)
    azimuth = (math.degrees(math.atan2(nx, ny)) + north_axis_deg) % 360
    return ORIENTATIONS[int(((azimuth + 45) % 360) // 90)]


class Model:
    """One IDF file with typed access to the objects the reconciliation compares."""

    def __init__(self, path):
        self.path = Path(path)
        self.objects = parse(self.path.read_text(errors='replace'))
        self.version = self._version()
        self.north_axis = number(self.first('building', [None, '0'])[1], 0.0)
        rules = self.first('globalgeometryrules', [])
        self.relative = len(rules) > 2 and rules[2].lower() == 'relative'
        self.zones = {f[0].lower(): self._zone(f) for f in self.all('zone')}
        self.zone_lists = {f[0].lower(): [z.lower() for z in f[1:] if z] for f in self.all('zonelist')}

    def _version(self):
        text = self.first('version', ['0'])[0]
        parts = [int(p) for p in re.findall(r'\d+', text)[:2]]
        return tuple(parts + [0] * (2 - len(parts)))

    def all(self, cls):
        return [f for k, f in self.objects if k == cls]

    def first(self, cls, default):
        return next((f for k, f in self.objects if k == cls), default)

    def _zone(self, f):
        origin = tuple(number(v, 0.0) for v in f[2:5]) if self.relative else (0.0, 0.0, 0.0)
        multiplier = int(number(f[6], 1) or 1) if len(f) > 6 else 1
        return {'name': f[0], 'origin': origin, 'multiplier': multiplier}

    def _shift(self, zone, points):
        ox, oy, oz = self.zones[zone.lower()]['origin'] if zone and zone.lower() in self.zones else (0, 0, 0)
        return [(x + ox, y + oy, z + oz) for x, y, z in points]

    def surfaces(self):
        """BuildingSurface:Detailed as dicts with absolute vertices."""
        has_space = self.version >= (9, 6)
        result = []
        for f in self.all('buildingsurface:detailed'):
            boundary = f[5 if has_space else 4].lower()
            first = 11 if has_space else 10
            result.append({'name': f[0], 'type': f[1].lower(), 'construction': f[2], 'zone': f[3],
                           'boundary': boundary, 'vertices': self._shift(f[3], vertices(f, first))})
        return result

    def fenestration(self):
        """FenestrationSurface:Detailed as dicts; vertices are absolute via the host's zone."""
        hosts = {s['name'].lower(): s for s in self.surfaces()}
        old = self.version < (9, 0)
        result = []
        for f in self.all('fenestrationsurface:detailed'):
            host = hosts.get(f[3].lower())
            multiplier = number(f[8 if old else 7], 1.0) or 1.0
            points = vertices(f, 10 if old else 9)
            if host:
                points = self._shift(host['zone'], points)
            result.append({'name': f[0], 'type': f[1].lower(), 'construction': f[2], 'host': f[3],
                           'host_type': host['type'] if host else None, 'zone': host['zone'] if host else None,
                           'multiplier': multiplier, 'vertices': points})
        return result

    def zone_names(self, target):
        """Expand a zone or zone-list name into zone names (lower case)."""
        key = target.lower()
        return self.zone_lists.get(key, [key])

    def loads(self, cls):
        """Internal-gain objects with the fields shared by all covered versions."""
        result = []
        for f in self.all(cls):
            item = {'name': f[0], 'zones': self.zone_names(f[1]), 'schedule': f[2], 'method': f[3].lower(),
                    'values': [number(v) for v in f[4:7]], 'fields': f}
            if cls == 'people':
                item['fraction_radiant'] = number(f[7]) if len(f) > 7 else None
                item['sensible_fraction'] = f[8] if len(f) > 8 else None
                item['activity_schedule'] = f[9] if len(f) > 9 else None
            elif cls == 'lights':
                item['fractions'] = {'return_air': number(f[7]), 'radiant': number(f[8]),
                                     'visible': number(f[9]), 'replaceable': number(f[10]) if len(f) > 10 else None}
                item['subcategory'] = f[11] if len(f) > 11 else ''
            else:
                item['fractions'] = {'latent': number(f[7]) if len(f) > 7 else None,
                                     'radiant': number(f[8]) if len(f) > 8 else None,
                                     'lost': number(f[9]) if len(f) > 9 else None}
                item['subcategory'] = f[10] if len(f) > 10 else ''
            result.append(item)
        return result

    def infiltration(self):
        result = []
        for f in self.all('zoneinfiltration:designflowrate'):
            result.append({'name': f[0], 'zones': self.zone_names(f[1]), 'schedule': f[2], 'method': f[3].lower(),
                           'values': [number(v) for v in f[4:8]],
                           'coefficients': [number(v) for v in f[8:12]]})
        return result

    def internal_mass(self):
        return [{'name': f[0], 'construction': f[1], 'zones': self.zone_names(f[2]), 'area': number(f[3])}
                for f in self.all('internalmass')]

    def materials(self):
        """Opaque and glazing materials keyed by lower-case name."""
        result = {}
        for f in self.all('material'):
            thickness, conductivity = number(f[2]), number(f[3])
            result[f[0].lower()] = {'kind': 'material', 'thickness': thickness, 'conductivity': conductivity,
                                    'density': number(f[4]), 'specific_heat': number(f[5]),
                                    'resistance': thickness / conductivity if thickness and conductivity else None}
        for f in self.all('material:nomass'):
            result[f[0].lower()] = {'kind': 'nomass', 'resistance': number(f[2])}
        for f in self.all('material:airgap'):
            result[f[0].lower()] = {'kind': 'airgap', 'resistance': number(f[1])}
        for f in self.all('windowmaterial:simpleglazingsystem'):
            result[f[0].lower()] = {'kind': 'simple_glazing', 'u_factor': number(f[1]), 'shgc': number(f[2]),
                                    'visible_transmittance': number(f[3]) if len(f) > 3 else None}
        for f in self.all('windowmaterial:glazing'):
            result[f[0].lower()] = {'kind': 'glazing', 'fields': f[1:]}
        for f in self.all('windowmaterial:gas'):
            result[f[0].lower()] = {'kind': 'gas', 'fields': f[1:]}
        return result

    def constructions(self):
        """Constructions keyed by lower-case name: layers (outside first) or F/C-factor values."""
        result = {f[0].lower(): {'kind': 'layers', 'layers': [x.lower() for x in f[1:] if x]}
                  for f in self.all('construction')}
        for f in self.all('construction:ffactorgroundfloor'):
            result[f[0].lower()] = {'kind': 'ffactor', 'f_factor': number(f[1]), 'area': number(f[2]),
                                    'perimeter': number(f[3])}
        for f in self.all('construction:cfactorundergroundwall'):
            result[f[0].lower()] = {'kind': 'cfactor', 'c_factor': number(f[1]), 'height': number(f[2])}
        return result

    def layer_resistance(self, construction):
        """Sum of layer resistances (m2K/W) without air films, or None if a layer has none."""
        item = self.constructions().get(construction.lower())
        if not item or item['kind'] != 'layers':
            return None
        materials = self.materials()
        total = 0.0
        for layer in item['layers']:
            r = materials.get(layer, {}).get('resistance')
            if r is None:
                return None
            total += r
        return total

    def schedules(self):
        return {f[0].lower(): f for f in self.all('schedule:compact')}

    def holidays(self):
        return [(f[0], f[1]) for f in self.all('runperiodcontrol:specialdays')]
