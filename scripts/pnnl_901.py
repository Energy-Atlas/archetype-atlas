"""Reading the PNNL ASHRAE 90.1 prototype IDFs for the release 2.4.0 inputs (ADR 0060).

The IDFs sit outside the repository (`ATLAS_PROTOTYPE_ROOT`, default `D:/Prototype Building Models`, pinned by
`sources/reference-models-lock.json`). A zone takes the standards space type its 90.1 template's geometry tags it with
(`scripts.lighting_controls.template_tags`, as ADR 0044 groups them), so a zone group is one atlas program: the program
of that space type in the folder of the type. Every value is read from the 19 location files of a template and must
agree in all of them; the evidence cites the Buffalo (5A) file, as ADR 0044 and ADR 0053 do.
"""
import math
from collections import defaultdict
from pathlib import Path

from scripts import idf_reader
from scripts.definition_contract import stable_id
from scripts.iecc_commercial_values import zones
from scripts.iecc_commercial_zones import BASE_CITY, CITIES, TYPES
from scripts.lighting_controls import Extract as ControlsExtract, prototype_root, template_tags

FAMILY = 'commercial-ashrae901'
YEARS = ('2007', '2013', '2019')
EXTRACTION_DATE = '2026-11-01'
ADR = 'docs/adr/0060-release-2-4-0-pnnl-prototype-corrections.md'


class Extract(ControlsExtract):
    """Source files and evidence rows (program-shaped: source_file_id, locator, ..., interpretation)."""

    def __init__(self, root=None):
        super().__init__(Path(root or prototype_root()))

    def cite(self, source_file, locator, value, unit, transformation, note):
        row = {'source_file_id': source_file, 'locator': locator, 'original_value': value, 'original_unit': unit,
               'transformation': transformation, 'extraction_date': EXTRACTION_DATE, 'interpretation': note}
        key = stable_id('evidence', row)
        self.evidence[key] = {'id': key, **row}
        return key


def path(root, pnnl, year, city):
    return Path(root)/FAMILY/f'ASHRAE901_{pnnl}'/f'ASHRAE901_{pnnl}_STD{year}_{city}.idf'


def require(root, pnnl, year):
    folder = Path(root)/FAMILY/f'ASHRAE901_{pnnl}'
    if not folder.is_dir():
        raise SystemExit(f'No PNNL 90.1 prototype IDFs under {folder}; set ATLAS_PROTOTYPE_ROOT')
    missing = [c for c in CITIES if not path(root, pnnl, year, c).is_file()]
    if missing:
        raise SystemExit(f'Missing {pnnl} STD{year} IDFs for {missing}')


class Models:
    """The 19 location models of one type and 90.1 edition, with the zones grouped by space type."""

    def __init__(self, extract, pnnl, year, keep=None):
        root = extract.root
        require(root, pnnl, year)
        self.pnnl, self.year = pnnl, year
        self.building_type, self.template = TYPES[pnnl], f'90.1-{year}'
        self.models = {city: idf_reader.Model(path(root, pnnl, year, city)) for city in CITIES}
        self.base = self.models[BASE_CITY]
        self.geometry = zones(self.base)
        self.file = extract.prototype_file(FAMILY, path(root, pnnl, year, BASE_CITY))
        tags = template_tags(year)
        self.space = {z: tags(self.building_type, g['name']) for z, g in self.geometry.items()}
        self.groups = defaultdict(list)
        for z in sorted(self.geometry):
            self.groups[self.space[z][1]].append(z)

    def area(self, zone):
        g = self.geometry[zone]
        return g['floor_m2']*g['multiplier']

    def group_area(self, zones_):
        return math.fsum(self.area(z) for z in zones_)

    def name(self, zone):
        return self.geometry[zone]['name']

    def folder(self):
        from scripts.atlas_format import slug
        return f'commercial/{slug(self.template)}/{slug(self.building_type)}'


def same_everywhere(values, what):
    """The value of the base city, required equal in every city."""
    base = values[BASE_CITY]
    differ = sorted(c for c, v in values.items() if v != base)
    if differ:
        raise ValueError(f'{what} differs from {BASE_CITY} in {differ}')
    return base
