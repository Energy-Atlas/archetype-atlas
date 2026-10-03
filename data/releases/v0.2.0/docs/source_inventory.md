# Source inventory and interpretation

Checked 2026-10-02. Machine-readable inventories are in
`sources/inventory.json`, `sources/parameter_matrix.csv`, `sources/selection.json`,
and `sources/lock.json`. The lock pins three repositories by full commit SHA and
each downloaded blob by SHA-256, length, URL and path. Branch names are discovery
metadata only; rebuilds never follow a floating branch. The repositories now use
the `NatLabRockies` organization; older NREL links may redirect.

The [ComStock repository](https://github.com/NatLabRockies/ComStock) has options,
stock characteristic tables, and generator measures. Its typical-building
measure requires OpenStudio Standards. This establishes a dependency, not proof
that this independently pinned standards commit matches a ComStock release.
Selected option/measure rows, including continuation measures, are retained as
commercial evidence. No stock distributions are sampled or used as weights.

The [ResStock repository](https://github.com/NatLabRockies/resstock) maps stock
options to measure arguments in `resources/options_lookup.tsv` and includes
OpenStudio-HPXML defaults. Explicit options provide thermostat, occupants,
infiltration, lighting, plug-load and heating-system evidence. They need unit
area, adjacency, equipment and schedule/default configurations before they can
become complete deterministic dwelling models. Mid/high-rise apartment program
support in v0.1.0 comes from standards benchmark inputs; it is not mislabeled as
a sampled ResStock multifamily model.

[OpenStudio Standards](https://github.com/NatLabRockies/openstudio-standards)
contains template space-type tables, a common schedule database, conditional
construction tables, prototype descriptors, HVAC maps and OSM standards tags.
The atlas directly extracts these inputs. Unit definitions were checked in the
pinned `Standards.SpaceType.rb`, `Standards.People.rb` and schedule generator.
The complete source row remains available for secondary parameters and
conditions that the atlas has not given canonical SI fields.

The [DOE reference-building inventory](https://www.energy.gov/cmei/buildings/commercial-reference-buildings)
separates new construction, pre-1980 and post-1980 existing-building models. Its
[pre-1980 page](https://www.energy.gov/cmei/buildings/existing-commercial-reference-buildings-constructed-1980)
describes packages and historical updates. Its linked Medium Office target
`https://www.energy.gov/cmei/articles/reference-buildings-building-type-medium-office-0`
returned HTTP 404 in this session. Standards DOE template inputs are retained
as a separate implementation of reference semantics, not a verified byte-for-byte
extraction from DOE's distributed IDFs.

The [DOE/PNNL prototype inventory](https://www.energycodes.gov/prototype-building-models)
describes new-construction/code models and downloadable IDF/output/scorecard
packages. The linked `2023-10/ASHRAE901_OfficeMedium_STD2013.zip` returned HTTP 404
on direct retrieval. It is recorded as an unresolved benchmark download, not
included in the blob lock or falsely reported as inspected. Standards template
rules are separately named. Future benchmark ingestion must pin package bytes,
check redistribution terms, parse IDFs against their EnergyPlus version, and
compare final generated inputs after controls and overrides.

## License handling

All three mirrored repository license notices are retained byte-for-byte under
`sources/licenses/`. ResStock's bundled HPXML notice is also retained. Sources
have permissive redistribution terms with attribution/notice obligations; the
atlas does not claim sponsorship or use the OpenStudio(R) name as its product
name. Original code/docs remain unlicensed by user choice. No DOE/PNNL ZIPs or
scorecards were redistributed. No service needs authentication for this workflow.

## Current extraction selection

All 17 commercial types in the union of the official DOE Reference and PNNL
commercial lists are selected through exact pinned prototype_inputs entries.
Five templates retain their existing-stock versus code-rule families. Highrise
Apartment is absent in the two DOE Reference templates: 83 combinations, not 85.
Climate sets remain at source granularity; weather and standard edition are external.

ResStock's project_national/resources/sdr_minimal_buildstock.csv supplies 41
joint source configurations. Exact argument-bearing lookup rows are referenced;
unmatched selections remain explicit. Five RECS classes and three 5+-unit height
groups cover seven residential classes. These are public modeled input selections,
not inferred population representatives; unrelated demographic columns are excluded.

Twenty-five refrigeration tables and four generator files add conditional compressor/condenser/system/walk-in
source evidence. The expanded lock has 160 files at the same three revisions.
