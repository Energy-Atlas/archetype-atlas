# ADR 0018: Preserve source RNG and bounded calendar semantics

> Amended by ADR 0035 (2026-10-17): the semantic decisions stand; bit-level exactness, authority locks and certification ceremony are superseded.

- Status: Accepted for the source-gated schedule-generator pilot
- Date: 2026-10-14

## Decision and evidence

`atlas_schedules.ruby_random.SourceRandom` ports the locked runtime's Ruby 3.2.2
MT19937 initialization, 53-bit exclusive uniform, and bounded-integer rejection
algorithm. Python `random.Random` is not a substitute. Ruby uses one-word
initialization for small seeds, array initialization for larger integers, and
removes a leading word equal to one before array initialization. Derived native
unit seeds are not capped at 64 bits. State is a versioned object with the
original seed, 624 unsigned 32-bit state words, and next-word index 0 through 624.
The words and index are exactly compared with independent Ruby marshal state.

The explicit master remains unsigned 64-bit. Unit order uses the source's
cumulative `seed *= (position + 1)` in
`BuildResidentialScheduleFile/measure.rb:162` at ResStock revision
`dd25369f41a83a0767aefeeac0b6f8a0b0edd649`; 42 therefore gives 42, 84, 252.
Insertion, removal and reordering change allocation. `source_streams(unit_seed)`
returns main and the original six streams from `resources/schedules.rb:127-133`,
in order hygiene, dishwasher, clothes_washer, clothes_dryer, ev, cooking. EV
still reserves a seed even though its outputs are excluded. Main occupancy and
appliance/water coupling stay with their upstream stream; this helper does not
introduce new per-appliance streams.

Commercial allocation is separately named `atlas_conditional_seeded_v1`:
`commercial_group_seed(master, operating_group)` converts the full SHA-256
of canonical `[policy, master, operating_group]` to an unsigned big-endian integer.
The commercial kernel receives this integer and must not hash it again. This is
the already approved conditional adaptation in the sampling audit; it is not a
claim of population replay and is not the residential RNG.

`evaluate_rules(schedule, year, holidays)` consumes inspected frozen source
objects, preserves their array order, month/day selectors and constant/hourly
step profiles, and returns 8,760 values. It rejects leap years, malformed or
out-of-year holidays, unknown selectors and unsupported interpolation. The
adapter follows the pinned `Standards.Model#model_add_schedule` and
`model_add_vals_to_sch`: later-created specific rules have higher priority,
Default rows set the default day independently of rule dates, and only actual
winter/summer design selectors produce special profiles. Design profiles do
not enter annual integrals. The source method does not create a holiday profile
from a Hol row; unused Hol metadata is preserved in the caller's input object.
Explicit holiday dates select the source default day. No implicit holiday, DST,
timezone conversion, residential activity rule, or residential design day is
introduced.

Two actual commercial source objects lack a Default row. Their source-created
empty OpenStudio default ScheduleDay evaluates to zero, independently captured
for an explicit holiday. That is recorded runtime behavior, not an unknown-to-zero
inference. Only objects carrying inspected Standards Constant/Hourly type tags
receive that empty-default behavior. Untyped companion objects without a source
default or full specific coverage fail closed.

## Provenance, verification and rebuilding

`sources/schedule-generator-reference-lock.json` pins Ruby's official v3_2_2
`random.c`, `missing/mt19937.c`, BSDL and COPYING bytes, the actual Standards model
method at revision `c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907`, source ResStock methods,
and the independent capture checksum. The runtime archive is independently
locked in `sources/runtime-lock.json`. The capture stores source locators, original
operation results and units, transformations, extraction date and interpretation.
Upstream Ruby/MT notices are retained in `sources/licenses/ruby-random.txt` and
packaged as `reference/notice-ruby-random`.

The opt-in `python -m scripts.schedule_generator_reference` command requires
explicit verified runtime, ResStock and Standards archive paths, the pinned Ruby
source cache, and a new destination. It extracts only bin, Ruby, lib and notices
to its own destination before executing. It never executes another worktree's
files and does not run during normal package generation. A candidate capture and
candidate lock are written to that destination; existing captures are not
silently overwritten. Source-cache filenames are source paths with `/` replaced
by `__`. Their official retrieval URLs and SHA-256 values are in the lock.

The committed capture is `data/schedule-generator/reference-vectors.json`.
`python -m scripts.schedule_generator_reference --verify-only` checks its locked
bytes and provenance. The ordinary pilot resource compiler packages the verified
capture as `reference/source-random-rule-vectors`; it performs no Ruby execution.
Consumers use the current packaged manifest identity instead of the earlier
297-record identity. Existing frozen releases and source records are untouched.

Ten seed cases include zero, native initial/multifamily seeds, 32-bit boundaries,
leading-guard cases, 64-bit boundaries and a native 30-unit derived seed. Each
records 825 mixed integer/uniform draws crossing MT state boundaries, exact
initial/final words and Ruby-restoration draws. All six end-use allocations are
independently captured for each seed. Seven actual selected commercial rule
objects have full-year vectors both with and without an explicit holiday,
plus actual source-required design profiles and the native default profile.
Random draws and states require exact equality. Hourly rule values use the
published fraction absolute tolerance 1e-8; current captures match exactly.

## Consequences

Runtime modules remain standard-library Python and source allocation stays
order-significant. The calendar adapter deliberately supports only the inspected
source profile shapes; extending shapes or upstream versions requires new locked
source evidence and independent captures. This foundation does not implement
household or commercial kernels, annual normalization, or generator shipment.
