# Residential dwellings

Release 1.4.0 adds a `residential/` tree beside the commercial templates. The
decision record is ADR 0038; the release notes are
`docs/release-notes-atlas-v1.4.0.md`.

## What a residential program is

A residential program is one whole dwelling. It has no space-type programs and no
mixes: rooms, zones and systems are the consumer's.

- **Loads keep the source basis.** ResStock and the IECC prototypes give loads per
  dwelling (W/dwelling, person/dwelling, m³/s/dwelling); the manufactured-housing
  prototypes give lighting and plug loads per floor area (W/m²) and record the
  dwelling floor area beside them.
- **Hot water is a dwelling load.** Water heaters, like every residential system, are
  not stored.
- **Multifamily** records are one unit, with the building around it as context
  fields (units in the building, stories, unit position).

## Folders

| Folder | Family | What it holds |
| --- | --- | --- |
| `residential/resstock-sdr/<building-type>/` | ResStock SDR source fixture | 41 sampled dwellings, one program each |
| `residential/iecc-<edition>/{single-family,multifamily}/` | IECC residential prototypes | see the IECC residential guide |
| `residential/{hud-code,doe-final-rule}/{single-section,multi-section}/` | Manufactured-housing prototypes | see the manufactured-housing guide |

Each folder has `programs/` and `constructions/`. The code-prototype folders keep their
ruleset schedules in `schedules.json`; the ResStock folders keep each dwelling's annual
8,760-hour series in `schedules/<program-id>.json`.

## ResStock dwellings

- **Identity.** A dwelling's ID names its climate, vintage, floor-area bin and source
  building, for example
  `resstock-sdr.single-family-detached.5a-pre1940-2000-2499ft2-b101526.<hash>`.
- **Values.** Every value is the frozen definition release's. The `filling` block
  holds the recovered magnitudes and fixed background schedules the frozen filled
  export applies, with the resolution rows that justify them.
- **Constructions.** One construction set per dwelling, with one context.
- **Apartments.** ResStock apartment units cite the commercial apartment folders of
  the DOE Ref and 90.1 templates, which stay commercial.

## Exports

Dwellings export as Program JSON 5.3.0:

```
python -m scripts.atlas_exports --release 1.4.0 --program <dwelling id> --version filled
```

The ResStock `source` and `filled` documents equal what the frozen exporters give for
the definition records; the code prototypes export `source` only.
