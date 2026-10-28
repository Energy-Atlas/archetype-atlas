# ADR 0044: Lighting controls and plenum programs (release 1.5.0)

Status: accepted for release 1.5.0 (2026-10-27). Recording lighting controls and
mapping the unmapped plenums are user decisions (plan
`docs/superpowers/plans/2026-10-27-stages-after-release-1-4-0.md`, P7, L-1 to L-3, P15
and G-1). Amends the residential plan's C4 ("daylighting controls: evidence only") and
ADR 0039 ("excluded, not guessed"). The choices the plan left open are agent
decisions, listed in section 4.

## 1. Context

- **Lighting in the atlas** was a design density (W/m²) and a usage schedule per
  program. Occupancy-sensor control credits are already inside the schedules (the
  office weekday peak falls from 0.9 to 0.797 to 0.753 across 90.1 editions), but
  daylight dimming was not recorded anywhere.
- **The source models.** Daylight dimming is an EnergyPlus `Daylighting:Controls`
  object per zone, with reference points that each control a fraction of the zone's
  lights. Counted over the pinned sources (`scan` in the input):

  | Source | Models | With controls |
  | --- | --- | --- |
  | PNNL ASHRAE 90.1-2007 | 304 | 0 |
  | PNNL ASHRAE 90.1-2013 and 2019 | 304 each | 247 each |
  | PNNL IECC 2006 and 2009 | 304 each | 0 |
  | PNNL IECC 2012 | 304 | 106 |
  | PNNL IECC 2015, 2018 and 2021 | 304 each | 247 each |
  | DOE reference buildings (pre-1980, 1980-2004, new 2004) | 256 each | 0 |
  | PNNL IECC residential (all extracted files) | 11,840 | 0 |
  | PNNL manufactured housing (all extracted files) | 1,216 | 0 |

- **openstudio-standards** builds the same controls at run time from the geometry
  (`space_add_daylighting_controls`). The pinned local cache has the space-type data
  (`target_illuminance_setpoint`, the office non-geometry fractions) but not the
  per-template Ruby rules that decide where controls are required.
- **Plenums.** Release 1.2.0 left 90 spaces without a program: untagged plenums of the
  tall and super-tall buildings and the detailed offices, and laboratory plenums
  tagged Laboratory/Plenum, a row no 90.1 table has (ADR 0039, release notes 1.2.0).

## 2. Decisions

1. **A program-level `lighting_controls` block** on every commercial source program
   and reviewed twin (L-1). Mixes carry none; consumers read their members'.
   - `daylighting`: the controls of the source model zones the program represents,
     or `null` where no zone has controls (a source zero in a complete model):
     controlled floor fraction, controlled lighting-power fraction, illuminance
     setpoint, control type, method, availability, minimum input-power and
     light-output fractions, stepped-control steps, and the zone counts.
   - `daylighting_by_climate`: the locations whose record differs, as
     `value_by_climate` does for loads (most common record, ties to 5A).
   - `geometry_dependent: true`: the fractions hold for the prototype geometry; a
     consumer with other geometry recomputes them (L-2, BEMGen's concern).
   - `status: unknown` with a reason where no source model represents the program.
2. **IECC commercial** values come from the IECC prototypes, zone groups as in ADR
   0040.
3. **90.1 templates** take the daylighting of the PNNL 90.1 prototypes of the same
   edition (2007, 2013, 2019), zones grouped by that template's own geometry tags, plus
   a `standards_rule` with the openstudio-standards space-type inputs (L-2). The
   prototypes back the `code_prototype_rules` family (S3 proved their geometry equal).
4. **DOE Ref templates** record a source zero: no DOE reference model has controls.
5. **Dwellings** record nothing: no IECC residential or manufactured-housing model has
   controls, and the ResStock fixture has no model.
6. **Occupancy-sensor credits** stay inside the lighting schedules and are not
   repeated (L-3).
7. **Plenums (G-1).** The 90 spaces take the template's Any/Plenum row through
   `sources/plenum-aliases.json`, one reason per entry. That adds a plenum program and
   its reviewed twin to 19 folders. None of the spaces counts toward floor area, so no
   mix weight changes. The twins take the resolution policy's plenum rules, as the
   1.0.0 office plenums do (openstudio-standards applies no internal loads to
   plenums): no occupancy, no lighting, no hot water, unconditioned; only the
   equipment schedule stays unresolved, as for the other construction-only programs.
8. **Program JSON 5.4.0**, an additive minor over 5.3.0, is the export of every
   program in release 1.5.0 (`lighting_controls` optional). The 5.1.0, 5.2.0, building
   services and source model constructions schemas add 1.5.0 to their release enums.
9. **Release 1.5.0**, a delta on 1.0.0 holding everything of 1.4.0, written by
   `scripts.atlas_minor_release` as a tagged block.

## 3. Consequences

- Inputs: `data/program-inputs/lighting-controls-v1.json` (`python -m
  scripts.lighting_controls`, reproducible with `--check` where the IDFs are
  present) and `data/program-inputs/plenum-aliases-v1.json` (`python -m
  scripts.plenum_aliases --check` from the pinned openstudio-standards sources).
- 1,373 program records: 195 with controls, 1,178 a source zero. 17 vary by climate,
  all in zones 6A, 6B, 7A and 8A (skylit retail cores, warehouse bulk and fine
  storage, school gyms).
- Every commercial program ID changes (IDs hash content), so the delta replaces the
  program files and the files that cite them.
- `tests/test_lighting_controls.py`; answer keys against the IDFs when
  `ATLAS_PROTOTYPE_ROOT` is set.

## 4. Agent decisions

Each entry: decision; alternatives; reason; evidence.

1. **90.1 control settings from the PNNL prototypes, not openstudio-standards.**
   *Alternatives:* the rule parameters only (the plan's L-2 wording), with the control
   type and fractions unknown; downloading the template rule files. *Reason:* the
   pinned cache lacks the template rules, a download needs permission, and the
   prototypes are the family's backing source. The openstudio-standards inputs are
   kept beside them in `standards_rule`, and the fractions are marked
   geometry-dependent as L-2 asks. *Evidence:* `lighting-controls-v1.json`, 90.1
   records.
2. **Weights.** Fractions and settings are weighted by zone lighting power (area ×
   multiplier × W/m²), by floor area where the program has no lighting.
   *Alternative:* floor area always. *Reason:* the controlled share of lighting
   energy is what the fraction is for. Settings come from the power-dominant zone;
   two records (the IECC 2015 and 2018 secondary-school lobby) have zones with
   different settings and carry `settings_conflict: true`.
3. **Availability as a descriptor.** Every source availability schedule is on all
   days except design days; it is stored as `all_days_except_design_days`, and the
   extractor fails on any other form. *Alternative:* a schedule record. *Reason:*
   one known form; a schedule record would need writer changes.
4. **Unknown, not zero, for programs without a prototype** (construction-only types,
   SuperMarket and 90.1 space types the prototypes do not carry). *Reason:* their
   models were never read; absence there is not a source zero.
5. **Dwellings export as 5.4.0 too.** The residential exporters are pinned by release
   1.4.0, so `atlas_exports.later_residential` sets the 5.4.0 identity and the
   extended source-model schema for the length of one export. *Alternative:* edit
   the exporters (breaks 1.4.0 verification). *Reason:* one Program JSON minor per
   release.
6. **Plenum inputs as a delta.** `scripts.plenum_aliases` reruns the ADR 0039 build
   with the aliases and stores only the added records; it fails if a mix, system,
   service or existing record would change. *Alternative:* regenerate
   `construction-only-v1.json` (pinned by release 1.2.0) or store a second full copy
   (46 MB).

## 5. Open questions

- Whether the 90.1 daylit fractions (from the PNNL prototypes) should become plain
  values rather than geometry-dependent references, once BEMGen decides its own
  daylighting method.
- Whether to fetch the openstudio-standards template rules (a download) so the 90.1
  records can be checked against the rules that generate them.

Answered by the user on 2026-10-27 (plan register, L-1 and L-2):

- **Plain values now**, without waiting for BEMGen: release 2.0.0 drops
  `geometry_dependent`, and consumers apply the recorded fractions as given. BEMGen's
  side is listed in `docs/bemgen-handoff-release-2-0-0.md`.
- **Fetch the template rules** in milestone B, pinned in a source lock, to check the
  90.1 records against them.

Done in milestone B, stage B2 (2026-10-28). The rules are pinned in
`sources/daylighting-rules-lock.json`, and `python -m scripts.daylighting_rules_review`
writes `docs/reviews/daylighting-rules-90-1.md`. No values change.

| Check | Result |
| --- | --- |
| 90.1-2007 controls | none, as its rules require |
| Control type, minimum input-power and light-output fractions (2013, 2019) | agree with the rules |
| Stepped-control steps | three 2013 Outpatient programs have 1 step where the rules give 3 |
| Illuminance setpoints | eight school setpoints (four per edition) are PNNL values that differ from openstudio-standards' space-type table |
| Office whole-building fractions | within the non-geometry caps |
| Which zones get controls, and the other fractions | not checked: they follow from window geometry |
