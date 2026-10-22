# Consumer contracts of release 1.0.0

[ADR 0036](adr/0036-suite-based-release-storage.md) stores the commercial atlas as
release `data/atlas-releases/v1.0.0`. Exports from it use three new majors:

| Export | New major | Previous | Schema |
| --- | --- | --- | --- |
| Program JSON | **5.0.0** | 3.0.0 (raw, defaulted), 4.0.0 (water heating) | [program-json-v5](../schemas/program-json-v5.schema.json) |
| Detailed construction set | **4.0.0** | 3.0.0 | [construction-json-v4](../schemas/construction-json-v4.schema.json) |
| Unified construction set | **3.0.0** | 2.0.0 | [construction-equivalent-v3](../schemas/construction-equivalent-v3.schema.json) |

The new schemas are derived from the previous ones by
`python -m scripts.atlas_exports --schemas`, so their physical rules cannot drift;
CI checks that the committed files match the derivation. The site still serves the
previous majors from the frozen releases until it is rebuilt from release 1.0.0.
Residential (ResStock) exports keep the previous majors. BEMGen component changes
are deferred.

```console
python -m scripts.atlas_exports --program ID --version filled
python -m scripts.atlas_exports --construction SET --context KEY --representation unified
```

## Program JSON 5.0.0

Each program has two versions:

- **`version: "source"`**: actual values only, as the source states them. This is
  the 3.0.0 `raw` form: unknowns stay unknown, hot water stays a `hot_water` load
  with an unresolved inlet, and `default_policy_id` is null.
- **`version: "filled"`**: fillings and approved defaults applied. This is the
  3.0.0 `defaulted` form with 4.0.0 draw-only water heating folded in: every
  active `hot_water` load moves to `water_heating[].draw` with its heater stages,
  and policy `atlas-program-defaults-2.0.0` is recorded.

Changes from 3.0.0 and 4.0.0:

1. **`version` replaces `export_mode`.** `source` corresponds to `raw`; `filled` to
   `defaulted` plus water heating. The document `id` no longer carries
   `:defaulted:…` or `:draw-only-v1` suffixes.
2. **Values the source implies as zero are actual in both versions.** A complete
   water path without fixture draw, or a schedule whose load magnitude is exactly
   zero, is stated as known zero; in 3.0.0 `raw` these were unknown.
3. **Readable IDs.** A program is `<template>.<building-type>.<mode>.<name>.<hash>`,
   for example `90-1-2019.hospital.department.icu-mixed.c4e48f`; `source.program_id`
   is the same ID. Schedules, services and members are cited by their release IDs.
   A filling constant (always zero) is an embedded schedule named
   `<template>.<building-type>.constant-0.<hash>`; a mix's composition is
   `<program id>:composition`. IDs the exporter derives (resolved schedules, mixed
   demands) are hashes of these and so differ from the previous majors.
4. **`source.release`** (`atlas-release-1.0.0`) replaces `source.definition_release`
   and `source.evidence_view`. `source.evidence` is listed in evidence-ID order.
5. **A mix has one identity.** Its demand and composition evidence are the source
   composition's in both versions; the reviewed twin's identities no longer exist.

Unchanged: loads, bases, units and heat fractions; controls and conditioning
states; embedded schedules' rules; shared services; required bindings; metadata;
the default policy; water-heating recipes and the ADR 0018 capped-delivery policy.
`tests/test_atlas_exports.py` compares every export with the previous major for
the same record after replacing IDs by what they reference.

## Detailed construction 4.0.0 and unified construction 3.0.0

Content is identical to detailed 3.0.0 and unified 2.0.0 for the same context,
including foundation and ground methods and the shared mass contract 1.0.0. Only
identities change:

- A context document is `<set id>.<context key>`, the unified one
  `<set id>.<context key>.unified`; the context key is the climate zone, plus the
  reference where a set covers several (for example
  `90-1-2019.office.construction-package.1993a1.5b.90-1-2019-small-office`).
- Sets are `<template>.<building-type>.construction-package.<hash>`; assemblies and
  materials are `<template>.<name>.<hash>` from the template library.
- References to them (component assignments, unified component sets, mass
  accounting, foundation extensions) follow.

Evidence IDs, internal identifiers (assignments, selectors, ground methods, mass
recipes) and citations of definition-release constructions keep their earlier form.
`tests/test_atlas_exports.py` checks that every export equals the previous major's
document with these identities replaced.
