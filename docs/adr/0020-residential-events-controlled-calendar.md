# ADR 0020: Native residential event shapes and controlled calendar reference

Date: 2026-10-14. Status: accepted for the schedule-generator implementation.

Task 5 resumes the serialized native main and six end-use checkpoints produced
by Task 4. It does not allocate streams again. EV has no emitted output, but its
allocator slot remains between dryer and cooking. Event draws never consume
main; sinks, baths and showers share hygiene. Dishwasher water then power share
dishwasher. Washer water then power share washer; washer power samples dryer even
when the dryer output is absent, and skips both power streams when washer is
absent. Cooking is independent. Presence receipts describe the actual branch,
including a present dryer suppressed by an absent washer. Zero residents retain
the upstream measure skip with no stream initialization or event output.

Port the pinned ResStock dd25369f41a83a0767aefeeac0b6f8a0b0edd649 event methods
(schedules.rb:1076-1564), not a replacement statistical model. Retain clusters,
source CDF tail behavior, Gaussian minimum, sampled power/duration rows, integer
sample indices, minute ceil/flow compensation, fixed gaps, state-edge suppression,
source step jumps, overwrite versus addition, and annual-end handling. Washer
starts dryer immediately after its realized washer duration; the source step
jump uses unmodified sampled washer+dryer 15-minute durations. Appliance monthly
multipliers change filled minutes without changing that step jump.

Hourly water fixture fractions normalize shower, sink and bath separately after
annual unit rotation, daily state/month rotation and hourly sums, then normalize
the sum of those three fractions. Appliance power and water each use their own
post-shift annual maximum. Calibration samples are shapes only. Annual energy
and water targets remain the original recovered definition evidence, including
separate fuels and zero budgets; effective amplitudes are fitted later. No old
frozen profile, release or target is rewritten.

Native power methods obtain month through `Time.new(year,1,1)+elapsed_seconds`.
An uncontrolled Windows run therefore inherits the host timezone/DST. A native
probe found minute 129555 (March 31 23:15 in the standard calendar) evaluated as
April 1 00:15 -0400 on the host, and minute 305235 similarly crossed July/August.
This changes dishwasher, washer/dryer and cooking duration multipliers at month
edges; stochastic draws and source start steps were unchanged.

The controller's binding calendar ruling pins only the reference subprocess's
`TZ=UTC`, and Python indexes the elapsed local-standard calendar. This is the
explicit `controlled_no_DST_local_standard_calendar` reference variant. UTC is
computational calendar control, not a conversion of physical lighting, solar,
weather or household time arrays. Source methods and OS timezone are unchanged.
Capture receipts assert offset 0 and DST false around March/November transitions
and month edges. Physical UTC offset remains the original lighting input. Do not
claim equality to uncontrolled host-DST arrays or relabel old frozen profiles.
The cost of a different calendar interpretation is month-edge regression and
reference revalidation; known annual targets are unaffected.

Immutable offline fixtures retain native random draw limits/results, final MT
states, selected power rows, nonzero minute runs `[start,length,value]`, complete
activity-state runs `[length,state]` and raw hourly channels. Run indices/lengths
and all random/discrete decisions compare exactly; continuous values use the
named policy in sources/schedule-generator-policy.json. Capture provenance pins
source/runtime/executable/harness/input/member hashes and ResourceSet identity.
One compiler-derived event-constants resource retains each source constant,
line/value/unit/transformation/date receipt and its explicit SI counterpart.
Generation consumes original calibration cells to preserve source operations.

Controlled component probes replace returned state matrices only after actual
seeded upstream activity execution. They test year-end event behavior, a valid
all-at-home non-active trace with no appliance/shower/bath events, and an all-absent
trace with 200 sink attempts/day. These are event-component inputs, not naturally
occurring seeded annual activities. The native no-event normalization produces
NaNs and ultimately `ArgumentError: comparison of Float with NaN failed`; the
port raises `GeneratorError(code='zero_generated_integral')` without retry or a
new seed. The positive original annual budget rejects a zero generated integral
separately through Task 2. True zero-resident skip, absent appliances, and known
annual-zero magnitudes have distinct receipts/tests. No claim is made that an
occupied activity-generated no-event seed was discovered.
