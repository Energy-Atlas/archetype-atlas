# Program JSON contract

Every program page offers the two consumer exports of its release, read straight from
the release by `scripts.atlas_exports`:

- **source**: actual values only, as the source states them, including values the
  source implies as zero. Unknowns stay null with their reason.
- **filled**: actual values plus fillings and approved defaults, each filling tagged with
  its rule and basis, and draw-only water heating. This is the version BEMGen consumes.

The major is 5; each release adds optional fields as a minor: 5.1.0 (DOE reference
reconciliation: fenestration, source calendar, alternates, building services), 5.2.0
(IECC commercial: loads and schedules by climate, source zones) and 5.3.0 (dwelling
programs). A later minor's optional blocks render on the program page without a site
change. IECC commercial, IECC residential and manufactured-housing programs export the
source version only until their water heaters are stored.

Contracts and schemas: [consumer contracts of release 1.0.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/consumer-contracts-release-1.0.0.md),
[release 1.1.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/consumer-contracts-release-1.1.0.md),
[release notes 1.3.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/release-notes-atlas-v1.3.0.md) and
[1.4.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/release-notes-atlas-v1.4.0.md); schemas in [`schemas/`](https://github.com/Energy-Atlas/archetype-atlas/blob/main/schemas).

```console
python -m scripts.atlas_exports --release 1.4.0 --program ID --version filled
```
