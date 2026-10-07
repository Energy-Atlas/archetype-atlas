# DTO JSON v2: inspectable objects and schedule visualization

Date: 2026-10-07.
Branch: `feature/dto-json-v2`.
Starting commit: `c1538e341c29ab82537addf8dddaab89ebd53bfa`.
Status: proposed design; experimental defaults authorized by the user. The
requested connector contract is recorded in `docs/program-json-v2-contract.md`
before site implementation.

## Intent and constraints

Make the atlas useful as a library a user can inspect and copy into a downstream
consumer. Keep the Residential / Non Residential entry gate and Programs /
Constructions / HVAC systems selection. Supporting objects are reached through
their references. Every object has inspectable JSON and a copy interaction;
schedules additionally have interactive day profiles and annual heatmaps.

All work stays local. Do not push, dispatch GitHub workflows, merge main, or
perform the previous plan's Task 11. Local commits are allowed after inspecting
the staged diff and passing the staged security audit.

The user's latest instructions supersede the earlier requirement to preserve
historical site URLs, downloads and v1 delivery compatibility. Remove obsolete
site output rather than generate archive notices, redirects or retained delivery
history. Keep canonical research inputs, immutable source files, and required
upstream notices in the repository: retirement concerns publication, not erasing
the evidence from which current objects are reproduced.

## Existing data and gaps

The current definition release has 1,900 programs, 3,798 constructions, 1,046
HVAC systems, and 4,410 schedules: 3,907 rule-based and 503 annual. The current
UI has primary-object pages, lazy supporting-resource disclosures, Copy ID,
daily schedule rule selection, and annual residential line plots. Supporting
objects currently do not have dedicated definition pages or Copy JSON.

The legacy site generator still emits old release catalogues, supplements,
generator explanations, downloads and delivery v1; the home page and navigation
still describe those releases. Retiring navigation alone would not remove them
from the generated site or search index.

Nulls include physical inputs, optional applicability selectors, properties of
other material models, and original source evidence. These categories cannot
share an unconditional replacement rule. For example, an opaque material does
not require a glazing SHGC, and a missing schedule reference cannot be replaced
with the number zero. No filled copy may alter canonical source evidence.

## Publication boundary

Generate the active site directly from the current verified definition bundle.
The active routes are home, catalogue gates/finders, object pages, concise
selection/JSON/schedule guides, source/provenance notices and current delivery.
Remove obsolete release pages, supplements, old catalogues, historical download
trees, delivery v1 and retained inactive v2 snapshots from generated output.
Do not replace removed URLs with redirects or archival placeholders.

Use a fresh staging tree so local history caches cannot repopulate retired
files. Stop legacy generation in the active build path, rather than generating
all old pages and deleting them afterward. Preserve immutable retrieval locks
and reproduction scripts needed to build the active data. Remove retired
navigation, search entries, links and smoke expectations together. Publish source
license notices through current source pages without linking old download trees.

## Object inspection and raw JSON

Primary and supporting objects have stable, linkable detail pages with a readable
name, kind, identity, applicable context, physical values and missing-input
status. Loads, schedule references, construction layers, materials, system
components, services and mixture members link to the designated objects. Distinct
references remain distinct; do not treat every string ending in ID as an object
link unless it is present in the verified object registry.

Each page has an expandable JSON section and a Copy JSON button. For programs,
the JSON view uses the complete self-contained connector DTO, including nulls
and embedded schedules; original canonical evidence remains separately traceable.
Raw/defaulted DTO modes are defined in `docs/program-json-v2-contract.md`. Other
objects retain their full raw definition representation. Fetch large records lazily,
verify size and SHA-256 before displaying them, and share the verified record
between plots and copying. Do not expose a projected query result as the complete
object. JSON is rendered as text and never inserted as executable HTML.

Copy JSON opens an accessible popup with two explicit choices:

1. Copy raw JSON: copy the same complete object shown in the JSON section.
2. Copy with defaults: show the applicable default policy, substitutions and
   remaining requirements, then copy a separately identified consumer export.

Keyboard focus moves into the popup, Escape cancels, focus returns to its trigger,
and clipboard success/failure is announced. If clipboard permission is unavailable,
provide selectable JSON. Never report success before the clipboard operation
completes. Do not write directly into a downstream application in this scope.

## Default-filled export: decision boundary

Canonical objects and their raw copy remain unchanged. Default-filled output
must identify its policy version and list the exact field paths and assumptions
applied. It is a consumer artifact, not a new source-reported measurement; keep
its identity and status distinct from the canonical definition. The on-page
physical summary continues to say Unknown for source unknowns.

The user authorized a documented atlas-wide experimental policy, including
nonzero physical assumptions where zero is invalid. The user chooses only raw
or default-filled JSON in the popup. Values, rationale, compatible units and
scope are recorded in `sources/program-json-defaults.json`; do not add per-field
configuration questions to that interaction.

Classify null fields by semantic role. Optional
metadata, unreported provenance and parameters of inactive material models are
not missing simulation inputs. Required references need valid referenced objects,
not empty strings or zero IDs. Any generated default schedule has a reproducible
definition, identity and assumption record. A zero load may not require a
nonzero-use profile, but it must not erase a known positive component or shared
service. Do not fill source-evidence subtrees or change mixture memberships.

Geometry, assignment and model sizing remain external responsibilities. Validate
the export against its schema, physical constraints and reference closure. Report
remaining requirements explicitly. The phrase simulation-ready is permitted only
for the supported object contract when those checks pass, not as a claim that a
complete building model has been created.

## Schedule pages

Display units, resolution, source/calendar context, rule dates and day selectors.
Rule-based schedules preserve original ordering and the existing documented rule
selection semantics. Group identical numeric day profiles for display without
merging or reordering canonical rules. Label the contributing rules and preserve
holiday and winter/summer design-day profiles separately.

Provide interactive step plots for unique day profiles and an annual heatmap
with day of year on one axis and hour of day on the other. Hover exposes the date,
time interval, value, unit and selected rule/profile. Selecting a heatmap day
shows its exact daily curve. Keep exact-value tables available when plotting or
JavaScript fails.

For rule-based schedules, require a visible calendar year; choose a deterministic
documented preview year and permit the user to change it. Include leap years,
wrapped seasonal ranges and explicit day-of-week resolution. Holidays are applied
only when an explicit holiday calendar is supplied; otherwise state that the
preview has no holiday overrides. Design days are displayed separately from the
ordinary annual preview. Missing coverage is a gap, never zero.

Existing annual schedules use their recorded year and timestep. Do not remap
2007 realizations to another year or regenerate stochastic profiles. Unique day
grouping uses exact values, with a compact selectable list when an annual
realization contains many unique days. Do not plot hundreds of curves by default.
Retain original interval conventions, seed and weather-proxy limitations.

Use a locally served, version-pinned Plotly bundle supporting both scatter and
heatmap traces. Lock its SHA-256 and size and retain its license. Load it only
on pages with charts. No runtime CDN dependency or backend is required.

## Validation and delivery

Start with Medium Office, one construction/material chain, one HVAC/component
chain, and one recorded residential annual schedule. Then generate full coverage.
Test reference closure and full raw-copy equivalence, default-policy substitutions
and exclusions, popup keyboard/clipboard behavior, and lazy verification errors.
Test schedule precedence, seasons crossing New Year, leap days, holidays, design
days, constant rules, missing intervals and recorded-year restrictions.

Build locally with strict MkDocs validation. Check links, retired route absence,
search contents, notice availability, output size and object coverage. Run browser
checks for navigation, JSON copying, step plots, heatmap interaction and mobile
layout. Keep the final verification local; no GitHub workflows are needed.

Record findings, autonomous decisions, default-policy evidence and remaining
limitations in a durable execution log. Final handoff reports the local branch,
checks run and any unsupported default-filled exports.
