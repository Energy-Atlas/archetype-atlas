# ADR 0015: self-contained program JSON and explicit experimental defaults

Date: 2026-10-07.
Status: connector contract prepared at the user's request; site integration pending.

## Context

The user will adapt the BEMGen connector to accept plain program JSON. The
payload must include schedule definitions, without requiring another atlas query.
The user authorized the atlas to choose defaults; copying offers only raw or
default-filled JSON. This does not authorize model geometry or HVAC sizing.

The user separately withdrew site backward-compatibility requirements and
authorized removing obsolete routes and versioned downloads from publication.
That changes publication scope, not the provenance of retained research inputs.

## Decision

Define connector schema version 2.0.0 in `schemas/program-json-v2.schema.json`.
It embeds its full schedule schema; a standalone schedule schema is also supplied.
This is a consumer DTO, separate from canonical definition schema 1.0.0 and the
selective-query envelope. Raw and defaulted modes use the same DTO structure.

Programs contain additive, basis-aware loads, controls, embedded schedules,
one-time shared services, original source evidence, and explicit external binding
requirements. Schedules support ordered rule sets and recorded annual hourly
realizations. Preserve rule precedence, units, annual year and source context.

Raw DTOs preserve unknown simulation inputs. Defaulted DTOs require non-null
simulation operands and identify policy `atlas-program-defaults-1.0.0`, with
JSON Pointer substitution records. Defaulted program/schedule variants have
distinct identities. Source evidence, inapplicable fields and model geometry
are not filled. The policy contains explicit experimental assumptions, rather
than claims that upstream sources report these values.

Preserve known positive loads and existing rules. Fill source leaves before
recomputing mixtures. Missing intervals in known rule sets use an explicitly
assumed lowest-priority fallback, with original rules still authoritative. A
fully specified program definition does not imply a complete simulation model.

## Validation and consequences

Supply actual reviewed Medium Office raw/defaulted examples and a recorded 2007
annual residential schedule. Schema checks reject invalid units, fractions,
defaulted null physical inputs and unsupported vector lengths. Additional checks
cover reference closure, schedule units and rule coverage, annual leap status,
temperature ordering, source preservation and explicit assumption records.

The connector imports `export_mode: "defaulted"`, applies declared basis scaling,
and binds model geometry/calendar/service hosts. JSON Schema validation alone
does not apply defaults or establish cross-object physical validity. The public
site exporter and popup will target this contract in subsequent implementation;
they are not part of this schema handoff.
