# ADR 0033: Explicit local reference sidecar for release layout 2

Status: accepted for the R67 packaging implementation; full A5 shipment gates remain closed.

The cumulative reference cannot be transported inside the generator ZIP within
the existing per-file limit. The old ZIP reproduction entrypoint reads only its
own extraction; a neighboring reference cannot cross that boundary implicitly.

Release manifest schema `2.0.0` therefore declares exactly four local files:
`manifest.json`, `generator.zip`, `reproduce.py`, and
`references/all-cases-bundle.json.gz`. The manifest inventories the three other
files, every ZIP member, exact request, raw and compressed reference identities,
and the runner/producer source provenance. It excludes its own hash. The runner
is copied byte-for-byte from `scripts/schedule_generator_release_reproduction.py`.
Transport hashes establish byte integrity, never scientific qualification.

The standard-library runner verifies the entire incoming release, safely
extracts its verified ZIP, and calls that package's unchanged ordinary
request/output CLI in the same process. It strictly validates both complete
bundles, requires their comparison policies to equal the verified packaged
resource, and uses the extracted scientific comparator. Its single parent
600-second timeout includes inventory, bounded single-gzip decoding, extraction,
generation, canonical output, parsing, both strict validations, comparison and
receipt. A separate ordinary ZIP generation gate retains 240 seconds. Every
transported file and tracked member retains the 104857600-byte limit; the full
decoded byte count is recorded separately and bounds decoding without truncation.

Both the release helper and apartment profiler select the same command from
`manifest.json`. The profiler copies all four inputs outside the repository and
keeps requests and outputs in a separate work directory. A successful receipt
is required; absence, partial results, nonzero exit and timeout all fail. There
is no external-reference discovery, request override or checkout fallback.

Layout 2 ZIP-only `--reproduce` exits 2 with an explicit release-level command.
The ZIP remains sufficient for ordinary generation. Layout 1 manifests,
bootstrap bytes, embedded all-cases/mixed references and historical releases
retain their existing route. Release schema 2 changes packaging only: public
request/bundle schemas, API/CLI implementation, resources, scientific source
proofs, qualification, controls, comparison tolerances and runtime reproduction
module are unchanged. Full current/3.11 feasibility, exact A5 science, final
suite, immutable release and independent reviews remain separate gates.
