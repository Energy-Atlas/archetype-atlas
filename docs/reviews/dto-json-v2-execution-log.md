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
