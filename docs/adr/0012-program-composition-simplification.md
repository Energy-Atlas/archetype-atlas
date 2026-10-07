# ADR 0012: Area-weighted program composition as an experimental simplification

Date: 2026-10-07. Status: accepted research specification; release implementation pending.

## Context

The atlas's source programs are often finer than the unit/program definitions
used by downstream UBEM plan generators. The researcher approved explicit
per-family program compositions and deliberately accepts the error introduced
by blending their controls and loads. That error will be benchmarked in later
experiments. This is distinct from geometric/thermal-zoning simplification.

## Decision

Use one exact source family, template and resolved context per recipe. For
eligible leaf areas A_i, compute w_i = A_i / sum(A_i) using unrounded represented
source areas. Blend heating and cooling setpoint schedules pointwise:

`T_mix(t) = sum(w_i * T_i(t))`.

Apply area weighting to other compatible numerical program values. For scheduled
loads, weight their hourly densities: `q_mix(t) = sum(w_i * d_i * s_i(t))`.
Preserve schedule calendar/day/design-day semantics during alignment. A required
unknown input remains unknown in the mixed field; null is not zero. Convert
absolute or non-area quantities to their appropriate comparable basis before
blending; do not relabel an absolute fixture flow as a floor-area density.

Do not add representative-control selectors, component control systems, or
mandatory thermal partitions to make these mixtures more physically faithful.
Area-weighted controls are the chosen experimental approximation. Preserve source
programs and composition provenance so the simplification can be compared later.

Basement and attic source programs, including named variants, never enter any
mixture or its denominator, even when counted by the source model. They remain
available as individual optional presets; family generators do not assume their
use. Other non-counted spaces remain available as source background definitions.

The default template is ASHRAE 90.1-2019. The default composition mode is the
finest supported source-program mode. Unsupported combinations are unavailable,
not silently substituted. The [family matrix](../reviews/program-aggregation-matrix.md)
defines the approved leaf groups and generator requirements.

## Consequences

Mixed controls are derived approximations, not source-prescribed control rules
or a claim of equivalence to a full prototype model. Mixture identity must retain
the exact members, weights, template and simplification rule. No stock-family
averaging or missing-input guessing is introduced. This decision does not itself
change canonical JSON schema, frozen releases or the current delivery contract;
release implementation and validation remain subsequent work.

## Execution sequence

The researcher defined three stages: (1) work out mixtures, (2) redesign the
catalogue, and (3) hand off to a BEMGen agent to derive plan generators, preset
definitions/schema and a value fetcher using the redesigned catalogue. Discuss
the stage 2 design before beginning implementation of any of the three stages.
This commit fixes the stage 1 decisions and evidence only; it does not dispatch
the BEMGen agent or change the current catalogue/delivery format.
