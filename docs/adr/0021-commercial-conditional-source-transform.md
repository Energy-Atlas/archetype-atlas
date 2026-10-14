# ADR 0021: Commercial conditional sampling and native transformation boundary

Date: 2026-10-14. Status: accepted for the bounded M1 generator implementation.

Commercial generation uses the passed Task 1 audit: exact `medium_office`
selectors, ComStock v33 tables and explicit stock-year2018 experimental context.
The stock year does not condition the selected rows. Frozen Standards develop
c8c1b9 program definitions and original reference budgets remain distinct from
the actual ComStock transformation dependency, RubyGems Standards0.8.6 (gem
SHA-256 9a3477cdb6aac7501430a214cc1be5fc93c28b8ddd444e39579d442931e3a19f).
No population-matrix realization, national configuration or stock/prototype
equivalence is asserted.

The standalone `atlas_conditional_seeded_v1` policy consumes an already-derived
full SHA-256 integer from `commercial_group_seed`. It uses Python random.Random
MT19937 53-bit uniforms, once per selected parameter including degenerate rows.
The ten draws retain source vector order: weekday start, weekend start, weekday
duration, weekend duration, plugload ratio type/weekday/weekend, lighting ratio
type/weekday/weekend. Dependent rows use original option strings, never formatted
SI values. Selection is the first original raw cumulative probability strictly
greater than the supplied uniform. A draw beyond a subunit raw CDF errors; no
normalization, tail fill, retry or new seed is used. Records retain row numbers,
selectors, original options/probabilities, raw CDF, uniforms, SI values/units,
NA modification flags and source receipts. Actual upstream population sampler
mode/index/count/buckets/allocation are unknown/null; available CLI modes are
descriptive evidence. Population realization equivalence is explicitly false.

Actual operating inference depends on `Space.spaces_get_occupancy_schedule`
and `space_hours_of_operation` in the pinned gem's `space/space.rb`. That complete
member is now part of the immutable source/resource dependency closure. Source
inference rounds weighted hourly occupancy to six decimals before dividing by
design occupancy and applying its normalized daily-range threshold. Therefore
arbitrary positive weight cancellation is not assumed.

For M1, require an explicit named single nonresidential Office reference
occupancy carrier, supplied as its original schedule, normalized nominal_people
weight1, residential=false and original source evidence. This is an inference
carrier, not an actual building occupant count, area, geometry or population.
Native probes at weights0.1/1/100 give the same inferred operating profiles for
this exact schedule; no broader scale-equivalence claim is made. A plenum may
use the carrier only through an explicit configuration binding; its own zero
occupancy cannot silently become building hours of operation. Missing context
fails. Mixed/residential aggregation requires a separately validated binding.

Port the actual Standards0.8.6 profile/formula dependency closure, including
occupancy threshold/gap removal, source start/mid/end anchor decisions, hours
and thermostat modes, ramp insertion, out-of-order correction, source minute
truncation, native point storage and hourly query representation. The runtime
accepts original Constant/Hourly rule objects, not arbitrary expressions or a
generalized schedule language. Original dates, selectors, design-day records
and source order remain in receipts. Numeric day profiles follow the actual
native rule selection; no reconstructed linear shift substitutes for formulas.

ComStock's inspected options lookup sets `peak_occ_frac=0.231` for both
baseline_hvac_sizing autosize/hardsize options. Require this explicit selected
lookup binding; sizing/intensity/geometry are not executed or sampled. Apply
the source occupancy multiplier to ordinary profiles, preserving design days.
People/count semantics are not annual-energy normalized. Retain actual lighting
and equipment set_sch_bpr behavior, including unchanged constants, the weekday
base and capped weekend base. NA disables that modification rather than setting
a zero ratio. An unbound required weekday base fails.

Independent native captures established three distinct precision boundaries:

- `ScheduleDay.addValue` stores doubles with15 significant digits. Positive,
  negative and occupancy multiplication readback probes preserve this boundary;
  e.g.0.2021249999999999 becomes0.202125. Apply this only where the native source
  stores values, never as a generic finalizer rounding rule.
- Native getValue selects the next model-timestep endpoint for off-grid queries
  with No interpolation. The verified model timestep is6 per hour. Captured
  queries at08:01/08:09/08:10 return the08:10 value, while08:11 returns08:20.
- Standards0.8.6 compares version strings lexically:3.10.0 <3.8.0 is true. The
  actual OpenStudio3.10.0 capture therefore takes the legacy getter, sampling at
  the minimum profile interval (at most15 minutes) and rounding5 decimal places.
  Do not replace it with the intended numerical-version averaged-timeSeries
  round10 branch. The source minimum interval need not divide60; its sample
  selection remains intact. These emitted values undergo no additional generic
  significant-digit rounding.

The zero-duration setter has native duplicate-time behavior: start08:00 with
duration0 produces inferred start24/end8/hours8. Full day start0/duration24
produces start=end24/hours24; the application method computes occupied duration
from the equal endpoints. Preserve those observed source decisions rather than
inventing intuitive zero/full-day transformations. Fixtures compare native
profile times/discrete rule selection and values for native, short, long,
overnight, zero, full-day, different weekday/weekend, constant/ramp/design-day
and sampled cases.

The opt-in native subprocess pins TZ=UTC as in ADR0020. Selected commercial
numerical methods use explicit Gregorian dates and no elapsed Time arithmetic;
Time.now occurs only in administrative occupancy-schedule properties, omitted
from scientific outputs. No physical offsets or OS timezone are changed.
Capture-only memoization keys exact native profile values/times/interpolation,
model version and timestep. Cache misses execute the actual native daily getter;
whole annual/inference/parametric callers remain source methods. Cached versus
uncached complete8760 equality is asserted for original and changed/interpolated
Office profiles. Generation and ordinary tests require no Ruby/OpenStudio/network.

Budgets are established from original raw frozen reference arrays/magnitudes
before sampling, source storage/export rounding, occupancy adjustment or BPR.
Bind the actual emitted8760 fractions afterward. Short and long realizations
have different effective magnitudes and identical known annual energy/volume
targets. Effective amplitude is not installed/nameplate capacity. The actual
commercial water-density unit m3/s/m2 integrates to m3/m2 with3600 seconds/hour;
bundle validation checks its basis/fuel/host/ownership and conservation. Old
releases, targets and units are unchanged.

Independent fixture provenance pins runtime/executable/gem/member/harness/input
hashes, actual method locators, extraction date, original values/units and
interpretation. Conditional options use stored source rows/uniforms and the
actual pinned `_com_execute_samples`; wrapper seed reproducibility is tested
separately. Continuous comparison uses the named source policy, with exact
source options, rule days and minute times where discrete. Upstream license
notices remain packaged; original work remains unlicensed by user choice.
