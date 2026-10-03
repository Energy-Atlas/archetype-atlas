# Catalogue site review and verification

Date: 2026-10-03. Branch: feat/catalogue-site.

A fresh read-only reviewer inspected v0.2.0 through commit 639fdaa, canonical
release records and the Chromium preview. Reviewer model selector: gpt-6-astra;
exact runtime identifier unavailable. Review considered scientific applicability,
units, missing fields, provenance, output safety, browser state, version URLs,
licensing notices and deployment permissions. Three Important defects were
reported; no Critical or Minor defects were reported.

## Fixes and regression evidence

1. Schedule IDs shared by roles overwrote bindings. Hospital program
   program-063ce56e8cb91eedd1ae lost its heating role when heating/cooling shared
   schedule-ad04522d70d654799159. A real-browser regression failed, then passed:
   both roles appear and export 24 hours, and minimum deadband is correctly zero.
   Record caching is separate from role bindings.
2. Independent sets of referencing building/template labels manufactured joint
   associations. The ApartmentMidRise OCC_APT_SCH record
   schedule-9841fa9f62ff202db619 incorrectly matched HighriseApartment/90.1-2019.
   Python and Node tests failed, then passed after storing exact source reference
   pairs and requiring one pair to satisfy the combined filters. Real
   HighriseApartment/2007 and MidriseApartment/2019 associations remain available.
3. A plot render resumed after a newer day selection, appending stale unit groups.
   A browser test deliberately blocked the first Plotly promise, selected
   Saturday, then released Monday's render. It failed with five mixed charts,
   then passed with three current charts after revision guards were added at
   every plotting await boundary.

## Scope rulings

Annual-calendar generation, complete simulation configurations and resolving
source gaps remain outside site scope. Upstream scientific extraction and
external reuse eligibility are governed by frozen evidence and source terms;
the presentation review does not claim to re-establish them. The expensive
build was verified by the implementer and GitHub Actions rather than repeated
by the reviewer. Initial Pages settings/publication are checked separately.

## Verification

- Full atlas/Python suite: 50 tests pass after fixes.
- Browser logic and schedule parity: seven Node tests pass.
- All 569 schedules: 39,830 day/date selections agree with Python.
- Strict MkDocs builds both frozen release views.
- All built internal URLs, fragments and project-subpath assets pass.
- Real browser checks cover filters/permalinks, role preservation, plots,
  controlled async race, CSV, residential gaps, mobile layout and no-JS fallback.
- Frozen ZIP members match release files byte-for-byte.
- Source values, schema and frozen releases are unchanged.
- Staged security audit runs before every commit.
