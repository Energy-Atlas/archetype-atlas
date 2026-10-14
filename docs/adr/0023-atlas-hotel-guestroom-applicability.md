# ADR 0023: Atlas-added generic hotel GuestRoom applicability

Date: 2026-10-14. Status: user approved implementation; local validation only.

## Decision

Expose generic GuestRoom construction applicability inside the hotel building
sets that lack an explicit generic definition. Preserve all source variants,
their assignment order, component physics and the single building ACH reference.

SmallHotel 90.1-2019 has an unused native generic recipe. Attach that same-template
recipe as `when.scope: space_type`, `when.space_type: GuestRoom`, retaining all
four existing occupied/vacant, lower/top-floor variants. The source reference
still does not instantiate generic GuestRoom; applicability is added by Atlas.

Older SmallHotel sets have no separate native generic construction recipe.
Declare generic GuestRoom inheritance on their existing building/story selector
receipts. Do not create a masking space override, copy another vintage/hotel's
physics, or average away source story dependencies. Existing Attic and other
space-specific overrides remain separate. LargeHotel already has native generic
GuestRoom definitions and receives no additional construction assignments.

## Representation and versions

Each relevant selector receipt carries typed `atlas_added_applicability` metadata:
extension schema version 1.0.0, Atlas origin, GuestRoom label, attachment versus
inheritance mode, original source-instantiation flag and an evidence reference.
The original scope and receipt fields retain their meanings. Construction-set
schema 2.0.0 already permits additional receipt metadata; its root/component,
matching and geometry contract is unchanged. A separate extension schema and
semantic validator enforce the added metadata and its complete provenance.

The v2.1.0 data release is a deterministic delta over checksum-verified v2.0.0.
It reuses all original assembly/material physics and adds configurations,
receipts, context references and seven Atlas policy evidence records. Original
v1/v2 artifacts and exporters remain immutable. The policy, implementation and
extension schema are hash-registered; source inventory is checked against the
original frozen geometry hash. Current exports use `load_current_release()` plus
the existing frozen hydrator. The original v2.0.0 loader remains available.

## Delivery and boundaries

Current site packets use the applicability release. A guarded local refresh uses
the configured Markdown extensions and existing page shells, updates construction
pages and content-addressed JSON, and leaves program pages untouched. Relative
document and download links resolve from their Markdown source locations.

The site's download manifest is explicitly a **site delivery** manifest, separate
from the immutable release manifest. It describes the exact served bytes and
filenames, including README.txt and the colocated extension schema, and records
the original release-manifest checksum. This avoids treating renamed Markdown
downloads as a byte-identical release directory.

No program/load/occupancy changes, new infiltration loads, ground or system work,
or BEMGen translator implementation. No push, CI/CD or production publication.
