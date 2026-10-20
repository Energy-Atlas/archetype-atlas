# Local construction v2 site integration

User scope: integrate the accepted frozen construction-set release into the
existing site, build locally, and stop for review. No push, GitHub workflow,
Pages deployment, BEMGen translator, source recovery, ground or system completion.
Baseline: `23c5f1d`, existing user-selected `feature/json-completion` checkout.

## Delivery

- [x] Replace construction finder rows with 224 source construction sets,
  preserving family, vintage, scope and full-climate/reference applicability.
- [x] Supply climate/reference selection and self-contained JSON v2 preview/copy,
  preserving frozen source physics, fixed ACH, variants and evidence closure.
- [x] Expose all 4,868 assemblies, 858 materials and 8,014 evidence records,
  with source-table-only recipes explicitly distinguished.
- [x] Add the construction contract, frozen examples/schemas, source lock and
  license notices. Keep source record JSON separately available.
- [x] Add a local reuse mode to refresh construction delivery without regenerating
  the research catalogue. Refresh program presentation only when its input/code
  fingerprint differs; no program scientific inputs or contracts change.
- [x] Complete the strict local build and focused delivery/browser checks.
- [x] Complete the full built-link/resource check.
- [x] Inspect staged diff and run the staged security audit; commit locally and stop.

## Decisions and verification record

The implementation follows `design/ui-design-spec.md` section 0 and reuses the
existing filters, compact record shell, theme and JSON verification/copy controls.
The transport packet is site-private schema 1.0.0; copied consumer JSON remains
the frozen construction-set schema 2.0.0. Browser hydration performs selection
and resource closure only. BEMGen retains all actual component/geometry matching.

The prior local site cache was Program JSON v2, so its program presentation was
refreshed from existing v3 inputs. No native recovery or program artifact freeze
ran. Subsequent unchanged runs reuse the v3 presentation. The fingerprint includes
exporter operands, shared semantics and presentation code to prevent stale reuse.

Independent technical review found incomplete cache dependencies and insufficient
page/evidence binding checks. Failing regression cases demonstrated both; repairs
compare complete packets against the immutable freeze and bind actual page
descriptors/context choices/resource routes to the verified delivery report.
Focused tests preserve exact browser/Python pilot document equality and protect
unrelated program pages and custom/subset site builds.

Local generated output and screenshots stay under ignored `build/`. Production
publication remains a separate protected-main task requiring the repository's
release checks. No remote action is authorized in this phase.

Validation: 30 focused Python presentation/delivery tests and seven existing
program/object browser tests pass; two Node construction-selection tests pass.
The strengthened construction verifier also passes all seven focused tests after
the memory-bounded cache change. All generated construction packets/resources
match the freeze and page bindings; no program export failures remain. Largest
decoded profile packet: 4,718,943 bytes (below the existing 16 MB delivery bound).
The strict local MkDocs build passed. Eight construction browser acceptance
checks pass, including exact Medium Office/residential JSON copies, explicit
unsupported/ambiguous selections, integrity/download failures, clipboard denial,
mobile light/dark screenshots and no-JavaScript lists. Screenshots were inspected.

The full built-site checker passed every link/fragment/asset, size ceiling,
retired-route guard, raw/ready program export and frozen construction delivery.
The local preview uses `http://127.0.0.1:8765/archetype-atlas/`; receipts/screenshots
remain in `build/construction-site-screenshots/`. Source science, frozen JSON and
schemas are unchanged. Work is retained as a local feature-branch commit only.
