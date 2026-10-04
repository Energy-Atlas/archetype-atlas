# Schedule availability after selective resolution

The immutable source atlas v0.2.0 retains its original missing values. Opt-in
resolution supplement v0.3.0 adds 2,125 explicit resolutions for 754 records.
The per-record inventory and reasons are machine-readable in
[`resolutions.json`](../data/resolution-releases/v0.3.0/resolutions.json);
the catalogue displays the same evidence alongside each original record.

| Added resolution | Count | Basis |
| --- | ---: | --- |
| Executed residential profile-column references | 503 | Pinned upstream execution; includes three explicitly zero-occupant occupancy references |
| Missing schedules with reported zero magnitudes | 33 | Source zero, not inference from absence |
| Reviewed no-occupancy programs | 30 | 24 cavities and six exact data-centre IDs; excludes transient maintenance |
| Reviewed plenum lighting zeros | 10 | Exact user-approved Medium/Large Office ceiling plenums |
| Reviewed unconditioned cavities | 24 | No mapped HVAC, excluded floor area and absent thermostats |
| Reviewed local hot-water demand zeros | 29 | 24 cavities and five elevator cores; no central-loop inference |
| Demonstrated all-electric dwelling gas loads | 4 | Every relevant selected fuel option checked; zero W without invented floor area |
| Selected absent appliance/fan fractions | 61 | Explicit absent/no-use source selection, including the zero-occupant apartment freezer |
| Reviewed clean-recipe gas equipment zeros | 1,426 | 713 fractional schedules and 713 matching densities; exact IDs and source creation guards |
| Fixed refrigeration defaults | 5 | Three refrigerators and two selected freezers in zero-occupant dwellings; no temperature feedback |

The counts above are resolutions, not distinct buildings or population weights.
Electrical-room positive equipment loads remain intact. Corridors, stairs and
support spaces are never classified solely by their names.

All 41 residential configurations were executed: 38 stochastic realizations
and three upstream zero-occupant skips, plus 41 nominal thermostat profiles.
Each has 8,760 hourly intervals. The skipped records are
`residential_archetype-08a27444abac71d3b335` (SingleFamilyDetached),
`residential_archetype-28457c00121833f065f2` (MultiFamily5PlusLowRise), and
`residential_archetype-aa1f864c610bf3d98e2e` (SingleFamilyDetached).
Their other stochastic loads remain unknown; five fixed refrigeration profiles
are separately supplied by v0.3.0, with one absent freezer zero. Occupancy zero
does not imply lights/other appliances zero. The [profile index](../data/resolution-releases/v0.3.0/profile-index.json)
links every record to its exact columns, status and artifact hashes.

The supplement leaves 557 commercial program fields unresolved:

| Field | Count | Why unresolved |
| --- | ---: | --- |
| Local service-water-heating schedule | 495 | Missing source value outside the specifically reviewed no-demand spaces |
| Electric equipment schedule | 24 | Cavities can contain equipment; absent source magnitude alone does not justify zero |
| Heating setpoint schedule | 19 | No reviewed evidence sufficient to disable heating |
| Cooling setpoint schedule | 19 | No reviewed evidence sufficient to disable cooling |

Residential unresolved end uses/controls are listed separately in each profile:
EV, refrigerator/freezer, exterior lighting and non-exported uses; stochastic
loads for the three upstream skips; and unavailable-day placement/overrides.
Weather is an explicitly labelled station proxy because the county archive was
inaccessible. These boundaries and exact generation inputs are explained in
[residential generation](residential-generation.md) and
[ADR 0004](adr/0004-selective-resolution.md). Applying this supplement does not
establish complete simulation readiness.

The active assessment excludes attic/plenum/basement source programs; their
archival records remain available. This leaves 523 unresolved fields:
485 local water, 19 heating and 19 cooling schedules. See the
[source review](schedule-source-review.md) for component-level gas/water verdicts,
fixed default schedule sources, exact HVAC unavailable-day cases and the DOE
reference-location decision. [ADR 0005](adr/0005-parametric-schedule-generators.md)
records the future parametric-generator direction; its interface is deferred.
[ADR 0006](adr/0006-deterministic-coverage-release.md) defers generator shipping
until near-full deterministic coverage and describes a source-conserving
program-level hot-water allocation equivalent. The 495 water gaps are not yet
closed; the method needs explicit fixture/service-zone mapping before assignment.
