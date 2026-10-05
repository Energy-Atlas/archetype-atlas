# Schedule supplement v0.4.0 and commercial-completion v0.1.0

Both releases explicitly extend immutable atlas v0.2.0. Source nulls remain
unchanged; consumers must select the resolved variant. Original work remains
unlicensed; upstream source notices accompany each bundle.

- All 574 assessed residential profile fields are supplied for 41 fixtures.
- Fixed selected-equipment defaults cover 40 refrigerators and 19 freezers;
  23 absent appliances have explicit zeros. Missing stochastic columns alone
  never establish appliance absence.
- The three vacant fixtures have 25 newly reviewed operational zeros, plus
  three exterior-lighting zeros. Upstream zero-occupant methods were executed;
  selected refrigeration remains active.
- Dwelling exterior lighting has 38 positive fixed defaults, verified against
  all 8,760 upstream application hours. Shared multifamily services remain separate.
- Eight pinned source-phase executions establish inactive direct conditioning
  for 19 exact programs, resolving 38 thermostat fields. Evidence is pre-sizing
  at climate 4A, not a full-model simulation or proof of no passive heat transfer.
- Commercial water evidence covers 217 draw paths, 28 recipes and 83
  building/template pairs. Source/normalized fractions and compatible SI flows
  conserve draw. Existing programs receive only supported serving assignments.
- Complete source absence closes 206 water gaps. The remaining 279 program-water
  assignments concern 59 unallocated main/booster/laundry service paths.
- Active commercial coverage is 4,859/5,138 fields (94.6%); residential assessed
  coverage is 574/574. Attic, plenum and basement records are outside the milestone.
- Sampled HVAC equipment-unavailability, complete load magnitudes and full-model
  controls remain excluded. The excluded transportation end use has no active
  schedules, catalogue entries, plots or coverage denominator. Archived source
  snapshots remain unchanged for provenance.

Validation includes schema, SI/physical bounds, references, ordered schedule
selectors/design days, allocation and interval conservation, finite source proofs,
runtime receipt matching and frozen inventory hashes. Fresh source retrieval
reproduced the completion packet; independent repeated freezes reproduced all
13 completion and 114 supplement files byte-for-byte. Exact manifests:

- Completion: `8826553abf7b0f123592542ec48807ead76d2a178ad299a1c83ed5b3db5b2ec5`
- Supplement: `129a5a4939e333e7fc541b610da4d2e6d58b53029188a553a5f5c6c1c229be61`

Reproduction commands and runtime boundaries are in
[ADR 0008](adr/0008-reviewed-schedule-completion.md) and the
[site build guide](site-build.md). A full-stock, direct DOE/PNNL generated-model
equivalence or simulation-readiness claim is not made. Parametric generator
shipping remains after deterministic data coverage.
