# ADR 0038: Residential release storage

Status: accepted (2026-10-26, user decisions). Extends ADR 0036, which deferred
residential storage. Applies when residential families enter the atlas release:
the ResStock SDR fixture first, then the IECC residential and manufactured-housing
prototype families (plan stages S12, S13).

## Context

ADR 0036 stores commercial data as one file per program and per construction set
under `commercial/<template>/<building-type>/`, with folder tables, per-template
libraries, an evidence tree, readable content-hashed IDs and minor-delta releases.
Residential data differs in its source structure:
- **A ResStock record is a whole dwelling.** It is one sampled dwelling whose
  geometry, envelope, HVAC, appliances and schedules were selected together.
  ADR 0002 forbids crossing those options.
- **Each sample has one climate, vintage and floor-area bin.** Single-family
  detached alone has 22 samples.
- **Loads are per dwelling** (person/dwelling, W/dwelling). Floor area is a bin, so
  no exact area exists.
- **Schedules are mostly annual 8,760-hour series:** 503 series, 31 MB of values.
  Only 454 are distinct, about 10 per dwelling. Single-family detached alone holds
  14 MB.
- **Envelopes are per sample:** 41 construction sets, one per dwelling.
- **The code-prototype families vary by climate zone, foundation type and heating
  system.**

## Decision

Everything not listed here follows ADR 0036's commercial design.

1. **Records.**
   - A residential program is one whole dwelling. It has no space-type programs and
     no department or general mixes.
   - Rooms and zones are the consumer's.
2. **Identity.**
   - Folders are `residential/<family-or-template>/<building-type>/`.
   - Climate, vintage and floor-area bin are record fields and part of the readable
     ID, for example
     `resstock-sdr.single-family-detached.5a-1980s-1500-1999ft2.<h6>`.
   - There is no climate subfolder.
3. **Load basis.**
   - Loads keep the source basis, per dwelling unit.
   - Program JSON gains the `dwelling_unit` basis as an additive minor.
   - No per-area conversion is made.
4. **Annual schedules.**
   - Each dwelling's annual series are stored in its own file,
     `schedules/<record-id>.json`, deduplicated within the folder.
   - Ruleset schedules stay in the folder's `schedules.json`.
   - Where the stochastic generator produced a series, its recipe and seed are
     recorded with the values (ADR 0035). The values are not regenerated.
5. **Constructions.**
   - Each dwelling has its own construction set with one context, linked one to
     one.
   - Assemblies and materials are shared through the template library.
6. **Code prototypes** (IECC residential, manufactured housing).
   - Programs follow the commercial pattern: per edition and type, independent of
     climate.
   - Construction sets carry foundation type as a context axis beside climate.
   - If internal gains turn out to vary by prototype variant, they become program
     variants, raised when S12 inspects the files.
7. **Systems are not stored for residential families for now.**
8. **Apartments.**
   - The DOE Ref and 90.1 Midrise and Highrise Apartment programs stay under
     `commercial/`.
   - ResStock apartment units are dwellings under `residential/`, cross-referenced
     to them.
9. **Other.**
   - A ResStock multifamily record is one unit, with its building-context fields
     (units in the building, stories, unit position). The atlas makes no
     building-level record.
   - Hot water is a dwelling load.

## Consequences

- Residential storage enters as a minor delta that adds `residential/`. Commercial
  fields keep their meaning.
- A folder's size grows with its sample count, and per-dwelling schedule files keep
  every file under ADR 0036's 25 MB limit.
- Consumers read whole-dwelling programs. Zoning a dwelling, and its systems, stay
  outside the atlas until a later decision.
