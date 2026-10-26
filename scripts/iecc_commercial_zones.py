"""Vocabulary, locations and the zone to space-type lookup of the IECC commercial family (ADR 0040).

The PNNL IECC IDFs have no Space objects. A zone takes the standards space type of
the same-named space in the openstudio-standards geometry of the 90.1 templates
(2007, 2013 and 2019, data/construction-inputs/geometry-v1.json), read through one
lookup table keyed by atlas building type and normalized name (lower case, spaces
as underscores). Only the tags are read, never values. Where the three templates
tag a name differently, or a name has no space at all, the committed alias table
sources/iecc-commercial-zone-aliases.json decides, with a reason for each entry.
"""
from scripts.common import ROOT, load_json

GEOMETRY = ROOT/'data/construction-inputs/geometry-v1.json'
ALIASES = ROOT/'sources/iecc-commercial-zone-aliases.json'
GEOMETRY_TEMPLATES = ('90.1-2007', '90.1-2013', '90.1-2019')
EDITIONS = ('2006', '2009', '2012', '2015', '2018', '2021')
FAMILY = 'iecc_commercial_prototype'
# PNNL type name: atlas building type (plan section 5, C3)
TYPES = {
    'ApartmentHighRise': 'HighriseApartment', 'ApartmentMidRise': 'MidriseApartment', 'Hospital': 'Hospital',
    'HotelLarge': 'LargeHotel', 'HotelSmall': 'SmallHotel', 'OfficeLarge': 'LargeOffice', 'OfficeMedium': 'MediumOffice',
    'OfficeSmall': 'SmallOffice', 'OutPatientHealthCare': 'Outpatient', 'RestaurantFastFood': 'QuickServiceRestaurant',
    'RestaurantSitDown': 'FullServiceRestaurant', 'RetailStandalone': 'RetailStandalone', 'RetailStripmall': 'RetailStripmall',
    'SchoolPrimary': 'PrimarySchool', 'SchoolSecondary': 'SecondarySchool', 'Warehouse': 'Warehouse'}
# PNNL location: (AnalysisClimateZone as the IDF header writes it, atlas climate label)
# Zones 7 and 8 have no moisture regime in the IDFs; openstudio-standards assigns the same
# International Falls and Fairbanks weather to 7A/7B and 8A/8B, so the atlas labels them 7A and 8A.
CITIES = {
    'HoChiMinh': ('0A', '0A'), 'Dubai': ('0B', '0B'), 'Miami': ('1A', '1A'), 'NewDelhi': ('1B', '1B'),
    'Tampa': ('2A', '2A'), 'Tucson': ('2B', '2B'), 'Atlanta': ('3A', '3A'), 'ElPaso': ('3B', '3B'),
    'SanDiego': ('3C', '3C'), 'NewYork': ('4A', '4A'), 'Albuquerque': ('4B', '4B'), 'Seattle': ('4C', '4C'),
    'Buffalo': ('5A', '5A'), 'Denver': ('5B', '5B'), 'PortAngeles': ('5C', '5C'), 'Rochester': ('6A', '6A'),
    'GreatFalls': ('6B', '6B'), 'InternationalFalls': ('7', '7A'), 'Fairbanks': ('8', '8A')}
BASE_CITY = 'Buffalo'  # climate-independent values cite the 5A file, as the DOE reconciliation cites Chicago


def template(edition):
    return f'IECC {edition}'


def normalize(name):
    return name.strip().lower().replace(' ', '_')


def geometry_tags():
    """{(building type, normalized name): {template: (standards building type, space type)}}."""
    out = {}
    for entry in load_json(GEOMETRY)['commercial']:
        if entry['template'] not in GEOMETRY_TEMPLATES or entry['building_type'] not in TYPES.values():
            continue
        for space in entry['spaces']:
            key = (entry['building_type'], normalize(space['name']))
            out.setdefault(key, {})[entry['template']] = (space['standards_building_type'], space['standards_space_type'])
    return out


class Lookup:
    """The single zone lookup table: geometry tags, conflicts resolved and guesses added by the alias table."""

    def __init__(self, aliases=None):
        aliases = aliases or load_json(ALIASES)
        tags = geometry_tags()
        self.table, self.origin = {}, {}
        resolved = {(a['building_type'], normalize(a['zone'])): a for a in aliases['conflicts']}
        for key, found in sorted(tags.items()):
            distinct = sorted(set(found.values()))
            if len(distinct) == 1:
                self.table[key] = distinct[0]
                self.origin[key] = 'geometry'
                continue
            entry = resolved.pop(key, None)
            if entry is None:
                raise ValueError(f'Zone name maps to several space types and the alias table does not decide: {key} {distinct}')
            chosen = (entry['standards_building_type'], entry['space_type'])
            if chosen not in distinct:
                raise ValueError(f'Alias choice is not one of the tagged space types: {key}')
            self.table[key] = chosen
            self.origin[key] = 'alias_conflict'
        if resolved:
            raise ValueError('Alias conflicts that are no longer conflicts: '+', '.join(map(str, sorted(resolved))))
        for entry in aliases['guesses']:
            key = (entry['building_type'], normalize(entry['zone']))
            if key in self.table:
                raise ValueError(f'Alias guess for a name the geometry already tags: {key}')
            self.table[key] = (entry['standards_building_type'], entry['space_type'])
            self.origin[key] = 'alias_guess'
        self.check()

    def check(self):
        """No normalized name maps to two space types (plan section 5, C1)."""
        seen = {}
        for key, value in self.table.items():
            if seen.setdefault(key, value) != value:
                raise ValueError(f'Zone name maps to two space types: {key}')

    def __call__(self, building_type, zone):
        key = (building_type, normalize(zone))
        if key not in self.table:
            raise KeyError(f'No space type for zone {zone!r} of {building_type}; add a reasoned guess to {ALIASES.name}')
        return self.table[key]


def conflict_candidates():
    """The names the three templates tag differently, for writing the alias table."""
    return {key: found for key, found in geometry_tags().items() if len(set(found.values())) > 1}
