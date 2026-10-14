# ADR 0017: Portable Python schedule resources and explicit sampling context

Status: Accepted for the M1 source foundation, 2026-10-14. Kernel and shipment
validation remain separate gates.

The atlas supplies deterministic energy semantics for zoning experiments. Its
frozen definitions, reviewed variants and annual reference targets remain
immutable. A portable stochastic realization needs inspectable calibration
tables, explicit conditional selectors and source transformations rather than
an installed OpenStudio/Ruby runtime or a recreated population sample.

## Decision

`atlas_schedules` uses strict finite JSON resources with schema version 1.0.0.
The six resource kinds are `residential`, `commercial`, `weather`, `program`,
`composition` and `reference`. Each JSON record has an inventory entry containing
its relative path, resource kind/key, byte count and SHA-256. The resource-set
identity is SHA-256 of the canonical manifest without its own identity field.
Canonical resource bytes are UTF-8, sorted JSON keys, compact separators and a
terminal LF. Array order remains source-significant. Destination paths never
enter identity. The loader requires the expected identity and rejects changed,
missing, extra, duplicate or unsafe members before returning copies of records.
This byte integrity rule applies to immutable resources, not floating-point
generator results. Schedule IDs percent-escape each instance/slot separately.

Source extraction verifies whole archive and selected-member bytes. It validates
all archive paths and forbids links/devices, including unselected members. It
never imports or executes upstream sampler/Ruby code. Ordered tables retain raw
strings, parsed finite values and source-row/column locators. Explicit SI
counterparts carry unit/multiplier receipts where the source defines a quantity.
Raw numerical tables remain available for upstream draw/transform fidelity;
unknowns are null and are never changed to zero. Frozen program evidence and
source-file receipts retain per-field original values, units and transformations.
Local execution-cache paths in residential metadata are omitted as null, with
that transformation recorded. Public upstream notices remain packaged.

The exact ten-case M1 manifest has its configuration/template/weather bindings
locked independently of generated resource directories. Source and reviewed
views remain distinct. `source_gate_passed_not_shipped` certifies resource
availability, not completed schedules or resolution of unknown load magnitudes.
Later kernel, resolution, numerical-comparison and release gates must pass all
ten cases and included channels. Other catalogue families remain visibly outside
this extraction scope rather than being included in a reduced denominator.

## Commercial sampling decision

`medium_office_90_1_2013` is an atlas experimental hybrid: frozen 90.1-2013
definition/reference targets plus ComStock temporal distributions. It does not
assert an upstream run with that configuration name or a stock-template match.
Use the public v33 archive at ComStock revision
`3c103063c0debb177a200dd1df8406b8d0f8d515`. Pinned archive-addition/update commit
receipts establish its kitchen-equipment inventory's compatibility with the
pinned sampler groups. This is an explicit policy selection; `national.yml`
uses a nonpublic precomputed path and does not identify its TSV version.
Public integration CSV evidence supplies the declared 2018 stock metadata
context. It does not condition the selected temporal rows.

All ten selected schedule parameters condition only on the explicitly supplied
`building_type=medium_office` and sampled start-time/ratio-type dependencies.
Region, size, stock year, vintage and weather are absent from this closure.
Medium Office interior parametric operating-hours/base-peak transforms are
weather-independent. Six residential weather inputs retain their exact station
proxy labels and hashes; they are not equivalent to unavailable county EPWs.

The actual commercial transform dependency is the declared RubyGems
`openstudio-standards=0.8.6` package, verified against the registry SHA-256.
It is distinct from the Standards development revision that produced frozen
atlas reference definitions. Relevant create-typical and schedule methods and
the package's own notice are retained as inspectable evidence.

The per-parameter audit records selected source rows/options, dependency closure,
full resolved groups, allocated dimensions and vector positions with/without
the official precomputed allocation-column context. The population sampler has
no seed argument or internal initialization in the inspected file. Exact row
replay additionally needs sample count/index, bucket layout, previous draws and
results, allocation row/column ordering, NumPy global state and, for Sobol,
sequence implementation plus Python shift and pandas shuffle states. Unknown
population values remain null. No population RNG equivalence is asserted.

The permitted standalone policy is `atlas_conditional_seeded_v1`: derive a
Python `random.Random` seed from the unsigned big-endian SHA-256 digest of
canonical `[policy_name, master_seed, operating_group]`; consume one 53-bit
uniform per parameter, including degenerate distributions, in the audited source
vector order, once per coordinated operating group. Conditional selection uses
the first raw cumulative probability strictly greater than the supplied draw.
The resource compiler accepts source decimal totals within 1e-6 but preserves
every raw probability. No normalization or tail option is invented. A draw
outside a subunit raw CDF must fail explicitly. Event-duration probability CSV
validation separately uses its recorded decimal quantization bound.

Some unselected hospital/car-wash v33 duration rows sum to zero. Compile only
rows matching the locked `medium_office` selector; do not advertise those other
contexts or silently repair them. The complete original archive stays immutable.

## Consequences

Generation can run from packaged Python resources without network or source
checkout imports. Source transforms and conditional selections are compared at
identical explicit parameters/draws; wrapper determinism is tested separately.
Annual-total conservation is a later atlas policy based on emitted schedules
and effective magnitude, separate from unmodified ComStock behavior. Changing
TSV version, selectors or RNG policy requires a versioned resource/sampling
policy; frozen annual reference targets remain fixed. Named comparison
tolerances and exported CSV quantization are recorded in
`sources/schedule-generator-policy.json`.

Reproduce with `python -m scripts.schedule_generator_sources --verify-only` and
`python -m scripts.schedule_generator_build --scope pilot --destination <empty>`.
Large sources have locked public retrieval URLs and hashes, and are not committed.
