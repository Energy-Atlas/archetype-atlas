# Selective Schedule Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Execution is autonomous under the user's instruction.

**Goal:** Execute reproducible residential schedule generation and selectively resolve justified inactive loads/conditioning with explicit provenance.

**Architecture:** A checksum-locked upstream runner produces profile artifacts; an evidence-gated resolver produces assumptions. A separately versioned supplement references immutable v0.2.0 and is displayed alongside source facts in the catalogue.

**Tech Stack:** Python, JSON Schema, pinned OpenStudio 3.10.0/Ruby and bundled OpenStudio-HPXML 1.11.0; existing MkDocs/Plotly.

**Spec:** docs/superpowers/specs/2026-10-03-schedule-resolution-design.md

## Global constraints

- Preserve frozen releases and reported nulls; never infer zero solely from absence.
- Prioritize actual upstream execution for all 41 residential configurations.
- Fix seed/year/timestep and label any reference-context input explicitly.
- Disable inactive conditioning explicitly; numerical sentinel temperatures are not source facts.
- No automatic support-space or electric-HVAC classification.
- SI normalized values; original values/units, locators, transformations and interpretation are retained.
- Source/runtime archives stay immutable and locked; original work remains unlicensed.
- Every commit requires staged diff inspection, staged audit and automated identity/trailer.

## Review focus

- A missing/positive load or mixed-fuel appliance must prevent an unjustified zero.
- Generic generated appliance columns must not imply appliance installation.
- Calendar, location, stochastic seed and thermostat offsets must remain interpretable.
- A partial generation failure must remain visible and not appear as simulation readiness.
- Catalogue evidence and downloads must distinguish source facts from assumptions.

## Task 1: Execute residential generator (highest priority)

Files: sources/runtime-lock.json; scripts/runtime.py; scripts/residential_profiles.py;
scripts/run_residential_profiles.rb; tests/test_residential_profiles.py;
docs/residential-generation.md. Generated outputs: ignored build/residential/.

Interfaces: runtime.fetch_runtime(lock, destination) returns verified paths;
residential_profiles.build_inputs(release, policy) returns deterministic run inputs;
residential_profiles.validate_profiles(path, metadata) checks executed output.

- [ ] Inspect pinned generator/runtime requirements and source input translation; document exact generation boundary.
- [ ] Test corrupted locks/unsafe paths, annual dimensions, invalid fractions and explicit input provenance; watch tests fail.
- [ ] Implement locked retrieval and upstream runner; test one recipe before expansion.
- [ ] Execute all 41 recipes with fixed seeds/calendar; validate outputs, match source controls and absent end uses; rerun pilot deterministically.
- [ ] Commit runner, locks, validation and scientific decisions after staged audit.

## Task 2: Selective resolution supplement

Files: schemas/resolution.schema.json; sources/resolution-policy.json;
scripts/resolve.py; tests/test_resolution.py; docs/adr/0004-selective-resolution.md.
Outputs: data/resolution-releases/v0.1.0/ with manifest, resolutions and profile index.

Interfaces: resolve.resolve_records(data, policy, profiles) returns explicit
resolution rows; resolve.validate_bundle(path) verifies schema, references,
evidence, units and hashes. Profiles are linked from Task 1, never fabricated.

- [ ] Test fail-closed handling of absent/positive loads, mixed/unknown fuels, conditioned spaces, water-use ambiguity and unchanged source records.
- [ ] Implement exact evidence-backed rules and explicit reviewed record IDs; emit unresolved candidates separately.
- [ ] Validate all applied assumptions and executed profiles, reproducibility and complete provenance; freeze the supplement with checksums and notices.
- [ ] Commit the versioned supplement and ADR after audit.

## Task 3: Catalogue delivery and review

Files: scripts/site.py; website/assets/site.js; website/content/guides/residential.md;
website/content/methods.md; tests/test_site.py; scripts/site_smoke.py;
docs/site-publication.md; this plan's implementation ledger.

Interfaces: site consumes only a validated resolution bundle; detail packets
include source record plus separately labelled resolution/profile metadata.

- [ ] Test resolution labels, original null preservation, referenced profile downloads and annual/day plot selection.
- [ ] Render assumption evidence and generated residential plots with units, seed/calendar and unresolved controls visible.
- [ ] Run Python/Node suites, release/supplement validation, strict site build, links and browser checks.
- [ ] Obtain one fresh whole-branch review, fix material findings with regressions, and publish the verified artifact autonomously without merging research branches.

## Implementation ledger

- Authorization: user's five rules plus prior autonomous/no-intervention instruction.
- Isolation: feat/schedule-resolution starts from aff4d3f; existing checkout retained by prior branch preference.
- Pre-flight: immutable v0.2.0 -> upstream input projection -> profiles -> supplement validation -> catalogue. Original record identities survive every boundary.
- Ruling: use an additive resolution release rather than mutate the atlas schema/frozen rows. Cost if wrong: a later normalized-schema migration; scientific source evidence stays intact.
- Ruling: use explicit inactive conditioning, not arbitrary extreme setpoints. Cost if wrong: a downstream numerical adapter must implement its own documented sentinel policy.
- Ruling: autonomous instruction supersedes skill design/plan approval handoffs. Cost if wrong: reversible branch/documentation changes and publication rollback.
