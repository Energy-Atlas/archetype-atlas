# Construction delivery: detailed v2.2.0 and unified 1.1.0

Prepared: 2026-10-15; shared-mass consumer update: 2026-10-16.
The [construction implementation closure](reviews/construction-milestone-closure.md)
records completed review and all-context validation. Protected-main publication
and BEMGen integration testing remain separate gates.

The current site adds shared-mass release **1.0.0**, delivering consumer schemas
**2.1.0** (detailed) and **1.2.0** (unified) over these unchanged normalized
releases. See [shared-mass release notes](release-notes-construction-mass-v1.0.0.md).
Publication is marked by `construction-delivery-2026-10-16` only after successful
protected-main Pages deployment and live verification.

## Release identities

| Artifact | Release | Consumer schema | Purpose |
| --- | --- | --- | --- |
| Detailed construction distribution | v2.2.0 | 2.0.0 | Complete building/dwelling sets with source assemblies and embedded assignment rules |
| Hotel applicability delta | v2.1.0 | 2.0.0 plus typed applicability receipt | Explicit generic GuestRoom applicability, preserving source distinctions |
| Detailed normalized base | v2.0.0 | 2.0.0 | Immutable shared assembly/material/evidence tables |
| Additive unified construction | 1.1.0 | 1.1.0 | One assembly per applicable semantic, reference weights, mass budgets and fit errors |
| Supporting reference profiles | 1.1.0 | Supporting-data schema 1.0.0 | Source-archetype exposure, floor shares and physical inventories |

The v2.2.0 distribution is a checksum-locked projection over the v2.1.0 delta
and v2.0.0 base, rather than a standalone copy of all tables. Use the current
loader or export CLI below. Keep all required frozen directories and manifests
together. Schema versions describe documents; release versions describe their
data and selection policy. Historical releases remain immutable and accessible
in the repository.

## Coverage and migration

There are 177 complete construction sets: 136 commercial building sets and 41
residential whole-dwelling sets. Both representations cover all 3,320 supported
climate/reference contexts, with zero active blockers under accepted policies.
Detailed physics retains 4,868 assemblies and 858 materials. Independent
source-table recipes remain identified without invented prototype applicability.

Construction sets include exterior/interior components together. Room/story
overrides are embedded in their building sets: 1,470 source contexts are retained
and 47 standalone partial space-type sets are retired from current selection.
Eight unsupported office plenum 0A/0B contexts remain nonselectable source
evidence. An unsupported climate is not substituted with another climate.

SmallHotel generic GuestRoom applicability is explicitly Atlas-added. The 2019
native generic recipe and all four specific variants remain distinct. Older
SmallHotel definitions retain their source building/story inheritance. A generic
recipe without instantiated reference area creates no invented blending share.

The website offers **Copy detailed JSON** and **Copy unified JSON** directly,
using the selected climate/reference independently of preview mode. There is no
construction source-record chooser; provenance remains inside the consumer data.
Program and other object copy behavior is unchanged. Scope and evidence-view
filters are absent from the construction finder; those distinctions remain metadata.

Consumers of former standalone space-type sets should select the complete
building set and evaluate its embedded rules. Consumers without component-level
program allocation can select the separate additive unified representation.
Detailed source assemblies and rules are preserved, not replaced by the blend.

## Modeling policies and limitations

- Fixed natural ACH uses source-archetype geometry and the accepted 2013 climate
  reference map. Residential source annual-average and commercial passive-envelope
  reference policies are retained. The same scalar applies across zoning variants;
  it does not model mechanical ventilation or operating door additions.
- Unified opaque recipes conserve common-reference-film conductance and areal
  heat capacity with two massive layers and one massless resistance, or a
  source-proven massless construction. The deterministic two-parameter fit has
  recorded frequency-response errors. It may inadequately reproduce some source
  assemblies; review flags are retained and do not silently increase layer count.
- Weights use precomputed source-archetype exposure rather than actual consumer
  geometry or population prevalence. Native program support keys are not new
  program load definitions.
- Unequal paired-face zone multipliers use the accepted symmetric mean of the
  multiplied areas. Original operands and approximation flags are retained.
- Residential overhang dimensions remain source evidence. BEMGen supplies actual
  overhang geometry; the unified export does not average geometric shadows.
- BEMGen supplies areas and geometry, resolves detailed assignments or unified
  semantics, reverses canonical paired floor/ceiling layers, and reconciles
  represented wall/slab mass with additional and residual mass budgets. Do not
  apply both representations' mass quantities or add explicit slabs twice.

Ready means contract completeness under these policies. Analytical wall tests
and small historical EnergyPlus material smoke cases do not establish annual
building-energy accuracy. Systematic construction-versus-zoning error validation
remains deferred. Ground/foundation, systems and translator implementation are
outside this release; program and existing schedule contracts remain independent.

## Export and verification

Use an ID from the current distribution, not a retired partial space context:

```console
python -m scripts.construction_distribution --context-id ID --output detailed.json
python -m scripts.construction_equivalent_release --context-id ID --output unified.json
```

Both commands use the same detailed context ID. The Python equivalent is
`construction_distribution.load_current_release()` plus
`construction_set_release.hydrate_context()` for detailed data, and
`construction_equivalent_release.export_frozen()` for unified data.

```console
python -m scripts.construction_base_reproduce --quiet
python -m scripts.construction_hotel_applicability --check
python -m scripts.construction_distribution --check
python -c "from scripts.construction_weighting import load_profiles; load_profiles()"
python -m scripts.construction_equivalent_release --check
```

The unified byte-reproduction command requires the original **Windows x64 /
CPython 3.14.7** producer. Cross-platform validation of every current detailed/
unified pair uses `python -m scripts.construction_delivery_validate`. Current
consumer exports can be generated from frozen data using
`construction_mass_release --context-id ID --representation detailed|unified
--output selected.json`. See [site build instructions](site-build.md) for the
producer pin and exhaustive Linux/Windows consumer checks.

These checks are configured in the existing research matrix. Profile integrity
verification uses frozen files and declared input hashes. Reproducing normalized
profiles with `construction_weighting --check` additionally requires the ignored
native-recovery cache; it is a maintenance check, not a fresh-checkout CI step.
The site build must pass
`site_check --require-construction` and the separate construction browser harness
before artifact upload. Actual remote check results are not claimed by this
local preparation. See [site build instructions](site-build.md) and the
[publication preparation record](reviews/construction-publication-preparation.md).

Retain `LICENSE`, `sources/licenses/` and the frozen base's source notices when
redistributing permitted upstream data. Original Atlas work remains unlicensed
by user choice. No source licensing terms are changed by this candidate.
