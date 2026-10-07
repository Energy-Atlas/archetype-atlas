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
