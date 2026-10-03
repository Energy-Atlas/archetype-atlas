# Choose energy semantics

The catalogue contains deterministic source inputs for zoning-LOD experiments.
It does not supply geometry, stock sampling weights or calibrated energy results.

1. Open the catalogue for the release you intend to cite.
2. Select a building type and commercial template, or a residential configuration.
3. Inspect the source family. Code/prototype editions and existing-stock evidence
   answer different questions; a code year is not the age of a building.
4. Follow the programs and systems actually referenced by the entry.
5. Inspect schedules, ventilation, infiltration and unresolved fields.
6. Choose envelope predicates separately: climate set, surface/construction type,
   building category and any percentage, orientation or projection limits.
7. Download the exact records and retain release IDs and source provenance.
8. Resolve the documented missing inputs before generating a simulation.

## Browse by several axes

The catalogue offers a search and filters, plus static tables for building,
program, vintage/template, climate, system, source and data status. All views
link to the same release-specific record pages. Filter URLs can be shared.
Shared schedules match building/template filters through real referencing
records; this does not create new schedule variants.

Climate labels remain exact. A thermal-only envelope set such as ClimateZone 4
and a moisture-specific set such as ClimateZone 4A are different source
predicates. Unspecified program climate means no climate-specific assignment.
Residential fixture climate is reported context, not a weather file.

## Nulls, literal options and status

**Unknown / not reported** means canonical null. It never implies zero.
Numerical zero is displayed as zero. A source option named **None** remains a
literal option and must be interpreted through its arguments and provenance.

Coverage means a named typology has source inputs. It does not mean a complete,
simulation-ready building exists. Conditional rules require their predicates;
unassigned efficiency metrics are not a system COP.

## Trace and cite

Use the Evidence link beside a field to inspect its original unit/value,
transformation, source locator, revision and extraction date. Record JSON
downloads include provenance and source metadata. Frozen snapshot archives
include the manifest, schemas, source lock, notices and supporting evidence.
Retain upstream attribution; original atlas code and documentation are unlicensed.
