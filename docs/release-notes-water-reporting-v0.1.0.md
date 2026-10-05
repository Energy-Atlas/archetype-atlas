# Water-reporting v0.1.0

Date: 2026-10-05. Schema: 0.1.0. Optional reporting variant bound to immutable
atlas v0.2.0, resolution v0.4.0 and commercial-completion v0.1.0 manifests.

- 734 active commercial programs have attributed-volume inspection curves.
- All 217 source fixture paths accounted for: 158 source assignments, 26
  design-occupant main allocations, 17 kitchen process allocations, six laundry
  process allocations, ten shared hospital main/laundry services.
- 88 peak-normalized reporting shapes retain timing through original source
  component rules, including seasons, holidays and design days.
- Design-occupant weights use checksum-bound reference floor polygons, people
  densities and zone multipliers applied once after space-handle deduplication.
- Coverage with resolution v0.4.0 is 5,138/5,138 operational schedule fields.
  Source-only coverage remains 4,859/5,138; original 279 local allocations remain
  unknown. A reporting zero is not an inferred source physical zero.
- Component target temperatures, original evidence and shared services remain
  separate. No zone sensible/latent gain assignments or heater-energy profiles
  are inferred. Complete magnitudes and full simulation readiness remain deferred.

Original work unlicensed. Source notices retained. Frozen earlier bundles unchanged.
Build and verify with `python -m scripts.water_reporting` and
`python -m scripts.water_reporting --verify`; construction never overwrites an
existing target. The manifest identifies files and dependency SHA-256 hashes.
