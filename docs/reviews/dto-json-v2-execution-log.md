# DTO JSON v2 execution log

Plan: `docs/superpowers/plans/2026-10-07-dto-json-v2.md`.
Base: `b45f15a`; branch: `feature/dto-json-v2`. Local work only.

## Preflight

The user authorized autonomous continuation after the schema handoff. Schema
files are a fixed interface for BEMGen. All existing source/release inputs remain
immutable. The current active site still emits historical archives; a fresh
current-only generation path is necessary to retire those outputs reliably.

Ruling: Reuse the user-requested branch in the current checkout, with its locked
source caches, rather than create another checkout. Cost if wrong: concurrent
changes require reconciliation; inspect status before commits.

Ruling: Preserve old generation functions as research tooling, but remove them
from the active build path and publication. No compatibility routes or downloads
are generated. Cost if wrong: unused code remains until a later repository cleanup.

Ruling: Default-filled copying applies to the handed-over program contract;
other object kinds expose exact raw JSON and explicitly identify unresolved
physical inputs. Do not invent HVAC performance or geometry to make an arbitrary
library descriptor look simulation-ready. Cost if wrong: additional object-specific
default contracts would need a later extension.

Ruling: Use the available PowerShell/Python tooling for progress records on
Windows; this committed log supplements the plan's isolated scratch ledger.
Cost if wrong: execution records would be less complete than the helper format.

## Task 1

Seven exporter tests first failed because the exporter was absent. The adapter
and defaults then passed all fourteen contract/export tests. The full-library
audit exported 1,900 raw and 1,900 defaulted programs with no failures in 119.9 s;
largest decoded payload was 673,497 bytes. A further RED/GREEN check ensures
source-known water targets are not labelled as experimental defaults. Annual
2007 calendars, count-based residential loads and positive mixture leaves remain
intact. Source definitions and the handed-over schemas are unchanged.

## Task 2

Three active-site tests first failed for the missing current-only generator.
Nine active/definition/HTML tests now pass. The active CLI builds a fresh staging
tree from the definition bundle only: no release catalogues, historical download
trees, v1 delivery, retained snapshots or old curated navigation are copied.
Programs expose verified raw/defaulted DTO descriptors and unknown values;
materials, components, schedules and all referenced records have designated pages.

Ruling: Energy objects use MkDocs pages; the much larger evidence/coverage tables
use compact generated HTML object pages with the same JSON inspection controls.
This keeps every record inspectable without expanding 43,000 evidence records
through the Markdown engine. Cost if wrong: metadata pages need their own small
presentation shell rather than Material's navigation runtime.

## Task 3

The eight schedule-core tests first failed for the missing module; all 22 Node
tests now pass. New pure schedule functions preserve wrapped seasons, leap days,
last-specific precedence, separate holidays/design days, exact unique profiles,
unknown gaps and recorded annual years. The interactive controller adds step
curves, a clickable annual heatmap and exact daily tables.

Plotly cartesian 3.1.0 includes scatter and heatmap (official distribution README).
Its local asset is locked at 1,339,916 bytes, SHA-256
`c462b40a1a542e16c3533f97d39fbbb91af4f5267f3cbf23bd70d785efc44c38`;
the existing MIT notice remains required.

Ruling: Run browser plot integration in Task 4 because it consumes that task's
verified object loader. Pure schedule and asset checks run now. Cost if wrong:
integration problems appear in Task 4 rather than this task's first test cycle.

## Task 4

The first browser test failed because the copy popup did not exist. The shared
loader now verifies the bounded compressed resource, SHA-256 and decoded size
before inspection, plotting or copying. All 23 focused Python/browser tests and
all 22 Node tests pass. Chromium exercised raw/defaulted full DTO copying before
expansion, native modal focus/Escape, clipboard rejection with complete selectable
text, checksum rejection without changing the clipboard, linked step/heatmap
plots, leap-year updates, recorded annual calendar locking and component JSON.
A repeated-copy test exposed stale success text; opening a new choice clears it
so consumers cannot mistake an earlier copy for the current operation.

## Task 5 — verification in progress

The retirement/export checker first failed because it was absent; its pilot now
passes and rejects retired routes, stale search entries and missing defaulted
exports. The fresh active browser smoke first failed for the missing module;
its pilot passes search, gates, filters, full copying, plots, mobile and no-JS.
Static exact source profiles first failed their presence check and now pass,
including all recorded annual day profiles. The popup policy inspection also
passed RED/GREEN: it exposes verified substitutions and external bindings without
changing the two copy choices. The focused acceptance suite passed 20/20 before
these additions; the latest fallback/browser suite passed 11/11 and the expanded
browser suite passed 7/7.

The first full active generation produced 65,597 object pages, including all
1,900 raw/defaulted program pairs with zero export failures. Independent
definition and canonical table rebuilds reproduced their original bytes. Schema,
physical, schedule, relationship and provenance validation passed. Full-suite,
final HTML/size/link checks and fresh review are still pending here.

Ruling: Retain only the freshly generated current v2 manifest and its single
content-addressed snapshot path, because the current finder delivery contract
requires it. No previously published snapshots or v1 output are restored.
Cost if wrong: removing that internal manifest path would require changing the
current delivery contract and client, rather than merely retiring old pages.

Ruling: Include exact unique source-day tables in schedule HTML so values remain
inspectable without Plotly or JavaScript. All annual dates are associated with
their exact source profiles. Cost if wrong: larger HTML output; the unchanged
publication ceiling and mobile overflow checks remain mandatory.

## Fresh whole-branch review and one fix pass

A fresh read-only reviewer inspected `c1538e3..c6b7908`, the fixed contracts,
specification, plan and rulings, and independently passed 14 contract/export and
eight schedule-core tests. No Critical findings or declined judgments. All three
Important findings retain that grade by actual consumer impact:

1. Existing fractional schedule gaps incorrectly inherited the positive-load
   missing-reference fallback 1. The regression for the Large Office Data Center
   first failed with `[1]` instead of `[0]`; uncovered existing schedules now use
   policy zero while a wholly missing positive-load schedule still uses one.
2. Raw Surgery/Outpatient mixtures repeated constituent local water services as
   shared demands. The regression first found all five duplicated services;
   represented demand identities are now collected recursively from source
   components before deduplication.
3. Mixture assumptions used metadata at `/loads` rather than its actual array.
   The regression first failed the exact pointer/value comparison. Leaf paths
   now use final indices and weighted values; array recomposition records the
   actual before/after arrays. Composed controls record their resulting schedules,
   unused leaf control records are excluded and semantic validation rejects
   orphan/mismatched assumption pointers. All 17 contract/export tests pass.

The pre-fix full suite passed 229/229; all 22 Node tests and all 4,410 schedule
calendar/profile inspections passed. There are 503 recorded annual schedules and
6,264 uncovered raw hours in the audit's leap-year rule preview. The post-fix full
suite passed 232/232 in 631.8 s; fresh generation again produced all 65,597 objects
and 1,900 raw/defaulted program pairs with zero failures. Final HTML checks are
running. There is no
second review; the regressions and green full suite verify this single fix pass.

Final: fixed existing positive fractional schedule gaps —
`test_existing_positive_schedule_gap_uses_zero_not_missing_schedule_one`
RED→GREEN, whole suite 232/232.

Final: fixed duplicated raw mixture water services —
`test_raw_mixture_does_not_repeat_constituent_water_as_shared_services`
RED→GREEN, whole suite 232/232.

Final: fixed mixture assumption pointers and actual replacement records —
`test_mixture_assumptions_resolve_to_exact_exported_values`
RED→GREEN, whole suite 232/232.

Ruling: Run the one fresh review while lengthy full-site verification was in
flight, then verify its fixes with regressions, the complete post-fix suite and
the final built artifact. Cost if wrong: the reviewer cannot rely on final HTML
results; the author's final acceptance checks must cover that evidence.

Final: minor (deferred): the default policy's final note and ADR 0015's status
still describe website integration as pending. Their numeric policy/contract is
unchanged; current build docs and this execution log state the implementation.
