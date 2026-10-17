# 0019: Residential activity and coordinated shape checkpoints

> Amended by ADR 0035 (2026-10-17): the semantic decisions stand; bit-level exactness, authority locks and certification ceremony are superseded.

Status: Accepted for the source-faithful Python schedule kernel, 2026-10-14.

The residential generator ports ResStock revision
`dd25369f41a83a0767aefeeac0b6f8a0b0edd649` using the locked original probability
tables, Ruby-compatible draws and native source call order. It returns compact
integer state traces instead of one-hot matrices. These describe identical
15-minute source states and preserve every resident separately. The recorded
sampled state/duration decisions precede the source four-hour annual rotation;
the state traces follow that rotation. The main-stream checkpoint is after the
unit offset draw, and all six end-use seed/state allocations remain available
for the later event producer, including the excluded EV allocation.

`simulate_activities(inputs, unit_seed, resources)` consumes explicit `year` and
`residents`. `occupancy_shapes(activities, inputs, resources)` additionally
requires `state`, `latitude`, `longitude`, `time_zone_utc_offset`, `weather_id`
and exact `installed` presence booleans. There is no household fallback.
Bedrooms, load magnitudes, and annual budgets belong to later consumers.

The presence object keys are `dishwasher`, `clothes_washer`, `clothes_dryer`,
`cooking_range`, `plug_loads_other`, `plug_loads_tv`, `ceiling_fan`, and `garage`.
Appliance flags are retained for later events; plug, TV, fan and garage flags
govern their actual upstream branches. Interior lighting always exists for
a simulated household. Garage lighting shares its identical source shape.

Emitted occupancy, plugs, TV, fan and lighting describe hourly dimensionless
fractions. The source sequence is minute expansion, circular annual unit
offset, separate daily state/month rotation, hourly sum and normalization.
Occupancy divides by 60; other channels divide by their annual maximum.
Resident counts and activity W/person receive no load-budget scaling here.
Weather controls the fan monthly threshold (strictly greater than 63 F monthly
mean); location controls the Building America lighting equation; state controls
daily rotations. None changes raw Markov activity draws.

The later A1 selected apartment subgraph has a narrower input contract than
`occupancy_shapes`: it consumes the actual state, latitude, longitude and
physical UTC offset plus positive integer N, source streams and the 2007
calendar, with no weather or installed flags. The original whole wrappers
above remain weather dependent. A1 compared 55 ordinary unmodified HMM
targets and three separately classified controlled component targets; the
four selected-method cases passed the named 8,760-hour fraction policy.
These results do not certify a particular prototype programme or caller unit.

Source zero-resident generation skips before any RNG initialization. The atlas
adapter therefore emits explicit zero occupancy only and marks the source skip;
it creates no schedules for unknown other loads. The zero occupancy array is an
adapter representation, not a schedule emitted by the skipped upstream kernel.
Undefined upstream normalizations and unsupported source location/state inputs
raise structured errors rather than manufacturing fallback schedules.

Lighting monthly weighting algebraically reduces to a common scalar that cancels
in upstream annual maximum normalization. The port computes that cancellation
directly, retaining the source piecewise solar equation and the >=51.49 latitude
table. This can differ at machine precision, not scientifically significant
precision. It applies the source equation's built-in seasonal offset without
applying a calendar DST conversion.

Development-only Ruby/OpenStudio capture intercepts actual source activity
methods and stops after actual coordinated shapes, before sink events. Its lock
records archive, source, resource, executable, harness and input hashes. Source
weather monthly means use the packaged hourly C values and actual upstream
UnitConversions. Offline tests read checked JSON. Discrete decisions and RNG
states compare exactly; raw fractions use the named policy `fraction`
(`rel_tol=1e-6`, `abs_tol=1e-8`). No rounded CSV equality is claimed.

No frozen release or Program JSON semantics change. Packaged generation needs
only Python standard-library and immutable ResourceSet data.
