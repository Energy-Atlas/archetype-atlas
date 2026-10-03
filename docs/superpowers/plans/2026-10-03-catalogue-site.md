# Archetype catalogue site content and delivery plan

**Goal:** Present the versioned energy atlas as a searchable research catalogue,
with multiple browsing axes, complete record details, provenance and interactive
schedule exploration, built with MkDocs and published through GitHub Pages.

**Audience:** Researchers and model builders choosing deterministic energy
semantics for zoning-LOD experiments. Readers should be able to find an entry,
understand its applicability and missing inputs, inspect the evidence, and
download the exact versioned records needed downstream.

**Scope:** Content and delivery planning only. No site implementation or deployment
is authorized by this document alone. The request asks for a plan.

**Architecture:** Generate catalogue pages and compact browser data from a chosen
frozen release. Maintain explanatory guides by hand. MkDocs produces static HTML;
browser JavaScript supplies filters and plots. Canonical JSON remains the data
authority. Presentation views do not change the atlas schema or scientific values.

**Proposed stack:** MkDocs, Material theme, a small catalogue filtering layer and
Plotly.js schedule charts. Pin compatible versions and retain asset license
notices when implementing. Build and publish using GitHub Actions Pages artifacts.

**Governing specification:** docs/AGENT_RESEARCH_BRIEF.md and AGENTS.md.

## 1. Baseline and scientific rules

The current checkout is research/first-release (v0.1.0). The complete-coverage
branch and v0.2.0 tag are available. The site should start from frozen v0.2.0,
selected explicitly during its build, rather than silently using the working
directory's processed data. Older releases remain accessible through versioned
URLs and a version selector.

v0.2.0 supplies 17 commercial typologies, 83 commercial building/template
combinations, 768 program records, 569 schedule records, and 41 residential
configurations across seven classes. Counts on the site must be generated from
the selected release manifest, not copied into hand-maintained site prose.

- Preserve existing-stock, code/prototype, source-fixture and option/rule evidence
  distinctions. A code edition is not automatically the age of existing stock.
- Preserve climate-independent program records. A climate filter must distinguish
  directly reported climate context, conditional applicability and unspecified
  applicability; it cannot imply that a complete climate-specific model exists.
- Display SI units for normalized values. Show original units/values separately.
  Source arguments and ambiguous specialized units remain source evidence.
- Null remains unknown/unreported/unresolved, never zero. Do not treat literal
  source option labels such as None as canonical null without interpretation.
- Display all available necessary inputs and explicitly list missing inputs.
  Site publication does not establish simulation readiness.
- Every record/plot is traceable to release, record ID and source provenance.

## 2. Site navigation and content ownership

| Section | Purpose | Content source |
| --- | --- | --- |
| Home | Research purpose, current release, coverage summary, prominent catalogue link | Curated explanation; generated counts |
| Catalogue | One page of linked tables grouped by different browsing axes; shared filters | Generated release index |
| Entries | Building/template and residential configuration detail pages | Generated release relationships |
| Reference library | Program, schedule, envelope, system, efficiency and specialized rule pages | Generated canonical records |
| Compare | Side-by-side compatible entries and schedule overlays | Generated data and browser state; second stage |
| How to use | Meaning of an archetype, selection workflow, assigning semantics to geometry, worked examples | Curated guides |
| Methods and validation | Schema, units, extraction, checks, confidence and scientific limitations | Existing documentation adapted for readers |
| Sources | Source projects, pinned versions, notices and field provenance | Lock, provenance and source documentation |
| Downloads and releases | JSON/CSV, manifests, checksums, release notes and citation information | Versioned release assets |

Keep the sidebar short. Record-level pages should be discoverable through the
catalogue, search and links, rather than placing thousands of records in navigation.

## 3. Catalogue: one page, multiple views

The main catalogue page has a text search, release selector, record-kind selector,
and shared filters. Its sections/tabs provide tables of links organized by axis:

| Browsing axis | What the table lists | Interpretation |
| --- | --- | --- |
| Building type | Offices, schools, healthcare, retail, hotels, apartments and residential classes | Links to building overviews and available variants |
| Program | Office, apartment unit, guest room, corridor, dining, kitchen, support, etc. | Links to distinct program records; source-specific variants stay separate |
| Vintage/template | DOE reference vintages, code editions, residential source vintages | Separate template classification from reported stock vintage |
| Climate | Envelope climate sets and residential reported climate context | Thermal-only sets and moisture-specific sets retain their original labels |
| System | Source system types and conditional equipment evidence | Unknown fuel, COP or terminal values stay visible |
| Source/family | Standards, ComStock, ResStock and benchmark/code interpretations | Attribution reflects actual extracted inputs, including Standards-derived DOE/PNNL coverage |
| Data status | Available inputs, conditional rules, unresolved inputs, simulation readiness | Separate source verification from complete model readiness |

Each table shows relevant counts, descriptive entry links and a short scope note.
Selecting an axis changes organization, not the identity of the underlying page.
All filters have shareable URL state, a clear reset action and an informative
empty-result state. Plain linked tables remain usable when JavaScript is disabled.

Default entry-table columns: name, record kind, building/program, template or
stock vintage, source family, climate basis, data status and details link. Secondary
columns such as system type and key load values appear only where meaningful.
Do not present inapplicable columns as unexplained blanks.

Example path: Catalogue -> Medium Office -> 90.1-2013 -> office program ->
occupancy/lighting/thermostat schedules. A climate selection then links to the
corresponding conditional envelope records; it does not rewrite office loads.

## 4. Entry types and granularity

1. **Building/template overview:** one overview for each of the 83 commercial
   combinations. It collects program rows, system definitions, mapping groups,
   relevant rule evidence and unresolved assembly steps. It is a source-input
   bundle, not a claimed complete simulation configuration.
2. **Residential configuration:** one page for each of the 41 deterministic
   fixture configurations. Show joint selections and exact option references,
   source context, unmatched options, thermostat bases and runtime gaps.
3. **Atomic reference record:** one stable page per program, schedule, envelope
   component, system or rule. Shared records are rendered once and linked from
   every referring entry. Option records may use a parameter/option library page
   with stable record anchors to avoid excessive tiny pages.
4. **Category overview:** explains a building/program/climate/template category
   and lists its available entries. Category pages provide research context;
   source-specific distinctions remain on the detail pages.

Use release-prefixed URLs and stable record IDs. Friendly titles aid reading;
record identity never relies solely on a title slug. An example pattern is
`releases/v0.2.0/programs/<record-id>/`. Preserve older URLs as releases grow.

## 5. Standard detail-page content

Every detail page uses the same reading order, adapted to its record kind:

| Page block | Required content |
| --- | --- |
| Identity | Descriptive title, release/schema version, ID, source family, building/program, template/variant |
| Applicability | Climate basis, source conditions, where the inputs can be used, dependencies and exclusions |
| Data status | Inputs reported versus missing; conditional rule/evidence labels; validation level and readiness |
| Internal loads | Occupancy, lighting, additional lighting, electric/gas equipment, units and linked schedules |
| Controls and schedules | Occupancy, load and thermostat schedule plots; source rules and exceptions |
| Ventilation and infiltration | Per-area, per-person and ACH components; pressure/basis; unresolved methods |
| Envelope | Relevant components and limits/targets, source predicates, films, U/SHGC/VT and interpretation |
| HVAC and systems | Source descriptors, availability/OA schedules, assignments and qualified efficiency rules |
| Mapping context | Source space names, benchmark multiplicity, floor-area flags, unknown area fractions/conditioned state |
| Specialized inputs | Refrigeration, healthcare or other process evidence, generator dependencies and unit uncertainty |
| Provenance | Source repository/path/revision, locator, original fields/units/values, transformations and notes |
| Reuse | Record JSON, inspection CSV where supported, related records, stable link and citation snippet |

Only include applicable blocks; mark required-but-unresolved input groups
explicitly. Do not render missing numerical values as zero in tables or plots.
Provenance can be expandable, with field-level links from displayed values.
Browser data and downloads must exclude the unrelated residential demographic
fields already excluded by v0.2.0 extraction and provenance projection.

## 6. Interactive visualizations

The first site release should prioritize schedule exploration:

- **Daily fractional profiles:** occupancy, lighting, electric/gas equipment,
  and relevant availability schedules. Step plots, clear legends and units;
  allow overlay, hover values, series toggling and image/data export.
- **Thermostat profiles:** heating and cooling on a separate temperature plot;
  show deadband/overlap and distinguish bases from effective schedules.
- **Controls:** choose a date and concrete day type, including weekday/weekend,
  holiday and winter/summer design day. Show the matching ordered source rules
  and the selected effective profile. Preserve original labels such as
  DummySmrDsn and explain the pinned generator interpretation.
- **Seasonal inspection:** expose date ranges and changed rules. This can be a
  rule timeline; a synthetic annual profile is not necessary for the first site.
- **Residential limitation:** where complete schedules are unavailable, show
  reported bases, offsets and source arguments with an explicit unavailable
  schedule state. Do not borrow commercial apartment profiles or invent curves.

Later plots can compare program loads across templates, envelope U/SHGC values
across matched climate/category predicates, and conditional equipment ratings by
capacity. Comparisons must use compatible units and applicability. Do not average
competing envelope rules or treat SEER, EER and COP as interchangeable.

Every chart has a linked underlying table and a static/accessibility fallback.
Plot data should load only when required. Fraction, temperature, activity and
power-density series should not share an unlabeled or misleading axis.

An annual heatmap/8760 export is a later feature, gated on an explicit year,
holiday calendar, leap-year and DST policy, and validated schedule precedence.
An energy-result plot requires simulation results; the input atlas cannot supply it.

## 7. Supporting guides and reader journey

First guides:

- What this atlas provides and how source-input coverage differs from readiness.
- How to select a building, program, template, climate and system context.
- Units, nulls, conditional rules, source families and provenance explained.
- Medium Office worked example, from catalogue selection to record downloads.
- Multifamily worked example separating code programs from ResStock recipes.
- How to assign energy semantics to a separate geometry/zoning generator.
- How to reproduce, cite and compare atlas releases; license notices and terms.

Primary journey: find -> inspect applicability -> inspect parameters/schedules ->
check unresolved inputs -> inspect provenance -> download/cite. The interface
should make the unresolved-input check easy at the point of selection.

## 8. Generation, versioning and GitHub Pages

Generate the site from a release manifest plus canonical tables. Keep curated
prose separate from generated content. Publish compact record payloads instead
of loading the complete provenance file into every browser page. Render source
code and text as escaped inert evidence; never execute downloaded generator code.

The deployment build should verify release hashes, generate the catalogue/pages,
run a strict MkDocs build, check links and browser plots, and produce a static
Pages artifact. A deployment job publishes that tested artifact. Check project
subpath behavior, such as `/archetype-atlas/`, for assets, filters and downloads.
Use pinned assets and GitHub Actions revisions, the Pages deployment environment
and minimal deployment permissions. Pull requests build previews/artifacts;
release publication is a separate action from authoring this plan.

Pin the site publication to a release tag; show the selected release on every
page. Version-specific URLs remain stable, while a clearly labeled latest alias
may point to the newest published release. Data downloads should reproduce the
record selection, preserve upstream notices and include release/manifest identity.

## 9. Delivery sequence and acceptance criteria

- [ ] **Pilot:** implement the catalogue layout and Medium Office/90.1-2013
  overview, office program and its schedule pages. Add one residential recipe
  and one conditional envelope record to verify uncertainty handling.
  Acceptance: every displayed value/plot matches the release; links and source
  traceability work; missing residential schedules are not fabricated.
- [ ] **Complete catalogue:** generate all category views, commercial overviews,
  residential entries and atomic libraries. Add search, filters and shareable
  state. Acceptance: generated counts match manifests; no orphan record links;
  the same record has the same URL from every browsing axis.
- [ ] **Schedule explorer and comparison:** add effective-profile inspection,
  source-rule display and compatible entry overlays. Acceptance: constant/hourly,
  seasonal, holiday and design-day behavior matches validated source semantics;
  units and nulls remain correct and fallbacks work.
- [ ] **Reader documentation and downloads:** publish selection examples,
  methods, provenance, coverage, release notes and citation/download support.
  Acceptance: a researcher can find and interpret a configuration without
  inspecting repository code; all runtime gaps are visible.
- [ ] **Publish:** pin dependencies and Actions, validate a release build and
  deploy to GitHub Pages. Acceptance: live links/assets work under the repository
  subpath; mobile/keyboard navigation and plot loading work; version identity
  and old release links are preserved.

## 10. Boundaries of the initial site

The first implementation provides discovery, inspection and reproducible record
downloads. A complete model configurator, EnergyPlus execution, statistical stock
sampling and automatic resolution of missing inputs are later research features.
Custom domain, analytics and public feedback workflows are optional later work.

The content architecture does not require new scientific assumptions. Any future
feature that creates new parameter values or claims model compatibility must
follow the governing brief's source, validation and versioning requirements.

## Primary technical references

- [MkDocs static deployment](https://www.mkdocs.org/user-guide/deploying-your-docs/)
- [Material table customization](https://squidfunk.github.io/mkdocs-material/reference/data-tables/)
- [Plotly.js line charts](https://plotly.com/javascript/line-charts/)
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
