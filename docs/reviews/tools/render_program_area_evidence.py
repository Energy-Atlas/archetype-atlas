import json, hashlib
from pathlib import Path
from collections import defaultdict
root=Path(__file__).resolve().parents[3]; data=json.loads((root/'build/reviews/program-area-evidence.json').read_text())
base=root/'data/releases/v0.2.0'; out=root/'docs/reviews/program-aggregation-evidence.md'
by_building=defaultdict(list)
for m in data:by_building[m['building_type']].append(m)
paths=sorted({m['geometry'] for m in data}); gid={p:f'G{i:02}' for i,p in enumerate(paths,1)}
templates=[('E-pre','DOE Ref Pre-1980'),('E-post','DOE Ref 1980-2004'),('C07','90.1-2007'),('C13','90.1-2013'),('C19','90.1-2019')]
resolved=[m for m in data if m['denominator_m2'] is not None]
lines=['# Source-area evidence for program aggregation','',
 'Inspection date: 2026-10-06. Companion to the editable [decision matrix](program-aggregation-matrix.md).',
 'Status: **source inspection; numerical area evidence, not released mixed energy presets**.','',
 '## What this inventory contains','',
 f'- All {sum(len(m["rows"]) for m in data)} commercial program records in atlas `v0.2.0`, organized into {sum(len({r["source_space_type"] for m in ms for r in m["rows"]}) for ms in by_building.values())} building/source-space-label combinations across {len(by_building)} building types.',
 f'- {len(data)} selected building/template contexts using {len(paths)} distinct geometry files, each verified against its locked SHA-256.',
 f'- Calculable counted-floor-area shares for all {len(resolved)} contexts. The earlier 16 unresolved contexts are now resolved using the matching OpenStudio 2.2.1 source default, with the original blank fields preserved as evidence.',
 '- Five commercial templates kept separate. No averaging of templates, stock variants or source families.',
 '- ResStock has 41 separate dwelling fixtures in this release. They are not commercial room programs and have no extracted internal room-area composition. Keep these dwelling bundles separate from the selected commercial apartment family; no internal room aggregation is inferred.','',
 'The commercial tables are OpenStudio Standards source inputs and geometry implementations. Their relationship to ComStock is upstream lineage, not proof that each table reproduces a particular ComStock generated model or its current ratio rules. Equivalence to independently downloaded DOE/PNNL IDFs has not been established.','',
 '## Reading the tables','',
 '| Column / marker | Meaning |', '| --- | --- |',
 '| E-pre | DOE Ref Pre-1980, existing-stock benchmark family |',
 '| E-post | DOE Ref 1980-2004, existing-stock benchmark family |',
 '| C07 / C13 / C19 | ASHRAE 90.1-2007 / 2013 / 2019, code/prototype rules family |',
 '| Numeric cell | Percent of the counted floor area of that exact source building/template; three-decimal inspection rounding |',
 '| NC | Source spaces are explicitly outside counted floor area; not zero energy or absent space |',
 '| U | Reserved for an unresolved denominator; none remain after the documented source-default check |',
 '| — | This source program or building context is absent in the frozen selection; not a zero share |','',
 'A whole-building fraction is not a target-program recipe weight. For the approved member subset with areas A_i, its internal weights are A_i / sum(A_i). Use the decision matrix for actual membership. The source tables retain basement/attic shares for provenance, but every approved mixture excludes those programs and renormalizes over its eligible members. Basement/attic presets remain optional and separate. A building-wide PACU or corridor area need not all belong to a selected department.',
 'Variant names such as top-floor, occupied/vacant, or tenant type do not by themselves establish subordinate uses that should be blended. Keep alternatives explicit.','',
 '## Method and provenance','',
 'Original values: source `OS:Surface` Floor vertex X/Y/Z tuples in metres, `OS:Space` Part of Total Floor Area Yes/No or blank flags, exact standards building/space tags on `OS:SpaceType`, and `OS:ThermalZone` dimensionless multipliers. Blank flags are interpreted only through the matching versioned source rule below; raw files are unchanged.',
 'Source locator for each table cell: the listed geometry file and all `OS:Space` objects whose linked `OS:SpaceType` exactly matches the row\'s Standards Building Type and Standards Space Type; join their `OS:Surface` floors through Space Name/handle and their thermal zones through Thermal Zone Name/handle. A plenum without a building tag uses the extractor\'s explicit `Any` convention. The exact source file revision and SHA-256 are in the lock table below.',
 'Transformation: sum planar floor polygon areas using the full XYZ coordinates, multiply each unique space\'s zone multiplier once, include effective Yes spaces (explicit or source-defaulted), group by exact source tags, and divide by the sum over all effective Yes spaces in the selected model. HVAC mappings are not summed; the same space can have multiple HVAC services. Use unrounded areas to compute any eventual recipe.',
 'Interpretation: source-model benchmark composition only, not a required architectural ratio, population weight, BEMGen plan geometry, or claim of weather-independent controls. Different templates may reuse a geometry file while having different energy semantics.',
 f'Validation on 2026-10-06: {len(paths)} file checksums passed; all {sum(len(m["rows"]) for m in data)} program records matched their source tags; no explicitly counted space was left without a canonical program. Positive counted-space areas and multipliers were checked. Unrounded grouped areas equaled each of the {len(resolved)} complete building denominators within relative tolerance 1e-10. Rounding may leave displayed totals slightly different from 100%.','',
 'Reproduce from the repository root with `python -m docs.reviews.tools.extract_program_area_evidence` then `python -m docs.reviews.tools.render_program_area_evidence`. Retrieve the geometry locks with `python -m scripts.fetch` first if the cache is absent. The extractor verifies/fetches the [matching SDK defaults](source-default-lock.json) through checksum-locked retrieval. The calculation uses the existing [floor-polygon reader](../../scripts/water_reporting.py) and [tagged space reader](../../scripts/semantics.py). Raw downloads remain immutable. No canonical table or delivery packet was changed.','',
 'Canonical energy inputs and IDs for a cell can be found in [programs.json](../../data/releases/v0.2.0/programs.json) by exact `building_type`, `template`, `source_building_type`, and `source_space_type`. Source field locators, original energy values/units and transformations are in [provenance.json](../../data/releases/v0.2.0/provenance.json). This is the source view; a reviewed supplemental view must be chosen explicitly for a final recipe.','',
 'Input file checksums for this inspection:','', '| Input | SHA-256 |','| --- | --- |']
for p in [base/'programs.json',base/'source_files.json',root/'sources/selection.json']:
 rel=p.relative_to(root).as_posix();lines.append(f'| [{rel}](../../{rel}) | `{hashlib.sha256(p.read_bytes()).hexdigest()}` |')
lines += ['', '## Building/program inventory','']
for b,ms in sorted(by_building.items()):
 lines += [f'### {b}','', '| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |', '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
 types=sorted({r['source_space_type'] for m in ms for r in m['rows']})
 for typ in types:
  sb=sorted({r['source_building_type'] for m in ms for r in m['rows'] if r['source_space_type']==typ});cells=[]
  for code,t in templates:
   m=next((m for m in ms if m['template']==t),None)
   rows=[r for r in m['rows'] if r['source_space_type']==typ] if m else []
   assert len(rows)<=1
   r=rows[0] if rows else None
   cells.append('—' if r is None else ('U' if r['area_status']=='unresolved_floor_flags' else ('NC' if r['area_status']=='not_counted' else f'{r["share_percent"]:.3f}')))
  lines.append('| `'+typ+'` | '+', '.join('`'+s+'`' for s in sb)+' | '+' | '.join(cells)+' |')
 lines += ['', '| Context | Geometry lock | Counted building floor area, m² |', '| --- | --- | ---: |']
 for code,t in templates:
  m=next((m for m in ms if m['template']==t),None)
  if m:lines.append(f'| {code} | {gid[m["geometry"]]} | '+(f'{m["denominator_m2"]:.6f}' if m['denominator_m2'] is not None else 'U')+' |')
 lines.append('')
lines += ['## Resolved floor-area defaults','',
 'The previous U markers were an extraction limitation, not proof that geometry or usable area shares were missing. All seven affected OSM files declare version 2.2.1. At OpenStudio revision `0a5e9cec3f9e57872c44b1e074e9a625cfd9531b` (v2.2.1), the model IDD defaults Part of Total Floor Area to Yes. Space.cpp applies that default to a blank field unless the thermal zone is a supply/return plenum. ThermalZone.cpp defines that exception by actual plenum connections, not by an architectural room name. No supply/return plenum objects exist in the seven affected geometry files; explicit No fields are still excluded. Thus all previously blank fields in these files resolve to Yes. This is a source-defined default, not an empirical area assumption.',
 '', '| Matching source rule | SHA-256 |', '| --- | --- |']
for p in ['Space.cpp','ThermalZone.cpp','OpenStudio.idd']:
 raw=root/'data/raw/openstudio-221'/p
 src='openstudiocore/resources/model/'+p if p.endswith('.idd') else 'openstudiocore/src/model/'+p
 url='https://github.com/NatLabRockies/OpenStudio/blob/0a5e9cec3f9e57872c44b1e074e9a625cfd9531b/'+src
 lines.append(f'| [{src}]({url}) | `{hashlib.sha256(raw.read_bytes()).hexdigest()}` |')
lines += ['', '## Geometry source locks','', 'All files below come from OpenStudio Standards revision `c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907`. Source license notices are retained in [the source notice](../../sources/licenses/openstudio-standards.txt). The links locate original source values; local raw caches are retrieval artifacts, not new delivery files.','', '| Lock | Pinned source geometry | SHA-256 |','| --- | --- | --- |']
for p in paths:
 m=next(m for m in data if m['geometry']==p)
 url=f'https://github.com/NatLabRockies/openstudio-standards/blob/{m["source_revision"]}/{p}'
 lines.append(f'| {gid[p]} | [{p}]({url}) | `{m["sha256"]}` |')
lines += ['','## Annotation boundary','', 'Edit membership, target weights and decisions in [the main matrix](program-aggregation-matrix.md). This companion records source evidence and should not be edited to make a desired recipe appear source-reported. If a ratio is chosen as an experimental assumption, record it as an assumption with its rationale in the main matrix.','']
out.write_text('\n'.join(lines),encoding='utf-8')
print('Written',out,'lines',len(lines),'bytes',out.stat().st_size)
print('Complete contexts',len(resolved),'unresolved contexts',len(data)-len(resolved))
