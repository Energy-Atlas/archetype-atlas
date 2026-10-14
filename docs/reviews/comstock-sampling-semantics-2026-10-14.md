# ComStock sampling preflight

Inspection date: 2026-10-14. This assessment covers the pinned public sampler,
not a completed port of selected distribution tables. Its cached bytes were
checked against `sources/schedule-generator-inspection-lock.json`.

## Finding

ComStock's population sampler is not a self-contained `parameters + seed`
function for an individual building. Conditional option selection can be
reproduced from explicit dependency values, an ordered probability row and a
supplied uniform draw. Reproducing a particular population realization also
requires the matrix layout and random states that supplied that draw.

Primary evidence is
[tsv_sampling.py at 3c103063c0debb177a200dd1df8406b8d0f8d515](https://github.com/NatLabRockies/ComStock/blob/3c103063c0debb177a200dd1df8406b8d0f8d515/sampling/tsv_sampling.py).
Source locators below refer to that exact revision.

| Mechanism | Source locator | Reproduction implications |
| --- | --- | --- |
| Constructor and CLI | Lines 26–63, 597–639 | Specify TSV version, stock simulation year, sample count, bucket count, sampler mode and optional precomputed CSV. Neither interface accepts a seed; this file does not initialize the global RNGs. |
| Attribute groups and dependencies | Lines 73–131, 230–269, 303–345, 416–474 | Operating start/duration fields share a group with unrelated building attributes; lighting/plug ratios occur in later groups. Group dimensions, resolved dependency order and previous results affect draw assignment. |
| Pseudorandom matrices | Lines 366–384 | Each bucket receives `np.random.random((n_dims, n_samples / n_buckets))`. Sample index, matrix dimensions, bucket layout and all prior consumption of NumPy's global RNG determine a row's draws. |
| Sobol mode | Lines 387–413, 615, 636 | Each bucket uses a Sobol sequence, Python `random` shifts and a pandas shuffle without an explicit `random_state`. Reproduction needs these additional states, sequence implementation and layout. At this pin the CLI defaults to Sobol; `--random` selects pseudorandom. |
| Precomputed allocation | Lines 167–188, 309–325, 503–515 | A precomputed CSV supplies dependency values and row order. Already supplied attributes bypass selection; the next newly sampled attribute consumes the next matrix-vector position. |
| Conditional selection | Lines 516–534 | Filter dependency rows to one row; retain option-column order and select the first cumulative probability **strictly greater** than the draw. Missing or ambiguous reductions are errors, not national defaults. |

For the pseudorandom matrix, let `m = sample_count / bucket_count`, `d` be
the group's allocated dimension count, `b` the bucket index, `j` its sample
column and `k` the vector position consumed by a newly sampled attribute.
Within that group's flat draw stream, the position is `b*d*m + k*m + j`.
Earlier groups add their draw consumption. This formula is derived from the
source's array shape and access order. Although the constructor calls buckets
a performance choice, changing their layout can change which draw reaches a
given building/attribute. Removing unrelated dimensions can do the same.

The pinned
[sampling README](https://github.com/NatLabRockies/ComStock/blob/3c103063c0debb177a200dd1df8406b8d0f8d515/sampling/README.md)
also describes a precomputed allocation file fixing building type, sampling
region, size bin, heating fuel and HVAC system. The atlas must not infer these
dependencies from a program name or invent a population row.

## Required gate before the commercial kernel

Task 1 must extend this assessment with the actual selected TSV archive and
each schedule parameter's dependency closure before Task 6 starts. Examine
`weekday_start_time`, `weekday_duration`, `weekend_start_time`,
`weekend_duration`, and the lighting/plug base-to-peak selectors and ratios
where the selected measures use them. Do not assume all ten fields apply.

For each selected field record its source/member hash, row selectors, option
order, conditional inputs, source group/vector position and whether a local
uniform draw suffices after conditioning. Trace dependencies outside the
schedule subset and distinguish explicitly supplied selectors from sampled
dependencies. Pin the chosen source configuration, TSV version, stock year
and actual transformation dependency. Archive selection and per-field
closure remain pending; this preliminary assessment does not pass that gate.

Store the completed machine-readable decision in
`data/schedule-generator/comstock-sampling-audit.json`. Its `gate_status`
must be `passed`, and every selected field must have a resolved decision,
before a commercial kernel or release can claim support. Missing public
tables or unbound selectors keep the gate closed.

## Standalone adaptation and comparison boundary

The approved pure Python interface permits an explicitly versioned
schedule-only seeded wrapper. It preserves the selected conditional
distributions and option-selection semantics, records its own RNG algorithm,
seed derivation, draw order, selected rows and options, and samples once per
coordinated commercial operating group. It does not recreate population
allocation, batch matrices or Sobol sampling. Label this policy
`atlas_conditional_seeded_v1` and set
`population_realization_equivalent: false` in audit and generation receipts.
The exact wrapper algorithm is settled and tested after the parameter closure
is known, rather than silently borrowing Ruby's initialization.

Validate conditional selection against identical stored row/draw pairs and
validate schedule transformations against identical selected parameter values.
Test wrapper determinism separately. A matching marginal distribution, seed
number or transformed schedule does not establish equivalent ComStock
population RNG behavior. Any future exact population-replay mode would need
the full context and a separately validated claim.

Annual-target conservation remains a second, explicitly documented atlas
normalization policy after the commercial source transformation. It is not
part of an unmodified ComStock realization.
