# Water-equivalent pilot v0.1.0

Released as an additive finite pilot against atlas v0.2.0, independently of
schedule supplement v0.3.0. It attaches to the existing Medium Office 90.1-2013
office program. No new program, source null replacement, stock weighting or
parametric generator interface is added.

The equivalent retains every source rule date, day selector, design day, value
order and source index. Its fractions are normalized by the source peak 0.57;
compatible SI flow scaling conserves draw. Per-field evidence, seven checksum-
locked primary files, schema 0.1.0, code snapshot, notices and the base-manifest
hash are included. Source spaces are deduplicated across HVAC mappings. Physical
fixture locations remain unspecified. This is mixed fixture draw at the source
target temperature, not water-heater energy, pure hot-water mixing fraction,
circulation or storage loss. Do not use its normalized curve with the old rated
flow or add an additional building-wide copy.

Reproduce/verify using:

```powershell
.venv/Scripts/python.exe -m scripts.fetch --lock sources/water-evidence-lock.json
.venv/Scripts/python.exe -m scripts.water_equivalent --verify
.venv/Scripts/python.exe -m scripts.water_equivalent --target build/water-repeat
.venv/Scripts/python.exe -m scripts.schedule_coverage --report build/schedule-coverage.json
```

The freezer/refrigerator/stochastic profiles and source atlas are unchanged.
The water pilot closes **zero** schedule gaps because its office already has
a source water schedule. Active commercial gaps remain 485 water plus 38
thermostats. The newly explicit release-scope policy excludes HVAC unavailability
overlays and complete magnitudes/full-model controls from the schedule milestone.
Archive those raw options without applying sampled interruptions. Generator
delivery follows near-full deterministic coverage.

The MkDocs office page provides original/equivalent interactive curves and
canonical JSON; new water and coverage guides explain conservation, scope and
per-record completeness denominators. See [ADR 0007](adr/0007-program-water-equivalents.md).

Public snapshot packaging fixes case-sensitive POSIX member order, creator system,
timestamp and permissions and stores entries without compression. This avoids
host and compression-library differences in Windows/Linux delivery. Every member
is an unchanged frozen-release file; the canonical manifest and release tag remain
unchanged.
