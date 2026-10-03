"""Shared serialization and schema constants."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0'
UNITS = {
    'people_per_m2': 'person/m2', 'lighting_W_m2': 'W/m2',
    'additional_lighting_W_m2': 'W/m2', 'electric_equipment_W_m2': 'W/m2',
    'gas_equipment_W_m2': 'W/m2', 'ventilation_m3_s_m2': 'm3/s/m2',
    'ventilation_m3_s_person': 'm3/s/person', 'ventilation_ach': '1/h',
    'infiltration_m3_s_m2': 'm3/s/m2', 'u_W_m2_K': 'W/m2/K',
    'shgc': 'dimensionless', 'visible_transmittance': 'dimensionless',
    'area_fraction': 'dimensionless', 'multiplicity': 'count',
}
TABLES = ['programs', 'schedules', 'envelope_components', 'systems', 'mappings',
          'efficiency_rules', 'residential_options', 'commercial_options', 'provenance', 'source_files']


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_atlas(path):
    path = Path(path)
    if path.is_dir():
        data = load_json(path/'metadata.json')
        data.update({t: load_json(path/(t+'.json')) for t in TABLES})
        return data
    return load_json(path)


def dump_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n',
                    encoding='utf-8', newline='\n')


def stable_id(namespace, *parts):
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
    return namespace + '-' + digest
