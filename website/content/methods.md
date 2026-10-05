# Methods and validation

The site is a generated presentation of frozen atlas releases. It does not
modify canonical records, fill missing fields or establish simulation readiness.
Each release has its own schema, source lock, manifest and stable record URLs.

An explicitly selected resolution supplement appears separately on v0.2.0
record pages. It contains executed residential profiles and narrowly reviewed
zero/inactive assumptions. Original nulls remain visible. Missing or positive
loads, electric HVAC alone, and support-space names do not automatically justify
zero. Reviewed attic/plenum conditioning uses explicit disabled states; no
arbitrary thermostat temperature is presented as a source fact.

The supplement has a separate version/schema, base-manifest hash, field evidence
and complete artifact inventory. The site verifies schema, reproducible rules,
profile/CSV equality, source input context, SI units, annual lengths, bounds and
thermostat consistency before rendering it. Execution provenance describes
station-proxy weather, fixed seeds/calendar, nominal setpoints and unresolved
controls. See the supplement downloads for exact policy and upstream notices.

## Data integrity

Before generating pages, the build verifies every manifest file's SHA-256 and
size, the release inventory, canonical record counts, frozen schema and
structural/physical/referential/provenance checks.

The upstream atlas pipeline separately validates source comparisons and
reproducibility before release. Supporting reports and the exact schema are
included in the frozen snapshot download. The site build requires no raw-source
authentication and executes no downloaded generator code.

Canonical numerical fields use the units in the release metadata. Source
attributes, generator arguments and conditional efficiency metrics preserve
their original meaning and units; they are not automatically normalized.
Specialized refrigeration/process evidence includes explicit unit uncertainty.

## Schedule interpretation

Schedule rows preserve source order, date ranges, day selectors, design days,
constant/hourly type and original units. The explorer expands constant profiles
to 24 hours, without interpolation. Among date-applicable rules, the last
matching specific rule wins, then the last default supplies fallback.

DummySmrDsn is displayed verbatim and matches summer design-day inspection,
following the documented pinned Standards generator. A missing profile is
reported as unavailable. Profile values are not interpolated or filled with zero.
The browser's selector is checked against the atlas Python inspection helper.

The month/day control uses the reference leap year 2000 solely for valid
date selection. It does not infer weekdays, weather, holidays, DST or an annual
8760 calendar. Those require an explicit downstream calendar policy.

## Public delivery

Source text is escaped as inert evidence. Browser metadata and record downloads
use the release's existing privacy projection; unrelated demographic fields
excluded by extraction are not recovered from raw sources.
Interactive filtering and plotting use local assets. Exact source notices
and a checksum-locked Plotly MIT notice are distributed with the site.

Internal links, fragments, project-subpath assets, filters and representative
charts are checked before producing a GitHub Pages artifact.
