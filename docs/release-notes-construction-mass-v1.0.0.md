# Construction shared-mass completion 1.0.0

Prepared 2026-10-16; included in the protected-main construction publication.
The publication marker `construction-delivery-2026-10-16` is created after
successful Pages deployment and live verification. BEMGen code and simulation
remain outside this release.

Detailed JSON **2.1.0** and unified JSON **1.2.0** now embed the same shared
mass-accounting **1.0.0** contract. The normalized overlay covers **177 complete
construction suites and 3,320 contexts**, with **496** distinct contracts and no
missing source mass inputs. Its manifest locks profiles, source release manifests,
new implementation, three schemas and every output payload by SHA-256.

The change closes the detailed export's source-quantity gap: InteriorWall and
InteriorFloor reference capacity budgets, and original commercial additional-mass
materials/quantities/scopes, including non-counted plenums. Residential partition
scaling remains source-defined. Source material/assignment rules, infiltration,
equivalent layer fits and approximation errors are unchanged. New quantities are
read from existing frozen support profiles; no source model, schedule or annual
simulation is regenerated.

Consumers dispatch on both kind and version. The two new consumer schemas embed
the common definitions, so each schema/document is self-contained. The shared
registry supplies original added-mass material layers independently of the legacy
detailed envelope registry or unified equivalent layer format. This is an additive
representation revision; every old schema, frozen construction release, API and
local handover packet remains available and unchanged.

Seven Git-controlled paired examples in docs/examples/construction-mass-v1 cover
Medium Office 2019/3B, Warehouse 2019/3B, sparse residential 5A, multistorey/garage
residential 4A, raised/exposed-floor residential 1A, MidriseApartment 2019/3B and an existing-stock apartment unit 1990s/4A. Sparse source_absent and
not_applicable components remain valid. Additional mass is instantiated once;
the legacy partition selector and equivalent mass objects must not create copies
of the inventory. Unknown source quantities fail explicitly, while known-zero
inventory is represented without an invented material or area.

Reference preservation is a consumer responsibility. Scale reference budgets by
actual counted building floor area, deduct represented interior capacity once and
restore only a positive residual by category. Retain signed residual/excess
diagnostics. Source-scope allocation needs explicit BEMGen handling when scopes
are absent after rezoning. The accounting is not an annual energy-accuracy claim.

See [the contract](construction-mass-accounting-v1-contract.md) and
[ADR 0026](adr/0026-shared-construction-mass-accounting.md). Local verification:

```console
python -m unittest tests.test_construction_mass_accounting tests.test_construction_mass_release tests.test_construction_equivalent_export tests.test_construction_distribution -q
python -m scripts.construction_mass_release --check --examples --validate-all
```

Exact regeneration uses **Windows x64 / CPython 3.14.7**, the verified producer.
Both Linux and Windows validate all frozen consumer exports with
`python -m scripts.construction_delivery_validate`. See
[the producer and consumer validation policy](site-build.md) for the numerical
runtime/platform distinction; no frozen materials, fit errors or IDs are changed.

Ground/foundation, systems, Program JSON migration and schedule generators remain
outside this completion. The site supplies separate direct-copy detailed and
unified exports with this shared contract. Retain all
Atlas and upstream licensing/notices; fixture preparation does not relicense
Atlas original work or authorize a BEMGen fixture commit.
