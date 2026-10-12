"""Recover the missing post-1980 triage magnitude from the official DOE scorecard.

The source workbook remains immutable in build/er-triage. --fetch retrieves only
the checksum-locked file; normal builds/checks are offline. No upstream code runs.
"""
import argparse
import hashlib
import io
import json
import math
import posixpath
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

from scripts.common import ROOT, dump_json, load_json

DATE = '2026-10-11'
PROGRAM_ID = 'program-a4ffe6755aa603f0cfcd'
OUTPUT = ROOT / 'data/program-inputs/er-triage-v1.json'
URL = 'https://data.openei.org/files/157/refbldghospitalpost1980v1.35.0si.xlsx'
SHA256 = 'ab70c78f8dd33460089470b17c858ac6b5235241def2dda1fdb0658c80611459'
SIZE = 733597
WORKBOOK = ROOT / 'build/er-triage/refbldghospitalpost1980v1.35.0si.xlsx'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
BASE = 'lib/openstudio-standards/standards/ashrae_90_1/'
POST = BASE + 'doe_ref_1980_2004/data/doe_ref_1980_2004.spc_typ.json'
PRE = BASE + 'doe_ref_pre_1980/data/doe_ref_pre_1980.spc_typ.json'
HELPER = 'lib/openstudio-standards/standards/Standards.SpaceType.rb'
HOSPITAL = 'lib/openstudio-standards/prototypes/common/buildings/Prototype.Hospital.rb'


def verified_bytes(data, expected):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Source checksum mismatch')
    return data


def workbook_cells(data):
    """Read literal OOXML cells; never mistake formula caches for source literals."""
    cells = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        strings = [''.join(node.itertext()) for node in
                   ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        rels = {r.attrib['Id']: r.attrib['Target'] for r in
                ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet', NS):
            if sheet.attrib['name'] not in ('BuildingSummary', 'ZoneSummary'):
                continue
            rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target = posixpath.normpath(posixpath.join('xl', rels[rid]))
            for cell in ET.fromstring(z.read(target)).findall('.//s:sheetData/s:row/s:c', NS):
                locator = sheet.attrib['name'] + '!' + cell.attrib['r']
                if cell.find('s:f', NS) is not None:
                    continue
                value = cell.find('s:v', NS)
                if value is None or value.text is None:
                    continue
                cells[locator] = (strings[int(value.text)] if cell.attrib.get('t') == 's'
                                  else float(value.text))
    return cells


def recover_scorecard(cells):
    required = {'BuildingSummary!C4': 'Hospital post-1980 construction',
                'ZoneSummary!A8': 'ER_Triage_Mult4_Flr_1',
                'ZoneSummary!L2': 'Elec Plug and Process (W/m2)'}
    for key, value in required.items():
        if cells.get(key) != value:
            raise ValueError('Scorecard identity/units mismatch at ' + key)
    value = cells.get('ZoneSummary!L8')
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('Missing or invalid active triage equipment magnitude')
    return value


def build_record():
    data = verified_bytes(WORKBOOK.read_bytes(), SHA256)
    if len(data) != SIZE:
        raise ValueError('Source workbook size mismatch')
    value = recover_scorecard(workbook_cells(data))
    lock = load_json(ROOT / 'sources/commercial-runtime-lock.json')
    entry = next(e for e in lock['archives'] if e['name'] == 'standards-controls')
    archive = ROOT / 'build/commercial-runtime/standards-controls.tar.gz'
    verified_bytes(archive.read_bytes(), entry['sha256'])
    inspected = []
    with tarfile.open(archive) as source:
        for path in (POST, PRE, HELPER, HOSPITAL):
            raw = source.extractfile(entry['root'] + '/' + path).read()
            item = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(),
                    'source_revision': entry['source_revision'],
                    'archive_sha256': entry['sha256']}
            if path in (POST, PRE):
                rows = json.loads(raw)['space_types']
                matches = [(i, r) for i, r in enumerate(rows)
                           if r['building_type'] == 'Hospital' and r['space_type'] == 'ER_Triage']
                if len(matches) != 1:
                    raise ValueError('Ambiguous triage source recipe')
                index, row = matches[0]
                item.update(locator=f'/space_types/{index}/electric_equipment_per_area',
                            original_value=row['electric_equipment_per_area'], original_unit='W/ft2')
                if path == POST:
                    if row['electric_equipment_per_area'] is not None:
                        raise ValueError('Source now reports triage equipment; recovery must be reviewed')
                    item['equipment_schedule'] = row['electric_equipment_schedule']
                    item['equipment_heat_fractions'] = {k: row['electric_equipment_fraction_' + k]
                                                       for k in ('latent', 'radiant', 'lost')}
            inspected.append(item)
    programs = load_json(ROOT / 'data/releases/v0.2.0/programs.json')
    program = next(p for p in programs if p['id'] == PROGRAM_ID)
    if (program['template'] != 'DOE Ref 1980-2004' or program['source_space_type'] != 'ER_Triage'
            or program['electric_equipment_W_m2'] is not None):
        raise ValueError('Frozen target identity or missing-value condition changed')
    return {
        'schema_version': '1.0.0', 'source_program_id': PROGRAM_ID,
        'status': 'recovered', 'value_W_m2': value,
        'evidence': {
            'project': 'DOE Commercial Reference Buildings / NREL',
            'source_family': 'existing_stock_benchmark',
            'source_version': 'Hospital post-1980 v1.3_5.0 SI scorecard',
            'url': URL, 'source_landing_page': 'https://data.openei.org/submissions/157',
            'sha256': SHA256, 'size_bytes': SIZE, 'extraction_date': DATE,
            'source_locator': 'ZoneSummary!L8', 'identity_locator': 'ZoneSummary!A8',
            'vintage_locator': 'BuildingSummary!C4', 'unit_locator': 'ZoneSummary!L2',
            'original_field': 'Elec Plug and Process (W/m2)',
            'original_value': value, 'original_unit': 'W/m2',
            'transformation': 'identity; preserve literal SI precision; no multiplier or area scaling',
            'interpretation': ('Magnitude-only recovery from the same DOE post-1980 Hospital benchmark. '
                               'This is an additional original DOE scorecard, not a value present in the '
                               'pinned standards JSON. Retain the standards schedule and heat fractions; '
                               'do not merge pre-1980 or code/prototype variants. No full model execution.'),
            'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
            'attribution': ('Deru, Michael, et al. Commercial Reference Building: Hospital. '
                            'National Renewable Energy Laboratory, 25 November 2014. OEDI submission 157.'),
            'source_null_preserved': True,
            'inspected_standards_sources': inspected,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.fetch and not WORKBOOK.exists():
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = verified_bytes(response.read(), SHA256)
        WORKBOOK.parent.mkdir(parents=True, exist_ok=True)
        WORKBOOK.write_bytes(data)
    result = build_record()
    if args.check:
        if load_json(OUTPUT) != result:
            raise SystemExit('ER_Triage recovery is stale; regenerate and review')
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        dump_json(OUTPUT, result)
    print(f"ER_Triage: {result['value_W_m2']} W/m2; source identity and checksums verified")


if __name__ == '__main__':
    main()
