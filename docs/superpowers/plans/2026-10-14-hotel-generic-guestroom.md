# Hotel generic GuestRoom applicability

Approved: attach generic guest-room construction applicability to hotel sets
without it, preserve specific variants and record Atlas-added applicability.
Local validation only; no push, CI/CD, program changes, ground or systems work.
Baseline `7770a6f`, existing user-selected `feature/json-completion` checkout.

## Implementation

- [x] Observe failing tests for all missing hotel definitions, preservation of
  native variants/infiltration, provenance, inheritance and repeatability.
- [x] Add a versioned, checksum-locked applicability policy and delta release.
  SmallHotel 2019 attaches its own native generic recipe; older SmallHotel sets
  declare generic GuestRoom inheritance through their existing building/story
  rules. LargeHotel generic definitions remain native. No cross-template recipe
  borrowing or averaging, no occupancy/load changes.
- [x] Integrate the overlay into current site packets and consumer exports.
  Keep frozen v1/v2 files, schemas and original exporter/hydrator unchanged.
- [x] Validate schema, physics, graph/provenance, all affected contexts,
  unaffected pilots, exact preservation and deterministic reproduction.
- [x] Refresh the existing local site using a guarded generator for changed
  content-addressed packets and their HTML descriptors; avoid a full unrelated
  page/program build. Run browser acceptance and focused delivery checks.
- [x] Fresh technical review, repair substantive findings with regressions,
  inspect staged diff, audit and commit locally. Stop for user review.

## Contract and decisions

Construction consumer schema remains 2.0.0: selector receipts already allow
additional metadata. A typed `atlas_added_applicability` extension is recorded on
relevant receipts and linked to provenance. Its own contract/policy is versioned.
For older sets this declares the generic label's existing fallback semantics;
it does not insert a space-type override that could mask source story overrides.
SmallHotel 2019 gains actual `when.space_type: GuestRoom` assignments from the
same-template native standalone recipe. All four specific variants stay intact.

The data release is a small v2.1.0 delta over checksum-verified v2.0.0. Existing
material/assembly resources are reused; only applicability/configuration receipts,
context references and new Atlas evidence are added. The original freeze remains
available and byte-identical. Implementation and policy hashes are registered.

## Execution record

Preflight: clean feature checkout; repository brief read. User approval covers
the proposed attachment and older-template inheritance approach. No additional
approval gate is needed. Review only the scoped change against this baseline.

Implementation: seven SmallHotel definitions / 143 contexts, comprising 21 native
generic-recipe attachments and 122 generic inheritance declarations. No new
material/assembly physics. Older DOE references also have Attic space overrides;
those stay unmarked and unchanged because generic inheritance uses only native
building/story fallback receipts.

Fresh technical review identified three Important issues. Negative regressions
first reproduced incorrect relative JSON/download links in the focused renderer,
missing frozen-geometry hash verification, and an inaccurate site delivery
manifest after filename transformation. All three regression cases pass after
repair. ADR 0023 records the typed metadata extension and data/schema versions.
Broader CI/native/program/full-site work remains explicitly out of scope.

Final validation: 43 focused Python tests and two Node tests pass. The delta's
`--check` validates all 143 affected contexts and unchanged Medium Office and
residential pilots, and reproduces every artifact byte. Existing source-specific
assignments/physics/ACH are preserved; unsupported or missing provenance/policies
are rejected. Browser acceptance has nine scenario groups, including exact
SmallHotel 2019 and 2007 copying, policy downloads, source variants, integrity
failures, mobile themes and no-JavaScript lists. Hotel mobile screenshots inspected.

Focused site refresh: 224 construction pages / 4,798 contexts, no program pages
regenerated. All construction delivery packets/resource bindings verify; all 232
refreshed pages (sets, guide and new evidence) pass internal-link checks. Static
download manifest hashes/filenames pass. Original v1/v2 files, schemas, source
exporters, program inputs and workflow configuration remain unchanged. Staged
diff inspection and security audit precede a local feature commit; no push or
CI/CD. The preview stays at http://127.0.0.1:8765/archetype-atlas/.
