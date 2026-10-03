"""Deterministic ResStock fixture configurations, without unexecuted defaults."""
import collections
import csv

from scripts.common import stable_id
from scripts.semantics import option_rows, convert

HEIGHT_TYPES = {
    'Single-Family Detached': 'SingleFamilyDetached',
    'Single-Family Attached': 'SingleFamilyAttached',
    'Multi-Family with 2 - 4 Units': 'MultiFamily2To4',
    'Multi-Family with 5+ Units, 1-3 Stories': 'MultiFamily5PlusLowRise',
    'Multi-Family with 5+ Units, 4-7 Stories': 'MidriseApartment',
    'Multi-Family with 5+ Units, 8+ Stories': 'HighriseApartment',
    'Mobile Home': 'ManufacturedHome',
}
CONTEXT = ['Geometry Building Type RECS', 'Geometry Building Type Height',
           'Geometry Floor Area', 'Geometry Stories', 'Geometry Building Number Units MF',
           'Geometry Building Number Units SFA', 'ASHRAE IECC Climate Zone 2004', 'Vintage']


def fixture_rows(builder):
    with (builder.raw_root/'resstock'/builder.selection['residential_fixture']).open(
            encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def selected_pairs(builder):
    text = (builder.raw_root/'resstock/resources/options_lookup.tsv').read_text(encoding='utf-8')
    parameters = {cols[0] for _, cols, _ in option_rows(text)}
    return {(key, value) for row in fixture_rows(builder) for key, value in row.items() if key in parameters}


def add_configurations(builder):
    index = collections.defaultdict(list)
    for row in builder.data['residential_options']:
        index[row['parameter'], row['option']].append(row['id'])
    text = (builder.raw_root/'resstock/resources/options_lookup.tsv').read_text(encoding='utf-8')
    known_pairs = {(c[0], c[1]) for _, c, _ in option_rows(text)}
    parameters = {k for k, _ in known_pairs}
    path = builder.selection['residential_fixture']
    for i, raw in enumerate(fixture_rows(builder)):
        selected = {k: v for k, v in raw.items() if k in parameters}
        ids, unresolved, no_arguments = [], [], []
        for parameter, option in selected.items():
            pair = (parameter, option)
            if pair not in known_pairs:
                unresolved.append({'parameter': parameter, 'option': option,
                                   'reason': 'No exact option in pinned lookup; no replacement inferred'})
            elif pair not in index:
                no_arguments.append({'parameter': parameter, 'option': option})
            else:
                ids.extend(index[pair])
        record = {
            'id': stable_id('residential_archetype', 'resstock', path, raw['Building']),
            'building_type': HEIGHT_TYPES[raw['Geometry Building Type Height']],
            'template': builder.selection['residential_template'],
            'source_family': 'existing_stock_source_fixture',
            'variant': 'source_building_' + raw['Building'],
            'source_building_id': raw['Building'],
            'source_context': {k: raw[k] for k in CONTEXT},
            'selected_options': selected, 'option_ids': sorted(set(ids)),
            'unresolved_options': unresolved, 'non_argument_options': no_arguments,
            'occupants': float(raw['Occupants']),
            'heating_base_C': convert(float(raw['Heating Setpoint'].removesuffix('F')), 'F'),
            'cooling_base_C': convert(float(raw['Cooling Setpoint'].removesuffix('F')), 'F'),
            'thermostat_base_overlap': float(raw['Heating Setpoint'][:-1]) > float(raw['Cooling Setpoint'][:-1]),
            'conditioned_floor_area_m2': None,
            'simulation_ready': False,
            'runtime_gaps': [
                'Complete ResStock/HPXML generation, argument translation and defaults not executed',
                'Floor-area bin retained; no exact area or density invented',
                'Thermostat bases precede offsets, seasons and unavailable-day overrides',
                'Schedules require pinned generator defaults/calendar or explicit profiles',
                'Fixture options absent from pinned lookup require source reconciliation',
            ],
        }
        specs = {
            'building_type': ('Geometry Building Type Height', 'source class', 'explicit height-class crosswalk'),
            'source_building_id': ('Building', 'source fixture ID', 'identity; public modeled input, not an address'),
            'source_context': ('source row', 'source-specific units', 'retain selected physical/climate/vintage context'),
            'selected_options': ('source row', 'option labels', 'retain every lookup-defined parameter; other survey metadata excluded'),
            'option_ids': ('source row', 'option labels', 'exact parameter/option join to all argument-bearing lookup rows'),
            'unresolved_options': ('source row', 'option labels', 'enumerate unmatched lookup-defined options without substitution'),
            'non_argument_options': ('source row', 'option labels', 'enumerate exact options without measure arguments'),
            'occupants': ('Occupants', 'person/unit', 'parse explicit fixture value'),
            'heating_base_C': ('Heating Setpoint', 'F', 'parse F label and convert to C; pre-offset base only'),
            'cooling_base_C': ('Cooling Setpoint', 'F', 'parse F label and convert to C; pre-offset base only'),
            'thermostat_base_overlap': ('source row', 'F', 'compare raw heating/cooling bases; flag unresolved overlap before seasonal controls'),
            'conditioned_floor_area_m2': ('Geometry Floor Area', 'ft2 bin', 'withhold exact area; source reports a bin'),
        }
        energy_source = {'Building': raw['Building'], **{k: raw[k] for k in CONTEXT}, **selected}
        builder.add('residential_archetypes', record, 'resstock', path,
                    f'CSV row {i+2}; Building={raw["Building"]}', energy_source, specs,
                    'Deterministic source fixture configuration, not a population representative. '
                    'Only exact lookup bindings are applied as references. Source families remain '
                    'separate from code apartment programs. Unresolved options and runtime defaults '
                    'prevent claims of simulation readiness. Source-row provenance is projected '
                    'onto energy and physical context fields; no demographic survey columns exported.')
